"""Cart & wishlist serializers — declared fields only (backend-api rule 2).

The cart payload is assembled server-side on every read (§6): live prices,
live stock, computed line totals, store-grouped items, and totals — the
client renders these values and never recomputes them (marketplace-orders
rule 1). Money crosses the wire as numbers, matching the catalog contract.
"""
from decimal import Decimal

from rest_framework import serializers

from apps.catalog import services as catalog_services
from apps.catalog.serializers import PublicProductSerializer
from apps.promotions import services as promotion_services

from . import services
from .models import WishlistItem


class AddCartItemSerializer(serializers.Serializer):
    """POST /cart/items body — validated server-side (§10.1)."""

    variant_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(
        min_value=1, max_value=services.MAX_LINE_QUANTITY, default=1
    )


class SetCartItemQuantitySerializer(serializers.Serializer):
    """PATCH /cart/items/<id> body."""

    quantity = serializers.IntegerField(
        min_value=1, max_value=services.MAX_LINE_QUANTITY
    )


class AddWishlistItemSerializer(serializers.Serializer):
    """POST /wishlist/ body — the product slug is the public identifier."""

    product_id = serializers.CharField(max_length=110)


def _primary_image_url(product, request):
    image = next(iter(product.images.all()), None)  # prefetched + ordered
    if image is None:
        return None
    url = image.image.url
    return request.build_absolute_uri(url) if request else url


def serialize_cart_item(item, request=None):
    """One cart line: server-truth price/stock plus computed values."""
    variant = item.variant
    product = variant.product
    purchasable, available, reason = services.variant_purchase_state(variant)
    price = variant.price
    compare_at = product.compare_at_price
    if compare_at is not None and compare_at <= price:
        compare_at = None
    return {
        'id': item.id,
        'variant_id': variant.id,
        'product_slug': product.slug,
        'title': product.title,
        'variant_name': variant.name,
        'sku': variant.sku,
        'price': float(price),
        'compare_at_price': float(compare_at) if compare_at is not None else None,
        'discount': catalog_services.compute_discount_percent(price, compare_at),
        'quantity': item.quantity,
        'line_total': float(price * item.quantity),
        'available': available,
        'purchasable': purchasable,
        'unavailable_reason': reason,
        'stock_limited': purchasable and available < item.quantity,
        # §16.2 — filled in by `build_cart_payload`'s engine pass; the
        # defaults keep the wire shape stable when no promotion applies.
        'promotion_savings': 0.0,
        'promotion_label': '',
        'primary_image': _primary_image_url(product, request),
        'store_slug': product.store.slug,
        'store_name': product.store.name,
    }


def build_cart_payload(cart, request=None):
    """Full cart read shape: items + store groups + totals (§6).

    Automatic promotions (§16.2) run one engine pass per store here — the
    exact rules the checkout preview, the voucher preview, and order
    creation judge — so a discount promised in the cart can never be
    refused at checkout. Line totals stay gross; each line carries its
    `promotion_savings` and the store groups and totals carry the store's
    `promotion_discount`."""
    rows = list(
        cart.items.select_related(
            'variant', 'variant__product', 'variant__product__store'
        ).prefetch_related('variant__product__images')
    )
    items = [serialize_cart_item(row, request) for row in rows]
    items_by_id = {item['id']: item for item in items}

    store_rows = {}
    for row in rows:
        store_rows.setdefault(row.variant.product.store, []).append(row)

    store_promotions = {}
    for store, store_item_rows in store_rows.items():
        engine_lines = [
            promotion_services.line_entry(
                idx,
                row.variant.product,
                row.quantity,
                row.variant.price,
                row.variant.price * row.quantity,
            )
            for idx, row in enumerate(store_item_rows)
        ]
        promo = promotion_services.evaluate_store_lines(store, engine_lines)
        store_promotions[store.slug] = promo
        for idx, row in enumerate(store_item_rows):
            savings = promo['line_discounts'].get(idx)
            if savings:
                item = items_by_id[row.id]
                item['promotion_savings'] = float(savings)
                item['promotion_label'] = promo['labels'].get(idx, '')

    groups = {}
    for item in items:
        group = groups.setdefault(
            item['store_slug'],
            {
                'store_slug': item['store_slug'],
                'store_name': item['store_name'],
                'items': [],
                'item_count': 0,
                'subtotal': 0.0,
                'promotion_discount': 0.0,
            },
        )
        group['items'].append(item)
        group['item_count'] += item['quantity']
        group['subtotal'] = round(group['subtotal'] + item['line_total'], 2)
    for slug, promo in store_promotions.items():
        if slug in groups:
            groups[slug]['promotion_discount'] = float(promo['discount_total'])

    promotion_discount = sum(
        (promo['discount_total'] for promo in store_promotions.values()),
        start=Decimal('0.00'),
    )
    totals = {
        'line_count': len(items),
        'item_count': sum(item['quantity'] for item in items),
        'subtotal': round(sum(item['line_total'] for item in items), 2),
        'savings': round(
            sum(
                (item['compare_at_price'] - item['price']) * item['quantity']
                for item in items
                if item['compare_at_price']
            ),
            2,
        ),
        'promotion_discount': float(promotion_discount),
    }
    # §20.2 v3 — publish the whole-order unit ceiling on the read so the cart can
    # warn *before* checkout. Advisory only: the binding check is on the server,
    # in `orders.services.create_order`, where the cart is re-read under lock.
    totals['max_order_units'] = services.max_order_units()
    totals['over_unit_ceiling'] = totals['item_count'] > totals['max_order_units']
    # §16.2 — the net figure lives server-side too: the cart renders this as
    # its "Items total" instead of subtracting anything in the browser.
    totals['items_total'] = float(max(
        Decimal('0.00'),
        Decimal(str(totals['subtotal'])) - promotion_discount,
    ))
    return {
        'id': cart.id,
        'owner': cart.owner_type,
        'items': items,
        'groups': list(groups.values()),
        'totals': totals,
    }


class WishlistItemSerializer(serializers.ModelSerializer):
    """Saved product for its owner — availability derived server-side."""

    product = serializers.SerializerMethodField()
    available = serializers.SerializerMethodField()

    class Meta:
        model = WishlistItem
        fields = ['id', 'created_at', 'available', 'product']

    def get_product(self, obj):
        return PublicProductSerializer(obj.product, context=self.context).data

    def get_available(self, obj):
        return services.product_is_available(obj.product)
