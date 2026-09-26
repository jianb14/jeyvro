"""Phase 13.4 gate tests — staff catalog console, takedown, and taxonomy.

Contracts proven here (§4 matrix, marketplace-admin rules 1-3, 6):
1. Product console: moderator/administrator only; support/finance/customer
   are denied. Filters (q/status/store/category) run server-side with the
   {count, items} envelope.
2. Review endpoint: publish/reject gated to moderators; reject demands a
   reason; every decision writes an audit row.
3. Takedown: published → unpublished with a required reason; the reason is
   seller-visible (stored on the product) and audit-logged.
4. Taxonomy: categories & brands are operations/administrator only; writes
   are audit-logged; cycles and non-empty category deletes are refused.
"""
import pytest
from django.contrib.auth.models import Group
from django.test import Client

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.catalog.models import Brand, Category, Product
from apps.stores.models import Store

pytestmark = pytest.mark.django_db

PASSWORD = 'Str0ng!Passw0rd'
PRODUCTS = '/api/v1/catalog/admin/products/'
CATEGORIES = '/api/v1/catalog/admin/categories/'
BRANDS = '/api/v1/catalog/admin/brands/'


def _make_user(email, *, group=None, is_staff=None):
    user = User.objects.create_user(
        email=email,
        password=PASSWORD,
        first_name=email.split('@')[0].capitalize(),
        last_name='User',
        is_staff=group is not None if is_staff is None else is_staff,
    )
    if group:
        grp, _ = Group.objects.get_or_create(name=group)
        user.groups.add(grp)
    return user


def _client_for(user):
    client = Client()
    client.force_login(user)
    return client


def _store_for(owner, name='Catalog Console Store'):
    return Store.objects.create(
        user=owner,
        name=name,
        description='Console tests',
        contact_email=owner.email,
        status=Store.Status.ACTIVE,
    )


def _product(store, *, title='Console Item', status=None, **extra):
    return Product.objects.create(
        store=store,
        title=title,
        base_price='199.00',
        status=status or Product.Status.PENDING_REVIEW,
        **extra,
    )


def test_product_console_group_gating():
    moderator = _make_user('cat-mod@example.com', group='moderator')
    support = _make_user('cat-sup@example.com', group='support')
    finance = _make_user('cat-fin@example.com', group='finance')
    customer = _make_user('cat-buyer@example.com', is_staff=False)

    seller = _make_user('cat-seller@example.com', is_staff=False)
    _product(_store_for(seller))

    assert _client_for(customer).get(PRODUCTS).status_code == 403
    assert _client_for(support).get(PRODUCTS).status_code == 403
    assert _client_for(finance).get(PRODUCTS).status_code == 403

    res = _client_for(moderator).get(PRODUCTS)
    assert res.status_code == 200
    body = res.json()
    assert body['count'] == 1
    row = body['items'][0]
    # Light console shape: store identity + counts, no full payloads.
    assert row['store_owner_email'] == 'cat-seller@example.com'
    assert row['status'] == 'pending_review'
    assert float(row['display_price']) == 199.0
    assert row['variant_count'] == 0
    assert 'variants' not in row


def test_product_console_filters_are_server_side():
    moderator = _make_user('cat-mod2@example.com', group='moderator')
    seller = _make_user('cat-seller2@example.com', is_staff=False)
    store = _store_for(seller, name='Filter Shop')
    category = Category.objects.create(name='Furniture')
    brand = Brand.objects.create(name='Rattan Co')

    _product(store, title='Alpha Chair', category=category, brand=brand)
    _product(store, title='Beta Table', status=Product.Status.PUBLISHED)
    _product(store, title='Gamma Lamp', status=Product.Status.ARCHIVED)

    client = _client_for(moderator)

    by_status = client.get(f'{PRODUCTS}?status=published').json()
    assert by_status['count'] == 1
    assert by_status['items'][0]['title'] == 'Beta Table'

    by_q = client.get(f'{PRODUCTS}?q=chair').json()
    assert [i['title'] for i in by_q['items']] == ['Alpha Chair']

    by_owner = client.get(f'{PRODUCTS}?q=cat-seller2').json()
    assert by_owner['count'] == 3

    by_category = client.get(f'{PRODUCTS}?category=furniture').json()
    assert [i['title'] for i in by_category['items']] == ['Alpha Chair']
    assert by_category['items'][0]['category_name'] == 'Furniture'
    assert by_category['items'][0]['brand_name'] == 'Rattan Co'

    by_store = client.get(f'{PRODUCTS}?store=filter-shop').json()
    assert by_store['count'] == 3

    paged = client.get(f'{PRODUCTS}?page_size=1&page=2').json()
    assert paged['count'] == 3 and len(paged['items']) == 1


def test_review_endpoint_is_gated_and_audited():
    moderator = _make_user('cat-mod3@example.com', group='moderator')
    support = _make_user('cat-sup3@example.com', group='support')
    seller = _make_user('cat-seller3@example.com', is_staff=False)
    store = _store_for(seller)
    pending = _product(store, title='Review Me')
    reject_me = _product(store, title='Reject Me')

    mod = _client_for(moderator)

    # Support cannot act (oversight does not include catalog moderation).
    res = _client_for(support).post(
        f'{PRODUCTS}{pending.id}/review',
        {'decision': 'published'},
        content_type='application/json',
    )
    assert res.status_code == 403

    # A rejection without a reason is refused.
    res = mod.post(
        f'{PRODUCTS}{reject_me.id}/review',
        {'decision': 'rejected'},
        content_type='application/json',
    )
    assert res.status_code == 400

    # Publish flips the status and writes the audit row.
    res = mod.post(
        f'{PRODUCTS}{pending.id}/review',
        {'decision': 'published'},
        content_type='application/json',
    )
    assert res.status_code == 200
    pending.refresh_from_db()
    assert pending.status == Product.Status.PUBLISHED
    assert AuditLog.objects.filter(
        action='product_review_published',
        actor=moderator,
        object_id=str(pending.id),
    ).exists()

    # Reject stores the seller-visible reason and audits.
    res = mod.post(
        f'{PRODUCTS}{reject_me.id}/review',
        {'decision': 'rejected', 'reason': 'Counterfeit listing.'},
        content_type='application/json',
    )
    assert res.status_code == 200
    reject_me.refresh_from_db()
    assert reject_me.status == Product.Status.REJECTED
    assert reject_me.rejection_reason == 'Counterfeit listing.'
    assert AuditLog.objects.filter(action='product_review_rejected').exists()


def test_staff_takedown_requires_reason_and_is_audited():
    moderator = _make_user('cat-mod4@example.com', group='moderator')
    support = _make_user('cat-sup4@example.com', group='support')
    seller = _make_user('cat-seller4@example.com', is_staff=False)
    store = _store_for(seller)
    live = _product(store, title='Live Item', status=Product.Status.PUBLISHED)
    draft = _product(store, title='Draft Item')

    mod = _client_for(moderator)

    # Support cannot take products down.
    res = _client_for(support).post(
        f'{PRODUCTS}{live.id}/unpublish',
        {'reason': 'not allowed'},
        content_type='application/json',
    )
    assert res.status_code == 403

    # The reason is mandatory (whitespace does not count).
    res = mod.post(
        f'{PRODUCTS}{live.id}/unpublish',
        {'reason': '   '},
        content_type='application/json',
    )
    assert res.status_code == 400

    # Only published products can be taken down.
    res = mod.post(
        f'{PRODUCTS}{draft.id}/unpublish',
        {'reason': 'not live yet'},
        content_type='application/json',
    )
    assert res.status_code == 400

    # Happy path: status flips, reason stays seller-visible, audit row.
    res = mod.post(
        f'{PRODUCTS}{live.id}/unpublish',
        {'reason': 'Unverified safety claim in the description.'},
        content_type='application/json',
    )
    assert res.status_code == 200
    live.refresh_from_db()
    assert live.status == Product.Status.UNPUBLISHED
    assert live.rejection_reason == 'Unverified safety claim in the description.'
    assert AuditLog.objects.filter(
        action='product_unpublished',
        actor=moderator,
        object_id=str(live.id),
    ).exists()


def test_category_management_gated_creates_and_audits():
    moderator = _make_user('cat-mod5@example.com', group='moderator')
    ops = _make_user('cat-ops@example.com', group='operations')

    # Moderators do not own taxonomy (§4 matrix).
    assert _client_for(moderator).get(CATEGORIES).status_code == 403

    ops_client = _client_for(ops)
    res = ops_client.get(CATEGORIES)
    assert res.status_code == 200
    body = res.json()
    assert 'count' in body and 'items' in body

    res = ops_client.post(
        CATEGORIES,
        {'name': 'Home & Living', 'description': 'Nest goods.'},
        content_type='application/json',
    )
    assert res.status_code == 201, res.content
    parent = res.json()
    assert parent['slug'] == 'home-living'
    assert parent['product_count'] == 0
    assert AuditLog.objects.filter(action='category_created', actor=ops).exists()

    res = ops_client.post(
        CATEGORIES,
        {'name': 'Rugs', 'parent': parent['id'], 'position': 2, 'is_active': False},
        content_type='application/json',
    )
    assert res.status_code == 201
    child = res.json()
    assert child['parent'] == parent['id']
    assert child['is_active'] is False


def test_category_writes_refuse_cycles():
    ops = _make_user('cat-ops2@example.com', group='operations')
    client = _client_for(ops)

    parent = client.post(
        CATEGORIES, {'name': 'Apparel'}, content_type='application/json'
    ).json()
    child = client.post(
        CATEGORIES,
        {'name': 'Shirts', 'parent': parent['id']},
        content_type='application/json',
    ).json()

    # Self-parenting is refused.
    res = client.patch(
        f"{CATEGORIES}{parent['id']}/",
        {'parent': parent['id']},
        content_type='application/json',
    )
    assert res.status_code == 400
    assert 'own parent' in res.json()['detail']

    # A category cannot move under its own descendant.
    res = client.patch(
        f"{CATEGORIES}{parent['id']}/",
        {'parent': child['id']},
        content_type='application/json',
    )
    assert res.status_code == 400
    assert 'descendant' in res.json()['detail']

    # A legal rename still works and is audit-logged.
    res = client.patch(
        f"{CATEGORIES}{child['id']}/",
        {'name': 'Shirts & Blouses'},
        content_type='application/json',
    )
    assert res.status_code == 200
    assert res.json()['name'] == 'Shirts & Blouses'
    assert AuditLog.objects.filter(action='category_updated', actor=ops).exists()


def test_category_delete_refuses_non_empty_and_audits_success():
    ops = _make_user('cat-ops3@example.com', group='operations')
    seller = _make_user('cat-seller5@example.com', is_staff=False)
    store = _store_for(seller)
    client = _client_for(ops)

    parent = client.post(
        CATEGORIES, {'name': 'Garden'}, content_type='application/json'
    ).json()
    child = client.post(
        CATEGORIES,
        {'name': 'Seeds', 'parent': parent['id']},
        content_type='application/json',
    ).json()
    _product(store, title='Seed Pack', category_id=child['id'])

    # Children block the delete.
    res = client.delete(f"{CATEGORIES}{parent['id']}/")
    assert res.status_code == 400
    assert 'subcategories' in res.json()['detail']

    # Products block the delete.
    res = client.delete(f"{CATEGORIES}{child['id']}/")
    assert res.status_code == 400
    assert 'products' in res.json()['detail']

    # An empty leaf deletes; the audit row survives the object (§9).
    empty = client.post(
        CATEGORIES, {'name': 'Pots'}, content_type='application/json'
    ).json()
    res = client.delete(f"{CATEGORIES}{empty['id']}/")
    assert res.status_code == 204
    assert not Category.objects.filter(pk=empty['id']).exists()
    assert AuditLog.objects.filter(
        action='category_deleted', actor=ops, object_id=str(empty['id']),
    ).exists()


def test_brand_management_crud_and_audit():
    moderator = _make_user('cat-mod6@example.com', group='moderator')
    ops = _make_user('cat-ops4@example.com', group='operations')
    seller = _make_user('cat-seller6@example.com', is_staff=False)
    store = _store_for(seller)

    assert _client_for(moderator).get(BRANDS).status_code == 403

    client = _client_for(ops)
    res = client.post(
        BRANDS, {'name': 'Bamboo Works'}, content_type='application/json'
    )
    assert res.status_code == 201
    brand = res.json()
    assert brand['slug'] == 'bamboo-works'

    # Duplicate names are refused by the serializer.
    res = client.post(
        BRANDS, {'name': 'Bamboo Works'}, content_type='application/json'
    )
    assert res.status_code == 400

    # Deleting the label detaches products (FK SET_NULL) and audits.
    product = _product(store, title='Bamboo Basket', brand_id=brand['id'])
    res = client.delete(f"{BRANDS}{brand['id']}/")
    assert res.status_code == 204
    product.refresh_from_db()
    assert product.brand is None
    assert AuditLog.objects.filter(action='brand_created', actor=ops).exists()
    assert AuditLog.objects.filter(action='brand_deleted', actor=ops).exists()

    # Rename path.
    other = client.post(
        BRANDS, {'name': 'Rattan Co'}, content_type='application/json'
    ).json()
    res = client.patch(
        f"{BRANDS}{other['id']}/",
        {'name': 'Rattan & Co'},
        content_type='application/json',
    )
    assert res.status_code == 200
    assert res.json()['name'] == 'Rattan & Co'
    assert AuditLog.objects.filter(action='brand_updated', actor=ops).exists()
