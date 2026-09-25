"""Phase 8 concurrency gate — two customers, one last unit (§6, rule 2).

A real threaded race on PostgreSQL: both checkouts pass the advisory
pre-check, then the row-locked reservation in catalog services serializes
them — exactly one order wins, stock never goes negative, and the loser
leaves no partial rows behind.
"""
import threading
from decimal import Decimal

import pytest
from django.db import close_old_connections

from apps.accounts.models import Address, User
from apps.cart.models import Cart, CartItem
from apps.catalog import services as catalog_services
from apps.catalog.models import Inventory, Product, Variant
from apps.orders import services as order_services
from apps.orders.models import Order, OrderItem
from apps.stores.models import Store

pytestmark = pytest.mark.django_db(transaction=True)


def _make_buyer(email, variant):
    """A signed-in customer with an address and the last unit in the cart."""
    user = User.objects.create_user(email=email, password='Str0ng!Passw0rd')
    address = Address.objects.create(
        user=user,
        full_name='Race Buyer',
        phone='09171234567',
        line1='1 Race Road',
        city='Manila',
        province='Metro Manila',
        postal_code='1000',
    )
    cart = Cart.objects.create(user=user)
    CartItem.objects.create(cart=cart, variant=variant, quantity=1)
    return user, address


def test_concurrent_checkout_of_the_last_unit():
    seller = User.objects.create_user(email='raceseller@example.com', password='x')
    store = Store.objects.create(
        user=seller, name='Race Store', status=Store.Status.ACTIVE
    )
    product = Product.objects.create(
        store=store,
        title='Last Unit',
        base_price=Decimal('100.00'),
        status=Product.Status.PUBLISHED,
    )
    variant = Variant.objects.create(
        product=product, name='Default', price=Decimal('100.00'), is_default=True
    )
    catalog_services.ensure_inventory(variant, initial_on_hand=1)

    user_a, address_a = _make_buyer('race-a@example.com', variant)
    user_b, address_b = _make_buyer('race-b@example.com', variant)

    results = []
    results_lock = threading.Lock()
    barrier = threading.Barrier(2)

    def attempt(user, address):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            order_services.create_order(user, address.id)
            outcome = 'placed'
        except order_services.CheckoutError as exc:
            outcome = exc.code
        finally:
            close_old_connections()
        with results_lock:
            results.append(outcome)

    threads = [
        threading.Thread(target=attempt, args=(user_a, address_a)),
        threading.Thread(target=attempt, args=(user_b, address_b)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert len(results) == 2, results
    assert results.count('placed') == 1, results
    assert results.count('insufficient_stock') == 1, results

    assert Order.objects.count() == 1
    assert OrderItem.objects.count() == 1
    inventory = Inventory.objects.get(variant=variant)
    assert inventory.on_hand == 1
    assert inventory.reserved == 1
    assert inventory.available == 0
