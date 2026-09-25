"""Phase 8 gate tests — checkout, shipping, order creation, inventory.

Marketplace-orders checklist drives these: totals are always recomputed
server-side (client input can never influence money), invalid/stale lines
cannot check out, multi-seller carts produce correct per-store orders,
snapshots are immutable, and cancelling releases the reservation again.
The concurrent last-unit race has its own file (test_checkout_race.py).

Phase 9 update: checkout now creates the order's payment record and the
order starts at `awaiting_payment` (COD is the default method) — the
payment gates live in test_payments*.py.
"""
from decimal import Decimal

import pytest
from django.test import Client

from apps.accounts.models import Address, User
from apps.audit.models import AuditLog
from apps.cart.models import Cart
from apps.catalog import services as catalog_services
from apps.catalog.models import Inventory, Product, StockMovement, Variant
from apps.orders.models import Order, OrderItem, SellerOrder
from apps.stores.models import Store

pytestmark = pytest.mark.django_db

REGISTER = '/api/v1/auth/register'
LOGIN = '/api/v1/auth/login'
LOGOUT = '/api/v1/auth/logout'
ADDRESSES = '/api/v1/auth/addresses/'
CHECKOUT = '/api/v1/checkout/'
CHECKOUT_ORDERS = '/api/v1/checkout/orders'
ORDERS = '/api/v1/orders/'
CART_ITEMS = '/api/v1/cart/items'

CUSTOMER = {'email': 'checkoutbuyer@example.com', 'password': 'Str0ng!Passw0rd'}
OTHER = {'email': 'checkoutother@example.com', 'password': 'Str0ng!Passw0rd2'}

ADDRESS_PAYLOAD = {
    'full_name': 'Bianca Buyer',
    'phone': '09171234567',
    'line1': '12 Mabini Street',
    'line2': 'Unit 4B',
    'city': 'Quezon City',
    'province': 'Metro Manila',
    'postal_code': '1100',
}


def register(client, payload):
    return client.post(REGISTER, payload, content_type='application/json')


def login(client, email, password):
    return client.post(
        LOGIN, {'email': email, 'password': password},
        content_type='application/json',
    )


def make_active_store(email, name, *, fee='0.00', threshold=None):
    """Direct ORM setup — Phase 4 flows are covered by test_stores.py."""
    user = User.objects.create_user(email=email, password='Str0ng!Passw0rd')
    store = Store.objects.create(
        user=user,
        name=name,
        status=Store.Status.ACTIVE,
        shipping_flat_fee=Decimal(fee),
        free_shipping_threshold=(
            Decimal(threshold) if threshold is not None else None
        ),
    )
    return user, store


def make_product(store, *, title='Test Product', price='299.00',
                 compare_at='399.00', stock=10, variant_name='Default'):
    product = Product.objects.create(
        store=store,
        title=title,
        base_price=Decimal(price),
        compare_at_price=Decimal(compare_at) if compare_at else None,
        status=Product.Status.PUBLISHED,
    )
    variant = Variant.objects.create(
        product=product, name=variant_name, price=Decimal(price),
        is_default=True,
    )
    catalog_services.ensure_inventory(variant, initial_on_hand=stock)
    return product, variant


def make_customer(client, user=CUSTOMER, *, with_address=True):
    """Registers + logs in the buyer; returns their default address id."""
    register(client, user)
    login(client, user['email'], user['password'])
    if not with_address:
        return None
    response = client.post(
        ADDRESSES, ADDRESS_PAYLOAD, content_type='application/json'
    )
    assert response.status_code == 201, response.content
    return response.json()['id']


def add_to_cart(client, variant, quantity=1):
    response = client.post(
        CART_ITEMS,
        {'variant_id': variant.id, 'quantity': quantity},
        content_type='application/json',
    )
    assert response.status_code == 200, response.content
    return response


# --- 8.2 Checkout preview (server-computed shipping + totals) ---

def test_checkout_preview_computes_shipping_and_totals_server_side(client):
    _seller, store = make_active_store(
        'previewseller@example.com', 'Preview Store', fee='50.00'
    )
    _product, variant = make_product(store, price='299.00', compare_at='399.00')
    make_customer(client)
    add_to_cart(client, variant, quantity=2)

    preview = client.get(CHECKOUT)
    assert preview.status_code == 200, preview.content
    body = preview.json()

    assert body['checkout_ready'] is True
    assert body['issues'] == []
    group = body['groups'][0]
    assert group['store_name'] == 'Preview Store'
    assert group['subtotal'] == 598.0
    assert group['shipping_fee'] == 50.0
    assert group['free_shipping'] is False

    totals = body['totals']
    assert totals['subtotal'] == 598.0
    assert totals['savings'] == 200.0
    assert totals['shipping_total'] == 50.0
    assert totals['tax_total'] == 0.0
    assert totals['grand_total'] == 648.0


def test_free_shipping_threshold_waives_the_flat_fee(client):
    _seller, store = make_active_store(
        'freeshipseller@example.com', 'Free Ship Store',
        fee='50.00', threshold='500.00',
    )
    _product, variant = make_product(store, price='299.00')
    make_customer(client)
    add_to_cart(client, variant, quantity=2)  # 598.00 >= 500.00

    body = client.get(CHECKOUT).json()
    group = body['groups'][0]
    assert group['subtotal'] == 598.0
    assert group['shipping_fee'] == 0.0
    assert group['free_shipping'] is True
    assert body['totals']['shipping_total'] == 0.0
    assert body['totals']['grand_total'] == 598.0


def test_threshold_below_subtotal_keeps_the_flat_fee(client):
    _seller, store = make_active_store(
        'thresholdseller@example.com', 'Threshold Store',
        fee='50.00', threshold='900.00',
    )
    _product, variant = make_product(store, price='299.00')
    make_customer(client)
    add_to_cart(client, variant, quantity=1)  # 299.00 < 900.00

    body = client.get(CHECKOUT).json()
    assert body['groups'][0]['shipping_fee'] == 50.0
    assert body['groups'][0]['free_shipping'] is False
    assert body['totals']['grand_total'] == 349.0


def test_guests_cannot_preview_or_place_orders(client):
    _seller, store = make_active_store('guardseller@example.com', 'Guard Store')
    _product, variant = make_product(store)
    client.post(
        CART_ITEMS, {'variant_id': variant.id, 'quantity': 1},
        content_type='application/json',
    )

    assert client.get(CHECKOUT).status_code in (401, 403)
    assert client.post(
        CHECKOUT_ORDERS, {'address_id': 1}, content_type='application/json'
    ).status_code in (401, 403)
    assert Order.objects.count() == 0


# --- 8.3 Order creation (snapshots, revalidation, no client math) ---

def test_client_money_fields_are_ignored_not_trusted(client):
    _seller, store = make_active_store(
        'trustseller@example.com', 'Trust Store', fee='50.00'
    )
    _product, variant = make_product(store, price='299.00')
    address_id = make_customer(client)
    add_to_cart(client, variant, quantity=1)

    # A hostile client tries to set its own prices and totals — the API
    # accepts only `address_id`, everything else is recomputed (§6).
    response = client.post(
        CHECKOUT_ORDERS,
        {
            'address_id': address_id,
            'subtotal': 1,
            'shipping_total': 0,
            'grand_total': 1,
            'unit_price': 1,
        },
        content_type='application/json',
    )
    assert response.status_code == 201, response.content
    body = response.json()
    assert body['totals']['subtotal'] == 299.0
    assert body['totals']['shipping_total'] == 50.0
    assert body['totals']['grand_total'] == 349.0
    item = body['seller_orders'][0]['items'][0]
    assert item['unit_price'] == 299.0


def test_price_change_after_cart_is_revalidated_at_checkout(client):
    _seller, store = make_active_store('priceseller@example.com', 'Price Store')
    _product, variant = make_product(store, price='299.00')
    address_id = make_customer(client)
    add_to_cart(client, variant, quantity=1)

    # The seller raises the price after the item was added to the cart.
    variant.price = Decimal('349.00')
    variant.save(update_fields=['price', 'updated_at'])

    preview = client.get(CHECKOUT).json()
    assert preview['totals']['subtotal'] == 349.0

    response = client.post(
        CHECKOUT_ORDERS, {'address_id': address_id},
        content_type='application/json',
    )
    assert response.status_code == 201, response.content
    body = response.json()
    assert body['totals']['subtotal'] == 349.0
    assert body['seller_orders'][0]['items'][0]['unit_price'] == 349.0


def test_unpublished_product_blocks_checkout_without_partial_order(client):
    _seller, store = make_active_store('draftseller@example.com', 'Draft Store')
    product, variant = make_product(store, stock=10)
    address_id = make_customer(client)
    add_to_cart(client, variant, quantity=2)

    product.status = Product.Status.DRAFT
    product.save(update_fields=['status', 'updated_at'])

    response = client.post(
        CHECKOUT_ORDERS, {'address_id': address_id},
        content_type='application/json',
    )
    assert response.status_code == 400, response.content
    assert response.json()['error'] == 'line_unavailable'
    assert Order.objects.count() == 0

    # The cart is untouched so the customer can fix the line.
    inventory = Inventory.objects.get(variant=variant)
    assert inventory.reserved == 0
    assert Cart.objects.get(user__email=CUSTOMER['email']).items.count() == 1


def test_stock_shortfall_blocks_checkout_and_reserves_nothing(client):
    _seller, store = make_active_store('stockseller@example.com', 'Stock Store')
    _product, variant = make_product(store, stock=5)
    address_id = make_customer(client)
    add_to_cart(client, variant, quantity=5)

    # Another checkout reserves most of the stock between add-to-cart and
    # checkout — only 2 units remain for a 5-unit line.
    catalog_services.reserve_stock(variant, 3)

    preview = client.get(CHECKOUT).json()
    assert preview['checkout_ready'] is False
    assert preview['issues'][0]['reason'].startswith('Only')

    response = client.post(
        CHECKOUT_ORDERS, {'address_id': address_id},
        content_type='application/json',
    )
    assert response.status_code == 400, response.content
    assert response.json()['error'] == 'insufficient_stock'
    assert Order.objects.count() == 0
    # Only the earlier reservation exists — the failed checkout added none.
    assert Inventory.objects.get(variant=variant).reserved == 3


def test_checkout_requires_an_address_from_the_owner(client):
    _seller, store = make_active_store('addrsseller@example.com', 'Address Store')
    _product, variant = make_product(store)
    make_customer(client)  # the buyer's own address is created
    add_to_cart(client, variant, quantity=1)

    other = User.objects.create_user(email='thirdparty@example.com', password='x')
    other_address = Address.objects.create(
        user=other, full_name='Someone Else', phone='0900', line1='9 Road',
        city='Cebu City', province='Cebu', postal_code='6000',
    )

    response = client.post(
        CHECKOUT_ORDERS, {'address_id': other_address.id},
        content_type='application/json',
    )
    assert response.status_code == 400, response.content
    assert response.json()['error'] == 'invalid_address'
    assert Order.objects.count() == 0

    missing = client.post(
        CHECKOUT_ORDERS, {'address_id': 99999},
        content_type='application/json',
    )
    assert missing.status_code == 400
    assert missing.json()['error'] == 'invalid_address'


def test_empty_cart_cannot_checkout(client):
    _seller, store = make_active_store('emptyseller@example.com', 'Empty Store')
    _product, _variant = make_product(store)
    address_id = make_customer(client)

    preview = client.get(CHECKOUT).json()
    assert preview['checkout_ready'] is False
    assert preview['items'] == []

    response = client.post(
        CHECKOUT_ORDERS, {'address_id': address_id},
        content_type='application/json',
    )
    assert response.status_code == 400
    assert response.json()['error'] == 'empty_cart'
    assert Order.objects.count() == 0


def test_multi_seller_order_creates_per_store_seller_orders(client):
    _seller_a, store_a = make_active_store(
        'seller-a@example.com', 'Store A', fee='50.00'
    )
    _seller_b, store_b = make_active_store(
        'seller-b@example.com', 'Store B', fee='80.00', threshold='200.00'
    )
    _product_a, variant_a = make_product(
        store_a, title='Basket', price='100.00', compare_at=None
    )
    _product_b, variant_b = make_product(
        store_b, title='Weave', price='100.00', compare_at=None
    )
    address_id = make_customer(client)
    add_to_cart(client, variant_a, quantity=2)   # 200.00 → fee 50 applies
    add_to_cart(client, variant_b, quantity=3)   # 300.00 → free shipping

    response = client.post(
        CHECKOUT_ORDERS, {'address_id': address_id},
        content_type='application/json',
    )
    assert response.status_code == 201, response.content
    body = response.json()

    assert body['number'].startswith('JV-')
    assert body['status'] == 'awaiting_payment'  # Phase 9: money is now due
    # Every order carries its server-computed payment record (§6 v1.8).
    assert body['payment']['method'] == 'cod'
    assert body['payment']['status'] == 'pending'
    assert body['payment']['amount'] == 550.0
    assert body['totals'] == {
        'subtotal': 500.0,
        'shipping_total': 50.0,
        'savings_total': 0.0,
        'tax_total': 0.0,
        'grand_total': 550.0,
    }

    slices = {so['store_name']: so for so in body['seller_orders']}
    assert set(slices) == {'Store A', 'Store B'}
    assert slices['Store A']['subtotal'] == 200.0
    assert slices['Store A']['shipping_fee'] == 50.0
    assert slices['Store A']['total'] == 250.0
    assert slices['Store B']['subtotal'] == 300.0
    assert slices['Store B']['shipping_fee'] == 0.0
    assert slices['Store B']['total'] == 300.0
    assert slices['Store A']['items'][0]['title'] == 'Basket'
    assert slices['Store B']['items'][0]['title'] == 'Weave'

    assert Order.objects.count() == 1
    assert SellerOrder.objects.count() == 2
    assert OrderItem.objects.count() == 2

    # The cart was cleared inside the same transaction.
    assert Cart.objects.get(user__email=CUSTOMER['email']).items.count() == 0


def test_checkout_reserves_stock_transactionally(client):
    _seller, store = make_active_store('reserveseller@example.com', 'Reserve Store')
    _product, variant = make_product(store, stock=10)
    address_id = make_customer(client)
    add_to_cart(client, variant, quantity=2)

    response = client.post(
        CHECKOUT_ORDERS, {'address_id': address_id},
        content_type='application/json',
    )
    assert response.status_code == 201, response.content

    inventory = Inventory.objects.get(variant=variant)
    assert inventory.on_hand == 10
    assert inventory.reserved == 2
    assert inventory.available == 8
    assert StockMovement.objects.filter(
        variant=variant,
        reason=StockMovement.Reason.RESERVE,
        note='reserved 2',
    ).exists()
    assert AuditLog.objects.filter(action='order.placed').exists()


def test_order_snapshots_are_immutable(client):
    _seller, store = make_active_store('snapseller@example.com', 'Snap Store')
    product, variant = make_product(
        store, title='Original Title', price='299.00', compare_at='399.00'
    )
    address_id = make_customer(client)
    add_to_cart(client, variant, quantity=2)

    response = client.post(
        CHECKOUT_ORDERS, {'address_id': address_id},
        content_type='application/json',
    )
    assert response.status_code == 201, response.content
    number = response.json()['number']

    # Life goes on after the purchase: rename, re-price, edit the address.
    product.title = 'Renamed Later'
    product.save(update_fields=['title', 'updated_at'])
    variant.price = Decimal('999.00')
    variant.save(update_fields=['price', 'updated_at'])
    address = Address.objects.get(pk=address_id)
    address.line1 = 'Moved Somewhere Else'
    address.save(update_fields=['line1', 'updated_at'])
    store.name = 'Renamed Store'
    store.save(update_fields=['name', 'updated_at'])

    body = client.get(f'{ORDERS}{number}/').json()
    assert body['totals']['subtotal'] == 598.0
    assert body['shipping_address']['line1'] == ADDRESS_PAYLOAD['line1']
    slice_ = body['seller_orders'][0]
    assert slice_['store_name'] == 'Snap Store'
    item = slice_['items'][0]
    assert item['title'] == 'Original Title'
    assert item['unit_price'] == 299.0
    assert item['compare_at_price'] == 399.0
    assert item['line_total'] == 598.0


def test_cancel_releases_the_reservation(client):
    _seller, store = make_active_store('cancelseller@example.com', 'Cancel Store')
    _product, variant = make_product(store, stock=10)
    address_id = make_customer(client)
    add_to_cart(client, variant, quantity=3)

    response = client.post(
        CHECKOUT_ORDERS, {'address_id': address_id},
        content_type='application/json',
    )
    number = response.json()['number']
    assert Inventory.objects.get(variant=variant).reserved == 3

    cancelled = client.post(f'{ORDERS}{number}/cancel')
    assert cancelled.status_code == 200, cancelled.content
    body = cancelled.json()
    assert body['status'] == 'cancelled'
    assert {so['status'] for so in body['seller_orders']} == {'cancelled'}

    inventory = Inventory.objects.get(variant=variant)
    assert inventory.reserved == 0
    assert inventory.available == 10
    assert StockMovement.objects.filter(
        variant=variant,
        reason=StockMovement.Reason.RELEASE,
        note='released 3',
    ).exists()
    assert AuditLog.objects.filter(action='order.cancelled').exists()

    # A cancelled order can never be cancelled twice.
    again = client.post(f'{ORDERS}{number}/cancel')
    assert again.status_code == 400
    assert again.json()['error'] == 'not_cancellable'


def test_orders_are_private_to_their_owner(client):
    _seller, store = make_active_store('privseller@example.com', 'Priv Store')
    _product, variant = make_product(store)
    address_id = make_customer(client)
    add_to_cart(client, variant, quantity=1)
    number = client.post(
        CHECKOUT_ORDERS, {'address_id': address_id},
        content_type='application/json',
    ).json()['number']

    assert client.get(ORDERS).json()['count'] == 1
    assert client.get(ORDERS).json()['items'][0]['number'] == number

    client.post(LOGOUT)
    make_customer(client, OTHER)

    listing = client.get(ORDERS).json()
    assert listing['count'] == 0
    assert client.get(f'{ORDERS}{number}/').status_code == 404
    assert client.post(f'{ORDERS}{number}/cancel').status_code == 404
    assert Order.objects.get(number=number).status == Order.Status.AWAITING_PAYMENT



