"""Platform settings services — singleton access and audited updates (§6 v1.13).

Every consumer (shipping seeding, COD availability, the payment window,
new-account notification defaults) reads through here, so the DB row is
the single source of truth and tests can flip one value without touching
Django settings.
"""
from django.conf import settings as django_settings
from django.db import OperationalError, ProgrammingError, transaction

from apps.audit.services import log_event

from .models import PlatformSettings


def _bootstrap_expiry_hours():
    """Env seeds the row's payment window on its FIRST creation only —
    afterwards the DB value wins (changing env never silently overrides
    live configuration)."""
    try:
        return int(getattr(django_settings, 'PAYMENTS_PAYMENT_EXPIRY_HOURS', 24))
    except (TypeError, ValueError):
        return 24


def get_settings():
    """The one PlatformSettings row, created on first use."""
    obj, _created = PlatformSettings.objects.get_or_create(
        pk=PlatformSettings.SINGLETON_ID,
        defaults={'payment_expiry_hours': _bootstrap_expiry_hours()},
    )
    return obj


def cod_is_enabled():
    """Checkout truth for Cash on Delivery (§6 v1.13)."""
    return get_settings().cod_enabled


def payment_window_hours():
    """The online-payment expiry window — DB truth, env fallback only when
    the platform table is not migrated yet (early bootstrap)."""
    try:
        return int(get_settings().payment_expiry_hours)
    except (OperationalError, ProgrammingError):
        try:
            return int(
                getattr(django_settings, 'PAYMENTS_PAYMENT_EXPIRY_HOURS', 24)
            )
        except (TypeError, ValueError):
            return 24


def notification_defaults():
    """Initial values for a NEW account's NotificationPreference row.

    Existing per-user rows are never overwritten — a customer's own choice
    always beats the platform default (§6 v1.13).
    """
    current = get_settings()
    return {
        'order_updates_email': current.default_order_updates_email,
        'promotions_email': current.default_promotions_email,
        'messaging_email': current.default_messaging_email,
    }


def apply_update(actor, *, changes, scope):
    """Persist validated field changes and audit the per-field diff.

    `changes` is serializer-validated data only; `scope` labels the audit
    row ('general' or 'commission') so the trail says which path edited.
    """
    if not changes:
        return get_settings()
    with transaction.atomic():
        settings_obj = get_settings()
        before = {}
        for field, value in changes.items():
            before[field] = getattr(settings_obj, field)
            setattr(settings_obj, field, value)
        settings_obj.updated_by = actor
        settings_obj.save(update_fields=[*changes.keys(), 'updated_by', 'updated_at'])
        log_event(
            actor,
            'platform_settings_update',
            settings_obj,
            detail={
                'scope': scope,
                'changes': {
                    field: {'from': str(before[field]), 'to': str(value)}
                    for field, value in changes.items()
                },
            },
        )
    return settings_obj
