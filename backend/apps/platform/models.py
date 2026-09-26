"""Platform settings model (Phase 13.6 — PROJECT_CONTEXT §6 v1.13).

One singleton row holds the marketplace's platform-wide configuration:
numbers and switches no single store owns. The row is pinned to pk=1 in
`save()` so a second row can never appear, and every bound that matters
carries a DB CheckConstraint — serializer validation is the API gate,
the constraints are the floor (§10).
"""
from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from apps.common.models import TimeStampedModel

MONEY_VALIDATOR = MinValueValidator(Decimal('0.00'))


class PlatformSettings(TimeStampedModel):
    """The marketplace's platform-wide configuration (singleton, §6 v1.13)."""

    SINGLETON_ID = 1

    # --- Marketplace -------------------------------------------------------
    platform_name = models.CharField(max_length=60, default='Jeyvro')
    support_email = models.EmailField(default='support@jeyvro.com')

    # --- Commission (§4: finance may adjust, administrator too) ------------
    commission_rate_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[
            MinValueValidator(Decimal('0.00')),
            MaxValueValidator(Decimal('100.00')),
        ],
        help_text='Platform commission taken from each sale (percent).',
    )

    # --- Shipping (seeds stores created after the change, §6 v1.7) ---------
    default_shipping_flat_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MONEY_VALIDATOR],
        help_text=(
            'Flat shipping fee a new store starts with (PHP); sellers may '
            'edit their own store afterwards.'
        ),
    )
    default_free_shipping_threshold = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MONEY_VALIDATOR],
        help_text=(
            'Free-shipping threshold a new store starts with; null means '
            'no threshold.'
        ),
    )

    # --- Feature switches ---------------------------------------------------
    cod_enabled = models.BooleanField(
        default=True,
        help_text='When off, checkout refuses Cash on Delivery entirely.',
    )
    payment_expiry_hours = models.PositiveSmallIntegerField(
        default=24,
        validators=[MinValueValidator(1), MaxValueValidator(168)],
        help_text='Hours an unpaid online payment may stay open (§6 v1.8).',
    )

    # --- Notification defaults for NEW accounts ----------------------------
    default_order_updates_email = models.BooleanField(default=True)
    default_promotions_email = models.BooleanField(default=False)
    default_messaging_email = models.BooleanField(default=True)

    updated_by = models.ForeignKey(
        'accounts.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='platform_settings_updates',
        help_text='Staff member who last changed these settings.',
    )

    class Meta:
        verbose_name = 'platform settings'
        verbose_name_plural = 'platform settings'
        constraints = [
            models.CheckConstraint(
                condition=Q(commission_rate_percent__gte=0)
                & Q(commission_rate_percent__lte=100),
                name='platform_commission_rate_bounds',
            ),
            models.CheckConstraint(
                condition=Q(default_shipping_flat_fee__gte=0),
                name='platform_shipping_fee_non_negative',
            ),
            models.CheckConstraint(
                condition=Q(default_free_shipping_threshold__isnull=True)
                | Q(default_free_shipping_threshold__gte=0),
                name='platform_free_threshold_non_negative',
            ),
            models.CheckConstraint(
                condition=Q(payment_expiry_hours__gte=1)
                & Q(payment_expiry_hours__lte=168),
                name='platform_payment_expiry_bounds',
            ),
        ]

    def save(self, *args, **kwargs):
        # The singleton guard: whatever happens, this row is pk 1.
        self.pk = self.SINGLETON_ID
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Platform settings ({self.platform_name})'
