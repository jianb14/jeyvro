"""Resolution domain models (Phase 17 — PROJECT_CONTEXT §6 v1.9, ROADMAP §17).

`OrderRequest` (Phase 11) is the *intake* record a customer files against an
order. Phase 17 turns the eligible ones into adjudicable cases: a
`ReturnCase` owns the verdict, the reverse parcel, the restock ledger and the
refund attribution; `Dispute` owns evidence, statements and the staff ruling.
Statuses move only inside services, and every movement is written twice —
once as an append-only `ReturnEvent`/`DisputeEvent` row the case timeline
reads, and once as an `AuditLog` row the platform audit viewer reads (§9).
"""
from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel
from apps.orders.models import ShipmentStatus


class ReturnReason(models.TextChoices):
    """Why goods are coming back (§17.1 return reason)."""

    DAMAGED = 'damaged', 'Arrived damaged'
    DEFECTIVE = 'defective', 'Defective or faulty'
    WRONG_ITEM = 'wrong_item', 'Wrong item sent'
    NOT_AS_DESCRIBED = 'not_as_described', 'Not as described'
    MISSING_PARTS = 'missing_parts', 'Missing parts or accessories'
    CHANGED_MIND = 'changed_mind', 'Changed my mind'
    OTHER = 'other', 'Other reason'


# Reasons whose goods are assumed unsellable on receipt: a damaged or
# defective item is restocked only when the seller explicitly says so, so the
# default flips here (server-side) rather than in the UI.
NON_RESELLABLE_REASONS = (ReturnReason.DAMAGED, ReturnReason.DEFECTIVE)


class ReturnStatus(models.TextChoices):
    """Return-case lifecycle (§17.1 return status).

    requested → approved / rejected (seller; staff may override) →
    in_transit → received (restock written) → refund_pending → refunded →
    closed. A customer may cancel while the case is still undecided.
    """

    REQUESTED = 'requested', 'Awaiting seller response'
    APPROVED = 'approved', 'Approved — send the items back'
    REJECTED = 'rejected', 'Rejected'
    IN_TRANSIT = 'in_transit', 'Return in transit'
    RECEIVED = 'received', 'Received — restocked'
    REFUND_PENDING = 'refund_pending', 'Refund pending'
    REFUNDED = 'refunded', 'Refunded'
    CLOSED = 'closed', 'Closed'
    CANCELLED = 'cancelled', 'Cancelled by customer'


# Statuses in which a case still occupies its order lines: a second case may
# not claim the same units while one of these is live.
OPEN_RETURN_STATUSES = (
    ReturnStatus.REQUESTED,
    ReturnStatus.APPROVED,
    ReturnStatus.IN_TRANSIT,
    ReturnStatus.RECEIVED,
    ReturnStatus.REFUND_PENDING,
)


class ReturnEventKind(models.TextChoices):
    """Append-only case-timeline entry kinds (§17.1, §17.3 audit trail)."""

    CREATED = 'created', 'Requested'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'
    ADMIN_OVERRIDE = 'admin_override', 'Staff decision'
    SHIPPED = 'shipped', 'Return parcel shipped'
    RECEIVED = 'received', 'Goods received'
    RESTOCKED = 'restocked', 'Stock restored'
    REFUND_ISSUED = 'refund_issued', 'Refund issued'
    REFUNDED = 'refunded', 'Refund settled'
    REFUND_FAILED = 'refund_failed', 'Refund failed'
    CANCELLED = 'cancelled', 'Cancelled'
    CLOSED = 'closed', 'Closed'
    NOTE = 'note', 'Note'


class ReturnCase(TimeStampedModel):
    """One adjudicable return request against an order or a store slice (§17.1).

    The customer states the reason and which lines come back; eligibility and
    the window were verified server-side before anything was written, and the
    window deadline is *snapshotted* so a later policy change can neither
    reopen a closed case nor quietly expire a live one. Money never moves
    from here directly — the refund due is computed from order snapshots
    (§17.2) and the payment ledger is moved only by `apps.payments`.
    """

    Status = ReturnStatus
    Reason = ReturnReason

    reference = models.CharField(
        max_length=32,
        unique=True,
        help_text='Public identifier, e.g. JVRET-20260928-8F3K2Q7A.',
    )
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.PROTECT,
        related_name='return_cases',
    )
    seller_order = models.ForeignKey(
        'orders.SellerOrder',
        on_delete=models.PROTECT,
        related_name='return_cases',
        null=True,
        blank=True,
        help_text='Null = the whole order (every store slice is returning).',
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='return_cases_opened',
        help_text='The customer who filed the return.',
    )
    request = models.ForeignKey(
        'orders.OrderRequest',
        on_delete=models.SET_NULL,
        related_name='return_cases',
        null=True,
        blank=True,
        help_text='The Phase 11 intake row this case resolves, when linked.',
    )
    reason = models.CharField(max_length=24, choices=ReturnReason.choices)
    note = models.TextField(
        blank=True, help_text='The customer’s own words.'
    )
    status = models.CharField(
        max_length=20,
        choices=ReturnStatus.choices,
        default=ReturnStatus.REQUESTED,
    )

    # Eligibility + window snapshots (the Phase 17 verdict, frozen at filing).
    delivered_at = models.DateTimeField(
        null=True, blank=True, help_text='Delivery moment the window was measured from.'
    )
    window_expires_at = models.DateTimeField(
        null=True, blank=True, help_text='Snapshot of the return deadline.'
    )

    # Money snapshot — what the customer is owed once the goods come back.
    refund_due = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Server-computed from order snapshots (§17.2), never client input.',
    )

    # Seller response (§17.1 seller response).
    responded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='return_cases_responded',
        null=True,
        blank=True,
    )
    responded_at = models.DateTimeField(null=True, blank=True)
    response_note = models.CharField(
        max_length=255, blank=True, help_text='Seller’s reply, shown to the customer.'
    )
    decision_reason = models.CharField(
        max_length=255, blank=True, help_text='Why it was approved or rejected.'
    )

    # Staff intervention (§17.1 admin intervention) — the only path for
    # whole-order cases, and the way a seller ruling is re-decided.
    admin_override_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='return_cases_overridden',
        null=True,
        blank=True,
    )
    admin_override_at = models.DateTimeField(null=True, blank=True)
    admin_override_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order'], name='resolutions_case_order_idx'),
            models.Index(fields=['status'], name='resolutions_case_status_idx'),
            models.Index(fields=['requested_by'], name='resolutions_case_user_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(refund_due__gte=0),
                name='resolutions_refund_due_non_negative',
            ),
        ]

    def __str__(self):
        return f'{self.reference} ({self.status})'

    @property
    def is_open(self):
        """True while the case still owns its order lines."""
        return self.status in OPEN_RETURN_STATUSES


class ReturnItem(TimeStampedModel):
    """One order line inside a case, with the units actually coming back.

    Quantity is capped by the service against `OrderItem.quantity` minus what
    other live cases already claimed, so two cases can never return the same
    unit twice. `restock` is the seller's call per line (damaged goods do not
    go back on the shelf by default), and `restocked_at` is the idempotency
    marker: stock for a line moves exactly once, inside `receive_return`.
    """

    case = models.ForeignKey(
        ReturnCase, on_delete=models.CASCADE, related_name='items'
    )
    order_item = models.ForeignKey(
        'orders.OrderItem',
        on_delete=models.PROTECT,
        related_name='return_items',
    )
    quantity = models.PositiveIntegerField()
    restock = models.BooleanField(
        default=True,
        help_text='Whether these units go back on the shelf when received.',
    )
    restocked_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When stock moved for this line; null = nothing has moved yet.',
    )

    class Meta:
        ordering = ['id']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1),
                name='resolutions_item_quantity_positive',
            ),
            models.UniqueConstraint(
                fields=['case', 'order_item'],
                name='resolutions_one_line_per_case',
            ),
        ]

    def __str__(self):
        return f'{self.case.reference}: {self.order_item.product_title} x {self.quantity}'

    @property
    def line_total(self):
        """The paid value of the returned units (order snapshot price)."""
        return self.order_item.unit_price * self.quantity


class ReturnEvent(TimeStampedModel):
    """Append-only case timeline (§17.1 return status, §17.3 audit trail).

    Rows are written by services only and never edited: they carry the
    customer-safe story of the case (who did what, from which status to
    which), while the matching `AuditLog` row carries the platform-audit
    view. `previous_status`/`new_status` make the transition explicit.
    """

    Kind = ReturnEventKind

    case = models.ForeignKey(
        ReturnCase, on_delete=models.CASCADE, related_name='events'
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='return_events',
        null=True,
        blank=True,
        help_text='Null = system-driven (e.g. an automatic close).',
    )
    kind = models.CharField(max_length=20, choices=ReturnEventKind.choices)
    message = models.CharField(max_length=255, blank=True)
    previous_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ['created_at', 'id']
        indexes = [
            models.Index(fields=['case', 'created_at'], name='resolutions_event_case_idx'),
        ]

    def __str__(self):
        return f'{self.case.reference} — {self.kind}'


class ReturnShipment(TimeStampedModel):
    """The reverse parcel — goods travelling *back* to the seller (§17.1).

    The forward flow's `orders.Shipment` cannot be reused: a return parcel
    belongs to a case, not to fulfillment, and its lifecycle ends in
    receipt-and-restock instead of delivery. Status reuses the fulfillment
    vocabulary so the two timelines read the same.
    """

    Status = ShipmentStatus

    case = models.OneToOneField(
        ReturnCase, on_delete=models.CASCADE, related_name='return_shipment'
    )
    tracking_number = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text='Carrier tracking number for the return leg.',
    )
    carrier = models.CharField(
        max_length=32,
        default='manual',
        help_text='Carrier code: manual, jtexpress, lbc, ninjavan.',
    )
    carrier_name = models.CharField(
        max_length=128,
        default='Standard Delivery',
        help_text='Display name of the carrier.',
    )
    status = models.CharField(
        max_length=24,
        choices=ShipmentStatus.choices,
        default=ShipmentStatus.PENDING,
    )
    notes = models.TextField(
        blank=True, help_text='Handling notes, e.g. bring the original packaging.'
    )
    shipped_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['case'], name='resolutions_ship_case_idx'),
            models.Index(fields=['status'], name='resolutions_ship_status_idx'),
        ]

    def __str__(self):
        return f'{self.case.reference} return via {self.tracking_number}'


class DisputeReason(models.TextChoices):
    """Why the buyer escalates (§17.3 dispute creation)."""

    ITEM_NOT_RECEIVED = 'item_not_received', 'Item never arrived'
    NOT_AS_DESCRIBED = 'not_as_described', 'Not as described'
    DAMAGED_IN_TRANSIT = 'damaged_in_transit', 'Arrived damaged'
    WRONG_ITEM = 'wrong_item', 'Wrong item sent'
    RETURN_REJECTED = 'return_rejected', 'Return rejected or ignored'
    REFUND_ISSUE = 'refund_issue', 'Refund missing or wrong'
    SELLER_UNRESPONSIVE = 'seller_unresponsive', 'Seller unresponsive'
    OTHER = 'other', 'Other reason'


class DisputeStatus(models.TextChoices):
    """Dispute lifecycle (§17.3 staff review → resolution).

    Opened by the buyer → the seller may answer with a statement while the
    case sits `open` → staff claim it (`under_review`) and rule (`resolved`);
    the buyer may withdraw it while it is still undecided (`cancelled`).
    """

    OPEN = 'open', 'Open — awaiting response'
    UNDER_REVIEW = 'under_review', 'Under staff review'
    RESOLVED = 'resolved', 'Resolved'
    CANCELLED = 'cancelled', 'Withdrawn by buyer'


# A dispute may only be altered (statements, evidence, withdrawal) while it
# is undecided — once ruled, the record is frozen for the audit trail.
OPEN_DISPUTE_STATUSES = (DisputeStatus.OPEN, DisputeStatus.UNDER_REVIEW)


class DisputeResolution(models.TextChoices):
    """The staff ruling (§17.3 resolution)."""

    BUYER_FAVOR = 'buyer_favor', 'Resolved for the buyer'
    SELLER_FAVOR = 'seller_favor', 'Resolved for the seller'


class DisputeParty(models.TextChoices):
    """Who wrote a statement/evidence row — always derived server-side."""

    CUSTOMER = 'customer', 'Customer'
    SELLER = 'seller', 'Seller'
    STAFF = 'staff', 'Staff'


class DisputeEventKind(models.TextChoices):
    """Append-only dispute-timeline entry kinds (§17.3 audit trail)."""

    CREATED = 'created', 'Dispute opened'
    STATEMENT_ADDED = 'statement_added', 'Statement added'
    EVIDENCE_ADDED = 'evidence_added', 'Evidence added'
    UNDER_REVIEW = 'under_review', 'Staff review started'
    RESOLVED = 'resolved', 'Dispute resolved'
    CANCELLED = 'cancelled', 'Withdrawn'


class Dispute(TimeStampedModel):
    """One buyer escalation against an order or a store slice (§17.3).

    The buyer states the reason and their opening statement; who may read or
    write the case is decided by ownership (buyer / store owner / staff), and
    the party on every statement or evidence row is derived from the caller —
    never sent by the client. The ruling records *who* won and *why*, and
    every movement is written twice: a `DisputeEvent` timeline row for the
    parties and an `AuditLog` row for the platform (§9). Money never moves
    from here — a win for the buyer is settled through the §17.2 payout.
    """

    Status = DisputeStatus
    Reason = DisputeReason
    Resolution = DisputeResolution

    reference = models.CharField(
        max_length=32,
        unique=True,
        help_text='Public identifier, e.g. JVDSP-20260928-8F3K2Q7A.',
    )
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.PROTECT,
        related_name='disputes',
    )
    seller_order = models.ForeignKey(
        'orders.SellerOrder',
        on_delete=models.PROTECT,
        related_name='disputes',
        null=True,
        blank=True,
        help_text='Null = the whole order (every store slice is in dispute).',
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='disputes_opened',
        help_text='The buyer who escalated.',
    )
    request = models.ForeignKey(
        'orders.OrderRequest',
        on_delete=models.SET_NULL,
        related_name='disputes',
        null=True,
        blank=True,
        help_text='The Phase 11 intake row this dispute resolves, when linked.',
    )
    return_case = models.ForeignKey(
        ReturnCase,
        on_delete=models.SET_NULL,
        related_name='disputes',
        null=True,
        blank=True,
        help_text='The return this dispute escalates, when raised against one.',
    )
    reason = models.CharField(max_length=24, choices=DisputeReason.choices)
    statement = models.TextField(
        help_text='The buyer’s opening statement (§17.3 customer statement).'
    )
    status = models.CharField(
        max_length=20,
        choices=DisputeStatus.choices,
        default=DisputeStatus.OPEN,
    )

    # The staff ruling (§17.3 resolution + resolution reason).
    resolution = models.CharField(
        max_length=20,
        choices=DisputeResolution.choices,
        blank=True,
    )
    resolution_reason = models.CharField(max_length=255, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='disputes_resolved',
        null=True,
        blank=True,
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order'], name='resolutions_dispute_order_idx'),
            models.Index(fields=['status'], name='resolutions_dispute_status_idx'),
            models.Index(fields=['requested_by'], name='resolutions_dispute_user_idx'),
        ]

    def __str__(self):
        return f'{self.reference} ({self.status})'

    @property
    def is_open(self):
        """True while the dispute can still be altered by the parties."""
        return self.status in OPEN_DISPUTE_STATUSES


class DisputeStatement(TimeStampedModel):
    """One party's words on a dispute (§17.3 customer/seller statement).

    Append-only: statements are never edited or deleted, and `party` is set
    by the service from the caller's role — a client cannot post as the
    other side.
    """

    dispute = models.ForeignKey(
        Dispute, on_delete=models.CASCADE, related_name='statements'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='dispute_statements',
    )
    party = models.CharField(max_length=16, choices=DisputeParty.choices)
    body = models.TextField()

    class Meta:
        ordering = ['created_at', 'id']
        indexes = [
            models.Index(fields=['dispute', 'created_at'],
                         name='resolutions_stmt_dispute_idx'),
        ]

    def __str__(self):
        return f'{self.dispute.reference} — {self.party}: {self.body[:40]}'


class DisputeEvidence(TimeStampedModel):
    """One evidence attachment on a dispute (§17.3 evidence).

    URL-based for now, exactly like `Message.attachment_url`, until the
    media phase lands real uploads.
    """

    dispute = models.ForeignKey(
        Dispute, on_delete=models.CASCADE, related_name='evidence'
    )
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='dispute_evidence',
    )
    party = models.CharField(max_length=16, choices=DisputeParty.choices)
    url = models.URLField(max_length=500)
    caption = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['created_at', 'id']
        indexes = [
            models.Index(fields=['dispute', 'created_at'],
                         name='resolutions_evid_dispute_idx'),
        ]

    def __str__(self):
        return f'{self.dispute.reference} — {self.url}'


class DisputeEvent(TimeStampedModel):
    """Append-only dispute timeline (§17.3 audit trail).

    Same contract as `ReturnEvent`: rows are written by services only and
    never edited; `previous_status`/`new_status` make each transition
    explicit, and the matching `AuditLog` row carries the platform view.
    """

    Kind = DisputeEventKind

    dispute = models.ForeignKey(
        Dispute, on_delete=models.CASCADE, related_name='events'
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='dispute_events',
        null=True,
        blank=True,
        help_text='Null = system-driven.',
    )
    kind = models.CharField(max_length=20, choices=DisputeEventKind.choices)
    message = models.CharField(max_length=255, blank=True)
    previous_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ['created_at', 'id']
        indexes = [
            models.Index(fields=['dispute', 'created_at'],
                         name='resolutions_event_dispute_idx'),
        ]

    def __str__(self):
        return f'{self.dispute.reference} — {self.kind}'

