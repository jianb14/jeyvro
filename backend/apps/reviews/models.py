"""Review domain models (Phase 14 — PROJECT_CONTEXT §6 v1.16).

One row per (user, product), backed by a DB unique constraint (§9). The
row is only ever created through `services.create_review`, which proves
the buyer owns a delivered/completed order line for the product — the
client never vouches for itself (§6, marketplace-community rule 1).

Review is PROTECT-linked to user, product, store and order: review
history is evidence of a real purchase and must never be orphaned by a
catalog or account deletion.
"""
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from apps.common.models import TimeStampedModel


class ReviewStatus(models.TextChoices):
    """Moderation state (§6 — reviews are moderateable).

    FLAGGED is set by the abuse foundation when enough distinct reporters
    flag a review; it drops the review off the public list until a
    moderator decides (restore → published, hide → hidden).
    """

    PUBLISHED = 'published', 'Published'
    FLAGGED = 'flagged', 'Flagged'
    HIDDEN = 'hidden', 'Hidden'


class Review(TimeStampedModel):
    """A verified buyer's review of one product."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='reviews',
        help_text='The verified buyer — PROTECT: review history is never orphaned.',
    )
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.PROTECT,
        related_name='reviews',
    )
    store = models.ForeignKey(
        'stores.Store',
        on_delete=models.PROTECT,
        related_name='reviews',
        help_text='Denormalized owning store — replies and store aggregates read it directly.',
    )
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.PROTECT,
        related_name='reviews',
        help_text='The purchase that proved eligibility (verified buyer, §6).',
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text='1–5 stars; the DB CheckConstraint is the floor.',
    )
    title = models.CharField(max_length=150, blank=True)
    body = models.TextField()

    # --- Moderation (staff only — sellers cannot touch this, §6) -----------
    status = models.CharField(
        max_length=16,
        choices=ReviewStatus.choices,
        default=ReviewStatus.PUBLISHED,
    )
    moderation_reason = models.CharField(max_length=255, blank=True)
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='moderated_reviews',
    )
    moderated_at = models.DateTimeField(null=True, blank=True)

    # --- Official store reply (seller of this review's store only) ---------
    seller_reply = models.TextField(blank=True)
    seller_replied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'product'],
                name='reviews_one_per_user_product',
            ),
            models.CheckConstraint(
                condition=Q(rating__gte=1) & Q(rating__lte=5),
                name='reviews_rating_bounds',
            ),
        ]
        indexes = [
            models.Index(fields=['product', 'status'], name='reviews_product_status_idx'),
            models.Index(fields=['store', 'status'], name='reviews_store_status_idx'),
            models.Index(fields=['status', 'created_at'], name='reviews_status_created_idx'),
            models.Index(fields=['user'], name='reviews_user_idx'),
        ]

    @property
    def is_visible(self):
        """Public visibility — only a fully published review shows."""
        return self.status == ReviewStatus.PUBLISHED

    def __str__(self):
        return f'{self.product_id} by user {self.user_id} ({self.rating}★, {self.status})'



class ReviewImage(TimeStampedModel):
    """A photo attached to a review (14.1 image attachments).

    URL-based for now, mirroring the store logo/banner seam — file
    uploads for reviews land with the deferred media phase.
    """

    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name='images',
    )
    image_url = models.URLField(help_text='Hosted review photo URL.')
    caption = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'Photo of review {self.review_id}'


class ReviewReport(TimeStampedModel):
    """Customer abuse report against a review (14.3 abuse foundation)."""

    class Reason(models.TextChoices):
        SPAM = 'spam', 'Spam'
        ABUSIVE = 'abusive', 'Abusive or harassing'
        IRRELEVANT = 'irrelevant', 'Not about this product'
        OTHER = 'other', 'Other'

    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name='reports',
    )
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='review_reports',
    )
    reason = models.CharField(max_length=16, choices=Reason.choices)
    notes = models.TextField(blank=True)
    resolved = models.BooleanField(
        default=False,
        help_text='Staff marks a report resolved once moderated.',
    )

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['review', 'reporter'],
                name='reviews_one_report_per_user',
            ),
        ]
        indexes = [
            models.Index(fields=['review'], name='reviews_report_review_idx'),
            models.Index(fields=['resolved'], name='reviews_report_resolved_idx'),
        ]

    def __str__(self):
        return f'{self.reason} → review {self.review_id}'
