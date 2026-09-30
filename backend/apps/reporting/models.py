"""Reporting aggregates (Phase 19 — PROJECT_CONTEXT §6 v1.16).

Derived, rebuildable rollup rows — never hand-edited. A dashboard reads these
tables and never the transactional ones (§17: reporting is fed by records, not
heavy live OLTP queries), which is why "the metrics reconcile with the
transactional data" is a thing the `rebuild_reporting` command can *prove*:
drop a date range, recompute it, and the same rows come back.

Grain is one row per day. Every money column is Decimal(14,2) and comes from a
snapshot already stored on a transactional row (C6) — nothing here is ever
computed from client input or from a live price lookup.
"""
from decimal import Decimal

from django.db import models

from apps.common.models import TimeStampedModel

# Money columns share one shape; a helper keeps the three tables consistent.
MONEY = {'max_digits': 14, 'decimal_places': 2}
ZERO = Decimal('0.00')


def money(**kwargs):
    """A Decimal(14,2) column defaulting to zero (§6 C6)."""
    return models.DecimalField(default=ZERO, **MONEY, **kwargs)


def counter():
    """A non-negative whole count (§19.3 — operational metrics are counts)."""
    return models.PositiveIntegerField(default=0)


class DailyPlatformMetric(TimeStampedModel):
    """One marketplace-wide day (§19.1).

    `commission_rate_percent` is a *snapshot of the rate the money was settled
    at*, not the current setting: finance may change the rate tomorrow, and
    that must never rewrite a settled day (§6 v1.16).
    """

    day = models.DateField(unique=True)

    # Volume
    orders_count = models.PositiveIntegerField(default=0)
    orders_cancelled = models.PositiveIntegerField(default=0)
    orders_paid = models.PositiveIntegerField(default=0)
    units_sold = models.PositiveIntegerField(default=0)
    products_sold = models.PositiveIntegerField(default=0)
    active_customers = models.PositiveIntegerField(default=0)
    active_sellers = models.PositiveIntegerField(default=0)

    # Merchandise money (order snapshots, non-cancelled orders placed that day)
    gmv = money()
    merchandise = money()
    shipping = money()
    discounts = money()

    # Cash money (the append-only ledger, by the day the movement happened)
    captured_total = money()
    refunded_total = money()
    revenue = money()

    # The platform's own cut
    commission_base = money()
    commission = money()
    commission_rate_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=ZERO
    )

    class Meta:
        ordering = ['-day']
        verbose_name = 'daily platform metric'
        verbose_name_plural = 'daily platform metrics'

    def __str__(self):
        return f'{self.day}: GMV {self.gmv}, commission {self.commission}'


class DailyStoreMetric(TimeStampedModel):
    """One store's day (§19.1, extended by §19.2).

    `seller_funded_discount` is the part of that day's discounts **this store
    absorbed** — its `VoucherUsage.seller_amount` plus the `PromotionUsage`
    rows of campaigns it owns. A platform-funded discount is the platform's
    cost and was never this store's revenue, so it does not reduce the base the
    commission is taken from (§6 v1.16).
    """

    day = models.DateField()
    store = models.ForeignKey(
        'stores.Store',
        on_delete=models.PROTECT,
        related_name='daily_metrics',
    )

    orders_count = models.PositiveIntegerField(default=0)
    units_sold = models.PositiveIntegerField(default=0)
    products_sold = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(
        default=False, help_text='Received at least one non-cancelled order.'
    )

    merchandise = money()
    shipping = money()
    promotion_discount = money()
    voucher_seller_share = money()
    seller_funded_discount = money()
    gross_sales = money()

    captured_total = money()
    refunded_total = money()
    revenue = money()

    commission_base = money()
    commission = money()
    commission_rate_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=ZERO
    )

    # §19.2 seller analytics: what the store's discounts really moved, and
    # what its customers said. Two definitions, pinned here because a seller
    # dashboard must never guess at them:
    #
    # * `voucher_redemptions` counts redemptions **involving this store** —
    #   every voucher redeemed on an order whose live slices include the
    #   store, the store's own vouchers included. `voucher_discount` is the
    #   part of those redemptions' discount that followed the store's lines
    #   (an order-level discount is apportioned across the stores that took
    #   part, exactly as the refund arithmetic apportions it), and the share
    #   the store itself funded is already `voucher_seller_share`.
    # * `reviews_count` / `reviews_rating_sum` are the day's **published**
    #   reviews of the store's products and the stars they gave — hidden or
    #   flagged rows stay out, matching `recompute_store_rating` (§6).
    voucher_redemptions = models.PositiveIntegerField(default=0)
    voucher_discount = money()
    reviews_count = models.PositiveIntegerField(default=0)
    reviews_rating_sum = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=ZERO,
        help_text='Sum of the day\'s published review ratings; average = sum/count.',
    )

    class Meta:
        ordering = ['-day', 'store_id']
        constraints = [
            models.UniqueConstraint(
                fields=['day', 'store'], name='reporting_store_day_unique'
            ),
        ]
        indexes = [
            models.Index(fields=['store', 'day'], name='reporting_store_lookup_idx'),
        ]
        verbose_name = 'daily store metric'
        verbose_name_plural = 'daily store metrics'

    def __str__(self):
        return f'{self.day} · {self.store_id}: {self.gross_sales}'


class DailyProductMetric(TimeStampedModel):
    """Product activity for one store-day (§19.1 "product activity", §19.2).

    `merchandise` is the summed `OrderItem.line_total` — the gross line value
    before any discount, because the line snapshot is gross (§6 v1.7).
    """

    day = models.DateField()
    store = models.ForeignKey(
        'stores.Store',
        on_delete=models.PROTECT,
        related_name='daily_product_metrics',
    )
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.PROTECT,
        related_name='daily_metrics',
    )

    orders_count = models.PositiveIntegerField(default=0)
    units_sold = models.PositiveIntegerField(default=0)
    merchandise = money()

    class Meta:
        ordering = ['-day', 'store_id', 'product_id']
        constraints = [
            models.UniqueConstraint(
                fields=['day', 'store', 'product'],
                name='reporting_product_day_unique',
            ),
        ]
        indexes = [
            models.Index(
                fields=['product', 'day'], name='reporting_product_lookup_idx'
            ),
        ]
        verbose_name = 'daily product metric'
        verbose_name_plural = 'daily product metrics'

    def __str__(self):
        return f'{self.day} · product {self.product_id}: {self.units_sold} units'


class DailyOperationsMetric(TimeStampedModel):
    """The marketplace's operational day (§19.3) — what *happened*, as counts.

    The money lives on `DailyPlatformMetric`; this table is the flow record
    beside it, pinned definition by pinned definition so an operations
    dashboard can never guess:

    * **Order status** (`orders_open` / `orders_completed` /
      `orders_cancelled` / `orders_refunded`) buckets the orders **created
      that day** by where they stand **as of this rebuild** — status is
      current-state, so a later rebuild re-derives the buckets from the same
      orders (idempotent; a day's row only changes when an order's status
      actually changed). `open` is everything not yet delivered, completed,
      cancelled or refunded. The four buckets always re-add to the orders
      created that day, and `orders_cancelled` mirrors
      `DailyPlatformMetric.orders_cancelled` exactly (both are "created that
      day, now cancelled").
    * **Fulfillment**: `shipments_created` counts parcels **created** that
      day — the seller's ship act (`Shipment.shipped_at` is never written by
      any code path, so creation is the dispatch signal); `shipments_delivered`
      counts `delivered_at` falling that day.
    * **Returns**: `returns_filed` is cases opened that day;
      `returns_approved` / `returns_rejected` count the day's **decision**
      events (the seller response, the staff ruling or the admin override),
      bucketed by the status the case moved to — one definition that covers
      every path a decision can take (the *kind* is what marks a decision:
      every timeline row records the case's status at its moment, so a
      goods-received row written while the case was still approved also
      carries "approved"); `returns_received` counts goods-received events.
    * **Refunds**: `refunds_issued` counts `Refund` rows created that day;
      `refunds_settled` counts the ledger's refund **debits** — the money
      truth (§9). The peso amounts stay on the platform row; these are counts.
    * **Support**: requests, conversations and messages created that day,
      disputes opened, and `disputes_resolved` = staff rulings written that
      day (a buyer's withdrawal is not a resolution and does not count).
    """

    day = models.DateField(unique=True)

    # Order status metrics (orders created that day, by status at rebuild)
    orders_open = counter()
    orders_completed = counter()
    orders_cancelled = counter()
    orders_refunded = counter()

    # Fulfillment events
    shipments_created = counter()
    shipments_delivered = counter()

    # Returns (filed / decided / received)
    returns_filed = counter()
    returns_approved = counter()
    returns_rejected = counter()
    returns_received = counter()

    # Refunds (counts; the money lives on the platform row)
    refunds_issued = counter()
    refunds_settled = counter()

    # Support workload
    requests_filed = counter()
    conversations_opened = counter()
    messages_sent = counter()
    disputes_opened = counter()
    disputes_resolved = counter()

    class Meta:
        ordering = ['-day']
        verbose_name = 'daily operations metric'
        verbose_name_plural = 'daily operations metrics'

    def __str__(self):
        return f'{self.day}: {self.orders_completed} completed, {self.shipments_delivered} delivered'


class DailyStoreOpsMetric(TimeStampedModel):
    """One store's operational day (§19.3 "seller performance").

    The store-grain slice of the operational records, attributed by the
    **store slice the record belongs to**: a shipment's `seller_order.store`,
    a case's `seller_order.store`, a message's `conversation.store`. A
    whole-order record (no slice) counts only at the platform grain — split
    counts across stores would invent numbers the records do not carry, and
    the parts are not required to re-add to a count the way pesos are.
    Range reads sum these rows (never the transactional tables — §17) and the
    performance endpoint serves them with the store's name.
    """

    day = models.DateField()
    store = models.ForeignKey(
        'stores.Store',
        on_delete=models.PROTECT,
        related_name='daily_ops_metrics',
    )

    shipments_created = counter()
    shipments_delivered = counter()
    returns_filed = counter()
    returns_received = counter()
    disputes_opened = counter()
    requests_filed = counter()
    messages_sent = counter()

    class Meta:
        ordering = ['-day', 'store_id']
        constraints = [
            models.UniqueConstraint(
                fields=['day', 'store'], name='reporting_store_ops_day_unique'
            ),
        ]
        indexes = [
            models.Index(fields=['store', 'day'], name='reporting_store_ops_idx'),
        ]
        verbose_name = 'daily store operations metric'
        verbose_name_plural = 'daily store operations metrics'

    def __str__(self):
        return f'{self.day} · store {self.store_id}: {self.shipments_delivered} delivered'
