"""Payment services — the only writers of payment state (§6, payments-skill).

Every transition here is row-locked, writes an explicit status, and leaves
attempt + ledger rows behind: the amount is verified against the order
snapshot before a payment may become `paid` (a gateway claim is never
trusted blindly), repeated calls are safe no-ops — double webhooks and
double clicks can never double-charge — and gateway access always goes
through an adapter (§6/§17). Views stay thin (§8).
"""
import json
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from django.utils.crypto import get_random_string

from apps.audit import services as audit_services
from apps.catalog import services as catalog_services
from apps.catalog.models import StockMovement
from apps.orders.models import Order, OrderItem, SellerOrder
from apps.platform import services as platform_services

from . import adapters
from .models import (
    AttemptStatus,
    Payment,
    PaymentAttempt,
    PaymentMethod,
    PaymentStatus,
    PaymentTransaction,
    Refund,
    RefundStatus,
    WebhookEvent,
    WebhookStatus,
)

# Unambiguous alphabet for payment references (no O/0, I/1, lookalikes).
REFERENCE_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'


class PaymentError(ValueError):
    """Customer-safe payment rejection — code + message, never a stack."""

    def __init__(self, message, *, code='payment_rejected'):
        super().__init__(message)
        self.code = code


class WebhookRejected(PaymentError):
    """A callback that must not touch state (bad signature, bad payload…)."""

    def __init__(self, message, *, code='webhook_rejected', status_code=400):
        super().__init__(message, code=code)
        self.status_code = status_code


def _generate_reference(prefix, model):
    """Unique public identifier, e.g. JVPAY-20260925-8F3K2Q7A."""
    date = timezone.now().strftime('%Y%m%d')
    for _ in range(10):
        candidate = f'{prefix}-{date}-{get_random_string(8, REFERENCE_ALPHABET)}'
        if not model.objects.filter(reference=candidate).exists():
            return candidate
    raise RuntimeError(f'Could not allocate a unique {prefix} reference.')


def _parse_amount(value):
    """Gateway-claimed or staff-entered amount → Decimal(12,2), else None."""
    try:
        return Decimal(str(value)).quantize(Decimal('0.01'))
    except (InvalidOperation, TypeError, ValueError):
        return None


def payment_expiry_hours():
    """The window is platform configuration now (§6 v1.13): the DB row
    wins; the env setting only seeds that row's first creation."""
    return platform_services.payment_window_hours()


def start_payment(order, method=PaymentMethod.COD):
    """Creates the order's payment — the amount is order truth, never input.

    COD just waits for delivery; online methods open a checkout session
    through their adapter. An unavailable method is refused *before* any
    order row commits (the caller's transaction rolls back), so an
    unpayable order can never exist.
    """
    if Payment.objects.filter(order=order).exists():
        raise PaymentError('This order already has a payment.', code='payment_exists')
    try:
        adapter = adapters.get_adapter(method)
    except ValueError as exc:
        raise PaymentError('Unsupported payment method.', code='unknown_method') from exc
    if not adapter.is_available():
        raise PaymentError(
            adapter.unavailable_note or 'This payment method is not available yet.',
            code='payment_method_unavailable',
        )
    payment = Payment.objects.create(
        reference=_generate_reference('JVPAY', Payment),
        order=order,
        method=method,
        status=PaymentStatus.PENDING,
        amount=order.grand_total,
        currency='PHP',
        provider=adapter.provider,
        expires_at=(
            None if method == PaymentMethod.COD
            else timezone.now() + timedelta(hours=payment_expiry_hours())
        ),
    )
    if method == PaymentMethod.COD:
        return payment  # cash moves on delivery — nothing to start
    try:
        session = adapter.create_checkout(payment)
    except adapters.GatewayNotConfigured as exc:
        raise PaymentError(str(exc), code='payment_method_unavailable') from exc
    except adapters.GatewayError as exc:
        raise PaymentError(str(exc), code='gateway_error') from exc
    if session.gateway_reference or session.checkout_url:
        payment.gateway_reference = session.gateway_reference
        payment.checkout_url = session.checkout_url
        payment.save(update_fields=['gateway_reference', 'checkout_url', 'updated_at'])
        PaymentAttempt.objects.create(
            payment=payment,
            status=AttemptStatus.PENDING,
            gateway_reference=session.gateway_reference,
            raw_response=session.raw,
        )
    return payment


def cancel_pending_payment(order, *, actor=None):
    """Order-cancellation path: a still-pending payment is voided, nothing else."""
    payment = Payment.objects.filter(order=order).first()
    if payment is None or payment.status != PaymentStatus.PENDING:
        return None
    payment.status = PaymentStatus.CANCELLED
    payment.save(update_fields=['status', 'updated_at'])
    audit_services.log_event(
        actor,
        'payment.cancelled',
        payment,
        detail={'order': order.number, 'method': payment.method},
    )
    return payment


def _lock_payment(payment_pk):
    return (
        Payment.objects.select_for_update()
        .select_related('order')
        .get(pk=payment_pk)
    )


def _order_items(order):
    return list(
        OrderItem.objects.filter(seller_order__order=order).select_related('variant')
    )


def mark_paid(payment, *, gateway_reference='', source='manual', actor=None,
              claimed_amount=None):
    """Captures the payment — verified against order truth, idempotent.

    A duplicate capture (double webhook, staff double-click) finds the
    payment already paid and returns it unchanged: no second attempt row and
    no second ledger entry — the whole point of §9.3. When the gateway sends
    an amount it must equal the server-computed amount, or nothing changes.
    """
    with transaction.atomic():
        payment = _lock_payment(payment.pk)
        if payment.status == PaymentStatus.PAID:
            return payment  # duplicate capture — already done, change nothing
        if payment.status != PaymentStatus.PENDING:
            raise PaymentError(
                'This payment can no longer be captured.', code='not_payable'
            )
        if claimed_amount is not None and _parse_amount(claimed_amount) != payment.amount:
            raise PaymentError(
                'The gateway amount does not match the order total.',
                code='amount_mismatch',
            )
        order = Order.objects.select_for_update().get(pk=payment.order_id)
        for item in _order_items(order):
            # Reservation → sale: on_hand and reserved both drop (§6 v1.7).
            catalog_services.commit_sale(
                item.variant,
                item.quantity,
                actor=actor,
                note=f'payment {payment.reference}',
            )
        now = timezone.now()
        payment.status = PaymentStatus.PAID
        payment.paid_at = now
        payment.failure_reason = ''
        if gateway_reference:
            payment.gateway_reference = gateway_reference
        payment.save(update_fields=[
            'status', 'paid_at', 'failure_reason', 'gateway_reference', 'updated_at',
        ])
        PaymentAttempt.objects.create(
            payment=payment,
            status=AttemptStatus.SUCCEEDED,
            gateway_reference=gateway_reference,
            raw_response={'source': source},
        )
        for seller_order in order.seller_orders.all():
            # One capture row per store: seller payouts derive from these (§17).
            PaymentTransaction.objects.create(
                payment=payment,
                seller_order=seller_order,
                kind=PaymentTransaction.Kind.CAPTURE,
                direction=PaymentTransaction.Direction.CREDIT,
                amount=seller_order.total,
                currency=payment.currency,
                note=f'capture {source}',
            )
        # Only advance non-fulfillment statuses to PAID
        if order.status in (Order.Status.PLACED, Order.Status.AWAITING_PAYMENT):
            order.status = Order.Status.PAID
            order.save(update_fields=['status', 'updated_at'])
        order.seller_orders.filter(
            status__in=[SellerOrder.Status.PLACED, SellerOrder.Status.AWAITING_PAYMENT]
        ).update(status=SellerOrder.Status.PAID, updated_at=now)
        audit_services.log_event(
            actor,
            'payment.captured',
            payment,
            detail={
                'order': order.number,
                'amount': str(payment.amount),
                'method': payment.method,
                'source': source,
            },
        )
    return payment


def _fail_payment(payment, order, reason, *, source, code='', actor=None,
                  status=PaymentStatus.FAILED, action='payment.failed'):
    """Shared dead-end: payment record + attempt + released stock + order."""
    now = timezone.now()
    payment.status = status
    payment.failure_reason = reason[:255]
    payment.save(update_fields=['status', 'failure_reason', 'updated_at'])
    PaymentAttempt.objects.create(
        payment=payment,
        status=AttemptStatus.FAILED,
        failure_code=code[:64],
        failure_message=reason[:255],
        raw_response={'source': source},
    )
    for item in _order_items(order):
        catalog_services.release_stock(item.variant, item.quantity)
    order.status = Order.Status.CANCELLED
    order.save(update_fields=['status', 'updated_at'])
    order.seller_orders.update(status=SellerOrder.Status.CANCELLED, updated_at=now)
    audit_services.log_event(
        actor,
        action,
        payment,
        detail={'order': order.number, 'reason': reason, 'source': source},
    )


def mark_failed(payment, reason, *, source='gateway', code='', actor=None):
    """A payment attempt failed — the order dies and its stock is released."""
    with transaction.atomic():
        payment = _lock_payment(payment.pk)
        if payment.status == PaymentStatus.FAILED:
            return payment  # duplicate failure event — change nothing
        if payment.status != PaymentStatus.PENDING:
            raise PaymentError('Only pending payments can fail.', code='not_failable')
        order = Order.objects.select_for_update().get(pk=payment.order_id)
        _fail_payment(payment, order, reason, source=source, code=code, actor=actor)
    return payment


def expire_overdue_payments(*, now=None):
    """Unpaid online payments past their window: expire + release (§9.1).

    COD never expires (cash is due at delivery). Returns the expired
    payments — the management command (cron entry point) calls this.
    """
    now = now or timezone.now()
    overdue = list(
        Payment.objects.filter(status=PaymentStatus.PENDING, expires_at__lte=now)
        .exclude(method=PaymentMethod.COD)
        .values_list('pk', flat=True)
    )
    expired = []
    for payment_pk in overdue:
        with transaction.atomic():
            payment = _lock_payment(payment_pk)
            if payment.status != PaymentStatus.PENDING:
                continue  # another worker paid/cancelled it first
            order = Order.objects.select_for_update().get(pk=payment.order_id)
            _fail_payment(
                payment,
                order,
                'The payment window expired before the order was paid.',
                source='expiry',
                code='expired',
                status=PaymentStatus.EXPIRED,
                action='payment.expired',
            )
            expired.append(payment)
    return expired


def refund(payment, amount, *, reason='', actor=None):
    """Refund against a captured payment — full or partial (§9.4).

    Row-locked and balance-checked, so parallel refund requests can never
    exceed what was captured. COD settles immediately (cash handed back by
    staff); a gateway refund stays pending until its webhook confirms.
    """
    with transaction.atomic():
        payment = _lock_payment(payment.pk)
        if payment.status not in (PaymentStatus.PAID, PaymentStatus.PARTIALLY_REFUNDED):
            raise PaymentError(
                'Only captured payments can be refunded.', code='not_refundable'
            )
        amount = _parse_amount(amount)
        if amount is None or amount <= 0:
            raise PaymentError(
                'Enter a refund amount greater than zero.', code='invalid_amount'
            )
        already_refunded = (
            payment.refunds.filter(status=RefundStatus.SUCCEEDED)
            .aggregate(total=Sum('amount'))['total']
            or Decimal('0.00')
        )
        if amount > payment.amount - already_refunded:
            raise PaymentError(
                'The refund exceeds the refundable balance.',
                code='refund_exceeds_balance',
            )
        record = Refund.objects.create(
            reference=_generate_reference('JVREF', Refund),
            payment=payment,
            amount=amount,
            reason=reason[:255],
            actor=actor,
        )
        adapter = adapters.get_adapter(payment.method)
        try:
            result = adapter.refund(record)
        except adapters.GatewayNotConfigured as exc:
            # Nothing was requested anywhere — the whole refund rolls back.
            raise PaymentError(str(exc), code='gateway_not_configured') from exc
        except adapters.GatewayError as exc:
            raise PaymentError(str(exc), code='gateway_error') from exc
        record.gateway_reference = result.get('gateway_reference', '') or ''
        outcome = result.get('status', RefundStatus.PENDING)
        if outcome == RefundStatus.FAILED:
            record.status = RefundStatus.FAILED
            record.save(update_fields=['status', 'gateway_reference', 'updated_at'])
            audit_services.log_event(
                actor,
                'refund.failed',
                record,
                detail={'payment': payment.reference, 'amount': str(amount)},
            )
            return record
        record.save(update_fields=['gateway_reference', 'updated_at'])
        if outcome == RefundStatus.SUCCEEDED:
            _settle_refund(record, actor=actor)
        return record


def _settle_refund(refund, *, actor=None):
    """A refund succeeded: reverse the ledger, update payment + order state.

    Full refunds also restore the reserved-then-sold stock (§6 rule 7 —
    Phase 17 builds the return-shipment flow on top of this foundation).
    """
    payment = _lock_payment(refund.payment_id)
    if payment.transactions.filter(refund=refund).exists():
        return refund  # already settled — duplicate confirmation, no-op
    refund.status = RefundStatus.SUCCEEDED
    refund.save(update_fields=['status', 'updated_at'])
    PaymentTransaction.objects.create(
        payment=payment,
        refund=refund,
        kind=PaymentTransaction.Kind.REFUND,
        direction=PaymentTransaction.Direction.DEBIT,
        amount=refund.amount,
        currency=payment.currency,
        note=f'refund {refund.reference}',
    )
    refunded_total = payment.refunded_total
    is_full = refunded_total >= payment.amount
    order = Order.objects.select_for_update().get(pk=payment.order_id)
    if is_full:
        payment.status = PaymentStatus.REFUNDED
        for item in _order_items(order):
            catalog_services.adjust_stock(
                actor,
                item.variant,
                delta=item.quantity,
                reason=StockMovement.Reason.RESTOCK,
                note=f'refund {refund.reference}',
            )
        order.status = Order.Status.REFUNDED
        order.save(update_fields=['status', 'updated_at'])
        order.seller_orders.update(
            status=SellerOrder.Status.REFUNDED, updated_at=timezone.now()
        )
    else:
        payment.status = PaymentStatus.PARTIALLY_REFUNDED
    payment.save(update_fields=['status', 'updated_at'])
    audit_services.log_event(
        actor,
        'refund.settled',
        refund,
        detail={
            'payment': payment.reference,
            'amount': str(refund.amount),
            'full': is_full,
            'refunded_total': str(refunded_total),
        },
    )
    return refund


def process_webhook(*, provider, body, signature):
    """Verified, idempotent webhook intake (§9.3).

    Order of operations: signature → payload parse → resolve the payment or
    refund being claimed → claim the (provider, event_id) pair → apply.
    Unverified or malformed callbacks change nothing; a duplicate event is
    acknowledged without touching state; an unknown reference is refused
    with 404 *without* claiming the event, so a gateway retry can still
    succeed once the payment exists. Returns (event, duplicate).
    """
    adapter = adapters.get_webhook_adapter(provider)
    if adapter is None:
        raise WebhookRejected(
            'Unknown payment provider.', code='unknown_provider', status_code=404
        )
    if not adapter.verify_webhook_signature(body, signature):
        raise WebhookRejected(
            'Signature verification failed.', code='invalid_signature'
        )
    try:
        payload = json.loads(body.decode('utf-8'))
    except (ValueError, UnicodeDecodeError) as exc:
        raise WebhookRejected(
            'Webhook payload is not valid JSON.', code='invalid_payload'
        ) from exc
    if not isinstance(payload, dict):
        raise WebhookRejected(
            'Webhook payload must be a JSON object.', code='invalid_payload'
        )
    try:
        event_data = adapter.parse_event(payload)
    except adapters.GatewayError as exc:
        raise WebhookRejected(str(exc), code='invalid_payload') from exc

    payment = Payment.objects.filter(
        Q(reference=event_data.reference) | Q(gateway_reference=event_data.reference)
    ).first()
    refund = None
    if payment is None:
        refund = Refund.objects.filter(
            Q(reference=event_data.reference)
            | Q(gateway_reference=event_data.reference)
        ).first()
    if payment is None and refund is None:
        raise WebhookRejected(
            'Unknown payment reference.', code='unknown_reference', status_code=404
        )

    with transaction.atomic():
        event, created = WebhookEvent.objects.get_or_create(
            provider=provider,
            event_id=event_data.event_id,
            defaults={
                'event_type': event_data.event_type,
                'payload': payload,
                'signature': signature[:255],
            },
        )
        if not created:
            return event, True  # already handled — acknowledged, nothing changes
        # Serialize parallel copies of the same event id: the second worker
        # waits here, then sees `processed_at` and is treated as a duplicate.
        event = WebhookEvent.objects.select_for_update().get(pk=event.pk)
        status_value, error = _apply_event(event_data, payment=payment, refund=refund)
        event.status = status_value
        event.error = error[:255]
        event.processed_at = timezone.now()
        event.save(update_fields=['status', 'error', 'processed_at', 'updated_at'])
    return event, False


def _apply_event(event_data, *, payment, refund):
    """Apply one verified event; returns (WebhookStatus, error).

    State changes only through the same services staff flows use — a
    webhook is just another caller that had to prove it is genuine.
    """
    event_type = event_data.event_type
    source = f'webhook:{event_type}'

    if event_type in ('payment.paid', 'payment.captured'):
        if payment is None:
            return WebhookStatus.IGNORED, 'payment_not_found'
        if payment.status == PaymentStatus.PAID:
            return WebhookStatus.IGNORED, 'already_paid'
        if payment.status != PaymentStatus.PENDING:
            return WebhookStatus.IGNORED, f'not_pending:{payment.status}'
        try:
            mark_paid(payment, source=source, claimed_amount=event_data.amount)
        except PaymentError as exc:
            return WebhookStatus.FAILED, f'{exc.code}: {exc}'
        return WebhookStatus.PROCESSED, ''

    if event_type in ('payment.failed', 'payment.expired'):
        if payment is None:
            return WebhookStatus.IGNORED, 'payment_not_found'
        if payment.status == PaymentStatus.FAILED:
            return WebhookStatus.IGNORED, 'already_failed'
        if payment.status != PaymentStatus.PENDING:
            return WebhookStatus.IGNORED, f'not_pending:{payment.status}'
        data = event_data.raw.get('data') or {}
        reason = str(
            data.get('failure_reason') or 'The payment failed at the gateway.'
        )
        mark_failed(payment, reason, source=source, code=event_type)
        return WebhookStatus.PROCESSED, ''

    if event_type in ('refund.succeeded', 'refund.updated', 'refund.failed'):
        if refund is None:
            return WebhookStatus.IGNORED, 'refund_not_found'
        if event_type == 'refund.failed':
            if refund.status == RefundStatus.FAILED:
                return WebhookStatus.IGNORED, 'already_failed'
            refund.status = RefundStatus.FAILED
            refund.save(update_fields=['status', 'updated_at'])
            return WebhookStatus.PROCESSED, ''
        if refund.status == RefundStatus.SUCCEEDED:
            return WebhookStatus.IGNORED, 'already_settled'
        _settle_refund(refund, actor=None)
        return WebhookStatus.PROCESSED, ''

    return WebhookStatus.IGNORED, f'unhandled_type:{event_type}'
