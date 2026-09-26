"""Phase 12 gate tests — seller operations & seller dashboard.

Marketplace-sellers verification checklist drives these: a seller sees and
touches only their own store (deny paths proven), dashboard aggregates are
scoped to one store and computed from its own rows, product/variant
delete resolves to archive/deactivate when order history exists, stock
stays append-only, and seller order payloads obey the customer privacy
ladder without blocking fulfillment.
"""
from decimal import Decimal

import pytest
from django.test import Client

from apps.accounts.models import Address, User
from apps.cart.models import Cart
from apps.catalog import services as catalog_services
from apps.catalog.models import Product, Variant
from apps.orders import services as order_services
from apps.orders.models import OrderStatus, SellerOrder
from apps.payments.models import PaymentMethod
from apps.stores.models import Store

pytestmark = pytest.mark.django_db

MY_PRODUCTS = '/api/v1/catalog/my/products/'
MY_STOCK = '/api/v1/catalog/my/stock'
DASHBOARD = '/api/v1/stores/my/dashboard'


def _make_seller(name, email):
    user = User.objects.create_user(email=email, password='SellerPassword1!')
    user.is_seller = True
    user.save(update_fields=['is_seller'])
    store = Store.objects.create(
        user=user,
        name=name,
        slug=name.lower().replace(' ', '-'),
        shipping_flat_fee=Decimal('50.00'),
        status=Store.Status.ACTIVE,
    )
    return user, store


def _make_product(store, title, price=Decimal('200.00'), stock=10):
    product = Product.objects.create(
        store=store,
        title=title,
        base_price=Decimal(str(price)),
        status=Product.Status.PUBLISHED,
    )
    variant = Variant.objects.create(
        product=product,
        name='Default',
        price=Decimal(str(price)),
        is_default=True,
    )
    catalog_services.ensure_inventory(variant, initial_on_hand=stock)
    return product, variant


def _create_order(customer, store_variants, *, name='Customer Buyer',
                  phone='09170000000'):
    address = Address.objects.create(
        user=customer,
        full_name=name,
        phone=phone,
        line1='123 Test St',
        city='Manila',
        province='Metro Manila',
        postal_code='1000',
    )
    cart = Cart.objects.create(user=customer)
    for variant, qty in store_variants:
        cart.items.create(variant=variant, quantity=qty)
    return order_services.create_order(
        customer, address.id, payment_method=PaymentMethod.COD
    )

def _client_for(user):
    client = Client()
    client.force_login(user)
    return client


# --- 12.1 Dashboard ---------------------------------------------------------

def test_dashboard_aggregates_are_scoped_to_the_owning_store():
    seller1, store1 = _make_seller('Dash Store', 'dash1@example.com')
    seller2, store2 = _make_seller('Other Store', 'dash2@example.com')
    customer = User.objects.create_user(
        email='dashbuyer@example.com', password='BuyerPassword1!'
    )
    _, variant1 = _make_product(store1, 'Dash Item', stock=4)
    _, variant2 = _make_product(store2, 'Other Item', stock=100)

    _create_order(customer, [(variant1, 2), (variant2, 1)])
    so1 = SellerOrder.objects.get(store=store1)

    body = _client_for(seller1).get(DASHBOARD).json()
    assert body['store']['slug'] == store1.slug
    # 200 × 2 + 50 flat shipping, awaiting_payment still counts as a sale
    assert body['sales']['orders'] == 1
    assert body['sales']['units_sold'] == 2
    assert body['sales']['gross'] == float(so1.total)
    assert body['sales']['average_order_value'] == float(so1.total)
    assert body['sales']['last_30_days']['orders'] == 1
    # 4 on hand − 2 reserved = 2 available ≤ 5 default threshold
    assert body['inventory']['low_stock_count'] == 1
    assert body['inventory']['low_stock_items'][0]['variant_id'] == variant1.id
    assert [o['id'] for o in body['recent_orders']] == [so1.id]
    assert body['recent_orders'][0]['customer'] == 'Customer B.'
    assert body['recent_reviews'] == []
    assert body['orders']['open'] == 1

    other = _client_for(seller2).get(DASHBOARD).json()
    assert other['sales']['orders'] == 1
    assert other['sales']['units_sold'] == 1
    assert [o['id'] for o in other['recent_orders']] != [so1.id]


def test_dashboard_excludes_cancelled_orders_from_sales():
    seller, store = _make_seller('Cancel Store', 'dashcancel@example.com')
    customer = User.objects.create_user(
        email='cancelbuyer@example.com', password='BuyerPassword1!'
    )
    _, variant = _make_product(store, 'Cancel Item')
    order = _create_order(customer, [(variant, 1)])
    order_services.cancel_order(customer, order.number)

    body = _client_for(seller).get(DASHBOARD).json()
    assert body['sales']['orders'] == 0
    assert body['sales']['gross'] == 0.0
    assert body['orders']['by_status'].get(OrderStatus.CANCELLED) == 1


def test_dashboard_requires_a_seller_account():
    customer = User.objects.create_user(
        email='notseller@example.com', password='BuyerPassword1!'
    )
    res = _client_for(customer).get(DASHBOARD)
    assert res.status_code == 403
    assert _client_for(customer).get('/api/v1/catalog/my/products/').status_code == 403


def _client_for(user):
    client = Client()
    client.force_login(user)
    return client


# --- 12.2 Products, variants, bulk -----------------------------------------

def test_seller_updates_their_product_without_moving_status():
    seller, store = _make_seller('Edit Store', 'edit@example.com')
    product, _ = _make_product(store, 'Editable Item')
    slug_before = product.slug

    res = _client_for(seller).patch(
        f'{MY_PRODUCTS}{product.id}/',
        {'title': 'Retitled Item', 'base_price': '259.00',
         'status': Product.Status.ARCHIVED},
        content_type='application/json',
    )
    assert res.status_code == 200, res.content
    body = res.json()
    assert body['title'] == 'Retitled Item'
    assert float(body['base_price']) == 259.0
    # Status is service-owned: the payload edit is ignored (read-only field)
    assert body['status'] == Product.Status.PUBLISHED
    product.refresh_from_db()
    assert product.slug == slug_before  # the public identity stays stable


def test_archived_products_reject_edits_and_foreign_ids_404():
    seller, store = _make_seller('Arch Store', 'arch@example.com')
    stranger, _ = _make_seller('Stranger Store', 'stranger@example.com')
    product, _ = _make_product(store, 'Archived Item')
    product.status = Product.Status.ARCHIVED
    product.save(update_fields=['status'])

    res = _client_for(seller).patch(
        f'{MY_PRODUCTS}{product.id}/', {'title': 'Nope'},
        content_type='application/json',
    )
    assert res.status_code == 400
    assert res.json()['error'] == 'not_editable'

    # Another seller's product is a 404 — never an existence leak (§10)
    res = _client_for(stranger).patch(
        f'{MY_PRODUCTS}{product.id}/', {'title': 'Nope'},
        content_type='application/json',
    )
    assert res.status_code == 404
    assert _client_for(stranger).delete(f'{MY_PRODUCTS}{product.id}/').status_code == 404


def test_product_delete_hard_deletes_when_never_ordered():
    seller, store = _make_seller('Delete Store', 'delete@example.com')
    product, _ = _make_product(store, 'Fresh Item')

    res = _client_for(seller).delete(f'{MY_PRODUCTS}{product.id}/')
    assert res.status_code == 200, res.content
    assert res.json()['action'] == 'deleted'
    assert not Product.objects.filter(pk=product.id).exists()


def test_product_delete_archives_when_order_history_exists():
    seller, store = _make_seller('History Store', 'history@example.com')
    customer = User.objects.create_user(
        email='histbuyer@example.com', password='BuyerPassword1!'
    )
    product, variant = _make_product(store, 'Ordered Item')
    _create_order(customer, [(variant, 1)])

    res = _client_for(seller).delete(f'{MY_PRODUCTS}{product.id}/')
    assert res.status_code == 200, res.content
    body = res.json()
    assert body['action'] == 'archived'
    assert body['product']['status'] == Product.Status.ARCHIVED
    product.refresh_from_db()
    assert product.status == Product.Status.ARCHIVED


def test_variant_edit_delete_and_deactivate_rules():
    seller, store = _make_seller('Variant Store', 'variant@example.com')
    product, variant = _make_product(store, 'Variant Item')
    fresh = Variant.objects.create(
        product=product, name='Fresh', price=Decimal('10.00')
    )

    url = f'{MY_PRODUCTS}{product.id}/variants/{variant.id}/'
    res = _client_for(seller).patch(
        url, {'price': '249.00', 'name': 'Large'},
        content_type='application/json',
    )
    assert res.status_code == 200, res.content
    variant.refresh_from_db()
    assert float(variant.price) == 249.0
    assert variant.name == 'Large'

    # Never-ordered variant → hard delete
    res = _client_for(seller).delete(
        f'{MY_PRODUCTS}{product.id}/variants/{fresh.id}/'
    )
    assert res.status_code == 200
    assert res.json()['action'] == 'deleted'
    assert not Variant.objects.filter(pk=fresh.pk).exists()

    # Ordered variant → deactivates instead of dying to PROTECT
    customer = User.objects.create_user(
        email='varbuyer@example.com', password='BuyerPassword1!'
    )
    _create_order(customer, [(variant, 1)])
    res = _client_for(seller).patch(
        url, {'is_active': False}, content_type='application/json'
    )
    assert res.status_code == 200, res.content
    variant.refresh_from_db()
    assert variant.is_active is False

    res = _client_for(seller).delete(url)
    assert res.status_code == 200
    assert res.json()['action'] == 'deactivated'
    variant.refresh_from_db()
    assert variant.is_active is False



def test_bulk_lifecycle_actions_report_per_id():
    seller, store = _make_seller('Bulk Store', 'bulk@example.com')
    other_seller, _ = _make_seller('Bulk Other', 'bulkother@example.com')
    draft, _ = _make_product(store, 'Bulk Draft Item')
    draft.status = Product.Status.DRAFT
    draft.save(update_fields=['status'])
    published, _ = _make_product(store, 'Bulk Published Item')
    client = _client_for(seller)

    res = client.post(
        f'{MY_PRODUCTS}bulk/',
        {'action': 'submit', 'ids': [draft.id, 999999]},
        content_type='application/json',
    )
    assert res.status_code == 200, res.content
    results = {row['id']: row for row in res.json()['results']}
    assert results[draft.id]['ok'] is True
    assert results[999999]['ok'] is False
    draft.refresh_from_db()
    assert draft.status == Product.Status.PENDING_REVIEW

    res = client.post(
        f'{MY_PRODUCTS}bulk/',
        {'action': 'unpublish', 'ids': [published.id]},
        content_type='application/json',
    )
    assert res.json()['results'][0]['ok'] is True
    published.refresh_from_db()
    assert published.status == Product.Status.UNPUBLISHED

    # Another seller cannot act on these ids — the batch reports failures
    res = _client_for(other_seller).post(
        f'{MY_PRODUCTS}bulk/',
        {'action': 'archive', 'ids': [published.id]},
        content_type='application/json',
    )
    assert res.json()['results'][0]['ok'] is False

    res = client.post(
        f'{MY_PRODUCTS}bulk/', {'action': 'explode', 'ids': [1]},
        content_type='application/json',
    )
    assert res.status_code == 400


# --- 12.3 Inventory --------------------------------------------------------

def test_inventory_list_low_stock_filter_and_threshold():
    seller, store = _make_seller('Stock Store', 'stock@example.com')
    _, healthy = _make_product(store, 'Healthy Item', stock=50)
    _, scarce = _make_product(store, 'Scarce Item', stock=3)

    client = _client_for(seller)
    body = client.get(MY_STOCK).json()
    assert body['count'] == 2
    rows = {row['variant_id']: row for row in body['items']}
    assert rows[scarce.id]['inventory']['available'] == 3
    assert rows[scarce.id]['inventory']['low_stock'] is True
    assert rows[healthy.id]['inventory']['low_stock'] is False
    assert rows[scarce.id]['product_title'] == 'Scarce Item'

    low = client.get(f'{MY_STOCK}?low_stock=1').json()
    assert low['count'] == 1
    assert low['items'][0]['variant_id'] == scarce.id

    # Lower the alert level below current stock → alert clears (§12.3)
    res = client.post(
        MY_STOCK, {'variant_id': scarce.id, 'threshold': 2},
        content_type='application/json',
    )
    assert res.status_code == 200, res.content
    assert client.get(f'{MY_STOCK}?low_stock=1').json()['count'] == 0


def test_stock_adjustment_appends_movement_and_scopes_history():
    seller, store = _make_seller('Move Store', 'move@example.com')
    _, variant = _make_product(store, 'Moving Item', stock=10)
    client = _client_for(seller)

    res = client.post(
        MY_STOCK, {'variant_id': variant.id, 'delta': -4, 'note': 'shrinkage'},
        content_type='application/json',
    )
    assert res.status_code == 200, res.content
    variant.refresh_from_db()
    assert variant.inventory.on_hand == 6

    history = client.get(f'{MY_STOCK}?variant_id={variant.id}').json()
    assert history['count'] == 2  # initial + adjustment
    assert history['items'][0]['quantity_delta'] == -4

    # Another seller can neither read nor move this stock (deny path)
    other, _ = _make_seller('Move Other', 'moveother@example.com')
    other_client = _client_for(other)
    assert other_client.get(
        f'{MY_STOCK}?variant_id={variant.id}'
    ).status_code == 404
    res = other_client.post(
        MY_STOCK, {'variant_id': variant.id, 'delta': 5},
        content_type='application/json',
    )
    assert res.status_code == 404


# --- 12.4 / 12.5 Seller orders: fulfillment flags + privacy ladder ---------

def test_seller_order_privacy_ladder_and_action_flags():
    seller, store = _make_seller('Privacy Store', 'privacy@example.com')
    customer = User.objects.create_user(
        email='privbuyer@example.com', password='BuyerPassword1!'
    )
    _, variant = _make_product(store, 'Private Item')
    order = _create_order(customer, [(variant, 2)])
    so = order.seller_orders.get(store=store)
    client = _client_for(seller)

    body = client.get(f'/api/v1/seller/orders/{so.id}/').json()
    assert body['order_number'] == order.number
    assert body['item_count'] == 2
    # Pre-acceptance: masked label, masked phone, no street address,
    # and never an email (§12.5)
    assert body['customer']['name'] == 'Customer B.'
    assert body['customer']['phone'] == '\u2022' * 7 + '0000'
    assert body['customer']['address'] is None
    assert body['customer']['revealed'] is False
    assert 'email' not in body['customer']
    assert body['payment'] == {
        'method': 'cod', 'method_label': 'Cash on Delivery',
        'status': 'pending', 'paid': False,
    }
    assert body['can_process'] is True
    assert body['can_pack'] is True
    assert body['can_ship'] is True

    # Accepting the order unlocks exactly what shipping needs
    body = client.post(f'/api/v1/seller/orders/{so.id}/process').json()
    assert body['customer']['revealed'] is True
    assert body['customer']['name'] == 'Customer Buyer'
    assert body['customer']['phone'] == '09170000000'
    assert '123 Test St' in body['customer']['address']
    assert body['can_process'] is False
    assert body['can_pack'] is True

    body = client.post(f'/api/v1/seller/orders/{so.id}/pack').json()
    assert body['can_pack'] is False
    assert body['can_ship'] is True

    res = client.post(
        f'/api/v1/seller/orders/{so.id}/ship', {'carrier': 'manual'},
        content_type='application/json',
    )
    assert res.status_code == 201, res.content
    body = client.get(f'/api/v1/seller/orders/{so.id}/').json()
    assert body['can_ship'] is False  # every item is already on a parcel
    assert body['shipments'][0]['tracking_number'].startswith('JVTRK-')
    so.refresh_from_db()
    assert so.status == OrderStatus.SHIPPED


def test_seller_order_list_search_status_filter_and_isolation():
    seller, store = _make_seller('Search Store', 'search@example.com')
    other_seller, other_store = _make_seller(
        'Search Other', 'searchother@example.com'
    )
    customer = User.objects.create_user(
        email='searchbuyer@example.com', password='BuyerPassword1!'
    )
    _, variant = _make_product(store, 'Searchable Item')
    _, other_variant = _make_product(other_store, 'Hidden Item')
    order = _create_order(customer, [(variant, 1), (other_variant, 1)])

    client = _client_for(seller)
    rows = client.get('/api/v1/seller/orders/').json()
    assert rows['count'] == 1  # the other store's slice never appears

    by_number = client.get(
        f'/api/v1/seller/orders/?q={order.number}'
    ).json()
    assert by_number['count'] == 1
    by_title = client.get('/api/v1/seller/orders/?q=Searchable').json()
    assert by_title['count'] == 1
    hidden = client.get('/api/v1/seller/orders/?q=Hidden+Item').json()
    assert hidden['count'] == 0

    filtered = client.get(
        '/api/v1/seller/orders/?status=awaiting_payment'
    ).json()
    assert filtered['count'] == 1

    # Cross-store detail stays a 404 for the other seller
    so_other = order.seller_orders.get(store=other_store)
    assert _client_for(seller).get(
        f'/api/v1/seller/orders/{so_other.id}/'
    ).status_code == 404

