"""Audit log model (§9 — staff actions and critical transactions).

Foundation shipped early with Phase 4: the marketplace-sellers rule makes
audit-logged moderation binding now, not in Phase 13. Domain services write
rows through apps.audit.services.log_event — never blindly from views.
"""
from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class AuditLog(TimeStampedModel):
    """Who did what, to which object, when (§10.7)."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='audit_events',
    )
    action = models.CharField(max_length=64)
    object_type = models.CharField(max_length=64)
    object_id = models.CharField(max_length=64)
    detail = models.JSONField(blank=True, default=dict)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(
                fields=['object_type', 'object_id'],
                name='audit_object_idx',
            ),
            models.Index(fields=['actor'], name='audit_actor_idx'),
            models.Index(fields=['created_at'], name='audit_created_idx'),
        ]

    def __str__(self):
        return f'{self.actor} — {self.action} — {self.object_type}#{self.object_id}'