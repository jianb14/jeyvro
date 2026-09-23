"""Account services — business logic lives here, never in views (§8).

Login throttling uses Django's cache (no new dependency, C3): 5 failed
attempts per email locks that email out for 15 minutes. Emails use Django's
token generator + the configured email backend (console in dev).
"""
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

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
