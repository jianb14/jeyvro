"""Resolution serializers — API truth in, shaped payloads out (§17).

Every payload here is *derived* from server state: the verdict, the refund
arithmetic, the status labels and the timeline all come from the services and
the policy module, so nothing on the wire is a client-supplied number. Money
is serialized as strings (Decimal → str) exactly like the payments/orders
payloads so the frontend never parses a float (§9).
"""
from decimal import Decimal

from rest_framework import serializers

from . import policies, services
from .models import DisputeReason, DisputeResolution, ReturnReason


def _money(value):
    return f'{value:.2f}'


def _iso(value):
    return value.isoformat() if value else ''


class ReturnLineSerializer(serializers.Serializer):
    """One line the customer asks to send back."""

    order_item_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class ReturnApplySerializer(serializers.Serializer):
    """POST /orders/<number>/returns — reason + lines + optional intake link."""

    reason = serializers.ChoiceField(choices=ReturnReason.choices)
    note = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    seller_order_id = serializers.IntegerField(required=False, allow_null=True)
    request_id = serializers.IntegerField(required=False, allow_null=True)
    lines = ReturnLineSerializer(many=True)


class ReturnDecisionSerializer(serializers.Serializer):
    """Seller/staff ruling — approve or reject, with the reason on record."""

    decision = serializers.ChoiceField(choices=['approve', 'reject'])
    reason = serializers.CharField(required=False, allow_blank=True, max_length=255)
    note = serializers.CharField(required=False, allow_blank=True, max_length=255)


class ReturnShipmentSerializer(serializers.Serializer):
    """Reverse parcel details — all optional; a tracking number is minted."""

    tracking_number = serializers.CharField(
        required=False, allow_blank=True, max_length=64
    )
    carrier = serializers.CharField(required=False, allow_blank=True, max_length=32)
    carrier_name = serializers.CharField(
        required=False, allow_blank=True, max_length=128
    )
    notes = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class ReturnReceiveSerializer(serializers.Serializer):
    """Receipt of goods — optional per-line restock overrides."""

    note = serializers.CharField(required=False, allow_blank=True, max_length=255)
    restock_overrides = ReturnLineSerializer(many=True, required=False)


class ReturnPayoutSerializer(serializers.Serializer):
    """§17.2 payout — amount omitted means "everything the case still owes".

    The cap is never the client's: the service re-checks the amount against
    the case's remaining balance and the payment's refundable balance.
    """

    amount = serializers.DecimalField(
        required=False,
        allow_null=True,
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01'),
    )
    reason = serializers.CharField(required=False, allow_blank=True, max_length=255)


def serialize_refund(refund):
    """One money movement on a case (§17.2 refund status)."""
    return {
        'reference': refund.reference,
        'amount': _money(refund.amount),
        'status': refund.status,
        'status_label': refund.get_status_display(),
        'gateway_reference': refund.gateway_reference,
        'reason': refund.reason,
        'actor': refund.actor.email if refund.actor_id else '',
        'created_at': refund.created_at.isoformat(),
    }


def serialize_return_item(line):
    """One returned unit set — snapshot titles, never live catalog reads."""
    item = line.order_item
    return {
        'order_item_id': item.id,
        'product_title': item.product_title,
        'variant_name': item.variant_name,
        'sku': item.sku,
        'quantity': line.quantity,
        'unit_price': _money(item.unit_price),
        'line_total': _money(line.line_total),
        'restock': line.restock,
        'restocked_at': _iso(line.restocked_at),
    }


def serialize_return_event(event):
    """One customer-safe timeline step (§17.1 return status)."""
    return {
        'kind': event.kind,
        'kind_label': event.get_kind_display(),
        'message': event.message,
        'previous_status': event.previous_status,
        'new_status': event.new_status,
        'actor': event.actor.email if event.actor_id and event.actor else 'System',
        'occurred_at': event.created_at.isoformat(),
    }


def serialize_return_shipment(shipment):
    """The reverse parcel (§17.1 return shipment)."""
    if shipment is None:
        return None
    return {
        'tracking_number': shipment.tracking_number,
        'carrier': shipment.carrier,
        'carrier_name': shipment.carrier_name,
        'status': shipment.status,
        'status_label': shipment.get_status_display(),
        'notes': shipment.notes,
        'shipped_at': _iso(shipment.shipped_at),
        'received_at': _iso(shipment.received_at),
    }



def serialize_return_case(case, *, include_events=True):
    """The case as both sides read it (§17.1).

    The seller sees the customer's own words and their slice; the customer
    sees the ruling and the money they are owed; neither endpoint leaks the
    other's internals — visibility is decided by the view that calls this.
    """
    shipment = getattr(case, 'return_shipment', None)
    committed, _settled = services.refund_totals(case)
    payload = {
        'reference': case.reference,
        'order_number': case.order.number,
        'seller_order_id': case.seller_order_id,
        'store_name': case.seller_order.store_name if case.seller_order_id else '',
        'scope': 'store' if case.seller_order_id else 'order',
        'status': case.status,
        'status_label': case.get_status_display(),
        'is_open': case.is_open,
        'reason': case.reason,
        'reason_label': case.get_reason_display(),
        'note': case.note,
        'refund_due': _money(case.refund_due),
        'delivered_at': _iso(case.delivered_at),
        'window_expires_at': _iso(case.window_expires_at),
        'decision_reason': case.decision_reason,
        'response_note': case.response_note,
        'responded_at': _iso(case.responded_at),
        'admin_override_at': _iso(case.admin_override_at),
        'admin_override_reason': case.admin_override_reason,
        'customer_email': case.requested_by.email,
        'created_at': case.created_at.isoformat(),
        'items': [serialize_return_item(line) for line in case.items.all()],
        'shipment': serialize_return_shipment(shipment),
        'refunds': [serialize_refund(refund) for refund in case.refunds.all()],
        'refunded_total': _money(committed),
        'refund_remaining': _money(services.refund_remaining(case)),
    }
    if include_events:
        payload['events'] = [serialize_return_event(e) for e in case.events.all()]
    return payload


def serialize_return_row(case):
    """Compact row for the seller desk and the staff queue."""
    return {
        'reference': case.reference,
        'order_number': case.order.number,
        'store_name': (
            case.seller_order.store_name if case.seller_order_id else 'All stores'
        ),
        'status': case.status,
        'status_label': case.get_status_display(),
        'reason': case.reason,
        'reason_label': case.get_reason_display(),
        'refund_due': _money(case.refund_due),
        'item_count': sum(line.quantity for line in case.items.all()),
        'customer_email': case.requested_by.email,
        'created_at': case.created_at.isoformat(),
        'window_expires_at': _iso(case.window_expires_at),
    }


def serialize_eligibility(verdict):
    """The return button's verdict — eligible flag, reason, returnable lines."""
    return {
        'eligible': verdict['eligible'],
        'code': verdict['code'],
        'reason': verdict['reason'],
        'days_left': verdict['days_left'],
        'delivered_at': _iso(verdict['delivered_at']),
        'window_expires_at': _iso(verdict['window_expires_at']),
        'window_days': policies.return_window_days(),
        'lines': [dict(row) for row in verdict['lines']],
    }


# -----------------------------------------------------------------------------
# §17.3 disputes
# -----------------------------------------------------------------------------

class DisputeCreateSerializer(serializers.Serializer):
    """POST /orders/<number>/disputes — reason + opening statement + links."""

    reason = serializers.ChoiceField(choices=DisputeReason.choices)
    statement = serializers.CharField(max_length=4000)
    seller_order_id = serializers.IntegerField(required=False, allow_null=True)
    request_id = serializers.IntegerField(required=False, allow_null=True)
    return_reference = serializers.CharField(
        required=False, allow_blank=True, max_length=32
    )


class DisputeStatementSerializer(serializers.Serializer):
    """One party's statement — body only; the party is derived server-side."""

    body = serializers.CharField(max_length=4000)


class DisputeEvidenceSerializer(serializers.Serializer):
    """One evidence row — a URL plus an optional caption (media phase later)."""

    url = serializers.URLField(max_length=500)
    caption = serializers.CharField(required=False, allow_blank=True, max_length=255)


class DisputeRespondSerializer(serializers.Serializer):
    """POST /seller/disputes/<reference>/respond — the store's answer."""

    statement = serializers.CharField(max_length=4000)
    evidence = serializers.ListField(
        child=serializers.URLField(max_length=500),
        required=False,
        allow_empty=True,
    )


class DisputeResolveSerializer(serializers.Serializer):
    """The staff ruling — who wins; the *why* is enforced by the service."""

    resolution = serializers.ChoiceField(choices=DisputeResolution.choices)
    # Optional here on purpose: the mandatory-reason rule lives in the
    # service (same shape as ReturnDecisionSerializer), so the caller gets
    # the domain code `reason_required`, not a generic validation error.
    reason = serializers.CharField(required=False, allow_blank=True, max_length=255)


def serialize_dispute_statement(row):
    """One statement row — party is server truth, never client input."""
    return {
        'party': row.party,
        'party_label': row.get_party_display(),
        'author': row.author.email,
        'body': row.body,
        'created_at': row.created_at.isoformat(),
    }


def serialize_dispute_evidence(row):
    """One evidence row (§17.3 evidence)."""
    return {
        'party': row.party,
        'party_label': row.get_party_display(),
        'added_by': row.added_by.email,
        'url': row.url,
        'caption': row.caption,
        'created_at': row.created_at.isoformat(),
    }


def serialize_dispute_event(event):
    """One customer-safe timeline step (§17.3 audit trail)."""
    return {
        'kind': event.kind,
        'kind_label': event.get_kind_display(),
        'message': event.message,
        'previous_status': event.previous_status,
        'new_status': event.new_status,
        'actor': event.actor.email if event.actor_id and event.actor else 'System',
        'occurred_at': event.created_at.isoformat(),
    }


def serialize_dispute(dispute, *, include_events=True):
    """The dispute as every side reads it (§17.3).

    Both parties and staff see the same record — statements and evidence
    carry their party label so authorship is never ambiguous, and the
    ruling only shows up once it exists.
    """
    payload = {
        'reference': dispute.reference,
        'order_number': dispute.order.number,
        'seller_order_id': dispute.seller_order_id,
        'store_name': dispute.seller_order.store_name if dispute.seller_order_id else '',
        'scope': 'store' if dispute.seller_order_id else 'order',
        'status': dispute.status,
        'status_label': dispute.get_status_display(),
        'is_open': dispute.is_open,
        'reason': dispute.reason,
        'reason_label': dispute.get_reason_display(),
        'statement': dispute.statement,
        'resolution': dispute.resolution,
        'resolution_label': (
            dispute.get_resolution_display() if dispute.resolution else ''
        ),
        'resolution_reason': dispute.resolution_reason,
        'resolved_by': (
            dispute.resolved_by.email if dispute.resolved_by_id else ''
        ),
        'resolved_at': _iso(dispute.resolved_at),
        'return_reference': (
            dispute.return_case.reference if dispute.return_case_id else ''
        ),
        'request_id': dispute.request_id,
        'customer_email': dispute.requested_by.email,
        'created_at': dispute.created_at.isoformat(),
        'statements': [
            serialize_dispute_statement(row) for row in dispute.statements.all()
        ],
        'evidence': [
            serialize_dispute_evidence(row) for row in dispute.evidence.all()
        ],
    }
    if include_events:
        payload['events'] = [
            serialize_dispute_event(e) for e in dispute.events.all()
        ]
    return payload


def serialize_dispute_row(dispute):
    """Compact row for the seller desk and the staff queue."""
    return {
        'reference': dispute.reference,
        'order_number': dispute.order.number,
        'store_name': (
            dispute.seller_order.store_name
            if dispute.seller_order_id else 'All stores'
        ),
        'status': dispute.status,
        'status_label': dispute.get_status_display(),
        'reason': dispute.reason,
        'reason_label': dispute.get_reason_display(),
        'resolution': dispute.resolution,
        'customer_email': dispute.requested_by.email,
        'created_at': dispute.created_at.isoformat(),
    }
