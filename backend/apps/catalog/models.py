"""Catalog domain models (Phase 5 — PROJECT_CONTEXT §6 v1.3).

One entity, one model (marketplace-catalog rule 1): a variant is NOT a
second product; stock lives per variant only. Images are stored via Django
media handling (§8) — validated file upload arrives with this phase
(Pillow stays out per C3; validation is extension + size + magic bytes).
"""
import os
import uuid

from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel
from apps.common.utils import slugify_unique


class Category(TimeStampedModel):
    """Category tree (Phase 5.1) — hierarchy via self-FK + ordering."""

    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        related_name='children',
        blank=True,
        null=True,
    )
    name = models.CharField(max_length=96)
    slug = models.SlugField(max_length=110, unique=True, blank=True)
    description = models.TextField(blank=True)
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = 'categories'
        ordering = ['position', 'name']
        indexes = [
            models.Index(fields=['parent'], name='catalog_cat_parent_idx'),
            models.Index(fields=['is_active'], name='catalog_cat_active_idx'),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify_unique(Category, self.name, exclude_pk=self.pk)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Brand(TimeStampedModel):
    """Brand reference (Phase 5.1) — shared across stores/categories."""

    name = models.CharField(max_length=96, unique=True)
    slug = models.SlugField(max_length=110, unique=True, blank=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify_unique(Brand, self.name, exclude_pk=self.pk)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


def product_image_path(instance, filename):
    """media/products/<uuid>.<ext> — random names, no client path info (§10)."""
    ext = os.path.splitext(filename)[1].lower()
    return f'products/{uuid.uuid4().hex}{ext}'


class Product(TimeStampedModel):
    """Seller-owned product (Phase 5.2). Lifecycle per §6 v1.3:

    draft → pending_review → published → unpublished / rejected / archived;
    out-of-stock is a derived display state, never a stored status.
    """

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PENDING_REVIEW = 'pending_review', 'Pending review'
        PUBLISHED = 'published', 'Published'
        UNPUBLISHED = 'unpublished', 'Unpublished'
        REJECTED = 'rejected', 'Rejected'
        ARCHIVED = 'archived', 'Archived'

    store = models.ForeignKey(
        'stores.Store',
        on_delete=models.CASCADE,
        related_name='products',
    )
    category = models.ForeignKey(
        'catalog.Category',
        on_delete=models.PROTECT,
        related_name='products',
        blank=True,
        null=True,
    )
    brand = models.ForeignKey(
        'catalog.Brand',
        on_delete=models.SET_NULL,
        related_name='products',
        blank=True,
        null=True,
    )
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(blank=True)
    base_price = models.DecimalField(max_digits=12, decimal_places=2)
    compare_at_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Reference price; discounts derive from this server-side.',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    rejection_reason = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='reviewed_products',
        blank=True,
        null=True,
    )
    reviewed_at = models.DateTimeField(blank=True, null=True)
    attributes = models.JSONField(blank=True, default=dict)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['store'], name='catalog_prod_store_idx'),
            models.Index(fields=['status'], name='catalog_prod_status_idx'),
            models.Index(fields=['category'], name='catalog_prod_category_idx'),
            models.Index(fields=['base_price'], name='catalog_prod_price_idx'),
            models.Index(fields=['created_at'], name='catalog_prod_created_idx'),
            models.Index(fields=['slug'], name='catalog_prod_slug_idx'),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify_unique(Product, self.title, exclude_pk=self.pk)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.title} ({self.status})'

# catalog part 2 (variants, images, inventory, movements) appended below


class Variant(TimeStampedModel):
    """Purchaseable unit — carries its own price/stock (rule 2)."""

    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.CASCADE,
        related_name='variants',
    )
    sku = models.CharField(max_length=64, unique=True, blank=True)
    name = models.CharField(max_length=128, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    attributes = models.JSONField(blank=True, default=dict)

    class Meta:
        ordering = ['-is_default', 'price']
        constraints = [
            models.UniqueConstraint(
                fields=['product'],
                condition=models.Q(is_default=True),
                name='catalog_one_default_variant_inventory',
            ),
        ]
        indexes = [
            models.Index(fields=['product'], name='catalog_var_product_idx'),
            models.Index(fields=['is_active'], name='catalog_var_active_idx'),
        ]

    def save(self, *args, **kwargs):
        if not self.sku:
            # Auto-SKU from the product slug — blank '' can never collide
            # (unique constraint holds across all variants).
            base = self.product.slug or 'variant'
            candidate = base
            counter = 2
            while Variant.objects.filter(sku=candidate).exclude(pk=self.pk).exists():
                candidate = f'{base}-{counter}'
                counter += 1
            self.sku = candidate
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.product.title} — {self.name or self.sku}'


class ProductImage(TimeStampedModel):
    """Validated upload (Phase 5.2/5.3) — Django media handling (§8).

    FileField (not ImageField) keeps Pillow out of the runtime (C3);
    content validation lives in services.validate_image_file (extension +
    5 MB cap + magic bytes). Add Pillow later only if image processing
    (thumbnails etc.) is approved.
    """

    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.CASCADE,
        related_name='images',
    )
    image = models.FileField(upload_to=product_image_path)
    alt_text = models.CharField(max_length=180, blank=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['position', 'created_at']
        indexes = [
            models.Index(fields=['product'], name='catalog_img_product_idx'),
        ]

    def __str__(self):
        return f'Image {self.position} for {self.product.title}'


class Inventory(TimeStampedModel):
    """Per-variant stock (Phase 5.4) — the ONLY place stock lives.

    available = on_hand − reserved; never negative (DB CHECK constraint
    below). Order-time reservation (Phase 8) reuses services here.
    """

    variant = models.OneToOneField(
        'catalog.Variant',
        on_delete=models.CASCADE,
        related_name='inventory',
    )
    on_hand = models.PositiveIntegerField(default=0)
    reserved = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=5)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(reserved__lte=models.F('on_hand')),
                name='catalog_inventory_never_negative',
            ),
        ]
        indexes = [
            models.Index(fields=['variant'], name='catalog_inv_variant_idx'),
        ]

    @property
    def available(self):
        return self.on_hand - self.reserved

    def __str__(self):
        return f'{self.variant.sku}: {self.available} available'

# catalog part 3 (stock movements) appended below


class StockMovement(TimeStampedModel):
    """Append-only stock history (Phase 5.4) — the audit trail for inventory.

    Rows are written by catalog services inside the same transaction as the
    Inventory change; never edited or deleted by application code.
    """

    class Reason(models.TextChoices):
        INITIAL = 'initial', 'Initial stock'
        ADJUSTMENT = 'adjustment', 'Manual adjustment'
        RESERVE = 'reserve', 'Reservation'
        RELEASE = 'release', 'Release'
        SALE = 'sale', 'Sale'
        RESTOCK = 'restock', 'Restock'

    variant = models.ForeignKey(
        'catalog.Variant',
        on_delete=models.CASCADE,
        related_name='stock_movements',
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='stock_movements',
        blank=True,
        null=True,
    )
    reason = models.CharField(max_length=16, choices=Reason.choices)
    quantity_delta = models.IntegerField()
    resulting_on_hand = models.PositiveIntegerField()
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['variant'], name='catalog_move_variant_idx'),
            models.Index(fields=['created_at'], name='catalog_move_created_idx'),
        ]

    def __str__(self):
        return f'{self.variant.sku} {self.reason} {self.quantity_delta:+d}'
