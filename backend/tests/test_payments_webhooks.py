"""Phase 9 webhook gates — signed, idempotent, server-verified (§9.3).

Unsigned or badly-signed callbacks change nothing, duplicate deliveries are
acknowledged exactly once, amounts are verified against the order total
before a capture lands, failures release the reservation, and unknown
references are refused *without* claiming the event so a gateway retry can
still succeed later.
"""
import hashlib
import hmac
import json
from decimal import Decimal

import pytest

from apps.accounts.models import Address, User
from apps.audit.models import AuditLog
from apps.cart.models import Cart, CartItem
from apps.catalog import services as catalog_services
from apps.catalog.models import Inventory, Product, Variant
from apps.orders import services as order_services
from apps.payments import services as payment_services
from apps.payments.models import (
    Payment,
    PaymentAttempt,
    PaymentTransaction,
    Refund,
    RefundStatus,
    WebhookEvent,
)
from apps.stores.models import Store

pytestmark = pytest.mark.django_db

WEBHOOK = '/api/v1/payments/webhooks/generic/'
SECRET = 'test-webhook-secret'


@pytest.fixture(autouse=True)
def payment_settings(settings):
    """Sandbox gateway + a known webhook secret for every test here."""
    settings.PAYMENTS_GATEWAY_SANDBOX = True
    settings.PAYMENTS_GATEWAY_WEBHOOK_SECRET = SECRET
    return settings


def sign(body):
    return hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()


def deliver(client, payload, *, signature=None, raw_body=None):
    body = raw_body if raw_body is not None else json.dumps(payload).encode()
    return client.post(
        WEBHOOK,
        data=body,
        content_type='application/json',
        HTTP_X_PAYMENTS_SIGNATURE=sign(body) if signature is None else signature,
    )


def event_payload(event_id, event_type, reference, amount=None, **extra_data):
    data = {'reference': reference}
    if amount is not None:
        data['amount'] = str(amount)
    data.update(extra_data)
    return {'id': event_id, 'type': event_type, 'data': data}


def make_pending_online_payment(*, method='card', quantity=2, stock=10,
                                price='299.00'):
    """A placed order with a pending online (sandbox) payment — no HTTP."""
    seller = User.objects.create_user(
        email='webhookseller@example.com', password='x'
    )
    store = Store.objects.create(
        user=seller, name='Webhook Store', status=Store.Status.ACTIVE
    )
    product = Product.objects.create(
        store=store,
        title='Webhook Product',
        base_price=Decimal(price),
        status=Product.Status.PUBLISHED,
    )
    variant = Variant.objects.create(
        product=product, name='Default', price=Decimal(price), is_default=True
    )
    catalog_services.ensure_inventory(variant, initial_on_hand=stock)

    buyer = User.objects.create_user(email='webhookbuyer@example.com', password='x')
    address = Address.objects.create(
        user=buyer, full_name='Webhook Buyer', phone='0900', line1='1 Webhook Way',
        city='Manila', province='Metro Manila', postal_code='1000',
    )
    cart = Cart.objects.create(user=buyer)
    CartItem.objects.create(cart=cart, variant=variant, quantity=quantity)
    order = order_services.create_order(buyer, address.id, method)
    return order, variant, order.payment


def test_unsigned_and_badly_signed_callbacks_change_nothing(client):
    order, _variant, payment = make_pending_online_payment()

    bad = deliver(
        client,
        event_payload('evt_bad_1', 'payment.paid', payment.reference),
        signature='deadbeef',
    )
    assert bad.status_code == 400, bad.content
    assert bad.json()['error'] == 'invalid_signature'

    missing = deliver(
        client,
        event_payload('evt_bad_2', 'payment.paid', payment.reference),
        signature='',
    )
    assert missing.status_code == 400

    payment.refresh_from_db()
    order.refresh_from_db()
    assert payment.status == 'pending'
    assert order.status == 'awaiting_payment'
    assert WebhookEvent.objects.count() == 0
    assert PaymentTransaction.objects.count() == 0


def test_unknown_providers_are_refused(client):
    order, _variant, payment = make_pending_online_payment()
    body = json.dumps(
        event_payload('evt_provider', 'payment.paid', payment.reference)
    ).encode()

    response = client.post(
        '/api/v1/payments/webhooks/paymongo/',
        data=body,
        content_type='application/json',
        HTTP_X_PAYMENTS_SIGNATURE=sign(body),
    )
    assert response.status_code == 404
    assert response.json()['error'] == 'unknown_provider'


def test_valid_paid_webhook_captures_the_payment(client):
    order, variant, payment = make_pending_online_payment()

    response = deliver(
        client,
        event_payload('evt_paid_1', 'payment.paid', payment.reference,
                      amount=payment.amount),
    )
    assert response.status_code == 200, response.content
    assert response.json() == {'status': 'processed', 'event_id': 'evt_paid_1'}

    payment.refresh_from_db()
    order.refresh_from_db()
    assert payment.status == 'paid'
    assert payment.paid_at is not None
    assert order.status == 'paid'

    inventory = Inventory.objects.get(variant=variant)
    assert inventory.on_hand == 8  # 10 - 2 sold
    assert inventory.reserved == 0

    entries = PaymentTransaction.objects.filter(payment=payment)
    assert entries.count() == 1
    assert entries.get().amount == order.grand_total
    assert PaymentAttempt.objects.filter(
        payment=payment, status='succeeded'
    ).count() == 1

    event = WebhookEvent.objects.get(event_id='evt_paid_1')
    assert event.status == 'processed'
    assert event.processed_at is not None
    assert AuditLog.objects.filter(action='payment.captured').exists()


def test_duplicate_delivery_is_acknowledged_exactly_once(client):
    order, _variant, payment = make_pending_online_payment()
    payload = event_payload('evt_dup_1', 'payment.paid', payment.reference,
                            amount=payment.amount)

    first = deliver(client, payload)
    assert first.status_code == 200
    assert first.json()['status'] == 'processed'

    second = deliver(client, payload)
    assert second.status_code == 200
    assert second.json() == {'status': 'duplicate', 'event_id': 'evt_dup_1'}

    # The money facts exist exactly once — no double charge, no extra rows.
    assert WebhookEvent.objects.count() == 1
    assert PaymentTransaction.objects.filter(payment=payment).count() == 1
    assert PaymentAttempt.objects.filter(payment=payment).count() == 2  # 1 session + 1 capture
    assert AuditLog.objects.filter(action='payment.captured').count() == 1
    payment.refresh_from_db()
    assert payment.status == 'paid'


def test_amount_mismatch_is_rejected_and_recorded(client):
    order, _variant, payment = make_pending_online_payment()

    response = deliver(
        client,
        event_payload('evt_mismatch', 'payment.paid', payment.reference,
                      amount=Decimal('1.00')),
    )
    assert response.status_code == 400, response.content
    body = response.json()
    assert body['status'] == 'failed'
    assert body['error'].startswith('amount_mismatch')

    payment.refresh_from_db()
    order.refresh_from_db()
    assert payment.status == 'pending'
    assert order.status == 'awaiting_payment'
    assert PaymentTransaction.objects.count() == 0

    # The refusal itself is auditable.
    event = WebhookEvent.objects.get(event_id='evt_mismatch')
    assert event.status == 'failed'
    assert 'amount_mismatch' in event.error


def test_failed_payment_event_cancels_the_order_and_releases_stock(client):
    order, variant, payment = make_pending_online_payment()

    response = deliver(
        client,
        event_payload('evt_failed', 'payment.failed', payment.reference,
                      amount=payment.amount, failure_reason='Card declined'),
    )
    assert response.status_code == 200, response.content
    assert response.json()['status'] == 'processed'

    payment.refresh_from_db()
    order.refresh_from_db()
    assert payment.status == 'failed'
    assert payment.failure_reason == 'Card declined'
    assert order.status == 'cancelled'
    assert Inventory.objects.get(variant=variant).reserved == 0
    assert PaymentAttempt.objects.filter(
        payment=payment, status='failed', failure_message='Card declined'
    ).exists()
    assert AuditLog.objects.filter(action='payment.failed').exists()


def test_unknown_reference_is_refused_without_claiming_the_event(client):
    response = deliver(
        client,
        event_payload('evt_unknown_ref', 'payment.paid', 'JVPAY-20260101-NOPE1234'),
    )
    assert response.status_code == 404
    assert response.json()['error'] == 'unknown_reference'
    # Not claimed: a gateway retry can still succeed once the payment exists.
    assert WebhookEvent.objects.count() == 0


def test_malformed_payloads_are_rejected(client):
    _order, _variant, payment = make_pending_online_payment()

    broken = deliver(client, None, raw_body=b'{not json')
    assert broken.status_code == 400
    assert broken.json()['error'] == 'invalid_payload'

    incomplete = deliver(
        client, {'id': 'evt_no_ref', 'type': 'payment.paid', 'data': {}}
    )
    assert incomplete.status_code == 400
    assert incomplete.json()['error'] == 'invalid_payload'

    assert payment.status == 'pending'
    assert WebhookEvent.objects.count() == 0


def test_unhandled_event_types_are_recorded_as_ignored(client):
    _order, _variant, payment = make_pending_online_payment()

    response = deliver(
        client,
        event_payload('evt_dispute', 'charge.disputed', payment.reference,
                      amount=payment.amount),
    )
    assert response.status_code == 200
    assert response.json()['status'] == 'ignored'

    event = WebhookEvent.objects.get(event_id='evt_dispute')
    assert event.status == 'ignored'
    assert event.error == 'unhandled_type:charge.disputed'
    assert Payment.objects.get(pk=payment.pk).status == 'pending'


def test_capture_event_after_manual_capture_is_ignored(client):
    _order, _variant, payment = make_pending_online_payment()
    # Someone confirmed the money first (staff action / earlier webhook).
    payment_services.mark_paid(payment, source='manual')

    response = deliver(
        client,
        event_payload('evt_late', 'payment.paid', payment.reference,
                      amount=payment.amount),
    )
    assert response.status_code == 200
    assert response.json()['status'] == 'ignored'
    assert WebhookEvent.objects.get(event_id='evt_late').error == 'already_paid'
    assert PaymentTransaction.objects.filter(payment=payment).count() == 1


def test_refund_webhooks_settle_or_fail_pending_refunds(client):
    order, _variant, payment = make_pending_online_payment()
    deliver(
        client,
        event_payload('evt_pay_refunds', 'payment.paid', payment.reference,
                      amount=payment.amount),
    )
    payment.refresh_from_db()

    pending = Refund.objects.create(
        reference='JVREF-20260101-TESTREF1',
        payment=payment,
        amount=Decimal('100.00'),
        status=RefundStatus.PENDING,
        gateway_reference='gwref_1',
    )

    settled = deliver(
        client,
        event_payload('evt_refund_ok', 'refund.succeeded', 'gwref_1',
                      amount='100.00'),
    )
    assert settled.status_code == 200, settled.content
    assert settled.json()['status'] == 'processed'
    pending.refresh_from_db()
    payment.refresh_from_db()
    assert pending.status == RefundStatus.SUCCEEDED
    assert payment.status == 'partially_refunded'
    assert PaymentTransaction.objects.filter(
        payment=payment, kind='refund', direction='debit'
    ).count() == 1

    failed = Refund.objects.create(
        reference='JVREF-20260101-TESTREF2',
        payment=payment,
        amount=Decimal('50.00'),
        status=RefundStatus.PENDING,
        gateway_reference='gwref_2',
    )
    refused = deliver(
        client,
        event_payload('evt_refund_bad', 'refund.failed', 'gwref_2'),
    )
    assert refused.status_code == 200
    failed.refresh_from_db()
    assert failed.status == RefundStatus.FAILED
    assert PaymentTransaction.objects.filter(payment=payment).count() == 2
