"""Analytics read serializers (Phase 19 — §19.1).

Money leaves as strings, which is what DRF's `DecimalField` does by default and
what the rest of the API already does — a peso amount is never handed to the
browser as a float.
"""
from rest_framework import serializers

from .models import DailyPlatformMetric, DailyProductMetric, DailyStoreMetric


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
            'voucher_seller_share', 'seller_funded_discount', 'gross_sales',
            'captured_total', 'refunded_total', 'revenue',
            'commission_base', 'commission', 'commission_rate_percent',
        ]
        read_only_fields = fields


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
