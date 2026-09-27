"""Notifications domain models (Phase 15 — ROADMAP §15.2, §15.3).

One row per user notification. Tracks in-app notification status, categories,
and actionable links.
"""
from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class NotificationCategory(models.TextChoices):
    ORDERS = 'orders', 'Orders'
    MESSAGING = 'messaging', 'Messaging'
    PROMOTIONS = 'promotions', 'Promotions'
    SYSTEM = 'system', 'System'


class Notification(TimeStampedModel):
    """An in-app notification for a user."""

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        db_index=True,
    )
    category = models.CharField(
        max_length=32,
        choices=NotificationCategory.choices,
        default=NotificationCategory.SYSTEM,
        db_index=True,
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    action_url = models.CharField(max_length=255, blank=True, default='')
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read', '-created_at']),
        ]

    def __str__(self):
        return f'Notification({self.recipient_id}, {self.category}, {self.title})'
