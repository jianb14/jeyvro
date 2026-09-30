"""Order serializers — declared shapes only (backend-api rule 2).

Money crosses the wire as JSON numbers (matching the catalog/cart contract)
and every value is server truth: the checkout preview reuses the cart
payload's live lines and adds per-store shipping, and order payloads render
only the immutable snapshots written at creation.
"""
from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from apps.cart.serializers import build_cart_payload
from apps.common.privacy import mask_name, mask_phone
from apps.payments import adapters as payment_adapters
from apps.payments.models import PaymentMethod
from apps.payments.serializers import serialize_payment
from apps.promotions import services as promotion_services
from apps.promotions.serializers import serialize_voucher_preview
from apps.stores.models import Store

from . import services
from .models import OrderStatus, RequestKind, ShipmentStatus


class CreateOrderSerializer(serializers.Serializer):
    """POST /checkout/orders body — the ONLY client input (§6 v1.8).

    Prices, fees, and totals are recomputed server-side; the client cannot
    send them at all, so they can never be trusted. The payment method is a
    choice, never an amount.
    """

    address_id = serializers.IntegerField(min_value=1)
    payment_method = serializers.ChoiceField(
        choices=PaymentMethod.choices, default=PaymentMethod.COD
    )
    voucher_code = serializers.CharField(
        max_length=32,
        required=False,
        allow_blank=True,
        default='',
        help_text='Optional voucher code (Phase 16 §16.1) — a code, never an amount.',
    )


class CreateOrderRequestSerializer(serializers.Serializer):
    """POST /orders/<number>/requests body (§11.3).

    The client states what it wants; eligibility (delivered slice, captured
    payment, open order) is re-checked server-side in the service — this
    shape only validates the shape.
    """

    kind = serializers.ChoiceField(choices=RequestKind.choices)
    seller_order_id = serializers.IntegerField(
        min_value=1, required=False, allow_null=True, default=None
    )
    reason = serializers.CharField(max_length=160)
    description = serializers.CharField(
        required=False, allow_blank=True, default='', max_length=2000
    )


class CreateShipmentSerializer(serializers.Serializer):
    """POST /seller/orders/<id>/ship body (§10.2)."""

    carrier = serializers.CharField(max_length=32, required=False, default='manual')
    package_notes = serializers.CharField(required=False, allow_blank=True, default='')
    package_weight_grams = serializers.IntegerField(required=False, min_value=1, allow_null=True, default=None)
    items = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True,
        default=list,
        help_text='Optional list of {"order_item_id": int, "quantity": int} for partial shipments.',
    )


class UpdateShipmentStatusSerializer(serializers.Serializer):
    """POST /shipments/<tracking_number>/events body (§10.2)."""

    status = serializers.ChoiceField(choices=['pending', 'packed', 'picked_up', 'in_transit', 'out_for_delivery', 'delivered', 'failed', 'cancelled'])
    location = serializers.CharField(max_length=128, required=False, allow_blank=True, default='')
    description = serializers.CharField(max_length=256, required=False, allow_blank=True, default='')



def build_checkout_preview(cart, request=None, voucher_code=''):
    """Checkout read shape: cart truth + per-store shipping + totals (§6).

    Reuses the cart payload (one implementation of line truth) and adds the
    fee each store charges, the payment options (with live availability from
    the adapter registry), an `issues` list for blocked lines, and the final
    totals — the client only renders these numbers. The grand total is net of
    the automatic promotion discount (§16.2) and, when `voucher_code` is
    supplied, of the voucher discount (§16.1) — both judged by the same
    services order creation uses, so this preview can never disagree with the
    order that follows. A rejected code leaves the totals gross and surfaces
    `voucher_error`; `create_order` stays the authoritative validator.
    """
    if cart is None:
        return {
            'id': None,
            'owner': 'user',
            'items': [],
            'groups': [],
            'totals': {
                'line_count': 0,
                'item_count': 0,
                'subtotal': 0,
                'savings': 0,
                'promotion_discount': 0,
                'items_total': 0,
                'shipping_total': 0,
                'discount_total': 0,
                'voucher_code': '',
                'tax_total': 0,
                'grand_total': 0,
            },
            'issues': [],
            'payment_methods': payment_adapters.payment_method_options(),
            'checkout_ready': False,
            'voucher': None,
            'voucher_error': None,
        }
    payload = build_cart_payload(cart, request)
    stores = {
        store.slug: store
        for store in Store.objects.filter(
            slug__in=[group['store_slug'] for group in payload['groups']]
        )
    }
    shipping_total = Decimal('0.00')
    for group in payload['groups']:
        store = stores.get(group['store_slug'])
        subtotal = Decimal(str(group['subtotal']))
        fee, is_free = (
            services.compute_shipping_fee(store, subtotal)
            if store is not None
            else (Decimal('0.00'), True)
        )
        if store is not None:
            waiver = promotion_services.find_shipping_waiver(store, subtotal)
            if waiver is not None:
                fee = Decimal('0.00')
                is_free = True
        group['shipping_fee'] = float(fee)
        group['free_shipping'] = is_free
        shipping_total += fee

    issues = []
    for item in payload['items']:
        if not item['purchasable']:
            issues.append({
                'item_id': item['id'],
                'title': item['title'],
                'reason': item['unavailable_reason'],
            })
        elif item['stock_limited']:
            issues.append({
                'item_id': item['id'],
                'title': item['title'],
                'reason': f"Only {item['available']} left in stock.",
            })

    subtotal_total = Decimal(str(payload['totals']['subtotal']))
    promotion_discount = Decimal(str(payload['totals']['promotion_discount']))
    tax_total = Decimal('0.00')  # §6: reserved slot, not computed yet

    # §16.1 — an applied voucher is judged by the exact service checkout
    # uses; a rejection is reported, never silently swallowed.
    voucher_plan = None
    voucher_error = None
    voucher_code = (voucher_code or '').strip()
    if voucher_code:
        if request is not None and getattr(request, 'user', None) is not None:
            store_lines = promotion_services.build_store_lines(
                cart.items.select_related(
                    'variant__product__store', 'variant__product__category'
                )
            )
            try:
                voucher_plan = promotion_services.evaluate_voucher(
                    voucher_code, request.user, store_lines
                )
            except promotion_services.VoucherError as exc:
                voucher_error = {'error': exc.code, 'detail': str(exc)}
                voucher_code = ''
        else:
            voucher_error = {
                'error': 'voucher_requires_user',
                'detail': 'Sign in to apply a voucher.',
            }
            voucher_code = ''
    voucher_discount = voucher_plan['discount_total'] if voucher_plan else Decimal('0.00')

    payload['totals'].update({
        'shipping_total': float(shipping_total),
        'discount_total': float(voucher_discount),
        'voucher_code': voucher_plan['voucher'].code if voucher_plan else '',
        'tax_total': float(tax_total),
        'grand_total': float(max(
            Decimal('0.00'),
            subtotal_total + shipping_total + tax_total - promotion_discount - voucher_discount,
        )),
    })
    payload['issues'] = issues
    payload['payment_methods'] = payment_adapters.payment_method_options()
    payload['checkout_ready'] = bool(payload['items']) and not issues
    payload['voucher'] = (
        serialize_voucher_preview(voucher_plan)
        if voucher_plan is not None
        else None
    )
    payload['voucher_error'] = voucher_error
    return payload


def _money(value):
    """Decimal → JSON number (the wire contract used across the app)."""
    return float(value)


def serialize_order_item(item):
    """One immutable line snapshot — display never re-reads the catalog."""
    return {
        'id': item.id,
        'product_slug': item.product_slug,
        'title': item.product_title,
        'variant_name': item.variant_name,
        'sku': item.sku,
        'unit_price': _money(item.unit_price),
        'compare_at_price': (
            _money(item.compare_at_price)
            if item.compare_at_price is not None
            else None
        ),
        'quantity': item.quantity,
        'line_total': _money(item.line_total),
    }


# Statuses where the seller has accepted the order and therefore needs the
# full delivery details to fulfil it (§12.5 privacy ladder).
SELLER_ADDRESS_VISIBLE_STATUSES = frozenset({
    OrderStatus.PROCESSING,
    OrderStatus.PACKED,
    OrderStatus.SHIPPED,
    OrderStatus.IN_TRANSIT,
    OrderStatus.OUT_FOR_DELIVERY,
    OrderStatus.DELIVERED,
    OrderStatus.COMPLETED,
})

SELLER_CLOSED_STATUSES = frozenset({
    OrderStatus.CANCELLED,
    OrderStatus.REFUNDED,
    OrderStatus.REFUND_PENDING,
})


def serialize_seller_order(seller_order, order=None):
    """One store's slice of the order — the seller's fulfillment unit (§12.4).

    Privacy ladder (§12.5): until the seller accepts the order they see a
    masked customer label, a masked phone, and city/province only; the full
    name, phone, and street address unlock at `processing` so the parcel can
    actually ship. Emails and payment credentials never cross this shape.
    `can_process` / `can_pack` / `can_ship` mirror the fulfillment services
    so the UI offers only transitions the backend accepts.
    """
    parent_order = order if order is not None else seller_order.order
    items = list(seller_order.items.all())
    shipments = list(seller_order.shipments.all())
    payment = getattr(parent_order, 'payment', None)

    shipped_by_item = {}
    for shipment in shipments:
        if shipment.status == ShipmentStatus.CANCELLED:
            continue
        for entry in shipment.items.all():
            shipped_by_item[entry.order_item_id] = (
                shipped_by_item.get(entry.order_item_id, 0) + entry.quantity
            )
    unfulfilled = [
        item for item in items
        if shipped_by_item.get(item.id, 0) < item.quantity
    ]

    revealed = seller_order.status in SELLER_ADDRESS_VISIBLE_STATUSES
    return {
        'id': seller_order.id,
        'order_number': parent_order.number,
        # Store pk so buyers can open an order-scoped conversation (§15.1).
        'store_id': seller_order.store_id,
        'placed_at': parent_order.created_at.isoformat(),
        'store_slug': seller_order.store.slug,
        'store_name': seller_order.store_name,
        'status': seller_order.status,
        'item_count': sum(item.quantity for item in items),
        'subtotal': _money(seller_order.subtotal),
        'shipping_fee': _money(seller_order.shipping_fee),
        'total': _money(seller_order.total),
        'items': [serialize_order_item(item) for item in items],
        'shipments': [serialize_shipment(s) for s in shipments],
        'payment': (
            {
                'method': payment.method,
                'method_label': payment.get_method_display(),
                'status': payment.status,
                'paid': payment.paid_at is not None,
            }
            if payment is not None
            else None
        ),
        'customer': {
            'name': (
                parent_order.ship_to_name if revealed
                else mask_name(parent_order.ship_to_name)
            ),
            'phone': (
                parent_order.ship_to_phone if revealed
                else mask_phone(parent_order.ship_to_phone)
            ),
            'city': parent_order.shipping_city,
            'province': parent_order.shipping_province,
            'postal_code': parent_order.shipping_postal_code,
            'address': (
                ', '.join(part for part in [
                    parent_order.shipping_line1,
                    parent_order.shipping_line2,
                    parent_order.shipping_city,
                    parent_order.shipping_province,
                    parent_order.shipping_postal_code,
                ] if part)
                if revealed
                else None
            ),
            'revealed': revealed,
        },
        'can_process': seller_order.status in (
            OrderStatus.PLACED, OrderStatus.AWAITING_PAYMENT, OrderStatus.PAID,
        ),
        'can_pack': seller_order.status in (
            OrderStatus.PROCESSING, OrderStatus.PAID, OrderStatus.AWAITING_PAYMENT,
        ),
        'can_ship': (
            seller_order.status not in SELLER_CLOSED_STATUSES
            and bool(unfulfilled)
        ),
    }


def serialize_tracking_event(event):
    """Tracking event timeline entry (§10.2)."""
    return {
        'id': event.id,
        'status': event.status,
        'location': event.location,
        'description': event.description,
        'occurred_at': event.occurred_at.isoformat(),
    }


def serialize_shipment_item(shipment_item):
    """Item row inside a shipment (§10.2)."""
    return {
        'id': shipment_item.id,
        'order_item_id': shipment_item.order_item_id,
        'product_title': shipment_item.order_item.product_title,
        'variant_name': shipment_item.order_item.variant_name,
        'sku': shipment_item.order_item.sku,
        'quantity': shipment_item.quantity,
    }


def serialize_shipment(shipment):
    """Full shipment record with events and items (§10.2)."""
    return {
        'id': shipment.id,
        'tracking_number': shipment.tracking_number,
        'carrier': shipment.carrier,
        'carrier_name': shipment.carrier_name,
        'shipping_method': shipment.shipping_method,
        'shipping_fee': _money(shipment.shipping_fee),
        'status': shipment.status,
        'package_weight_grams': shipment.package_weight_grams,
        'package_notes': shipment.package_notes,
        'shipped_at': shipment.shipped_at.isoformat() if shipment.shipped_at else None,
        'estimated_delivery': (
            shipment.estimated_delivery.isoformat()
            if shipment.estimated_delivery
            else None
        ),
        'delivered_at': (
            shipment.delivered_at.isoformat()
            if shipment.delivered_at
            else None
        ),
        'recipient_name': shipment.recipient_name,
        'recipient_phone': shipment.recipient_phone,
        'shipping_address_text': shipment.shipping_address_text,
        'items': [serialize_shipment_item(si) for si in shipment.items.all()],
        'tracking_events': [
            serialize_tracking_event(evt) for evt in shipment.tracking_events.all()
        ],
    }



def serialize_tracking_status(shipment):
    """The **public** tracking projection — status only, no buyer PII (§10.3).

    A tracking number is a bearer token, not an identity: whoever holds it
    learns where the parcel is and when, never *who* it belongs to. The
    recipient, the address, the goods, the shipping fee and the seller's own
    handling notes stay with the order owner, the fulfilling seller and staff
    — the same privacy ladder §6 v1.7 draws for addresses, applied here
    because a tracking number is far easier to obtain than an order account.

    Events are projected to status + timestamp only: a courier's prose and a
    manually typed `description` can carry more than the journey needs.
    """
    return {
        'tracking_number': shipment.tracking_number,
        'carrier': shipment.carrier,
        'carrier_name': shipment.carrier_name,
        'shipping_method': shipment.shipping_method,
        'status': shipment.status,
        'shipped_at': shipment.shipped_at.isoformat() if shipment.shipped_at else None,
        'estimated_delivery': (
            shipment.estimated_delivery.isoformat()
            if shipment.estimated_delivery
            else None
        ),
        'delivered_at': (
            shipment.delivered_at.isoformat() if shipment.delivered_at else None
        ),
        'tracking_events': [
            {
                'status': event.status,
                'occurred_at': event.occurred_at.isoformat(),
            }
            for event in shipment.tracking_events.all()
        ],
    }


def serialize_order(order):
    """Full order read shape: snapshots + payment + per-store slices (§6)."""
    seller_orders = list(order.seller_orders.all())
    payment = getattr(order, 'payment', None)
    item_count = sum(
        item.quantity
        for seller_order in seller_orders
        for item in seller_order.items.all()
    )
    return {
        'id': order.id,
        'number': order.number,
        'status': order.status,
        'created_at': order.created_at.isoformat(),
        'item_count': item_count,
        'payment': serialize_payment(payment) if payment else None,
        'shipping_address': {
            'full_name': order.ship_to_name,
            'phone': order.ship_to_phone,
            'line1': order.shipping_line1,
            'line2': order.shipping_line2,
            'city': order.shipping_city,
            'province': order.shipping_province,
            'postal_code': order.shipping_postal_code,
        },
        'totals': {
            'subtotal': _money(order.subtotal),
            'shipping_total': _money(order.shipping_total),
            'savings_total': _money(order.savings_total),
            'promotion_discount': _money(order.promotion_discount),
            'discount_total': _money(order.discount_total),
            'voucher_code': order.voucher_code,
            'tax_total': _money(order.tax_total),
            'grand_total': _money(order.grand_total),
        },
        'seller_orders': [
            serialize_seller_order(seller_order, order=order)
            for seller_order in seller_orders
        ],
        'can_cancel': services.can_cancel(order),
        'timeline': services.build_order_timeline(order),
        'requests': [serialize_order_request(r) for r in order.requests.all()],
    }


def serialize_order_summary(order):
    """List row for the orders index (Phase 11.2) — snapshot values only."""
    return {
        'number': order.number,
        'status': order.status,
        'created_at': order.created_at.isoformat(),
        'item_count': sum(
            item.quantity
            for seller_order in order.seller_orders.all()
            for item in seller_order.items.all()
        ),
        'grand_total': _money(order.grand_total),
        'store_names': [so.store_name for so in order.seller_orders.all()],
        'can_cancel': services.can_cancel(order),
    }


def serialize_order_request(request):
    """One post-purchase request record (§11.3)."""
    return {
        'id': request.id,
        'kind': request.kind,
        'kind_label': request.get_kind_display(),
        'status': request.status,
        'reason': request.reason,
        'description': request.description,
        'seller_order_id': request.seller_order_id,
        'store_name': (
            request.seller_order.store_name if request.seller_order_id else ''
        ),
        'created_at': request.created_at.isoformat(),
    }


# --- Staff oversight shapes (13.5 — /staff/orders console) ------------------


def serialize_staff_order_row(order):
    """One oversight row — customer, money, payment state, store slices."""
    payment = getattr(order, 'payment', None)
    return {
        'number': order.number,
        'status': order.status,
        'created_at': order.created_at.isoformat(),
        'customer_email': order.user.email,
        'ship_to_city': order.shipping_city,
        'ship_to_province': order.shipping_province,
        'grand_total': _money(order.grand_total),
        'item_count': sum(
            item.quantity
            for seller_order in order.seller_orders.all()
            for item in seller_order.items.all()
        ),
        'store_names': [so.store_name for so in order.seller_orders.all()],
        'payment_method': payment.method if payment else None,
        'payment_status': payment.status if payment else None,
    }


def serialize_staff_shipment_row(shipment):
    """One parcel row for shipment oversight (13.5).

    `event_count` is annotated in the view — the list never N+1s the
    append-only tracking timeline.
    """
    return {
        'tracking_number': shipment.tracking_number,
        'order_number': shipment.seller_order.order.number,
        'store_name': shipment.seller_order.store_name,
        'carrier': shipment.carrier,
        'carrier_name': shipment.carrier_name,
        'status': shipment.status,
        'shipped_at': (
            shipment.shipped_at.isoformat() if shipment.shipped_at else None
        ),
        'delivered_at': (
            shipment.delivered_at.isoformat() if shipment.delivered_at else None
        ),
        'event_count': shipment.event_count,
        'created_at': shipment.created_at.isoformat(),
    }


def serialize_staff_request_row(request):
    """One request row with its order context (13.5 return/refund/dispute oversight)."""
    return {
        **serialize_order_request(request),
        'order_number': request.order.number,
        'customer_email': request.order.user.email,
    }


def serialize_stale_cod_row(order, *, now=None):
    """One stale COD row — what stock is being held, and for how long (§20.2 v2).

    `age_days` is the number a staff member actually acts on: it is how long
    this reservation has been sitting on a seller's `available` count while
    nobody paid. The order is reached through the normal staff detail route, so
    this listing stays identifiers-and-money rather than a second copy of the
    order.
    """
    payment = getattr(order, 'payment', None)
    now = now or timezone.now()
    return {
        'number': order.number,
        'status': order.status,
        'created_at': order.created_at.isoformat(),
        'age_days': max(0, (now - order.created_at).days),
        'customer_email': order.user.email,
        'ship_to_city': order.shipping_city,
        'ship_to_province': order.shipping_province,
        'grand_total': _money(order.grand_total),
        'item_count': sum(
            item.quantity
            for seller_order in order.seller_orders.all()
            for item in seller_order.items.all()
        ),
        'store_names': [so.store_name for so in order.seller_orders.all()],
        'payment_method': payment.method if payment else None,
        'payment_status': payment.status if payment else None,
    }
