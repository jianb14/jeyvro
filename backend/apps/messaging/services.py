"""Messaging services (Phase 15 — ROADMAP §15.1, §12.6, §15.3).

All messaging logic:
- Participant checks (customer, store owner, or staff).
- Auto-updating `updated_at` and `last_read_at`.
- Unread badge calculations for both buyer and seller.
- Generating in-app notifications on receiving a new message.
- Reporting conversations and moderation workflow.
"""
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from apps.audit.services import log_event
from apps.notifications.services import create_notification
from apps.notifications.models import NotificationCategory
from .models import (
    Conversation,
    ConversationReport,
    ConversationStatus,
    ConversationType,
    Message,
)


def can_access_conversation(conversation: Conversation, user) -> bool:
    """Check if user is allowed to read this conversation."""
    if not user or not user.is_authenticated:
        return False
    if user.is_staff and (
        user.is_superuser or user.groups.filter(name__in=['support', 'administrator', 'moderator']).exists()
    ):
        return True
    if conversation.customer_id == user.id:
        return True
    if conversation.store and conversation.store.user_id == user.id:
        return True
    return False

@transaction.atomic
def start_or_get_conversation(
    user,
    *,
    store=None,
    order=None,
    product=None,
    conversation_type: str = ConversationType.SELLER,
    subject: str = '',
    initial_message: str = '',
) -> tuple[Conversation, bool]:
    """Start a new conversation or reuse an existing matching open one."""
    if conversation_type == ConversationType.SELLER:
        if not store:
            raise ValidationError('A store is required for seller conversations.')
        if store.user_id == user.id:
            raise ValidationError('Sellers cannot start conversations with their own store.')

        existing = Conversation.objects.filter(
            customer=user,
            store=store,
            type=ConversationType.SELLER,
            status=ConversationStatus.OPEN,
            order=order,
            product=product,
        ).first()

        if existing:
            if initial_message:
                send_message(existing, user, initial_message)
            return existing, False

    elif conversation_type == ConversationType.SUPPORT:
        existing = Conversation.objects.filter(
            customer=user,
            type=ConversationType.SUPPORT,
            status=ConversationStatus.OPEN,
            order=order,
        ).first()

        if existing:
            if initial_message:
                send_message(existing, user, initial_message)
            return existing, False

    now = timezone.now()
    default_subj = f'Inquiry: {product.title}' if product else (f'Order #{order.order_number}' if order else 'Inquiry')
    conversation = Conversation.objects.create(
        customer=user,
        store=store,
        order=order,
        product=product,
        type=conversation_type,
        subject=subject or default_subj,
        customer_last_read_at=now,
    )

    if initial_message:
        send_message(conversation, user, initial_message)

    return conversation, True



@transaction.atomic
def send_message(
    conversation: Conversation,
    sender,
    body: str,
    attachment_url: str = '',
    is_system: bool = False,
) -> Message:
    """Send a message within an existing conversation and notify the recipient."""
    if not is_system and not can_access_conversation(conversation, sender):
        raise PermissionDenied('You do not have permission to post to this conversation.')

    if conversation.status == ConversationStatus.CLOSED and not sender.is_staff:
        raise ValidationError('This conversation is closed.')

    body_clean = body.strip()
    if not body_clean and not attachment_url:
        raise ValidationError('Message body or attachment is required.')

    now = timezone.now()
    message = Message.objects.create(
        conversation=conversation,
        sender=sender,
        body=body_clean,
        attachment_url=attachment_url,
        is_system=is_system,
    )

    update_fields = ['updated_at']
    conversation.updated_at = now
    if sender.id == conversation.customer_id:
        conversation.customer_last_read_at = now
        update_fields.append('customer_last_read_at')
    elif conversation.store and sender.id == conversation.store.user_id:
        conversation.seller_last_read_at = now
        update_fields.append('seller_last_read_at')
    elif sender.is_staff:
        conversation.support_last_read_at = now
        update_fields.append('support_last_read_at')

    conversation.save(update_fields=update_fields)

    # Notify recipient(s) in-app (§15.3)
    if not is_system:
        sender_name = sender.first_name or sender.email
        if sender.id == conversation.customer_id:
            if conversation.store and not conversation.is_muted_by_seller:
                create_notification(
                    recipient=conversation.store.user,
                    category=NotificationCategory.MESSAGING,
                    title=f'New message from {sender_name}',
                    message=body_clean[:120] if body_clean else 'Sent an attachment.',
                    action_url=f'/seller/messages?id={conversation.id}',
                )
        else:
            if not conversation.is_muted_by_customer:
                create_notification(
                    recipient=conversation.customer,
                    category=NotificationCategory.MESSAGING,
                    title=f'New message regarding {conversation.subject or "your inquiry"}',
                    message=body_clean[:120] if body_clean else 'Sent an attachment.',
                    action_url=f'/account/messages?id={conversation.id}',
                )

    return message


@transaction.atomic
def mark_conversation_as_read(conversation: Conversation, user) -> Conversation:
    """Mark all current messages in conversation read for the user."""
    if not can_access_conversation(conversation, user):
        raise PermissionDenied('Cannot access conversation.')

    now = timezone.now()
    update_fields = []
    if user.id == conversation.customer_id:
        conversation.customer_last_read_at = now
        update_fields.append('customer_last_read_at')
    if conversation.store and user.id == conversation.store.user_id:
        conversation.seller_last_read_at = now
        update_fields.append('seller_last_read_at')
    if user.is_staff:
        conversation.support_last_read_at = now
        update_fields.append('support_last_read_at')

    if update_fields:
        conversation.save(update_fields=update_fields)
    return conversation


@transaction.atomic
def report_conversation(conversation: Conversation, reporter, reason: str, details: str = '') -> ConversationReport:
    """Flag a conversation for abuse/moderation."""
    if not can_access_conversation(conversation, reporter):
        raise PermissionDenied('Cannot report a conversation you are not part of.')

    report = ConversationReport.objects.create(
        conversation=conversation,
        reporter=reporter,
        reason=reason,
        details=details,
    )
    conversation.status = ConversationStatus.REPORTED
    conversation.save(update_fields=['status', 'updated_at'])

    log_event(
        reporter,
        action='conversation_reported',
        obj=conversation,
        detail={'reason': reason, 'report_id': report.id},
    )
    return report


def get_conversation_unread_count(conversation: Conversation, user) -> int:
    """Calculate unread messages for a given user in this conversation."""
    if user.id == conversation.customer_id:
        last_read = conversation.customer_last_read_at
        qs = conversation.messages.exclude(sender=user)
    elif conversation.store and user.id == conversation.store.user_id:
        last_read = conversation.seller_last_read_at
        qs = conversation.messages.exclude(sender=user)
    elif user.is_staff:
        last_read = conversation.support_last_read_at
        qs = conversation.messages.exclude(sender=user)
    else:
        return 0

    if not last_read:
        return qs.count()
    return qs.filter(created_at__gt=last_read).count()


def get_total_unread_messages(user) -> int:
    """Compute total unread messages across all conversations for this user."""
    if not user or not user.is_authenticated:
        return 0

    customer_convs = Conversation.objects.filter(customer=user)
    unread = 0
    for c in customer_convs:
        unread += get_conversation_unread_count(c, user)

    seller_convs = Conversation.objects.filter(store__user=user)
    for c in seller_convs:
        unread += get_conversation_unread_count(c, user)

    return unread

