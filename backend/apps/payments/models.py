"""Payment domain models (Phase 9 — PROJECT_CONTEXT §6).

Money lives in records, never flags: `Payment` is the server-computed
obligation for exactly one order, `PaymentAttempt` rows record every gateway
interaction, `Refund` rows record money given back, and `PaymentTransaction`
rows are the append-only ledger — capture/refund entries whose sums are the
auditable balance. `WebhookEvent` makes gateway callbacks idempotent (§9.3:
duplicate events are safe). Every amount is Decimal(12,2) and derives from
the order snapshot — never from the client or the gateway claim itself.
"""
from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class PaymentMethod(models.TextChoices):
    """Checkout options; online gateways plug in behind adapters (§6)."""

    COD = 'cod', 'Cash on Delivery'
    CARD = 'card', 'Card'
    GCASH = 'gcash', 'GCash'
    MAYA = 'maya', 'Maya'


class PaymentStatus(models.TextChoices):
    """Payment lifecycle — transitions happen only in payments.services."""

    PENDING = 'pending', 'Pending'
    PAID = 'paid', 'Paid'
    FAILED = 'failed', 'Failed'
    EXPIRED = 'expired', 'Expired'
    CANCELLED = 'cancelled', 'Cancelled'
    PARTIALLY_REFUNDED = 'partially_refunded', 'Partially refunded'
    REFUNDED = 'refunded', 'Refunded'


class Payment(TimeStampedModel):
    """One order's payment record — status is explicit, amount is server truth.

    The amount is copied from `order.grand_total` at creation and re-verified
    before the payment may become `paid` (§6: the gateway is never trusted
    blindly). COD payments carry no expiry; online payments expire after the
    configured window and release their reservation via services.
    """

    Status = PaymentStatus
    Method = PaymentMethod

    reference = models.CharField(
        max_length=32,
        unique=True,
        help_text='Public identifier, e.g. JVPAY-20260925-8F3K2Q7A (services generate it).',
    )
    order = models.OneToOneField(
        'orders.Order',
        on_delete=models.PROTECT,
        related_name='payment',
    )
    method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    status = models.CharField(
        max_length=24,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text='Server-computed from the order snapshot (order.grand_total).',
    )
    currency = models.CharField(max_length=3, default='PHP')
    provider = models.CharField(
        max_length=32,
        blank=True,
        help_text='Adapter that owns the money movement (cod, generic, paymongo…).',
    )
    gateway_reference = models.CharField(
        max_length=128,
        blank=True,
        help_text='The gateway’s own id for this payment (session/intent).',
    )
    checkout_url = models.URLField(
        blank=True, help_text='Where the customer pays (online methods only).'
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Online payments only — after this the order is released.',
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status'], name='payments_status_idx'),
            models.Index(fields=['method'], name='payments_method_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gte=0),
                name='payments_amount_nonnegative',
            ),
        ]

    def __str__(self):
        return f'{self.reference} ({self.method}/{self.status})'

    def _ledger_sum(self, **filters):
        total = self.transactions.filter(**filters).aggregate(
            total=models.Sum('amount')
        )['total']
        return total or Decimal('0.00')

    @property
    def captured_total(self):
        """Money captured for this payment (ledger credits)."""
        return self._ledger_sum(
            kind=PaymentTransaction.Kind.CAPTURE,
            direction=PaymentTransaction.Direction.CREDIT,
        )

    @property
    def refunded_total(self):
        """Money returned so far (ledger debits) — recomputed, never cached."""
        return self._ledger_sum(
            kind=PaymentTransaction.Kind.REFUND,
            direction=PaymentTransaction.Direction.DEBIT,
        )


class AttemptStatus(models.TextChoices):
    """One gateway interaction's outcome."""

    PENDING = 'pending', 'Pending'
    SUCCEEDED = 'succeeded', 'Succeeded'
    FAILED = 'failed', 'Failed'


class PaymentAttempt(TimeStampedModel):
    """Every gateway interaction, kept as history (never the money truth).

    Attempts are the audit trail of what was tried: a checkout session was
    started, a capture succeeded, a failure came back with its reason. The
    ledger (`PaymentTransaction`) stays the money truth.
    """

    Status = AttemptStatus

    payment = models.ForeignKey(
        Payment, on_delete=models.CASCADE, related_name='attempts'
    )
    status = models.CharField(
        max_length=16, choices=AttemptStatus.choices, default=AttemptStatus.PENDING
    )
    gateway_reference = models.CharField(max_length=128, blank=True)
    failure_code = models.CharField(max_length=64, blank=True)
    failure_message = models.CharField(max_length=255, blank=True)
    raw_response = models.JSONField(
        default=dict, blank=True, help_text='Gateway-shaped details, no secrets (C7).'
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payment'], name='payments_attempt_payment_idx'),
        ]

    def __str__(self):
        return f'{self.payment.reference} attempt ({self.status})'


class RefundStatus(models.TextChoices):
    """Refund lifecycle — settled refunds write the ledger reversal."""

    PENDING = 'pending', 'Pending'
    SUCCEEDED = 'succeeded', 'Succeeded'
    FAILED = 'failed', 'Failed'


class Refund(TimeStampedModel):
    """Money returned to the customer — full or partial (§9.4).

    Created by payments.services only, row-locked against the payment so
    parallel refunds can never exceed the captured amount. COD refunds settle
    immediately (cash returned by staff); gateway refunds settle when the
    gateway confirms via webhook.
    """

    Status = RefundStatus

    reference = models.CharField(
        max_length=32,
        unique=True,
        help_text='Public identifier, e.g. JVREF-20260925-8F3K2Q7A.',
    )
    payment = models.ForeignKey(
        Payment, on_delete=models.PROTECT, related_name='refunds'
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=16, choices=RefundStatus.choices, default=RefundStatus.PENDING
    )
    reason = models.CharField(max_length=255, blank=True)
    gateway_reference = models.CharField(max_length=128, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='refunds_issued',
        help_text='Staff member who issued the refund (Phase 13 tools).',
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payment'], name='payments_refund_payment_idx'),
            models.Index(fields=['status'], name='payments_refund_status_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name='payments_refund_amount_positive',
            ),
        ]

    def __str__(self):
        return f'{self.reference} ({self.status})'


class PaymentTransaction(TimeStampedModel):
    """Append-only ledger row — one immutable money movement per row (§6).

    Capture rows split per store (`seller_order`) so seller payouts can be
    derived from records later (§13/§17); refund rows reference the refund.
    Rows are never updated or deleted — the balance is always the sum, which
    is what makes the books replayable.
    """

    class Kind(models.TextChoices):
        CAPTURE = 'capture', 'Capture'
        REFUND = 'refund', 'Refund'

    class Direction(models.TextChoices):
        CREDIT = 'credit', 'Credit'
        DEBIT = 'debit', 'Debit'

    payment = models.ForeignKey(
        Payment, on_delete=models.PROTECT, related_name='transactions'
    )
    seller_order = models.ForeignKey(
        'orders.SellerOrder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ledger_entries',
        help_text='Set on captures — the store slice this money belongs to.',
    )
    refund = models.ForeignKey(
        Refund,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
    )
    kind = models.CharField(max_length=16, choices=Kind.choices)
    direction = models.CharField(max_length=8, choices=Direction.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='PHP')
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['id']
        indexes = [
            models.Index(fields=['payment'], name='payments_txn_payment_idx'),
            models.Index(fields=['kind'], name='payments_txn_kind_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name='payments_txn_amount_positive',
            ),
        ]

    def __str__(self):
        return f'{self.kind}/{self.direction} {self.amount} ({self.payment.reference})'


class WebhookStatus(models.TextChoices):
    """How a gateway callback was handled."""

    RECEIVED = 'received', 'Received'
    PROCESSED = 'processed', 'Processed'
    IGNORED = 'ignored', 'Ignored'
    FAILED = 'failed', 'Failed'


class WebhookEvent(TimeStampedModel):
    """One claimed gateway event — the idempotency record (§9.3).

    (provider, event_id) is unique: a duplicate delivery finds the row and is
    acknowledged without touching payment state. Unverified callbacks never
    reach this table — the signature check comes first.
    """

    Status = WebhookStatus

    provider = models.CharField(max_length=32)
    event_id = models.CharField(max_length=128)
    event_type = models.CharField(max_length=64, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    signature = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=16, choices=WebhookStatus.choices, default=WebhookStatus.RECEIVED
    )
    error = models.CharField(max_length=255, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['provider', 'event_id'],
                name='payments_webhook_unique_event',
            ),
        ]
        indexes = [
            models.Index(
                fields=['provider', 'status'], name='payments_webhook_provider_idx'
            ),
        ]

    def __str__(self):
        return f'{self.provider}:{self.event_id} ({self.status})'
