"""Phase 19.1 gate tests — analytics & reporting (§6 v1.16, §19.1).

Contracts proven here:

1. The aggregates are *derived*: every number the reporting tables hold is
   recomputed from the order snapshots and the payment ledger, and `rebuild`
   is idempotent — running it twice leaves the same rows, same pks.
2. Commission is taken on the store's **own net merchandise**: gross slice
   subtotal less the discounts that store funded, never shipping, never a
   platform-funded discount.
3. The rate is the one **in force when the money was captured** — a later
   rate change cannot rewrite a settled day.
4. Refunds reverse revenue and are charged to the stores whose lines came
   back, with the parts re-adding to the refund exactly.
5. The read API serves the **aggregates**, not the transactional tables, and
   is group-gated per §4/§6 v1.16.
"""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from django.test import Client
from django.utils import timezone

from apps.accounts.models import User
from apps.catalog import services as catalog_services
from apps.catalog.models import Product, Variant
from apps.orders.models import Order, SellerOrder
from apps.payments import services as payment_services
from apps.platform import services as platform_services
from apps.promotions.models import (
    Campaign,
    Promotion,
    PromotionKind,
    PromotionScope,
    PromotionUsage,
)
from apps.reporting import services as reporting_services
from apps.reporting.models import (
    DailyPlatformMetric,
    DailyProductMetric,
    DailyStoreMetric,
)
from apps.stores.models import Store

pytestmark = pytest.mark.django_db

PASSWORD = 'Str0ng!Passw0rd'
SUMMARY = '/api/v1/admin/analytics/summary/'
STORES = '/api/v1/admin/analytics/stores/'
PRODUCTS = '/api/v1/admin/analytics/products/'
REGISTER = '/api/v1/auth/register'
LOGIN = '/api/v1/auth/login'
ADDRESSES = '/api/v1/auth/addresses/'
CART_ITEMS = '/api/v1/cart/items'
CHECKOUT_ORDERS = '/api/v1/checkout/orders'

ADDRESS_PAYLOAD = {
    'full_name': 'Nena Buyer',
    'phone': '09171234567',
    'line1': '9 Bonifacio Street',
    'line2': '',
    'city': 'Makati',
    'province': 'Metro Manila',
    'postal_code': '1200',
}


def _make_user(email, *, group=None, is_staff=False):
    user = User.objects.create_user(
        email=email,
        password=PASSWORD,
        first_name=email.split('@')[0].capitalize(),
        last_name='User',
        is_staff=is_staff or group is not None,
    )
    if group:
        grp, _ = Group.objects.get_or_create(name=group)
        user.groups.add(grp)
    return user


def _client_for(user):
    client = Client()
    client.force_login(user)
    return client


def _catalog(price='500.00', fee='0.00', suffix=''):
    """An active store with one published, stocked variant."""
    seller = _make_user(f'reportseller{suffix}@example.com')
    store = Store.objects.create(
        user=seller,
        name=f'Report Store{suffix}',
        status=Store.Status.ACTIVE,
        shipping_flat_fee=Decimal(fee),
    )
    product = Product.objects.create(
        store=store,
        title=f'Report Product{suffix}',
        base_price=Decimal(price),
        status=Product.Status.PUBLISHED,
    )
    variant = Variant.objects.create(
        product=product, name='Default', price=Decimal(price), is_default=True
    )
    catalog_services.ensure_inventory(variant, initial_on_hand=20)
    return store, product, variant


def _buyer(client, email='reportbuyer@example.com'):
    """Registers + signs in a buyer and returns their address id."""
    credentials = {'email': email, 'password': PASSWORD}
    assert client.post(
        REGISTER, credentials, content_type='application/json'
    ).status_code == 201
    assert client.post(
        LOGIN, credentials, content_type='application/json'
    ).status_code == 200
    response = client.post(
        ADDRESSES, ADDRESS_PAYLOAD, content_type='application/json'
    )
    assert response.status_code == 201, response.content
    return response.json()['id']


def _paid_order(email='reportbuyer@example.com', *, quantity=1, price='500.00',
                fee='0.00', suffix='', voucher_code=''):
    """A checkout driven through the real API, then captured (§9)."""
    store, product, variant = _catalog(price=price, fee=fee, suffix=suffix)
    client = Client()
    address_id = _buyer(client, email)
    assert client.post(
        CART_ITEMS,
        {'variant_id': variant.id, 'quantity': quantity},
        content_type='application/json',
    ).status_code == 200
    payload = {'address_id': address_id, 'payment_method': 'cod'}
    if voucher_code:
        payload['voucher_code'] = voucher_code
    response = client.post(CHECKOUT_ORDERS, payload, content_type='application/json')
    assert response.status_code == 201, response.content

    order = Order.objects.get(number=response.json()['number'])
    payment_services.mark_paid(order.payment, source='test')
    order.refresh_from_db()
    return store, product, order


# --- §19.1 derivation ---------------------------------------------------------


def test_rebuild_derives_the_platform_day_from_the_records():
    """The rollup is a pure function of the orders and the ledger."""
    store, product, order = _paid_order()
    day = timezone.localdate()

    summary = reporting_services.rebuild(start=day, end=day)
    assert summary['days'] == 1

    row = DailyPlatformMetric.objects.get(day=day)
    assert row.orders_count == 1
    assert row.orders_paid == 1
    assert row.gmv == order.grand_total
    assert row.merchandise == order.subtotal
    assert row.active_customers == 1
    assert row.active_sellers == 1
    # The ledger is the money truth: one capture row per store slice.
    assert row.captured_total == SellerOrder.objects.get(order=order).total
    assert row.revenue == row.captured_total

    # Product activity is its own grain, and it adds up to the platform row.
    activity = DailyProductMetric.objects.get(day=day)
    assert activity.product_id == product.id
    assert activity.store_id == store.id
    assert activity.units_sold == 1
    assert row.units_sold == 1
    assert row.products_sold == 1


def test_rebuild_is_idempotent_and_drops_stale_rows():
    """Running the same range twice leaves the same rows — and the same pks."""
    store, _product, order = _paid_order()
    day = timezone.localdate()

    reporting_services.rebuild(start=day, end=day)
    first = DailyPlatformMetric.objects.get(day=day)
    store_row = DailyStoreMetric.objects.get(day=day, store=store)

    reporting_services.rebuild(start=day, end=day)
    again = DailyPlatformMetric.objects.get(day=day)
    assert again.pk == first.pk
    assert again.gmv == first.gmv
    assert again.commission == first.commission
    assert DailyStoreMetric.objects.get(day=day, store=store).pk == store_row.pk

    # A day the records no longer support keeps no row: cancelling the order
    # empties it on the next rebuild instead of leaving a stale figure behind.
    order.status = Order.Status.CANCELLED
    order.save(update_fields=['status', 'updated_at'])
    SellerOrder.objects.filter(order=order).update(
        status=Order.Status.CANCELLED, updated_at=timezone.now()
    )
    reporting_services.rebuild(start=day, end=day)
    emptied = DailyPlatformMetric.objects.get(day=day)
    assert emptied.orders_count == 0
    assert emptied.gmv == Decimal('0.00')

    # Product activity is a placement grain, so the cancelled order leaves no
    # product row at all...
    assert not DailyProductMetric.objects.filter(day=day, store=store).exists()

    # ...but the store row survives, because the cash is real: the capture had
    # already landed before the order was cancelled. The store's day reads zero
    # sales AND the money it collected — a rollup that forgot this would drop
    # money the ledger still holds.
    settled = DailyStoreMetric.objects.get(day=day, store=store)
    assert settled.is_active is False
    assert settled.orders_count == 0
    assert settled.gross_sales == Decimal('0.00')
    assert settled.captured_total == Decimal('500.00')
    assert emptied.captured_total == Decimal('500.00')


# --- §19.1 commission & funding ----------------------------------------------


def test_commission_is_taken_on_the_stores_own_net_merchandise():
    """Gross slice subtotal, minus what the STORE paid for — never shipping."""
    admin = _make_user('cmadmin@example.com', group='administrator')
    platform_services.apply_update(
        admin, changes={'commission_rate_percent': Decimal('5.00')}, scope='commission'
    )
    store, _product, order = _paid_order(price='500.00', quantity=2)
    day = timezone.localdate()

    reporting_services.rebuild(start=day, end=day)
    row = DailyStoreMetric.objects.get(day=day, store=store)
    assert row.merchandise == Decimal('1000.00')
    assert row.seller_funded_discount == Decimal('0.00')
    assert row.commission_base == Decimal('1000.00')
    assert row.commission == Decimal('50.00')

    # The platform's cut is the stores' cut — one derivation, never two.
    platform = DailyPlatformMetric.objects.get(day=day)
    assert platform.commission == row.commission
    assert platform.commission_base == row.commission_base
    assert platform.commission_rate_percent == Decimal('5.00')


def test_only_seller_funded_discounts_shrink_the_commission_base():
    """A platform-funded discount was never the store's revenue (§16.3)."""
    admin = _make_user('fundadmin@example.com', group='administrator')
    platform_services.apply_update(
        admin, changes={'commission_rate_percent': Decimal('10.00')}, scope='commission'
    )
    store, _product, order = _paid_order(price='1000.00')
    buyer = order.user
    day = timezone.localdate()

    platform_campaign = Campaign.objects.create(
        scope=PromotionScope.PLATFORM, name='Platform-wide sale'
    )
    platform_rule = Promotion.objects.create(
        campaign=platform_campaign,
        kind=PromotionKind.PRODUCT_DISCOUNT,
        label='10% off',
        value=Decimal('10.00'),
    )
    PromotionUsage.objects.create(
        promotion=platform_rule,
        user=buyer,
        order=order,
        store=store,
        discount_amount=Decimal('100.00'),
    )

    reporting_services.rebuild(start=day, end=day)
    row = DailyStoreMetric.objects.get(day=day, store=store)
    # The platform's own money does not reduce what the store owes.
    assert row.promotion_discount == Decimal('0.00')
    assert row.commission_base == Decimal('1000.00')
    assert row.commission == Decimal('100.00')

    seller_campaign = Campaign.objects.create(
        scope=PromotionScope.SELLER, store=store, name='Store sale'
    )
    seller_rule = Promotion.objects.create(
        campaign=seller_campaign,
        kind=PromotionKind.PRODUCT_DISCOUNT,
        label='10% off',
        value=Decimal('10.00'),
    )
    PromotionUsage.objects.create(
        promotion=seller_rule,
        user=buyer,
        order=order,
        store=store,
        discount_amount=Decimal('100.00'),
    )

    reporting_services.rebuild(start=day, end=day)
    row = DailyStoreMetric.objects.get(day=day, store=store)
    # Now the store is paying for part of its own sale, so its base shrinks.
    assert row.promotion_discount == Decimal('100.00')
    assert row.seller_funded_discount == Decimal('100.00')
    assert row.commission_base == Decimal('900.00')
    assert row.commission == Decimal('90.00')


def test_commission_keeps_the_rate_that_was_in_force_at_capture():
    """A later rate change cannot rewrite a settled day (§6 v1.16)."""
    admin = _make_user('rateadmin@example.com', group='administrator')
    platform_services.apply_update(
        admin, changes={'commission_rate_percent': Decimal('5.00')}, scope='commission'
    )
    store, _product, order = _paid_order(price='1000.00')

    # Finance raises the rate after the money was already captured.
    platform_services.apply_update(
        admin, changes={'commission_rate_percent': Decimal('9.00')}, scope='commission'
    )

    day = timezone.localdate()
    reporting_services.rebuild(start=day, end=day)
    row = DailyStoreMetric.objects.get(day=day, store=store)
    assert row.commission_base == Decimal('1000.00')
    # Charged at 5% — the rate in force when the capture landed.
    assert row.commission == Decimal('50.00')
    # The column records the rate the day closed on, which is a different
    # question from the rate this slice was charged at.
    assert row.commission_rate_percent == Decimal('9.00')


# --- §19.1 refunds -----------------------------------------------------------


def test_refund_reverses_revenue_and_lands_on_the_returning_store():
    """A refund takes its money back off the day it settled, per store."""
    store, _product, order = _paid_order(price='400.00')
    day = timezone.localdate()
    reporting_services.rebuild(start=day, end=day)
    assert DailyPlatformMetric.objects.get(day=day).revenue == Decimal('400.00')

    finance = _make_user('refundfinance@example.com', group='finance')
    payment_services.refund(
        order.payment, Decimal('150.00'), reason='Arrived damaged', actor=finance
    )

    reporting_services.rebuild(start=day, end=day)
    platform = DailyPlatformMetric.objects.get(day=day)
    row = DailyStoreMetric.objects.get(day=day, store=store)

    assert platform.refunded_total == Decimal('150.00')
    assert platform.revenue == Decimal('250.00')
    # A refund with no return case behind it is charged across the order's
    # stores by what each was captured for — here, all of it.
    assert row.refunded_total == Decimal('150.00')
    assert row.revenue == Decimal('250.00')
    # The parts always re-add to the whole: no cent is invented or lost.
    store_parts = sum(
        DailyStoreMetric.objects.filter(day=day).values_list(
            'refunded_total', flat=True
        ),
        Decimal('0.00'),
    )
    assert store_parts == platform.refunded_total


# --- §19.1 read API ----------------------------------------------------------


def test_summary_serves_the_aggregates_not_the_transactional_tables():
    """The §17 promise, proven: hand-edit the rollup and the API follows it."""
    _paid_order(price='300.00')
    day = timezone.localdate()
    reporting_services.rebuild(start=day, end=day)

    finance = _make_user('apifinance@example.com', group='finance')
    client = _client_for(finance)
    response = client.get(SUMMARY)
    assert response.status_code == 200, response.content
    body = response.json()
    assert body['totals']['orders_count'] == 1
    assert body['totals']['gmv'] == '300.00'
    assert body['totals']['commission'] == '0.00'
    assert body['days'][-1]['day'] == str(day)

    # Rewrite the aggregate by hand: if the endpoint were reading the orders
    # this number would not budge, and a dashboard would be paying for a live
    # OLTP query on every load.
    DailyPlatformMetric.objects.filter(day=day).update(gmv=Decimal('999999.00'))
    mutated = client.get(SUMMARY).json()
    assert mutated['totals']['gmv'] == '999999.00'


def test_analytics_reads_are_group_gated():
    """§4/§6 v1.16: finance owns the money, oversight groups see activity."""
    for group in ('finance', 'administrator'):
        user = _make_user(f'sum{group}@example.com', group=group)
        assert _client_for(user).get(SUMMARY).status_code == 200, group
    for group in ('support', 'operations', 'moderator'):
        user = _make_user(f'sum{group}@example.com', group=group)
        assert _client_for(user).get(SUMMARY).status_code == 403, group
    assert _client_for(_make_user('sumcustomer@example.com')).get(SUMMARY).status_code == 403
    assert Client().get(SUMMARY).status_code == 403

    # Product activity is operational, so the read-only groups that already
    # oversee those records get it — moderator, who owns neither, does not.
    for group in ('support', 'operations', 'finance', 'administrator'):
        user = _make_user(f'prod{group}@example.com', group=group)
        assert _client_for(user).get(PRODUCTS).status_code == 200, group
    moderator = _make_user('prodmoderator@example.com', group='moderator')
    assert _client_for(moderator).get(PRODUCTS).status_code == 403


def test_range_filtering_is_validated_server_side():
    admin = _make_user('rangeadmin@example.com', group='administrator')
    client = _client_for(admin)
    day = timezone.localdate()

    ok = client.get(SUMMARY, {'from': str(day), 'to': str(day)})
    assert ok.status_code == 200, ok.content
    assert ok.json()['start'] == str(day)
    assert ok.json()['end'] == str(day)

    inverted = client.get(
        SUMMARY, {'from': str(day), 'to': str(day - timedelta(days=3))}
    )
    assert inverted.status_code == 400
    assert inverted.json()['error'] == 'invalid_range'

    assert client.get(SUMMARY, {'from': 'yesterday'}).status_code == 400
    assert client.get(
        SUMMARY, {'from': str(day - timedelta(days=400))}
    ).status_code == 400

    # The store drill-down is store-scoped and group-gated like the rest.
    detail = client.get(f'{STORES}1/')
    assert detail.status_code == 200, detail.content
    assert detail.json()['items'] == []
