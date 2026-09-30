"""Messaging domain models (Phase 15 — ROADMAP §15.1, §12.6, PROJECT_CONTEXT §6).

Conversations are participant-scoped (customer ↔ store seller, or customer ↔ support).
Each conversation may carry order context (Order) and/or product context (Product).
Moderation access is group-scoped (moderator, administrator, support) and auditable.
"""
from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class ConversationType(models.TextChoices):
    SELLER = 'seller', 'Seller'
    SUPPORT = 'support', 'Support'


class ConversationStatus(models.TextChoices):
    OPEN = 'open', 'Open'
    CLOSED = 'closed', 'Closed'
    REPORTED = 'reported', 'Reported'


class Conversation(TimeStampedModel):
    """A buyer ↔ seller or buyer ↔ support message thread."""

    type = models.CharField(
        max_length=16,
        choices=ConversationType.choices,
        default=ConversationType.SELLER,
        db_index=True,
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='customer_conversations',
        help_text='The customer participating in the conversation.',
    )
    store = models.ForeignKey(
        'stores.Store',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conversations',
        help_text='The store involved (null for customer-support conversations).',
    )
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conversations',
        help_text='Optional order context.',
    )
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conversations',
        help_text='Optional product context.',
    )
    subject = models.CharField(max_length=200, blank=True, default='')
    status = models.CharField(
        max_length=16,
        choices=ConversationStatus.choices,
        default=ConversationStatus.OPEN,
        db_index=True,
    )
    customer_last_read_at = models.DateTimeField(null=True, blank=True)
    seller_last_read_at = models.DateTimeField(null=True, blank=True)
    support_last_read_at = models.DateTimeField(null=True, blank=True)
    is_muted_by_customer = models.BooleanField(default=False)
    is_muted_by_seller = models.BooleanField(default=False)

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['customer', '-updated_at']),
            models.Index(fields=['store', '-updated_at']),
            models.Index(fields=['type', 'status']),
        ]

    def __str__(self):
        return f'Conversation({self.pk}, {self.type}, customer={self.customer_id}, store={self.store_id})'


class Message(TimeStampedModel):
    """An individual message within a conversation."""

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='sent_messages',
    )
    body = models.TextField()
    attachment_url = models.URLField(blank=True, default='', max_length=500)
    is_system = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
        ]

    def __str__(self):
        return f'Message({self.pk}, conversation={self.conversation_id}, sender={self.sender_id})'


class ConversationReport(TimeStampedModel):
    """A user report flagging a conversation for moderation review (§15.1)."""

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='reports',
    )
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='conversation_reports',
    )
    reason = models.CharField(max_length=64)
    details = models.TextField(blank=True, default='')
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='resolved_conversation_reports',
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['conversation', '-created_at']),
        ]

    def __str__(self):
        return f'ConversationReport({self.conversation_id}, reporter={self.reporter_id}, reason={self.reason})'


class ConversationBlock(TimeStampedModel):
    """One user refusing further contact from another (§20.2 messaging abuse).

    A block is user-scoped, not conversation-scoped on purpose: a buyer who
    blocks a seller is refusing that *person*, and must not be able to open a
    fresh thread on a different product to escape the block. `store` is kept
    as context for the seller console; the block itself resolves through
    `blocked`, so it still holds if the seller later renames or the store is
    deleted.
    """

    blocker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversation_blocks_made',
    )
    blocked = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversation_blocks_received',
        help_text='The party being blocked — the store owner, not the store.',
    )
    store = models.ForeignKey(
        'stores.Store',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='blocked_conversations',
        help_text='Store context when the blocked party is a seller.',
    )
    reason = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'conversation blocks'
        constraints = [
            models.UniqueConstraint(
                fields=['blocker', 'blocked'],
                name='messaging_one_block_per_pair',
            ),
            models.CheckConstraint(
                condition=~models.Q(blocker=models.F('blocked')),
                name='messaging_no_self_block',
            ),
        ]
        indexes = [
            models.Index(fields=['blocker', '-created_at'], name='messaging_blocker_idx'),
            models.Index(fields=['blocked'], name='messaging_blocked_idx'),
        ]

    def __str__(self):
        return f'ConversationBlock({self.blocker_id} -> {self.blocked_id})'

