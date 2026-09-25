"""Audit service — the single write path for audit rows (§9)."""
from .models import AuditLog


def log_event(actor, action, obj, detail=None):
    """Records one critical action. `obj` is any model instance.

    `actor` may be None for system transitions (gateway webhooks, cron):
    the AuditLog row then reads as system-driven, never as pretending a
    human did it.
    """
    return AuditLog.objects.create(
        actor=actor,
        action=action,
        object_type=f'{obj._meta.app_label}.{obj._meta.model_name}',
        object_id=str(obj.pk),
        detail=detail or {},
    )