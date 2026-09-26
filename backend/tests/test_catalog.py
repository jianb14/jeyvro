"""Phase 5 catalog gate tests — lifecycle, scoping, inventory safety.

Marketplace-catalog verification checklist drives these: variants own
price/stock (product price resolved server-side), search/filter/sort are
server-side + paginated, store scoping deny-paths are proven, images are
validated, and stock can never go negative.
"""
from decimal import Decimal

import pytest

from apps.catalog import services
from apps.catalog.models import (
    Brand,
    Category,
    Inventory,
    Product,
    ProductImage,
    StockMovement,
    Variant,
)
from apps.stores.models import Store

pytestmark = pytest.mark.django_db

REGISTER = '/api/v1/auth/register'
LOGIN = '/api/v1/auth/login'
LOGOUT = '/api/v1/auth/logout'
CATALOG = '/api/v1/catalog/products/'
MY_PRODUCTS = '/api/v1/catalog/my/products/'
MY_STOCK = '/api/v1/catalog/my/stock'
ADMIN_PRODUCTS = '/api/v1/catalog/admin/products/'

USER = {'email': 'catseller@example.com', 'password': 'Str0ng!Passw0rd',
        'first_name': 'Cata', 'last_name': 'Log'}
OTHER = {'email': 'catother@example.com', 'password': 'Str0ng!Passw0rd2'}
STAFF = {'email': 'catstaff@example.com', 'password': 'Str0ng!Passw0rd3'}


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
    from apps.accounts.models import User
    register(client, STAFF)
    grant_moderator(STAFF['email'])
    login(client, STAFF['email'], STAFF['password'])
    return User.objects.get(email=STAFF['email'])


def make_approved_seller_with_store(client):
    """Registers USER, applies, staff-approves; leaves USER logged in.

    Returns (user, store) — the Phase 4 happy path reused as a fixture.
    """
    register(client, USER)
    login(client, USER['email'], USER['password'])
    client.post(
        '/api/v1/stores/apply',
        {'store_name': 'Cata Log Store', 'store_description': 'x',
         'contact_phone': ''},
        content_type='application/json',
    )
    from apps.accounts.models import User
    user = User.objects.get(email=USER['email'])
    make_staff(client)
    application_id = client.get(
        '/api/v1/stores/admin/applications/'
    ).json()['items'][0]['id']
    review = client.post(
        f'/api/v1/stores/admin/applications/{application_id}/review',
        {'decision': 'approved'},
        content_type='application/json',
    )
    assert review.status_code == 200, review.content
    client.post(LOGOUT)
    login(client, USER['email'], USER['password'])
    return user, Store.objects.get(user=user)


def make_published_product(store, *, stock=10, price='299.00',
                           compare_at='399.00', title='Test Product'):
    product = Product.objects.create(
        store=store,
        title=title,
        base_price=Decimal(price),
        compare_at_price=Decimal(compare_at) if compare_at else None,
        status=Product.Status.PUBLISHED,
    )
    variant = Variant.objects.create(
        product=product, name='Default', price=Decimal(price),
        is_default=True,
    )
    services.ensure_inventory(variant, initial_on_hand=stock)
    return product, variant


def test_seller_creates_product_and_variant(client):
    user, store = make_approved_seller_with_store(client)
    creation = client.post(
        MY_PRODUCTS,
        {'title': 'Handwoven Basket', 'base_price': '349.00',
         'description': 'Woven basket.'},
        content_type='application/json',
    )
    assert creation.status_code == 201, creation.content
    product_id = creation.json()['id']
    assert creation.json()['status'] == Product.Status.DRAFT

    variant = client.post(
        f'{MY_PRODUCTS}{product_id}/variants/',
        {'price': '349.00', 'name': 'Large', 'initial_stock': 12},
        content_type='application/json',
    )
    assert variant.status_code == 201, variant.content
    body = variant.json()
    assert body['is_default'] is True
    assert body['inventory']['on_hand'] == 12
    assert body['inventory']['available'] == 12

    history = client.get(f'{MY_STOCK}?variant_id={body["id"]}')
    assert history.status_code == 200
    assert history.json()['count'] == 1  # initial movement recorded


def test_public_catalog_exposes_published_from_active_stores_only(client):
    _user, store = make_approved_seller_with_store(client)
    product, _variant = make_published_product(store)
    draft = Product.objects.create(
        store=store, title='Draft Item', base_price=Decimal('100.00'),
        status=Product.Status.DRAFT,
    )
    Variant.objects.create(
        product=draft, name='D', price=Decimal('100.00'), is_default=True
    )

    response = client.get(CATALOG)
    assert response.status_code == 200
    body = response.json()
    assert body['count'] == 1
    item = body['items'][0]
    assert item['title'] == 'Test Product'
    # Server-resolved truth: price/discount/stock come from the API (§6).
    assert Decimal(str(item['price'])) == Decimal('299.00')
    assert Decimal(str(item['originalPrice'])) == Decimal('399.00')
    assert item['discount'] == 25
    assert item['stock'] == 10


def test_search_filter_sort_server_side(client):
    _user, store = make_approved_seller_with_store(client)
    category = Category.objects.create(name='Home & Living')
    make_published_product(store, title='Bamboo Basket')
    published = make_published_product(
        store, title='Ceramic Plates', price='899.00',
        compare_at=None, stock=3,
    )[0]
    published.category = category
    published.save(update_fields=['category'])
    make_published_product(store, title='Abaca Tote')

    search = client.get(f'{CATALOG}?q=bamboo')
    assert {i['title'] for i in search.json()['items']} == {'Bamboo Basket'}

    filtered = client.get(f'{CATALOG}?category=home-living')
    assert {i['title'] for i in filtered.json()['items']} == {'Ceramic Plates'}

    sorted_prices = client.get(f'{CATALOG}?sort=price')
    prices = [Decimal(str(i['price'])) for i in sorted_prices.json()['items']]
    assert prices == sorted(prices)


def test_seller_cannot_touch_another_stores_product(client):
    _user, store = make_approved_seller_with_store(client)
    product, _variant = make_published_product(store)
    # A second, unrelated seller — their store scope must not see or touch
    # the first seller's products.
    register(client, OTHER)
    login(client, OTHER['email'], OTHER['password'])
    from apps.accounts.models import User
    other_user = User.objects.get(email=OTHER['email'])
    other_store = Store.objects.create(
        user=other_user, name='Other Shop', status=Store.Status.ACTIVE
    )
    other_user.is_seller = True
    other_user.save(update_fields=['is_seller', 'updated_at'])

    foreign = client.get(MY_PRODUCTS)
    assert foreign.status_code == 200
    assert foreign.json()['count'] == 0  # other stores' products invisible

    hijack = client.post(
        f'{MY_PRODUCTS}{product.id}/unpublish/',
        content_type='application/json',
    )
    assert hijack.status_code in (403, 404)  # deny path holds

    # And a plain customer (no store at all) is denied at the gate.
    register(client, {'email': 'plain@example.com',
                      'password': 'Str0ng!Passw0rd9'})
    login(client, 'plain@example.com', 'Str0ng!Passw0rd9')
    assert client.get(MY_PRODUCTS).status_code == 403


def test_stock_cannot_go_negative(client):
    _user, store = make_approved_seller_with_store(client)
    _product, variant = make_published_product(store, stock=5)
    from apps.accounts.models import User
    seller = User.objects.get(email=USER['email'])

    with pytest.raises(ValueError):
        services.adjust_stock(seller, variant, delta=-10)
    assert Inventory.objects.get(variant=variant).on_hand == 5  # rolled back

    # Reservation beyond availability is blocked.
    with pytest.raises(ValueError):
        services.reserve_stock(variant, 6)

    # Valid reservation + release round-trips.
    services.reserve_stock(variant, 3)
    assert Inventory.objects.get(variant=variant).available == 2
    services.release_stock(variant, 3)
    assert Inventory.objects.get(variant=variant).available == 5

    # Every change left an append-only movement row.
    assert StockMovement.objects.filter(variant=variant).count() == 3


def test_lifecycle_requires_staff_publish_with_audit(client):
    _user, store = make_approved_seller_with_store(client)
    product, _variant = make_published_product(
        store, title='Lifecycle Item', stock=4
    )
    from apps.accounts.models import User
    seller = User.objects.get(email=USER['email'])
    staff_user = User.objects.get(email=STAFF['email'])

    # Seller unpublishes, resubmits; staff approves; audit logged.
    services.unpublish_product(seller, product.id)
    product.refresh_from_db()
    assert product.status == Product.Status.UNPUBLISHED
    services.submit_for_review(seller, product.id)
    product.refresh_from_db()
    assert product.status == Product.Status.PENDING_REVIEW
    services.review_product(
        staff_user, product.id, decision=Product.Status.PUBLISHED
    )
    product.refresh_from_db()
    assert product.status == Product.Status.PUBLISHED
    from apps.audit.models import AuditLog
    assert AuditLog.objects.filter(
        action='product_review_published', object_id=str(product.id)
    ).exists()

    # Publishing again is invalid — the product is no longer pending.
    with pytest.raises(ValueError):
        services.review_product(
            staff_user, product.id, decision=Product.Status.PUBLISHED
        )


def _upload(content, name):
    from django.core.files.uploadedfile import SimpleUploadedFile
    return SimpleUploadedFile(name, content, content_type='image/png')


def test_image_upload_validates_content(client):
    _user, store = make_approved_seller_with_store(client)
    product, _variant = make_published_product(store, title='Image Product')
    png = b'\x89PNG\r\n\x1a\n' + b'\x00' * 24  # real PNG header + body
    fake = b'MZ\x90\x00' + b'A' * 32  # executable bytes disguised as .png

    good = client.post(
        f'{MY_PRODUCTS}{product.id}/images/',
        {'image': _upload(png, 'photo.png')}, format='multipart',
    )
    assert good.status_code == 201, good.content
    assert ProductImage.objects.filter(product=product).count() == 1

    bad = client.post(
        f'{MY_PRODUCTS}{product.id}/images/',
        {'image': _upload(fake, 'malware.png')}, format='multipart',
    )
    assert bad.status_code == 400
    assert bad.json()['error'] == 'invalid_image'
    assert ProductImage.objects.filter(product=product).count() == 1


def test_public_payload_carries_category_slug_and_images(client):
    """Phase 6 discovery: the public shape feeds the detail gallery and
    category links (images[] + category_slug)."""
    _user, store = make_approved_seller_with_store(client)
    category = Category.objects.create(name='Home & Living')
    product, _variant = make_published_product(store, title='Gallery Item')
    product.category = category
    product.save(update_fields=['category'])
    ProductImage.objects.create(product=product, image='products/gallery.png')

    response = client.get(f'{CATALOG}{product.slug}/')
    assert response.status_code == 200, response.content
    body = response.json()
    assert body['category'] == 'Home & Living'
    assert body['category_slug'] == 'home-living'
    assert len(body['images']) == 1
    assert body['images'][0]['image'].endswith('/media/products/gallery.png')
    assert body['primary_image'].endswith('/media/products/gallery.png')


def test_discount_sort_ranks_biggest_real_discount_first(client):
    """Phase 6 discovery: sort=discount is truthful — products without a
    reference price never rank as deals (nulls last)."""
    _user, store = make_approved_seller_with_store(client)
    make_published_product(store, title='No Deals', price='100.00', compare_at=None)
    make_published_product(store, title='Half Off', price='50.00', compare_at='100.00')
    make_published_product(store, title='Small Deal', price='90.00', compare_at='100.00')

    response = client.get(f'{CATALOG}?sort=discount')
    assert response.status_code == 200, response.content
    titles = [item['title'] for item in response.json()['items']]
    assert titles == ['Half Off', 'Small Deal', 'No Deals']

    # Page-size/page params keep the {count, items} envelope intact —
    # the browse UI paginates against `count`.
    paged = client.get(f'{CATALOG}?sort=discount&page_size=1&page=2')
    assert paged.json()['count'] == 3
    assert [i['title'] for i in paged.json()['items']] == ['Small Deal']