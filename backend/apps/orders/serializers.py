"""Order serializers — declared shapes only (backend-api rule 2).

Money crosses the wire as JSON numbers (matching the catalog/cart contract)
and every value is server truth: the checkout preview reuses the cart
payload's live lines and adds per-store shipping, and order payloads render
only the immutable snapshots written at creation.
"""
from decimal import Decimal

from rest_framework import serializers

from apps.cart.serializers import build_cart_payload
from apps.payments import adapters as payment_adapters
from apps.payments.models import PaymentMethod
from apps.payments.serializers import serialize_payment
from apps.stores.models import Store

from . import services
from .models import RequestKind


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



def build_checkout_preview(cart, request=None):
    """Checkout read shape: cart truth + per-store shipping + totals (§6).

    Reuses the cart payload (one implementation of line truth) and adds the
    fee each store charges, the payment options (with live availability from
    the adapter registry), an `issues` list for blocked lines, and the final
    totals — the client only renders these numbers.
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
                'shipping_total': 0,
                'tax_total': 0,
                'grand_total': 0,
            },
            'issues': [],
            'payment_methods': payment_adapters.payment_method_options(),
            'checkout_ready': False,
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
    tax_total = Decimal('0.00')  # §6: reserved slot, not computed yet
    payload['totals'].update({
        'shipping_total': float(shipping_total),
        'tax_total': float(tax_total),
        'grand_total': float(subtotal_total + shipping_total + tax_total),
    })
    payload['issues'] = issues
    payload['payment_methods'] = payment_adapters.payment_method_options()
    payload['checkout_ready'] = bool(payload['items']) and not issues
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


def serialize_seller_order(seller_order):
    """One store's slice of the order — the seller's fulfillment unit."""
    shipments = list(seller_order.shipments.all())
    return {
        'id': seller_order.id,
        'store_slug': seller_order.store.slug,
        'store_name': seller_order.store_name,
        'status': seller_order.status,
        'subtotal': _money(seller_order.subtotal),
        'shipping_fee': _money(seller_order.shipping_fee),
        'total': _money(seller_order.total),
        'items': [serialize_order_item(item) for item in seller_order.items.all()],
        'shipments': [serialize_shipment(s) for s in shipments],
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
            'tax_total': _money(order.tax_total),
            'grand_total': _money(order.grand_total),
        },
        'seller_orders': [
            serialize_seller_order(seller_order) for seller_order in seller_orders
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
