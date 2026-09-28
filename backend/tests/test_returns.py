"""Phase 17 gate tests — returns, restocking and the window (ROADMAP §17.1).

The §17 Gate drives these, slice by slice:
1. An eligible return can be requested — delivery + window are server
   verdicts, the case snapshots the window and the refund due, and filing
   writes a timeline event plus an audit row.
2. A seller can process the return — approval, the reverse parcel, and
   receipt restock the *ordered* lines through the append-only stock ledger
   (idempotent per line, opt-out per line for unsellable goods), while the
   linked Phase 11 intake row is resolved.
3. Admin intervention — whole-order cases are staff-only, and a staff ruling
   on a seller's decision is recorded as an override.
4. Unauthorized users cannot touch disputes/returns — owner-, store- and
   group-scoped at the query level (404/403, never a leak).
5. Refund maths stay server-side — discounts are allocated to the lines that
   enjoyed them and shipping comes back only on a fully returned slice; the
   ledger itself does not move in this slice (§17.2 owns the payout).
6. Disputes are auditable (§17.3) — creation, statements/evidence with
   server-derived parties, staff review and a reasoned ruling, every step on
   the timeline and in the AuditLog; unauthorized users cannot alter them
   (403/404, nothing written).
"""
from datetime import timedelta
from decimal import Decimal
import hashlib
import hmac
import json

import pytest
from django.contrib.auth.models import Group
from django.test import Client
from django.utils import timezone

from apps.accounts.models import Address, User
from apps.audit.models import AuditLog
from apps.cart.models import Cart
from apps.catalog import services as catalog_services
from apps.catalog.models import Inventory, Product, StockMovement, Variant
from apps.notifications.models import Notification
from apps.orders import services as order_services
from apps.orders.models import (
    Order,
    OrderRequest,
    OrderStatus,
    RequestKind,
    ShipmentStatus,
)
from apps.payments import services as payment_services
from apps.payments.adapters.gateway import GenericGatewayAdapter
from apps.payments.models import PaymentTransaction, Refund, RefundStatus
from apps.resolutions import policies, services as resolution_services
from apps.resolutions.models import Dispute, ReturnCase, ReturnStatus
from apps.stores.models import Store

pytestmark = pytest.mark.django_db

PASSWORD = 'Str0ng!Passw0rd'
REGISTER = '/api/v1/auth/register'
LOGIN = '/api/v1/auth/login'
ADDRESSES = '/api/v1/auth/addresses/'
CART_ITEMS = '/api/v1/cart/items'
CHECKOUT_ORDERS = '/api/v1/checkout/orders'
ORDERS = '/api/v1/orders/'
RETURNS = '/api/v1/returns/'
ADMIN_RETURNS = '/api/v1/admin/returns/'
DISPUTES = '/api/v1/disputes/'
SELLER_DISPUTES = '/api/v1/seller/disputes/'
ADMIN_DISPUTES = '/api/v1/admin/disputes/'

BUYER = {'email': 'returnbuyer@example.com', 'password': PASSWORD}
OTHER_BUYER = {'email': 'returnother@example.com', 'password': PASSWORD}

ADDRESS_PAYLOAD = {
    'full_name': 'Rina Returner',
    'phone': '09175551234',
    'line1': '8 Rizal Avenue',
    'line2': '',
    'city': 'Cebu City',
    'province': 'Cebu',
    'postal_code': '6000',
}


def _register(client, payload):
    response = client.post(REGISTER, payload, content_type='application/json')
    assert response.status_code == 201, response.content
    response = client.post(
        LOGIN, payload, content_type='application/json'
    )
    assert response.status_code == 200, response.content
    return User.objects.get(email=payload['email'])


def _store(email, *, name='Return Store', slug='return-store', fee='50.00'):
    user = User.objects.create_user(email=email, password=PASSWORD)
    user.is_seller = True
    user.save(update_fields=['is_seller'])
    store = Store.objects.create(
        user=user,
        name=name,
        slug=slug,
        status=Store.Status.ACTIVE,
        shipping_flat_fee=Decimal(fee),
    )
    return user, store


def _product(store, *, title='Return Product', price='299.00', stock=10):
    product = Product.objects.create(
        store=store,
        title=title,
        base_price=Decimal(price),
        status=Product.Status.PUBLISHED,
    )
    variant = Variant.objects.create(
        product=product, name='Default', price=Decimal(price), is_default=True
    )
    catalog_services.ensure_inventory(variant, initial_on_hand=stock)
    return product, variant


def _deliver_multi(buyer, variants, quantities=None):
    """Places one order across several stores and delivers every slice (§10)."""
    quantities = quantities or [1] * len(variants)
    address = Address.objects.create(
        user=buyer, full_name='Rina Returner', phone='09175551234',
        line1='8 Rizal Avenue', city='Cebu City', province='Cebu', postal_code='6000',
    )
    cart = Cart.objects.create(user=buyer)
    for variant, quantity in zip(variants, quantities):
        cart.items.create(variant=variant, quantity=quantity)
    order = order_services.create_order(buyer, address.id, payment_method='cod')
    for seller_order in order.seller_orders.all():
        seller = seller_order.store.user
        order_services.mark_seller_order_processing(seller_order, actor=seller)
        order_services.mark_seller_order_packed(seller_order, actor=seller)
        shipment = order_services.create_shipment(
            seller_order, carrier_code='manual', package_notes='Return fixture',
            package_weight_grams=400, actor=seller,
        )
        order_services.update_shipment_status(
            shipment, ShipmentStatus.DELIVERED, actor=seller
        )
    order.refresh_from_db()
    assert order.seller_orders.count() == len(variants)
    return order


def _deliver(buyer, variant, quantity=1, payment_method='cod'):
    """Runs the real COD flow until the parcel is delivered (§10)."""
    address = Address.objects.create(
        user=buyer,
        full_name='Rina Returner',
        phone='09175551234',
        line1='8 Rizal Avenue',
        city='Cebu City',
        province='Cebu',
        postal_code='6000',
    )
    cart = Cart.objects.create(user=buyer)
    cart.items.create(variant=variant, quantity=quantity)
    order = order_services.create_order(
        buyer, address.id, payment_method=payment_method
    )

    seller = variant.product.store.user
    seller_order = order.seller_orders.first()
    order_services.mark_seller_order_processing(seller_order, actor=seller)
    order_services.mark_seller_order_packed(seller_order, actor=seller)
    shipment = order_services.create_shipment(
        seller_order, carrier_code='manual', package_notes='Return fixture',
        package_weight_grams=400, actor=seller,
    )
    order_services.update_shipment_status(
        shipment, ShipmentStatus.DELIVERED, actor=seller
    )
    order.refresh_from_db()
    assert order.status == OrderStatus.DELIVERED
    return order, shipment


def _lines(order):
    """[{order_item_id, quantity}] for the first slice, fully."""
    item = order.seller_orders.first().items.first()
    return [{'order_item_id': item.id, 'quantity': item.quantity}]


def _client_for(user):
    client = Client()
    client.force_login(user)
    return client


def _staff(email, group='support'):
    user = User.objects.create_user(
        email=email, password=PASSWORD, first_name='Staff', last_name='Member',
        is_staff=True,
    )
    user.groups.add(Group.objects.get_or_create(name=group)[0])
    return user


# --- 17.1: eligibility & window ------------------------------------------------

def test_eligibility_is_a_server_verdict_with_returnable_lines(client):
    _seller, store = _store('eligseller@example.com')
    product, variant = _product(store)
    buyer = _register(client, BUYER)
    order, _shipment = _deliver(buyer, variant, quantity=3)

    response = client.get(f'{ORDERS}{order.number}/return-eligibility')
    assert response.status_code == 200, response.content
    body = response.json()
    assert body['eligible'] is True
    assert body['code'] == ''
    assert body['window_days'] == 7
    assert body['days_left'] == 7
    assert body['delivered_at'] and body['window_expires_at']
    assert len(body['lines']) == 1
    line = body['lines'][0]
    assert line['quantity'] == 3
    assert line['claimed'] == 0
    assert line['remaining'] == 3

    # Owner-scoped: another buyer can never read this verdict.
    other = _client_for(_register(Client(), OTHER_BUYER))
    assert other.get(f'{ORDERS}{order.number}/return-eligibility').status_code == 404


def test_return_window_blocks_a_late_request(client):
    _seller, store = _store('lateseller@example.com')
    product, variant = _product(store)
    buyer = _register(client, BUYER)
    order, shipment = _deliver(buyer, variant)

    shipment.delivered_at = timezone.now() - timedelta(days=8)
    shipment.save(update_fields=['delivered_at'])

    verdict = client.get(f'{ORDERS}{order.number}/return-eligibility')
    body = verdict.json()
    assert body['eligible'] is False
    assert body['code'] == 'window_expired'
    assert body['lines'] == []

    response = client.post(
        f'{ORDERS}{order.number}/returns',
        {'reason': 'damaged', 'lines': _lines(order)},
        content_type='application/json',
    )
    assert response.status_code == 400
    assert response.json()['error'] == 'window_expired'


def test_filing_a_return_snapshots_window_and_refund_and_audits(client):
    _seller, store = _store('filedseller@example.com')
    product, variant = _product(store, price='299.00')
    buyer = _register(client, BUYER)
    order, shipment = _deliver(buyer, variant, quantity=2)

    # The Phase 11 intake row this case will answer (§11.3 → §17.1).
    intake = client.post(
        f'{ORDERS}{order.number}/requests',
        {'kind': RequestKind.RETURN, 'reason': 'Damaged box'},
        content_type='application/json',
    )
    assert intake.status_code == 201, intake.content
    intake_id = intake.json()['id']

    response = client.post(
        f'{ORDERS}{order.number}/returns',
        {
            'reason': 'damaged',
            'note': 'Both mugs arrived cracked.',
            'request_id': intake_id,
            'lines': _lines(order),
        },
        content_type='application/json',
    )
    assert response.status_code == 201, response.content
    body = response.json()

    case = ReturnCase.objects.get(reference=body['reference'])
    assert case.status == ReturnStatus.REQUESTED
    assert case.seller_order.store == store
    assert case.delivered_at is not None
    assert case.window_expires_at is not None
    # 2 × 299 lines + 50 shipping (the whole slice is returning).
    assert Decimal(body['refund_due']) == Decimal('648.00')
    assert case.refund_due == Decimal('648.00')
    # Damaged goods do not go back on the shelf by default (§17.1).
    assert case.items.first().restock is False
    assert case.request_id == intake_id
    assert body['events'][0]['kind'] == 'created'

    assert AuditLog.objects.filter(action='return.requested').exists()
    assert Notification.objects.filter(
        recipient=store.user, category='orders'
    ).exists()

    # Intake stays pending until the case is decided — it is answered, not gone.
    intake_row = OrderRequest.objects.get(pk=intake_id)
    assert intake_row.status == 'pending'
    assert intake_row.return_cases.count() == 1


def test_quantity_caps_and_open_duplicates_are_refused(client):
    _seller, store = _store('capseller@example.com')
    product, variant = _product(store, stock=10)
    buyer = _register(client, BUYER)
    order, _shipment = _deliver(buyer, variant, quantity=2)
    item = order.seller_orders.first().items.first()

    too_many = client.post(
        f'{ORDERS}{order.number}/returns',
        {'reason': 'changed_mind', 'lines': [{'order_item_id': item.id, 'quantity': 3}]},
        content_type='application/json',
    )
    assert too_many.status_code == 400
    assert too_many.json()['error'] == 'quantity_exceeded'

    created = client.post(
        f'{ORDERS}{order.number}/returns',
        {'reason': 'changed_mind', 'lines': _lines(order)},
        content_type='application/json',
    )
    assert created.status_code == 201, created.content

    duplicate = client.post(
        f'{ORDERS}{order.number}/returns',
        {'reason': 'changed_mind', 'lines': _lines(order)},
        content_type='application/json',
    )
    assert duplicate.status_code == 400
    assert duplicate.json()['error'] in ('case_exists', 'quantity_exceeded')


# --- 17.1: seller processing, restocking, staff intervention -------------------

def _file_return(client, order, **extra):
    payload = {'reason': 'changed_mind', 'lines': _lines(order), **extra}
    response = client.post(
        f'{ORDERS}{order.number}/returns', payload, content_type='application/json'
    )
    assert response.status_code == 201, response.content
    return response.json()


def test_seller_processes_return_end_to_end_and_restocks(client):
    _seller_user, store = _store('processeller@example.com')
    product, variant = _product(store, price='299.00', stock=10)
    buyer = _register(client, BUYER)
    order, _shipment = _deliver(buyer, variant, quantity=2)

    # Delivery committed the sale: 10 on hand − 2 sold = 8.
    inventory = Inventory.objects.get(variant=variant)
    assert inventory.on_hand == 8

    reference = _file_return(client, order)['reference']
    seller = _client_for(store.user)

    approved = seller.post(
        f'/api/v1/seller/returns/{reference}/respond',
        {'decision': 'approve', 'note': 'Please use the return slip.'},
        content_type='application/json',
    )
    assert approved.status_code == 200, approved.content
    assert approved.json()['status'] == 'approved'
    assert approved.json()['responded_at']
    assert Notification.objects.filter(
        recipient=buyer, title='Return approved'
    ).exists()

    booked = seller.post(
        f'/api/v1/seller/returns/{reference}/shipment',
        {}, content_type='application/json',
    )
    assert booked.status_code == 200, booked.content
    booking = booked.json()
    assert booking['tracking_number'].startswith('JVRTN-')
    assert booking['status'] == 'in_transit'

    received = seller.post(
        f'/api/v1/seller/returns/{reference}/receive',
        {}, content_type='application/json',
    )
    assert received.status_code == 200, received.content
    body = received.json()
    # Goods are back and stock moved; the payout is the §17.2 slice.
    assert body['status'] == 'refund_pending'
    assert Decimal(body['refund_due']) == Decimal('648.00')

    inventory.refresh_from_db()
    assert inventory.on_hand == 10
    movements = StockMovement.objects.filter(
        variant=variant, reason=StockMovement.Reason.RESTOCK
    )
    assert movements.count() == 1
    assert movements.first().note == f'return {reference}'
    assert body['shipment']['received_at']
    assert [event['kind'] for event in body['events']] == [
        'created', 'approved', 'shipped', 'received', 'restocked',
    ]

    # No money moves in slice v1: the ledger stays the payment's own truth.
    assert Refund.objects.count() == 0
    assert order.payment.refunded_total == Decimal('0.00')
    assert AuditLog.objects.filter(action='return.received').exists()


def test_receipt_is_idempotent_and_honours_the_restock_opt_out(client):
    _seller_user, store = _store('optoutseller@example.com')
    product, variant = _product(store, stock=10)
    buyer = _register(client, BUYER)
    order, _shipment = _deliver(buyer, variant, quantity=1)
    inventory = Inventory.objects.get(variant=variant)
    assert inventory.on_hand == 9

    # 'damaged' defaults the line to written-off: receipt must not restock it.
    response = client.post(
        f'{ORDERS}{order.number}/returns',
        {'reason': 'damaged', 'lines': _lines(order)},
        content_type='application/json',
    )
    assert response.status_code == 201, response.content
    reference = response.json()['reference']
    seller = _client_for(store.user)

    seller.post(
        f'/api/v1/seller/returns/{reference}/respond',
        {'decision': 'approve'}, content_type='application/json',
    )
    received = seller.post(
        f'/api/v1/seller/returns/{reference}/receive',
        {}, content_type='application/json',
    )
    assert received.status_code == 200, received.content
    inventory.refresh_from_db()
    assert inventory.on_hand == 9  # unchanged — no restock movement
    assert not StockMovement.objects.filter(
        variant=variant, reason=StockMovement.Reason.RESTOCK
    ).exists()
    line = ReturnCase.objects.get(reference=reference).items.first()
    assert line.restocked_at is not None

    # Receipt is a one-way transition: no double-processing.
    again = seller.post(
        f'/api/v1/seller/returns/{reference}/receive',
        {}, content_type='application/json',
    )
    assert again.status_code == 400
    assert again.json()['error'] == 'not_receivable'


def test_customer_can_cancel_an_undecided_return_and_units_free_up(client):
    _seller_user, store = _store('cancelseller@example.com')
    product, variant = _product(store, stock=10)
    buyer = _register(client, BUYER)
    order, _shipment = _deliver(buyer, variant, quantity=2)

    reference = _file_return(client, order)['reference']
    cancelled = client.post(
        f'{RETURNS}{reference}/cancel',
        {'note': 'Found a fix at home.'},
        content_type='application/json',
    )
    assert cancelled.status_code == 200, cancelled.content
    assert cancelled.json()['status'] == 'cancelled'
    assert cancelled.json()['events'][-1]['kind'] == 'cancelled'
    assert Notification.objects.filter(
        recipient=store.user, title='Return cancelled'
    ).exists()
    assert AuditLog.objects.filter(action='return.cancelled').exists()

    # The units are free again: a fresh case may claim them.
    refilled = client.post(
        f'{ORDERS}{order.number}/returns',
        {'reason': 'changed_mind', 'lines': _lines(order)},
        content_type='application/json',
    )
    assert refilled.status_code == 201, refilled.content

    # A cancelled case cannot be cancelled a second time.
    again = client.post(
        f'{RETURNS}{reference}/cancel', {}, content_type='application/json'
    )
    assert again.status_code == 400
    assert again.json()['error'] == 'not_cancellable'


def test_rejection_resolves_the_intake_and_staff_can_override(client):
    _seller_user, store = _store('overrideseller@example.com')
    product, variant = _product(store)
    buyer = _register(client, BUYER)
    order, _shipment = _deliver(buyer, variant)

    intake = client.post(
        f'{ORDERS}{order.number}/requests',
        {'kind': RequestKind.RETURN, 'reason': 'Wrong colour delivered'},
        content_type='application/json',
    )
    assert intake.status_code == 201, intake.content
    reference = _file_return(
        client, order, request_id=intake.json()['id']
    )['reference']

    seller = _client_for(store.user)
    rejected = seller.post(
        f'/api/v1/seller/returns/{reference}/respond',
        {'decision': 'reject', 'reason': 'Outside our policy.'},
        content_type='application/json',
    )
    assert rejected.status_code == 200, rejected.content
    assert rejected.json()['status'] == 'rejected'
    # The Phase 11 intake row this case answered is now decided (§11.3).
    assert OrderRequest.objects.get(pk=intake.json()['id']).status == 'resolved'

    staff_user = _staff('returnsupport@example.com')
    support = _client_for(staff_user)
    decided = support.post(
        f'{ADMIN_RETURNS}{reference}/decide',
        {'decision': 'approve', 'reason': 'Goodwill for a repeat customer.'},
        content_type='application/json',
    )
    assert decided.status_code == 200, decided.content
    body = decided.json()
    assert body['status'] == 'approved'
    assert body['admin_override_reason'] == 'Goodwill for a repeat customer.'

    case = ReturnCase.objects.get(reference=reference)
    assert case.admin_override_by == staff_user
    assert case.responded_by == store.user  # the original ruling stays on record
    assert case.events.filter(kind='admin_override').exists()
    assert AuditLog.objects.filter(action='return.admin_decision').exists()


def test_returns_are_owner_store_and_group_scoped(client):
    _sa, store_a = _store('scopellera@example.com', name='Scope A', slug='scope-a')
    _sb, store_b = _store(
        'scopellerb@example.com', name='Scope B', slug='scope-b', fee='0.00'
    )
    _pa, variant_a = _product(store_a, price='299.00')
    _pb, variant_b = _product(store_b, title='Scope B Product', price='100.00')
    buyer = _register(client, BUYER)
    order = _deliver_multi(buyer, [variant_a, variant_b])

    # Whole-order case (both stores returning) — only staff adjudicate it.
    reference = _file_return(client, order)['reference']
    case = ReturnCase.objects.get(reference=reference)
    assert case.seller_order_id is None

    seller_a = _client_for(store_a.user)
    desk = seller_a.get('/api/v1/seller/returns/')
    assert desk.status_code == 200
    assert desk.json()['count'] == 0  # a whole-order case is not theirs
    assert seller_a.get(f'/api/v1/seller/returns/{reference}/').status_code == 404
    refused = seller_a.post(
        f'/api/v1/seller/returns/{reference}/respond',
        {'decision': 'approve'}, content_type='application/json',
    )
    assert refused.status_code == 404

    support = _client_for(_staff('scopestaff@example.com'))
    listed = support.get(ADMIN_RETURNS)
    assert listed.status_code == 200
    assert listed.json()['count'] == 1
    decided = support.post(
        f'{ADMIN_RETURNS}{reference}/decide',
        {'decision': 'approve'}, content_type='application/json',
    )
    assert decided.status_code == 200, decided.content

    # The staff queue is group-gated; another customer cannot read the case;
    # a buyer without a store cannot touch the seller desk.
    assert client.get(ADMIN_RETURNS).status_code == 403
    other = _client_for(_register(Client(), OTHER_BUYER))
    assert other.get(f'{RETURNS}{reference}/').status_code == 404
    assert client.post(
        f'/api/v1/seller/returns/{reference}/respond',
        {'decision': 'approve'}, content_type='application/json',
    ).status_code == 403


def test_refund_calculation_allocates_discounts_and_shipping(client):
    _sa, store_a = _store('mathsellera@example.com', name='Math A', slug='math-a')
    _sb, store_b = _store(
        'mathsellerb@example.com', name='Math B', slug='math-b', fee='0.00'
    )
    _pa, variant_a = _product(store_a, price='299.00')
    _pb, variant_b = _product(store_b, title='Math B Product', price='100.00')
    buyer = _register(client, BUYER)
    order = _deliver_multi(buyer, [variant_a, variant_b])

    order.promotion_discount = Decimal('30.00')
    order.save(update_fields=['promotion_discount', 'updated_at'])
    item_a = order.seller_orders.get(store=store_a).items.first()
    item_b = order.seller_orders.get(store=store_b).items.first()

    partial = resolution_services.calculate_refund_due(order, [(item_a, 1)])
    # 299 − its 22.48 share of the order-level promo + the 50 shipping fee,
    # because the whole store-A slice is coming back.
    assert partial == Decimal('326.52')

    everything = resolution_services.calculate_refund_due(
        order, [(item_a, 1), (item_b, 1)]
    )
    # Every line back: 399 − the 30 promo + 50 shipping (store B ships free).
    assert everything == Decimal('419.00')

    allocation = policies.allocate_discount(
        [Decimal('299.00'), Decimal('100.00')], Decimal('30.00')
    )
    assert sum(allocation) == Decimal('30.00')  # no cent invented or lost
    assert policies.refundable_amount(
        Decimal('100.00'), Decimal('120.00')
    ) == Decimal('0.00')  # a fully-discounted line refunds nothing


# --- 17.2: refund adjudication and money movement -------------------------------

WEBHOOK = '/api/v1/payments/webhooks/generic/'
WEBHOOK_SECRET = 'returns-webhook-secret'


def _received_case(client, buyer, store, variant, *, quantity=1, method='cod'):
    """A return the seller approved and has received — the payable state."""
    order, _shipment = _deliver(buyer, variant, quantity=quantity, payment_method=method)
    reference = _file_return(client, order)['reference']
    seller = _client_for(store.user)
    assert seller.post(
        f'/api/v1/seller/returns/{reference}/respond',
        {'decision': 'approve'}, content_type='application/json',
    ).status_code == 200
    assert seller.post(
        f'/api/v1/seller/returns/{reference}/receive',
        {}, content_type='application/json',
    ).status_code == 200
    if method != 'cod':
        # The gateway captured it; COD would have captured at delivery.
        payment_services.mark_paid(
            order.payment, source='webhook', gateway_reference='gw_paid_case_1'
        )
        order.refresh_from_db()
    return order, reference


def test_staff_payout_settles_the_ledger_and_never_double_restocks(client):
    _seller_user, store = _store('payoutseller@example.com')
    product, variant = _product(store, price='299.00', stock=10)
    buyer = _register(client, BUYER)
    order, reference = _received_case(client, buyer, store, variant, quantity=2)

    # Receipt already put the 2 returned units back: 10 - 2 sold + 2 back.
    inventory = Inventory.objects.get(variant=variant)
    assert inventory.on_hand == 10
    case = ReturnCase.objects.get(reference=reference)
    assert case.status == ReturnStatus.REFUND_PENDING
    assert case.refund_due == Decimal('648.00')  # 2 × 299 + 50 shipping

    finance = _client_for(_staff('payoutfinance@example.com', group='finance'))
    paid = finance.post(
        f'{ADMIN_RETURNS}{reference}/refund', {}, content_type='application/json'
    )
    assert paid.status_code == 201, paid.content
    assert paid.json()['amount'] == '648.00'
    assert paid.json()['status'] == 'succeeded'  # COD settles immediately

    case.refresh_from_db()
    assert case.status == ReturnStatus.REFUNDED
    order.payment.refresh_from_db()
    assert order.payment.status == 'refunded'
    order.refresh_from_db()
    assert order.status == OrderStatus.REFUNDED
    assert PaymentTransaction.objects.filter(
        payment=order.payment, kind='refund', direction='debit'
    ).count() == 1

    # The case owns the restock story: the payout must not restock again.
    inventory.refresh_from_db()
    assert inventory.on_hand == 10
    movements = StockMovement.objects.filter(
        variant=variant, reason=StockMovement.Reason.RESTOCK
    )
    assert movements.count() == 1
    assert movements.first().note == f'return {reference}'

    # The case owes nothing more, so a second payout is refused.
    again = finance.post(
        f'{ADMIN_RETURNS}{reference}/refund', {}, content_type='application/json'
    )
    assert again.status_code == 400
    assert again.json()['error'] == 'already_refunded'
    assert AuditLog.objects.filter(action='return.refunded').exists()


def test_partial_payouts_settle_the_case_and_only_finance_may_pay(client):
    _seller_user, store = _store('partialseller@example.com')
    product, variant = _product(store, price='299.00', stock=10)
    buyer = _register(client, BUYER)
    order, reference = _received_case(client, buyer, store, variant, quantity=2)

    # Support adjudicates returns, but money is finance/administrator (§4).
    support = _client_for(_staff('payoutsupport@example.com', group='support'))
    refused = support.post(
        f'{ADMIN_RETURNS}{reference}/refund', {}, content_type='application/json'
    )
    assert refused.status_code == 403

    finance_user = _staff('partialfinance@example.com', group='finance')
    finance = _client_for(finance_user)
    first = finance.post(
        f'{ADMIN_RETURNS}{reference}/refund',
        {'amount': '500.00', 'reason': 'Goodwill on the second mug.'},
        content_type='application/json',
    )
    assert first.status_code == 201, first.content
    assert first.json()['amount'] == '500.00'

    case = ReturnCase.objects.get(reference=reference)
    assert case.status == ReturnStatus.REFUND_PENDING  # not settled in full yet
    order.payment.refresh_from_db()
    assert order.payment.status == 'partially_refunded'

    detail = client.get(f'{RETURNS}{reference}/').json()
    assert detail['refunded_total'] == '500.00'
    assert detail['refund_remaining'] == '148.00'
    assert detail['refunds'][0]['actor'] == 'partialfinance@example.com'
    assert detail['refunds'][0]['reason'] == 'Goodwill on the second mug.'

    # Over the case balance is refused by the case itself, not the ledger.
    over = finance.post(
        f'{ADMIN_RETURNS}{reference}/refund',
        {'amount': '500.00'}, content_type='application/json',
    )
    assert over.status_code == 400
    assert over.json()['error'] == 'refund_exceeds_case'

    # The remainder pays the case off.
    rest = finance.post(
        f'{ADMIN_RETURNS}{reference}/refund', {}, content_type='application/json'
    )
    assert rest.status_code == 201, rest.content
    assert rest.json()['amount'] == '148.00'

    case.refresh_from_db()
    assert case.status == ReturnStatus.REFUNDED
    assert Refund.objects.filter(return_case=case).count() == 2
    order.payment.refresh_from_db()
    assert order.payment.status == 'refunded'


def test_a_gateway_payout_waits_for_its_webhook_before_the_case_settles(
    client, settings, monkeypatch
):
    settings.PAYMENTS_GATEWAY_SANDBOX = True
    settings.PAYMENTS_GATEWAY_WEBHOOK_SECRET = WEBHOOK_SECRET

    _seller_user, store = _store('gatewayseller@example.com')
    product, variant = _product(store, price='299.00', stock=10)
    buyer = _register(client, BUYER)
    order, reference = _received_case(
        client, buyer, store, variant, quantity=1, method='card'
    )

    # A hosted gateway answers "accepted, pending" — the ledger is not written
    # until its signed webhook confirms (§9.3, §17.2).
    monkeypatch.setattr(
        GenericGatewayAdapter,
        'refund',
        lambda self, refund: {
            'status': RefundStatus.PENDING, 'gateway_reference': 'gw_case_1',
        },
    )
    finance = _client_for(_staff('gatewayfinance@example.com', group='finance'))
    issued = finance.post(
        f'{ADMIN_RETURNS}{reference}/refund', {}, content_type='application/json'
    )
    assert issued.status_code == 201, issued.content
    assert issued.json()['status'] == 'pending'
    assert issued.json()['gateway_reference'] == 'gw_case_1'

    case = ReturnCase.objects.get(reference=reference)
    assert case.status == ReturnStatus.REFUND_PENDING  # the money has not moved
    assert resolution_services.refund_remaining(case) == Decimal('0.00')
    order.payment.refresh_from_db()
    assert order.payment.status == 'paid'
    assert not PaymentTransaction.objects.filter(
        payment=order.payment, kind='refund'
    ).exists()

    # A second payout cannot double-pay while the first is still in flight.
    twice = finance.post(
        f'{ADMIN_RETURNS}{reference}/refund', {}, content_type='application/json'
    )
    assert twice.status_code == 400
    assert twice.json()['error'] == 'already_refunded'

    # The signed confirmation settles the refund, and the case follows it.
    body = json.dumps({
        'id': 'evt_case_refund_ok',
        'type': 'refund.succeeded',
        'data': {'reference': 'gw_case_1', 'amount': '349.00'},
    }).encode()
    signature = hmac.new(
        WEBHOOK_SECRET.encode(), body, hashlib.sha256
    ).hexdigest()
    delivered = client.post(
        WEBHOOK, data=body, content_type='application/json',
        HTTP_X_PAYMENTS_SIGNATURE=signature,
    )
    assert delivered.status_code == 200, delivered.content
    assert delivered.json()['status'] == 'processed'

    case.refresh_from_db()
    assert case.status == ReturnStatus.REFUNDED
    order.payment.refresh_from_db()
    assert order.payment.status == 'refunded'
    assert Notification.objects.filter(
        recipient=buyer, title='Refund completed'
    ).exists()


def test_an_unconfigured_gateway_refuses_the_payout_and_rolls_it_back(
    client, settings
):
    # Online checkout needs sandbox to create the order fixture...
    settings.PAYMENTS_GATEWAY_SANDBOX = True

    _seller_user, store = _store('unconfiguredseller@example.com')
    product, variant = _product(store, price='299.00', stock=10)
    buyer = _register(client, BUYER)
    order, reference = _received_case(
        client, buyer, store, variant, quantity=1, method='card'
    )

    # ...then we turn off the gateway so the refund payout cannot proceed.
    settings.PAYMENTS_GATEWAY_SANDBOX = False
    settings.PAYMENTS_GATEWAY_CHECKOUT_URL = ''

    finance = _client_for(
        _staff('unconfiguredfinance@example.com', group='finance')
    )
    refused = finance.post(
        f'{ADMIN_RETURNS}{reference}/refund', {}, content_type='application/json'
    )
    assert refused.status_code == 400
    assert refused.json()['error'] == 'gateway_not_configured'

    # Nothing was written: no refund row, no "issued" event, money unmoved.
    assert Refund.objects.count() == 0
    case = ReturnCase.objects.get(reference=reference)
    assert case.status == ReturnStatus.REFUND_PENDING
    assert not case.events.filter(kind='refund_issued').exists()
    order.payment.refresh_from_db()
    assert order.payment.status == 'paid'


# --- 17.3: disputes — buyer escalation, statements, staff ruling --------------


def test_dispute_creation_is_owner_scoped_and_audited(client):
    _seller, store = _store('disputeseller@example.com')
    product, variant = _product(store, price='299.00')
    buyer = _register(client, BUYER)
    order, _shipment = _deliver(buyer, variant)

    # The buyer escalates their undecided return and links the intake (§17.3).
    ret = _file_return(client, order)
    intake = client.post(
        f'{ORDERS}{order.number}/requests',
        {'kind': RequestKind.ISSUE, 'reason': 'Never arrived'},
        content_type='application/json',
    )
    assert intake.status_code == 201, intake.content

    created = client.post(
        f'{ORDERS}{order.number}/disputes',
        {
            'reason': 'return_rejected',
            'statement': 'The return was ignored and nobody answers me.',
            'request_id': intake.json()['id'],
            'return_reference': ret['reference'],
        },
        content_type='application/json',
    )
    assert created.status_code == 201, created.content
    body = created.json()
    assert body['reference'].startswith('JVDSP-')
    assert body['status'] == 'open'
    assert body['scope'] == 'store'
    assert body['return_reference'] == ret['reference']
    assert body['events'][0]['kind'] == 'created'
    assert body['statements'] == [] and body['evidence'] == []

    dispute = Dispute.objects.get(reference=body['reference'])
    assert dispute.request_id == intake.json()['id']
    assert dispute.return_case_id is not None
    assert AuditLog.objects.filter(action='dispute.created').exists()
    assert Notification.objects.filter(
        recipient=store.user, category='orders'
    ).exists()

    # One open dispute per slice — a second submit is refused.
    duplicate = client.post(
        f'{ORDERS}{order.number}/disputes',
        {'reason': 'other', 'statement': 'One more.'},
        content_type='application/json',
    )
    assert duplicate.status_code == 400
    assert duplicate.json()['error'] == 'dispute_exists'

    # Another buyer cannot open on — or even read — this order's disputes.
    outsider = _client_for(_register(Client(), OTHER_BUYER))
    denied = outsider.post(
        f'{ORDERS}{order.number}/disputes',
        {'reason': 'other', 'statement': 'Let me in.'},
        content_type='application/json',
    )
    assert denied.status_code == 404
    assert outsider.get(f'{DISPUTES}{body["reference"]}/').status_code == 404


def test_dispute_evidence_and_statements_stay_party_scoped(client):
    _seller, store = _store('disputeresponder@example.com')
    product, variant = _product(store, price='299.00')
    _other_seller, other_store = _store(
        'othershopowner@example.com', name='Other Shop', slug='other-shop'
    )
    buyer = _register(client, BUYER)
    order, _shipment = _deliver(buyer, variant)

    created = client.post(
        f'{ORDERS}{order.number}/disputes',
        {'reason': 'damaged_in_transit', 'statement': 'The box was crushed.'},
        content_type='application/json',
    )
    assert created.status_code == 201, created.content
    reference = created.json()['reference']

    # Statement and evidence land with party=customer — the client never
    # chooses the party (§17.3).
    stmt = client.post(
        f'{DISPUTES}{reference}/statements',
        {'body': 'The mug handle snapped off.'},
        content_type='application/json',
    )
    assert stmt.status_code == 200, stmt.content
    ev = client.post(
        f'{DISPUTES}{reference}/evidence',
        {'url': 'https://cdn.example.com/unboxing.jpg',
         'caption': 'Unboxing photo'},
        content_type='application/json',
    )
    assert ev.status_code == 200, ev.content

    # The store answers with its own statement plus evidence in one call.
    seller = _client_for(store.user)
    resp = seller.post(
        f'{SELLER_DISPUTES}{reference}/respond',
        {
            'statement': 'Parcel was scanned at 2kg on handover.',
            'evidence': ['https://cdn.example.com/handover-slip.png'],
        },
        content_type='application/json',
    )
    assert resp.status_code == 200, resp.content
    detail = resp.json()
    assert {row['party'] for row in detail['statements']} == {'customer', 'seller'}
    assert detail['evidence'][0]['party'] == 'customer'
    assert detail['evidence'][1]['party'] == 'seller'
    assert detail['status'] == 'open'  # only staff move the status (§17.3)

    # Another store can neither read nor answer this dispute.
    stranger = _client_for(other_store.user)
    assert stranger.get(f'{SELLER_DISPUTES}{reference}/').status_code == 404
    refused = stranger.post(
        f'{SELLER_DISPUTES}{reference}/respond',
        {'statement': 'Not ours.'},
        content_type='application/json',
    )
    assert refused.status_code == 404

    # An empty statement is refused server-side.
    blank = client.post(
        f'{DISPUTES}{reference}/statements', {'body': ''},
        content_type='application/json',
    )
    assert blank.status_code == 400


def test_staff_review_and_ruling_close_the_dispute(client):
    _seller, store = _store('disputeruling@example.com')
    product, variant = _product(store, price='299.00')
    buyer = _register(client, BUYER)
    order, _shipment = _deliver(buyer, variant)

    intake = client.post(
        f'{ORDERS}{order.number}/requests',
        {'kind': RequestKind.ISSUE, 'reason': 'Missing parcel'},
        content_type='application/json',
    )
    assert intake.status_code == 201, intake.content
    created = client.post(
        f'{ORDERS}{order.number}/disputes',
        {
            'reason': 'item_not_received',
            'statement': 'Tracking says delivered; nothing arrived.',
            'request_id': intake.json()['id'],
        },
        content_type='application/json',
    )
    assert created.status_code == 201, created.content
    reference = created.json()['reference']

    support = _client_for(_staff('disputesupport@example.com', group='support'))
    queue = support.get(ADMIN_DISPUTES)
    assert queue.status_code == 200
    assert [row['reference'] for row in queue.json()['items']] == [reference]

    claimed = support.post(
        f'{ADMIN_DISPUTES}{reference}/review', {},
        content_type='application/json',
    )
    assert claimed.status_code == 200, claimed.content
    assert claimed.json()['status'] == 'under_review'
    assert AuditLog.objects.filter(action='dispute.review').exists()
    # Claiming is idempotent — the second call changes nothing.
    again = support.post(
        f'{ADMIN_DISPUTES}{reference}/review', {},
        content_type='application/json',
    )
    assert again.json()['status'] == 'under_review'

    # A ruling without a reason never lands (§17.3 resolution reason).
    missing = support.post(
        f'{ADMIN_DISPUTES}{reference}/resolve',
        {'resolution': 'buyer_favor'},
        content_type='application/json',
    )
    assert missing.status_code == 400
    assert missing.json()['error'] == 'reason_required'

    ruled = support.post(
        f'{ADMIN_DISPUTES}{reference}/resolve',
        {
            'resolution': 'buyer_favor',
            'reason': 'No delivery signature; the buyer credibly has no goods.',
        },
        content_type='application/json',
    )
    assert ruled.status_code == 200, ruled.content
    body = ruled.json()
    assert body['status'] == 'resolved'
    assert body['resolution'] == 'buyer_favor'
    assert body['resolution_reason']
    assert body['resolved_by'] == 'disputesupport@example.com'
    assert [e['kind'] for e in body['events']] == [
        'created', 'under_review', 'resolved'
    ]
    assert AuditLog.objects.filter(action='dispute.resolved').exists()

    # The linked Phase 11 intake is answered by the ruling (§11.3).
    intake_row = OrderRequest.objects.get(pk=intake.json()['id'])
    assert intake_row.status == 'resolved'

    # The record is frozen: no statements, no withdrawal, no second ruling.
    late_stmt = client.post(
        f'{DISPUTES}{reference}/statements', {'body': 'One more thing.'},
        content_type='application/json',
    )
    assert late_stmt.status_code == 400
    assert late_stmt.json()['error'] == 'dispute_closed'
    assert client.post(
        f'{DISPUTES}{reference}/cancel', {}, content_type='application/json'
    ).status_code == 400
    assert support.post(
        f'{ADMIN_DISPUTES}{reference}/resolve',
        {'resolution': 'seller_favor', 'reason': 'Changed my mind.'},
        content_type='application/json',
    ).status_code == 400

    # Both sides were told (§15.3).
    assert Notification.objects.filter(recipient=buyer).exists()
    assert Notification.objects.filter(
        recipient=store.user, category='orders'
    ).exists()


def test_unauthorized_users_cannot_alter_disputes(client):
    _seller, store = _store('disputeguard@example.com')
    product, variant = _product(store, price='299.00')
    buyer = _register(client, BUYER)
    order, _shipment = _deliver(buyer, variant)
    created = client.post(
        f'{ORDERS}{order.number}/disputes',
        {'reason': 'seller_unresponsive', 'statement': 'Nobody replies.'},
        content_type='application/json',
    )
    assert created.status_code == 201, created.content
    reference = created.json()['reference']

    seller = _client_for(store.user)
    # Neither party may claim or rule — the staff desks are group-gated (§4).
    assert seller.post(
        f'{ADMIN_DISPUTES}{reference}/review', {},
        content_type='application/json',
    ).status_code == 403
    assert seller.post(
        f'{ADMIN_DISPUTES}{reference}/resolve',
        {'resolution': 'seller_favor', 'reason': 'No.'},
        content_type='application/json',
    ).status_code == 403
    assert client.post(
        f'{ADMIN_DISPUTES}{reference}/resolve',
        {'resolution': 'buyer_favor', 'reason': 'Me.'},
        content_type='application/json',
    ).status_code == 403

    # The buyer cannot answer as the store (no seller flag → 403), and the
    # store cannot withdraw the buyer's dispute (not the party → 404).
    assert client.post(
        f'{SELLER_DISPUTES}{reference}/respond',
        {'statement': 'Pretending to be the store.'},
        content_type='application/json',
    ).status_code == 403
    assert seller.post(
        f'{DISPUTES}{reference}/cancel', {}, content_type='application/json'
    ).status_code == 404

    # Anonymous callers get nothing at all.
    anon = Client()
    assert anon.get(f'{DISPUTES}{reference}/').status_code in (401, 403)
    assert anon.post(
        f'{ADMIN_DISPUTES}{reference}/review', {}, content_type='application/json'
    ).status_code in (401, 403)

    # None of those attempts wrote anything — only the creation is on record.
    assert not Dispute.objects.get(reference=reference).events.exclude(
        kind='created'
    ).exists()
    assert AuditLog.objects.filter(action__startswith='dispute.').count() == 1



