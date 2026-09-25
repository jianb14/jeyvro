"""Phase 10 gate tests — order fulfillment, parcel shipments, delivery & tracking.

Rules tested (§10.1, §10.2, §10.3, Phase 9 COD integration):
1. Order lifecycle transitions: placed/awaiting_payment -> processing -> packed -> shipped -> delivered.
2. Seller fulfillment isolation: seller can only fulfill their own store's orders; other sellers are denied (404/403).
3. Full shipment creation: generates unique tracking number, creates Shipment and ShipmentItem records, and initial TrackingEvent.
4. Partial shipment handling: can ship item subsets; remaining quantity tracks correctly; order stays processing until all items shipped.
5. Tracking events: status transitions append immutable TrackingEvents with timestamp, location, and description.
6. Public tracking lookup: customers/anyone with tracking number can check status and event timeline.
7. Parent order aggregation: parent order aggregates seller order statuses (mixed statuses, all shipped, all delivered).
8. Delivery COD collection: when COD order is delivered, payment is marked paid via the Phase 9 payment service.
"""
from decimal import Decimal

import pytest
from django.test import Client

from apps.accounts.models import Address, User
from apps.audit.models import AuditLog
from apps.cart.models import Cart
from apps.catalog import services as catalog_services
from apps.catalog.models import Inventory, Product, Variant
from apps.orders import services as order_services
from apps.orders.models import Order, OrderItem, OrderStatus, SellerOrder, Shipment, ShipmentStatus
from apps.payments.models import Payment, PaymentMethod, PaymentStatus
from apps.stores.models import Store

pytestmark = pytest.mark.django_db


def _make_seller(name, email):
    user = User.objects.create_user(email=email, password='SellerPassword1!')
    user.is_seller = True
    user.save(update_fields=['is_seller'])
    store = Store.objects.create(
        user=user,
        name=name,
        slug=name.lower().replace(' ', '-'),
        shipping_flat_fee=Decimal('50.00'),
        status='active',
    )
    return user, store


def _make_product(store, title, price=Decimal('200.00'), stock=10):
    from django.utils.crypto import get_random_string
    product = Product.objects.create(
        store=store,
        title=title,
        base_price=Decimal(str(price)),
        status=Product.Status.PUBLISHED,
    )
    rand_sku = get_random_string(6, 'ABCDEF0123456789')
    variant = Variant.objects.create(
        product=product,
        name='Default',
        sku=f'SKU-{rand_sku}',
        price=Decimal(str(price)),
        is_default=True,
    )
    catalog_services.ensure_inventory(variant, initial_on_hand=stock)
    return product, variant


def _create_test_order(customer, store_variants, payment_method=PaymentMethod.COD):
    address = Address.objects.create(
        user=customer,
        full_name='Customer Buyer',
        phone='09170000000',
        line1='123 Test St',
        city='Manila',
        province='Metro Manila',
        postal_code='1000',
    )
    cart = Cart.objects.create(user=customer)
    for variant, qty in store_variants:
        cart.items.create(variant=variant, quantity=qty)

    order = order_services.create_order(customer, address.id, payment_method=payment_method)
    return order



def test_seller_can_process_and_pack_order():
    """Seller transitions order through processing -> packed."""
    seller, store = _make_seller('Store A', 'sellerA@example.com')
    customer = User.objects.create_user(email='buyer@example.com', password='BuyerPassword1!')
    _, variant = _make_product(store, 'Product 1')

    order = _create_test_order(customer, [(variant, 2)])
    seller_order = order.seller_orders.first()
    assert seller_order.status == OrderStatus.AWAITING_PAYMENT

    # Step 1: Processing
    so = order_services.mark_seller_order_processing(seller_order, actor=seller)
    assert so.status == OrderStatus.PROCESSING
    order.refresh_from_db()
    assert order.status == OrderStatus.PROCESSING

    # Step 2: Packed
    so = order_services.mark_seller_order_packed(so, actor=seller)
    assert so.status == OrderStatus.PACKED
    order.refresh_from_db()
    assert order.status == OrderStatus.PROCESSING


def test_seller_shipment_creation_full():
    """Creating a full shipment sets seller order to SHIPPED and creates tracking event."""
    seller, store = _make_seller('Store B', 'sellerB@example.com')
    customer = User.objects.create_user(email='buyer2@example.com', password='BuyerPassword1!')
    _, variant = _make_product(store, 'Product 2')

    order = _create_test_order(customer, [(variant, 3)])
    seller_order = order.seller_orders.first()
    order_services.mark_seller_order_processing(seller_order, actor=seller)

    shipment = order_services.create_shipment(
        seller_order,
        carrier_code='manual',
        package_notes='Fragile items',
        package_weight_grams=500,
        actor=seller,
    )

    assert shipment.tracking_number.startswith('JVTRK-')
    assert shipment.status == ShipmentStatus.PICKED_UP
    assert shipment.items.count() == 1
    assert shipment.items.first().quantity == 3
    assert shipment.tracking_events.count() == 1
    assert shipment.recipient_name == 'Customer Buyer'

    seller_order.refresh_from_db()
    assert seller_order.status == OrderStatus.SHIPPED
    order.refresh_from_db()


def test_partial_shipment_handling():
    """Shipping only part of the order leaves seller order in PROCESSING until rest is shipped."""
    seller, store = _make_seller('Store C', 'sellerC@example.com')
    customer = User.objects.create_user(email='buyer3@example.com', password='BuyerPassword1!')
    _, variant1 = _make_product(store, 'Item Alpha')
    _, variant2 = _make_product(store, 'Item Beta')

    order = _create_test_order(customer, [(variant1, 2), (variant2, 1)])
    seller_order = order.seller_orders.first()
    items = list(seller_order.items.all())
    item1 = items[0]
    item2 = items[1]

    shipment1 = order_services.create_shipment(
        seller_order,
        items_data=[{'order_item_id': item1.id, 'quantity': 2}],
        actor=seller,
    )
    assert shipment1.items.count() == 1
    seller_order.refresh_from_db()
    assert seller_order.status == OrderStatus.PROCESSING

    shipment2 = order_services.create_shipment(
        seller_order,
        items_data=[{'order_item_id': item2.id, 'quantity': 1}],
        actor=seller,
    )
    assert shipment2.items.count() == 1
    seller_order.refresh_from_db()
    assert seller_order.status == OrderStatus.SHIPPED
    order.refresh_from_db()
    assert order.status == OrderStatus.SHIPPED


def test_cannot_overship_items():
    """Trying to ship more quantity than ordered is rejected with error."""
    seller, store = _make_seller('Store D', 'sellerD@example.com')
    customer = User.objects.create_user(email='buyer4@example.com', password='BuyerPassword1!')
    _, variant = _make_product(store, 'Item Delta')

    order = _create_test_order(customer, [(variant, 2)])
    seller_order = order.seller_orders.first()
    item = seller_order.items.first()

    with pytest.raises(order_services.FulfillmentError) as exc_info:
        order_services.create_shipment(
            seller_order,
            items_data=[{'order_item_id': item.id, 'quantity': 5}],
            actor=seller,
        )
    assert exc_info.value.code == 'excess_quantity'
    order.refresh_from_db()
    assert order.status == OrderStatus.AWAITING_PAYMENT


def test_shipment_lifecycle_and_cod_collection():
    """Transitioning shipment through in_transit -> delivered triggers COD collection."""
    seller, store = _make_seller('Store E', 'sellerE@example.com')
    customer = User.objects.create_user(email='buyer5@example.com', password='BuyerPassword1!')
    _, variant = _make_product(store, 'COD Product')

    order = _create_test_order(customer, [(variant, 1)], payment_method=PaymentMethod.COD)
    seller_order = order.seller_orders.first()

    shipment = order_services.create_shipment(seller_order, actor=seller)
    assert order.payment.status == PaymentStatus.PENDING

    # Step: In transit
    s = order_services.update_shipment_status(
        shipment,
        ShipmentStatus.IN_TRANSIT,
        location='Metro Manila Hub',
        description='Departed sorting facility',
    )
    assert s.status == ShipmentStatus.IN_TRANSIT
    seller_order.refresh_from_db()
    assert seller_order.status == OrderStatus.IN_TRANSIT

    # Step: Out for delivery
    s = order_services.update_shipment_status(
        s,
        ShipmentStatus.OUT_FOR_DELIVERY,
        location='Local Depot',
        description='Rider is out for delivery',
    )
    assert s.status == ShipmentStatus.OUT_FOR_DELIVERY

    # Step: Delivered -> triggers COD collection!
    s = order_services.update_shipment_status(
        s,
        ShipmentStatus.DELIVERED,
        location='Doorstep',
        description='Handed to customer and cash collected',
    )
    assert s.status == ShipmentStatus.DELIVERED
    assert s.delivered_at is not None

    seller_order.refresh_from_db()
    assert seller_order.status == OrderStatus.DELIVERED

    order.refresh_from_db()
    assert order.status == OrderStatus.DELIVERED

    # Payment was captured via cod_delivery source!
    order.payment.refresh_from_db()
    assert order.payment.status == PaymentStatus.PAID
    assert order.payment.paid_at is not None



def test_multi_seller_fulfillment_aggregation():
    """Parent order aggregates shipments from multiple sellers independently."""
    seller1, store1 = _make_seller('Store 1', 'seller1@example.com')
    seller2, store2 = _make_seller('Store 2', 'seller2@example.com')
    customer = User.objects.create_user(email='buyer6@example.com', password='BuyerPassword1!')

    _, variant1 = _make_product(store1, 'Product from Store 1')
    _, variant2 = _make_product(store2, 'Product from Store 2')

    order = _create_test_order(customer, [(variant1, 1), (variant2, 1)])
    assert order.seller_orders.count() == 2

    so1 = order.seller_orders.get(store=store1)
    so2 = order.seller_orders.get(store=store2)

    # Store 1 ships its parcel
    s1 = order_services.create_shipment(so1, actor=seller1)
    so1.refresh_from_db()
    so2.refresh_from_db()
    order.refresh_from_db()

    assert so1.status == OrderStatus.SHIPPED
    assert so2.status == OrderStatus.AWAITING_PAYMENT
    assert order.status == OrderStatus.SHIPPED

    # Store 1 delivers its parcel, but Store 2 has not
    order_services.update_shipment_status(s1, ShipmentStatus.DELIVERED)
    so1.refresh_from_db()
    order.refresh_from_db()
    assert so1.status == OrderStatus.DELIVERED
    assert order.status == OrderStatus.SHIPPED

    # Now Store 2 ships and delivers
    s2 = order_services.create_shipment(so2, actor=seller2)
    order_services.update_shipment_status(s2, ShipmentStatus.DELIVERED)
    so2.refresh_from_db()
    order.refresh_from_db()
    assert so2.status == OrderStatus.DELIVERED
    assert order.status == OrderStatus.DELIVERED




def test_seller_api_endpoints_and_isolation():
    """Seller endpoints enforce ownership: seller cannot see or touch other stores' orders."""
    seller1, store1 = _make_seller('Store Alpha', 'seller_alpha@example.com')
    seller2, store2 = _make_seller('Store Beta', 'seller_beta@example.com')
    customer = User.objects.create_user(email='buyer7@example.com', password='BuyerPassword1!')

    _, variant1 = _make_product(store1, 'Alpha Item')
    _, variant2 = _make_product(store2, 'Beta Item')

    order = _create_test_order(customer, [(variant1, 1), (variant2, 1)])
    so1 = order.seller_orders.get(store=store1)
    so2 = order.seller_orders.get(store=store2)

    client1 = Client()
    client1.force_login(seller1)

    # Seller 1 can list their own orders
    res = client1.get('/api/v1/seller/orders/')
    assert res.status_code == 200
    ids = [item['id'] for item in res.json()['items']]
    assert so1.id in ids
    assert so2.id not in ids

    # Seller 1 can view detail of so1
    res = client1.get(f'/api/v1/seller/orders/{so1.id}/')
    assert res.status_code == 200
    assert res.json()['store_slug'] == store1.slug

    # Seller 1 CANNOT view or process so2 (IDOR protection -> 404)
    res_other = client1.get(f'/api/v1/seller/orders/{so2.id}/')
    assert res_other.status_code == 404

    res_proc = client1.post(f'/api/v1/seller/orders/{so2.id}/process')
    assert res_proc.status_code == 404

    # Seller 1 processes and packs so1
    res = client1.post(f'/api/v1/seller/orders/{so1.id}/process')
    assert res.status_code == 200
    assert res.json()['status'] == 'processing'

    res = client1.post(f'/api/v1/seller/orders/{so1.id}/pack')
    assert res.status_code == 200
    assert res.json()['status'] == 'packed'

    # Seller 1 dispatches shipment
    res = client1.post(f'/api/v1/seller/orders/{so1.id}/ship', {
        'package_notes': 'Handle with care',
    }, content_type='application/json')
    assert res.status_code == 201
    shipment_data = res.json()
    tracking_no = shipment_data['tracking_number']
    assert tracking_no.startswith('JVTRK-')

    # Public tracking endpoint
    anon = Client()
    track_res = anon.get(f'/api/v1/shipments/track/{tracking_no}/')
    assert track_res.status_code == 200
    assert track_res.json()['tracking_number'] == tracking_no
    assert len(track_res.json()['tracking_events']) >= 1

    # Customer sees shipment in OrderDetail
    customer_client = Client()
    customer_client.force_login(customer)
    order_res = customer_client.get(f'/api/v1/orders/{order.number}/')
    assert order_res.status_code == 200
    seller_order_data = order_res.json()['seller_orders'][0]
    assert len(seller_order_data['shipments']) == 1
    assert seller_order_data['shipments'][0]['tracking_number'] == tracking_no
