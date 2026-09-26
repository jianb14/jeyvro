"""Phase 13.5 gate tests — staff order & payment operations (§4 matrix).

Contracts proven here:
1. Oversight endpoints are group-gated: orders/requests read for
   support/finance/operations/administrator, shipments for
   support/operations/administrator, payments/refunds for
   support/finance/administrator — customers and out-of-group staff get 403.
2. Every list answers the {count, items} envelope with server-side filters
   (q/status/kind/method/carrier) and pagination.
3. The staff order detail serves the full snapshot plus the customer email
   and 404s unknown numbers.
4. Refunds are finance/administrator only (§4): support cannot issue one;
   a finance refund settles, writes the ledger reversal, and audits.
5. Refund oversight lists issued refunds with the issuing staff member.
"""
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from django.test import Client

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.orders.models import Order, OrderRequest, SellerOrder, Shipment
from apps.payments import services as payment_services
from apps.payments.models import Payment, Refund
from apps.stores.models import Store

pytestmark = pytest.mark.django_db

PASSWORD = 'Str0ng!Passw0rd'
ORDERS = '/api/v1/admin/orders/'
SHIPMENTS = '/api/v1/admin/shipments/'
REQUESTS = '/api/v1/admin/requests/'
PAYMENTS = '/api/v1/payments/admin/payments/'
REFUNDS = '/api/v1/payments/admin/refunds/'


def _make_user(email, *, group=None, is_staff=None):
    user = User.objects.create_user(
        email=email,
        password=PASSWORD,
        first_name=email.split('@')[0].capitalize(),
        last_name='User',
        is_staff=group is not None if is_staff is None else is_staff,
    )
    if group:
        grp, _ = Group.objects.get_or_create(name=group)
        user.groups.add(grp)
    return user


def _client_for(user):
    client = Client()
    client.force_login(user)
    return client


def _store_for(owner, name='Oversight Store'):
    return Store.objects.create(
        user=owner,
        name=name,
        description='13.5 tests',
        contact_email=owner.email,
        status=Store.Status.ACTIVE,
    )


def _order(user, *, number, status='placed', city='Quezon City'):
    return Order.objects.create(
        number=number,
        user=user,
        status=status,
        ship_to_name=f'{user.first_name} {user.last_name}',
        ship_to_phone='09171234567',
        shipping_line1='12 Mabini Street',
        shipping_city=city,
        shipping_province='Metro Manila',
        shipping_postal_code='1100',
        subtotal=Decimal('299.00'),
        shipping_total=Decimal('50.00'),
        savings_total=Decimal('0.00'),
        tax_total=Decimal('0.00'),
        grand_total=Decimal('349.00'),
    )


def _seller_order(order, store):
    return SellerOrder.objects.create(
        order=order,
        store=store,
        store_name=store.name,
        subtotal=Decimal('299.00'),
        shipping_fee=Decimal('50.00'),
        total=Decimal('349.00'),
    )


def _payment(order, *, reference, method='cod', status='pending'):
    return Payment.objects.create(
        reference=reference,
        order=order,
        method=method,
        status=status,
        amount=order.grand_total,
    )


def _shipment(seller_order, *, tracking, status='in_transit', carrier='manual'):
    return Shipment.objects.create(
        seller_order=seller_order,
        tracking_number=tracking,
        carrier=carrier,
        carrier_name='Manual Carrier',
        shipping_method='standard',
        shipping_fee=Decimal('50.00'),
        status=status,
        recipient_name='Bianca Buyer',
        recipient_phone='09171234567',
        shipping_address_text='12 Mabini Street, Quezon City',
    )


# --- 1. Order oversight: gating, filters, detail -----------------------------

def test_order_console_group_gating():
    support = _make_user('ops-sup@example.com', group='support')
    finance = _make_user('ops-fin@example.com', group='finance')
    operations = _make_user('ops-ops@example.com', group='operations')
    admin = _make_user('ops-adm@example.com', group='administrator')
    moderator = _make_user('ops-mod@example.com', group='moderator')
    bare_staff = _make_user('ops-bare@example.com', group=None, is_staff=True)
    customer = _make_user('ops-buyer@example.com', is_staff=False)

    seller = _make_user('ops-seller@example.com', is_staff=False)
    store = _store_for(seller)
    order = _order(customer, number='JV-OPS-00000001')
    _payment(order, reference='JVPAY-OPS-00000001')
    _seller_order(order, store)

    for user in (customer, moderator, bare_staff):
        assert _client_for(user).get(ORDERS).status_code == 403, user.email

    for user in (support, finance, operations, admin):
        res = _client_for(user).get(ORDERS)
        assert res.status_code == 200, user.email
        body = res.json()
        assert body['count'] == 1
        row = body['items'][0]
        assert row['number'] == 'JV-OPS-00000001'
        assert row['customer_email'] == 'ops-buyer@example.com'
        assert row['payment_method'] == 'cod'
        assert row['payment_status'] == 'pending'
        assert float(row['grand_total']) == 349.0
        assert row['store_names'] == ['Oversight Store']
        # Light oversight row — no line snapshots or address blocks.
        assert 'items' not in row
        assert 'shipping_address' not in row


def test_order_console_filters_are_server_side():
    support = _make_user('ops-sup2@example.com', group='support')
    seller = _make_user('ops-seller2@example.com', is_staff=False)
    store = _store_for(seller, name='Filter Fulfillment')
    buyer = _make_user('ops-buyer2@example.com', is_staff=False)

    placed = _order(buyer, number='JV-OPS-00000002')
    _payment(placed, reference='JVPAY-OPS-00000002')
    _seller_order(placed, store)

    shipped = _order(
        buyer, number='JV-OPS-00000003', status='shipped', city='Cebu City'
    )
    _payment(shipped, reference='JVPAY-OPS-00000003', status='paid')
    _seller_order(shipped, store)

    cancelled = _order(buyer, number='JV-OPS-00000004', status='cancelled')
    _payment(cancelled, reference='JVPAY-OPS-00000004', status='cancelled')
    _seller_order(cancelled, store)

    client = _client_for(support)

    by_status = client.get(f'{ORDERS}?status=shipped').json()
    assert by_status['count'] == 1
    assert by_status['items'][0]['number'] == 'JV-OPS-00000003'
    assert by_status['items'][0]['payment_status'] == 'paid'

    by_q = client.get(f'{ORDERS}?q=JV-OPS-00000004').json()
    assert [row['number'] for row in by_q['items']] == ['JV-OPS-00000004']

    by_email = client.get(f'{ORDERS}?q=ops-buyer2').json()
    assert by_email['count'] == 3

    by_payment = client.get(f'{ORDERS}?payment=cancelled').json()
    assert [row['number'] for row in by_payment['items']] == ['JV-OPS-00000004']

    by_store = client.get(f'{ORDERS}?store=filter-fulfillment').json()
    assert by_store['count'] == 3

    paged = client.get(f'{ORDERS}?page_size=1&page=2').json()
    assert paged['count'] == 3 and len(paged['items']) == 1


def test_order_detail_serves_full_snapshot_and_404s():
    support = _make_user('ops-sup3@example.com', group='support')
    customer = _make_user('ops-buyer3@example.com', is_staff=False)
    seller = _make_user('ops-seller3@example.com', is_staff=False)
    store = _store_for(seller)

    order = _order(customer, number='JV-OPS-00000005')
    _payment(order, reference='JVPAY-OPS-00000005', status='paid')
    _seller_order(order, store)

    client = _client_for(support)
    res = client.get(f'{ORDERS}JV-OPS-00000005/')
    assert res.status_code == 200, res.content
    body = res.json()
    assert body['number'] == 'JV-OPS-00000005'
    assert body['customer_email'] == 'ops-buyer3@example.com'
    assert body['payment']['reference'] == 'JVPAY-OPS-00000005'
    assert body['seller_orders'][0]['store_name'] == 'Oversight Store'
    assert 'requests' in body

    assert client.get(f'{ORDERS}JV-NOPE-00000000/').status_code == 404
    # The detail is staff-gated exactly like the list.
    customer_client = _client_for(customer)
    assert customer_client.get(f'{ORDERS}JV-OPS-00000005/').status_code == 403


# --- 2. Shipment oversight ---------------------------------------------------

def test_shipment_console_gating_and_filters():
    support = _make_user('shp-sup@example.com', group='support')
    operations = _make_user('shp-ops@example.com', group='operations')
    admin = _make_user('shp-adm@example.com', group='administrator')
    finance = _make_user('shp-fin@example.com', group='finance')
    customer = _make_user('shp-buyer@example.com', is_staff=False)

    seller = _make_user('shp-seller@example.com', is_staff=False)
    store = _store_for(seller, name='Parcel Partners')
    order = _order(customer, number='JV-SHP-00000001')
    seller_order = _seller_order(order, store)

    _shipment(
        seller_order, tracking='TRACK-SHP-0001', status='in_transit'
    )
    _shipment(
        seller_order, tracking='TRACK-SHP-0002', status='delivered',
        carrier='jtex',
    )

    # Finance is out of the shipment group (§4) — support/operations read.
    assert _client_for(finance).get(SHIPMENTS).status_code == 403
    assert _client_for(customer).get(SHIPMENTS).status_code == 403

    client = _client_for(operations)
    body = client.get(SHIPMENTS).json()
    assert body['count'] == 2
    row = next(r for r in body['items'] if r['tracking_number'] == 'TRACK-SHP-0001')
    assert row['order_number'] == 'JV-SHP-00000001'
    assert row['store_name'] == 'Parcel Partners'
    assert row['carrier'] == 'manual'
    assert row['status'] == 'in_transit'
    assert row['event_count'] == 0

    by_status = client.get(f'{SHIPMENTS}?status=delivered').json()
    assert [r['tracking_number'] for r in by_status['items']] == ['TRACK-SHP-0002']

    by_carrier = client.get(f'{SHIPMENTS}?carrier=jtex').json()
    assert by_carrier['count'] == 1

    by_q = client.get(f'{SHIPMENTS}?q=TRACK-SHP-0001').json()
    assert [r['tracking_number'] for r in by_q['items']] == ['TRACK-SHP-0001']

    by_order = client.get(f'{SHIPMENTS}?q=JV-SHP-00000001').json()
    assert by_order['count'] == 2

    assert _client_for(support).get(SHIPMENTS).status_code == 200
    assert _client_for(admin).get(SHIPMENTS).status_code == 200


# --- 3. Return/refund/dispute intake oversight -------------------------------

def test_request_console_gating_and_filters():
    support = _make_user('req-sup@example.com', group='support')
    finance = _make_user('req-fin@example.com', group='finance')
    operations = _make_user('req-ops@example.com', group='operations')
    admin = _make_user('req-adm@example.com', group='administrator')
    moderator = _make_user('req-mod@example.com', group='moderator')
    customer = _make_user('req-buyer@example.com', is_staff=False)

    seller = _make_user('req-seller@example.com', is_staff=False)
    store = _store_for(seller)
    order = _order(customer, number='JV-REQ-00000001')
    seller_order = _seller_order(order, store)

    OrderRequest.objects.create(
        order=order, seller_order=seller_order,
        kind=OrderRequest.Kind.RETURN, reason='Wrong size delivered',
    )
    OrderRequest.objects.create(
        order=order, kind=OrderRequest.Kind.REFUND, reason='Item arrived broken',
    )
    disputed = OrderRequest.objects.create(
        order=order, seller_order=seller_order,
        kind=OrderRequest.Kind.ISSUE, reason='Parcel never arrived',
    )
    OrderRequest.objects.create(
        order=order, kind=OrderRequest.Kind.RETURN,
        reason='Changed their mind', status=OrderRequest.Status.WITHDRAWN,
    )

    assert _client_for(customer).get(REQUESTS).status_code == 403
    assert _client_for(moderator).get(REQUESTS).status_code == 403

    client = _client_for(support)
    body = client.get(REQUESTS).json()
    assert body['count'] == 4
    assert {row['kind'] for row in body['items']} == {'return', 'refund', 'issue'}
    assert all(
        row['order_number'] == 'JV-REQ-00000001' for row in body['items']
    )
    assert all(
        row['customer_email'] == 'req-buyer@example.com'
        for row in body['items']
    )

    by_kind = client.get(f'{REQUESTS}?kind=issue').json()
    assert by_kind['count'] == 1
    assert by_kind['items'][0]['reason'] == 'Parcel never arrived'
    assert by_kind['items'][0]['id'] == disputed.id

    by_status = client.get(f'{REQUESTS}?status=withdrawn').json()
    assert [r['reason'] for r in by_status['items']] == ['Changed their mind']

    by_q = client.get(f'{REQUESTS}?q=broken').json()
    assert [r['kind'] for r in by_q['items']] == ['refund']

    by_order = client.get(f'{REQUESTS}?q=JV-REQ-00000001').json()
    assert by_order['count'] == 4

    for user in (finance, operations, admin):
        assert _client_for(user).get(REQUESTS).status_code == 200, user.email


# --- 4. Payment & refund oversight -------------------------------------------

def test_payment_console_gating_and_filters():
    support = _make_user('pay-sup@example.com', group='support')
    finance = _make_user('pay-fin@example.com', group='finance')
    admin = _make_user('pay-adm@example.com', group='administrator')
    operations = _make_user('pay-ops@example.com', group='operations')
    customer = _make_user('pay-buyer@example.com', is_staff=False)

    buyer = _make_user('pay-buyer2@example.com', is_staff=False)

    cod = _order(buyer, number='JV-PAY-00000001')
    _payment(cod, reference='JVPAY-PAY-00000001', method='cod', status='pending')

    online = _order(buyer, number='JV-PAY-00000002', status='paid')
    _payment(online, reference='JVPAY-PAY-00000002', method='gcash', status='paid')

    dead = _order(buyer, number='JV-PAY-00000003', status='cancelled')
    _payment(dead, reference='JVPAY-PAY-00000003', method='card', status='failed')

    # Out-of-group: operations never touches money (§4); customers never see it.
    assert _client_for(operations).get(PAYMENTS).status_code == 403
    assert _client_for(customer).get(PAYMENTS).status_code == 403

    client = _client_for(finance)
    body = client.get(PAYMENTS).json()
    assert body['count'] == 3
    row = next(
        r for r in body['items'] if r['reference'] == 'JVPAY-PAY-00000002'
    )
    assert row['method'] == 'gcash'
    assert row['status'] == 'paid'
    assert row['order_number'] == 'JV-PAY-00000002'
    assert row['customer_email'] == 'pay-buyer2@example.com'
    assert float(row['amount']) == 349.0
    assert float(row['refunded_total']) == 0.0

    by_method = client.get(f'{PAYMENTS}?method=cod').json()
    assert [r['reference'] for r in by_method['items']] == ['JVPAY-PAY-00000001']

    by_status = client.get(f'{PAYMENTS}?status=failed').json()
    assert [r['reference'] for r in by_status['items']] == ['JVPAY-PAY-00000003']

    by_q = client.get(f'{PAYMENTS}?q=JV-PAY-00000002').json()
    assert by_q['count'] == 1

    by_email = client.get(f'{PAYMENTS}?q=pay-buyer2').json()
    assert by_email['count'] == 3

    paged = client.get(f'{PAYMENTS}?page_size=1&page=3').json()
    assert paged['count'] == 3 and len(paged['items']) == 1

    assert _client_for(support).get(PAYMENTS).status_code == 200
    assert _client_for(admin).get(PAYMENTS).status_code == 200


def test_refunds_are_finance_only_and_oversight_lists_them():
    support = _make_user('ref-sup@example.com', group='support')
    finance = _make_user('ref-fin@example.com', group='finance')
    operations = _make_user('ref-ops@example.com', group='operations')
    bare_staff = _make_user('ref-bare@example.com', group=None, is_staff=True)
    customer = _make_user('ref-buyer@example.com', is_staff=False)

    seller = _make_user('ref-seller@example.com', is_staff=False)
    store = _store_for(seller)
    order = _order(customer, number='JV-REF-00000001')
    order.status = Order.Status.AWAITING_PAYMENT
    order.save(update_fields=['status'])
    _seller_order(order, store)
    payment = _payment(order, reference='JVPAY-REF-00000001')

    # Capture through the real service so the balance check has ledger truth.
    payment = payment_services.mark_paid(payment, source='cod_collection')

    def issue_refund(user):
        return _client_for(user).post(
            f'/api/v1/payments/{payment.reference}/refunds',
            {'amount': '50.00', 'reason': 'Goodwill credit'},
            content_type='application/json',
        )

    # Support, out-of-group staff, and customers never move money (§4).
    assert issue_refund(support).status_code == 403
    assert issue_refund(bare_staff).status_code == 403
    assert issue_refund(customer).status_code == 403

    res = issue_refund(finance)
    assert res.status_code == 201, res.content
    refund = res.json()
    assert refund['status'] == 'succeeded'  # COD settles immediately
    assert float(refund['amount']) == 50.0

    payment.refresh_from_db()
    assert payment.refunded_total == Decimal('50.00')
    assert AuditLog.objects.filter(action='refund.settled').exists()
    assert Refund.objects.get(reference=refund['reference']).actor == finance

    # Refund oversight: support reads the trail, operations cannot.
    body = _client_for(support).get(REFUNDS).json()
    assert body['count'] == 1
    row = body['items'][0]
    assert row['reference'] == refund['reference']
    assert row['payment_reference'] == 'JVPAY-REF-00000001'
    assert row['order_number'] == 'JV-REF-00000001'
    assert row['issued_by'] == 'ref-fin@example.com'
    assert row['reason'] == 'Goodwill credit'

    by_status = _client_for(finance).get(f'{REFUNDS}?status=succeeded').json()
    assert by_status['count'] == 1
    by_q = _client_for(finance).get(f'{REFUNDS}?q=JV-REF-00000001').json()
    assert by_q['count'] == 1

    assert _client_for(operations).get(REFUNDS).status_code == 403
    assert _client_for(customer).get(REFUNDS).status_code == 403