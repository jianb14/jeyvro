"""Platform settings serializers (Phase 13.6 — backend-api rule 2).

Declared fields only, never `__all__`. Two write shapes exist on purpose:
the general serializer (administrator path, everything except the audit
read-fields) and the commission serializer (the finance path — §4 keeps
commission adjustments in finance/administrator hands).
"""
from rest_framework import serializers

from .models import PlatformSettings


class PlatformSettingsSerializer(serializers.ModelSerializer):
    """Full settings shape — serves GET and the administrator PATCH."""

    updated_by_email = serializers.SerializerMethodField()

    class Meta:
        model = PlatformSettings
        fields = [
            'platform_name',
            'support_email',
            'commission_rate_percent',
            'default_shipping_flat_fee',
            'default_free_shipping_threshold',
            'cod_enabled',
            'payment_expiry_hours',
            'default_order_updates_email',
            'default_promotions_email',
            'default_messaging_email',
            'updated_by_email',
            'updated_at',
        ]
        read_only_fields = ['updated_by_email', 'updated_at']

    def get_updated_by_email(self, obj):
        return obj.updated_by.email if obj.updated_by else None


class CommissionSettingsSerializer(serializers.ModelSerializer):
    """Commission-only shape — the finance PATCH path."""

    class Meta:
        model = PlatformSettings
        fields = ['commission_rate_percent']


class PublicPlatformInfoSerializer(serializers.Serializer):
    """The public subset — nothing but name and support contact ever
    leaves the platform unauthenticated (no money, no switches)."""

    platform_name = serializers.CharField(max_length=60)
    support_email = serializers.EmailField()
