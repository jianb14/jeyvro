"""Analytics read serializers (Phase 19 — §19.1–§19.3).

Money leaves as strings, which is what DRF's `DecimalField` does by default and
what the rest of the API already does — a peso amount is never handed to the
browser as a float. The §19.3 operational rows are counts (IntegerField) —
there is no peso on them to get wrong.
"""
from rest_framework import serializers

from .models import (
    DailyOperationsMetric,
    DailyPlatformMetric,
    DailyProductMetric,
    DailyStoreMetric,
)


class DailyPlatformMetricSerializer(serializers.ModelSerializer):
    """One marketplace day — the series a chart plots."""

    class Meta:
        model = DailyPlatformMetric
        fields = [
            'day',
            'orders_count', 'orders_cancelled', 'orders_paid',
            'units_sold', 'products_sold', 'active_customers', 'active_sellers',
            'gmv', 'merchandise', 'shipping', 'discounts',
            'captured_total', 'refunded_total', 'revenue',
            'commission_base', 'commission', 'commission_rate_percent',
        ]
        read_only_fields = fields


class PlatformTotalsSerializer(serializers.Serializer):
    """The range headline.

    `customer_days` / `seller_days` are named for what they are — sums of the
    daily active counts, not distinct people — because a day's active count
    does not add up across days. The per-day exact figures ride the series.
    """

    start = serializers.DateField(allow_null=True)
    end = serializers.DateField(allow_null=True)
    orders_count = serializers.IntegerField()
    orders_cancelled = serializers.IntegerField()
    orders_paid = serializers.IntegerField()
    units_sold = serializers.IntegerField()
    products_sold = serializers.IntegerField()
    customer_days = serializers.IntegerField()
    seller_days = serializers.IntegerField()
    gmv = serializers.DecimalField(max_digits=16, decimal_places=2)
    merchandise = serializers.DecimalField(max_digits=16, decimal_places=2)
    shipping = serializers.DecimalField(max_digits=16, decimal_places=2)
    discounts = serializers.DecimalField(max_digits=16, decimal_places=2)
    captured_total = serializers.DecimalField(max_digits=16, decimal_places=2)
    refunded_total = serializers.DecimalField(max_digits=16, decimal_places=2)
    revenue = serializers.DecimalField(max_digits=16, decimal_places=2)
    commission_base = serializers.DecimalField(max_digits=16, decimal_places=2)
    commission = serializers.DecimalField(max_digits=16, decimal_places=2)


class StoreTotalsSerializer(serializers.Serializer):
    """One store's range headline (§19.2) — the seller's own numbers.

    `review_rating_avg` is null when nothing was reviewed: "no rating yet" is
    not a rating of zero, and the seed of it (`reviews_rating_sum` / count)
    rides along so the average stays checkable.
    """

    start = serializers.DateField(allow_null=True)
    end = serializers.DateField(allow_null=True)
    orders_count = serializers.IntegerField()
    units_sold = serializers.IntegerField()
    products_sold = serializers.IntegerField()
    voucher_redemptions = serializers.IntegerField()
    reviews_count = serializers.IntegerField()
    reviews_rating_sum = serializers.DecimalField(max_digits=12, decimal_places=2)
    review_rating_avg = serializers.DecimalField(
        max_digits=3, decimal_places=2, allow_null=True
    )
    gross_sales = serializers.DecimalField(max_digits=16, decimal_places=2)
    merchandise = serializers.DecimalField(max_digits=16, decimal_places=2)
    shipping = serializers.DecimalField(max_digits=16, decimal_places=2)
    promotion_discount = serializers.DecimalField(max_digits=16, decimal_places=2)
    voucher_seller_share = serializers.DecimalField(max_digits=16, decimal_places=2)
    voucher_discount = serializers.DecimalField(max_digits=16, decimal_places=2)
    seller_funded_discount = serializers.DecimalField(max_digits=16, decimal_places=2)
    captured_total = serializers.DecimalField(max_digits=16, decimal_places=2)
    refunded_total = serializers.DecimalField(max_digits=16, decimal_places=2)
    revenue = serializers.DecimalField(max_digits=16, decimal_places=2)
    commission_base = serializers.DecimalField(max_digits=16, decimal_places=2)
    commission = serializers.DecimalField(max_digits=16, decimal_places=2)


class StoreInventorySerializer(serializers.Serializer):
    """The store's stock *now* — a snapshot, labeled as one on the page (§19.2)."""

    variants_tracked = serializers.IntegerField()
    low_stock_count = serializers.IntegerField()
    out_of_stock_count = serializers.IntegerField()
    units_on_hand = serializers.IntegerField()


class StoreLeaderboardRowSerializer(serializers.Serializer):
    """One store's range totals (§19.2 preview)."""

    store_id = serializers.IntegerField()
    store__name = serializers.CharField()
    store__slug = serializers.SlugField()
    orders_count = serializers.IntegerField()
    units_sold = serializers.IntegerField()
    gross_sales = serializers.DecimalField(max_digits=16, decimal_places=2)
    merchandise = serializers.DecimalField(max_digits=16, decimal_places=2)
    seller_funded_discount = serializers.DecimalField(max_digits=16, decimal_places=2)
    captured_total = serializers.DecimalField(max_digits=16, decimal_places=2)
    refunded_total = serializers.DecimalField(max_digits=16, decimal_places=2)
    revenue = serializers.DecimalField(max_digits=16, decimal_places=2)
    commission_base = serializers.DecimalField(max_digits=16, decimal_places=2)
    commission = serializers.DecimalField(max_digits=16, decimal_places=2)


class TopProductRowSerializer(serializers.Serializer):
    """One product's range totals — product activity (§19.1)."""

    product_id = serializers.IntegerField()
    product__title = serializers.CharField()
    store_id = serializers.IntegerField()
    store__name = serializers.CharField()
    units_sold = serializers.IntegerField()
    orders_count = serializers.IntegerField()
    merchandise = serializers.DecimalField(max_digits=16, decimal_places=2)


class DailyStoreMetricSerializer(serializers.ModelSerializer):
    """One store-day, for the store drill-down."""

    store_name = serializers.CharField(source='store.name', read_only=True)

    class Meta:
        model = DailyStoreMetric
        fields = [
            'day', 'store_id', 'store_name',
            'orders_count', 'units_sold', 'products_sold', 'is_active',
            'merchandise', 'shipping', 'promotion_discount',
            'voucher_seller_share', 'voucher_discount', 'voucher_redemptions',
            'reviews_count', 'reviews_rating_sum',
            'seller_funded_discount', 'gross_sales',
            'captured_total', 'refunded_total', 'revenue',
            'commission_base', 'commission', 'commission_rate_percent',
        ]
        read_only_fields = fields


OPERATIONS_COUNT_FIELDS = [
    'orders_open', 'orders_completed', 'orders_cancelled', 'orders_refunded',
    'shipments_created', 'shipments_delivered',
    'returns_filed', 'returns_approved', 'returns_rejected', 'returns_received',
    'refunds_issued', 'refunds_settled',
    'requests_filed', 'conversations_opened', 'messages_sent',
    'disputes_opened', 'disputes_resolved',
]


class OperationsTotalsSerializer(serializers.Serializer):
    """The range's operational headline (§19.3) — counts, never pesos.

    Rates are deliberately absent: they do not sum across days, so the row
    ships the two counts a rate would divide and the server owns any division
    it decides to do.
    """

    start = serializers.DateField(allow_null=True)
    end = serializers.DateField(allow_null=True)
    orders_open = serializers.IntegerField()
    orders_completed = serializers.IntegerField()
    orders_cancelled = serializers.IntegerField()
    orders_refunded = serializers.IntegerField()
    shipments_created = serializers.IntegerField()
    shipments_delivered = serializers.IntegerField()
    returns_filed = serializers.IntegerField()
    returns_approved = serializers.IntegerField()
    returns_rejected = serializers.IntegerField()
    returns_received = serializers.IntegerField()
    refunds_issued = serializers.IntegerField()
    refunds_settled = serializers.IntegerField()
    requests_filed = serializers.IntegerField()
    conversations_opened = serializers.IntegerField()
    messages_sent = serializers.IntegerField()
    disputes_opened = serializers.IntegerField()
    disputes_resolved = serializers.IntegerField()


class DailyOperationsMetricSerializer(serializers.ModelSerializer):
    """One operational day, for the operations series."""

    class Meta:
        model = DailyOperationsMetric
        fields = ['day'] + OPERATIONS_COUNT_FIELDS
        read_only_fields = fields


class StorePerformanceRowSerializer(serializers.Serializer):
    """One store's operational range totals (§19.3 "seller performance").

    Store-sliced records only — whole-order records are the platform's row to
    carry, so these columns are honest counts rather than a split that would
    invent store attribution.
    """

    store_id = serializers.IntegerField()
    store__name = serializers.CharField()
    shipments_created = serializers.IntegerField()
    shipments_delivered = serializers.IntegerField()
    returns_filed = serializers.IntegerField()
    returns_received = serializers.IntegerField()
    disputes_opened = serializers.IntegerField()
    requests_filed = serializers.IntegerField()
    messages_sent = serializers.IntegerField()


class DailyProductMetricSerializer(serializers.ModelSerializer):
    """One store-product-day."""

    product_title = serializers.CharField(source='product.title', read_only=True)

    class Meta:
        model = DailyProductMetric
        fields = [
            'day', 'store_id', 'product_id', 'product_title',
            'orders_count', 'units_sold', 'merchandise',
        ]
        read_only_fields = fields
