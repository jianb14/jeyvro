"""Store serializers — declared fields only (backend-api rule 2).

The public shape matches the data-layer contract: id/slug/name/description/
logo_url/banner_url/rating placeholder/policies. `rating` stays null until
reviews exist (Phase 14) — the frontend renders API truth only.
"""
from decimal import Decimal

from rest_framework import serializers

from .models import SellerApplication, Store


class SellerApplicationCreateSerializer(serializers.ModelSerializer):
    """Customer-facing application payload."""

    class Meta:
        model = SellerApplication
        fields = ['store_name', 'store_description', 'contact_phone']

    def validate_store_name(self, value):
        if not value.strip():
            raise serializers.ValidationError('Store name is required.')
        return value


class SellerApplicationSerializer(serializers.ModelSerializer):
    """Staff-facing review list shape."""

    applicant_email = serializers.EmailField(source='user.email', read_only=True)
    store_slug = serializers.SlugField(source='store.slug', read_only=True)
    store_status = serializers.CharField(source='store.status', read_only=True)

    class Meta:
        model = SellerApplication
        fields = [
            'id', 'applicant_email', 'store_slug', 'store_status',
            'store_name', 'store_description', 'contact_phone',
            'status', 'rejection_reason', 'reviewed_by', 'reviewed_at',
            'created_at',
        ]


class SellerStoreSerializer(serializers.ModelSerializer):
    """Owner-facing store profile — editable by the seller (own store only).

    Money fields cross the wire as JSON numbers (matching the catalog/cart
    contract); fees are validated ≥ 0 server-side (§10.1, §6 v1.7).
    """

    shipping_flat_fee = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0'),
        coerce_to_string=False,
    )
    free_shipping_threshold = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0'),
        coerce_to_string=False,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Store
        fields = [
            'id', 'name', 'slug', 'description', 'logo_url', 'banner_url',
            'contact_email', 'contact_phone', 'return_policy',
            'shipping_policy', 'shipping_flat_fee', 'free_shipping_threshold',
            'status', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'slug', 'contact_email', 'status', 'created_at', 'updated_at',
        ]

class StaffStoreSerializer(serializers.ModelSerializer):
    """Staff oversight shape (§13.3) — full store details plus owner info."""

    owner_email = serializers.EmailField(source='user.email', read_only=True)
    owner_name = serializers.CharField(source='user.get_full_name', read_only=True)
    product_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Store
        fields = [
            'id',
            'name',
            'slug',
            'description',
            'owner_email',
            'owner_name',
            'status',
            'contact_email',
            'contact_phone',
            'product_count',
            'suspended_at',
            'created_at',
            'updated_at',
        ]


class PublicStoreSerializer(serializers.ModelSerializer):
    """Storefront shape — active stores only, no owner/contact internals.

    Shipping fees are public truth (checkout charges them); thresholds let
    the storefront surface "free shipping over X" later without a new read.
    """

    rating = serializers.FloatField(read_only=True, allow_null=True, default=None)
    shipping_flat_fee = serializers.DecimalField(
        max_digits=12, decimal_places=2, coerce_to_string=False, read_only=True
    )
    free_shipping_threshold = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        coerce_to_string=False,
        allow_null=True,
        read_only=True,
    )

    class Meta:
        model = Store
        fields = [
            'id', 'slug', 'name', 'description', 'logo_url', 'banner_url',
            'return_policy', 'shipping_policy', 'shipping_flat_fee',
            'free_shipping_threshold', 'rating', 'created_at',
        ]