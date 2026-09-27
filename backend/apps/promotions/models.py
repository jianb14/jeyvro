"""Promotions & voucher domain models (Phase 16 — ROADMAP §16.1).

Vouchers are server-verified discount definitions. Every rule that decides
whether a code applies — scope, window, spend floor, usage counters, product
or category targeting — lives in `services` and is evaluated against live
server truth, never the client (§6/§10.1: the client never calculates).

`VoucherUsage` is the append-only redemption ledger: one row per voucher per
order, written under a row lock inside the checkout transaction, so totals
and counters can never diverge (§16 Gate — usage is race-condition safe and
every discount is auditable).
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
