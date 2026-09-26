"""Phase 13 gate tests — staff operations, group permissions, and audit log.

Tests the Slice v1 contracts:
1. Staff permission groups (least privilege, support ≠ moderator ≠ administrator).
2. Seller application queue & review (approve flips is_seller and store.status).
3. Anti-self-review policy (staff cannot review their own application).
4. Store suspension & reactivation (audit-logged).
5. Audit viewer endpoint (group-gated, filterable, envelope).
"""
import pytest
from django.contrib.auth.models import Group
from django.test import Client

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.stores.models import SellerApplication, Store

pytestmark = pytest.mark.django_db

STAFF_PASS = 'Str0ng!Passw0rd'
CUSTOMER_PASS = 'BuyerPassword1!'

APPLICATIONS = '/api/v1/stores/admin/applications/'
STORES = '/api/v1/stores/admin/stores/'
AUDIT_EVENTS = '/api/v1/audit/events/'


def _make_user(email, *, is_staff=False, is_superuser=False, group=None):
    user = User.objects.create_user(
        email=email,
        password=STAFF_PASS if is_staff else CUSTOMER_PASS,
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


def _apply_for_store(user, name='Sample Crafts'):
    store = Store.objects.create(
        user=user,
        name=name,
        description='Craft shop',
        contact_email=user.email,
        status=Store.Status.PENDING,
    )
    app = SellerApplication.objects.create(
        user=user,
        store=store,
        store_name=name,
        status=SellerApplication.Status.PENDING,
    )
    return app, store


def test_staff_roles_never_leak_to_non_staff():
    """/auth/me exposes staff_roles to staff only; customers get an empty list."""
    moderator = _make_user('roledmod@example.com', is_staff=True, group='moderator')
    customer = _make_user('plainbuyer@example.com')

    staff_me = _client_for(moderator).get('/api/v1/auth/me').json()
    assert staff_me['is_staff'] is True
    assert staff_me['staff_roles'] == ['moderator']

    customer_me = _client_for(customer).get('/api/v1/auth/me').json()
    assert customer_me['is_staff'] is False
    assert customer_me['staff_roles'] == []


def test_customer_and_unauthorized_staff_denied_on_applications():
    """Customers and non-moderation staff never reach the review queue."""
    customer = _make_user('buyer@example.com')
    support = _make_user('support@example.com', is_staff=True, group='support')
    finance = _make_user('finance@example.com', is_staff=True, group='finance')

    # Customer gets 403 on staff queue
    res = _client_for(customer).get(APPLICATIONS)
    assert res.status_code == 403

    # Staff from a group outside the review matrix get 403 as well
    assert _client_for(finance).get(APPLICATIONS).status_code == 403

    # Support may read the queue (oversight) but never act on it
    res_support = _client_for(support).get(APPLICATIONS)
    assert res_support.status_code == 200
    assert 'items' in res_support.json()

    applicant = _make_user('readonly-target@example.com')
    app, _ = _apply_for_store(applicant, 'Read Only Store')
    res_review = _client_for(support).post(
        f'/api/v1/stores/admin/applications/{app.id}/review',
        {'decision': 'approved'},
        content_type='application/json',
    )
    assert res_review.status_code == 403
    applicant.refresh_from_db()
    assert applicant.is_seller is False


def test_moderator_reviews_application_approved_and_rejected():
    applicant = _make_user('applicant@example.com')
    app, store = _apply_for_store(applicant, 'Cordillera Weaves')

    moderator = _make_user('mod@example.com', is_staff=True, group='moderator')
    client = _client_for(moderator)

    # Approve
    review_url = f'/api/v1/stores/admin/applications/{app.id}/review'
    res = client.post(review_url, {'decision': 'approved'}, content_type='application/json')
    assert res.status_code == 200, res.content
    assert res.json()['status'] == 'approved'

    applicant.refresh_from_db()
    store.refresh_from_db()
    assert applicant.is_seller is True
    assert store.status == Store.Status.ACTIVE

    # Audit log was written
    assert AuditLog.objects.filter(
        action='seller_application_approved',
        actor=moderator,
        object_id=str(app.id),
    ).exists()

    # Second review attempt rejected (already reviewed)
    res_second = client.post(review_url, {'decision': 'approved'}, content_type='application/json')
    assert res_second.status_code == 400

    # Rejection requires a reason
    applicant2 = _make_user('applicant2@example.com')
    app2, _ = _apply_for_store(applicant2, 'Second Shop')
    res_no_reason = client.post(
        f'/api/v1/stores/admin/applications/{app2.id}/review',
        {'decision': 'rejected', 'reason': ''},
        content_type='application/json',
    )
    assert res_no_reason.status_code == 400

    res_rejected = client.post(
        f'/api/v1/stores/admin/applications/{app2.id}/review',
        {'decision': 'rejected', 'reason': 'Missing valid contact details.'},
        content_type='application/json',
    )
    assert res_rejected.status_code == 200
    assert res_rejected.json()['status'] == 'rejected'
    applicant2.refresh_from_db()
    assert applicant2.is_seller is False


def test_anti_self_review_policy():
    """Staff cannot approve/reject their own seller application."""
    staff_seller = _make_user('staffmod@example.com', is_staff=True, group='moderator')
    app, _ = _apply_for_store(staff_seller, 'Staff Owned Store')

    client = _client_for(staff_seller)
    res = client.post(
        f'/api/v1/stores/admin/applications/{app.id}/review',
        {'decision': 'approved'},
        content_type='application/json',
    )
    assert res.status_code == 400
    assert 'Staff cannot review their own application' in res.json().get('detail', '')


def test_store_suspension_and_reactivation_audit_logged():
    moderator = _make_user('mod2@example.com', is_staff=True, group='moderator')
    support = _make_user('support2@example.com', is_staff=True, group='support')
    seller = _make_user('activeseller@example.com')
    _, store = _apply_for_store(seller, 'Active Store')
    store.status = Store.Status.ACTIVE
    store.save()

    # Support cannot suspend (least-privileged)
    res_sup = _client_for(support).post(
        f'/api/v1/stores/admin/stores/{store.id}/suspend',
        {'reason': 'policy breach'},
        content_type='application/json',
    )
    assert res_sup.status_code == 403

    # Moderator can suspend
    res_mod = _client_for(moderator).post(
        f'/api/v1/stores/admin/stores/{store.id}/suspend',
        {'reason': 'Counterfeit report under investigation.'},
        content_type='application/json',
    )
    assert res_mod.status_code == 200
    store.refresh_from_db()
    assert store.status == Store.Status.SUSPENDED

    assert AuditLog.objects.filter(
        action='store_suspended',
        actor=moderator,
        object_id=str(store.id),
    ).exists()

    # Reactivate
    res_act = _client_for(moderator).post(
        f'/api/v1/stores/admin/stores/{store.id}/activate',
        {'reason': 'Cleared.'},
        content_type='application/json',
    )
    assert res_act.status_code == 200
    store.refresh_from_db()
    assert store.status == Store.Status.ACTIVE


def test_audit_log_viewer_permissions_and_filters():
    admin_user = _make_user('admin@example.com', is_staff=True, group='administrator')
    customer = _make_user('buyer3@example.com')
    support = _make_user('support3@example.com', is_staff=True, group='support')

    AuditLog.objects.create(
        actor=admin_user,
        action='test_action',
        object_type='stores.store',
        object_id='99',
        detail={'note': 'seed'},
    )

    # Customer gets 403
    assert _client_for(customer).get(AUDIT_EVENTS).status_code == 403

    # Support cannot view audit events (admin/ops/moderator only)
    assert _client_for(support).get(AUDIT_EVENTS).status_code == 403

    # Admin can view
    client = _client_for(admin_user)
    res = client.get(AUDIT_EVENTS)
    assert res.status_code == 200
    body = res.json()
    assert 'count' in body
    assert 'items' in body
    assert any(ev['action'] == 'test_action' for ev in body['items'])

    # Filter by action
    res_filtered = client.get(f'{AUDIT_EVENTS}?action=test_action')
    assert res_filtered.status_code == 200
    assert all(ev['action'] == 'test_action' for ev in res_filtered.json()['items'])

    # Support group CAN read the applications queue
    res = _client_for(support).get(APPLICATIONS)
    assert res.status_code == 200
    assert 'items' in res.json()
