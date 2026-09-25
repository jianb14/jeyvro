"""Order domain models (Phase 8 — PROJECT_CONTEXT §6 v1.7).

One parent `Order` per checkout, one `SellerOrder` per store (multi-vendor
scoping), and immutable `OrderItem` snapshots. Money is Decimal(12,2) and is
always resolved server-side at creation — the client never sends prices,
fees, or totals (§6). Snapshots never change when the catalog or the
customer's address book changes later (§9).
"""
from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class OrderStatus(models.TextChoices):
    """Shared order lifecycle (§6 v1.7) — parent and per-store orders.

    Transitions happen only in service functions (CONVENTIONS.md — Status
    fields): Phase 8 owns placed/cancelled, Phase 9 sets awaiting_payment at
    checkout (payments.services owns paid / refunded, expiry releases), and
    Phase 10 adds fulfillment.
    """

    PLACED = 'placed', 'Placed'
    AWAITING_PAYMENT = 'awaiting_payment', 'Awaiting payment'
    PAID = 'paid', 'Paid'
    SHIPPED = 'shipped', 'Shipped'
    DELIVERED = 'delivered', 'Delivered'
    COMPLETED = 'completed', 'Completed'
    CANCELLED = 'cancelled', 'Cancelled'
    REFUNDED = 'refunded', 'Refunded'


class Order(TimeStampedModel):
    """Parent order — one checkout, fully snapshotted and priced server-side.

    The shipping address is frozen as plain fields (never a live FK to the
    address book): later edits to the saved address must not alter an
    existing order (§6/§9).
    """

    Status = OrderStatus

    number = models.CharField(
        max_length=24,
        unique=True,
        help_text='Public identifier, e.g. JV-20260925-8F3K2Q7A (services generate it).',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='orders',
    )
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.PLACED,
    )

    # Shipping address snapshot — immutable, taken at checkout (§6 v1.7).
    ship_to_name = models.CharField(max_length=128)
    ship_to_phone = models.CharField(max_length=32)
    shipping_line1 = models.CharField(max_length=256)
    shipping_line2 = models.CharField(max_length=256, blank=True)
    shipping_city = models.CharField(max_length=128)
    shipping_province = models.CharField(max_length=128)
    shipping_postal_code = models.CharField(max_length=16)

    # Money snapshots (C6 — Decimal only, computed server-side).
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    shipping_total = models.DecimalField(max_digits=12, decimal_places=2)
    savings_total = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00')
    )
    tax_total = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00')
    )
    grand_total = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user'], name='orders_user_idx'),
            models.Index(fields=['status'], name='orders_status_idx'),
            models.Index(fields=['created_at'], name='orders_created_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(grand_total__gte=0),
                name='orders_grand_total_nonnegative',
            ),
        ]

    def __str__(self):
        return f'{self.number} ({self.status})'


class SellerOrder(TimeStampedModel):
    """Per-store sub-order — the unit a seller fulfills (§6 multi-vendor).

    Carries its own status (fulfillment is per store); the parent `Order`
    status stays the overall view. Phase 8 sets both to placed/cancelled.
    """

    Status = OrderStatus

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='seller_orders',
    )
    store = models.ForeignKey(
        'stores.Store',
        on_delete=models.PROTECT,
        related_name='seller_orders',
    )
    store_name = models.CharField(
        max_length=128,
        help_text='Snapshot — the store may be renamed later.',
    )
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.PLACED,
    )
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    shipping_fee = models.DecimalField(max_digits=12, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ['id']
        constraints = [
            models.UniqueConstraint(
                fields=['order', 'store'],
                name='orders_one_seller_order_per_store',
            ),
        ]
        indexes = [
            models.Index(fields=['store'], name='orders_seller_store_idx'),
            models.Index(fields=['status'], name='orders_seller_status_idx'),
        ]

    def __str__(self):
        return f'{self.order.number} → {self.store_name}'


class OrderItem(TimeStampedModel):
    """Immutable purchase snapshot — title/variant/price never change (§9).

    Product and variant FKs stay for lineage (PROTECT — money records are
    never orphaned); display always reads the snapshot fields.
    """

    seller_order = models.ForeignKey(
        SellerOrder,
        on_delete=models.CASCADE,
        related_name='items',
    )
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.PROTECT,
        related_name='order_items',
    )
    variant = models.ForeignKey(
        'catalog.Variant',
        on_delete=models.PROTECT,
        related_name='order_items',
    )
    product_title = models.CharField(
        max_length=180, help_text='Snapshot of the title at purchase time.'
    )
    product_slug = models.SlugField(
        max_length=200, help_text='Snapshot — keeps order links stable.'
    )
    variant_name = models.CharField(max_length=128, blank=True)
    sku = models.CharField(max_length=64)
    unit_price = models.DecimalField(
        max_digits=12, decimal_places=2, help_text='Snapshot of the paid unit price.'
    )
    compare_at_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Snapshot for savings display; null when there was no discount.',
    )
    quantity = models.PositiveIntegerField()
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ['id']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1),
                name='orders_item_quantity_positive',
            ),
        ]
        indexes = [
            models.Index(fields=['seller_order'], name='orders_item_seller_idx'),
            models.Index(fields=['product'], name='orders_item_product_idx'),
        ]

    def __str__(self):
        return f'{self.product_title} x {self.quantity}'
