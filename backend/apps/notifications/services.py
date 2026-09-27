"""Notification services (Phase 15 — ROADMAP §15.2, §15.3, §15.4).

Provides in-app notification creation with category tagging, user preference checks,
and safe email delivery seams.
"""
import logging
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import NotificationPreference
from apps.platform.services import notification_defaults
from .models import Notification, NotificationCategory

logger = logging.getLogger(__name__)


def should_send_email_for_category(user, category: str) -> bool:
    """Check whether the user has opted in to emails for this category."""
    prefs, _ = NotificationPreference.objects.get_or_create(
        user=user, defaults=notification_defaults()
    )
    if category == NotificationCategory.ORDERS:
        return bool(prefs.order_updates_email)
    elif category == NotificationCategory.MESSAGING:
        return bool(prefs.messaging_email)
    elif category == NotificationCategory.PROMOTIONS:
        return bool(prefs.promotions_email)
    # System notifications default to False unless critical
    return False


@transaction.atomic
def create_notification(
    recipient,
    *,
    category: str,
    title: str,
    message: str,
    action_url: str = '',
    send_email: bool = True,
) -> Notification:
    """Create an in-app notification and optionally trigger email delivery."""
    notification = Notification.objects.create(
        recipient=recipient,
        category=category,
        title=title,
        message=message,
        action_url=action_url,
    )

    if send_email and recipient.email:
        try:
            if should_send_email_for_category(recipient, category):
                # Background-job / Celery seam (§15.4): synchronous fallback via Django send_mail
                send_mail(
                    subject=f'[JEYVRO] {title}',
                    message=message,
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@jeyvro.local'),
                    recipient_list=[recipient.email],
                    fail_silently=True,
                )
        except Exception as e:
            logger.warning('Failed to send notification email to %s: %s', recipient.email, e)

    return notification


@transaction.atomic
def mark_notification_as_read(notification_id: int, user) -> Notification:
    """Mark a single notification as read for the requesting user."""
    notification = Notification.objects.select_for_update().get(pk=notification_id, recipient=user)
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=['is_read', 'read_at', 'updated_at'])
    return notification


@transaction.atomic
def mark_all_notifications_as_read(user) -> int:
    """Mark all unread notifications as read for the user. Returns count updated."""
    now = timezone.now()
    count = Notification.objects.filter(recipient=user, is_read=False).update(
        is_read=True, read_at=now, updated_at=now
    )
    return count


def get_unread_notification_count(user) -> int:
    """Return count of unread notifications for a user."""
    if not user or not user.is_authenticated:
        return 0
    return Notification.objects.filter(recipient=user, is_read=False).count()
