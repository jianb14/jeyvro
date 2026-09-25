"""Order services — checkout validation, order creation, cancellation (§6).

Everything money- or stock-critical happens here, inside one transaction:
the cart is re-validated against live server truth, the order is snapshotted
(immutably), stock is reserved through the row-locked catalog services (the
only place stock changes), and the cart is cleared. Views stay thin (§8).
"""
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.crypto import get_random_string

from apps.accounts.models import Address
from apps.audit import services as audit_services
from apps.cart import services as cart_services
from apps.cart.models import Cart
from apps.catalog import services as catalog_services
from apps.payments import services as payment_services
from apps.payments.models import PaymentMethod, PaymentStatus

from .models import (
    Order,
    OrderItem,
    OrderRequest,
    OrderStatus,
    RequestKind,
    RequestStatus,
    SellerOrder,
    Shipment,
)


# Unambiguous alphabet for order numbers (no O/0, I/1, lookalikes).
ORDER_NUMBER_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'


class CheckoutError(ValueError):
    """Customer-safe checkout rejection — code + message, never a stack."""

    def __init__(self, message, *, code='checkout_rejected'):
        super().__init__(message)
        self.code = code


def compute_shipping_fee(store, subtotal):
    """Per-store shipping truth (§6 v1.7): flat fee, free at/above threshold.

    Returns (fee, is_free). A null threshold means the flat fee always
    applies; reaching the threshold waives it without touching the subtotal.
    """
    fee = store.shipping_flat_fee or Decimal('0.00')
    threshold = store.free_shipping_threshold
    if threshold is not None and subtotal >= threshold:
        return Decimal('0.00'), True
    return fee, False


def _generate_order_number():
    """Unique public identifier: JV-YYYYMMDD-XXXXXXXX (CONVENTIONS §2.2)."""
    date = timezone.now().strftime('%Y%m%d')
    for _ in range(10):
        candidate = f'JV-{date}-{get_random_string(8, ORDER_NUMBER_ALPHABET)}'
        if not Order.objects.filter(number=candidate).exists():
            return candidate
    raise RuntimeError('Could not allocate a unique order number.')


def create_order(user, address_id, payment_method=PaymentMethod.COD):
    """Creates the parent order + one SellerOrder per store — one transaction.

    Re-validates every cart line against live product/variant/stock/price
    truth (the client sends only an address and a payment method — never
    prices or totals), snapshots everything, reserves stock with row locks,
    starts the payment, then clears the cart. Any failure raises
    CheckoutError and rolls the whole thing back, so an invalid line or an
    unpayable method can never produce a partial order.
    """
    address = Address.objects.filter(pk=address_id, user=user).first()
    if address is None:
        raise CheckoutError('Choose a valid shipping address.', code='invalid_address')

    with transaction.atomic():
        # Lock the cart row: two parallel submits (double-click) serialize
        # here — the second one finds an empty cart and is rejected.
        cart = Cart.objects.select_for_update().filter(user=user).first()
        items = (
            list(
                cart.items.select_related(
                    'variant',
                    'variant__inventory',
                    'variant__product',
                    'variant__product__store',
                )
            )
            if cart is not None
            else []
        )
        if not items:
            raise CheckoutError('Your cart is empty.', code='empty_cart')

        groups = {}
        for item in items:
            variant = item.variant
            product = variant.product
            purchasable, available, reason = cart_services.variant_purchase_state(variant)
            if not purchasable:
                raise CheckoutError(
                    f'{product.title}: {reason}', code='line_unavailable'
                )
            if item.quantity > available:
                raise CheckoutError(
                    f'{product.title}: only {available} left in stock.',
                    code='insufficient_stock',
                )
            groups.setdefault(product.store, []).append(item)

        subtotal = Decimal('0.00')
        shipping_total = Decimal('0.00')
        savings_total = Decimal('0.00')
        store_plans = []
        for store, store_items in groups.items():
            store_subtotal = Decimal('0.00')
            store_savings = Decimal('0.00')
            store_lines = []
            for item in store_items:
                variant = item.variant
                price = variant.price
                compare_at = variant.product.compare_at_price
                if compare_at is not None and compare_at <= price:
                    compare_at = None
                line_total = price * item.quantity
                store_subtotal += line_total
                if compare_at is not None:
                    store_savings += (compare_at - price) * item.quantity
                store_lines.append((item, price, compare_at, line_total))
            fee, _is_free = compute_shipping_fee(store, store_subtotal)
            subtotal += store_subtotal
            shipping_total += fee
            savings_total += store_savings
            store_plans.append((store, store_lines, store_subtotal, fee))

        tax_total = Decimal('0.00')  # §6: tax is not computed yet — slot reserved
        grand_total = subtotal + shipping_total + tax_total

        order = Order.objects.create(
            number=_generate_order_number(),
            user=user,
            status=Order.Status.PLACED,
            ship_to_name=address.full_name,
            ship_to_phone=address.phone,
            shipping_line1=address.line1,
            shipping_line2=address.line2,
            shipping_city=address.city,
            shipping_province=address.province,
            shipping_postal_code=address.postal_code,
            subtotal=subtotal,
            shipping_total=shipping_total,
            savings_total=savings_total,
            tax_total=tax_total,
            grand_total=grand_total,
        )

        for store, store_lines, store_subtotal, fee in store_plans:
            seller_order = SellerOrder.objects.create(
                order=order,
                store=store,
                store_name=store.name,
                status=SellerOrder.Status.PLACED,
                subtotal=store_subtotal,
                shipping_fee=fee,
                total=store_subtotal + fee,
            )
            for item, price, compare_at, line_total in store_lines:
                variant = item.variant
                OrderItem.objects.create(
                    seller_order=seller_order,
                    product=variant.product,
                    variant=variant,
                    product_title=variant.product.title,
                    product_slug=variant.product.slug,
                    variant_name=variant.name,
                    sku=variant.sku,
                    unit_price=price,
                    compare_at_price=compare_at,
                    quantity=item.quantity,
                    line_total=line_total,
                )
                # The race gate: row-locked reservation; another checkout
                # that took the last unit makes this raise and roll back.
                try:
                    catalog_services.reserve_stock(variant, item.quantity)
                except ValueError as exc:
                    raise CheckoutError(
                        f'{variant.product.title}: {exc}',
                        code='insufficient_stock',
                    ) from exc

        cart.items.all().delete()

        # Payments (§6 v1.8): every order is immediately awaiting payment —
        # COD collects on delivery, online payments start through the adapter
        # seam. A method that cannot be paid is refused before anything moves.
        try:
            payment = payment_services.start_payment(order, payment_method)
        except payment_services.PaymentError as exc:
            raise CheckoutError(str(exc), code=exc.code) from exc
        order.status = Order.Status.AWAITING_PAYMENT
        order.save(update_fields=['status', 'updated_at'])
        order.seller_orders.update(
            status=SellerOrder.Status.AWAITING_PAYMENT, updated_at=timezone.now()
        )

        audit_services.log_event(
            user,
            'order.placed',
            order,
            detail={
                'number': order.number,
                'grand_total': str(order.grand_total),
                'stores': len(store_plans),
                'payment_method': payment.method,
                'payment': payment.reference,
            },
        )
    return order


def can_cancel(order):
    """Cancellation eligibility — the one server-side verdict (§11.3).

    Only pre-payment orders cancel here (the reservation is released
    whole). Paid orders move through refunds/returns instead (Phase 17),
    so the customer UI renders this flag rather than guessing.
    """
    return order.status in (Order.Status.PLACED, Order.Status.AWAITING_PAYMENT)


def cancel_order(user, number):
    """Customer cancellation before payment — releases the reservations (§6).

    Only `placed` / `awaiting_payment` orders can be cancelled here (see
    `can_cancel`); after payment, refunds are the path (Phase 17). Every
    line's reservation is released through the row-locked catalog service,
    then both the parent and the per-store orders are marked cancelled —
    one transaction.
    """
    with transaction.atomic():
        order = (
            Order.objects.select_for_update()
            .filter(number=number, user=user)
            .first()
        )
        if order is None:
            raise Order.DoesNotExist(f'Order {number} not found.')
        if not can_cancel(order):
            raise CheckoutError(
                'This order can no longer be cancelled.', code='not_cancellable'
            )
        items = OrderItem.objects.filter(
            seller_order__order=order
        ).select_related('variant')
        for item in items:
            catalog_services.release_stock(item.variant, item.quantity)
        order.status = Order.Status.CANCELLED
        order.save(update_fields=['status', 'updated_at'])
        order.seller_orders.update(
            status=SellerOrder.Status.CANCELLED, updated_at=timezone.now()
        )
        # A still-pending payment is voided with its order (§6 v1.8).
        payment_services.cancel_pending_payment(order, actor=user)
        audit_services.log_event(
            user, 'order.cancelled', order, detail={'number': order.number}
        )
    return order



# -----------------------------------------------------------------------------
# Phase 10: Order Fulfillment & Delivery Services (§10.1, §10.2, §10.3)
# -----------------------------------------------------------------------------

class FulfillmentError(ValueError):
    """Customer/Seller-safe fulfillment rejection — code + message, never a stack."""

    def __init__(self, message, *, code='fulfillment_rejected'):
        super().__init__(message)
        self.code = code


def aggregate_order_status(order):
    """Derives and saves parent Order status from its SellerOrders (§10.3)."""
    seller_statuses = set(order.seller_orders.values_list('status', flat=True))
    if not seller_statuses:
        return order.status

    target_status = None
    if seller_statuses == {OrderStatus.CANCELLED}:
        target_status = OrderStatus.CANCELLED
    elif seller_statuses == {OrderStatus.REFUNDED}:
        target_status = OrderStatus.REFUNDED
    elif seller_statuses.issubset({OrderStatus.DELIVERED, OrderStatus.COMPLETED}):
        target_status = OrderStatus.DELIVERED
    elif any(s in (OrderStatus.SHIPPED, OrderStatus.IN_TRANSIT, OrderStatus.OUT_FOR_DELIVERY, OrderStatus.DELIVERED) for s in seller_statuses):
        target_status = OrderStatus.SHIPPED
    elif any(s in (OrderStatus.PACKED, OrderStatus.PROCESSING) for s in seller_statuses):
        target_status = OrderStatus.PROCESSING
    elif seller_statuses == {OrderStatus.PAID}:
        target_status = OrderStatus.PAID
    elif seller_statuses == {OrderStatus.AWAITING_PAYMENT}:
        target_status = OrderStatus.AWAITING_PAYMENT

    if target_status and order.status != target_status:
        order.status = target_status
        order.save(update_fields=['status', 'updated_at'])
        audit_services.log_event(
            None,
            'order.status_aggregated',
            order,
            detail={'number': order.number, 'status': order.status},
        )
    return order.status


def mark_seller_order_processing(seller_order, *, actor=None):
    """Seller marks order as being processed/prepared (§10.1)."""
    with transaction.atomic():
        so = SellerOrder.objects.select_for_update().get(pk=seller_order.pk)
        valid_initial = (OrderStatus.PAID, OrderStatus.AWAITING_PAYMENT, OrderStatus.PLACED)
        if so.status not in valid_initial:
            raise FulfillmentError(
                f'Order cannot move to processing from {so.status}.',
                code='invalid_status_transition',
            )
        so.status = OrderStatus.PROCESSING
        so.save(update_fields=['status', 'updated_at'])
        audit_services.log_event(
            actor,
            'seller_order.processing',
            so,
            detail={'id': so.id, 'store': so.store_name},
        )
        aggregate_order_status(so.order)
    return so


def mark_seller_order_packed(seller_order, *, actor=None):
    """Seller marks order items as packed and ready for dispatch (§10.1)."""
    with transaction.atomic():
        so = SellerOrder.objects.select_for_update().get(pk=seller_order.pk)
        if so.status not in (OrderStatus.PROCESSING, OrderStatus.PAID, OrderStatus.AWAITING_PAYMENT):
            raise FulfillmentError(
                f'Order cannot be marked packed from {so.status}.',
                code='invalid_status_transition',
            )
        so.status = OrderStatus.PACKED
        so.save(update_fields=['status', 'updated_at'])
        audit_services.log_event(
            actor,
            'seller_order.packed',
            so,
            detail={'id': so.id, 'store': so.store_name},
        )
        aggregate_order_status(so.order)
    return so


def create_shipment(seller_order, *, items_data=None, carrier_code='manual',
                    package_notes='', package_weight_grams=None, actor=None):
    """Creates a Shipment parcel for a SellerOrder (§10.2, §10.3)."""
    from .carriers import get_carrier
    from .models import Shipment, ShipmentItem, ShipmentStatus, TrackingEvent

    carrier = get_carrier(carrier_code)
    parent_order = seller_order.order

    with transaction.atomic():
        so = SellerOrder.objects.select_for_update().get(pk=seller_order.pk)
        if so.status in (OrderStatus.CANCELLED, OrderStatus.REFUNDED, OrderStatus.DELIVERED, OrderStatus.COMPLETED):
            raise FulfillmentError(
                f'Cannot create shipment for order in {so.status} status.',
                code='order_closed',
            )

        order_items = {item.id: item for item in so.items.all()}
        if not order_items:
            raise FulfillmentError('No items in this seller order.', code='empty_order')

        existing_shipped = {}
        for s in so.shipments.exclude(status=ShipmentStatus.CANCELLED):
            for si in s.items.all():
                existing_shipped[si.order_item_id] = existing_shipped.get(si.order_item_id, 0) + si.quantity

        pack_plan = []
        if not items_data:
            for item_id, item in order_items.items():
                shipped = existing_shipped.get(item_id, 0)
                remaining = item.quantity - shipped
                if remaining > 0:
                    pack_plan.append((item, remaining))
        else:
            for line in items_data:
                item_id = line.get('order_item_id')
                qty = int(line.get('quantity', 0))
                if item_id not in order_items:
                    raise FulfillmentError(
                        f'Item {item_id} does not belong to this seller order.',
                        code='invalid_item',
                    )
                if qty <= 0:
                    raise FulfillmentError('Quantity must be at least 1.', code='invalid_quantity')
                item = order_items[item_id]
                already_shipped = existing_shipped.get(item_id, 0)
                available = item.quantity - already_shipped
                if qty > available:
                    raise FulfillmentError(
                        f'Cannot pack {qty} for {item.product_title}; only {available} unfulfilled.',
                        code='excess_quantity',
                    )
                pack_plan.append((item, qty))

        if not pack_plan:
            raise FulfillmentError('All items have already been shipped.', code='already_fulfilled')

        address_parts = [
            parent_order.shipping_line1,
            parent_order.shipping_line2,
            parent_order.shipping_city,
            parent_order.shipping_province,
            parent_order.shipping_postal_code,
        ]
        address_text = ', '.join([p for p in address_parts if p])

        tracking_number = carrier.generate_tracking_number()
        while Shipment.objects.filter(tracking_number=tracking_number).exists():
            tracking_number = carrier.generate_tracking_number()

        now = timezone.now()
        shipment = Shipment.objects.create(
            seller_order=so,
            tracking_number=tracking_number,
            carrier=carrier.carrier_code,
            carrier_name=carrier.carrier_name,
            shipping_method='standard',
            shipping_fee=so.shipping_fee,
            status=ShipmentStatus.PICKED_UP,
            shipped_at=now,
            package_weight_grams=package_weight_grams,
            package_notes=package_notes,
            recipient_name=parent_order.ship_to_name,
            recipient_phone=parent_order.ship_to_phone,
            shipping_address_text=address_text,
        )

        for item, qty in pack_plan:
            ShipmentItem.objects.create(
                shipment=shipment,
                order_item=item,
                quantity=qty,
            )

        TrackingEvent.objects.create(
            shipment=shipment,
            status=ShipmentStatus.PICKED_UP,
            location=so.store_name,
            description=f'Parcel picked up by {carrier.carrier_name}.',
            occurred_at=now,
        )

        all_fulfilled = True
        for item_id, item in order_items.items():
            shipped_total = existing_shipped.get(item_id, 0) + sum(
                qty for itm, qty in pack_plan if itm.id == item_id
            )
            if shipped_total < item.quantity:
                all_fulfilled = False
                break

        if all_fulfilled:
            so.status = OrderStatus.SHIPPED
        else:
            so.status = OrderStatus.PROCESSING
        so.save(update_fields=['status', 'updated_at'])

        audit_services.log_event(
            actor,
            'shipment.created',
            shipment,
            detail={
                'tracking_number': shipment.tracking_number,
                'carrier': carrier.carrier_code,
                'items_count': len(pack_plan),
                'all_fulfilled': all_fulfilled,
            },
        )

        aggregate_order_status(parent_order)
    return shipment


def update_shipment_status(shipment, new_status, *, location='', description='', actor=None):
    """Transitions a shipment status and appends a TrackingEvent (§10.2).

    When delivered:
    - Sets delivered_at on the shipment
    - If all shipments of the SellerOrder are delivered, sets SellerOrder to DELIVERED
    - Aggregates parent order status
    - If order is DELIVERED and payment is COD (pending), triggers COD collection capture!
    """
    from apps.payments import services as payment_services
    from apps.payments.models import PaymentMethod
    from .models import Shipment, ShipmentStatus, TrackingEvent

    with transaction.atomic():
        s = Shipment.objects.select_for_update().get(pk=shipment.pk)
        so = SellerOrder.objects.select_for_update().get(pk=s.seller_order_id)
        parent_order = Order.objects.select_for_update().get(pk=so.order_id)

        valid_statuses = [c[0] for c in ShipmentStatus.choices]
        if new_status not in valid_statuses:
            raise FulfillmentError(f'Unknown shipment status {new_status}.', code='invalid_status')

        now = timezone.now()
        s.status = new_status
        if new_status == ShipmentStatus.DELIVERED and not s.delivered_at:
            s.delivered_at = now

        update_fields = ['status', 'updated_at']
        if s.delivered_at:
            update_fields.append('delivered_at')
        s.save(update_fields=update_fields)

        default_desc = {
            ShipmentStatus.PENDING: 'Shipment created.',
            ShipmentStatus.PACKED: 'Shipment packed and ready.',
            ShipmentStatus.PICKED_UP: 'Parcel picked up by courier.',
            ShipmentStatus.IN_TRANSIT: 'In transit to destination sorting hub.',
            ShipmentStatus.OUT_FOR_DELIVERY: 'Out for delivery with courier rider.',
            ShipmentStatus.DELIVERED: 'Parcel successfully delivered.',
            ShipmentStatus.FAILED: 'Delivery attempt failed.',
            ShipmentStatus.CANCELLED: 'Shipment cancelled.',
        }.get(new_status, f'Status updated to {new_status}')

        TrackingEvent.objects.create(
            shipment=s,
            status=new_status,
            location=location or '',
            description=description or default_desc,
            occurred_at=now,
        )

        if new_status == ShipmentStatus.DELIVERED:
            all_delivered = not so.shipments.exclude(status=ShipmentStatus.DELIVERED).exists()
            if all_delivered:
                so.status = OrderStatus.DELIVERED
                so.save(update_fields=['status', 'updated_at'])
        elif new_status == ShipmentStatus.IN_TRANSIT:
            if so.status in (OrderStatus.SHIPPED, OrderStatus.PACKED, OrderStatus.PROCESSING):
                so.status = OrderStatus.IN_TRANSIT
                so.save(update_fields=['status', 'updated_at'])
        elif new_status == ShipmentStatus.OUT_FOR_DELIVERY:
            if so.status in (OrderStatus.SHIPPED, OrderStatus.IN_TRANSIT, OrderStatus.PACKED, OrderStatus.PROCESSING):
                so.status = OrderStatus.OUT_FOR_DELIVERY
                so.save(update_fields=['status', 'updated_at'])

        aggregate_order_status(parent_order)

        # Delivery COD Collection Hook (§9.2, Phase 10 seam):
        payment = getattr(parent_order, 'payment', None)
        if (parent_order.status == OrderStatus.DELIVERED and
                payment and payment.method == PaymentMethod.COD and
                payment.status == 'pending'):
            payment_services.mark_paid(payment, source='cod_delivery', actor=actor)

        audit_services.log_event(
            actor,
            'shipment.status_updated',
            s,
            detail={
                'tracking_number': s.tracking_number,
                'status': new_status,
                'location': location,
            },
        )

    return s


# -----------------------------------------------------------------------------
# Phase 11: Customer Account & Order Management Services (§11.1, §11.2, §11.3)
# -----------------------------------------------------------------------------

class RequestError(ValueError):
    """Customer-safe post-purchase rejection — code + message, never a stack."""

    def __init__(self, message, *, code='request_rejected'):
        super().__init__(message)
        self.code = code


_FULFILLED_STATUSES = (OrderStatus.DELIVERED, OrderStatus.COMPLETED)


# Customer-safe copy for the audit trail → order timeline (§11.2). Only
# whitelisted actions are mapped, and only known keys are read out of
# `detail` — raw audit payloads never cross to the client.
_TIMELINE_STEPS = {
    'order.placed': ('Order placed', 'success'),
    'payment.captured': ('Payment received', 'success'),
    'order.cancelled': ('Order cancelled', 'danger'),
    'refund.settled': ('Refund completed', 'info'),
}

_SELLER_ORDER_STEPS = {
    'seller_order.processing': ('Being prepared', 'info'),
    'seller_order.packed': ('Packed and ready to ship', 'info'),
}

_SHIPMENT_STATUS_LABELS = {
    'pending': 'Shipment created',
    'packed': 'Packed and ready',
    'picked_up': 'Picked up by the courier',
    'in_transit': 'In transit',
    'out_for_delivery': 'Out for delivery',
    'delivered': 'Delivered',
    'failed': 'Delivery attempt failed',
    'cancelled': 'Shipment cancelled',
}

_SHIPMENT_TONES = {
    'delivered': 'success',
    'failed': 'danger',
    'cancelled': 'neutral',
}


def _timeline_step(row):
    """One audit row → one customer-safe timeline step (None = skip)."""
    occurred_at = row.created_at.isoformat()
    if row.action == 'shipment.status_updated':
        status = row.detail.get('status', '')
        description = ' · '.join(
            part
            for part in (
                f"Tracking {row.detail.get('tracking_number', '')}".strip(),
                row.detail.get('location', ''),
            )
            if part
        )
        return {
            'title': _SHIPMENT_STATUS_LABELS.get(status, 'Shipment updated'),
            'description': description,
            'tone': _SHIPMENT_TONES.get(status, 'info'),
            'occurred_at': occurred_at,
        }
    if row.action == 'shipment.created':
        tracking = row.detail.get('tracking_number', '')
        return {
            'title': 'Parcel handed to the courier',
            'description': f'Tracking {tracking}' if tracking else '',
            'tone': 'info',
            'occurred_at': occurred_at,
        }
    if row.action in _SELLER_ORDER_STEPS:
        title, tone = _SELLER_ORDER_STEPS[row.action]
        return {
            'title': title,
            'description': row.detail.get('store', ''),
            'tone': tone,
            'occurred_at': occurred_at,
        }
    if row.action in _TIMELINE_STEPS:
        title, tone = _TIMELINE_STEPS[row.action]
        return {
            'title': title,
            'description': '',
            'tone': tone,
            'occurred_at': occurred_at,
        }
    return None


def build_order_timeline(order):
    """Owner-facing lifecycle timeline assembled from the audit trail (§11.2).

    Every lifecycle transition already writes an append-only AuditLog row
    (Phases 8–10); this maps the whitelisted subset into customer-safe
    steps. Unknown actions are skipped, never leaked.
    """
    from apps.audit.models import AuditLog
    from apps.payments.models import Refund

    targets = [
        ('orders.order', [order.pk]),
        (
            'orders.sellerorder',
            order.seller_orders.values_list('pk', flat=True),
        ),
        (
            'orders.shipment',
            Shipment.objects.filter(seller_order__order=order).values_list(
                'pk', flat=True
            ),
        ),
        (
            'payments.refund',
            Refund.objects.filter(payment__order=order).values_list('pk', flat=True),
        ),
    ]
    payment = getattr(order, 'payment', None)
    if payment is not None:
        targets.append(('payments.payment', [payment.pk]))

    query = Q()
    for object_type, ids in targets:
        ids = [str(pk) for pk in ids]
        if ids:
            query |= Q(object_type=object_type, object_id__in=ids)
    if not query:
        return []

    steps = []
    for row in AuditLog.objects.filter(query).order_by('created_at', 'id'):
        step = _timeline_step(row)
        if step:
            steps.append(step)
    return steps


def reorder_into_cart(user, number):
    """Adds every still-buyable line of an order back into the cart (§11.2).

    Each line is re-validated against live catalog/stock truth through the
    same cart service the buy flow uses; unavailable lines are reported,
    never silently dropped, so the caller can tell the customer what was
    skipped and why.
    """
    order = Order.objects.filter(number=number, user=user).first()
    if order is None:
        raise Order.DoesNotExist(f'Order {number} not found.')

    cart = Cart.objects.get_or_create(user=user)[0]
    items = OrderItem.objects.filter(seller_order__order=order).select_related(
        'variant',
        'variant__inventory',
        'variant__product',
        'variant__product__store',
    )

    added, skipped = [], []
    for item in items:
        try:
            cart_services.add_item(cart, item.variant, item.quantity)
        except ValueError as exc:
            skipped.append({'title': item.product_title, 'reason': str(exc)})
        else:
            added.append({
                'title': item.product_title,
                'variant_name': item.variant_name,
                'quantity': item.quantity,
            })
    return {
        'added': added,
        'skipped': skipped,
        'cart_item_count': sum(cart.items.values_list('quantity', flat=True)),
    }


def _request_slices(order, seller_order_id):
    """Resolves the target store slice(s) for a request, order-scoped."""
    slices = list(order.seller_orders.all())
    if seller_order_id is None:
        return slices
    target = next((so for so in slices if so.pk == seller_order_id), None)
    if target is None:
        raise RequestError(
            'That store is not part of this order.', code='invalid_store'
        )
    return [target]


def create_order_request(user, number, kind, reason, description='', seller_order_id=None):
    """Records a customer request against their own order (§11.3).

    Eligibility is server-verified: returns need a delivered slice, refund
    requests need captured money, and issues need an order that is not
    closed. The record is the intake — Phase 17 owns the adjudication.
    """
    if kind not in RequestKind.values:
        raise RequestError('Unknown request type.', code='invalid_kind')
    reason = (reason or '').strip()
    if not reason:
        raise RequestError('Please include a reason.', code='reason_required')

    with transaction.atomic():
        order = (
            Order.objects.select_for_update()
            .filter(number=number, user=user)
            .prefetch_related('seller_orders')
            .first()
        )
        if order is None:
            raise Order.DoesNotExist(f'Order {number} not found.')

        targets = _request_slices(order, seller_order_id)

        if kind == RequestKind.RETURN:
            fulfilled = all(
                so.status in _FULFILLED_STATUSES for so in targets
            )
            if not targets or not fulfilled:
                raise RequestError(
                    'You can request a return once the items have been delivered.',
                    code='not_delivered',
                )
        elif kind == RequestKind.REFUND:
            payment = getattr(order, 'payment', None)
            if payment is None or payment.status not in (
                PaymentStatus.PAID,
                PaymentStatus.PARTIALLY_REFUNDED,
            ):
                raise RequestError(
                    'A refund request needs a completed payment.',
                    code='nothing_to_refund',
                )
        else:  # issue
            if order.status in (OrderStatus.CANCELLED, OrderStatus.REFUNDED):
                raise RequestError('This order is already closed.', code='order_closed')

        duplicate = OrderRequest.objects.filter(
            order=order,
            kind=kind,
            seller_order_id=seller_order_id,
            status=RequestStatus.PENDING,
        ).exists()
        if duplicate:
            raise RequestError(
                'You already have a pending request like this.',
                code='request_exists',
            )

        request = OrderRequest.objects.create(
            order=order,
            seller_order_id=seller_order_id,
            kind=kind,
            reason=reason[:160],
            description=(description or '').strip()[:2000],
        )
        audit_services.log_event(
            user,
            'order.request_created',
            request,
            detail={
                'order': order.number,
                'kind': kind,
                'seller_order': seller_order_id,
            },
        )
    return request


def withdraw_order_request(user, number, request_id):
    """Customer withdraws their own pending request (§11.3)."""
    with transaction.atomic():
        request = (
            OrderRequest.objects.select_for_update()
            .filter(pk=request_id, order__number=number, order__user=user)
            .first()
        )
        if request is None:
            raise OrderRequest.DoesNotExist('Request not found.')
        if request.status != RequestStatus.PENDING:
            raise RequestError(
                'Only pending requests can be withdrawn.', code='not_withdrawable'
            )
        request.status = RequestStatus.WITHDRAWN
        request.save(update_fields=['status', 'updated_at'])
        audit_services.log_event(
            user,
            'order.request_withdrawn',
            request,
            detail={'order': request.order.number, 'kind': request.kind},
        )
    return request

