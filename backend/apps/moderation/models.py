"""Automatic content flags (Phase 20.2 slice v1 — ROADMAP §20.2).

One row per piece of customer- or seller-authored content that tripped an
automatic rule. The row is the *evidence* an over-broad rule produced: the
content itself is never edited, never censored and never silently rewritten —
it is taken out of the public list and handed to a human (`apps.moderation
.views`) who decides. That is the same contract §14.3 set for customer abuse
reports, extended from "people complained" to "the rules noticed".

Deliberately **not** here: a profanity or slur list. Content moderation
blocklists tuned on one language flag ordinary Filipino/Tagalog prose, and a
marketplace that mutes its own customers' accents is a worse product than one
that shows a moderator a few extra rows. The documented rules are structural
(properties of the text) rather than lexical (which words it used).
"""
from django.conf import settings
from django.core.validators import MinLengthValidator
from django.db import models
from django.db.models import Q

from apps.common.models import TimeStampedModel


class ContentFlag(TimeStampedModel):
    """An automatic-rule hit waiting for a staff decision (§20.2)."""

    class Kind(models.TextChoices):
        REVIEW = 'review', 'Review'
        CONVERSATION = 'conversation', 'Conversation'

    class Rule(models.TextChoices):
        LINK = 'link', 'Contains a link'
        CONTACT = 'contact', 'Contains contact details'
        SHOUTING = 'shouting', 'Excessive capital letters'

    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        DISMISSED = 'dismissed', 'Dismissed — content was fine'
        CONFIRMED = 'confirmed', 'Confirmed — content was abuse'

    kind = models.CharField(max_length=16, choices=Kind.choices, db_index=True)

    rules = models.JSONField(
        default=list,
        help_text='Every rule code that fired, so one row can carry a double hit.',
    )

    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )

    # Exactly one subject per row — enforced by the DB, not by convention.
    review = models.ForeignKey(
        'reviews.Review',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='content_flags',
    )
    conversation = models.ForeignKey(
        'messaging.Conversation',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='content_flags',
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='content_flags_authored',
        help_text='Who wrote the flagged text — the person staff may act against.',
    )

    # No excerpt of the text is copied here on purpose. Staff read the linked
    # review/conversation itself; duplicating a body that may hold someone's
    # email or phone number would create a second copy of their PII to redact,
    # retain and eventually leak (§10.1 — one copy, not two).
    rule_detail = models.CharField(max_length=255, blank=True, default='')

    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='content_flags_resolved',
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.CharField(
        max_length=255,
        blank=True,
        default='',
        validators=[MinLengthValidator(0)],
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'content flags'
        constraints = [
            # A flag points at exactly one subject, never zero and never two.
            models.CheckConstraint(
                condition=(
                    Q(review__isnull=False, conversation__isnull=True)
                    | Q(review__isnull=True, conversation__isnull=False)
                ),
                name='moderation_flag_exactly_one_subject',
            ),
            # One live flag per subject: a user editing their own review twice
            # must not manufacture a queue of duplicate rows for staff to
            # re-triage. Re-flagging reopens the same row.
            models.UniqueConstraint(
                fields=['review'],
                condition=Q(review__isnull=False),
                name='moderation_one_flag_per_review',
            ),
            models.UniqueConstraint(
                fields=['conversation'],
                condition=Q(conversation__isnull=False),
                name='moderation_one_flag_per_conversation',
            ),
        ]
        indexes = [
            models.Index(fields=['status', '-created_at'], name='moderation_status_idx'),
            models.Index(fields=['kind', 'status'], name='moderation_kind_status_idx'),
            models.Index(fields=['author', '-created_at'], name='moderation_author_idx'),
        ]

    def __str__(self):
        subject = f'review={self.review_id}' if self.review_id else f'conversation={self.conversation_id}'
        return f'ContentFlag({self.pk}, {self.kind}, {subject}, {self.status})'
