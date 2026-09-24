"""Store domain models (Phase 4 — PROJECT_CONTEXT §6 v1.2).

A seller IS a user with a store (§4) — one user owns exactly one store;
there is no parallel seller-account model. Store media is URL-based for
now, consistent with `accounts.User.avatar_url`; validated file upload
arrives with the media phase (CONVENTIONS.md — Media).
"""
from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel
from apps.common.utils import slugify_unique
from apps.common.utils import slugify_unique


class Store(TimeStampedModel):
    """One seller's storefront. Lifecycle: pending → active → suspended.

    Transitions happen only in services (CONVENTIONS.md — Status fields);
    staff-only flips are audit-logged (§9). Sellers never self-approve.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACTIVE = 'active', 'Active'
        SUSPENDED = 'suspended', 'Suspended'

    user = models.OneToOneField(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='store',
        help_text='The seller who owns this store — exactly one per user (§6 v1.2).',
    )
    name = models.CharField(max_length=128)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField(blank=True)
    logo_url = models.URLField(blank=True)
    banner_url = models.URLField(blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=32, blank=True)
    return_policy = models.TextField(blank=True)
    shipping_policy = models.TextField(blank=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    suspended_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['slug'], name='stores_slug_idx'),
            models.Index(fields=['status'], name='stores_status_idx'),
            models.Index(fields=['user'], name='stores_user_idx'),
            models.Index(fields=['created_at'], name='stores_created_idx'),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify_unique(Store, self.name, exclude_pk=self.pk)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name} ({self.status})'


class SellerApplication(TimeStampedModel):
    """A customer's application to become a seller (Phase 4.1).

    Review state is mirrored onto Store.status by the moderation service —
    the store is the live object; this is its application record.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='seller_applications',
    )
    store = models.OneToOneField(
        'stores.Store',
        on_delete=models.CASCADE,
        related_name='application',
    )
    store_name = models.CharField(max_length=128)
    store_description = models.TextField(blank=True)
    contact_phone = models.CharField(max_length=32, blank=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    rejection_reason = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='reviewed_seller_applications',
        blank=True,
        null=True,
    )
    reviewed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status'], name='stores_app_status_idx'),
            models.Index(fields=['user'], name='stores_app_user_idx'),
        ]

    def __str__(self):
        return f'{self.store_name} — {self.status}'