"""Catalog services — every lifecycle/stock transition lives here (§13).

Rules honoured (PROJECT_CONTEXT §6 v1.3, marketplace-catalog):
- sellers own draft→pending_review, unpublish, archive; staff own
  pending_review→published / rejected (reason required, audit-logged)
- stock lives per variant; every change is transactional with row locks,
  appends a StockMovement, and can never make available negative
- order-time reservation (Phase 8) reuses reserve/release from here
"""
from decimal import Decimal
import os

from django.db import transaction
from django.utils import timezone

from apps.audit.services import log_event

from .models import Brand, Category, Inventory, Product, StockMovement, Variant

MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB (validated at the upload view)


# --- Pricing (resolved server-side, never trusted from the client) ---

def resolve_display_price(product):
    """Lowest active variant price; falls back to the product base price."""
    variant_prices = [
        v.price for v in product.variants.filter(is_active=True)
    ]
    return min(variant_prices) if variant_prices else product.base_price


def compute_discount_percent(price, compare_at_price):
    """Server-computed discount from the reference price (§6 v1.3)."""
    if not compare_at_price or compare_at_price <= price:
        return 0
    ratio = (compare_at_price - price) / compare_at_price
    return int((ratio * Decimal('100')).quantize(Decimal('1')))


# --- Product lifecycle (transitions only through these functions) ---

def _get_owned_product(seller_user, product_id):
    """Store-scoped fetch: a seller touches only their own products."""
    return Product.objects.get(
        pk=product_id, store__user=seller_user
    )


def create_product(seller_user, *, store, title, base_price, **extra):
    """Seller creates a product in draft (variants/images added after)."""
    if store.user_id != seller_user.pk:
        raise PermissionError('You may only manage your own store products.')
    return Product.objects.create(
        store=store,
        title=title,
        base_price=base_price,
        **extra,
    )


def submit_for_review(seller_user, product_id):
    """draft/rejected/unpublished → pending_review (seller action)."""
    product = _get_owned_product(seller_user, product_id)
    allowed = (
        Product.Status.DRAFT,
        Product.Status.REJECTED,
        Product.Status.UNPUBLISHED,
    )
    if product.status not in allowed:
        raise ValueError('This product cannot be submitted for review.')
    if not product.variants.exists():
        raise ValueError('Add at least one variant before submitting.')
    product.status = Product.Status.PENDING_REVIEW
    product.rejection_reason = ''
    product.save(update_fields=['status', 'rejection_reason', 'updated_at'])
    return product


def unpublish_product(seller_user, product_id):
    """published → unpublished (seller action; storefront disappears)."""
    product = _get_owned_product(seller_user, product_id)
    if product.status != Product.Status.PUBLISHED:
        raise ValueError('Only published products can be unpublished.')
    product.status = Product.Status.UNPUBLISHED
    product.save(update_fields=['status', 'updated_at'])
    return product


def archive_product(seller_user, product_id):
    """draft/rejected/unpublished → archived (terminal; never public)."""
    product = _get_owned_product(seller_user, product_id)
    allowed = (
        Product.Status.DRAFT,
        Product.Status.REJECTED,
        Product.Status.UNPUBLISHED,
    )
    if product.status not in allowed:
        raise ValueError('This product cannot be archived.')
    product.status = Product.Status.ARCHIVED
    product.save(update_fields=['status', 'updated_at'])
    return product


def update_product(seller_user, product_id, **fields):
    """Seller edits the editable fields of their own product (§12.2).

    Status transitions never happen through edits — they run through the
    submit/unpublish/archive services (marketplace-catalog rule 4). The
    slug stays: it is the product's public identity, so a retitle never
    breaks existing links.
    """
    product = _get_owned_product(seller_user, product_id)
    if product.status == Product.Status.ARCHIVED:
        raise ValueError('Archived products cannot be edited.')
    editable = (
        'title', 'description', 'base_price', 'compare_at_price',
        'category', 'brand', 'attributes',
    )
    changed = [field for field in editable if field in fields]
    for field in changed:
        setattr(product, field, fields[field])
    if changed:
        product.save(update_fields=changed + ['updated_at'])
    return product


def delete_product(seller_user, product_id):
    """Delete a never-ordered product; archive one with order history (§12.2).

    OrderItem.product is PROTECT (money records are never orphaned), so a
    product that has ever been ordered resolves to archive instead of a
    hard delete — the seller's intent ("remove it from my store") still
    holds and past orders keep their lineage. Returns (action, product).
    """
    product = _get_owned_product(seller_user, product_id)
    if product.order_items.exists():
        if product.status != Product.Status.ARCHIVED:
            product.status = Product.Status.ARCHIVED
            product.save(update_fields=['status', 'updated_at'])
        return 'archived', product
    for image in product.images.all():
        image.image.delete(save=False)
    product.delete()
    return 'deleted', None


def review_product(staff_user, product_id, *, decision, reason=''):
    """Staff publishes or rejects a pending_review product (audit-logged)."""
    product = Product.objects.get(pk=product_id)
    if product.status != Product.Status.PENDING_REVIEW:
        raise ValueError('This product is not pending review.')
    if decision not in (Product.Status.PUBLISHED, Product.Status.REJECTED):
        raise ValueError("Decision must be 'published' or 'rejected'.")
    if decision == Product.Status.REJECTED and not reason.strip():
        raise ValueError('A rejection reason is required.')

    with transaction.atomic():
        product.status = decision
        product.rejection_reason = reason if decision == Product.Status.REJECTED else ''
        product.reviewed_by = staff_user
        product.reviewed_at = timezone.now()
        product.save(update_fields=[
            'status', 'rejection_reason', 'reviewed_by', 'reviewed_at',
            'updated_at',
        ])
        log_event(
            staff_user,
            f'product_review_{decision}',
            product,
            detail={'store_id': product.store_id, 'reason': reason},
        )
    return product


def staff_unpublish_product(staff_user, product, *, reason):
    """Staff takedown: published → unpublished (moderation; audit-logged).

    Unlike the seller's own unpublish, a takedown demands a reason — it is
    stored on the product so the seller sees why it disappeared, and it is
    written to the audit row (§4 matrix: moderators own publish/reject/
    unpublish).
    """
    if product.status != Product.Status.PUBLISHED:
        raise ValueError('Only published products can be taken down.')
    if not reason.strip():
        raise ValueError('A reason is required for a staff takedown.')

    with transaction.atomic():
        product.status = Product.Status.UNPUBLISHED
        product.rejection_reason = reason.strip()
        product.save(update_fields=['status', 'rejection_reason', 'updated_at'])
        log_event(
            staff_user,
            'product_unpublished',
            product,
            detail={'store_id': product.store_id, 'reason': reason.strip()},
        )
    return product


# --- Taxonomy management (13.4 — operations/administrator, audited) ---

def _validate_category_parent(category, parent):
    """Refuses self-parenting and cycles: walking up from the new parent
    must never meet the category being moved."""
    if parent is None:
        return
    if parent.pk == category.pk:
        raise ValueError('A category cannot be its own parent.')
    seen = {parent.pk}  # guard against pre-existing corrupt loops
    cursor = parent.parent
    while cursor is not None and cursor.pk not in seen:
        if cursor.pk == category.pk:
            raise ValueError(
                'A category cannot be moved under its own descendant.'
            )
        seen.add(cursor.pk)
        cursor = cursor.parent


def create_category(staff_user, *, name, parent=None, description='',
                    position=0, is_active=True):
    """Operations/administrator category create (audit-logged)."""
    category = Category.objects.create(
        name=name.strip(),
        parent=parent,
        description=description,
        position=position or 0,
        is_active=is_active,
    )
    log_event(
        staff_user,
        'category_created',
        category,
        detail={'name': category.name, 'parent_id': category.parent_id},
    )
    return category


def update_category(staff_user, category, *, changes):
    """Field edits incl. reparenting — cycle-checked (audit-logged)."""
    if 'parent' in changes:
        _validate_category_parent(category, changes['parent'])
    if 'name' in changes:
        changes['name'] = changes['name'].strip()

    for field, value in changes.items():
        setattr(category, field, value)
    category.save()
    log_event(
        staff_user,
        'category_updated',
        category,
        detail={'name': category.name, 'fields': sorted(changes.keys())},
    )
    return category


def delete_category(staff_user, category):
    """Refuses non-empty categories: children would cascade and products
    are PROTECTed — both must be moved first. The audit row is written
    before the delete so the object id still exists (§9 append-only trail).
    """
    if category.children.exists():
        raise ValueError('Move or delete the subcategories first.')
    if category.products.exists():
        raise ValueError('This category still has products — move them first.')

    with transaction.atomic():
        log_event(
            staff_user,
            'category_deleted',
            category,
            detail={'name': category.name, 'parent_id': category.parent_id},
        )
        category.delete()


def create_brand(staff_user, *, name):
    """Operations/administrator brand create (audit-logged)."""
    brand = Brand.objects.create(name=name.strip())
    log_event(staff_user, 'brand_created', brand, detail={'name': brand.name})
    return brand


def update_brand(staff_user, brand, *, name):
    brand.name = name.strip()
    brand.save()
    log_event(staff_user, 'brand_updated', brand, detail={'name': brand.name})
    return brand


def delete_brand(staff_user, brand):
    """Products detach (FK SET_NULL) — deletion only removes the label."""
    with transaction.atomic():
        log_event(staff_user, 'brand_deleted', brand, detail={'name': brand.name})
        brand.delete()


# --- Inventory (transaction-safe; every change appends a movement row) ---

def ensure_inventory(variant, *, initial_on_hand=0, actor=None, note=''):
    """Creates the inventory row for a variant (used at variant creation
    and by seed data). Writes the initial movement when stock > 0."""
    inventory, created = Inventory.objects.get_or_create(
        variant=variant,
        defaults={'on_hand': initial_on_hand},
    )
    if created and initial_on_hand > 0:
        StockMovement.objects.create(
            variant=variant,
            actor=actor,
            reason=StockMovement.Reason.INITIAL,
            quantity_delta=initial_on_hand,
            resulting_on_hand=initial_on_hand,
            note=note,
        )
    return inventory


def adjust_stock(actor, variant, *, delta, reason=StockMovement.Reason.ADJUSTMENT,
                 note=''):
    """Seller/staff stock change: +restock / −shrinkage. Row-locked,
    append-only movement, and the DB CHECK blocks negative availability
    (the guard below raises a clean error before the constraint does)."""
    if reason not in (
        StockMovement.Reason.ADJUSTMENT,
        StockMovement.Reason.RESTOCK,
    ):
        raise ValueError('Invalid adjustment reason.')
    if delta == 0:
        raise ValueError('Adjustment must be a non-zero quantity.')

    with transaction.atomic():
        inventory = Inventory.objects.select_for_update().get(variant=variant)
        new_on_hand = inventory.on_hand + delta
        if new_on_hand < 0 or inventory.reserved > new_on_hand:
            raise ValueError(
                'Stock cannot go below what is already reserved.'
            )
        inventory.on_hand = new_on_hand
        inventory.save(update_fields=['on_hand', 'updated_at'])
        StockMovement.objects.create(
            variant=variant,
            actor=actor,
            reason=reason,
            quantity_delta=delta,
            resulting_on_hand=new_on_hand,
            note=note,
        )
    return inventory


def update_variant(seller_user, product_id, variant_id, **fields):
    """Seller edits a variant's own fields (§12.2) — name/price/active/attrs.

    Stock never moves through here: on_hand changes go through adjust_stock
    so every movement stays in the append-only history (§12.3).
    """
    product = _get_owned_product(seller_user, product_id)
    if product.status == Product.Status.ARCHIVED:
        raise ValueError('Archived products cannot be edited.')
    variant = Variant.objects.get(pk=variant_id, product=product)
    editable = ('name', 'price', 'is_active', 'attributes')
    changed = [field for field in editable if field in fields]
    for field in changed:
        setattr(variant, field, fields[field])
    if changed:
        variant.save(update_fields=changed + ['updated_at'])
    return variant


def delete_variant(seller_user, product_id, variant_id):
    """Delete a never-ordered variant; deactivate one with order history.

    OrderItem.variant is PROTECT for the same reason as the product FK, so
    a variant that appears in a past order resolves to is_active=False
    instead of a hard delete. Returns (action, variant).
    """
    product = _get_owned_product(seller_user, product_id)
    if product.status == Product.Status.ARCHIVED:
        raise ValueError('Archived products cannot be edited.')
    variant = Variant.objects.get(pk=variant_id, product=product)
    if variant.order_items.exists():
        if variant.is_active:
            variant.is_active = False
            variant.save(update_fields=['is_active', 'updated_at'])
        return 'deactivated', variant
    variant.delete()
    return 'deleted', None


def set_low_stock_threshold(seller_user, variant, *, threshold):
    """Seller sets the low-stock alert level for their own variant (§12.3)."""
    if variant.product.store.user_id != seller_user.pk:
        raise PermissionError('You may only manage your own store inventory.')
    if threshold < 0:
        raise ValueError('Threshold cannot be negative.')
    inventory, _ = Inventory.objects.get_or_create(variant=variant)
    inventory.low_stock_threshold = threshold
    inventory.save(update_fields=['low_stock_threshold', 'updated_at'])
    return inventory


def reserve_stock(variant, quantity):
    """Order-time reservation (Phase 8 consumes this). Row-locked; raises
    ValueError when available stock is insufficient."""
    if quantity <= 0:
        raise ValueError('Reservation quantity must be positive.')
    with transaction.atomic():
        inventory = Inventory.objects.select_for_update().get(variant=variant)
        if inventory.available < quantity:
            raise ValueError('Insufficient stock.')
        inventory.reserved += quantity
        inventory.save(update_fields=['reserved', 'updated_at'])
        StockMovement.objects.create(
            variant=variant,
            reason=StockMovement.Reason.RESERVE,
            quantity_delta=0,
            resulting_on_hand=inventory.on_hand,
            note=f'reserved {quantity}',
        )
    return inventory


def release_stock(variant, quantity):
    """Cancelling a reservation (Phase 8 consumes this)."""
    if quantity <= 0:
        raise ValueError('Release quantity must be positive.')
    with transaction.atomic():
        inventory = Inventory.objects.select_for_update().get(variant=variant)
        inventory.reserved = max(0, inventory.reserved - quantity)
        inventory.save(update_fields=['reserved', 'updated_at'])
        StockMovement.objects.create(
            variant=variant,
            reason=StockMovement.Reason.RELEASE,
            quantity_delta=0,
            resulting_on_hand=inventory.on_hand,
            note=f'released {quantity}',
        )
    return inventory


def commit_sale(variant, quantity, *, actor=None, note=''):
    """A reservation converts to a sale: on_hand and reserved both drop
    (Phase 8 consumes this at payment confirmation)."""
    if quantity <= 0:
        raise ValueError('Sale quantity must be positive.')
    with transaction.atomic():
        inventory = Inventory.objects.select_for_update().get(variant=variant)
        new_on_hand = inventory.on_hand - quantity
        if new_on_hand < 0:
            raise ValueError('Stock cannot go negative.')
        inventory.on_hand = new_on_hand
        inventory.reserved = max(0, inventory.reserved - quantity)
        inventory.save(update_fields=['on_hand', 'reserved', 'updated_at'])
        StockMovement.objects.create(
            variant=variant,
            actor=actor,
            reason=StockMovement.Reason.SALE,
            quantity_delta=-quantity,
            resulting_on_hand=new_on_hand,
            note=note,
        )
    return inventory


# --- Image upload validation (C3: no Pillow — extension + size + magic) ---

ALLOWED_IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp'}


def validate_image_file(django_file):
    """Validates an uploaded product image server-side (§10.1):
    extension allowlist, 5 MB cap, and magic-byte sniffing."""
    from django.core.exceptions import ValidationError

    ext = os.path.splitext(django_file.name)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTS:
        raise ValidationError('Allowed image types: JPG, PNG, WebP.')
    django_file.seek(0, os.SEEK_END)
    size = django_file.tell()
    django_file.seek(0)
    if size > MAX_IMAGE_BYTES:
        raise ValidationError('Image must be 5 MB or smaller.')
    if size < 16:
        raise ValidationError('Image file is empty or corrupted.')
    header = django_file.read(16)
    django_file.seek(0)
    is_jpeg = header.startswith(b'\xff\xd8\xff')
    is_png = header.startswith(b'\x89PNG\r\n\x1a\n')
    is_webp = header.startswith(b'RIFF') and header[8:12] == b'WEBP'
    if not (is_jpeg or is_png or is_webp):
        raise ValidationError('File content is not a valid image.')
    return True
