"""Cart & wishlist domain models (Phase 7 — PROJECT_CONTEXT §6).

One cart per customer or per guest session — never both (DB CHECK) — one
line per variant, and a private, product-level wishlist. No price is ever
stored on a cart line: unit prices are resolved server-side on every read
and recomputed again at checkout (§6), so a stale price can never be
trusted from the client or from an earlier request.
"""
from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class Cart(TimeStampedModel):
    """Server-side basket (§6): exactly one owner — a user OR a session.

    Guest strategy (Phase 7): anonymous visitors get a session-keyed cart
    (the Django session cookie); `services.merge_guest_cart` folds it into
    the account cart at login, so nothing is lost across the sign-in step.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='carts',
        blank=True,
        null=True,
    )
    session_key = models.CharField(
        max_length=40,
        blank=True,
        help_text='Django session key for guest carts; empty for user carts.',
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(user__isnull=False, session_key='')
                    | (models.Q(user__isnull=True) & ~models.Q(session_key=''))
                ),
                name='cart_exactly_one_owner',
            ),
            models.UniqueConstraint(
                fields=['user'],
                condition=models.Q(user__isnull=False),
                name='cart_one_per_user',
            ),
            models.UniqueConstraint(
                fields=['session_key'],
                condition=~models.Q(session_key=''),
                name='cart_one_per_session',
            ),
        ]

    @property
    def owner_type(self):
        return 'user' if self.user_id else 'guest'

    def __str__(self):
        return f'Cart #{self.pk} ({self.owner_type})'


class CartItem(TimeStampedModel):
    """One line per variant — quantity only, never a stored price (§6)."""

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey(
        'catalog.Variant',
        on_delete=models.CASCADE,
        related_name='cart_items',
    )
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['cart', 'variant'], name='cart_one_line_per_variant'
            ),
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1), name='cart_quantity_positive'
            ),
        ]
        indexes = [
            models.Index(fields=['cart'], name='cart_item_cart_idx'),
        ]

    def __str__(self):
        return f'{self.variant.sku} x {self.quantity}'


class WishlistItem(TimeStampedModel):
    """Private saved product (Phase 7.2) — one row per (user, product)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wishlist_items',
    )
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.CASCADE,
        related_name='wishlist_items',
    )

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'product'], name='wishlist_one_per_product'
            ),
        ]
        indexes = [
            models.Index(fields=['user'], name='wishlist_user_idx'),
        ]

    def __str__(self):
        return f'{self.user_id} -> {self.product_id}'
