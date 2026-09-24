"""Store serializers — declared fields only (backend-api rule 2).

The public shape matches the data-layer contract: id/slug/name/description/
logo_url/banner_url/rating placeholder/policies. `rating` stays null until
reviews exist (Phase 14) — the frontend renders API truth only.
"""
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
    """Owner-facing store profile — editable by the seller (own store only)."""

    class Meta:
        model = Store
        fields = [
            'id', 'name', 'slug', 'description', 'logo_url', 'banner_url',
            'contact_email', 'contact_phone', 'return_policy',
            'shipping_policy', 'status', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'slug', 'contact_email', 'status', 'created_at', 'updated_at',
        ]


class PublicStoreSerializer(serializers.ModelSerializer):
    """Storefront shape — active stores only, no owner/contact internals."""

    rating = serializers.FloatField(read_only=True, allow_null=True, default=None)

    class Meta:
        model = Store
        fields = [
            'id', 'slug', 'name', 'description', 'logo_url', 'banner_url',
            'return_policy', 'shipping_policy', 'rating', 'created_at',
        ]