"""Phase 11 gate tests — customer account & order management.

Roadmap Phase 11 gate, tested here:
1. Order history is owner-scoped and paginated ({count, items} envelope).
2. Order detail is owner-scoped (no IDOR) and renders immutable snapshots —
   the receipt data — even after the catalog or the address book changes.
3. The order timeline comes from the order's own audit rows, whitelisted.
4. Reorder re-validates live availability and reports skipped lines.
5. Request intake is server-verified (delivered slice / captured money /
   open order), de-duplicated, and withdrawable by its owner only.
6. Cancellation eligibility (`can_cancel`) is the server's verdict.
"""
from decimal import Decimal

import pytest
from django.test import Client

from apps.accounts.models import Address, User
from apps.cart.models import CartItem
from apps.catalog import services as catalog_services
from apps.catalog.models import Product, Variant
from apps.orders import services as order_services
from apps.orders.models import Order, OrderStatus, ShipmentStatus
from apps.payments.models import Payment, PaymentStatus
from apps.stores.models import Store

pytestmark = pytest.mark.django_db

REGISTER = '/api/v1/auth/register'
LOGIN = '/api/v1/auth/login'
ADDRESSES = '/api/v1/auth/addresses/'
CART_ITEMS = '/api/v1/cart/items'
CHECKOUT_ORDERS = '/api/v1/checkout/orders'
ORDERS = '/api/v1/orders/'

CUSTOMER = {'email': 'accountbuyer@example.com', 'password': 'Str0ng!Passw0rd'}
OTHER = {'email': 'accountother@example.com', 'password': 'Str0ng!Passw0rd2'}

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


def make_store(email, name, *, fee='50.00'):
    user = User.objects.create_user(email=email, password='Str0ng!Passw0rd')
    store = Store.objects.create(
        user=user,
        name=name,
        status=Store.Status.ACTIVE,
        shipping_flat_fee=Decimal(fee),
    )
    return user, store


def make_product(store, *, title='Test Product', price='299.00', stock=10):
    product = Product.objects.create(
        store=store,
        title=title,
        base_price=Decimal(price),
        status=Product.Status.PUBLISHED,
    )
    variant = Variant.objects.create(
        product=product, name='Default', price=Decimal(price), is_default=True
    )
    catalog_services.ensure_inventory(variant, initial_on_hand=stock)
    return product, variant


def make_customer(client, user=CUSTOMER):
    """Registers + logs in the buyer on `client`; returns their address id."""
    register(client, user)
    login(client, user['email'], user['password'])
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


def place_order(client, address_id):
    response = client.post(
        CHECKOUT_ORDERS,
        {'address_id': address_id, 'payment_method': 'cod'},
        content_type='application/json',
    )
    assert response.status_code == 201, response.content
    return response.json()


# --- 11.2 Order history -------------------------------------------------------

def test_order_history_is_owner_scoped_and_summarised(client):
    _seller, store = make_store('historyseller@example.com', 'History Store')
    _product, variant = make_product(store)
    address_id = make_customer(client)
    add_to_cart(client, variant, quantity=2)
    number = place_order(client, address_id)['number']

    other = Client()
    other_address = make_customer(other, OTHER)
    add_to_cart(other, variant, quantity=1)
    other_number = place_order(other, other_address)['number']

    history = client.get(ORDERS)
    assert history.status_code == 200
    body = history.json()
    assert body['count'] == 1
    row = body['items'][0]
    assert row['number'] == number
    assert row['item_count'] == 2
    assert row['grand_total'] == 648.0  # 598 + 50 shipping
    assert row['store_names'] == ['History Store']
    assert row['can_cancel'] is True

    other_history = other.get(ORDERS).json()
    assert [r['number'] for r in other_history['items']] == [other_number]


# --- 11.2 Order detail = the receipt source ----------------------------------

def test_order_detail_receipt_snapshots_survive_catalog_and_address_edits(client):
    _seller, store = make_store('receiptseller@example.com', 'Receipt Store')
    product, variant = make_product(store, title='Woven Basket', price='299.00')
    address_id = make_customer(client)
    add_to_cart(client, variant, quantity=1)
    placed = place_order(client, address_id)

    # Rename + reprice the product and move the saved address afterwards —
    # the order (and therefore the receipt) must not move with them (§9).
    Product.objects.filter(pk=product.pk).update(title='Renamed Basket')
    Variant.objects.filter(pk=variant.pk).update(price=Decimal('999.00'))
    Address.objects.filter(pk=address_id).update(city='Cebu City')

    detail = client.get(f"{ORDERS}{placed['number']}/")
    assert detail.status_code == 200
    body = detail.json()
    assert body['seller_orders'][0]['items'][0]['title'] == 'Woven Basket'
    assert body['seller_orders'][0]['items'][0]['unit_price'] == 299.0
    assert body['shipping_address']['city'] == 'Quezon City'
    assert body['totals']['grand_total'] == 349.0  # 299 + 50 shipping
    assert body['can_cancel'] is True
    assert body['timeline'][0]['title'] == 'Order placed'


def test_order_detail_reorder_and_requests_are_owner_scoped(client):
    _seller, store = make_store('idorseller@example.com', 'IDOR Store')
    _product, variant = make_product(store)
    address_id = make_customer(client)
    add_to_cart(client, variant, quantity=1)
    number = place_order(client, address_id)['number']

    other = Client()
    make_customer(other, OTHER)

    assert other.get(f'{ORDERS}{number}/').status_code == 404
    assert other.post(f'{ORDERS}{number}/reorder').status_code == 404
    assert other.post(
        f'{ORDERS}{number}/requests',
        {'kind': 'issue', 'reason': 'Mine now'},
        content_type='application/json',
    ).status_code == 404
    assert other.post(f'{ORDERS}{number}/requests/1/withdraw').status_code == 404


# --- 11.2 Timeline + shipment tracking ---------------------------------------

def test_timeline_whitelists_the_orders_own_audit_events(client):
    seller, store = make_store('timelineseller@example.com', 'Timeline Store')
    _product, variant = make_product(store)
    address_id = make_customer(client)
    add_to_cart(client, variant, quantity=1)
    number = place_order(client, address_id)['number']

    order = Order.objects.get(number=number)
    seller_order = order.seller_orders.get()
    order_services.mark_seller_order_processing(seller_order, actor=seller)
    order_services.mark_seller_order_packed(seller_order, actor=seller)
    shipment = order_services.create_shipment(
        seller_order, carrier_code='manual', actor=seller
    )
    order_services.update_shipment_status(
        shipment, ShipmentStatus.IN_TRANSIT, location='Manila hub', actor=seller
    )

    body = client.get(f'{ORDERS}{number}/').json()
    titles = [step['title'] for step in body['timeline']]
    assert titles[0] == 'Order placed'
    assert 'Being prepared' in titles
    assert 'Packed and ready to ship' in titles
    assert 'Parcel handed to the courier' in titles
    assert 'In transit' in titles

    allowed_keys = {'title', 'description', 'tone', 'occurred_at'}
    assert all(set(step) <= allowed_keys for step in body['timeline'])
    occurred = [step['occurred_at'] for step in body['timeline']]
    assert occurred == sorted(occurred)


# --- 11.2 Reorder -------------------------------------------------------------

def test_reorder_readds_live_lines_and_reports_skipped_ones(client):
    _seller_a, store_a = make_store('reorderA@example.com', 'Reorder Store A')
    _seller_b, store_b = make_store('reorderB@example.com', 'Reorder Store B')
    _live_product, live_variant = make_product(store_a, title='Live Item', stock=5)
    dead_product, dead_variant = make_product(store_b, title='Dead Item', stock=5)

    address_id = make_customer(client)
    add_to_cart(client, live_variant, quantity=2)
    add_to_cart(client, dead_variant, quantity=1)
    number = place_order(client, address_id)['number']

    Product.objects.filter(pk=dead_product.pk).update(
        status=Product.Status.UNPUBLISHED
    )

    response = client.post(f'{ORDERS}{number}/reorder')
    assert response.status_code == 200
    body = response.json()
    assert [row['title'] for row in body['added']] == ['Live Item']
    assert body['added'][0]['quantity'] == 2
    assert [row['title'] for row in body['skipped']] == ['Dead Item']
    assert body['skipped'][0]['reason'] == 'This product is no longer available.'
    assert body['cart_item_count'] == 2

    line = CartItem.objects.get(variant=live_variant)
    assert line.quantity == 2


# --- 11.3 Request intake ------------------------------------------------------

def test_request_intake_is_server_verified_and_withdrawable(client):
    seller, store = make_store('requestseller@example.com', 'Request Store')
    _product, variant = make_product(store)
    address_id = make_customer(client)
    add_to_cart(client, variant, quantity=1)
    number = place_order(client, address_id)['number']
    order = Order.objects.get(number=number)
    endpoint = f'{ORDERS}{number}/requests'

    def submit(kind, **extra):
        return client.post(
            endpoint,
            {'kind': kind, 'reason': 'Changed my mind', **extra},
            content_type='application/json',
        )

    blocked_return = submit('return')
    assert blocked_return.status_code == 400
    assert blocked_return.json()['error'] == 'not_delivered'

    blocked_refund = submit('refund')
    assert blocked_refund.status_code == 400
    assert blocked_refund.json()['error'] == 'nothing_to_refund'

    issue = submit('issue')
    assert issue.status_code == 201, issue.content
    assert issue.json()['status'] == 'pending'

    duplicate = submit('issue')
    assert duplicate.status_code == 400
    assert duplicate.json()['error'] == 'request_exists'

    wrong_store = submit('issue', seller_order_id=99999)
    assert wrong_store.status_code == 400
    assert wrong_store.json()['error'] == 'invalid_store'

    request_id = issue.json()['id']
    withdrawn = client.post(f'{endpoint}/{request_id}/withdraw')
    assert withdrawn.status_code == 200
    assert withdrawn.json()['status'] == 'withdrawn'

    again = client.post(f'{endpoint}/{request_id}/withdraw')
    assert again.status_code == 400
    assert again.json()['error'] == 'not_withdrawable'

    # Fulfil end-to-end: process -> ship -> deliver (COD capture at delivery).
    seller_order = order.seller_orders.get()
    order_services.mark_seller_order_processing(seller_order, actor=seller)
    shipment = order_services.create_shipment(
        seller_order, carrier_code='manual', actor=seller
    )
    order_services.update_shipment_status(
        shipment, ShipmentStatus.DELIVERED, actor=seller
    )
    order.refresh_from_db()
    assert order.status == OrderStatus.DELIVERED
    assert Payment.objects.get(order=order).status == PaymentStatus.PAID

    accepted_return = submit('return')
    assert accepted_return.status_code == 201, accepted_return.content
    assert accepted_return.json()['kind_label'] == 'Return'

    accepted_refund = submit('refund')
    assert accepted_refund.status_code == 201, accepted_refund.content
    assert accepted_refund.json()['kind_label'] == 'Refund'

    detail = client.get(f'{ORDERS}{number}/').json()
    assert {r['kind'] for r in detail['requests']} == {'return', 'refund', 'issue'}
    assert detail['can_cancel'] is False


# --- 11.3 Cancel eligibility --------------------------------------------------

def test_can_cancel_is_the_servers_verdict(client):
    _seller, store = make_store('cancelseller@example.com', 'Cancel Store')
    _product, variant = make_product(store)
    address_id = make_customer(client)
    add_to_cart(client, variant, quantity=1)
    number = place_order(client, address_id)['number']

    assert client.get(f'{ORDERS}{number}/').json()['can_cancel'] is True

    Order.objects.filter(number=number).update(status=OrderStatus.PAID)

    assert client.get(f'{ORDERS}{number}/').json()['can_cancel'] is False
    cancelled = client.post(f'{ORDERS}{number}/cancel')
    assert cancelled.status_code == 400
    assert cancelled.json()['error'] == 'not_cancellable'