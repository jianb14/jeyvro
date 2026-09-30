"""Phase 19.2 gate tests — the seller analytics endpoint (§6 v1.16, §19.2).

Contracts proven here:

1. The endpoint is **ownership-scoped**: the store is resolved from the
   session (`Store.user == request.user`), so there is no `store_id` to tamper
   with — one seller can never read another store's figures, a caller with no
   store gets a 404, and everyone else is refused (marketplace-sellers rules
   4/5: the Phase 12 `/seller` dashboard stays untouched; this reads the same
   reporting aggregates the staff drill-down serves).
2. The period figures are the *same aggregates* everywhere: `totals` re-add to
   the store's own `DailyStoreMetric` rows, `days` is byte-for-byte the staff
   store-detail payload, and `rebuild` stays idempotent over the new voucher
   and review columns too.
3. Voucher activity equals the `VoucherUsage` redemption ledger; review
   activity counts **published** reviews only (hidden/flagged stay out, as they
   stay out of `recompute_store_rating`); and a review-only day still earns a
   store row with zeroed money, because a metric read from the rollups must
   exist for every day the records support.
4. Inventory is a **live snapshot** of the stock — labeled as one on the page —
   not a period metric: it follows a stock change without a rebuild.
"""
from datetime import datetime, time, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from django.test import Client
from django.utils import timezone

from apps.accounts.models import User
from apps.catalog import services as catalog_services
from apps.catalog.models import Product, Variant
from apps.orders.models import Order
from apps.payments import services as payment_services
from apps.promotions.models import (
    Voucher,
    VoucherDiscountType,
    VoucherScope,
    VoucherUsage,
)
from apps.reporting import services as reporting_services
from apps.reporting.models import DailyStoreMetric
from apps.reviews.models import Review, ReviewStatus
from apps.stores.models import Store

pytestmark = pytest.mark.django_db

PASSWORD = 'Str0ng!Passw0rd'
ANALYTICS = '/api/v1/seller/analytics/'
STAFF_STORES = '/api/v1/admin/analytics/stores/'
REGISTER = '/api/v1/auth/register'
LOGIN = '/api/v1/auth/login'
ADDRESSES = '/api/v1/auth/addresses/'
CART_ITEMS = '/api/v1/cart/items'
CHECKOUT_ORDERS = '/api/v1/checkout/orders'

ADDRESS_PAYLOAD = {
    'full_name': 'Ana Buyer',
    'phone': '09179876543',
    'line1': '12 Aurora Boulevard',
    'line2': '',
    'city': 'Quezon City',
    'province': 'Metro Manila',
    'postal_code': '1101',
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


def _store(suffix='', price='500.00', fee='0.00'):
    """An active store with one published, stocked variant, owned by a seller.

    `is_seller` is flipped here the way store approval flips it (§4) — the
    permission class reads that flag before the ownership lookup runs.
    """
    seller = _make_user(f'sellana{suffix}@example.com')
    store = Store.objects.create(
        user=seller,
        name=f'Seller Analytics {suffix or "Store"}',
        status=Store.Status.ACTIVE,
        shipping_flat_fee=Decimal(fee),
    )
    seller.is_seller = True
    seller.save(update_fields=['is_seller'])
    product = Product.objects.create(
        store=store,
        title=f'Seller Analytics Product {suffix or "One"}',
        base_price=Decimal(price),
        status=Product.Status.PUBLISHED,
    )
    variant = Variant.objects.create(
        product=product, name='Default', price=Decimal(price), is_default=True
    )
    catalog_services.ensure_inventory(variant, initial_on_hand=20)
    return store, product, variant


def _buy(variant, email, *, quantity=1, voucher_code=''):
    """A checkout driven through the real API, then captured (§9)."""
    client = Client()
    credentials = {'email': email, 'password': PASSWORD}
    assert client.post(
        REGISTER, credentials, content_type='application/json'
    ).status_code == 201
    assert client.post(
        LOGIN, credentials, content_type='application/json'
    ).status_code == 200
    address = client.post(ADDRESSES, ADDRESS_PAYLOAD, content_type='application/json')
    assert address.status_code == 201, address.content
    assert client.post(
        CART_ITEMS,
        {'variant_id': variant.id, 'quantity': quantity},
        content_type='application/json',
    ).status_code == 200
    payload = {'address_id': address.json()['id'], 'payment_method': 'cod'}
    if voucher_code:
        payload['voucher_code'] = voucher_code
    response = client.post(CHECKOUT_ORDERS, payload, content_type='application/json')
    assert response.status_code == 201, response.content

    order = Order.objects.get(number=response.json()['number'])
    payment_services.mark_paid(order.payment, source='test')
    order.refresh_from_db()
    return order


def _voucher(code):
    return Voucher.objects.create(
        scope=VoucherScope.PLATFORM,
        code=code,
        title=f'Seller analytics {code}',
        discount_type=VoucherDiscountType.PERCENTAGE,
        value=Decimal('10.00'),
    )


# --- §19.2 the seller's own numbers -------------------------------------------


def test_totals_readd_to_the_store_rows_and_the_staff_drill_down():
    """One store, two orders: totals == its daily rows == the staff view."""
    store, _product, variant = _store('recon', price='300.00')
    _buy(variant, 'reconbuyer1@example.com')
    _buy(variant, 'reconbuyer2@example.com', quantity=2)
    day = timezone.localdate()
    reporting_services.rebuild(start=day, end=day)

    body = _client_for(store.user).get(ANALYTICS)
    assert body.status_code == 200, body.content
    payload = body.json()
    row = DailyStoreMetric.objects.get(store=store, day=day)

    assert payload['end'] == str(day)
    # No range given: the default window is the trailing 30 days (§8).
    assert payload['start'] == str(day - timedelta(days=29))
    assert payload['totals']['orders_count'] == row.orders_count == 2
    assert payload['totals']['units_sold'] == row.units_sold == 3
    assert payload['totals']['products_sold'] == 1
    assert (
        Decimal(payload['totals']['gross_sales'])
        == row.gross_sales
        == Decimal('900.00')
    )
    assert Decimal(payload['totals']['merchandise']) == row.merchandise
    assert Decimal(payload['totals']['revenue']) == row.revenue
    assert Decimal(payload['totals']['commission']) == row.commission

    # The chart's series is the staff drill-down at the store grain — the same
    # rows, served through the ownership-scoped door.
    finance = _make_user('reconfinance@example.com', group='finance')
    detail = _client_for(finance).get(f'{STAFF_STORES}{store.id}/')
    assert detail.status_code == 200, detail.content
    assert payload['days'] == detail.json()['items']


def test_a_seller_reads_their_own_store_and_nothing_else():
    """No `store_id` exists to forge: the session picks the store (§10.3)."""
    store_a, _product_a, variant_a = _store('iso', price='400.00')
    store_b, _product_b, variant_b = _store('iso2', price='900.00')
    _buy(variant_a, 'isobuyer1@example.com', quantity=2)  # A: 800.00
    _buy(variant_b, 'isobuyer2@example.com')  # B: 900.00
    day = timezone.localdate()
    reporting_services.rebuild(start=day, end=day)

    body = _client_for(store_a.user).get(ANALYTICS)
    assert body.status_code == 200, body.content
    payload = body.json()
    assert {entry['store_id'] for entry in payload['days']} == {store_a.id}
    assert {row['store_id'] for row in payload['top_products']} == {store_a.id}
    assert Decimal(payload['totals']['gross_sales']) == Decimal('800.00')

    other = _client_for(store_b.user).get(ANALYTICS).json()
    assert Decimal(other['totals']['gross_sales']) == Decimal('900.00')

    # A forged query parameter widens nothing — the view never reads one.
    forged = _client_for(store_a.user).get(ANALYTICS, {'store_id': store_b.id}).json()
    assert Decimal(forged['totals']['gross_sales']) == Decimal('800.00')


def test_only_sellers_reach_the_endpoint():
    """`IsAuthenticated, IsSeller`, then 404 when the account owns no store."""
    customer = _make_user('anacustomer@example.com')
    assert _client_for(customer).get(ANALYTICS).status_code == 403

    finance = _make_user('anafinance@example.com', group='finance')
    assert _client_for(finance).get(ANALYTICS).status_code == 403

    # `is_seller` without a store is a broken account, not a dashboard: the
    # ownership lookup finds nothing and the request is a straight 404.
    ghost = _make_user('anaghost@example.com')
    ghost.is_seller = True
    ghost.save(update_fields=['is_seller'])
    assert _client_for(ghost).get(ANALYTICS).status_code == 404

    assert Client().get(ANALYTICS).status_code == 403


def test_the_range_is_validated_server_side():
    """Same `?from=&to=` contract as the staff endpoints (§8: no silent default)."""
    store, _product, _variant = _store('range')
    day = timezone.localdate()
    client = _client_for(store.user)

    ok = client.get(ANALYTICS, {'from': str(day), 'to': str(day)})
    assert ok.status_code == 200, ok.content
    assert ok.json()['start'] == str(day)
    assert ok.json()['end'] == str(day)

    inverted = client.get(
        ANALYTICS, {'from': str(day), 'to': str(day - timedelta(days=3))}
    )
    assert inverted.status_code == 400
    assert inverted.json()['error'] == 'invalid_range'

    assert client.get(ANALYTICS, {'from': 'yesterday'}).status_code == 400
    assert client.get(
        ANALYTICS, {'from': str(day - timedelta(days=400))}
    ).status_code == 400


# --- §19.2 voucher, review and inventory grains -------------------------------


def test_voucher_activity_equals_the_redemption_ledger():
    """The counts and pesos on the page are the `VoucherUsage` rows, no more."""
    store, _product, variant = _store('voucher', price='1000.00')
    _voucher('VCHA10')  # 10% → 100.00 off this single-store order
    order = _buy(variant, 'voucherbuyer@example.com', voucher_code='VCHA10')
    day = timezone.localdate()
    reporting_services.rebuild(start=day, end=day)

    usage = VoucherUsage.objects.get(order=order)
    row = DailyStoreMetric.objects.get(store=store, day=day)
    assert row.voucher_redemptions == 1
    assert row.voucher_discount == usage.discount_amount == Decimal('100.00')

    totals = _client_for(store.user).get(ANALYTICS).json()['totals']
    assert totals['voucher_redemptions'] == VoucherUsage.objects.count() == 1
    # The apportioned discount re-adds to the ledger's order-level figure.
    assert Decimal(totals['voucher_discount']) == usage.discount_amount


def test_reviews_count_published_reviews_and_only_those():
    """Hidden and flagged rows leave the figures as they leave the public list."""
    store, product, variant = _store('reviews')
    order = _buy(variant, 'revbuyer1@example.com')
    day = timezone.localdate()

    # One published review by the actual buyer...
    Review.objects.create(
        user=order.user,
        product=product,
        store=store,
        order=order,
        rating=4,
        body='Exactly as described.',
    )
    # ...and the other moderation states, which must not count. The model only
    # enforces (user, product); eligibility itself lives in the review service,
    # which these reporting fixtures deliberately bypass (same as §19.1's).
    for index, state in enumerate((ReviewStatus.HIDDEN, ReviewStatus.FLAGGED), start=2):
        Review.objects.create(
            user=_make_user(f'revextra{index}@example.com'),
            product=product,
            store=store,
            order=order,
            rating=1,
            body=f'Review in state {state}.',
            status=state,
        )

    reporting_services.rebuild(start=day, end=day)
    row = DailyStoreMetric.objects.get(store=store, day=day)
    assert row.reviews_count == 1
    assert row.reviews_rating_sum == Decimal('4.00')

    totals = _client_for(store.user).get(ANALYTICS).json()['totals']
    assert totals['reviews_count'] == 1
    assert Decimal(totals['reviews_rating_sum']) == Decimal('4.00')
    assert Decimal(totals['review_rating_avg']) == Decimal('4.00')


def test_a_review_only_day_keeps_a_zero_money_store_row():
    """A day the records support must exist on the page — money zeroed (§19.2)."""
    store, product, variant = _store('rod')
    order = _buy(variant, 'rodbuyer@example.com')
    day = timezone.localdate()
    yesterday = day - timedelta(days=1)

    review = Review.objects.create(
        user=order.user,
        product=product,
        store=store,
        order=order,
        rating=5,
        body='Arrived a day early.',
    )
    # Backdate the review: yesterday carried no order for this store, so the
    # day earns its row from the review alone.
    Review.objects.filter(pk=review.pk).update(
        created_at=timezone.make_aware(
            datetime.combine(yesterday, time(12, 0))
        )
    )
    reporting_services.rebuild(start=yesterday, end=day)

    row = DailyStoreMetric.objects.get(store=store, day=yesterday)
    assert row.reviews_count == 1
    assert row.reviews_rating_sum == Decimal('5.00')
    assert row.orders_count == 0
    assert row.gross_sales == Decimal('0.00')
    assert row.revenue == Decimal('0.00')
    assert row.is_active is False

    payload = _client_for(store.user).get(
        ANALYTICS, {'from': str(yesterday), 'to': str(day)}
    ).json()
    # The series carries both days; the totals re-add across them.
    assert [(entry['day'], entry['reviews_count']) for entry in payload['days']] == [
        (str(yesterday), 1),
        (str(day), 0),
    ]
    assert payload['totals']['reviews_count'] == 1
    assert payload['totals']['orders_count'] == 1


def test_inventory_is_the_live_snapshot_of_the_stock():
    """A snapshot, not a metric: it follows stock changes with no rebuild."""
    store, _product, variant = _store('inv', price='250.00')
    _buy(variant, 'invbuyer@example.com')  # 20 − 1 = 19 on hand
    day = timezone.localdate()
    reporting_services.rebuild(start=day, end=day)

    client = _client_for(store.user)
    snapshot = client.get(ANALYTICS).json()['inventory']
    assert snapshot == {
        'variants_tracked': 1,
        'low_stock_count': 0,
        'out_of_stock_count': 0,
        'units_on_hand': 19,
    }

    # Sell the shelf down through the real ledger after the rebuild: the next
    # read shows today's truth without waiting for `rebuild_reporting`.
    catalog_services.adjust_stock(store.user, variant, delta=-19)
    live = client.get(ANALYTICS).json()['inventory']
    assert live['units_on_hand'] == 0
    assert live['out_of_stock_count'] == 1
    assert live['low_stock_count'] == 1  # available ≤ the variant's threshold


def test_best_sellers_are_store_scoped_and_respect_the_limit():
    """Units first, only this seller's shelf, bounded by `?limit=` (§8)."""
    store, product, variant = _store('best', price='150.00')
    runner_up = Product.objects.create(
        store=store,
        title='Seller Analytics Runner Up',
        base_price=Decimal('150.00'),
        status=Product.Status.PUBLISHED,
    )
    runner_variant = Variant.objects.create(
        product=runner_up, name='Default', price=Decimal('150.00'), is_default=True
    )
    catalog_services.ensure_inventory(runner_variant, initial_on_hand=20)

    _buy(variant, 'bestbuyer1@example.com', quantity=3)
    _buy(runner_variant, 'bestbuyer2@example.com')
    day = timezone.localdate()
    reporting_services.rebuild(start=day, end=day)

    client = _client_for(store.user)
    payload = client.get(ANALYTICS).json()
    rows = payload['top_products']
    assert [row['product_id'] for row in rows] == [product.id, runner_up.id]
    assert rows[0]['units_sold'] == 3
    assert rows[1]['units_sold'] == 1
    assert {row['store_id'] for row in rows} == {store.id}
    assert payload['totals']['products_sold'] == 2

    limited = client.get(ANALYTICS, {'limit': 1}).json()
    assert [row['product_id'] for row in limited['top_products']] == [product.id]


def test_rebuild_stays_idempotent_over_the_new_columns():
    """Same rows, same pks — the voucher and review grains re-derive exactly."""
    store, product, variant = _store('idem', price='800.00')
    _voucher('IDEM10')
    order = _buy(variant, 'idembuyer@example.com', voucher_code='IDEM10')
    Review.objects.create(
        user=order.user,
        product=product,
        store=store,
        order=order,
        rating=3,
        body='Fair for the price.',
    )
    day = timezone.localdate()

    reporting_services.rebuild(start=day, end=day)
    first = DailyStoreMetric.objects.get(store=store, day=day)

    reporting_services.rebuild(start=day, end=day)
    again = DailyStoreMetric.objects.get(store=store, day=day)
    assert again.pk == first.pk
    assert again.voucher_redemptions == first.voucher_redemptions == 1
    assert again.voucher_discount == first.voucher_discount == Decimal('80.00')
    assert again.reviews_count == first.reviews_count == 1
    assert again.reviews_rating_sum == first.reviews_rating_sum == Decimal('3.00')
    # A platform-funded voucher never moves the store's own gross (§16.3): the
    # slice's snapshot total stays at the 800.00 it sold, while the 80.00 the
    # platform paid rides `voucher_discount` instead.
    assert again.gross_sales == first.gross_sales == Decimal('800.00')




