"""Audit service — the single write path for audit rows (§9)."""
from .models import AuditLog


def log_event(actor, action, obj=None, detail=None, *, object_type='',
              object_id=''):
    """Records one critical action. `obj` is any model instance.

    `actor` may be None for system transitions (gateway webhooks, cron):
    the AuditLog row then reads as system-driven, never as pretending a
    human did it.

    `obj` may be None too, for an event that belongs to no domain record — an
    **export** is a sensitive read, so it has no row to hang itself on, and
    such an event names its subject explicitly with `object_type`/`object_id`
    (§20.3). Omitting both is refused rather than stored: a blank row would be
    a trail that proves nothing.
    """
    if obj is not None:
        object_type = f'{obj._meta.app_label}.{obj._meta.model_name}'
        object_id = str(obj.pk)
    if not object_type:
        raise ValueError(
            f'Audit event {action!r} needs an object or an explicit object_type.'
        )
    return AuditLog.objects.create(
        actor=actor,
        action=action,
        object_type=object_type,
        object_id=object_id,
        detail=detail or {},
    )