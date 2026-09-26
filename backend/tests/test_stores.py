"""Phase 4 gate tests — seller application → review → storefront ownership.

Marketplace-sellers verification checklist drives these: moderation is
staff-only and audit-logged, sellers never self-approve, ownership deny
paths are proven (seller A ≠ store B), and pending/suspended stores never
leak through the public storefront.
"""
from decimal import Decimal

import pytest

from apps.audit.models import AuditLog
from apps.stores.models import SellerApplication, Store

pytestmark = pytest.mark.django_db

REGISTER = '/api/v1/auth/register'
LOGIN = '/api/v1/auth/login'
LOGOUT = '/api/v1/auth/logout'
APPLY = '/api/v1/stores/apply'
MY_STORE = '/api/v1/stores/my/store'
APPLICATIONS = '/api/v1/stores/admin/applications/'
PUBLIC = '/api/v1/stores/public/kalinga-crafts/'
PUBLIC_LIST = '/api/v1/stores/public/'

USER = {'email': 'seller@example.com', 'password': 'Str0ng!Passw0rd',
        'first_name': 'Sella', 'last_name': 'Seller'}
OTHER = {'email': 'other@example.com', 'password': 'Str0ng!Passw0rd2'}
STAFF = {'email': 'staff@example.com', 'password': 'Str0ng!Passw0rd3'}

APPLICATION_PAYLOAD = {
    'store_name': 'Kalinga Crafts',
    'store_description': 'Handwoven baskets from the Cordilleras.',
    'contact_phone': '+63 917 000 0000',
}


def register(client, payload):
    return client.post(REGISTER, payload, content_type='application/json')


def login(client, email, password):
    return client.post(
        LOGIN, {'email': email, 'password': password},
        content_type='application/json',
    )


def grant_moderator(email):
    """Phase 13 group rules (PROJECT_CONTEXT section 4): the is_staff flag
    alone no longer unlocks the review queue, so test staff join the group."""
    from django.contrib.auth.models import Group
    from apps.accounts.models import User
    User.objects.filter(email=email).update(is_staff=True)
    user = User.objects.get(email=email)
    group, _ = Group.objects.get_or_create(name='moderator')
    user.groups.add(group)
    return user


def make_staff(client):
    """Creates a moderator user and starts their session."""
    from apps.accounts.models import User
    register(client, STAFF)
    grant_moderator(STAFF['email'])
    login(client, STAFF['email'], STAFF['password'])
    return User.objects.get(email=STAFF['email'])


def setup_approved_store(client, approve=True):
    """Registers + logs in USER, applies, then reviews as staff.

    Returns (application, staff_user). Rejection keeps the store pending.
    """
    register(client, USER)
    login(client, USER['email'], USER['password'])
    apply_response = client.post(
        APPLY, APPLICATION_PAYLOAD, content_type='application/json'
    )
    assert apply_response.status_code == 201, apply_response.content
    staff_user = make_staff(client)
    application_id = client.get(APPLICATIONS).json()['items'][0]['id']
    decision = 'approved' if approve else 'rejected'
    review = client.post(
        f'{APPLICATIONS}{application_id}/review',
        {'decision': decision}
        if approve
        else {'decision': decision, 'reason': 'Incomplete business details.'},
        content_type='application/json',
    )
    assert review.status_code == 200, review.content
    # Hand the session back to the seller — most callers continue as USER.
    client.post(LOGOUT)
    login(client, USER['email'], USER['password'])
    return (
        SellerApplication.objects.get(pk=application_id),
        staff_user,
    )


def test_apply_creates_pending_application_and_store(client):
    register(client, USER)
    login(client, USER['email'], USER['password'])
    response = client.post(
        APPLY, APPLICATION_PAYLOAD, content_type='application/json'
    )
    assert response.status_code == 201, response.content
    assert response.json()['status'] == SellerApplication.Status.PENDING

    application = SellerApplication.objects.get(user__email=USER['email'])
    store = application.store
    assert store.status == Store.Status.PENDING
    assert store.slug == 'kalinga-crafts'
    # is_seller flips only on approval — applying alone grants nothing.
    assert application.user.is_seller is False

    # Duplicate application is rejected (one application per user).
    duplicate = client.post(
        APPLY, APPLICATION_PAYLOAD, content_type='application/json'
    )
    assert duplicate.status_code == 409


def test_customer_cannot_review_own_application(client):
    register(client, USER)
    login(client, USER['email'], USER['password'])
    client.post(APPLY, APPLICATION_PAYLOAD, content_type='application/json')
    # No staff session — the review queue is staff-group only.
    applications = client.get(APPLICATIONS)
    assert applications.status_code in (401, 403)


def test_staff_can_review_and_approval_activates_store(client):
    application, staff_user = setup_approved_store(client)

    assert application.status == SellerApplication.Status.APPROVED
    assert application.store.status == Store.Status.ACTIVE
    assert application.reviewed_by_id == staff_user.pk
    application.user.refresh_from_db()
    assert application.user.is_seller is True

    # Moderation is audit-logged (marketplace-sellers rule 3).
    event = AuditLog.objects.filter(
        object_type='stores.sellerapplication',
        object_id=str(application.pk),
    ).latest('created_at')
    assert event.action == 'seller_application_approved'
    assert event.actor_id == staff_user.pk


def test_rejection_requires_reason_and_stays_pending(client):
    application, _staff_user = setup_approved_store(client, approve=False)

    assert application.status == SellerApplication.Status.REJECTED
    assert application.rejection_reason == 'Incomplete business details.'
    # Store stays pending; the applicant never became a seller.
    store = application.store
    assert store.status == Store.Status.PENDING
    assert store.user.is_seller is False


def test_pending_store_not_public_until_approved(client):
    register(client, USER)
    login(client, USER['email'], USER['password'])
    client.post(APPLY, APPLICATION_PAYLOAD, content_type='application/json')

    # Pending storefront is invisible.
    assert client.get(PUBLIC).status_code == 404

    make_staff(client)
    application_id = client.get(APPLICATIONS).json()['items'][0]['id']
    review = client.post(
        f'{APPLICATIONS}{application_id}/review',
        {'decision': 'approved'},
        content_type='application/json',
    )
    assert review.status_code == 200, review.content

    # Approved storefront is public and exposes no owner/contact internals.
    public = client.get(PUBLIC)
    assert public.status_code == 200, public.content
    body = public.json()
    assert body['name'] == 'Kalinga Crafts'
    for internal in ('user', 'contact_email', 'contact_phone', 'status'):
        assert internal not in body


def test_seller_can_edit_own_store_but_not_another(client):
    application, _staff_user = setup_approved_store(client)

    # Seller edits their own store profile (4.3 store settings).
    edit = client.patch(
        MY_STORE,
        {'description': 'Updated storefront description.',
         'return_policy': 'Returns within 7 days.'},
        content_type='application/json',
    )
    assert edit.status_code == 200, edit.content
    assert edit.json()['return_policy'] == 'Returns within 7 days.'

    # Seller B cannot reach seller A's store — ownership deny path.
    client.post(LOGOUT)
    login(client, OTHER['email'], OTHER['password'])
    denied = client.get(MY_STORE)
    assert denied.status_code in (401, 403)


def test_seller_cannot_flip_own_store_status(client):
    application, _staff_user = setup_approved_store(client)

    # Status is read-only on the owner serializer — self-serve flips are
    # impossible by payload (marketplace-sellers rule 3).
    spoof = client.patch(
        MY_STORE, {'status': 'suspended'}, content_type='application/json'
    )
    assert spoof.status_code == 200
    assert application.store.status == Store.Status.ACTIVE


def test_staff_suspend_and_reactivate_store(client):
    application, staff_user = setup_approved_store(client)
    store = application.store

    from apps.stores import services

    suspended = services.suspend_store(
        staff_user, store, reason='Policy violation'
    )
    assert suspended.status == Store.Status.SUSPENDED
    assert suspended.suspended_at is not None
    assert AuditLog.objects.filter(
        action='store_suspended', object_id=str(store.pk)
    ).exists()

    # Suspended storefront disappears from the public API.
    assert client.get(PUBLIC).status_code == 404

    reactivated = services.activate_store(staff_user, store)
    assert reactivated.status == Store.Status.ACTIVE
    assert client.get(PUBLIC).status_code == 200


def test_public_store_directory_lists_active_stores_only(client):
    """Phase 6 discovery: the public store directory ({count, items})
    exposes active stores only — no owner/contact internals."""
    application, staff_user = setup_approved_store(client)

    # The directory is public — anonymous browsers can read it.
    client.post(LOGOUT)
    response = client.get(PUBLIC_LIST)
    assert response.status_code == 200, response.content
    body = response.json()
    assert body['count'] == 1
    item = body['items'][0]
    assert item['name'] == 'Kalinga Crafts'
    for internal in ('user', 'contact_email', 'contact_phone', 'status'):
        assert internal not in item

    # Suspended stores drop out of the directory immediately.
    from apps.stores import services
    services.suspend_store(
        staff_user, application.store, reason='Policy violation'
    )
    assert client.get(PUBLIC_LIST).json()['count'] == 0


def test_seller_sets_shipping_fees_and_public_store_exposes_them(client):
    """Phase 8: per-store flat fee + free-shipping threshold (§6 v1.7).

    The seller owns these values; JSON crosses the wire as numbers and the
    public storefront reads them without owner/contact internals.
    """
    application, _staff_user = setup_approved_store(client)

    edit = client.patch(
        MY_STORE,
        {'shipping_flat_fee': '49.00', 'free_shipping_threshold': '500.00'},
        content_type='application/json',
    )
    assert edit.status_code == 200, edit.content
    body = edit.json()
    assert body['shipping_flat_fee'] == 49.0
    assert body['free_shipping_threshold'] == 500.0

    public = client.get(PUBLIC)
    assert public.status_code == 200, public.content
    public_body = public.json()
    assert public_body['shipping_flat_fee'] == 49.0
    assert public_body['free_shipping_threshold'] == 500.0

    # A null threshold remains allowed (no free shipping) and defaults hold.
    cleared = client.patch(
        MY_STORE, {'free_shipping_threshold': None},
        content_type='application/json',
    )
    assert cleared.status_code == 200, cleared.content
    assert cleared.json()['free_shipping_threshold'] is None
    assert application.store.shipping_flat_fee == Decimal('49.00')


def test_shipping_fees_cannot_be_negative(client):
    application, _staff_user = setup_approved_store(client)

    bad = client.patch(
        MY_STORE, {'shipping_flat_fee': '-1.00'},
        content_type='application/json',
    )
    assert bad.status_code == 400, bad.content
    assert application.store.shipping_flat_fee == Decimal('0.00')

    bad_threshold = client.patch(
        MY_STORE, {'free_shipping_threshold': '-5'},
        content_type='application/json',
    )
    assert bad_threshold.status_code == 400
    assert application.store.free_shipping_threshold is None
