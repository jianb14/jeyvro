"""Resolution services — the only place a return case changes (§17.1–§17.3).

Rules live here, not in views and not in the UI: eligibility and the return
window are server verdicts computed from order/fulfillment snapshots, the
case is written inside one transaction under a row lock, and stock moves only
through the catalog services. Money is never invented here either: the case
prices what it owes from order snapshots, and the payout itself is always
`apps.payments.refund()` — the single owner of the ledger. The flag
`restock=False` on that call is how the two stay honest: this flow has already
returned exactly the case's lines to the shelf (§17.1, §17.2).
"""
import math
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.utils.crypto import get_random_string

from apps.audit import services as audit_services
from apps.catalog import services as catalog_services
from apps.catalog.models import StockMovement
from apps.notifications import services as notification_services
from apps.notifications.models import NotificationCategory
from apps.payments import services as payment_services
from apps.payments.models import (
    PaymentStatus,
    RefundStatus as PaymentRefundStatus,
)
from apps.orders.models import (
    Order,
    OrderItem,
    OrderRequest,
    OrderStatus,
    RequestStatus,
    SellerOrder,
)

from . import policies
from .models import (
    NON_RESELLABLE_REASONS,
    OPEN_DISPUTE_STATUSES,
    OPEN_RETURN_STATUSES,
    Dispute,
    DisputeEvent,
    DisputeEventKind,
    DisputeEvidence,
    DisputeParty,
    DisputeReason,
    DisputeResolution,
    DisputeStatement,
    DisputeStatus,
    ReturnCase,
    ReturnEvent,
    ReturnEventKind,
    ReturnItem,
    ReturnReason,
    ReturnShipment,
    ReturnStatus,
)

REFERENCE_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
FULFILLED_STATUSES = (OrderStatus.DELIVERED, OrderStatus.COMPLETED)


class ReturnError(ValueError):
    """Customer/seller-safe rejection — code + message, never a stack."""

    def __init__(self, message, *, code='return_rejected'):
        super().__init__(message)
        self.code = code


def _generate_reference():
    """Unique public identifier: JVRET-YYYYMMDD-XXXXXXXX (CONVENTIONS §2.2)."""
    date = timezone.now().strftime('%Y%m%d')
    for _ in range(10):
        candidate = f'JVRET-{date}-{get_random_string(8, REFERENCE_ALPHABET)}'
        if not ReturnCase.objects.filter(reference=candidate).exists():
            return candidate
    raise RuntimeError('Could not allocate a unique return reference.')


def _money(value):
    return policies.quantize_money(value or Decimal('0.00'))


def resolve_slices(order, seller_order_id=None):
    """Which store slices a return targets — one slice, or the whole order."""
    slices = list(order.seller_orders.all())
    if seller_order_id in (None, '', '0'):
        return slices
    target = [so for so in slices if str(so.pk) == str(seller_order_id)]
    if not target:
        raise ReturnError('That store is not part of this order.', code='invalid_slice')
    return target


def _delivered_at(slices):
    """When the *last* of the targeted slices was delivered ("" = never)."""
    moments = [
        shipment.delivered_at
        for seller_order in slices
        for shipment in seller_order.shipments.all()
        if shipment.delivered_at
    ]
    return max(moments) if moments else None


def evaluate_return_eligibility(order, seller_order_id=None, *, at=None):
    """The server verdict behind the return button (§17.1 eligibility/window).

    A return is only possible while the targeted slices are delivered and
    inside the return window; every refusal carries a customer-safe code and
    message so the UI can explain itself without guessing. Returns the verdict
    plus the window snapshot the case will store.
    """
    at = at or timezone.now()
    try:
        slices = resolve_slices(order, seller_order_id)
    except ReturnError as exc:
        return {'eligible': False, 'code': exc.code, 'reason': str(exc),
                'delivered_at': None, 'window_expires_at': None, 'days_left': 0,
                'lines': []}

    if order.status in (OrderStatus.CANCELLED, OrderStatus.REFUNDED):
        return {'eligible': False, 'code': 'order_closed',
                'reason': 'This order is already closed.',
                'delivered_at': None, 'window_expires_at': None, 'days_left': 0,
                'lines': []}

    if not slices or not all(so.status in FULFILLED_STATUSES for so in slices):
        return {'eligible': False, 'code': 'not_delivered',
                'reason': 'You can request a return once the items have been delivered.',
                'delivered_at': None, 'window_expires_at': None, 'days_left': 0,
                'lines': []}

    delivered_at = _delivered_at(slices)
    if delivered_at is None:
        # Delivered slice with no timestamp (legacy/manual status) — the
        # window cannot be measured, so it is treated as open.
        return {'eligible': True, 'code': '', 'reason': '',
                'delivered_at': None, 'window_expires_at': None, 'days_left': 0,
                'lines': returnable_lines(order, seller_order_id)}

    expires_at = policies.return_window_deadline(delivered_at)
    if at > expires_at:
        return {'eligible': False, 'code': 'window_expired',
                'reason': (
                    f'The {policies.return_window_days()}-day return window for this '
                    'order has closed.'
                ),
                'delivered_at': delivered_at, 'window_expires_at': expires_at,
                'days_left': 0, 'lines': []}

    return {
        'eligible': True,
        'code': '',
        'reason': '',
        'delivered_at': delivered_at,
        'window_expires_at': expires_at,
        # Ceil, not `.days`: moments after delivery the window is still a full
        # 7 days minus milliseconds, which `.days` would floor to 6.
        'days_left': max(
            0, math.ceil((expires_at - at).total_seconds() / 86400)
        ),
        'lines': returnable_lines(order, seller_order_id),
    }



# Units are considered spent once a case is decided-and-refunded, so a second
# case can never claim the same unit twice.
CLAIMED_RETURN_STATUSES = tuple(OPEN_RETURN_STATUSES) + (ReturnStatus.REFUNDED,)


def _claimed_quantities(order):
    """OrderItem id → units already claimed by live/refunded cases."""
    rows = (
        ReturnItem.objects.filter(
            case__order=order, case__status__in=CLAIMED_RETURN_STATUSES
        )
        .values('order_item_id')
        .annotate(total=Sum('quantity'))
    )
    return {row['order_item_id']: row['total'] for row in rows}


def _line_rows(slices, order):
    """Every order line inside the slices, with what is still returnable."""
    claimed = _claimed_quantities(order)
    rows = []
    for seller_order in slices:
        for item in seller_order.items.all().order_by('id'):
            taken = claimed.get(item.id, 0)
            rows.append({
                'order_item_id': item.id,
                'seller_order_id': seller_order.pk,
                'store_name': seller_order.store_name,
                'product_title': item.product_title,
                'variant_name': item.variant_name,
                'sku': item.sku,
                'unit_price': str(_money(item.unit_price)),
                'quantity': item.quantity,
                'claimed': taken,
                'remaining': max(0, item.quantity - taken),
            })
    return rows


def returnable_lines(order, seller_order_id=None):
    """What the customer may still send back (§17.1) — [] when nothing is."""
    try:
        slices = resolve_slices(order, seller_order_id)
    except ReturnError:
        return []
    return _line_rows(slices, order)


def calculate_refund_due(order, lines):
    """What returning these lines is worth (§17.2 refund calculation).

    Line truth comes from the order snapshots (never the live catalog), the
    order-level promotion/voucher discounts are apportioned to the lines that
    already enjoyed them, and a store slice's shipping fee comes back only
    when *every* line of that slice is returning — a partial return still
    consumed the delivery. Pure function: same inputs, same cents.
    """
    order_items = list(
        OrderItem.objects.filter(seller_order__order=order).order_by('id')
    )
    line_totals = [item.unit_price * item.quantity for item in order_items]
    allocated = policies.allocate_discount(
        line_totals, order.promotion_discount + order.discount_total
    )
    discount_by_item = {
        item.id: allocated[idx] for idx, item in enumerate(order_items)
    }

    returned = {}
    slices_touched = set()
    for item, quantity in lines:
        returned[item.id] = returned.get(item.id, 0) + quantity
        slices_touched.add(item.seller_order_id)

    total = Decimal('0.00')
    for item, quantity in lines:
        if quantity <= 0:
            continue
        discount_share = discount_by_item.get(item.id, Decimal('0.00'))
        if item.quantity:
            discount_share = policies.quantize_money(
                discount_share * (Decimal(quantity) / Decimal(item.quantity))
            )
        total += policies.refundable_amount(
            item.unit_price * quantity, discount_share
        )

    # Shipping comes back only on a fully-returned slice (§17.2).
    for seller_order in order.seller_orders.all():
        if seller_order.pk not in slices_touched:
            continue
        slice_items = list(seller_order.items.all())
        if not slice_items:
            continue
        everything_back = all(
            returned.get(entry.id, 0) >= entry.quantity for entry in slice_items
        )
        if everything_back and seller_order.shipping_fee > Decimal('0.00'):
            total += seller_order.shipping_fee

    return policies.quantize_money(total)


def _notify(user, *, title, message, action_url):
    """Phase 15 wiring — both sides hear about a case (§15.3)."""
    if user is None:
        return
    notification_services.create_notification(
        user,
        category=NotificationCategory.ORDERS,
        title=title,
        message=message,
        action_url=action_url,
    )


def _record(case, *, actor, kind, audit_action, new_status=None, message='',
            detail=None):
    """One case transition: timeline row + audit row, always together."""
    previous = case.status
    fields = ['updated_at']
    if new_status is not None and new_status != previous:
        case.status = new_status
        fields.append('status')
    case.save(update_fields=fields)
    ReturnEvent.objects.create(
        case=case,
        actor=actor,
        kind=kind,
        message=message[:255],
        previous_status=previous,
        new_status=case.status,
    )
    audit_services.log_event(
        actor,
        audit_action,
        case,
        detail={
            'return': case.reference,
            'order': case.order.number,
            'from': previous,
            'to': case.status,
            **(detail or {}),
        },
    )


def _resolve_linked_request(case, actor):
    """The Phase 11 intake row this case answers is now resolved (§11.3)."""
    linked = case.request
    if linked is None or linked.status != RequestStatus.PENDING:
        return
    linked.status = RequestStatus.RESOLVED
    linked.save(update_fields=['status', 'updated_at'])
    audit_services.log_event(
        actor,
        'order.request_resolved',
        linked,
        detail={'order': case.order.number, 'return': case.reference},
    )


def apply_return(user, number, *, reason, note='', seller_order_id=None,
                 lines=None, request_id=None):
    """Files a return case against the customer's own order (§17.1).

    The client sends only a reason, a note, line quantities, and (optionally)
    the Phase 11 request it answers — eligibility, the window, the line caps
    and the refund due are all decided here. One transaction, one row lock on
    the order: two parallel submits serialize, and the loser sees the winner's
    open case and is refused instead of double-booking the same units.
    """
    reason = (reason or '').strip()
    if reason not in ReturnReason.values:
        raise ReturnError('Choose a valid return reason.', code='invalid_reason')

    requested = {}
    for entry in lines or []:
        try:
            order_item_id = int(entry['order_item_id'])
            quantity = int(entry['quantity'])
        except (KeyError, TypeError, ValueError):
            raise ReturnError(
                'Each return line needs an item and a quantity.', code='invalid_lines'
            ) from None
        if quantity < 1:
            raise ReturnError(
                'Return quantities must be at least 1.', code='invalid_lines'
            )
        requested[order_item_id] = requested.get(order_item_id, 0) + quantity
    if not requested:
        raise ReturnError('Choose at least one item to return.', code='no_lines')

    with transaction.atomic():
        order = (
            Order.objects.select_for_update()
            .filter(number=number, user=user)
            .first()
        )
        if order is None:
            raise Order.DoesNotExist(f'Order {number} not found.')

        verdict = evaluate_return_eligibility(order, seller_order_id)
        if not verdict['eligible']:
            raise ReturnError(verdict['reason'], code=verdict['code'])

        slices = resolve_slices(order, seller_order_id)
        open_cases = ReturnCase.objects.filter(
            order=order, status__in=OPEN_RETURN_STATUSES
        )
        if len(slices) == 1:
            duplicate = open_cases.filter(seller_order_id=slices[0].pk).exists()
        else:
            duplicate = open_cases.exists()
        if duplicate:
            raise ReturnError(
                'You already have an open return for these items.', code='case_exists'
            )

        items_by_id = {
            item.id: item
            for seller_order in slices
            for item in seller_order.items.all()
        }
        rows = {row['order_item_id']: row for row in _line_rows(slices, order)}
        line_pairs = []
        for order_item_id, quantity in requested.items():
            row = rows.get(order_item_id)
            item = items_by_id.get(order_item_id)
            if row is None or item is None:
                raise ReturnError(
                    'That item is not part of this order.', code='invalid_item'
                )
            if quantity > row['remaining']:
                raise ReturnError(
                    f"Only {row['remaining']} of “{row['product_title']}” "
                    'can still be returned.',
                    code='quantity_exceeded',
                )
            line_pairs.append((item, quantity))

        linked_request = None
        if request_id not in (None, '', 0, '0'):
            linked_request = OrderRequest.objects.filter(
                pk=request_id, order=order, order__user=user
            ).first()
            if linked_request is None:
                raise ReturnError(
                    'That request does not belong to this order.',
                    code='invalid_request',
                )

        delivered_at = _delivered_at(slices)
        case = ReturnCase.objects.create(
            reference=_generate_reference(),
            order=order,
            seller_order=slices[0] if len(slices) == 1 else None,
            requested_by=user,
            request=linked_request,
            reason=reason,
            note=(note or '').strip()[:2000],
            delivered_at=delivered_at,
            window_expires_at=policies.return_window_deadline(delivered_at),
            refund_due=calculate_refund_due(order, line_pairs),
        )
        for item, quantity in line_pairs:
            ReturnItem.objects.create(
                case=case,
                order_item=item,
                quantity=quantity,
                # Damaged/defective goods do not go back on the shelf unless
                # the seller says so (§17.1 restocking).
                restock=reason not in NON_RESELLABLE_REASONS,
            )
        _record(
            case,
            actor=user,
            kind=ReturnEventKind.CREATED,
            audit_action='return.requested',
            message=f'Return requested — {case.get_reason_display()}',
            detail={'refund_due': str(case.refund_due)},
        )
        for seller_order in slices:
            _notify(
                seller_order.store.user,
                title='New return request',
                message=(
                    f'{case.reference} · {seller_order.store_name} · '
                    f'{case.get_reason_display()}'
                ),
                action_url='/seller/returns',
            )
    return case


# A seller may respond while the case is undecided, and a staff member may
# re-decide it at any of these points — but never once the goods are back.
DECIDABLE_STATUSES = (
    ReturnStatus.REQUESTED,
    ReturnStatus.REJECTED,
    ReturnStatus.APPROVED,
)

DECISIONS = ('approve', 'reject')


def _decide(case, user, *, decision, reason, note='', override=False):
    """Shared approve/reject writer — used by the seller and the staff paths."""
    if decision not in DECISIONS:
        raise ReturnError('Choose approve or reject.', code='invalid_decision')
    reason = (reason or '').strip()
    if decision == 'reject' and not reason:
        raise ReturnError('Tell the customer why the return was rejected.',
                          code='reason_required')
    if case.status not in DECIDABLE_STATUSES:
        raise ReturnError(
            'This return has already moved past the decision stage.',
            code='not_decidable',
        )

    previous = case.status
    new_status = (
        ReturnStatus.APPROVED if decision == 'approve' else ReturnStatus.REJECTED
    )
    case.status = new_status
    case.response_note = (note or case.response_note or '')[:255]
    case.decision_reason = reason[:255]
    fields = ['status', 'response_note', 'decision_reason', 'updated_at']
    if not override:
        case.responded_by = user
        case.responded_at = timezone.now()
        fields += ['responded_by', 'responded_at']
    else:
        case.admin_override_by = user
        case.admin_override_at = timezone.now()
        case.admin_override_reason = reason[:255]
        fields += ['admin_override_by', 'admin_override_at', 'admin_override_reason']
    case.save(update_fields=fields)

    ReturnEvent.objects.create(
        case=case,
        actor=user,
        kind=(
            ReturnEventKind.ADMIN_OVERRIDE if override
            else (ReturnEventKind.APPROVED if decision == 'approve'
                  else ReturnEventKind.REJECTED)
        ),
        message=(reason or case.response_note)[:255],
        previous_status=previous,
        new_status=new_status,
    )
    audit_services.log_event(
        user,
        'return.admin_decision' if override else f'return.{decision}d',
        case,
        detail={
            'return': case.reference,
            'order': case.order.number,
            'from': previous,
            'to': new_status,
            'reason': reason,
            'refund_due': str(case.refund_due),
        },
    )
    return case


def respond_to_return(user, reference, *, decision, reason='', note=''):
    """Seller ruling on their own store's case (§17.1 seller response).

    Seller-scoped at the query level: a case that belongs to another store —
    or a whole-order case, which support adjudicates — simply does not exist
    for this caller, so there is nothing to leak or to tamper with.
    """
    with transaction.atomic():
        case = (
            # `of=('self')` — Postgres cannot FOR UPDATE the nullable side of
            # seller_order's LEFT JOIN, so only the case row is locked.
            ReturnCase.objects.select_for_update(of=('self',))
            .select_related('order', 'seller_order__store')
            .filter(reference=reference, seller_order__store__user=user)
            .first()
        )
        if case is None:
            raise ReturnCase.DoesNotExist('Return not found.')
        case = _decide(case, user, decision=decision, reason=reason, note=note)
        _resolve_linked_request(case, user)
        if decision == 'approve':
            _notify(
                case.requested_by,
                title='Return approved',
                message=(
                    f'{case.reference} was approved. Send the items back and we '
                    'will refund you on receipt.'
                ),
                action_url=f'/account/orders/{case.order.number}',
            )
        else:
            _notify(
                case.requested_by,
                title='Return update',
                message=f'{case.reference} was declined: {case.decision_reason}',
                action_url=f'/account/orders/{case.order.number}',
            )
    return case


def decide_return(user, reference, *, decision, reason='', note=''):
    """Staff intervention: any case, including whole-order ones (§17.1).

    Group-gated at the view (support/operations/administrator). A staff
    ruling on a case a seller already decided is recorded as an override —
    with its own timeline event and audit row — so the history shows who
    changed someone else's decision and why.
    """
    with transaction.atomic():
        case = (
            ReturnCase.objects.select_for_update(of=('self',))
            .select_related('order', 'seller_order__store')
            .filter(reference=reference)
            .first()
        )
        if case is None:
            raise ReturnCase.DoesNotExist('Return not found.')
        override = case.responded_by_id is not None and case.status != ReturnStatus.REQUESTED
        case = _decide(
            case, user, decision=decision, reason=reason, note=note, override=override
        )
        _resolve_linked_request(case, user)
        _notify(
            case.requested_by,
            title='Return update' if decision == 'reject' else 'Return approved',
            message=(
                f'{case.reference}: {case.decision_reason}'
                if case.decision_reason else f'{case.reference} was updated by support.'
            ),
            action_url=f'/account/orders/{case.order.number}',
        )
    return case


def _actor_case(user, reference, *, staff_allowed):
    """Load a case for its seller (or for staff when allowed), row-locked."""
    if user is None or not getattr(user, 'is_authenticated', False):
        raise ReturnCase.DoesNotExist('Return not found.')
    queryset = (
        ReturnCase.objects.select_for_update(of=('self',))
        .select_related('order', 'order__user', 'seller_order__store')
    )
    if staff_allowed and (user.is_staff or user.is_superuser):
        return queryset.filter(reference=reference).first()
    return queryset.filter(reference=reference, seller_order__store__user=user).first()


def _generate_tracking_number():
    """Return-leg tracking number: JVRTN-YYYYMMDD-XXXXXXXX."""
    date = timezone.now().strftime('%Y%m%d')
    for _ in range(10):
        candidate = f'JVRTN-{date}-{get_random_string(8, REFERENCE_ALPHABET)}'
        if not ReturnShipment.objects.filter(tracking_number=candidate).exists():
            return candidate
    raise RuntimeError('Could not allocate a unique return tracking number.')


def register_return_shipment(user, reference, *, tracking_number='', carrier='manual',
                             carrier_name='Standard Delivery', notes=''):
    """The reverse parcel: goods are on their way back (§17.1 return shipment).

    Booked by the store (or staff acting for it) once the return is approved;
    booking again updates the tracking details instead of creating a second
    parcel, and the case moves to `in_transit`.
    """
    with transaction.atomic():
        case = _actor_case(user, reference, staff_allowed=True)
        if case is None:
            raise ReturnCase.DoesNotExist('Return not found.')
        if case.status not in (ReturnStatus.APPROVED, ReturnStatus.IN_TRANSIT):
            raise ReturnError(
                'Approve the return before booking the return parcel.',
                code='not_shippable',
            )
        shipment = ReturnShipment.objects.filter(case=case).first()
        if shipment is None:
            shipment = ReturnShipment(case=case)
        shipment.tracking_number = (
            (tracking_number or '').strip()
            or shipment.tracking_number
            or _generate_tracking_number()
        )[:64]
        shipment.carrier = (carrier or 'manual')[:32]
        shipment.carrier_name = (carrier_name or 'Standard Delivery')[:128]
        shipment.notes = (notes or '').strip()
        shipment.status = ReturnShipment.Status.IN_TRANSIT
        shipment.shipped_at = shipment.shipped_at or timezone.now()
        shipment.save()

        _record(
            case,
            actor=user,
            kind=ReturnEventKind.SHIPPED,
            audit_action='return.shipped',
            new_status=ReturnStatus.IN_TRANSIT,
            message=f'Return parcel {shipment.tracking_number} in transit',
            detail={
                'tracking_number': shipment.tracking_number,
                'carrier': shipment.carrier,
            },
        )
        _notify(
            case.requested_by,
            title='Return in transit',
            message=(
                f'{case.reference}: your parcel {shipment.tracking_number} is on '
                'its way back.'
            ),
            action_url=f'/account/orders/{case.order.number}',
        )
    return shipment


def receive_return(user, reference, *, note='', restock_overrides=None):
    """Goods are back: write the restock ledger, then price the payout (§17.1).

    Stock moves here and *only* here, once per line (`restocked_at` is the
    idempotency marker), through the row-locked catalog service, so the
    append-only stock history stays the single inventory truth. A line whose
    `restock` flag is off (damaged in transit, unsellable) is closed out
    without touching stock. The seller may override the flag per line at
    receipt — they are the ones holding the parcel.
    """
    overrides = {}
    for entry in restock_overrides or []:
        try:
            overrides[int(entry['order_item_id'])] = bool(entry['restock'])
        except (KeyError, TypeError, ValueError):
            raise ReturnError(
                'Restock overrides need an item and a true/false flag.',
                code='invalid_lines',
            ) from None

    with transaction.atomic():
        case = _actor_case(user, reference, staff_allowed=True)
        if case is None:
            raise ReturnCase.DoesNotExist('Return not found.')
        if case.status not in (ReturnStatus.APPROVED, ReturnStatus.IN_TRANSIT):
            raise ReturnError(
                'Only an approved or in-transit return can be received.',
                code='not_receivable',
            )

        restored = 0
        skipped = 0
        now = timezone.now()
        for line in case.items.select_related('order_item__variant').order_by('id'):
            if line.order_item_id in overrides:
                line.restock = overrides[line.order_item_id]
            if line.restocked_at is not None:
                continue
            if line.restock:
                catalog_services.adjust_stock(
                    user,
                    line.order_item.variant,
                    delta=line.quantity,
                    reason=StockMovement.Reason.RESTOCK,
                    note=f'return {case.reference}',
                )
                restored += 1
            else:
                skipped += 1
            line.restocked_at = now
            line.save(update_fields=['restock', 'restocked_at', 'updated_at'])

        shipment = ReturnShipment.objects.filter(case=case).first()
        if shipment is not None:
            shipment.status = ReturnShipment.Status.DELIVERED
            shipment.received_at = now
            shipment.save(update_fields=['status', 'received_at', 'updated_at'])

        _record(
            case,
            actor=user,
            kind=ReturnEventKind.RECEIVED,
            audit_action='return.received',
            message=(note or '')[:255] or f'{restored} line(s) received',
            detail={'restored_lines': restored, 'not_restocked_lines': skipped},
        )
        _record(
            case,
            actor=user,
            kind=ReturnEventKind.RESTOCKED,
            audit_action='return.restocked',
            new_status=(
                ReturnStatus.REFUND_PENDING
                if case.refund_due > Decimal('0.00')
                else ReturnStatus.RECEIVED
            ),
            message=f'{restored} line(s) restocked, {skipped} written off',
            detail={'refund_due': str(case.refund_due)},
        )
        _notify(
            case.requested_by,
            title='Return received',
            message=(
                f'{case.reference}: we received your items. '
                + (
                    f'Your refund of ₱{case.refund_due} is being processed.'
                    if case.refund_due > Decimal('0.00')
                    else 'Nothing further is owed on this return.'
                )
            ),
            action_url=f'/account/orders/{case.order.number}',
        )
    return case


def cancel_return(user, reference, *, note=''):
    """Customer withdraws their own return before the goods move (§17.1).

    Only possible while the case is undecided or approved-but-not-shipped: a
    parcel already travelling back is the seller's to receive, not the
    customer's to un-request.
    """
    with transaction.atomic():
        case = (
            ReturnCase.objects.select_for_update(of=('self',))
            .select_related('order', 'seller_order__store')
            .filter(reference=reference, requested_by=user)
            .first()
        )
        if case is None:
            raise ReturnCase.DoesNotExist('Return not found.')
        if case.status not in (ReturnStatus.REQUESTED, ReturnStatus.APPROVED):
            raise ReturnError(
                'This return can no longer be cancelled.', code='not_cancellable'
            )
        _record(
            case,
            actor=user,
            kind=ReturnEventKind.CANCELLED,
            audit_action='return.cancelled',
            new_status=ReturnStatus.CANCELLED,
            message=(note or '').strip()[:255] or 'Cancelled by the customer',
        )
        _resolve_linked_request(case, user)
        sellers = (
            [case.seller_order.store.user]
            if case.seller_order_id
            else [so.store.user for so in case.order.seller_orders.all()]
        )
        for seller_user in sellers:
            _notify(
                seller_user,
                title='Return cancelled',
                message=f'{case.reference} was cancelled by the customer.',
                action_url='/seller/returns',
            )
    return case


def close_return(user, reference, *, note=''):
    """Final state — the case is done and its lines are settled (§17.1)."""
    with transaction.atomic():
        case = _actor_case(user, reference, staff_allowed=True)
        if case is None:
            raise ReturnCase.DoesNotExist('Return not found.')
        if case.status not in (ReturnStatus.RECEIVED, ReturnStatus.REFUNDED):
            raise ReturnError(
                'Only a received or refunded return can be closed.',
                code='not_closable',
            )
        _record(
            case,
            actor=user,
            kind=ReturnEventKind.CLOSED,
            audit_action='return.closed',
            new_status=ReturnStatus.CLOSED,
            message=(note or '').strip()[:255] or 'Return closed',
        )
    return case


# -----------------------------------------------------------------------------
# Phase 17 §17.2: refund adjudication — the case prices it, payments moves it
# -----------------------------------------------------------------------------

# A case is payable once the goods are back (the seller holds the parcel), or
# if it has already been refunded (to report already_refunded on replay); a
# refund before receipt is the seller's decision to risk, not the platform's.
PAYABLE_STATUSES = (
    ReturnStatus.REFUND_PENDING,
    ReturnStatus.RECEIVED,
    ReturnStatus.REFUNDED,
)


def refund_totals(case):
    """(committed, settled) — pending gateway refunds still count as committed.

    A gateway refund settles later, through its webhook; the money is already
    promised, so a second payout must not double-pay the customer while the
    first is still in flight.
    """
    committed = case.refunds.exclude(
        status=PaymentRefundStatus.FAILED
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    settled = case.refunds.filter(
        status=PaymentRefundStatus.SUCCEEDED
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    return policies.quantize_money(committed), policies.quantize_money(settled)


def refund_remaining(case):
    """What the case still owes the customer, in pesos."""
    committed, _settled = refund_totals(case)
    return max(
        Decimal('0.00'), policies.quantize_money(case.refund_due) - committed
    )


def issue_refund(user, reference, *, amount=None, reason=''):
    """Pay out an approved-and-received case (§17.2 refund approval/transaction).

    Finance or administrator only (view-gated, §4) — the seller asked for the
    return, the customer is owed the money, and the platform is the one that
    moves it. `amount` may settle part of what the case owes (goodwill, a
    partial refund); it can never exceed the case's remaining balance, and the
    ledger's own balance check still has the last word.

    Returns the `payments.Refund` — already settled for COD, still pending for
    a gateway, which is exactly what the caller renders.
    """
    with transaction.atomic():
        case = _actor_case(user, reference, staff_allowed=True)
        if case is None:
            raise ReturnCase.DoesNotExist('Return not found.')
        if case.status not in PAYABLE_STATUSES:
            raise ReturnError(
                'This return is not ready for a payout — receive the goods first.',
                code='not_payable',
            )
        remaining = refund_remaining(case)
        if remaining <= Decimal('0.00'):
            raise ReturnError(
                'This return has already been refunded in full.',
                code='already_refunded',
            )
        if amount in (None, ''):
            amount = remaining
        try:
            amount = policies.quantize_money(amount)
        except (InvalidOperation, TypeError, ValueError):
            raise ReturnError(
                'Enter a valid refund amount.', code='invalid_amount'
            ) from None
        if amount <= Decimal('0.00'):
            raise ReturnError(
                'Enter a refund amount greater than zero.', code='invalid_amount'
            )
        if amount > remaining:
            raise ReturnError(
                'The payout exceeds what this return still owes.',
                code='refund_exceeds_case',
            )

        payment = getattr(case.order, 'payment', None)
        if payment is None or payment.status not in (
            PaymentStatus.PAID,
            PaymentStatus.PARTIALLY_REFUNDED,
        ):
            raise ReturnError(
                'A refund needs a captured payment.', code='nothing_to_refund'
            )

        if case.status == ReturnStatus.RECEIVED:
            case.status = ReturnStatus.REFUND_PENDING
            case.save(update_fields=['status', 'updated_at'])
        _record(
            case,
            actor=user,
            kind=ReturnEventKind.REFUND_ISSUED,
            audit_action='return.refund_issued',
            message=f'Refund of {amount} issued for {case.reference}',
            detail={'amount': str(amount), 'payment': payment.reference},
        )
        # `restock=False`: receipt already put exactly these lines back on the
        # shelf, so the payments-side restock would double-count them.
        return payment_services.refund(
            payment,
            amount,
            reason=(reason or f'return {case.reference}')[:255],
            actor=user,
            restock=False,
            return_case=case,
        )


def on_refund_settled(refund, actor=None):
    """Payments says the case's money landed (§17.2 refund status).

    Called by the payments service for COD and sandbox gateways (immediately)
    and by the verified webhook (later), so the case reaches `refunded` the
    moment the ledger reversal is written — never before.
    """
    case = refund.return_case
    if case is None:
        return None
    case.refresh_from_db()
    _committed, settled = refund_totals(case)
    fully_paid = settled >= policies.quantize_money(case.refund_due)
    _record(
        case,
        actor=refund.actor or actor,
        kind=ReturnEventKind.REFUNDED,
        audit_action='return.refunded',
        new_status=(
            ReturnStatus.REFUNDED if fully_paid else ReturnStatus.REFUND_PENDING
        ),
        message=f'Refund {refund.reference} settled — {refund.amount}',
        detail={
            'refund': refund.reference,
            'amount': str(refund.amount),
            'settled_total': str(settled),
        },
    )
    _notify(
        case.requested_by,
        title='Refund completed',
        message=f'{case.reference}: {refund.amount} is on its way back to you.',
        action_url=f'/account/orders/{case.order.number}',
    )
    return case


def on_refund_failed(refund):
    """A payout the gateway refused (§17.2 refund status) — the case waits.

    The case stays payable so finance can retry; the failure is on the case
    timeline and in the audit trail, and the customer is told to wait rather
    than shown a refund that never happened.
    """
    case = refund.return_case
    if case is None:
        return None
    _record(
        case,
        actor=refund.actor,
        kind=ReturnEventKind.REFUND_FAILED,
        audit_action='return.refund_failed',
        message=f'Refund {refund.reference} failed — {refund.amount}',
        detail={'refund': refund.reference, 'amount': str(refund.amount)},
    )
    _notify(
        case.requested_by,
        title='Refund pending',
        message=(
            f'{case.reference}: we are still processing your refund. Nothing is '
            'needed from you.'
        ),
        action_url=f'/account/orders/{case.order.number}',
    )
    return case


# -----------------------------------------------------------------------------
# §17.3 disputes — the buyer escalation workflow
# -----------------------------------------------------------------------------

def _generate_dispute_reference():
    """Unique public identifier: JVDSP-YYYYMMDD-XXXXXXXX (CONVENTIONS §2.2)."""
    date = timezone.now().strftime('%Y%m%d')
    for _ in range(10):
        candidate = f'JVDSP-{date}-{get_random_string(8, REFERENCE_ALPHABET)}'
        if not Dispute.objects.filter(reference=candidate).exists():
            return candidate
    raise RuntimeError('Could not allocate a unique dispute reference.')


def _record_dispute(dispute, *, actor, kind, audit_action, new_status=None,
                    message='', detail=None):
    """One dispute transition: timeline row + audit row, always together (§9)."""
    previous = dispute.status
    fields = ['updated_at']
    if new_status is not None and new_status != previous:
        dispute.status = new_status
        fields.append('status')
    dispute.save(update_fields=fields)
    DisputeEvent.objects.create(
        dispute=dispute,
        actor=actor,
        kind=kind,
        message=message[:255],
        previous_status=previous,
        new_status=dispute.status,
    )
    audit_services.log_event(
        actor,
        audit_action,
        dispute,
        detail={
            'dispute': dispute.reference,
            'order': dispute.order.number,
            'from': previous,
            'to': dispute.status,
            **(detail or {}),
        },
    )
    return dispute


def _dispute_party(dispute, user):
    """Which side this caller is on — derived, never client-supplied (§17.3).

    Buyer first (a staff member's own order still reads as their own), then
    the store owner of the disputed slice, then staff. Everyone else is not
    a party and the dispute does not exist for them.
    """
    if user is None or not getattr(user, 'is_authenticated', False):
        return None
    if dispute.requested_by_id == user.id:
        return DisputeParty.CUSTOMER
    if dispute.seller_order_id and dispute.seller_order.store.user_id == user.id:
        return DisputeParty.SELLER
    if user.is_staff:
        return DisputeParty.STAFF
    return None


def _dispute_for(user, reference, *, parties=None):
    """Row-locked load scoped to who may touch this dispute (§17.3 gate).

    A dispute outside `parties` — or one this caller is not on at all —
    raises `Dispute.DoesNotExist`, so the view answers 404 and nothing
    leaks (same contract as the return desk).
    """
    dispute = (
        Dispute.objects.select_for_update(of=('self',))
        .select_related('order', 'seller_order__store', 'requested_by',
                        'return_case')
        .filter(reference=reference)
        .first()
    )
    if dispute is None:
        raise Dispute.DoesNotExist('Dispute not found.')
    party = _dispute_party(dispute, user)
    if party is None or (parties is not None and party not in parties):
        raise Dispute.DoesNotExist('Dispute not found.')
    return dispute, party


def _dispute_sellers(dispute):
    """Who hears the seller's side: the slice's store, or every store."""
    if dispute.seller_order_id:
        return [dispute.seller_order.store.user]
    return list(dispute.order.seller_orders.values_list('store__user', flat=True))


def _announce_dispute(dispute, party, what):
    """Tell the *other* side something landed on the dispute (§15.3)."""
    if party == DisputeParty.STAFF:
        _notify(
            dispute.requested_by,
            title='Dispute update',
            message=f'{dispute.reference}: support {what}.',
            action_url=f'/account/orders/{dispute.order.number}',
        )
        for recipient in _dispute_sellers(dispute):
            _notify(
                recipient,
                title='Dispute update',
                message=f'{dispute.reference}: support {what}.',
                action_url='/seller/disputes',
            )
    elif party == DisputeParty.CUSTOMER:
        for recipient in _dispute_sellers(dispute):
            _notify(
                recipient,
                title='Dispute update',
                message=f'{dispute.reference}: the buyer {what}.',
                action_url='/seller/disputes',
            )
    else:
        _notify(
            dispute.requested_by,
            title='Dispute update',
            message=f'{dispute.reference}: the store {what}.',
            action_url=f'/account/orders/{dispute.order.number}',
        )


def open_dispute(user, number, *, reason, statement, seller_order_id=None,
                 request_id=None, return_reference=None):
    """Escalation filed against the customer's own order (§17.3 creation).

    The client sends only a reason, its opening statement and (optionally)
    the Phase 11 intake it answers or the return it escalates — slice
    resolution, ownership, the duplicate guard and the reference are all
    decided here, inside one row-locked transaction: two parallel submits
    serialize and the loser is refused instead of double-opening.
    """
    reason = (reason or '').strip()
    if reason not in DisputeReason.values:
        raise ReturnError('Choose a valid dispute reason.', code='invalid_reason')
    statement = (statement or '').strip()
    if not statement:
        raise ReturnError('Tell us what went wrong.', code='statement_required')

    with transaction.atomic():
        order = (
            Order.objects.select_for_update()
            .filter(number=number, user=user)
            .first()
        )
        if order is None:
            raise Order.DoesNotExist(f'Order {number} not found.')
        if order.status == OrderStatus.CANCELLED:
            raise ReturnError('This order is already closed.', code='order_closed')

        slices = resolve_slices(order, seller_order_id)

        open_disputes = Dispute.objects.filter(
            order=order, status__in=OPEN_DISPUTE_STATUSES
        )
        if len(slices) == 1:
            duplicate = open_disputes.filter(seller_order_id=slices[0].pk).exists()
        else:
            duplicate = open_disputes.exists()
        if duplicate:
            raise ReturnError(
                'You already have an open dispute for these items.',
                code='dispute_exists',
            )

        linked_request = None
        if request_id not in (None, '', 0, '0'):
            linked_request = OrderRequest.objects.filter(
                pk=request_id, order=order, order__user=user
            ).first()
            if linked_request is None:
                raise ReturnError(
                    'That request does not belong to this order.',
                    code='invalid_request',
                )

        escalated = None
        if return_reference:
            escalated = ReturnCase.objects.filter(
                reference=return_reference, order=order, requested_by=user
            ).first()
            if escalated is None:
                raise ReturnError(
                    'That return does not belong to this order.',
                    code='invalid_return',
                )

        dispute = Dispute.objects.create(
            reference=_generate_dispute_reference(),
            order=order,
            seller_order=slices[0] if len(slices) == 1 else None,
            requested_by=user,
            request=linked_request,
            return_case=escalated,
            reason=reason,
            statement=statement[:4000],
        )
        _record_dispute(
            dispute,
            actor=user,
            kind=DisputeEventKind.CREATED,
            audit_action='dispute.created',
            message=f'Dispute opened — {dispute.get_reason_display()}',
            detail={'reason': reason},
        )
        for seller_order in slices:
            _notify(
                seller_order.store.user,
                title='New dispute',
                message=(
                    f'{dispute.reference} · {seller_order.store_name} · '
                    f'{dispute.get_reason_display()}'
                ),
                action_url='/seller/disputes',
            )
    return dispute


def add_dispute_statement(user, reference, *, body):
    """One party's statement on their own dispute (§17.3 statements).

    The party is derived from the caller (`_dispute_for`), so nobody can
    post as the other side, and a dispute that is already ruled is frozen.
    """
    body = (body or '').strip()
    if not body:
        raise ReturnError(
            'Write a statement before posting.', code='statement_required'
        )
    with transaction.atomic():
        dispute, party = _dispute_for(user, reference)
        if not dispute.is_open:
            raise ReturnError(
                'This dispute is closed — statements are frozen.',
                code='dispute_closed',
            )
        DisputeStatement.objects.create(
            dispute=dispute, author=user, party=party, body=body[:4000]
        )
        _record_dispute(
            dispute,
            actor=user,
            kind=DisputeEventKind.STATEMENT_ADDED,
            audit_action='dispute.statement_added',
            message=f'{party} statement added',
            detail={'party': party},
        )
        _announce_dispute(dispute, party, 'added a statement')
    return dispute


def add_dispute_evidence(user, reference, *, url, caption=''):
    """One evidence row on their own dispute (§17.3 evidence, URL-based)."""
    url = (url or '').strip()
    if not url:
        raise ReturnError(
            'Add a link to your evidence.', code='evidence_required'
        )
    with transaction.atomic():
        dispute, party = _dispute_for(user, reference)
        if not dispute.is_open:
            raise ReturnError(
                'This dispute is closed — evidence is frozen.',
                code='dispute_closed',
            )
        DisputeEvidence.objects.create(
            dispute=dispute,
            added_by=user,
            party=party,
            url=url[:500],
            caption=(caption or '').strip()[:255],
        )
        _record_dispute(
            dispute,
            actor=user,
            kind=DisputeEventKind.EVIDENCE_ADDED,
            audit_action='dispute.evidence_added',
            message=f'{party} evidence added',
            detail={'party': party},
        )
        _announce_dispute(dispute, party, 'added evidence')
    return dispute


def respond_to_dispute(user, reference, *, statement, evidence=None):
    """The store's answer: one statement plus optional evidence (§17.3).

    Seller-scoped at the query level: a dispute on another store's slice —
    or a whole-order one, which staff mediates — does not exist for this
    caller.
    """
    body = (statement or '').strip()
    if not body:
        raise ReturnError(
            'Write a statement before posting.', code='statement_required'
        )
    with transaction.atomic():
        dispute, party = _dispute_for(
            user, reference, parties=(DisputeParty.SELLER,)
        )
        if not dispute.is_open:
            raise ReturnError(
                'This dispute is closed.', code='dispute_closed'
            )
        DisputeStatement.objects.create(
            dispute=dispute, author=user, party=party, body=body[:4000]
        )
        extra = 0
        for entry in evidence or []:
            url = (entry or '').strip()
            if not url:
                continue
            DisputeEvidence.objects.create(
                dispute=dispute, added_by=user, party=party, url=url[:500]
            )
            extra += 1
        _record_dispute(
            dispute,
            actor=user,
            kind=DisputeEventKind.STATEMENT_ADDED,
            audit_action='dispute.statement_added',
            message='Seller statement added',
            detail={'party': party, 'evidence': extra},
        )
        _announce_dispute(dispute, party, 'replied')
    return dispute


def review_dispute(user, reference):
    """Staff claim the dispute (§17.3 staff review).

    Claiming is idempotent — a second `review` on an already-claimed case
    changes nothing — and only staff reach it (the view is group-gated, the
    service re-checks the party).
    """
    with transaction.atomic():
        dispute, _party = _dispute_for(
            user, reference, parties=(DisputeParty.STAFF,)
        )
        if dispute.status == DisputeStatus.UNDER_REVIEW:
            return dispute
        if not dispute.is_open:
            raise ReturnError(
                'This dispute is already closed.', code='dispute_closed'
            )
        _record_dispute(
            dispute,
            actor=user,
            kind=DisputeEventKind.UNDER_REVIEW,
            audit_action='dispute.review',
            message='Staff review started',
            new_status=DisputeStatus.UNDER_REVIEW,
        )
        _notify(
            dispute.requested_by,
            title='Dispute under review',
            message=f'{dispute.reference}: our team is reviewing your dispute.',
            action_url=f'/account/orders/{dispute.order.number}',
        )
    return dispute


def resolve_dispute(user, reference, *, resolution, reason=''):
    """The staff ruling — who wins and why (§17.3 resolution/reason).

    No money moves here: a buyer win is settled through the §17.2 payout
    (finance/administrator only), so this ruling decides the case and the
    linked Phase 11 intake, never the ledger.
    """
    resolution = (resolution or '').strip()
    if resolution not in DisputeResolution.values:
        raise ReturnError('Choose a valid resolution.', code='invalid_resolution')
    reason = (reason or '').strip()
    if not reason:
        raise ReturnError(
            'Record why the dispute was resolved.', code='reason_required'
        )

    with transaction.atomic():
        dispute, _party = _dispute_for(
            user, reference, parties=(DisputeParty.STAFF,)
        )
        if not dispute.is_open:
            raise ReturnError(
                'This dispute has already been resolved.', code='dispute_closed'
            )
        dispute.resolution = resolution
        dispute.resolution_reason = reason[:255]
        dispute.resolved_by = user
        dispute.resolved_at = timezone.now()
        dispute.save(update_fields=[
            'resolution', 'resolution_reason', 'resolved_by', 'resolved_at',
            'updated_at',
        ])
        _record_dispute(
            dispute,
            actor=user,
            kind=DisputeEventKind.RESOLVED,
            audit_action='dispute.resolved',
            message=reason[:255],
            new_status=DisputeStatus.RESOLVED,
            detail={'resolution': resolution, 'reason': reason},
        )

        # The intake this dispute answers is now answered (§11.3).
        linked = dispute.request
        if linked is not None and linked.status == RequestStatus.PENDING:
            linked.status = RequestStatus.RESOLVED
            linked.save(update_fields=['status', 'updated_at'])
            audit_services.log_event(
                user,
                'order.request_resolved',
                linked,
                detail={
                    'order': dispute.order.number,
                    'dispute': dispute.reference,
                },
            )

        _notify(
            dispute.requested_by,
            title='Dispute resolved',
            message=f'{dispute.reference}: {reason[:120]}',
            action_url=f'/account/orders/{dispute.order.number}',
        )
        for recipient in _dispute_sellers(dispute):
            _notify(
                recipient,
                title='Dispute resolved',
                message=f'{dispute.reference}: resolved — {reason[:120]}',
                action_url='/seller/disputes',
            )
    return dispute


def cancel_dispute(user, reference):
    """The buyer withdraws their own dispute while it is still undecided."""
    with transaction.atomic():
        dispute, _party = _dispute_for(
            user, reference, parties=(DisputeParty.CUSTOMER,)
        )
        if not dispute.is_open:
            raise ReturnError(
                'This dispute has already been resolved.', code='dispute_closed'
            )
        _record_dispute(
            dispute,
            actor=user,
            kind=DisputeEventKind.CANCELLED,
            audit_action='dispute.cancelled',
            message='Withdrawn by the buyer',
            new_status=DisputeStatus.CANCELLED,
        )
        for recipient in _dispute_sellers(dispute):
            _notify(
                recipient,
                title='Dispute withdrawn',
                message=f'{dispute.reference}: the buyer withdrew the dispute.',
                action_url='/seller/disputes',
            )
    return dispute

