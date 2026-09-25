"""Phase 9 concurrency gate — parallel captures and refunds (rule 8).

Real threaded races on PostgreSQL: two workers try to capture the same
payment at once, and two workers try to refund the same captured balance.
The row locks in payments.services serialize them — exactly one capture
lands, and refunds can never sum past what was captured.
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
from apps.payments import services as payment_services
from apps.payments.models import PaymentTransaction
from apps.stores.models import Store

pytestmark = pytest.mark.django_db(transaction=True)


def _make_cod_order(*, quantity=2, price='299.00'):
    """A placed COD order (store + product + cart → checkout service)."""
    seller = User.objects.create_user(
        email='race-payseller@example.com', password='x'
    )
    store = Store.objects.create(
        user=seller, name='Race Pay Store', status=Store.Status.ACTIVE
    )
    product = Product.objects.create(
        store=store,
        title='Race Item',
        base_price=Decimal(price),
        status=Product.Status.PUBLISHED,
    )
    variant = Variant.objects.create(
        product=product, name='Default', price=Decimal(price), is_default=True
    )
    catalog_services.ensure_inventory(variant, initial_on_hand=10)

    buyer = User.objects.create_user(email='race-paybuyer@example.com', password='x')
    address = Address.objects.create(
        user=buyer, full_name='Race Buyer', phone='0900', line1='1 Race Road',
        city='Manila', province='Metro Manila', postal_code='1000',
    )
    cart = Cart.objects.create(user=buyer)
    CartItem.objects.create(cart=cart, variant=variant, quantity=quantity)
    order = order_services.create_order(buyer, address.id)
    return order, variant, order.payment


def _run_parallel(tasks):
    """Run callables in threads behind a barrier; return their outcomes."""
    results = []
    results_lock = threading.Lock()
    barrier = threading.Barrier(len(tasks))

    def run(task):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            outcome = task()
        except Exception as exc:  # the raised error *is* an observation
            outcome = f'{type(exc).__name__}:{exc}'
        finally:
            close_old_connections()
        with results_lock:
            results.append(outcome)

    threads = [threading.Thread(target=run, args=(task,)) for task in tasks]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    return results


def test_parallel_captures_charge_once():
    order, variant, payment = _make_cod_order()

    results = _run_parallel([
        lambda: payment_services.mark_paid(payment, source='cod_collection').status,
        lambda: payment_services.mark_paid(payment, source='cod_collection').status,
    ])

    assert results.count('paid') == 2, results  # both calls succeed…
    assert PaymentTransaction.objects.filter(
        payment=payment, kind='capture'
    ).count() == 1  # …but the money moves exactly once

    payment.refresh_from_db()
    order.refresh_from_db()
    assert payment.status == 'paid'
    assert order.status == 'paid'
    inventory = Inventory.objects.get(variant=variant)
    assert inventory.on_hand == 8
    assert inventory.reserved == 0


def test_parallel_refunds_cannot_exceed_the_captured_balance():
    _order, variant, payment = _make_cod_order()
    payment_services.mark_paid(payment, source='cod_collection')

    results = _run_parallel([
        lambda: payment_services.refund(payment, payment.amount, reason='first').status,
        lambda: payment_services.refund(payment, payment.amount, reason='second').status,
    ])

    assert results.count('succeeded') == 1, results
    assert sum(1 for r in results if 'PaymentError' in r) == 1, results

    payment.refresh_from_db()
    assert payment.status == 'refunded'
    debits = PaymentTransaction.objects.filter(payment=payment, kind='refund')
    assert debits.count() == 1
    assert sum(entry.amount for entry in debits) == payment.amount
    assert PaymentTransaction.objects.filter(payment=payment).count() == 2  # capture + refund

    # The single full refund restored the stock exactly once.
    assert Inventory.objects.get(variant=variant).on_hand == 10
