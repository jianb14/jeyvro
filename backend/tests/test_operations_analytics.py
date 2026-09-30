"""Phase 19.3 gate tests — operational analytics (§6 v1.16, ROADMAP §19.3).

Contracts proven here:

1. **Derived, never queried live**: the operations and performance endpoints
   read the §19.3 rollups, and the §17 promise is proven the §19.1 way — hand-edit
   a rollup row and the API follows it.
2. **The buckets partition the day**: the four order-status buckets re-add to the
   orders created that day, and `orders_cancelled` mirrors the platform row
   exactly — two independent derivations that must agree.
3. **Fulfillment, returns and refunds are events, not opinions**: parcels
   created and delivered, cases filed / approved / rejected / received, refunds
   issued — and *settled* counted from the ledger debits, the money truth.
4. **Seller performance is store-sliced**: store rows attribute the records of
   the slice they belong to; a whole-order record stays at the platform grain.
5. **Access is §4-gated** (the oversight groups; moderator out), every range is
   validated server-side, and `rebuild_reporting` stays idempotent over the new
   tables.
"""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from django.test import Client
from django.utils import timezone

from apps.accounts.models import Address, User
from apps.cart.models import Cart
from apps.catalog import services as catalog_services
from apps.catalog.models import Product, Variant
from apps.messaging.models import Conversation, Message
from apps.orders import services as order_services
from apps.orders.models import (
    Order,
    OrderRequest,
    RequestKind,
    ShipmentStatus,
)
from apps.payments import services as payment_services
from apps.reporting import services as reporting_services
from apps.reporting.models import (
    DailyOperationsMetric,
    DailyPlatformMetric,
    DailyStoreOpsMetric,
)
from apps.resolutions import services as resolution_services
from apps.resolutions.models import (
    Dispute,
    DisputeEvent,
    DisputeEventKind,
    ReturnCase,
)
from apps.stores.models import Store

pytestmark = pytest.mark.django_db

PASSWORD = 'Str0ng!Passw0rd'
OPERATIONS = '/api/v1/admin/analytics/operations/'
PERFORMANCE = '/api/v1/admin/analytics/performance/'


def _make_user(email, *, group=None):
    user = User.objects.create_user(
        email=email,
        password=PASSWORD,
        first_name=email.split('@')[0].capitalize(),
        last_name='User',
        is_staff=bool(group),
    )
    if group:
        grp, _ = Group.objects.get_or_create(name=group)
        user.groups.add(grp)
    return user


def _client_for(user):
    client = Client()
    client.force_login(user)
    return client


def _store(suffix, price='500.00'):
    """An active store with one published, stocked variant, and its seller."""
    seller = _make_user(f'opsseller{suffix}@example.com')
    store = Store.objects.create(
        user=seller,
        name=f'Ops Store {suffix}',
        status=Store.Status.ACTIVE,
        shipping_flat_fee=Decimal('50.00'),
    )
    seller.is_seller = True
    seller.save(update_fields=['is_seller'])
    product = Product.objects.create(
        store=store,
        title=f'Ops Product {suffix}',
        base_price=Decimal(price),
        status=Product.Status.PUBLISHED,
    )
    variant = Variant.objects.create(
        product=product, name='Default', price=Decimal(price), is_default=True
    )
    catalog_services.ensure_inventory(variant, initial_on_hand=20)
    return seller, store, product, variant


def _order(buyer, variant, quantity=1):
    """A real checkout through the services (§8) — unpaid COD, still in flight."""
    address = Address.objects.create(
        user=buyer,
        full_name='Op Buyer',
        phone='09171234567',
        line1='9 Kalayaan Street',
        city='Quezon City',
        province='Metro Manila',
        postal_code='1100',
    )
    cart = Cart.objects.filter(user=buyer).first() or Cart.objects.create(user=buyer)
    cart.items.update_or_create(variant=variant, defaults={'quantity': quantity})
    return order_services.create_order(buyer, address.id, payment_method='cod')


def _fulfil(order):
    """processing → packed → parcel → delivered: the real §10 flow."""
    for seller_order in order.seller_orders.all():
        seller = seller_order.store.user
        order_services.mark_seller_order_processing(seller_order, actor=seller)
        order_services.mark_seller_order_packed(seller_order, actor=seller)
        shipment = order_services.create_shipment(
            seller_order,
            carrier_code='manual',
            package_notes='Ops fixture',
            package_weight_grams=300,
            actor=seller,
        )
        order_services.update_shipment_status(
            shipment, ShipmentStatus.DELIVERED, actor=seller
        )
    order.refresh_from_db()
    return order


# --- §19.3 derivation ---------------------------------------------------------


def test_the_operational_day_is_derived_from_the_records():
    """Every column is a count over the records — one day, four orders."""
    seller, store, product, variant = _store('derived')
    finance = _make_user('opsfinance@example.com', group='finance')

    # One order per status bucket: in flight, delivered, cancelled, refunded.
    open_order = _order(_make_user('opsopen@example.com'), variant)
    delivered = _fulfil(_order(_make_user('opsdelivered@example.com'), variant))
    cancelled = _order(_make_user('opscancelled@example.com'), variant)
    order_services.cancel_order(cancelled.user, cancelled.number)
    refunded = _order(_make_user('opsrefunded@example.com'), variant)
    payment_services.mark_paid(refunded.payment, source='test')
    payment_services.refund(
        refunded.payment,
        refunded.payment.amount,
        reason='Ops fixture refund',
        actor=finance,
    )

    # A return on the delivered order, through the real §17.1 flow: filed →
    # approved → received (each step writes its own timeline event).
    item_id = delivered.seller_orders.first().items.first().id
    case = resolution_services.apply_return(
        delivered.user,
        delivered.number,
        reason=ReturnCase.Reason.DAMAGED,
        lines=[{'order_item_id': item_id, 'quantity': 1}],
    )
    resolution_services.respond_to_return(
        seller, case.reference, decision='approve'
    )
    resolution_services.receive_return(seller, case.reference)

    # Support records: one intake, one thread with two messages, one dispute
    # with a staff ruling.
    OrderRequest.objects.create(
        order=delivered, kind=RequestKind.ISSUE, reason='Parcel arrived late'
    )
    conversation = Conversation.objects.create(
        customer=open_order.user, store=store, subject='Where is my parcel?'
    )
    Message.objects.create(
        conversation=conversation, sender=open_order.user, body='Any update?'
    )
    Message.objects.create(
        conversation=conversation,
        sender=open_order.user,
        body='Order shipped.',
        is_system=True,
    )
    dispute = Dispute.objects.create(
        reference='JVDSP-OPS-DERIVED',
        order=open_order,
        requested_by=open_order.user,
        reason=Dispute.Reason.OTHER,
        statement='The seller never replied.',
    )
    DisputeEvent.objects.create(
        dispute=dispute,
        kind=DisputeEventKind.RESOLVED,
        previous_status=Dispute.Status.OPEN,
        new_status=Dispute.Status.RESOLVED,
        message='Refund agreed',
    )

    day = timezone.localdate()
    reporting_services.rebuild(start=day, end=day)
    row = DailyOperationsMetric.objects.get(day=day)

    assert row.orders_open == 1
    assert row.orders_completed == 1
    assert row.orders_cancelled == 1
    assert row.orders_refunded == 1
    assert row.shipments_created == 1
    assert row.shipments_delivered == 1
    assert row.returns_filed == 1
    assert row.returns_approved == 1
    assert row.returns_rejected == 0
    assert row.returns_received == 1
    assert row.refunds_issued == 1
    assert row.refunds_settled == 1  # the COD refund settled at once
    assert row.requests_filed == 1
    assert row.conversations_opened == 1
    assert row.messages_sent == 2  # the system notice counts too
    assert row.disputes_opened == 1
    assert row.disputes_resolved == 1

    # The endpoint serves the same numbers, and only the rollups.
    support = _client_for(_make_user('opssupport@example.com', group='support'))
    body = support.get(OPERATIONS)
    assert body.status_code == 200, body.content
    assert body.json()['totals']['orders_completed'] == 1
    assert body.json()['days'][-1]['messages_sent'] == 2

    # §17 proven the §19.1 way: hand-edit the rollup and the API follows it —
    # if this endpoint read the orders, this number would not budge.
    DailyOperationsMetric.objects.filter(day=day).update(orders_completed=99)
    assert support.get(OPERATIONS).json()['totals']['orders_completed'] == 99


def test_status_buckets_partition_the_day_and_mirror_the_platform_row():
    """Two independent derivations of the same day must agree (§17)."""
    _seller, _shop, _product, variant = _store('buckets')
    _order(_make_user('bucketopen@example.com'), variant)
    _fulfil(_order(_make_user('bucketdone@example.com'), variant))
    cancelled = _order(_make_user('bucketcancel@example.com'), variant)
    order_services.cancel_order(cancelled.user, cancelled.number)

    day = timezone.localdate()
    reporting_services.rebuild(start=day, end=day)
    operations = DailyOperationsMetric.objects.get(day=day)
    platform = DailyPlatformMetric.objects.get(day=day)

    created = Order.objects.filter(created_at__date=day).count()
    assert created == 3
    buckets = (
        operations.orders_open
        + operations.orders_completed
        + operations.orders_cancelled
        + operations.orders_refunded
    )
    assert buckets == created
    # Both tables derive "cancelled" from the orders; they must not disagree.
    assert operations.orders_cancelled == platform.orders_cancelled == 1
    # The platform's live count excludes cancelled orders — the other three
    # buckets are exactly what it counted.
    assert platform.orders_count == (
        operations.orders_open
        + operations.orders_completed
        + operations.orders_refunded
    )


def test_seller_performance_is_store_sliced_and_reads_the_rollups():
    """Store rows attribute the slice's records; whole-order stays platform-wide."""
    _seller_a, store_a, _product_a, variant_a = _store('perfa')
    _seller_b, store_b, _product_b, variant_b = _store('perfb')
    buyer = _make_user('perfbuyer@example.com')

    delivered_a = _fulfil(_order(buyer, variant_a))
    _fulfil(_order(_make_user('perfbuyer2@example.com'), variant_b))
    delivered_b = _fulfil(_order(_make_user('perfbuyer3@example.com'), variant_b))

    # A return on store B's slice — the case names the slice, so the store row
    # can name it too.
    item_id = delivered_b.seller_orders.first().items.first().id
    resolution_services.apply_return(
        delivered_b.user,
        delivered_b.number,
        reason=ReturnCase.Reason.WRONG_ITEM,
        lines=[{'order_item_id': item_id, 'quantity': 1}],
    )
    # A whole-order case carries no slice, so it belongs to the platform grain
    # alone — splitting it across stores would invent attribution. (The service
    # path for filing is test_returns' job; this is the shape it writes.)
    ReturnCase.objects.create(
        reference='JVRET-PERF-WHOLE',
        order=delivered_a,
        requested_by=buyer,
        reason=ReturnCase.Reason.CHANGED_MIND,
    )

    day = timezone.localdate()
    reporting_services.rebuild(start=day, end=day)

    row_a = DailyStoreOpsMetric.objects.get(day=day, store=store_a)
    row_b = DailyStoreOpsMetric.objects.get(day=day, store=store_b)
    assert row_a.shipments_created == 1
    assert row_a.shipments_delivered == 1
    assert row_a.returns_filed == 0  # the whole-order case is not store A's
    assert row_b.shipments_created == 2
    assert row_b.shipments_delivered == 2
    assert row_b.returns_filed == 1

    operations = DailyOperationsMetric.objects.get(day=day)
    assert operations.returns_filed == 2  # slice case + whole-order case

    support = _client_for(_make_user('perfstaff@example.com', group='support'))
    body = support.get(PERFORMANCE)
    assert body.status_code == 200, body.content
    items = body.json()['items']
    # Biggest deliverer first.
    assert [row['store_id'] for row in items] == [store_b.id, store_a.id]
    assert items[0]['store__name'] == store_b.name
    assert items[0]['shipments_delivered'] == 2
    assert items[0]['returns_filed'] == 1
    # The endpoint reads the same rollup rows the test just derived.
    assert items[0]['shipments_created'] == row_b.shipments_created

    limited = support.get(f'{PERFORMANCE}?limit=1').json()
    assert [row['store_id'] for row in limited['items']] == [store_b.id]


# --- §19.3 the read API -------------------------------------------------------


def test_operational_reads_are_group_gated():
    """§4: the oversight groups oversee operations; moderator owns neither."""
    for group in ('support', 'operations', 'finance', 'administrator'):
        client = _client_for(_make_user(f'gate{group}@example.com', group=group))
        assert client.get(OPERATIONS).status_code == 200, group
        assert client.get(PERFORMANCE).status_code == 200, group

    moderator = _client_for(_make_user('gatemoderator@example.com', group='moderator'))
    assert moderator.get(OPERATIONS).status_code == 403
    assert moderator.get(PERFORMANCE).status_code == 403

    customer = _make_user('gatecustomer@example.com')
    assert _client_for(customer).get(OPERATIONS).status_code == 403
    assert Client().get(PERFORMANCE).status_code == 403


def test_the_range_is_validated_server_side():
    """Same `?from=&to=` contract as the other §19 endpoints (§8)."""
    staff = _client_for(_make_user('rangelocal@example.com', group='operations'))
    day = timezone.localdate()

    ok = staff.get(OPERATIONS, {'from': str(day), 'to': str(day)})
    assert ok.status_code == 200, ok.content
    assert ok.json()['start'] == str(day)

    inverted = staff.get(OPERATIONS, {'from': str(day), 'to': str(day - timedelta(days=3))})
    assert inverted.status_code == 400
    assert inverted.json()['error'] == 'invalid_range'

    assert staff.get(OPERATIONS, {'from': 'yesterday'}).status_code == 400
    assert staff.get(OPERATIONS, {'from': str(day - timedelta(days=400))}).status_code == 400
    assert staff.get(
        PERFORMANCE, {'from': str(day), 'to': str(day - timedelta(days=1))}
    ).status_code == 400


def test_rebuild_stays_idempotent_over_the_operations_tables():
    """Same rows, same pks — the new grains re-derive exactly."""
    _seller, store, _product, variant = _store('idem')
    delivered = _fulfil(_order(_make_user('idembuyer@example.com'), variant))

    day = timezone.localdate()
    reporting_services.rebuild(start=day, end=day)
    first = DailyOperationsMetric.objects.get(day=day)
    first_store = DailyStoreOpsMetric.objects.get(day=day, store=store)
    assert first.shipments_delivered == 1

    reporting_services.rebuild(start=day, end=day)
    again = DailyOperationsMetric.objects.get(day=day)
    again_store = DailyStoreOpsMetric.objects.get(day=day, store=store)
    assert again.pk == first.pk
    assert again.orders_completed == first.orders_completed
    assert again.shipments_created == first.shipments_created
    assert again_store.pk == first_store.pk
    assert again_store.shipments_delivered == first_store.shipments_delivered
    # An order cancelled after delivery moves bucket on the next rebuild — the
    # parcel really was delivered, so that column never rewrites itself.
    delivered.status = Order.Status.CANCELLED
    delivered.save(update_fields=['status', 'updated_at'])
    reporting_services.rebuild(start=day, end=day)
    emptied = DailyOperationsMetric.objects.get(day=day)
    assert emptied.shipments_delivered == 1
    assert emptied.orders_cancelled == 1
    assert emptied.orders_completed == 0


def test_support_workload_counts_only_what_was_written():
    """Requests, threads, messages and disputes — nothing inferred."""
    _seller, store, _product, variant = _store('support')
    buyer = _make_user('supportbuyer@example.com')
    delivered = _fulfil(_order(buyer, variant))

    OrderRequest.objects.create(
        order=delivered, kind=RequestKind.RETURN, reason='Wrong size'
    )
    OrderRequest.objects.create(
        order=delivered, kind=RequestKind.ISSUE, reason='Box was open'
    )
    store_thread = Conversation.objects.create(
        customer=buyer, store=store, subject='Sizing question'
    )
    support_thread = Conversation.objects.create(
        customer=buyer, subject='Platform help', store=None
    )
    for conversation, text in (
        (store_thread, 'Which size fits?'),
        (store_thread, 'Size M ships tomorrow.'),
        (support_thread, 'How do I return this?'),
    ):
        Message.objects.create(conversation=conversation, sender=buyer, body=text)

    # A dispute the buyer withdrew is opened, not resolved.
    dispute = Dispute.objects.create(
        reference='JVDSP-OPS-SUPPORT',
        order=delivered,
        requested_by=buyer,
        reason=Dispute.Reason.OTHER,
        statement='Still waiting.',
    )
    DisputeEvent.objects.create(
        dispute=dispute,
        kind=DisputeEventKind.CANCELLED,
        previous_status=Dispute.Status.OPEN,
        new_status=Dispute.Status.CANCELLED,
    )

    day = timezone.localdate()
    reporting_services.rebuild(start=day, end=day)
    row = DailyOperationsMetric.objects.get(day=day)
    assert row.requests_filed == 2
    assert row.conversations_opened == 2
    assert row.messages_sent == 3
    assert row.disputes_opened == 1
    assert row.disputes_resolved == 0  # a withdrawal is not a ruling

    # Store grain: only the store's own thread is its message volume.
    store_row = DailyStoreOpsMetric.objects.get(day=day, store=store)
    assert store_row.messages_sent == 2
    assert store_row.requests_filed == 0  # neither intake named the slice

