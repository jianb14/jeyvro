"""Promotions & voucher domain models (Phase 16 — ROADMAP §16.1 & §16.2).

Vouchers are server-verified discount definitions. Every rule that decides
whether a code applies — scope, window, spend floor, usage counters, product
or category targeting — lives in `services` and is evaluated against live
server truth, never the client (§6/§10.1: the client never calculates).

`VoucherUsage` is the append-only redemption ledger: one row per voucher per
order, written under a row lock inside the checkout transaction, so totals
and counters can never diverge (§16 Gate — usage is race-condition safe and
every discount is auditable).

Section 16.2 adds the automatic promotion engine: a `Campaign` is the
container (scope + window) and each `Promotion` inside it is one rule —
product discount, flash sale, free shipping, bundle, or buy-X-get-Y. They
need no code: the engine applies them to live lines at cart read, checkout
preview, voucher evaluation, and order creation, and `PromotionUsage` is the
append-only ledger that makes every applied discount auditable.
"""
from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class VoucherScope(models.TextChoices):
    """Who issues the voucher: the platform or one store (§16.1)."""

    PLATFORM = 'platform', 'Platform'
    SELLER = 'seller', 'Seller'


class VoucherDiscountType(models.TextChoices):
    PERCENTAGE = 'percentage', 'Percentage'
    FIXED = 'fixed', 'Fixed amount'


class VoucherFunding(models.TextChoices):
    """Who pays for the discount (§16.3) — recorded now, settled later."""

    PLATFORM = 'platform', 'Platform-funded'
    SELLER = 'seller', 'Seller-funded'
    SHARED = 'shared', 'Shared'


class Voucher(TimeStampedModel):
    """One redeemable code (§16.1): platform/seller × percentage/fixed.

    Seller vouchers MUST carry a store and platform vouchers MUST NOT (DB
    CheckConstraint); targeting rows (`VoucherEligibility`) narrow a voucher
    to specific products or categories — no rows means "everything in scope".
    Counters (`usage_limit`, `per_user_limit`) are enforced against the
    `VoucherUsage` ledger, under a row lock, inside the checkout transaction.
    """

    scope = models.CharField(
        max_length=16, choices=VoucherScope.choices, default=VoucherScope.PLATFORM
    )
    store = models.ForeignKey(
        'stores.Store',
        on_delete=models.CASCADE,
        related_name='vouchers',
        blank=True,
        null=True,
        help_text='Required for seller vouchers; null for platform vouchers.',
    )
    code = models.CharField(
        max_length=32,
        unique=True,
        help_text='Customer-facing code, stored uppercase (services normalize).',
    )
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)

    discount_type = models.CharField(
        max_length=16, choices=VoucherDiscountType.choices
    )
    value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text='Percent (0–100) for percentage vouchers; PHP amount for fixed.',
    )
    min_spend = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00')
    )
    max_discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Optional cap for percentage vouchers (maximum discount).',
    )

    usage_limit = models.PositiveIntegerField(
        blank=True, null=True, help_text='Total redemptions allowed; null = unlimited.'
    )
    per_user_limit = models.PositiveIntegerField(
        blank=True,
        null=True,
        default=1,
        help_text='Redemptions per customer; null = unlimited.',
    )
    first_order_only = models.BooleanField(
        default=False, help_text='Only customers with no prior orders may redeem.'
    )

    starts_at = models.DateTimeField(blank=True, null=True)
    ends_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    funded_by = models.CharField(
        max_length=16, choices=VoucherFunding.choices, default=VoucherFunding.PLATFORM
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='created_vouchers',
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['scope'], name='promo_voucher_scope_idx'),
            models.Index(fields=['is_active'], name='promo_voucher_active_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(value__gt=0), name='voucher_value_positive'
            ),
            models.CheckConstraint(
                condition=models.Q(min_spend__gte=0),
                name='voucher_min_spend_non_negative',
            ),
            models.CheckConstraint(
                condition=models.Q(discount_type='fixed') | models.Q(value__lte=100),
                name='voucher_percentage_within_100',
            ),
            models.CheckConstraint(
                condition=models.Q(max_discount__isnull=True)
                | models.Q(max_discount__gte=0),
                name='voucher_max_discount_non_negative',
            ),
            models.CheckConstraint(
                condition=models.Q(usage_limit__isnull=True) | models.Q(usage_limit__gte=1),
                name='voucher_usage_limit_positive',
            ),
            models.CheckConstraint(
                condition=models.Q(per_user_limit__isnull=True)
                | models.Q(per_user_limit__gte=1),
                name='voucher_per_user_limit_positive',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(starts_at__isnull=True)
                    | models.Q(ends_at__isnull=True)
                    | models.Q(ends_at__gt=models.F('starts_at'))
                ),
                name='voucher_window_ordered',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(scope='seller', store__isnull=False)
                    | models.Q(scope='platform', store__isnull=True)
                ),
                name='voucher_scope_matches_store',
            ),
        ]

    def save(self, *args, **kwargs):
        """Codes are case-insensitive customer input — always stored uppercase."""
        self.code = (self.code or '').strip().upper()
        super().save(*args, **kwargs)

    @property
    def is_percentage(self):
        return self.discount_type == VoucherDiscountType.PERCENTAGE

    def __str__(self):
        return f'{self.code} ({self.get_scope_display()})'


class VoucherEligibility(TimeStampedModel):
    """Targeting row — narrows a voucher to a product or a category (§16.1).

    A voucher with no rows applies to everything in its scope (the whole
    cart for platform vouchers, that store's lines for seller vouchers);
    every row must name exactly one target, and a target repeats never.
    """

    voucher = models.ForeignKey(
        Voucher, on_delete=models.CASCADE, related_name='eligibility_rules'
    )
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.CASCADE,
        related_name='voucher_eligibility',
        blank=True,
        null=True,
    )
    category = models.ForeignKey(
        'catalog.Category',
        on_delete=models.CASCADE,
        related_name='voucher_eligibility',
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ['id']
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(product__isnull=True, category__isnull=True),
                name='voucher_eligibility_requires_target',
            ),
            models.UniqueConstraint(
                fields=['voucher', 'product'],
                condition=models.Q(product__isnull=False),
                name='voucher_eligibility_unique_product',
            ),
            models.UniqueConstraint(
                fields=['voucher', 'category'],
                condition=models.Q(category__isnull=False),
                name='voucher_eligibility_unique_category',
            ),
        ]

    def __str__(self):
        target = (
            f'product {self.product_id}'
            if self.product_id
            else f'category {self.category_id}'
        )
        return f'{self.voucher.code} → {target}'


class VoucherUsage(TimeStampedModel):
    """Append-only redemption ledger (§16.1) — the counter the limits trust."""

    voucher = models.ForeignKey(
        Voucher, on_delete=models.PROTECT, related_name='usages'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='voucher_usages',
    )
    order = models.ForeignKey(
        'orders.Order', on_delete=models.CASCADE, related_name='voucher_usages'
    )
    store = models.ForeignKey(
        'stores.Store',
        on_delete=models.SET_NULL,
        related_name='voucher_usages',
        blank=True,
        null=True,
        help_text='The funding store for seller vouchers; null for platform vouchers.',
    )
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['voucher', 'user'], name='promo_usage_voucher_user_idx'),
            models.Index(fields=['order'], name='promo_usage_order_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(discount_amount__gt=0),
                name='voucher_usage_discount_positive',
            ),
            models.UniqueConstraint(
                fields=['voucher', 'order'], name='voucher_one_usage_per_order'
            ),
        ]

    def __str__(self):
        return f'{self.voucher.code} on {self.order.number} (-{self.discount_amount})'


# --- Phase 16.2: automatic promotions (campaigns) ----------------------------


class PromotionScope(models.TextChoices):
    """Who runs the campaign: the platform or one store (§16.2)."""

    PLATFORM = 'platform', 'Platform'
    SELLER = 'seller', 'Seller'


class PromotionKind(models.TextChoices):
    """The five automatic promotion rules §16.2 ships.

    PRODUCT_DISCOUNT / FLASH_SALE share one line-discount engine (the flash
    difference is the label and the tight window). FREE_SHIPPING waives the
    store's flat fee. BUNDLE needs a quantity floor. BUY_X_GET_Y is the
    cross-product rule — buy N of one product, get M units of another at
    `value`% off.
    """

    PRODUCT_DISCOUNT = 'product_discount', 'Product discount'
    FLASH_SALE = 'flash_sale', 'Flash sale'
    FREE_SHIPPING = 'free_shipping', 'Free shipping'
    BUNDLE = 'bundle', 'Bundle discount'
    BUY_X_GET_Y = 'buy_x_get_y', 'Buy X get Y'


class Campaign(TimeStampedModel):
    """One promotion container (§16.2): scope + window, no money rules itself.

    A campaign belongs to the platform (store null) or exactly one store
    (DB CheckConstraint, same shape as `Voucher`). Each `Promotion` row inside
    it carries one rule; the campaign's `is_active` flag and window switch the
    whole group on and off.
    """

    scope = models.CharField(
        max_length=16, choices=PromotionScope.choices, default=PromotionScope.PLATFORM
    )
    store = models.ForeignKey(
        'stores.Store',
        on_delete=models.CASCADE,
        related_name='campaigns',
        blank=True,
        null=True,
        help_text='Required for seller campaigns; null for platform campaigns.',
    )
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    starts_at = models.DateTimeField(blank=True, null=True)
    ends_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-id']
        constraints = [
            models.CheckConstraint(
                condition=~(
                    models.Q(scope='seller', store__isnull=True)
                    | models.Q(scope='platform', store__isnull=False)
                ),
                name='campaign_scope_store_required',
            ),
        ]

    def __str__(self):
        return f'{self.name} ({self.get_scope_display()})'


class Promotion(TimeStampedModel):
    """One automatic rule inside a campaign (§16.2) — never redeemed by code.

    Money fields mirror the voucher vocabulary: `discount_type` + `value`
    (percent or PHP) with a `min_spend` floor; `min_qty` adds the bundle
    quantity floor; the buy/get fields carry the BXGY pair and must be either
    all set (kind=buy_x_get_y) or all empty (every other kind) — enforced by
    DB CheckConstraints. `label` is the customer-facing badge text the UI
    renders; targeting lives in `PromotionTarget` (no rows = everything in
    the campaign's scope).
    """

    campaign = models.ForeignKey(
        Campaign, on_delete=models.CASCADE, related_name='promotions'
    )
    kind = models.CharField(max_length=24, choices=PromotionKind.choices)
    label = models.CharField(
        max_length=120, help_text='Customer-facing badge text (e.g. "20% off").'
    )

    discount_type = models.CharField(
        max_length=16,
        choices=VoucherDiscountType.choices,
        default=VoucherDiscountType.PERCENTAGE,
    )
    value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Percent (0–100) or PHP amount; ignored for free shipping.',
    )
    min_spend = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00')
    )
    min_qty = models.PositiveIntegerField(
        default=1,
        help_text='Bundle floor: total eligible units in the store required (≥2).',
    )

    buy_product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.CASCADE,
        related_name='buy_x_get_y_promotions',
        blank=True,
        null=True,
    )
    buy_qty = models.PositiveIntegerField(blank=True, null=True)
    get_product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.CASCADE,
        related_name='get_promotions',
        blank=True,
        null=True,
    )
    get_qty = models.PositiveIntegerField(blank=True, null=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['id']
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        kind='buy_x_get_y',
                        buy_product__isnull=False,
                        buy_qty__isnull=False,
                        get_product__isnull=False,
                        get_qty__isnull=False,
                    )
                    | (
                        ~models.Q(kind='buy_x_get_y')
                        & models.Q(
                            buy_product__isnull=True,
                            buy_qty__isnull=True,
                            get_product__isnull=True,
                            get_qty__isnull=True,
                        )
                    )
                ),
                name='promotion_kind_requires_bxgy_products',
            ),
            models.CheckConstraint(
                condition=models.Q(buy_qty__isnull=True, get_qty__isnull=True)
                | models.Q(buy_qty__gte=1, get_qty__gte=1),
                name='promotion_bxgy_qty_positive',
            ),
            models.CheckConstraint(
                condition=models.Q(kind='free_shipping') | models.Q(value__gt=0),
                name='promotion_value_positive',
            ),
            models.CheckConstraint(
                condition=models.Q(kind='free_shipping')
                | ~models.Q(discount_type='percentage')
                | models.Q(value__lte=100),
                name='promotion_percentage_bounded',
            ),
            models.CheckConstraint(
                condition=~models.Q(kind='buy_x_get_y')
                | models.Q(discount_type='percentage'),
                name='promotion_bxgy_percentage_only',
            ),
            models.CheckConstraint(
                condition=~models.Q(kind='bundle') | models.Q(min_qty__gte=2),
                name='promotion_bundle_min_qty',
            ),
            models.CheckConstraint(
                condition=models.Q(min_spend__gte=0),
                name='promotion_min_spend_non_negative',
            ),
        ]

    def __str__(self):
        return f'{self.label} ({self.get_kind_display()})'


class PromotionTarget(TimeStampedModel):
    """Targeting row — narrows a promotion to a product or a category (§16.2).

    Same contract as `VoucherEligibility`: no rows means "everything in the
    campaign's scope", every row names exactly one target, and a target
    repeats never. Free-shipping and BXGY rules ignore these rows (their
    targets are the whole store or the buy/get pair).
    """

    promotion = models.ForeignKey(
        Promotion, on_delete=models.CASCADE, related_name='target_rules'
    )
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.CASCADE,
        related_name='promotion_targets',
        blank=True,
        null=True,
    )
    category = models.ForeignKey(
        'catalog.Category',
        on_delete=models.CASCADE,
        related_name='promotion_targets',
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ['id']
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(product__isnull=True, category__isnull=True),
                name='promotion_target_requires_target',
            ),
            models.UniqueConstraint(
                fields=['promotion', 'product'],
                condition=models.Q(product__isnull=False),
                name='promotion_target_unique_product',
            ),
            models.UniqueConstraint(
                fields=['promotion', 'category'],
                condition=models.Q(category__isnull=False),
                name='promotion_target_unique_category',
            ),
        ]

    def __str__(self):
        target = (
            f'product {self.product_id}'
            if self.product_id
            else f'category {self.category_id}'
        )
        return f'{self.promotion_id} → {target}'


class PromotionUsage(TimeStampedModel):
    """Append-only application ledger (§16.2) — what the audit trusts.

    One row per promotion per store per order, written inside the checkout
    transaction next to the voucher ledger. `discount_amount` records the
    value handed over: the summed line discounts, or the waived flat fee for
    free-shipping rules. Promotions carry no counters today (windowed price
    rules cannot race), so this row is pure audit — §16 Gate: every discount
    calculation is auditable.
    """

    promotion = models.ForeignKey(
        Promotion, on_delete=models.PROTECT, related_name='usages'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='promotion_usages',
    )
    order = models.ForeignKey(
        'orders.Order', on_delete=models.CASCADE, related_name='promotion_usages'
    )
    store = models.ForeignKey(
        'stores.Store',
        on_delete=models.PROTECT,
        related_name='promotion_usages',
        help_text='The store whose lines (or shipping) the discount hit.',
    )
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['promotion', 'user'], name='promo_rule_usage_idx'),
            models.Index(fields=['order'], name='promo_rule_order_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(discount_amount__gt=0),
                name='promotion_usage_discount_positive',
            ),
            models.UniqueConstraint(
                fields=['promotion', 'order', 'store'],
                name='promotion_usage_once_per_store',
            ),
        ]

    def __str__(self):
        return f'{self.promotion_id} on {self.order.number} (-{self.discount_amount})'
