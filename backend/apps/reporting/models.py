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
