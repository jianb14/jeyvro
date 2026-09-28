"""Promotion serializers (Phase 16 — ROADMAP §16.1–§16.3) — declared shapes only.

The client sends a code, never an amount; everything else crosses the wire
as server-resolved JSON numbers (the same contract as cart/orders).
`funded_by` is a declaration of who pays for the code, never a split the
client may influence — the split itself is settled server-side at redemption
(§16.3) and never appears on the wire.
"""
from rest_framework import serializers


class VoucherValidateSerializer(serializers.Serializer):
    """POST /vouchers/validate body — a code, nothing else."""

    code = serializers.CharField(max_length=32)


def serialize_voucher(voucher):
    """Public-safe voucher shape (the voucher center renders this)."""
    store = voucher.store
    return {
        'id': voucher.id,
        'code': voucher.code,
        'title': voucher.title,
        'description': voucher.description,
        'scope': voucher.scope,
        'store_id': voucher.store_id,
        'store_name': store.name if store else None,
        'store_slug': store.slug if store else None,
        'funded_by': voucher.funded_by,
        'discount_type': voucher.discount_type,
        'value': float(voucher.value),
        'min_spend': float(voucher.min_spend),
        'max_discount': (
            float(voucher.max_discount) if voucher.max_discount is not None else None
        ),
        'first_order_only': voucher.first_order_only,
        'starts_at': voucher.starts_at.isoformat() if voucher.starts_at else None,
        'ends_at': voucher.ends_at.isoformat() if voucher.ends_at else None,
        'usage_limit': voucher.usage_limit,
        'per_user_limit': voucher.per_user_limit,
    }


def serialize_voucher_preview(plan):
    """The validate endpoint's verdict payload — everything the UI needs."""
    return {
        'valid': True,
        'code': plan['voucher'].code,
        'voucher': serialize_voucher(plan['voucher']),
        'eligible_subtotal': float(plan['eligible_subtotal']),
        'discount_total': float(plan['discount_total']),
    }


def serialize_promotion(promo):
    """Public / seller / staff promotion read shape."""
    campaign = promo.campaign
    store = campaign.store if campaign else None
    return {
        'id': promo.id,
        'store_id': store.id if store else None,
        'store_name': store.name if store else None,
        'store_slug': store.slug if store else None,
        'name': promo.label,
        'kind': promo.kind,
        'label': promo.label,
        'discount_type': promo.discount_type,
        'value': float(promo.value),
        'min_spend': float(promo.min_spend),
        'min_qty': promo.min_qty,
        'buy_product_id': promo.buy_product_id,
        'buy_qty': promo.buy_qty,
        'get_product_id': promo.get_product_id,
        'get_qty': promo.get_qty,
        'is_active': promo.is_active,
        'campaign_id': campaign.id if campaign else None,
        'campaign_name': campaign.name if campaign else None,
        'starts_at': campaign.starts_at.isoformat() if campaign and campaign.starts_at else None,
        'ends_at': campaign.ends_at.isoformat() if campaign and campaign.ends_at else None,
    }


def serialize_campaign(campaign):
    """Staff / seller campaign read shape."""
    return {
        'id': campaign.id,
        'name': campaign.name,
        'scope': campaign.scope,
        'store_id': campaign.store_id,
        'store_name': campaign.store.name if campaign.store else None,
        'description': campaign.description,
        'starts_at': campaign.starts_at.isoformat() if campaign.starts_at else None,
        'ends_at': campaign.ends_at.isoformat() if campaign.ends_at else None,
        'is_active': campaign.is_active,
        'promotion_count': campaign.promotions.count(),
    }


class PromotionCreateSerializer(serializers.Serializer):
    """Store owner promotion creation payload."""

    name = serializers.CharField(max_length=120)
    kind = serializers.ChoiceField(
        choices=[
            'flash_sale',
            'product_discount',
            'bundle',
            'free_shipping',
            'buy_x_get_y',
        ]
    )
    discount_type = serializers.ChoiceField(choices=['percentage', 'fixed'], default='percentage')
    value = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0, default=0.0)
    min_spend = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=0, default=0.0
    )
    min_qty = serializers.IntegerField(min_value=1, default=1)
    label = serializers.CharField(max_length=120, required=False, allow_blank=True, default='')
    starts_at = serializers.DateTimeField(required=False, allow_null=True)
    ends_at = serializers.DateTimeField(required=False, allow_null=True)
    is_active = serializers.BooleanField(default=True)
    target_type = serializers.ChoiceField(
        choices=['all', 'product', 'category'], default='all'
    )
    product_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, default=list
    )
    category_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, default=list
    )
    # Buy X get Y (§16.2) — the pair is part of the rule, and only a
    # buy-X-get-Y rule may carry it. The DB constraints agree; this is the
    # friendly version that answers with field errors instead of a 500.
    buy_product_id = serializers.IntegerField(required=False, min_value=1, default=None)
    buy_qty = serializers.IntegerField(required=False, min_value=1, default=None)
    get_product_id = serializers.IntegerField(required=False, min_value=1, default=None)
    get_qty = serializers.IntegerField(required=False, min_value=1, default=None)

    BXGY_PAIR_FIELDS = ('buy_product_id', 'buy_qty', 'get_product_id', 'get_qty')

    def validate(self, attrs):
        pair = {name: attrs.get(name) for name in self.BXGY_PAIR_FIELDS}
        if attrs.get('kind') == 'buy_x_get_y':
            missing = [name for name, value in pair.items() if value is None]
            if missing:
                raise serializers.ValidationError(
                    {name: ['Required for a buy X get Y rule.'] for name in missing}
                )
            if attrs.get('discount_type') != 'percentage':
                raise serializers.ValidationError(
                    {'discount_type': ['A buy X get Y rule must be a percentage.']}
                )
        elif any(value is not None for value in pair.values()):
            raise serializers.ValidationError(
                {
                    name: ['Only a buy X get Y rule may set the buy/get pair.']
                    for name, value in pair.items()
                    if value is not None
                }
            )
        return attrs


