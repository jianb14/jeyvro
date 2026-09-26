"""JEYVRO identity models.

A seller IS a user with a store (PROJECT_CONTEXT §4/backend-core rule 1) —
never a parallel "seller account". Role foundations are flags on the user;
stores arrive in Phase 4. Group-based staff permissions land via data
migration (support / moderator / administrator).
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel

from .managers import UserManager


class User(AbstractUser, TimeStampedModel):
    """Email-as-username user with seller/staff role foundations.

    Inherits TimeStampedModel (created_at/updated_at) via apps.common.
    """

    class AccountStatus(models.TextChoices):
        ACTIVE = 'active', 'Active'
        SUSPENDED = 'suspended', 'Suspended'

    username = None  # email is the identifier — usernames are not used
    email = models.EmailField('email address', unique=True)
    phone = models.CharField(max_length=32, blank=True)
    avatar_url = models.URLField(
        blank=True,
        help_text='URL-based for now; validated file upload arrives with the media phase (12).',
    )
    is_seller = models.BooleanField(
        default=False,
        help_text='Set true when the user owns a store (Phase 4).',
    )
    email_verified = models.BooleanField(default=False)
    account_status = models.CharField(
        max_length=16,
        choices=AccountStatus.choices,
        default=AccountStatus.ACTIVE,
    )
    suspended_at = models.DateTimeField(blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        indexes = [
            models.Index(fields=['email'], name='accounts_email_idx'),
            models.Index(fields=['is_seller'], name='accounts_is_seller_idx'),
            models.Index(fields=['created_at'], name='accounts_created_idx'),
        ]

    @property
    def is_login_allowed(self):
        """Login gate: active flag AND active status (§4 — role checks are
        enforced server-side on every request, never by the UI alone)."""
        return self.is_active and self.account_status == self.AccountStatus.ACTIVE

    def suspend(self):
        """Suspend the account AND revoke its live sessions.

        `is_active=False` matters: Django's session auth re-loads the user on
        every request through the auth backend, which refuses inactive users —
        so an already-signed-in (or stolen) session dies immediately instead of
        surviving until its next login (§4 v1.10).
        """
        self.account_status = self.AccountStatus.SUSPENDED
        self.suspended_at = timezone.now()
        self.is_active = False
        self.save(update_fields=[
            'account_status', 'suspended_at', 'is_active', 'updated_at',
        ])

    def reactivate(self):
        self.account_status = self.AccountStatus.ACTIVE
        self.suspended_at = None
        self.is_active = True
        self.save(update_fields=[
            'account_status', 'suspended_at', 'is_active', 'updated_at',
        ])

    def __str__(self):
        return self.email


class Address(TimeStampedModel):
    """Customer address book foundation (Phase 3.4)."""

    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='addresses',
    )
    label = models.CharField(max_length=64, blank=True)
    full_name = models.CharField(max_length=128)
    phone = models.CharField(max_length=32)
    line1 = models.CharField(max_length=256)
    line2 = models.CharField(max_length=256, blank=True)
    city = models.CharField(max_length=128)
    province = models.CharField(max_length=128)
    postal_code = models.CharField(max_length=16)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user'], name='accounts_addr_user_idx'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                condition=models.Q(is_default=True),
                name='accounts_one_default_address_per_user',
            ),
        ]

    def save(self, *args, **kwargs):
        # Enforce single default per user at the service boundary too.
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).exclude(
                pk=self.pk
            ).update(is_default=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.full_name} — {self.city}'


class NotificationPreference(TimeStampedModel):
    """Customer notification preferences foundation (Phase 3.4).

    One row per user; email digests ship later (§17 — Celery).
    """

    user = models.OneToOneField(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='notification_preferences',
    )
    order_updates_email = models.BooleanField(default=True)
    promotions_email = models.BooleanField(default=False)
    messaging_email = models.BooleanField(default=True)

    def __str__(self):
        return f'Preferences for {self.user.email}'
