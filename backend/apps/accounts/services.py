"""Account services — business logic lives here, never in views (§8).

Login throttling uses Django's cache (no new dependency, C3): 5 failed
attempts per email locks that email out for 15 minutes. Emails use Django's
token generator + the configured email backend (console in dev).
"""
from django.contrib.auth.models import Group
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import transaction
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from apps.audit.services import log_event

from .models import User

MAX_FAILED_LOGINS = 5
LOCKOUT_SECONDS = 15 * 60


# --- Login throttling (Phase 3.2 — login throttling / failed-login handling)

def _fail_key(email):
    return f'login-fail:{email.strip().lower()}'


def register_failed_login(email):
    key = _fail_key(email)
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, LOCKOUT_SECONDS)
        count = 1
    return count


def is_locked_out(email):
    return cache.get(_fail_key(email), 0) >= MAX_FAILED_LOGINS


def clear_failed_logins(email):
    cache.delete(_fail_key(email))


# --- Email tokens (verification / password reset share the generator)

def _send_action_email(request, user, subject, body_text, url_name):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    path = reverse(url_name)
    link = request.build_absolute_uri(f'{path}?uid={uid}&token={token}')
    send_mail(
        subject=subject,
        message=(
            f'Hello {user.email},\n\n'
            f'{body_text}\n\n{link}\n\n'
            f'If you did not request this, ignore this email.\n'
        ),
        from_email=None,  # DEFAULT_FROM_EMAIL
        recipient_list=[user.email],
        fail_silently=False,
    )
    return uid, token


def send_verification_email(request, user):
    return _send_action_email(
        request,
        user,
        subject='Verify your JEYVRO account',
        body_text='Verify your email address to finish activating your account:',
        url_name='accounts:verify-email',
    )


def send_password_reset_email(request, user):
    return _send_action_email(
        request,
        user,
        subject='Reset your JEYVRO password',
        body_text='Use the link below to reset your password:',
        url_name='accounts:password-reset-confirm',
    )


def decode_uid(uidb64):
    try:
        return User.objects.get(pk=force_str(urlsafe_base64_decode(uidb64)))
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        return None


# --- Staff administration (Phase 13.1/13.2 — §4 v1.10)
#
# Only administrators reach these services (group-gated at the view layer);
# the guards here are the final line of defense (§10). Every change writes an
# AuditLog row, so role/status history is reconstructible from §13.7.

STAFF_GROUP_NAMES = (
    'support',
    'moderator',
    'finance',
    'operations',
    'administrator',
    'super_administrator',
)


def _staff_group(group_name):
    """Resolves a canonical staff group or refuses (§4 matrix, no free names)."""
    group = Group.objects.filter(name=group_name).first()
    if group is None or group_name not in STAFF_GROUP_NAMES:
        raise ValueError('Unknown staff group.')
    return group


def _refuse_protected_target(actor, target, *, action_label):
    """Self- and superuser-target guards shared by role and status changes."""
    if target.pk == actor.pk:
        raise ValueError(f'You cannot {action_label} your own account.')
    if target.is_superuser:
        raise ValueError('Superuser accounts manage their own access.')


def assign_staff_group(actor, target, *, group_name):
    """Administrator grants one staff group (audit-logged)."""
    group = _staff_group(group_name)
    _refuse_protected_target(actor, target, action_label='manage staff roles on')

    with transaction.atomic():
        if target.groups.filter(pk=group.pk).exists():
            raise ValueError('This user already has that staff role.')
        target.is_staff = True
        target.save(update_fields=['is_staff', 'updated_at'])
        target.groups.add(group)
        log_event(
            actor,
            'staff_group_assigned',
            target,
            detail={'email': target.email, 'group': group_name},
        )
    return target


def remove_staff_group(actor, target, *, group_name):
    """Administrator revokes one staff group (audit-logged).

    Removing the last staff group also clears `is_staff` — the flag alone never
    grants power (§4), so an ex-staff user stops being staff-shaped entirely.
    The marketplace's last administrator cannot be demoted.
    """
    group = _staff_group(group_name)
    _refuse_protected_target(actor, target, action_label='manage staff roles on')

    with transaction.atomic():
        if not target.groups.filter(pk=group.pk).exists():
            raise ValueError('This user does not have that staff role.')
        if group_name == 'administrator':
            others = User.objects.filter(
                groups__name='administrator'
            ).exclude(pk=target.pk)
            if not others.exists():
                raise ValueError('The last administrator cannot be demoted.')
        target.groups.remove(group)
        if not target.groups.filter(name__in=STAFF_GROUP_NAMES).exists():
            target.is_staff = False
            target.save(update_fields=['is_staff', 'updated_at'])
        log_event(
            actor,
            'staff_group_removed',
            target,
            detail={'email': target.email, 'group': group_name},
        )
    return target


def suspend_user(actor, target, *, reason=''):
    """Administrator suspends an account (audit-logged).

    Suspension revokes live sessions (User.suspend) — see §4 v1.10. Superuser
    accounts are the technical-governance carve-out and cannot be suspended
    through this operational surface.
    """
    _refuse_protected_target(actor, target, action_label='suspend')
    if target.account_status == User.AccountStatus.SUSPENDED:
        raise ValueError('This account is already suspended.')

    with transaction.atomic():
        target.suspend()
        log_event(
            actor,
            'user_suspended',
            target,
            detail={'email': target.email, 'reason': reason},
        )
    return target


def reactivate_user(actor, target, *, reason=''):
    """Administrator lifts a suspension (audit-logged)."""
    if target.account_status != User.AccountStatus.SUSPENDED:
        raise ValueError('This account is not suspended.')

    with transaction.atomic():
        target.reactivate()
        log_event(
            actor,
            'user_reactivated',
            target,
            detail={'email': target.email, 'reason': reason},
        )
    return target
