"""Promotion serializers (Phase 16 — ROADMAP §16.1) — declared shapes only.

The client sends a code, never an amount; everything else crosses the wire
as server-resolved JSON numbers (the same contract as cart/orders).
"""
from rest_framework import serializers


class VoucherValidateSerializer(serializers.Serializer):
    """POST /vouchers/validate body — a code, nothing else."""

    code = serializers.CharField(max_length=32)


def serialize_voucher(voucher):
    """Public-safe voucher shape (the voucher center renders this later)."""
    return {
        'id': voucher.id,
        'code': voucher.code,
        'title': voucher.title,
        'description': voucher.description,
        'scope': voucher.scope,
        'store_id': voucher.store_id,
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
