"""Phase 7 cart & wishlist gate tests — server truth, guest merge, privacy.

Marketplace-orders checklist drives these: the cart is server-side and
per-user (or per guest session), prices/stock are revalidated on every
read, invalid stock cannot be purchased, multi-seller carts group by
store, guest carts merge at login, and the wishlist stays private.
"""
from decimal import Decimal

import pytest
from django.test import Client

from apps.cart.models import Cart, CartItem, WishlistItem
from apps.catalog import services as catalog_services
from apps.catalog.models import Product, Variant
from apps.stores.models import Store

pytestmark = pytest.mark.django_db

REGISTER = '/api/v1/auth/register'
LOGIN = '/api/v1/auth/login'
LOGOUT = '/api/v1/auth/logout'
CART = '/api/v1/cart/'
CART_ITEMS = '/api/v1/cart/items'
WISHLIST = '/api/v1/wishlist/'

USER = {'email': 'cartseller@example.com', 'password': 'Str0ng!Passw0rd',
        'first_name': 'Cart', 'last_name': 'Seller'}
SHOPPER = {'email': 'shopper@example.com', 'password': 'Str0ng!Passw0rd2'}
OTHER = {'email': 'othershopper@example.com', 'password': 'Str0ng!Passw0rd3'}
STAFF = {'email': 'cartstaff@example.com', 'password': 'Str0ng!Passw0rd4'}


def register(client, payload):
    return client.post(REGISTER, payload, content_type='application/json')


def login(client, email, password):
    return client.post(
        LOGIN, {'email': email, 'password': password},
        content_type='application/json',
    )


def make_approved_seller_with_store(client, user=USER,
                                    store_name='Cart Log Store'):
    """Registers a seller, applies, staff-approves; leaves the seller in.

    Returns (user, store) — the Phase 4 happy path reused as a fixture.
    """
    register(client, user)
    login(client, user['email'], user['password'])
    client.post(
        '/api/v1/stores/apply',
        {'store_name': store_name, 'store_description': 'x',
         'contact_phone': ''},
        content_type='application/json',
    )
    from apps.accounts.models import User
    seller = User.objects.get(email=user['email'])
    register(client, STAFF)
    User.objects.filter(email=STAFF['email']).update(is_staff=True)
    login(client, STAFF['email'], STAFF['password'])
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
    login(client, user['email'], user['password'])
    return seller, Store.objects.get(user=seller)


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
    catalog_services.ensure_inventory(variant, initial_on_hand=stock)
    return product, variant


def add_to_cart(client, variant, quantity=1):
    return client.post(
        CART_ITEMS,
        {'variant_id': variant.id, 'quantity': quantity},
        content_type='application/json',
    )


def get_cart(client):
    return client.get(CART)


# --- 7.1 Cart: server-authoritative reads, validation, totals ---

def test_guest_cart_is_server_authoritative_across_requests(client):
    _seller, store = make_approved_seller_with_store(client)
    _product, variant = make_published_product(store)
    client.post(LOGOUT)

    added = add_to_cart(client, variant, 2)
    assert added.status_code == 200, added.content
    payload = added.json()
    assert payload['owner'] == 'guest'
    assert payload['totals'] == {
        'line_count': 1, 'item_count': 2, 'subtotal': 598.0, 'savings': 200.0,
    }
    item = payload['items'][0]
    assert item['price'] == 299.0           # server-resolved, never client-sent
    assert item['line_total'] == 598.0
    assert item['quantity'] == 2
    assert item['available'] == 10
    assert item['purchasable'] is True
    assert item['stock_limited'] is False

    # The cart survives the request boundary — same session, same server cart.
    again = get_cart(client).json()
    assert again['totals']['item_count'] == 2
    assert again['items'][0]['variant_id'] == variant.id


def test_add_to_cart_increments_existing_line(client):
    _seller, store = make_approved_seller_with_store(client)
    _product, variant = make_published_product(store)
    client.post(LOGOUT)

    add_to_cart(client, variant, 1)
    payload = add_to_cart(client, variant, 3).json()
    assert payload['totals'] == {
        'line_count': 1, 'item_count': 4,
        'subtotal': 1196.0, 'savings': 400.0,
    }


def test_stock_validation_blocks_oversell(client):
    _seller, store = make_approved_seller_with_store(client)
    _product, variant = make_published_product(store, stock=3)
    client.post(LOGOUT)

    too_many = add_to_cart(client, variant, 4)
    assert too_many.status_code == 400
    assert too_many.json()['detail'] == 'Only 3 left in stock.'

    assert add_to_cart(client, variant, 3).status_code == 200
    increment_past_stock = add_to_cart(client, variant, 1)
    assert increment_past_stock.status_code == 400
    assert increment_past_stock.json()['detail'] == 'Only 3 left in stock.'


def test_unavailable_products_cannot_be_added(client):
    _seller, store = make_approved_seller_with_store(client)
    product, variant = make_published_product(store)
    client.post(LOGOUT)

    product.status = Product.Status.DRAFT
    product.save(update_fields=['status'])
    rejected = add_to_cart(client, variant, 1)
    assert rejected.status_code == 400
    assert rejected.json()['detail'] == 'This product is no longer available.'

    product.status = Product.Status.PUBLISHED
    product.save(update_fields=['status'])
    store.status = Store.Status.SUSPENDED
    store.save(update_fields=['status'])
    rejected = add_to_cart(client, variant, 1)
    assert rejected.status_code == 400
    assert rejected.json()['detail'] == 'This product is no longer available.'

    assert client.post(
        CART_ITEMS, {'variant_id': 99999, 'quantity': 1},
        content_type='application/json',
    ).status_code == 404


def test_update_remove_and_clear_cart(client):
    _seller, store = make_approved_seller_with_store(client)
    _product, variant = make_published_product(store, stock=10)
    client.post(LOGOUT)

    item_id = add_to_cart(client, variant, 2).json()['items'][0]['id']

    updated = client.patch(
        f'{CART_ITEMS}/{item_id}',
        {'quantity': 5},
        content_type='application/json',
    )
    assert updated.status_code == 200
    assert updated.json()['totals']['item_count'] == 5

    invalid = client.patch(
        f'{CART_ITEMS}/{item_id}',
        {'quantity': 0},
        content_type='application/json',
    )
    assert invalid.status_code == 400
    assert 'field_errors' in invalid.json()

    over_stock = client.patch(
        f'{CART_ITEMS}/{item_id}',
        {'quantity': 11},   # over the 10 in stock, under the 99-per-line cap
        content_type='application/json',
    )
    assert over_stock.status_code == 400
    assert over_stock.json()['detail'] == 'Only 10 left in stock.'

    removed = client.delete(f'{CART_ITEMS}/{item_id}')
    assert removed.status_code == 200
    assert removed.json()['totals']['item_count'] == 0

    assert client.delete(f'{CART_ITEMS}/{item_id}').status_code == 404

    add_to_cart(client, variant, 1)
    add_to_cart(client, variant, 2)
    cleared = client.delete(CART)
    assert cleared.status_code == 200
    assert cleared.json()['items'] == []
    assert cleared.json()['totals']['item_count'] == 0
    assert CartItem.objects.count() == 0


def test_price_revalidation_reflects_variant_changes(client):
    _seller, store = make_approved_seller_with_store(client)
    _product, variant = make_published_product(store, price='299.00')
    client.post(LOGOUT)
    add_to_cart(client, variant, 2)

    variant.price = Decimal('250.00')
    variant.save(update_fields=['price'])

    payload = get_cart(client).json()
    assert payload['items'][0]['price'] == 250.0
    assert payload['items'][0]['line_total'] == 500.0
    assert payload['totals']['subtotal'] == 500.0


def test_multi_seller_cart_groups_by_store(client):
    _seller_a, store_a = make_approved_seller_with_store(client)
    _product_a, variant_a = make_published_product(
        store_a, title='Basket A', price='100.00', compare_at=None
    )
    # Second store, second seller — reuse the fixture with a fresh account.
    second = {'email': 'cartseller2@example.com', 'password': 'Str0ng!Passw0rd5'}
    _seller_b, store_b = make_approved_seller_with_store(
        client, user=second, store_name='Second Cart Store'
    )
    _product_b, variant_b = make_published_product(
        store_b, title='Tote B', price='250.00', compare_at=None
    )
    client.post(LOGOUT)

    add_to_cart(client, variant_a, 1)
    payload = add_to_cart(client, variant_b, 2).json()

    assert payload['totals']['line_count'] == 2
    assert payload['totals']['item_count'] == 3
    assert payload['totals']['subtotal'] == 600.0
    groups = payload['groups']
    assert len(groups) == 2
    by_store = {group['store_slug']: group for group in groups}
    assert by_store[store_a.slug]['item_count'] == 1
    assert by_store[store_a.slug]['subtotal'] == 100.0
    assert by_store[store_b.slug]['item_count'] == 2
    assert by_store[store_b.slug]['subtotal'] == 500.0
    assert by_store[store_b.slug]['store_name'] == 'Second Cart Store'


def test_guest_carts_are_isolated_per_session(client):
    _seller, store = make_approved_seller_with_store(client)
    _product, variant = make_published_product(store)
    client.post(LOGOUT)

    add_to_cart(client, variant, 2)

    other_guest = Client()
    assert get_cart(other_guest).json()['totals']['item_count'] == 0


# --- 7.1 Guest -> account merge at login ---

def test_guest_cart_merges_into_account_at_login(client):
    _seller, store = make_approved_seller_with_store(client)
    _product, variant = make_published_product(store)
    client.post(LOGOUT)

    add_to_cart(client, variant, 2)

    register(client, SHOPPER)
    response = login(client, SHOPPER['email'], SHOPPER['password'])
    assert response.status_code == 200

    payload = get_cart(client).json()
    assert payload['owner'] == 'user'
    assert payload['totals']['item_count'] == 2
    # The guest cart was folded in, not duplicated or orphaned.
    from apps.accounts.models import User
    user = User.objects.get(email=SHOPPER['email'])
    assert Cart.objects.filter(user=user).count() == 1
    assert Cart.objects.filter(user__isnull=True).count() == 0


def test_login_merge_sums_quantities_with_existing_account_cart(client):
    _seller, store = make_approved_seller_with_store(client)
    _product, variant = make_published_product(store, stock=10)
    client.post(LOGOUT)

    register(client, SHOPPER)
    login(client, SHOPPER['email'], SHOPPER['password'])
    add_to_cart(client, variant, 1)
    client.post(LOGOUT)

    add_to_cart(client, variant, 3)
    login(client, SHOPPER['email'], SHOPPER['password'])

    payload = get_cart(client).json()
    assert payload['owner'] == 'user'
    assert payload['items'][0]['quantity'] == 4
    assert payload['totals']['item_count'] == 4


# --- 7.2 Wishlist: private, idempotent, availability-aware ---

def test_wishlist_requires_authentication(client):
    _seller, store = make_approved_seller_with_store(client)
    product, _variant = make_published_product(store)
    client.post(LOGOUT)

    assert client.get(WISHLIST).status_code in (401, 403)
    assert client.post(
        WISHLIST, {'product_id': product.slug},
        content_type='application/json',
    ).status_code in (401, 403)


def test_wishlist_add_is_idempotent_and_removable(client):
    _seller, store = make_approved_seller_with_store(client)
    product, _variant = make_published_product(store)
    client.post(LOGOUT)
    register(client, SHOPPER)
    login(client, SHOPPER['email'], SHOPPER['password'])

    created = client.post(
        WISHLIST, {'product_id': product.slug},
        content_type='application/json',
    )
    assert created.status_code == 201
    assert created.json()['product']['slug'] == product.slug

    again = client.post(
        WISHLIST, {'product_id': product.slug},
        content_type='application/json',
    )
    assert again.status_code == 200       # idempotent — no duplicate row
    assert WishlistItem.objects.count() == 1

    listing = client.get(WISHLIST).json()
    assert listing['count'] == 1
    assert listing['items'][0]['product']['title'] == 'Test Product'
    assert listing['items'][0]['available'] is True

    removed = client.delete(f'{WISHLIST}items/{product.slug}')
    assert removed.status_code == 200
    assert removed.json()['count'] == 0
    assert WishlistItem.objects.count() == 0


def test_wishlist_is_private_per_customer(client):
    _seller, store = make_approved_seller_with_store(client)
    product, _variant = make_published_product(store)
    client.post(LOGOUT)

    register(client, SHOPPER)
    login(client, SHOPPER['email'], SHOPPER['password'])
    client.post(
        WISHLIST, {'product_id': product.slug},
        content_type='application/json',
    )
    client.post(LOGOUT)

    register(client, OTHER)
    login(client, OTHER['email'], OTHER['password'])
    assert client.get(WISHLIST).json()['count'] == 0

    # Removing someone else's saved product is a no-op, never a delete.
    client.delete(f'{WISHLIST}items/{product.slug}')
    assert WishlistItem.objects.count() == 1


def test_unpublished_products_cannot_be_wishlisted(client):
    _seller, store = make_approved_seller_with_store(client)
    product, _variant = make_published_product(store)
    client.post(LOGOUT)
    register(client, SHOPPER)
    login(client, SHOPPER['email'], SHOPPER['password'])

    product.status = Product.Status.DRAFT
    product.save(update_fields=['status'])
    assert client.post(
        WISHLIST, {'product_id': product.slug},
        content_type='application/json',
    ).status_code == 404


def test_wishlist_flags_products_that_left_the_catalog(client):
    _seller, store = make_approved_seller_with_store(client)
    product, _variant = make_published_product(store)
    client.post(LOGOUT)
    register(client, SHOPPER)
    login(client, SHOPPER['email'], SHOPPER['password'])
    client.post(
        WISHLIST, {'product_id': product.slug},
        content_type='application/json',
    )

    product.status = Product.Status.ARCHIVED
    product.save(update_fields=['status'])

    listing = client.get(WISHLIST).json()
    assert listing['count'] == 1
    assert listing['items'][0]['available'] is False



