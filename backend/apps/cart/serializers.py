"""Cart & wishlist serializers — declared fields only (backend-api rule 2).

The cart payload is assembled server-side on every read (§6): live prices,
live stock, computed line totals, store-grouped items, and totals — the
client renders these values and never recomputes them (marketplace-orders
rule 1). Money crosses the wire as numbers, matching the catalog contract.
"""
from rest_framework import serializers

from apps.catalog import services as catalog_services
from apps.catalog.serializers import PublicProductSerializer

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
        'primary_image': _primary_image_url(product, request),
        'store_slug': product.store.slug,
        'store_name': product.store.name,
    }


def build_cart_payload(cart, request=None):
    """Full cart read shape: items + store groups + totals (§6)."""
    items = [
        serialize_cart_item(item, request)
        for item in cart.items.select_related(
            'variant', 'variant__product', 'variant__product__store'
        ).prefetch_related('variant__product__images')
    ]
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
            },
        )
        group['items'].append(item)
        group['item_count'] += item['quantity']
        group['subtotal'] = round(group['subtotal'] + item['line_total'], 2)
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
    }
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
