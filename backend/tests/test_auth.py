"""Phase 3 auth gate tests — register/login/logout, throttling, ownership.

Money/auth rule (§11): no auth logic merges without tests. Ownership checks
are tested by proving user B cannot reach user A's records.
"""
import re

import pytest
from django.core.cache import cache
from django.core import mail
from django.test import override_settings

REGISTER = '/api/v1/auth/register'
LOGIN = '/api/v1/auth/login'
LOGOUT = '/api/v1/auth/logout'
ME = '/api/v1/auth/me'
ADDRESSES = '/api/v1/auth/addresses/'

pytestmark = pytest.mark.django_db

USER_A = {'email': 'a@example.com', 'password': 'Str0ng!Passw0rd',
          'first_name': 'A', 'last_name': 'Owner'}
USER_B = {'email': 'b@example.com', 'password': 'Str0ng!Passw0rd2'}


def register(client, payload):
    return client.post(REGISTER, payload, content_type='application/json')


def login(client, email, password):
    return client.post(
        LOGIN, {'email': email, 'password': password},
        content_type='application/json',
    )


def test_register_login_me_logout(client):
    response = register(client, USER_A)
    assert response.status_code == 201
    assert response.json()['email'] == USER_A['email']
    assert 'password' not in response.json()  # passwords never round-trip

    assert login(client, USER_A['email'], USER_A['password']).status_code == 200
    me = client.get(ME)
    assert me.status_code == 200
    assert me.json()['email'] == USER_A['email']

    assert client.post(LOGOUT).status_code == 200
    assert client.get(ME).status_code in (401, 403)  # session gone


def test_me_requires_authentication(client):
    assert client.get(ME).status_code in (401, 403)


def test_duplicate_email_rejected(client):
    assert register(client, USER_A).status_code == 201
    dup = register(client, USER_A)
    assert dup.status_code == 400
    assert 'field_errors' in dup.json()


def test_wrong_password_then_lockout(client):
    login(client, USER_A['email'], USER_A['password'])  # creates user
    cache.clear()  # isolate throttle counters for this test

    for _ in range(5):
        response = login(client, USER_A['email'], 'WrongPassword1!')
        assert response.status_code == 400

    locked = login(client, USER_A['email'], USER_A['password'])
    assert locked.status_code == 429  # even the CORRECT password is blocked
    assert locked.json()['error'] == 'account_locked'
    cache.clear()  # don't leak lockout into later tests


def test_suspended_user_cannot_login(client):
    from apps.accounts.models import User
    cache.clear()  # isolate throttle counters from other tests
    register(client, USER_A)
    User.objects.get(email=USER_A['email']).suspend()

    response = login(client, USER_A['email'], USER_A['password'])
    assert response.status_code == 403
    assert response.json()['error'] == 'account_suspended'


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
def test_email_verification_and_password_reset(client, settings):
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
    register(client, USER_A)
    assert len(mail.outbox) == 1  # verification email on register

    # --- email verification via the link in the email body
    verify_match = re.search(r'\?uid=([^&\s]+)&token=([^\s]+)', mail.outbox[0].body)
    assert verify_match, 'verification link missing from email'
    verify = client.get(
        f'/api/v1/auth/verify-email?uid={verify_match.group(1)}'
        f'&token={verify_match.group(2)}'
    )
    assert verify.status_code == 200

    # --- password reset flow
    client.post(
        '/api/v1/auth/password-reset', {'email': USER_A['email']},
        content_type='application/json',
    )
    assert len(mail.outbox) == 2
    reset_match = re.search(r'\?uid=([^&\s]+)&token=([^\s]+)', mail.outbox[1].body)
    confirm = client.post(
        '/api/v1/auth/password-reset-confirm',
        {'uid': reset_match.group(1), 'token': reset_match.group(2),
         'new_password': 'BrandNew!Pass1'},
        content_type='application/json',
    )
    assert confirm.status_code == 200

    assert login(client, USER_A['email'], USER_A['password']).status_code == 400  # old
    assert login(client, USER_A['email'], 'BrandNew!Pass1').status_code == 200   # new


def test_address_ownership_enforced(client):
    register(client, USER_A)
    login(client, USER_A['email'], USER_A['password'])

    created = client.post(
        ADDRESSES,
        {'full_name': 'A Owner', 'phone': '09171234567', 'line1': '1 Main St',
         'city': 'Quezon City', 'province': 'Metro Manila',
         'postal_code': '1101', 'is_default': True},
        content_type='application/json',
    )
    assert created.status_code == 201
    address_id = created.json()['id']

    # Switch to user B — A's address must be invisible and untouchable.
    register(client, USER_B)
    login(client, USER_B['email'], USER_B['password'])

    assert client.get(ADDRESSES).json()['count'] == 0  # scoped list
    assert client.get(f'{ADDRESSES}/{address_id}/').status_code == 404  # no leak
    attack = client.patch(
        f'{ADDRESSES}/{address_id}/', {'city': 'Hacked'},
        content_type='application/json',
    )
    assert attack.status_code == 404  # deny path tested


def test_change_password_flow(client):
    register(client, USER_A)
    login(client, USER_A['email'], USER_A['password'])

    # CSRF dance exactly like the SPA: a FRESH token before each unsafe
    # request (Django rotates the csrftoken cookie after each validated POST,
    # so a captured token is single-use).
    def fresh_csrf():
        return client.get('/api/v1/auth/csrf').json()['csrfToken']

    def post(url, payload):
        return client.post(
            url, payload, content_type='application/json',
            HTTP_X_CSRFTOKEN=fresh_csrf(),
        )

    change = post(
        '/api/v1/auth/change-password',
        {'current_password': 'WrongCurrent1!', 'new_password': 'NewStrong!99'},
    )
    assert change.status_code == 400, change.content  # wrong current rejected

    change = post(
        '/api/v1/auth/change-password',
        {'current_password': USER_A['password'], 'new_password': 'NewStrong!99'},
    )
    assert change.status_code == 200, change.content

    # The session survives the change (update_session_auth_hash)…
    me = client.get(ME)
    assert me.status_code == 200, me.content
    # …and the new password works on a fresh login.
    fresh = client.post(
        LOGIN, {'email': USER_A['email'], 'password': 'NewStrong!99'},
        content_type='application/json', HTTP_X_CSRFTOKEN=fresh_csrf(),
    )
    assert fresh.status_code == 200, fresh.content


def test_addresses_require_authentication(client):
    assert client.get(ADDRESSES).status_code in (401, 403)

