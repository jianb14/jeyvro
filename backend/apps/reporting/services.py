"""Reporting derivation (Phase 19 — PROJECT_CONTEXT §6 v1.16).

`rebuild` is the **only writer** of the three rollup tables, and it is
idempotent: running it twice over the same range leaves the same rows, because
every number is derived from the transactional records and nothing is
accumulated in place. That is what makes the §19 gate — "the metrics reconcile
with the transactional data" — something the command can prove rather than
assert.

Two grains share one row, deliberately:

* **Placement columns** (`orders_count`, `units_sold`, `merchandise`,
  `shipping`, `discounts`, `gross_sales`) answer *what was ordered that day*,
  read from the day's order snapshots.
* **Cash columns** (`captured_total`, `refunded_total`, `revenue`) answer
  *what money moved that day*, read from the append-only ledger.
* **Commission follows the cash, not the badge**: it is computed only on
  slices whose capture landed that day (§6 v1.16), so an order placed Monday
  and paid Wednesday pays commission into Wednesday.

The commission rate is the rate **in force at the moment the money was
captured**, recovered from the settings audit trail (`AuditLog` keeps every
`commission_rate_percent` change with its `from`/`to`), so changing the rate
tomorrow can never rewrite a settled day. With no audited change at all the
current row is the only rate there has ever been.
"""
from collections import defaultdict
from datetime import datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Count, Max, Min, Q, Sum
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.orders.models import Order, OrderItem, OrderStatus, SellerOrder
from apps.payments.models import PaymentTransaction
from apps.platform import services as platform_services
from apps.promotions.models import PromotionScope, PromotionUsage, VoucherUsage
from apps.reviews.models import Review, ReviewStatus

from .models import DailyPlatformMetric, DailyProductMetric, DailyStoreMetric

CENT = Decimal('0.01')
ZERO = Decimal('0.00')
HUNDRED = Decimal('100')

RATE_ACTION = 'platform_settings_update'
RATE_FIELD = 'commission_rate_percent'


def _money(value):
    """Coerce a possibly-null aggregate into a quantized peso amount."""
    return (value or ZERO).quantize(CENT)


def commission_for(base, rate_percent):
    """The platform's cut — half-up, the odd cent on the platform's side.

    Same convention as shared voucher funding (§16.3): a cent is never lost
    and never invented.
    """
    if base <= 0 or rate_percent <= 0:
        return ZERO
    return (base * rate_percent / HUNDRED).quantize(CENT, rounding=ROUND_HALF_UP)


def _apportion(amount, weights):
    """Split `amount` across keys in proportion to `weights`, exactly.

    The rounding drift goes to the largest weight, so the parts always re-add
    to the amount being split — the ledger's own arithmetic rule (§16.3).
    """
    total = sum(weights.values())
    if amount <= 0 or total <= 0:
        return {}
    parts = {
        key: (amount * weight / total).quantize(CENT, rounding=ROUND_HALF_UP)
        for key, weight in weights.items()
    }
    drift = amount - sum(parts.values())
    if drift != ZERO:
        parts[max(weights, key=lambda key: weights[key])] += drift
    return parts


# --- The commission rate as it stood, from the audit trail -------------------


def _rate_changes():
    """Every audited commission-rate change, oldest first."""
    rows = (
        AuditLog.objects.filter(
            action=RATE_ACTION, detail__changes__has_key=RATE_FIELD
        )
        .order_by('created_at')
        .values_list('created_at', 'detail')
    )
    changes = []
    for created_at, detail in rows:
        change = detail['changes'][RATE_FIELD]
        changes.append(
            (created_at, Decimal(str(change['to'])), Decimal(str(change['from'])))
        )
    return changes


def _rate_at(moment, changes, current):
    """The rate that applied at `moment` (§6 v1.16 — never rewrite history)."""
    rate = None
    for changed_at, to_value, from_value in changes:
        if changed_at <= moment:
            rate = to_value
        else:
            # The first change after `moment`: whatever it came *from* is what
            # was in force before it.
            return rate if rate is not None else from_value
    return rate if rate is not None else current


# --- Source queries ----------------------------------------------------------


def _live_orders(day):
    """Orders placed that day that were not cancelled (§19 GMV definition)."""
    return Order.objects.filter(created_at__date=day).exclude(
        status=OrderStatus.CANCELLED
    )


def _live_slices(day):
    """Store slices of the day's live orders — the merchant grain.

    A slice cancelled on its own (or by its parent) did not sell anything, so
    it stays out of the store's merchandise columns.
    """
    return (
        SellerOrder.objects.filter(order__created_at__date=day)
        .exclude(
            Q(status=OrderStatus.CANCELLED) | Q(order__status=OrderStatus.CANCELLED)
        )
        .select_related('store')
    )


def _voucher_shares(day):
    """{(order_id, store_id): pesos the STORE absorbed of a voucher (§16.3)}."""
    shares = defaultdict(lambda: ZERO)
    rows = (
        VoucherUsage.objects.filter(order__created_at__date=day, store__isnull=False)
        .exclude(order__status=OrderStatus.CANCELLED)
        .values('order_id', 'store_id')
        .annotate(amount=Sum('seller_amount'))
    )
    for row in rows:
        shares[(row['order_id'], row['store_id'])] += _money(row['amount'])
    return shares


def _voucher_activity(day):
    """{(order_id, store_id): {'redemptions', 'discount'}} for the day (§19.2).

    A redemption counts for **every store whose live slices the order
    carried** — the voucher was used on their goods — and the discount (an
    order-level figure) is apportioned across those stores in proportion to
    their subtotals, the same "the parts re-add to the whole" rule the refund
    arithmetic uses. A zero-value order still redeems: the count is real even
    when there is no merchandise to carry the discount.
    """
    usages = list(
        VoucherUsage.objects.filter(order__created_at__date=day)
        .exclude(order__status=OrderStatus.CANCELLED)
        .values('order_id', 'discount_amount')
    )
    if not usages:
        return {}

    weights = defaultdict(lambda: defaultdict(lambda: ZERO))
    slices = (
        SellerOrder.objects.filter(
            order_id__in=[usage['order_id'] for usage in usages]
        )
        .exclude(
            Q(status=OrderStatus.CANCELLED) | Q(order__status=OrderStatus.CANCELLED)
        )
        .values('order_id', 'store_id', 'subtotal')
    )
    for line in slices:
        weights[line['order_id']][line['store_id']] += line['subtotal']

    activity = {}
    for usage in usages:
        order_weights = weights.get(usage['order_id'], {})
        parts = _apportion(_money(usage['discount_amount']), order_weights)
        if not parts and order_weights:
            parts = {store_id: ZERO for store_id in order_weights}
        for store_id, part in parts.items():
            row = activity.setdefault(
                (usage['order_id'], store_id), {'redemptions': 0, 'discount': ZERO}
            )
            row['redemptions'] += 1
            row['discount'] += part
    return activity


def _review_rows(day):
    """{store_id: (count, rating_sum)} of the day's published reviews (§19.2).

    Hidden and flagged rows stay out of the metric exactly as they stay out of
    `recompute_store_rating` (§6): moderation pulls a review off the record
    and off the figures with it.
    """
    rows = (
        Review.objects.filter(created_at__date=day, status=ReviewStatus.PUBLISHED)
        .values('store_id')
        .annotate(reviews=Count('id'), rating_sum=Sum('rating'))
    )
    return {
        row['store_id']: (row['reviews'], Decimal(row['rating_sum']))
        for row in rows
    }


def _promotion_shares(day):
    """{(order_id, store_id): pesos of seller-scoped campaign discounts}.

    Funding follows ownership: a campaign belongs to the platform or to one
    store (`Campaign.scope`), so a seller-scoped campaign's discount comes out
    of that store's own revenue and reduces what commission is taken on. A
    platform-scoped campaign was never the store's money (§6 v1.16).
    """
    shares = defaultdict(lambda: ZERO)
    rows = (
        PromotionUsage.objects.filter(
            order__created_at__date=day,
            promotion__campaign__scope=PromotionScope.SELLER,
        )
        .exclude(order__status=OrderStatus.CANCELLED)
        .values('order_id', 'store_id')
        .annotate(amount=Sum('discount_amount'))
    )
    for row in rows:
        shares[(row['order_id'], row['store_id'])] += _money(row['amount'])
    return shares


def _ledger(day):
    """The day's ledger rows, split into captures and refund debits."""
    rows = PaymentTransaction.objects.filter(created_at__date=day)
    captures = rows.filter(
        kind=PaymentTransaction.Kind.CAPTURE,
        direction=PaymentTransaction.Direction.CREDIT,
    )
    refunds = rows.filter(
        kind=PaymentTransaction.Kind.REFUND,
        direction=PaymentTransaction.Direction.DEBIT,
    ).select_related('refund__return_case', 'payment__order')
    return captures, refunds


def _refunds_by_store(refunds):
    """Attribute each refund debit to the stores it actually came out of.

    The ledger records a refund against the *payment*, not a store (a refund
    is money back to the customer for the whole order), so the store split is
    derived:

    * a refund that followed a return case is charged to the stores owning the
      case's returned lines, in proportion to those lines' value — the store
      whose goods came back wears the refund;
    * a refund with no case behind it (a manual staff settlement) has no line
      story to read, so it is charged across the order's stores in proportion
      to what each was captured for.

    Either way the parts re-add to the refund exactly.
    """
    totals = defaultdict(lambda: ZERO)
    for row in refunds:
        case = row.refund.return_case if row.refund_id else None
        weights = defaultdict(lambda: ZERO)

        if case is not None:
            for item in case.items.select_related('order_item'):
                weights[item.order_item.seller_order_id] += (
                    item.order_item.unit_price * item.quantity
                )

        if not weights:
            captures = (
                PaymentTransaction.objects.filter(
                    payment=row.payment,
                    kind=PaymentTransaction.Kind.CAPTURE,
                    direction=PaymentTransaction.Direction.CREDIT,
                )
                .exclude(seller_order__isnull=True)
                .values('seller_order__store_id')
                .annotate(amount=Sum('amount'))
            )
            for capture in captures:
                weights[capture['seller_order__store_id']] += _money(capture['amount'])

        for store_id, part in _apportion(_money(row.amount), weights).items():
            totals[store_id] += part
    return totals


def _day_end(day):
    """The last instant of a local calendar day (§10: Manila days)."""
    return timezone.make_aware(datetime.combine(day, time.max))


def _empty_store_row(rate):
    """A zeroed store-day — the shape every later addend fills in."""
    return {
        'orders_count': 0,
        'units_sold': 0,
        'products_sold': 0,
        'is_active': False,
        'merchandise': ZERO,
        'shipping': ZERO,
        'promotion_discount': ZERO,
        'voucher_seller_share': ZERO,
        'voucher_discount': ZERO,
        'voucher_redemptions': 0,
        'reviews_count': 0,
        'reviews_rating_sum': ZERO,
        'seller_funded_discount': ZERO,
        'gross_sales': ZERO,
        'captured_total': ZERO,
        'refunded_total': ZERO,
        'revenue': ZERO,
        'commission_base': ZERO,
        'commission': ZERO,
        'commission_rate_percent': rate,
        '_products': set(),
    }


def _store_rows(day, changes, current_rate):
    """{store_id: defaults} for every store that sold, was paid, or was
    reviewed that day (§19.1 extended by §19.2).

    A review-only day still produces a row — money zeroed — because a metric
    read from the rollups must exist for every day the records support, not
    only the days an order landed (§19.2 "review metrics").
    """
    rows = {}

    def row_for(store_id):
        return rows.setdefault(store_id, _empty_store_row(current_rate))

    voucher_shares = _voucher_shares(day)
    promotion_shares = _promotion_shares(day)

    # --- Placement grain: what this store sold that day --------------------
    for seller_order in _live_slices(day):
        row = row_for(seller_order.store_id)
        row['orders_count'] += 1
        row['is_active'] = True
        row['merchandise'] += seller_order.subtotal
        row['shipping'] += seller_order.shipping_fee
        row['gross_sales'] += seller_order.total
        # The store's own funding, per order (§16.3).
        row['voucher_seller_share'] += voucher_shares.get(
            (seller_order.order_id, seller_order.store_id), ZERO
        )
        row['promotion_discount'] += promotion_shares.get(
            (seller_order.order_id, seller_order.store_id), ZERO
        )

    # --- Redemption grain: the vouchers this store's orders carried (§19.2) -
    for (_order_id, store_id), activity in _voucher_activity(day).items():
        row = row_for(store_id)
        row['voucher_redemptions'] += activity['redemptions']
        row['voucher_discount'] += activity['discount']

    line_rows = (
        OrderItem.objects.filter(seller_order__order__created_at__date=day)
        .exclude(
            Q(seller_order__status=OrderStatus.CANCELLED)
            | Q(seller_order__order__status=OrderStatus.CANCELLED)
        )
        .values('seller_order__store_id', 'product_id')
        .annotate(units=Sum('quantity'))
    )
    for line in line_rows:
        row = row_for(line['seller_order__store_id'])
        row['units_sold'] += line['units'] or 0
        row['_products'].add(line['product_id'])

    # --- Cash grain: what was collected and given back that day ------------
    captures, refunds = _ledger(day)
    captured_rows = (
        captures.exclude(seller_order__isnull=True)
        .values('seller_order__store_id')
        .annotate(amount=Sum('amount'))
    )
    for capture in captured_rows:
        row_for(capture['seller_order__store_id'])['captured_total'] += _money(
            capture['amount']
        )
    for store_id, amount in _refunds_by_store(refunds).items():
        row_for(store_id)['refunded_total'] += amount

    # --- Commission: earned on capture, at the rate then in force ----------
    moments = {}
    for entry in (
        captures.exclude(seller_order__isnull=True)
        .values('seller_order_id', 'created_at')
    ):
        seen = moments.get(entry['seller_order_id'])
        if seen is None or entry['created_at'] > seen:
            moments[entry['seller_order_id']] = entry['created_at']

    for slice_id, captured_at in moments.items():
        seller_order = SellerOrder.objects.select_related('store').get(pk=slice_id)
        store_id = seller_order.store_id
        funded = voucher_shares.get(
            (seller_order.order_id, store_id), ZERO
        ) + promotion_shares.get((seller_order.order_id, store_id), ZERO)
        base = max(ZERO, seller_order.subtotal - funded)
        row = row_for(store_id)
        row['commission_base'] += base
        row['commission'] += commission_for(
            base, _rate_at(captured_at, changes, current_rate)
        )

    # --- Voice grain: what customers said about the store that day (§19.2) --
    for store_id, (reviews, rating_sum) in _review_rows(day).items():
        row = row_for(store_id)
        row['reviews_count'] += reviews
        row['reviews_rating_sum'] += rating_sum

    # --- Finalize: exact money, derived columns, no private keys -----------
    for row in rows.values():
        row['products_sold'] = len(row.pop('_products'))
        row['voucher_seller_share'] = _money(row['voucher_seller_share'])
        row['voucher_discount'] = _money(row['voucher_discount'])
        row['reviews_rating_sum'] = row['reviews_rating_sum'].quantize(CENT)
        row['promotion_discount'] = _money(row['promotion_discount'])
        row['seller_funded_discount'] = (
            row['voucher_seller_share'] + row['promotion_discount']
        )
        for field in (
            'merchandise',
            'shipping',
            'gross_sales',
            'captured_total',
            'refunded_total',
            'commission_base',
            'commission',
        ):
            row[field] = _money(row[field])
        row['revenue'] = row['captured_total'] - row['refunded_total']
    return rows


def _platform_metrics(day, store_rows, end_rate):
    """The marketplace's day — volume from the orders, cash from the ledger.

    Commission is summed from the store rows rather than recomputed here: the
    platform's cut *is* what the stores owe, so one derivation keeps the two
    grains from ever disagreeing.
    """
    orders = _live_orders(day)
    totals = orders.aggregate(
        gmv=Sum('grand_total'),
        merchandise=Sum('subtotal'),
        shipping=Sum('shipping_total'),
        promotion=Sum('promotion_discount'),
        voucher=Sum('discount_total'),
    )
    captures, refunds = _ledger(day)
    captured_total = _money(captures.aggregate(total=Sum('amount'))['total'])
    refunded_total = _money(refunds.aggregate(total=Sum('amount'))['total'])

    return {
        'orders_count': orders.count(),
        'orders_cancelled': Order.objects.filter(
            created_at__date=day, status=OrderStatus.CANCELLED
        ).count(),
        'orders_paid': captures.values('payment_id').distinct().count(),
        'units_sold': sum(row['units_sold'] for row in store_rows.values()),
        'products_sold': sum(row['products_sold'] for row in store_rows.values()),
        'active_customers': orders.values('user_id').distinct().count(),
        'active_sellers': sum(1 for row in store_rows.values() if row['is_active']),
        'gmv': _money(totals['gmv']),
        'merchandise': _money(totals['merchandise']),
        'shipping': _money(totals['shipping']),
        'discounts': _money(
            (totals['promotion'] or ZERO) + (totals['voucher'] or ZERO)
        ),
        'captured_total': captured_total,
        'refunded_total': refunded_total,
        'revenue': captured_total - refunded_total,
        'commission_base': _money(
            sum((row['commission_base'] for row in store_rows.values()), ZERO)
        ),
        'commission': _money(
            sum((row['commission'] for row in store_rows.values()), ZERO)
        ),
        'commission_rate_percent': end_rate,
    }


def _product_rows(day):
    """{(store_id, product_id): defaults} — product activity for the day."""
    rows = {}
    lines = (
        OrderItem.objects.filter(seller_order__order__created_at__date=day)
        .exclude(
            Q(seller_order__status=OrderStatus.CANCELLED)
            | Q(seller_order__order__status=OrderStatus.CANCELLED)
        )
        .values('seller_order__store_id', 'seller_order__order_id', 'product_id')
        .annotate(units=Sum('quantity'), merchandise=Sum('line_total'))
    )
    for line in lines:
        key = (line['seller_order__store_id'], line['product_id'])
        row = rows.setdefault(
            key, {'units_sold': 0, 'merchandise': ZERO, '_orders': set()}
        )
        row['units_sold'] += line['units'] or 0
        row['merchandise'] += line['merchandise'] or ZERO
        row['_orders'].add(line['seller_order__order_id'])

    for row in rows.values():
        row['orders_count'] = len(row.pop('_orders'))
        row['merchandise'] = _money(row['merchandise'])
    return rows


def _sync_stores(day, rows):
    """Make the day's store rows match exactly what was derived — no more."""
    stale = set(
        DailyStoreMetric.objects.filter(day=day).values_list('store_id', flat=True)
    ) - set(rows)
    if stale:
        DailyStoreMetric.objects.filter(day=day, store_id__in=stale).delete()
    for store_id, defaults in rows.items():
        DailyStoreMetric.objects.update_or_create(
            day=day, store_id=store_id, defaults=defaults
        )


def _sync_products(day, rows):
    """Same for product activity: rows the derivation no longer produces go."""
    stale = set(
        DailyProductMetric.objects.filter(day=day).values_list(
            'store_id', 'product_id'
        )
    ) - set(rows)
    for store_id, product_id in stale:
        DailyProductMetric.objects.filter(
            day=day, store_id=store_id, product_id=product_id
        ).delete()
    for (store_id, product_id), defaults in rows.items():
        DailyProductMetric.objects.update_or_create(
            day=day, store_id=store_id, product_id=product_id, defaults=defaults
        )


def _rebuild_day(day, changes, current_rate):
    """Recompute one day, end to end."""
    store_rows = _store_rows(day, changes, current_rate)
    product_rows = _product_rows(day)
    # A day normally lives under one rate. If finance changed the rate mid-day
    # each slice was still charged at its own capture-time rate; the column
    # records the rate the day ended on (§6 v1.16).
    end_rate = _rate_at(_day_end(day), changes, current_rate)
    for row in store_rows.values():
        row['commission_rate_percent'] = end_rate

    with transaction.atomic():
        DailyPlatformMetric.objects.update_or_create(
            day=day, defaults=_platform_metrics(day, store_rows, end_rate)
        )
        _sync_stores(day, store_rows)
        _sync_products(day, product_rows)


def _data_window():
    """The window the records actually cover, ending no earlier than today.

    Reviews count as records too: a review-only day (a product reviewed long
    after its orders settled) still gets a store row, so the default rebuild
    range must reach back to the first review when that is the earliest fact
    (§19.2).
    """
    first = last = None
    for model in (Order, PaymentTransaction, Review):
        window = model.objects.aggregate(
            first=Min('created_at'), last=Max('created_at')
        )
        if window['first'] is None:
            continue
        start = timezone.localtime(window['first']).date()
        finish = timezone.localtime(window['last']).date()
        first = start if first is None or start < first else first
        last = finish if last is None or finish > last else last
    today = timezone.localdate()
    if first is None:
        return today, today
    return first, max(last, today)


def rebuild(*, start=None, end=None):
    """Rebuild the rollup tables for a day range (§19.1).

    Idempotent by construction: every row is recomputed from the records, so
    running this twice over the same range leaves the same numbers, and a
    range recomputed after a refund lands picks the refund up. Raises
    `ValueError` on an inverted or unusable range — the caller turns that into
    a 400.
    """
    first_day, last_day = _data_window()
    start = start or first_day
    end = end or last_day
    if end < start:
        raise ValueError('The end of the range cannot precede its start.')

    changes = _rate_changes()
    current_rate = Decimal(
        str(platform_services.get_settings().commission_rate_percent)
    )
    days = [
        start + timedelta(days=offset)
        for offset in range((end - start).days + 1)
    ]
    for day in days:
        _rebuild_day(day, changes, current_rate)

    return {
        'start': start,
        'end': end,
        'days': len(days),
        'stores': DailyStoreMetric.objects.filter(day__range=(start, end))
        .values('store_id')
        .distinct()
        .count(),
        'products': DailyProductMetric.objects.filter(day__range=(start, end))
        .values('product_id')
        .distinct()
        .count(),
    }


# --- Reads ------------------------------------------------------------------
#
# Dashboards call these and nothing else: every number below comes out of the
# rollup tables, so a busy marketplace never pays for a live OLTP query (§17).


def platform_series(start, end):
    """The marketplace's daily rows in order — the chart's own data."""
    return DailyPlatformMetric.objects.filter(
        day__range=(start, end)
    ).order_by('day')


def store_series(store_id, start, end):
    """One store's daily rows in order (§19.2 drill-down)."""
    return (
        DailyStoreMetric.objects.filter(day__range=(start, end), store_id=store_id)
        .select_related('store')
        .order_by('day')
    )


def _clamp(start, end):
    """Never serve a window the rollups do not cover yet."""
    first = DailyPlatformMetric.objects.order_by('day').values_list('day', flat=True).first()
    if first is None:
        return None, None
    return max(start, first), end


def platform_totals(start, end):
    """Range totals, summed from the daily rows.

    Columns that do not add up across days are named for what they are:
    `customer_days` and `seller_days` are sums of the daily active counts (a
    customer who ordered on three days is three customer-days), while the
    exact per-day figures ride the series. `products_sold` is the distinct
    count, taken from the product rows rather than summed from days.
    """
    start, end = _clamp(start, end)
    if start is None:
        return _empty_totals()

    totals = DailyPlatformMetric.objects.filter(day__range=(start, end)).aggregate(
        orders_count=Sum('orders_count'),
        orders_cancelled=Sum('orders_cancelled'),
        orders_paid=Sum('orders_paid'),
        units_sold=Sum('units_sold'),
        customer_days=Sum('active_customers'),
        seller_days=Sum('active_sellers'),
        gmv=Sum('gmv'),
        merchandise=Sum('merchandise'),
        shipping=Sum('shipping'),
        discounts=Sum('discounts'),
        captured_total=Sum('captured_total'),
        refunded_total=Sum('refunded_total'),
        revenue=Sum('revenue'),
        commission_base=Sum('commission_base'),
        commission=Sum('commission'),
    )
    for key, value in totals.items():
        if key not in ('orders_count', 'orders_cancelled', 'orders_paid', 'units_sold',
                       'customer_days', 'seller_days'):
            totals[key] = _money(value)
    for key in ('orders_count', 'orders_cancelled', 'orders_paid', 'units_sold',
                'customer_days', 'seller_days'):
        totals[key] = totals[key] or 0
    totals['products_sold'] = (
        DailyProductMetric.objects.filter(day__range=(start, end))
        .values('product_id')
        .distinct()
        .count()
    )
    totals['start'] = start
    totals['end'] = end
    return totals


def _empty_totals():
    """The shape a dashboard can always render, even with no data yet."""
    zero = ZERO
    return {
        'start': None, 'end': None,
        'orders_count': 0, 'orders_cancelled': 0, 'orders_paid': 0,
        'units_sold': 0, 'products_sold': 0, 'customer_days': 0, 'seller_days': 0,
        'gmv': zero, 'merchandise': zero, 'shipping': zero, 'discounts': zero,
        'captured_total': zero, 'refunded_total': zero, 'revenue': zero,
        'commission_base': zero, 'commission': zero,
    }


def store_totals(store_id, start, end):
    """One store's range totals, summed from its daily rows (§19.2).

    The mirror of `platform_totals` at the store grain: `products_sold` is the
    distinct count taken from the product rows (a product sold on three days is
    one product), and `review_rating_avg` is derived from the summed reviews —
    None, not zero, when there are none, because "no rating yet" is not a
    rating of zero.
    """
    start, end = _clamp(start, end)
    if start is None:
        return _empty_store_totals()

    totals = DailyStoreMetric.objects.filter(
        store_id=store_id, day__range=(start, end)
    ).aggregate(
        orders_count=Sum('orders_count'),
        units_sold=Sum('units_sold'),
        voucher_redemptions=Sum('voucher_redemptions'),
        reviews_count=Sum('reviews_count'),
        reviews_rating_sum=Sum('reviews_rating_sum'),
        gross_sales=Sum('gross_sales'),
        merchandise=Sum('merchandise'),
        shipping=Sum('shipping'),
        promotion_discount=Sum('promotion_discount'),
        voucher_seller_share=Sum('voucher_seller_share'),
        voucher_discount=Sum('voucher_discount'),
        seller_funded_discount=Sum('seller_funded_discount'),
        captured_total=Sum('captured_total'),
        refunded_total=Sum('refunded_total'),
        revenue=Sum('revenue'),
        commission_base=Sum('commission_base'),
        commission=Sum('commission'),
    )
    for key in (
        'gross_sales', 'merchandise', 'shipping', 'promotion_discount',
        'voucher_seller_share', 'voucher_discount', 'seller_funded_discount',
        'captured_total', 'refunded_total', 'revenue',
        'commission_base', 'commission', 'reviews_rating_sum',
    ):
        totals[key] = _money(totals[key])
    for key in ('orders_count', 'units_sold', 'voucher_redemptions', 'reviews_count'):
        totals[key] = totals[key] or 0
    totals['products_sold'] = (
        DailyProductMetric.objects.filter(store_id=store_id, day__range=(start, end))
        .values('product_id')
        .distinct()
        .count()
    )
    totals['review_rating_avg'] = (
        (totals['reviews_rating_sum'] / totals['reviews_count']).quantize(
            CENT, rounding=ROUND_HALF_UP
        )
        if totals['reviews_count']
        else None
    )
    totals['start'] = start
    totals['end'] = end
    return totals


def _empty_store_totals():
    """The shape a seller dashboard can always render, even with no data."""
    zero = ZERO
    return {
        'start': None, 'end': None,
        'orders_count': 0, 'units_sold': 0, 'products_sold': 0,
        'voucher_redemptions': 0, 'reviews_count': 0, 'review_rating_avg': None,
        'gross_sales': zero, 'merchandise': zero, 'shipping': zero,
        'promotion_discount': zero, 'voucher_seller_share': zero,
        'voucher_discount': zero, 'seller_funded_discount': zero,
        'captured_total': zero, 'refunded_total': zero, 'revenue': zero,
        'commission_base': zero, 'commission': zero,
        'reviews_rating_sum': zero,
    }


def store_inventory_snapshot(store_id):
    """The store's stock **right now** — a snapshot, deliberately not a rollup.

    Stock level is current state, not a period metric: the records hold no
    daily on-hand snapshot, so "inventory performance" pairs the period's
    rollup figures (units sold) with the live counters the Phase 12 dashboard
    already reads — and it is labeled as a snapshot on the page for exactly
    that reason. Low stock uses the same comparison as that dashboard:
    available ≤ the variant's own threshold.
    """
    from apps.catalog.models import Product, Variant  # local: reporting ↔ catalog

    rows = (
        Variant.objects.filter(product__store_id=store_id)
        .exclude(product__status=Product.Status.ARCHIVED)
        .select_related('inventory')
    )
    tracked = low = out = units = 0
    for variant in rows:
        inventory = getattr(variant, 'inventory', None)
        if inventory is None:
            continue
        tracked += 1
        available = inventory.available
        units += max(0, available)
        if available <= 0:
            out += 1
        if available <= inventory.low_stock_threshold:
            low += 1
    return {
        'variants_tracked': tracked,
        'low_stock_count': low,
        'out_of_stock_count': out,
        'units_on_hand': units,
    }


def store_leaderboard(start, end, limit=None):
    """Per-store totals for the range, biggest seller first (§19.2 preview)."""
    rows = (
        DailyStoreMetric.objects.filter(day__range=(start, end))
        .values('store_id', 'store__name', 'store__slug')
        .annotate(
            orders_count=Sum('orders_count'),
            units_sold=Sum('units_sold'),
            gross_sales=Sum('gross_sales'),
            merchandise=Sum('merchandise'),
            seller_funded_discount=Sum('seller_funded_discount'),
            captured_total=Sum('captured_total'),
            refunded_total=Sum('refunded_total'),
            revenue=Sum('revenue'),
            commission_base=Sum('commission_base'),
            commission=Sum('commission'),
        )
        .order_by('-gross_sales', 'store__name')
    )
    return list(rows[:limit]) if limit else list(rows)


def top_products(start, end, limit=10, store_id=None):
    """Best-selling products for the range — units first (§19.2).

    One seller reads their own shelf by passing `store_id`; staff pass nothing
    and get the whole marketplace.
    """
    rows = DailyProductMetric.objects.filter(day__range=(start, end))
    if store_id is not None:
        rows = rows.filter(store_id=store_id)
    return list(
        rows.values('product_id', 'product__title', 'store_id', 'store__name')
        .annotate(
            units_sold=Sum('units_sold'),
            orders_count=Sum('orders_count'),
            merchandise=Sum('merchandise'),
        )
        .order_by('-units_sold', 'product__title')[:limit]
    )
