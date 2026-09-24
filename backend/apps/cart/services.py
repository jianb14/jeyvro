"""Cart & wishlist services — business logic lives here, never in views (§8).

Rules honoured (PROJECT_CONTEXT §6, marketplace-orders):
- the cart is server-side and per-user (or per guest session); prices and
  totals are resolved on every read and recomputed again at checkout
- add/update validate variant, product, store, and live stock — cart-time
  checks are advisory (no reservation); checkout locks stock rows (Phase 8)
- guest carts merge into the account cart at login (single entry point:
  the accounts LoginView, which passes the pre-login session key)
"""
from django.db import transaction

from apps.catalog.models import Product
from apps.stores.models import Store

from .models import Cart, CartItem, WishlistItem

MAX_LINE_QUANTITY = 99


# --- Cart resolution (guest strategy: session-keyed carts) ---

def get_or_create_cart(request):
    """The requester's cart — the account cart when signed in, else the
    session cart (creating the Django session on first touch)."""
    if request.user.is_authenticated:
        return Cart.objects.get_or_create(user=request.user)[0]
    if not request.session.session_key:
        request.session.create()
    return Cart.objects.get_or_create(session_key=request.session.session_key)[0]


# --- Server-truth gates (variant, product, store, stock) ---

def product_is_available(product):
    """Public availability — the same gate the catalog applies (§6 v1.3)."""
    return (
        product.status == Product.Status.PUBLISHED
        and product.store.status == Store.Status.ACTIVE
    )


def variant_purchase_state(variant):
    """Server truth for one variant: (purchasable, available, reason).

    `available` is live stock (on_hand − reserved, never negative); the
    reason is a customer-safe sentence when the variant cannot be bought.
    """
    inventory = getattr(variant, 'inventory', None)
    available = inventory.available if inventory is not None else 0
    if not variant.is_active or not product_is_available(variant.product):
        return False, available, 'This product is no longer available.'
    if available < 1:
        return False, available, 'This item is out of stock.'
    return True, available, ''


def _assert_buyable(variant):
    purchasable, available, reason = variant_purchase_state(variant)
    if not purchasable:
        raise ValueError(reason)
    return available


def _clean_quantity(quantity):
    if quantity < 1:
        raise ValueError('Quantity must be at least 1.')
    if quantity > MAX_LINE_QUANTITY:
        raise ValueError(f'Quantity cannot exceed {MAX_LINE_QUANTITY} per item.')
    return quantity


# --- Cart item operations (each returns the touched line) ---

def add_item(cart, variant, quantity=1):
    """Adds to the cart — an existing line is incremented, never duplicated."""
    _clean_quantity(quantity)
    available = _assert_buyable(variant)
    if quantity > available:
        raise ValueError(f'Only {available} left in stock.')
    with transaction.atomic():
        item = (
            CartItem.objects.select_for_update()
            .filter(cart=cart, variant=variant)
            .first()
        )
        if item is None:
            return CartItem.objects.create(
                cart=cart, variant=variant, quantity=quantity
            )
        new_quantity = _clean_quantity(item.quantity + quantity)
        if new_quantity > available:
            raise ValueError(f'Only {available} left in stock.')
        item.quantity = new_quantity
        item.save(update_fields=['quantity', 'updated_at'])
    return item


def set_item_quantity(cart, item_id, quantity):
    """Sets an exact line quantity after revalidating live stock."""
    _clean_quantity(quantity)
    item = (
        CartItem.objects.select_related(
            'variant', 'variant__product', 'variant__product__store'
        )
        .filter(cart=cart, pk=item_id)
        .first()
    )
    if item is None:
        raise CartItem.DoesNotExist('Cart item not found.')
    available = _assert_buyable(item.variant)
    if quantity > available:
        raise ValueError(f'Only {available} left in stock.')
    item.quantity = quantity
    item.save(update_fields=['quantity', 'updated_at'])
    return item


def remove_item(cart, item_id):
    deleted, _ = CartItem.objects.filter(cart=cart, pk=item_id).delete()
    if not deleted:
        raise CartItem.DoesNotExist('Cart item not found.')


def clear_cart(cart):
    CartItem.objects.filter(cart=cart).delete()


# --- Guest -> account merge (runs at login) ---

def merge_guest_cart(user, session_key):
    """Folds the guest session's cart into the user's cart at login.

    Quantities are summed per variant (capped at the line maximum) and the
    guest cart is removed in the same transaction — the merge is atomic, so
    a failure never loses or duplicates lines. Returns the user cart when a
    merge happened, else None.
    """
    if not session_key:
        return None
    guest_cart = (
        Cart.objects.filter(session_key=session_key, user__isnull=True).first()
    )
    if guest_cart is None:
        return None
    with transaction.atomic():
        user_cart, _ = Cart.objects.get_or_create(user=user)
        for guest_item in guest_cart.items.select_related('variant'):
            existing = (
                CartItem.objects.select_for_update()
                .filter(cart=user_cart, variant=guest_item.variant)
                .first()
            )
            if existing is None:
                CartItem.objects.create(
                    cart=user_cart,
                    variant=guest_item.variant,
                    quantity=guest_item.quantity,
                )
            else:
                existing.quantity = min(
                    existing.quantity + guest_item.quantity, MAX_LINE_QUANTITY
                )
                existing.save(update_fields=['quantity', 'updated_at'])
        guest_cart.delete()
    return user_cart


# --- Wishlist (private per customer, product-level) ---

def add_to_wishlist(user, product):
    """Idempotent save — returns (item, created)."""
    return WishlistItem.objects.get_or_create(user=user, product=product)


def remove_from_wishlist(user, product):
    """Removes only the requesting user's row (privacy by query scope)."""
    deleted, _ = WishlistItem.objects.filter(user=user, product=product).delete()
    return deleted
