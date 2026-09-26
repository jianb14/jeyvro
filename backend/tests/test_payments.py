"""Phase 9 gate tests — payments, COD, refunds, ledger (PROJECT_CONTEXT §6).

Wave 1 of the payments gates: every order gets a payment whose amount is
server truth, COD captures at collection (the reservation commits), refused
methods leave no partial rows, duplicate captures are safe no-ops, and
refunds are balance-checked and reverse the ledger. Balance is always the
sum of immutable ledger rows.
"""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.catalog import services as catalog_services
from apps.catalog.models import Inventory, Product, StockMovement, Variant
from apps.orders.models import Order, SellerOrder
from apps.payments.models import (
    Payment,
    PaymentAttempt,
    PaymentTransaction,
    Refund,
)
from apps.stores.models import Store

pytestmark = pytest.mark.django_db

REGISTER = '/api/v1/auth/register'
LOGIN = '/api/v1/auth/login'
ADDRESSES = '/api/v1/auth/addresses/'
CHECKOUT_ORDERS = '/api/v1/checkout/orders'
CART_ITEMS = '/api/v1/cart/items'

CUSTOMER = {'email': 'paybuyer@example.com', 'password': 'Str0ng!Passw0rd'}
OTHER = {'email': 'payother@example.com', 'password': 'Str0ng!Passw0rd2'}
STAFF = {'email': 'paystaff@example.com', 'password': 'Str0ng!Passw0rd3'}

ADDRESS_PAYLOAD = {
    'full_name': 'Bianca Buyer',
    'phone': '09171234567',
    'line1': '12 Mabini Street',
    'line2': 'Unit 4B',
    'city': 'Quezon City',
    'province': 'Metro Manila',
    'postal_code': '1100',
}


def register(client, payload):
    return client.post(REGISTER, payload, content_type='application/json')


def login(client, email, password):
    return client.post(
        LOGIN, {'email': email, 'password': password},
        content_type='application/json',
    )


def make_active_store(email, name, *, fee='0.00', threshold=None):
    """Direct ORM setup — Phase 4 flows are covered by test_stores.py."""
    user = User.objects.create_user(email=email, password='Str0ng!Passw0rd')
    store = Store.objects.create(
        user=user,
        name=name,
        status=Store.Status.ACTIVE,
        shipping_flat_fee=Decimal(fee),
        free_shipping_threshold=(
            Decimal(threshold) if threshold is not None else None
        ),
    )
    return user, store


def make_product(store, *, title='Test Product', price='299.00',
                 compare_at='399.00', stock=10):
    product = Product.objects.create(
        store=store,
        title=title,
        base_price=Decimal(price),
        compare_at_price=Decimal(compare_at) if compare_at else None,
        status=Product.Status.PUBLISHED,
    )
    variant = Variant.objects.create(
        product=product, name='Default', price=Decimal(price), is_default=True,
    )
    catalog_services.ensure_inventory(variant, initial_on_hand=stock)
    return product, variant


def make_customer(client, user=CUSTOMER):
    """Registers + logs in the buyer; returns their default address id."""
    register(client, user)
    login(client, user['email'], user['password'])
    response = client.post(
        ADDRESSES, ADDRESS_PAYLOAD, content_type='application/json'
    )
    assert response.status_code == 201, response.content
    return response.json()['id']


def login_as_staff(client):
    register(client, STAFF)
    User.objects.filter(email=STAFF['email']).update(is_staff=True)
    # 13.5 tightened refunds to finance/administrator (§4 least privilege);
    # this helper's staff user settles money, so it carries the finance group.
    finance, _ = Group.objects.get_or_create(name='finance')
    User.objects.get(email=STAFF['email']).groups.add(finance)
    response = login(client, STAFF['email'], STAFF['password'])
    assert response.status_code == 200, response.content


def add_to_cart(client, variant, quantity=1):
    response = client.post(
        CART_ITEMS,
        {'variant_id': variant.id, 'quantity': quantity},
        content_type='application/json',
    )
    assert response.status_code == 200, response.content
    return response


def checkout(client, address_id, method=None):
    payload = {'address_id': address_id}
    if method is not None:
        payload['payment_method'] = method
    return client.post(CHECKOUT_ORDERS, payload, content_type='application/json')


def place_order(client, *, method='cod', fee='50.00', price='299.00',
                quantity=1, stock=10):
    """Full HTTP checkout; returns (order payload, store, variant)."""
    _seller, store = make_active_store('payseller@example.com', 'Pay Store', fee=fee)
    _product, variant = make_product(store, price=price, stock=stock)
    address_id = make_customer(client)
    add_to_cart(client, variant, quantity=quantity)
    response = checkout(client, address_id, method)
    assert response.status_code == 201, response.content
    return response.json(), store, variant


# --- 9.1 / 9.2 COD flow: payment record, awaiting_payment, capture ---

def test_cod_checkout_creates_a_pending_payment_and_awaits_payment(client):
    body, store, variant = place_order(client)

    assert body['status'] == 'awaiting_payment'
    payment = body['payment']
    assert payment['method'] == 'cod'
    assert payment['status'] == 'pending'
    assert payment['amount'] == 349.0  # 299 + 50 shipping, server-computed
    assert payment['currency'] == 'PHP'
    assert payment['expires_at'] is None  # cash is due at delivery
    assert payment['paid_at'] is None
    assert payment['refunded_total'] == 0.0

    record = Payment.objects.get(reference=payment['reference'])
    assert record.order.number == body['number']
    assert record.amount == Decimal('349.00')
    assert record.provider == 'cod'

    # Reservation only — the money has not moved yet.
    inventory = Inventory.objects.get(variant=variant)
    assert inventory.on_hand == 10
    assert inventory.reserved == 1
    assert SellerOrder.objects.get(order=record.order).status == 'awaiting_payment'
    assert PaymentTransaction.objects.count() == 0
    assert AuditLog.objects.filter(action='order.placed').exists()


def test_checkout_defaults_to_cod_when_no_method_is_sent(client):
    _seller, store = make_active_store('defaultseller@example.com', 'Default Store')
    _product, variant = make_product(store)
    address_id = make_customer(client)
    add_to_cart(client, variant)

    response = checkout(client, address_id)  # no payment_method
    assert response.status_code == 201, response.content
    assert response.json()['payment']['method'] == 'cod'


def test_unavailable_online_methods_leave_no_partial_rows(client):
    _seller, store = make_active_store(
        'onlinefail@example.com', 'Online Store', fee='50.00'
    )
    _product, variant = make_product(store)
    address_id = make_customer(client)
    add_to_cart(client, variant)

    response = checkout(client, address_id, 'gcash')
    assert response.status_code == 400, response.content
    assert response.json()['error'] == 'payment_method_unavailable'
    assert Order.objects.count() == 0
    assert Payment.objects.count() == 0
    # The whole transaction rolled back — no reservation survives.
    assert Inventory.objects.get(variant=variant).reserved == 0


def test_checkout_preview_publishes_payment_options_with_availability(client):
    _seller, store = make_active_store('optionsseller@example.com', 'Options Store')
    _product, variant = make_product(store)
    make_customer(client)
    add_to_cart(client, variant)

    body = client.get('/api/v1/checkout/').json()
    options = {option['id']: option for option in body['payment_methods']}
    assert set(options) == {'cod', 'card', 'gcash', 'maya'}
    assert options['cod']['available'] is True
    assert options['cod']['label'] == 'Cash on Delivery'
    # Server truth: no gateway exists yet, so online methods stay unavailable.
    assert options['gcash']['available'] is False


def test_staff_cod_collection_captures_and_commits_the_sale(client):
    body, store, variant = place_order(client, quantity=2)
    reference = body['payment']['reference']
    order = Order.objects.get(number=body['number'])
    seller_order = SellerOrder.objects.get(order=order)

    login_as_staff(client)
    response = client.post(f'/api/v1/payments/{reference}/cod-collected')
    assert response.status_code == 200, response.content
    payload = response.json()
    assert payload['status'] == 'paid'
    assert payload['paid_at'] is not None

    order.refresh_from_db()
    seller_order.refresh_from_db()
    assert order.status == 'paid'
    assert seller_order.status == 'paid'

    # Reservation → sale: on_hand and reserved both drop.
    inventory = Inventory.objects.get(variant=variant)
    assert inventory.on_hand == 8
    assert inventory.reserved == 0

    # Ledger: one capture row per store, whose sum is the order total.
    entries = PaymentTransaction.objects.filter(payment__reference=reference)
    assert entries.count() == 1
    entry = entries.get()
    assert entry.kind == 'capture'
    assert entry.direction == 'credit'
    assert entry.amount == Decimal('648.00')  # 2 × 299 + 50 shipping
    assert entry.seller_order_id == seller_order.id
    assert sum(e.amount for e in entries) == order.grand_total

    assert PaymentAttempt.objects.filter(
        payment__reference=reference, status='succeeded'
    ).count() == 1
    assert AuditLog.objects.filter(action='payment.captured').exists()


def test_duplicate_captures_are_safe_no_ops(client):
    body, _store, _variant = place_order(client)
    reference = body['payment']['reference']
    login_as_staff(client)

    first = client.post(f'/api/v1/payments/{reference}/cod-collected')
    assert first.status_code == 200, first.content
    second = client.post(f'/api/v1/payments/{reference}/cod-collected')
    # Idempotent by design: a duplicate confirmation returns the unchanged
    # payment (200) — never a second capture, attempt, or ledger row.
    assert second.status_code == 200, second.content
    assert second.json()['status'] == 'paid'

    # Nothing duplicated: one attempt, one ledger row, one capture audit row.
    assert PaymentAttempt.objects.filter(payment__reference=reference).count() == 1
    assert PaymentTransaction.objects.filter(payment__reference=reference).count() == 1
    assert AuditLog.objects.filter(action='payment.captured').count() == 1


def test_money_actions_require_staff_and_owners_cannot_forge_them(client):
    body, _store, _variant = place_order(client)
    reference = body['payment']['reference']

    # The signed-in customer cannot confirm their own cash collection…
    forbidden = client.post(f'/api/v1/payments/{reference}/cod-collected')
    assert forbidden.status_code in (401, 403), forbidden.content
    # …nor refund themselves.
    forbidden_refund = client.post(
        f'/api/v1/payments/{reference}/refunds',
        {'amount': '10.00'}, content_type='application/json',
    )
    assert forbidden_refund.status_code in (401, 403), forbidden_refund.content
    assert Payment.objects.get(reference=reference).status == 'pending'


def test_cancelling_an_unpaid_order_voids_its_payment(client):
    body, _store, variant = place_order(client)
    reference = body['payment']['reference']

    response = client.post(f"/api/v1/orders/{body['number']}/cancel")
    assert response.status_code == 200, response.content

    payment = Payment.objects.get(reference=reference)
    assert payment.status == 'cancelled'
    assert Inventory.objects.get(variant=variant).reserved == 0
    assert AuditLog.objects.filter(action='payment.cancelled').exists()

    # A cancelled payment cannot be collected afterwards.
    login_as_staff(client)
    late = client.post(f'/api/v1/payments/{reference}/cod-collected')
    assert late.status_code == 400
    assert late.json()['error'] == 'not_payable'


def test_payment_records_are_private_to_the_order_owner(client):
    body, _store, _variant = place_order(client)
    reference = body['payment']['reference']

    mine = client.get(f'/api/v1/payments/{reference}/')
    assert mine.status_code == 200, mine.content
    assert mine.json()['order_number'] == body['number']
    assert mine.json()['refunds'] == []

    # A second signed-in customer must not see it (§4 IDOR).
    register(client, OTHER)
    login(client, OTHER['email'], OTHER['password'])
    theirs = client.get(f'/api/v1/payments/{reference}/')
    assert theirs.status_code == 404


# --- 9.2 online seam (sandbox) + 9.1 expiration handling ---

def test_online_payments_flow_through_the_adapter_seam_in_sandbox(client, settings):
    settings.PAYMENTS_GATEWAY_SANDBOX = True

    body, _store, _variant = place_order(client, method='gcash')
    payment = body['payment']
    assert body['status'] == 'awaiting_payment'
    assert payment['method'] == 'gcash'
    assert payment['provider'] == 'generic'
    assert payment['expires_at'] is not None  # the 24-hour window
    assert payment['checkout_url'].startswith('https://sandbox.payments.local/')

    record = Payment.objects.get(reference=payment['reference'])
    assert record.gateway_reference.startswith('sbx_')
    attempt = PaymentAttempt.objects.get(payment=record)
    assert attempt.status == 'pending'
    assert attempt.gateway_reference == record.gateway_reference


def test_expiry_command_releases_unpaid_online_orders(client, settings):
    settings.PAYMENTS_GATEWAY_SANDBOX = True

    body, _store, variant = place_order(client, method='card')
    reference = body['payment']['reference']

    # Time passes (or the job runs late): the window is over.
    Payment.objects.filter(reference=reference).update(
        expires_at=timezone.now() - timedelta(minutes=1)
    )
    call_command('expire_payments')

    payment = Payment.objects.get(reference=reference)
    assert payment.status == 'expired'
    assert payment.order.status == 'cancelled'
    assert Inventory.objects.get(variant=variant).reserved == 0
    assert AuditLog.objects.filter(action='payment.expired').exists()

    # A second run is a no-op — nothing left to expire.
    call_command('expire_payments')
    assert Payment.objects.get(reference=reference).status == 'expired'


# --- 9.4 Refund foundation: full, partial, status, ledger reversal ---

def test_full_refund_restores_stock_and_reverses_the_ledger(client):
    body, _store, variant = place_order(client, quantity=2)
    reference = body['payment']['reference']
    order = Order.objects.get(number=body['number'])

    login_as_staff(client)
    client.post(f'/api/v1/payments/{reference}/cod-collected')  # capture first

    response = client.post(
        f'/api/v1/payments/{reference}/refunds',
        {'amount': str(order.grand_total), 'reason': 'Item damaged'},
        content_type='application/json',
    )
    assert response.status_code == 201, response.content
    payload = response.json()
    assert payload['status'] == 'succeeded'
    assert payload['amount'] == float(order.grand_total)

    payment = Payment.objects.get(reference=reference)
    order.refresh_from_db()
    assert payment.status == 'refunded'
    assert order.status == 'refunded'
    assert payment.refunded_total == order.grand_total

    # A full refund returns the goods: stock comes back (restock movement).
    inventory = Inventory.objects.get(variant=variant)
    assert inventory.on_hand == 10
    assert inventory.reserved == 0
    assert StockMovement.objects.filter(
        variant=variant, reason=StockMovement.Reason.RESTOCK
    ).exists()

    # Ledger: capture (credit) + refund (debit) — the balance is the sum.
    assert payment.captured_total - payment.refunded_total == Decimal('0.00')
    assert payment.transactions.filter(direction='debit').count() == 1
    assert AuditLog.objects.filter(action='refund.settled').exists()


def test_partial_refunds_are_balance_checked(client):
    body, _store, _variant = place_order(client)
    reference = body['payment']['reference']
    login_as_staff(client)
    client.post(f'/api/v1/payments/{reference}/cod-collected')

    first = client.post(
        f'/api/v1/payments/{reference}/refunds',
        {'amount': '100.00', 'reason': 'Coupon promised'},
        content_type='application/json',
    )
    assert first.status_code == 201, first.content

    payment = Payment.objects.get(reference=reference)
    assert payment.status == 'partially_refunded'
    assert payment.order.status == 'paid'  # a partial refund keeps it live
    assert payment.refunded_total == Decimal('100.00')

    # The remaining balance is 249.00 — 300.00 must be refused, atomically.
    too_much = client.post(
        f'/api/v1/payments/{reference}/refunds',
        {'amount': '300.00'}, content_type='application/json',
    )
    assert too_much.status_code == 400
    assert too_much.json()['error'] == 'refund_exceeds_balance'
    payment.refresh_from_db()
    assert payment.refunded_total == Decimal('100.00')
    assert Refund.objects.filter(payment=payment).count() == 1


def test_refunds_are_impossible_before_capture_and_for_bad_amounts(client):
    body, _store, _variant = place_order(client)
    reference = body['payment']['reference']
    login_as_staff(client)

    early = client.post(
        f'/api/v1/payments/{reference}/refunds',
        {'amount': '10.00'}, content_type='application/json',
    )
    assert early.status_code == 400
    assert early.json()['error'] == 'not_refundable'

    client.post(f'/api/v1/payments/{reference}/cod-collected')
    zero = client.post(
        f'/api/v1/payments/{reference}/refunds',
        {'amount': '0'}, content_type='application/json',
    )
    assert zero.status_code == 400
    negative = client.post(
        f'/api/v1/payments/{reference}/refunds',
        {'amount': '-5.00'}, content_type='application/json',
    )
    assert negative.status_code == 400
    assert Payment.objects.get(reference=reference).refunded_total == Decimal('0.00')
