"""Payment serializers — declared shapes only (backend-api rule 2).

Money crosses the wire as JSON numbers (the app-wide contract) and every
value is server truth: the payment amount was verified against the order
snapshot, the refund total is recomputed from settled refunds, and the
client only ever renders these values.
"""
from decimal import Decimal

from rest_framework import serializers


class CreateRefundSerializer(serializers.Serializer):
    """POST /payments/<reference>/refunds body — staff-issued refunds."""

    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal('0.01')
    )
    reason = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=''
    )


def _money(value):
    """Decimal → JSON number (the wire contract used across the app)."""
    return float(value)


def serialize_refund(refund):
    """One refund record — status is what the ledger reversal already did."""
    return {
        'reference': refund.reference,
        'amount': _money(refund.amount),
        'status': refund.status,
        'reason': refund.reason,
        'created_at': refund.created_at.isoformat(),
    }


def serialize_payment(payment):
    """The payment block embedded in order payloads (§6)."""
    return {
        'reference': payment.reference,
        'method': payment.method,
        'status': payment.status,
        'amount': _money(payment.amount),
        'currency': payment.currency,
        'provider': payment.provider,
        'checkout_url': payment.checkout_url or None,
        'paid_at': payment.paid_at.isoformat() if payment.paid_at else None,
        'expires_at': payment.expires_at.isoformat() if payment.expires_at else None,
        'refunded_total': _money(payment.refunded_total),
    }


def serialize_payment_detail(payment):
    """GET /payments/<reference>/ — payment state plus its refund history."""
    payload = serialize_payment(payment)
    payload['order_number'] = payment.order.number
    payload['refunds'] = [
        serialize_refund(refund) for refund in payment.refunds.all()
    ]
    return payload


# --- Staff oversight shapes (13.5 — /staff/payments console) ----------------


def serialize_staff_payment_row(payment):
    """One payment row — order context, money state, refund total."""
    return {
        'reference': payment.reference,
        'order_number': payment.order.number,
        'customer_email': payment.order.user.email,
        'method': payment.method,
        'status': payment.status,
        'amount': _money(payment.amount),
        'currency': payment.currency,
        'provider': payment.provider,
        'refunded_total': _money(payment.refunded_total),
        'paid_at': payment.paid_at.isoformat() if payment.paid_at else None,
        'created_at': payment.created_at.isoformat(),
    }


def serialize_staff_refund_row(refund):
    """One refund row — who issued it (finance, §4) and against which order."""
    return {
        'reference': refund.reference,
        'payment_reference': refund.payment.reference,
        'order_number': refund.payment.order.number,
        'amount': _money(refund.amount),
        'status': refund.status,
        'reason': refund.reason,
        'issued_by': refund.actor.email if refund.actor else None,
        'created_at': refund.created_at.isoformat(),
    }
