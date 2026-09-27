"""Phase 16 concurrency gate — one limited voucher, two checkouts.

A real threaded race on PostgreSQL: both checkouts evaluate the code and
pass the advisory pre-check, then the row-locked ledger write in
`promotions.services.redeem_voucher` serializes them — exactly one order
wins the discount, the loser rolls back whole (no order, no usage row, its
cart untouched), and the counters match the ledger exactly (§16 Gate).
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
from apps.orders.models import Order
from apps.promotions.models import (
    Voucher,
    VoucherDiscountType,
    VoucherScope,
    VoucherUsage,
)
from apps.stores.models import Store

pytestmark = pytest.mark.django_db(transaction=True)


def _make_buyer(email, variant):
    """A signed-in customer with an address and one unit in the cart."""
    user = User.objects.create_user(email=email, password='Str0ng!Passw0rd')
    address = Address.objects.create(
        user=user,
        full_name='Voucher Racer',
        phone='09171234567',
        line1='1 Race Road',
        city='Manila',
        province='Metro Manila',
        postal_code='1000',
    )
    cart = Cart.objects.create(user=user)
    CartItem.objects.create(cart=cart, variant=variant, quantity=1)
    return user, address


def _make_racer_store():
    seller = User.objects.create_user(email='vraceseller@example.com', password='x')
    store = Store.objects.create(
        user=seller, name='VRace Store', status=Store.Status.ACTIVE
    )
    product = Product.objects.create(
        store=store,
        title='Raced Product',
        base_price=Decimal('100.00'),
        status=Product.Status.PUBLISHED,
    )
    variant = Variant.objects.create(
        product=product, name='Default', price=Decimal('100.00'), is_default=True
    )
    catalog_services.ensure_inventory(variant, initial_on_hand=5)
    return variant


def test_concurrent_redemption_of_a_single_use_voucher():
    variant = _make_racer_store()
    Voucher.objects.create(
        scope=VoucherScope.PLATFORM,
        code='RACEONCE',
        title='One-shot 10%',
        discount_type=VoucherDiscountType.PERCENTAGE,
        value=Decimal('10.00'),
        usage_limit=1,
        per_user_limit=None,
    )
    _user_a, address_a = _make_buyer('vrace-a@example.com', variant)
    user_a = User.objects.get(email='vrace-a@example.com')
    _user_b, address_b = _make_buyer('vrace-b@example.com', variant)
    user_b = User.objects.get(email='vrace-b@example.com')

    results = []
    results_lock = threading.Lock()
    barrier = threading.Barrier(2)

    def attempt(user, address):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            order_services.create_order(user, address.id, voucher_code='RACEONCE')
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
    assert results.count('voucher_usage_limit') == 1, results

    # One order, one ledger row, the discount on the money — nothing partial.
    assert Order.objects.count() == 1
    assert VoucherUsage.objects.count() == 1
    order = Order.objects.get()
    assert order.voucher_code == 'RACEONCE'
    assert order.discount_total == Decimal('10.00')
    assert order.grand_total == Decimal('90.00')
    assert order.payment.amount == Decimal('90.00')

    # Only the winner's unit stayed reserved; the loser rolled back cleanly
    # and its cart is untouched (cleared cart = the winner).
    inventory = Inventory.objects.get(variant=variant)
    assert inventory.on_hand == 5
    assert inventory.reserved == 1
    cart_item_counts = sorted(
        cart.items.count() for cart in Cart.objects.order_by('id')
    )
    assert cart_item_counts == [0, 1]
