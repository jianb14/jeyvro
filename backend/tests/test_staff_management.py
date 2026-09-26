"""Phase 13 slice v2 gate tests — staff roles, permission audit, user management.

Contracts tested here (§4 v1.10):
1. The staff directory and every role change are administrator-only — per-group
   deny paths for customers, moderators, and support.
2. Role changes are audit-logged; self / superuser / last-administrator guards
   refuse unsafe demotions.
3. User management: support reads with filters and the {count, items} envelope;
   administrators suspend/reactivate.
4. Suspension revokes live sessions and blocks login until reactivated.
"""
import pytest
from django.contrib.auth.models import Group
from django.test import Client

from apps.accounts.models import User
from apps.audit.models import AuditLog

pytestmark = pytest.mark.django_db

STAFF_PASS = 'Str0ng!Passw0rd'
CUSTOMER_PASS = 'BuyerPassword1!'

USERS = '/api/v1/auth/admin/users/'
STAFF = '/api/v1/auth/admin/staff/'
LOGIN = '/api/v1/auth/login'
ME = '/api/v1/auth/me'

ALL_GROUPS = (
    'support', 'moderator', 'finance', 'operations',
    'administrator', 'super_administrator',
)


def _ensure_groups():
    for name in ALL_GROUPS:
        Group.objects.get_or_create(name=name)


def _make_user(email, *, is_staff=False, is_superuser=False, group=None):
    user = User.objects.create_user(
        email=email,
        password=STAFF_PASS if (is_staff or is_superuser) else CUSTOMER_PASS,
        first_name=email.split('@')[0].capitalize(),
        last_name='User',
        is_staff=is_staff,
        is_superuser=is_superuser,
    )
    if group:
        grp, _ = Group.objects.get_or_create(name=group)
        user.groups.add(grp)
    return user


def _client_for(user):
    client = Client()
    client.force_login(user)
    return client


def _post(client, url, payload=None):
    return client.post(url, payload or {}, content_type='application/json')


def test_staff_directory_is_administrator_only_and_searchable():
    admin = _make_user('adm@example.com', is_staff=True, group='administrator')
    moderator = _make_user('mod@example.com', is_staff=True, group='moderator')
    support = _make_user('sup@example.com', is_staff=True, group='support')
    customer = _make_user('plain@example.com')
    _make_user('ops@example.com', is_staff=True, group='operations')

    # Deny paths first — the directory is administrator-only (§4 matrix).
    assert _client_for(customer).get(STAFF).status_code == 403
    assert _client_for(moderator).get(STAFF).status_code == 403
    assert _client_for(support).get(STAFF).status_code == 403

    res = _client_for(admin).get(STAFF)
    assert res.status_code == 200
    body = res.json()
    assert 'count' in body and 'items' in body
    emails = {row['email'] for row in body['items']}
    assert {'adm@example.com', 'mod@example.com', 'ops@example.com'} <= emails

    row = next(r for r in body['items'] if r['email'] == 'ops@example.com')
    assert row['staff_roles'] == ['operations']
    assert row['is_staff'] is True
    assert row['is_superuser'] is False

    filtered = _client_for(admin).get(f'{STAFF}?q=ops@')
    assert filtered.status_code == 200
    assert {r['email'] for r in filtered.json()['items']} == {'ops@example.com'}


def test_role_assignment_grants_and_audits():
    _ensure_groups()
    admin = _make_user('adm2@example.com', is_staff=True, group='administrator')
    newbie = _make_user('newbie@example.com')  # plain customer, no groups

    res = _post(
        _client_for(admin),
        f'{STAFF}{newbie.id}/roles/assign',
        {'group': 'moderator'},
    )
    assert res.status_code == 200
    newbie.refresh_from_db()
    assert newbie.is_staff is True
    assert list(newbie.groups.values_list('name', flat=True)) == ['moderator']
    assert res.json()['staff_roles'] == ['moderator']

    event = AuditLog.objects.get(
        action='staff_group_assigned', object_id=str(newbie.id)
    )
    assert event.actor == admin
    assert event.detail['group'] == 'moderator'
    assert event.detail['email'] == 'newbie@example.com'

    # Assigning a role twice is refused, never silently duplicated.
    again = _post(
        _client_for(admin),
        f'{STAFF}{newbie.id}/roles/assign',
        {'group': 'moderator'},
    )
    assert again.status_code == 400


def test_role_change_denied_for_non_admins_and_guards():
    _ensure_groups()
    admin = _make_user('adm3@example.com', is_staff=True, group='administrator')
    support = _make_user('sup3@example.com', is_staff=True, group='support')
    moderator = _make_user('mod3@example.com', is_staff=True, group='moderator')
    target = _make_user('target@example.com')

    # Per-group deny paths — only administrators change roles (§4).
    assert _post(
        _client_for(support), f'{STAFF}{target.id}/roles/assign', {'group': 'support'}
    ).status_code == 403
    assert _post(
        _client_for(moderator), f'{STAFF}{target.id}/roles/remove', {'group': 'support'}
    ).status_code == 403

    admin_client = _client_for(admin)
    # Unknown group names are refused — no free-form groups.
    assert _post(
        admin_client, f'{STAFF}{target.id}/roles/assign', {'group': 'superadmin'}
    ).status_code == 400
    # Self changes are refused (no self-escalation).
    assert _post(
        admin_client, f'{STAFF}{admin.id}/roles/assign', {'group': 'support'}
    ).status_code == 400
    # Superuser targets are protected, even from another superuser.
    root = _make_user('root@example.com', is_staff=True, is_superuser=True)
    root2 = _make_user('root2@example.com', is_staff=True, is_superuser=True)
    assert _post(
        _client_for(root), f'{STAFF}{root2.id}/roles/assign', {'group': 'support'}
    ).status_code == 400
    # …but a superuser may still assign roles (technical governance bypass).
    assert _post(
        _client_for(root), f'{STAFF}{target.id}/roles/assign', {'group': 'support'}
    ).status_code == 200


def test_role_removal_clears_staff_flag_and_audits():
    _ensure_groups()
    admin = _make_user('adm4@example.com', is_staff=True, group='administrator')
    staffer = _make_user('staffer@example.com', is_staff=True, group='support')
    admin_client = _client_for(admin)

    res = _post(
        admin_client, f'{STAFF}{staffer.id}/roles/remove', {'group': 'support'}
    )
    assert res.status_code == 200
    staffer.refresh_from_db()
    assert staffer.groups.count() == 0
    assert staffer.is_staff is False  # the flag alone never grants power (§4)
    assert AuditLog.objects.filter(
        action='staff_group_removed', object_id=str(staffer.id)
    ).exists()

    # Removing a role the user does not hold is refused.
    assert _post(
        admin_client, f'{STAFF}{staffer.id}/roles/remove', {'group': 'support'}
    ).status_code == 400

    # A second role keeps the staff flag alive.
    multi = _make_user('multi@example.com', is_staff=True, group='support')
    multi.groups.add(Group.objects.get(name='moderator'))
    assert _post(
        admin_client, f'{STAFF}{multi.id}/roles/remove', {'group': 'support'}
    ).status_code == 200
    multi.refresh_from_db()
    assert multi.is_staff is True
    assert list(multi.groups.values_list('name', flat=True)) == ['moderator']


def test_last_administrator_cannot_be_demoted():
    _ensure_groups()
    admin = _make_user('soleadmin@example.com', is_staff=True, group='administrator')
    root = _make_user('root3@example.com', is_staff=True, is_superuser=True)
    root_client = _client_for(root)

    blocked = _post(
        root_client, f'{STAFF}{admin.id}/roles/remove', {'group': 'administrator'}
    )
    assert blocked.status_code == 400
    assert 'last administrator' in blocked.json()['detail'].lower()
    admin.refresh_from_db()
    assert admin.groups.filter(name='administrator').exists()

    # With a second administrator in place the demotion is allowed.
    _make_user('secondadmin@example.com', is_staff=True, group='administrator')
    allowed = _post(
        root_client, f'{STAFF}{admin.id}/roles/remove', {'group': 'administrator'}
    )
    assert allowed.status_code == 200


def test_user_management_list_envelope_and_filters():
    admin = _make_user('adm5@example.com', is_staff=True, group='administrator')
    support = _make_user('sup5@example.com', is_staff=True, group='support')
    moderator = _make_user('mod5@example.com', is_staff=True, group='moderator')
    customer = _make_user('buyer5@example.com')
    seller = _make_user('seller5@example.com')
    seller.is_seller = True
    seller.save(update_fields=['is_seller'])
    suspended = _make_user('susp5@example.com')
    suspended.suspend()

    # Deny paths — moderators and customers never reach user management.
    assert _client_for(moderator).get(USERS).status_code == 403
    assert _client_for(customer).get(USERS).status_code == 403

    support_client = _client_for(support)
    res = support_client.get(USERS)
    assert res.status_code == 200
    body = res.json()
    assert 'count' in body and 'items' in body

    # Search across email/name/phone.
    search = support_client.get(f'{USERS}?q=seller5@')
    assert [row['email'] for row in search.json()['items']] == ['seller5@example.com']

    # Role filter buckets.
    sellers = support_client.get(f'{USERS}?role=seller')
    assert 'seller5@example.com' in [
        row['email'] for row in sellers.json()['items']
    ]
    staff_rows = support_client.get(f'{USERS}?role=staff')
    staff_emails = [row['email'] for row in staff_rows.json()['items']]
    assert 'sup5@example.com' in staff_emails
    assert 'seller5@example.com' not in staff_emails

    # Status filter + suspended metadata.
    status_rows = support_client.get(f'{USERS}?status=suspended')
    assert [row['email'] for row in status_rows.json()['items']] == [
        'susp5@example.com'
    ]
    row = status_rows.json()['items'][0]
    assert row['account_status'] == 'suspended'
    assert row['suspended_at'] is not None

    # Detail endpoint — support reads a single record.
    detail = support_client.get(f'{USERS}{seller.id}/')
    assert detail.status_code == 200
    assert detail.json()['is_seller'] is True
    assert detail.json()['full_name']


def test_suspension_revokes_sessions_and_blocks_login_until_reactivated():
    admin = _make_user('adm6@example.com', is_staff=True, group='administrator')
    buyer = _make_user('buyer6@example.com')
    buyer_client = _client_for(buyer)
    assert buyer_client.get(ME).status_code == 200  # a live session

    res = _post(
        _client_for(admin),
        f'{USERS}{buyer.id}/suspend',
        {'reason': 'Abuse report under investigation.'},
    )
    assert res.status_code == 200
    body = res.json()
    assert body['account_status'] == 'suspended'
    assert body['suspended_at'] is not None

    buyer.refresh_from_db()
    assert buyer.is_active is False  # suspension revokes live sessions (§4 v1.10)

    # The previously-live session dies immediately, not at the next login.
    assert buyer_client.get(ME).status_code in (401, 403)

    # Login is refused with the explicit suspension error, not a generic one.
    login = Client().post(
        LOGIN,
        {'email': 'buyer6@example.com', 'password': CUSTOMER_PASS},
        content_type='application/json',
    )
    assert login.status_code == 403
    assert login.json()['error'] == 'account_suspended'

    event = AuditLog.objects.get(action='user_suspended', object_id=str(buyer.id))
    assert event.actor == admin
    assert event.detail['reason'] == 'Abuse report under investigation.'

    # Reactivation restores access and writes its own audit row.
    res = _post(
        _client_for(admin),
        f'{USERS}{buyer.id}/reactivate',
        {'reason': 'Appeal accepted.'},
    )
    assert res.status_code == 200
    buyer.refresh_from_db()
    assert buyer.is_active is True
    assert buyer.account_status == 'active'
    assert AuditLog.objects.filter(
        action='user_reactivated', object_id=str(buyer.id)
    ).exists()

    relogin = Client().post(
        LOGIN,
        {'email': 'buyer6@example.com', 'password': CUSTOMER_PASS},
        content_type='application/json',
    )
    assert relogin.status_code == 200


def test_suspend_and_reactivate_guards():
    _ensure_groups()
    admin = _make_user('adm7@example.com', is_staff=True, group='administrator')
    support = _make_user('sup7@example.com', is_staff=True, group='support')
    moderator = _make_user('mod7@example.com', is_staff=True, group='moderator')
    root = _make_user('root7@example.com', is_staff=True, is_superuser=True)
    target = _make_user('target7@example.com')
    admin_client = _client_for(admin)

    # Deny paths — suspension is administrator-only (§4 matrix).
    assert _post(
        _client_for(support), f'{USERS}{target.id}/suspend', {'reason': ''}
    ).status_code == 403
    assert _post(
        _client_for(moderator), f'{USERS}{target.id}/suspend', {'reason': ''}
    ).status_code == 403

    # Self-suspension refused (no self-lockout).
    assert _post(
        admin_client, f'{USERS}{admin.id}/suspend', {'reason': ''}
    ).status_code == 400
    # Superuser accounts are the governance carve-out.
    assert _post(
        admin_client, f'{USERS}{root.id}/suspend', {'reason': ''}
    ).status_code == 400
    # Double-suspension and reactivating an active account are both refused.
    assert _post(
        admin_client, f'{USERS}{target.id}/suspend', {'reason': 'First.'}
    ).status_code == 200
    assert _post(
        admin_client, f'{USERS}{target.id}/suspend', {'reason': 'Again.'}
    ).status_code == 400
    assert _post(
        admin_client, f'{USERS}{target.id}/reactivate', {'reason': ''}
    ).status_code == 200
    assert _post(
        admin_client, f'{USERS}{target.id}/reactivate', {'reason': ''}
    ).status_code == 400
