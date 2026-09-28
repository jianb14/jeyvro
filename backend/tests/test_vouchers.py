"""Phase 16 gate tests — the voucher engine (ROADMAP §16.1).

The §16 Gate drives these: promotion rules are calculated server-side (the
client only ever sends a code), invalid vouchers are rejected with a
customer-safe reason and roll the checkout back, usage limits are enforced
against the ledger under a row lock (the sequential loser path is proven
here; the true concurrent case rides the same `select_for_update` the race
tests exercise elsewhere), and every discount is auditable — one
`VoucherUsage` row plus one `voucher.redeemed` AuditLog event per order.
"""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.test import Client
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.cart.models import Cart
from apps.catalog import services as catalog_services
from apps.catalog.models import Category, Product, Variant
from apps.orders.models import Order
from apps.promotions import services as promotion_services
from apps.promotions.models import (
    Voucher,
    VoucherDiscountType,
    VoucherEligibility,
    VoucherScope,
    VoucherUsage,
)
from apps.stores.models import Store

pytestmark = pytest.mark.django_db
PASSWORD = 'Str0ng!Passw0rd'

REGISTER = '/api/v1/auth/register'
LOGIN = '/api/v1/auth/login'
ADDRESSES = '/api/v1/auth/addresses/'
VALIDATE = '/api/v1/vouchers/validate/'
CHECKOUT = '/api/v1/checkout/'
CHECKOUT_ORDERS = '/api/v1/checkout/orders'

ADDRESS_PAYLOAD = {
    'full_name': 'Vera Buyer',
    'phone': '09171112222',
    'line1': '1 Mabini Street',
    'line2': '',
    'city': 'Quezon City',
    'province': 'Metro Manila',
    'postal_code': '1100',
}


def _make_active_store(email, name='Voucher Store', slug='voucher-store', fee='0.00'):
    """Direct ORM setup — the store flows have their own gate tests."""
    user = User.objects.create_user(email=email, password=PASSWORD)
    store = Store.objects.create(
        user=user,
        name=name,
        slug=slug,
        status=Store.Status.ACTIVE,
        shipping_flat_fee=Decimal(fee),
    )
    return user, store


def _make_product(store, *, title='Voucher Product', price='200.00', stock=10,
                  category=None):
    product = Product.objects.create(
        store=store,
        title=title,
        base_price=Decimal(price),
        status=Product.Status.PUBLISHED,
        category=category,
    )
    variant = Variant.objects.create(
        product=product, name='Default', price=Decimal(price), is_default=True
    )
    catalog_services.ensure_inventory(variant, initial_on_hand=stock)
    return product, variant


def _sign_in(client, email):
    """Register + log in the buyer through the real auth flow."""
    response = client.post(
        REGISTER, {'email': email, 'password': PASSWORD},
        content_type='application/json',
    )
    assert response.status_code == 201, response.content
    response = client.post(
        LOGIN, {'email': email, 'password': PASSWORD},
        content_type='application/json',
    )
    assert response.status_code == 200, response.content
    return User.objects.get(email=email)


def _add_address(client):
    response = client.post(ADDRESSES, ADDRESS_PAYLOAD, content_type='application/json')
    assert response.status_code == 201, response.content
    return response.json()['id']


def _cart_with(user, variant, quantity=1):
    cart = Cart.objects.filter(user=user).first() or Cart.objects.create(user=user)
    cart.items.update_or_create(variant=variant, defaults={'quantity': quantity})
    return cart


def _platform_voucher(code='WELCOME10', **overrides):
    data = {
        'scope': VoucherScope.PLATFORM,
        'code': code,
        'title': 'Welcome 10% off',
        'discount_type': VoucherDiscountType.PERCENTAGE,
        'value': Decimal('10.00'),
    }
    data.update(overrides)
    return Voucher.objects.create(**data)


def _checkout(client, address_id, code=None):
    payload = {'address_id': address_id}
    if code is not None:
        payload['voucher_code'] = code
    return client.post(CHECKOUT_ORDERS, payload, content_type='application/json')


def test_validate_endpoint_and_checkout_share_the_verdict():
    """The preview and the order must agree — one service, one discount."""
    client = Client()
    buyer = _sign_in(client, 'buyer1@example.com')
    address_id = _add_address(client)
    _seller, store = _make_active_store('seller1@example.com', fee='50.00')
    _product, variant = _make_product(store, price='200.00')
    _cart_with(buyer, variant, quantity=2)  # 400.00 + 50.00 shipping
    _platform_voucher()  # 10% → 40.00

    preview = client.post(
        VALIDATE, {'code': 'welcome10'},  # lowercase on purpose
        content_type='application/json',
    )
    assert preview.status_code == 200, preview.content
    body = preview.json()
    assert body['valid'] is True
    assert body['code'] == 'WELCOME10'
    assert body['eligible_subtotal'] == 400.0
    assert body['discount_total'] == 40.0

    response = _checkout(client, address_id, 'WELCOME10')
    assert response.status_code == 201, response.content
    body = response.json()
    assert body['totals'] == {
        'subtotal': 400.0,
        'shipping_total': 50.0,
        'savings_total': 0.0,
        'promotion_discount': 0.0,
        'discount_total': 40.0,
        'voucher_code': 'WELCOME10',
        'tax_total': 0.0,
        'grand_total': 410.0,
    }
    # The payment asks for the discounted amount, not the raw total.
    assert body['payment']['amount'] == 410.0

    voucher = Voucher.objects.get(code='WELCOME10')
    usage = VoucherUsage.objects.get(voucher=voucher)
    assert usage.user_id == buyer.id
    assert usage.order_id == body['id']
    assert usage.discount_amount == Decimal('40.00')
    assert usage.store is None  # platform-funded → no store slice
    audit = AuditLog.objects.get(action='voucher.redeemed')
    assert audit.detail['code'] == 'WELCOME10'
    assert audit.detail['discount_total'] == '40.00'


def test_checkout_preview_prices_an_applied_voucher_server_side():
    """The preview judges the code with the same service as the order —
    net totals now, and the order that follows charges exactly that."""
    client = Client()
    buyer = _sign_in(client, 'previewbuyer@example.com')
    address_id = _add_address(client)
    _seller, store = _make_active_store(
        'previewseller@example.com', fee='50.00'
    )
    _product, variant = _make_product(store, price='200.00')
    _cart_with(buyer, variant, quantity=2)  # 400.00 + 50.00 shipping
    _platform_voucher()  # 10% → 40.00

    body = client.get(f'{CHECKOUT}?voucher_code=welcome10').json()
    assert body['voucher_error'] is None
    assert body['voucher']['code'] == 'WELCOME10'
    assert body['voucher']['discount_total'] == 40.0
    totals = body['totals']
    assert totals['discount_total'] == 40.0
    assert totals['voucher_code'] == 'WELCOME10'
    assert totals['grand_total'] == 410.0  # 400 + 50 − 40

    # The order that follows agrees with the preview to the cent.
    response = _checkout(client, address_id, 'WELCOME10')
    assert response.status_code == 201, response.content
    assert response.json()['totals']['grand_total'] == 410.0


def test_checkout_preview_reports_a_refused_code_without_breaking():
    """A stale/invalid code leaves the totals gross and explains why —
    `create_order` stays the authoritative validator at place time."""
    client = Client()
    buyer = _sign_in(client, 'previewbad@example.com')
    _add_address(client)
    _seller, store = _make_active_store(
        'previewbadseller@example.com', slug='preview-bad-store', fee='50.00'
    )
    _product, variant = _make_product(store, price='200.00')
    _cart_with(buyer, variant, quantity=2)  # 400.00 + 50.00 shipping

    response = client.get(f'{CHECKOUT}?voucher_code=nope-not-real')
    assert response.status_code == 200
    body = response.json()
    assert body['voucher'] is None
    assert body['voucher_error']['error'] == 'voucher_not_found'
    assert body['voucher_error']['detail']
    totals = body['totals']
    assert totals['discount_total'] == 0.0
    assert totals['voucher_code'] == ''
    assert totals['grand_total'] == 450.0  # gross: 400 + 50
    assert body['checkout_ready'] is True


def test_unknown_code_is_rejected_and_codes_normalize():
    client = Client()
    buyer = _sign_in(client, 'buyer2@example.com')
    _seller, store = _make_active_store('seller2@example.com', slug='store-two')
    _product, variant = _make_product(store, price='150.00')
    _cart_with(buyer, variant)

    response = client.post(
        VALIDATE, {'code': 'nope-not-real'}, content_type='application/json'
    )
    assert response.status_code == 400
    assert response.json()['error'] == 'voucher_not_found'
    assert response.json()['detail']

    # Codes are stored uppercase no matter how they are typed.
    voucher = Voucher.objects.create(
        scope=VoucherScope.PLATFORM,
        code='  save20 ',
        title='Save 20',
        discount_type=VoucherDiscountType.FIXED,
        value=Decimal('20.00'),
    )
    assert voucher.code == 'SAVE20'

    # Signed-in only — an anonymous caller cannot probe codes.
    anonymous = Client().post(
        VALIDATE, {'code': 'SAVE20'}, content_type='application/json'
    )
    assert anonymous.status_code in (401, 403)


def test_min_spend_and_targeting_rejections():
    client = Client()
    buyer = _sign_in(client, 'buyer3@example.com')
    _seller, store = _make_active_store('seller3@example.com', slug='store-three')
    _product, variant = _make_product(store, price='200.00')
    _cart_with(buyer, variant, quantity=1)  # 200.00

    _platform_voucher(code='BIGSPEND', min_spend=Decimal('500.00'))
    response = client.post(
        VALIDATE, {'code': 'BIGSPEND'}, content_type='application/json'
    )
    assert response.status_code == 400
    assert response.json()['error'] == 'voucher_min_spend'

    # A voucher targeted at a product outside the cart never applies.
    other_product, _other_variant = _make_product(store, title='Other', price='50.00')
    targeted = _platform_voucher(code='ONLYOTHER')
    VoucherEligibility.objects.create(voucher=targeted, product=other_product)
    response = client.post(
        VALIDATE, {'code': 'ONLYOTHER'}, content_type='application/json'
    )
    assert response.status_code == 400
    assert response.json()['error'] == 'voucher_no_eligible_items'


def test_percentage_cap_and_fixed_cap_at_subtotal():
    client = Client()
    buyer = _sign_in(client, 'buyer4@example.com')
    address_id = _add_address(client)
    _seller, store = _make_active_store(
        'seller4@example.com', slug='store-four', fee='50.00'
    )
    _product, variant = _make_product(store, price='200.00')
    _cart_with(buyer, variant, quantity=2)  # 400.00

    # 50% with a PHP 30 cap → exactly 30.
    _platform_voucher(
        code='HALFCAP', value=Decimal('50.00'), max_discount=Decimal('30.00')
    )
    response = client.post(
        VALIDATE, {'code': 'HALFCAP'}, content_type='application/json'
    )
    assert response.status_code == 200, response.content
    assert response.json()['discount_total'] == 30.0

    # A fixed amount above the eligible subtotal caps at the subtotal and
    # never goes negative — the buyer still pays shipping only.
    _platform_voucher(
        code='HUGE',
        discount_type=VoucherDiscountType.FIXED,
        value=Decimal('1000.00'),
    )
    response = _checkout(client, address_id, 'HUGE')
    assert response.status_code == 201, response.content
    body = response.json()
    assert body['totals']['discount_total'] == 400.0
    assert body['totals']['grand_total'] == 50.0


def test_expired_not_started_and_inactive_windows():
    client = Client()
    buyer = _sign_in(client, 'buyer5@example.com')
    _seller, store = _make_active_store('seller5@example.com', slug='store-five')
    _product, variant = _make_product(store, price='200.00')
    _cart_with(buyer, variant)
    now = timezone.now()

    _platform_voucher(code='EXPIRED', ends_at=now - timedelta(days=1))
    _platform_voucher(code='SOON', starts_at=now + timedelta(days=1))
    _platform_voucher(code='OFF', is_active=False)

    for code, error in (
        ('EXPIRED', 'voucher_expired'),
        ('SOON', 'voucher_not_started'),
        ('OFF', 'voucher_inactive'),
    ):
        response = client.post(
            VALIDATE, {'code': code}, content_type='application/json'
        )
        assert response.status_code == 400, code
        assert response.json()['error'] == error


def test_usage_limit_blocks_the_second_order_and_rolls_it_back():
    client = Client()
    buyer = _sign_in(client, 'buyer6@example.com')
    address_id = _add_address(client)
    _seller, store = _make_active_store('seller6@example.com', slug='store-six')
    _product, variant = _make_product(store, price='200.00', stock=20)
    # Unlimited per-user, exactly one redemption total — isolates the counter.
    _platform_voucher(code='ONLYONE', usage_limit=1, per_user_limit=None)

    _cart_with(buyer, variant, quantity=1)
    response = _checkout(client, address_id, 'ONLYONE')
    assert response.status_code == 201, response.content
    assert Order.objects.count() == 1

    # A fresh cart, real stock — only the exhausted usage limit stops it.
    _cart_with(buyer, variant, quantity=1)
    response = _checkout(client, address_id, 'ONLYONE')
    assert response.status_code == 400
    assert response.json()['error'] == 'voucher_usage_limit'

    # The rejection rolled the whole checkout back: one order, cart intact,
    # ledger untouched — totals and counters can never diverge (§16 Gate).
    assert Order.objects.count() == 1
    assert VoucherUsage.objects.count() == 1
    assert Cart.objects.get(user=buyer).items.count() == 1


def test_per_user_limit_and_first_order_rules():
    client = Client()
    buyer = _sign_in(client, 'buyer7@example.com')
    address_id = _add_address(client)
    _seller, store = _make_active_store('seller7@example.com', slug='store-seven')
    _product, variant = _make_product(store, price='200.00', stock=20)
    _platform_voucher(code='ONCE', per_user_limit=1)

    _cart_with(buyer, variant, quantity=1)
    assert _checkout(client, address_id, 'ONCE').status_code == 201

    # Same buyer, second attempt → refused by the per-user counter.
    _cart_with(buyer, variant, quantity=1)
    response = _checkout(client, address_id, 'ONCE')
    assert response.status_code == 400
    assert response.json()['error'] == 'voucher_user_limit'

    # First-order vouchers stop applying once any order exists.
    _platform_voucher(code='FIRSTONLY', first_order_only=True)
    response = client.post(
        VALIDATE, {'code': 'FIRSTONLY'}, content_type='application/json'
    )
    assert response.status_code == 400
    assert response.json()['error'] == 'voucher_first_order_only'


def test_seller_and_category_scoping():
    client = Client()
    buyer = _sign_in(client, 'buyer8@example.com')
    _seller_a, store_a = _make_active_store(
        'seller8a@example.com', name='Store A', slug='store-a'
    )
    _seller_b, store_b = _make_active_store(
        'seller8b@example.com', name='Store B', slug='store-b'
    )
    category = Category.objects.create(name='Voucher Category', slug='voucher-cat')
    _p_a, variant_a = _make_product(store_a, title='In A', price='100.00')
    _p_cat, variant_cat = _make_product(
        store_a, title='Categorized', price='300.00', category=category
    )
    _p_b, variant_b = _make_product(store_b, title='In B', price='500.00')
    Voucher.objects.create(
        scope=VoucherScope.SELLER,
        store=store_a,
        code='STORE10',
        title='Store A 10%',
        discount_type=VoucherDiscountType.PERCENTAGE,
        value=Decimal('10.00'),
    )

    # A mixed cart: only Store A's lines are eligible (100.00 + 300.00).
    _cart_with(buyer, variant_a)
    _cart_with(buyer, variant_cat)
    _cart_with(buyer, variant_b)
    response = client.post(
        VALIDATE, {'code': 'STORE10'}, content_type='application/json'
    )
    assert response.status_code == 200, response.content
    assert response.json()['eligible_subtotal'] == 400.0
    assert response.json()['discount_total'] == 40.0

    # A cart with only Store B's lines → the store voucher refuses outright.
    cart = Cart.objects.get(user=buyer)
    cart.items.exclude(variant=variant_b).delete()
    response = client.post(
        VALIDATE, {'code': 'STORE10'}, content_type='application/json'
    )
    assert response.status_code == 400
    assert response.json()['error'] == 'voucher_store_mismatch'

    # Category targeting narrows the same cart to the categorized product.
    cat_voucher = _platform_voucher(code='CATTEN')
    VoucherEligibility.objects.create(voucher=cat_voucher, category=category)
    _cart_with(buyer, variant_cat)
    response = client.post(
        VALIDATE, {'code': 'CATTEN'}, content_type='application/json'
    )
    assert response.status_code == 200, response.content
    assert response.json()['eligible_subtotal'] == 300.0
    assert response.json()['discount_total'] == 30.0


def test_model_constraints_guard_the_rules():
    _seller, store = _make_active_store('seller9@example.com', slug='store-nine')

    def _expect_integrity_error(factory):
        with pytest.raises(IntegrityError), transaction.atomic():
            factory()

    # Seller vouchers need a store; platform vouchers must not have one.
    _expect_integrity_error(
        lambda: Voucher.objects.create(
            scope=VoucherScope.SELLER, code='NOSHOP', title='x',
            discount_type=VoucherDiscountType.FIXED, value=Decimal('10.00'),
        )
    )
    _expect_integrity_error(
        lambda: Voucher.objects.create(
            scope=VoucherScope.PLATFORM, store=store, code='SHOPFUL', title='x',
            discount_type=VoucherDiscountType.FIXED, value=Decimal('10.00'),
        )
    )
    # Value is always positive; a percentage can never exceed 100.
    _expect_integrity_error(
        lambda: _platform_voucher(code='ZERO', value=Decimal('0.00'))
    )
    _expect_integrity_error(
        lambda: _platform_voucher(code='OVER', value=Decimal('150.00'))
    )
    # The window must move forward in time.
    now = timezone.now()
    _expect_integrity_error(
        lambda: _platform_voucher(
            code='BACKWARD', starts_at=now, ends_at=now - timedelta(hours=1)
        )
    )
    # Targeting rows need a target; a target repeats never.
    voucher = _platform_voucher(code='TARGETS')
    _expect_integrity_error(lambda: VoucherEligibility.objects.create(voucher=voucher))
    product, _variant = _make_product(store, title='Targeted', price='10.00')
    VoucherEligibility.objects.create(voucher=voucher, product=product)
    _expect_integrity_error(
        lambda: VoucherEligibility.objects.create(voucher=voucher, product=product)
    )


def test_redeem_ledger_rechecks_counters_and_is_single_write_per_order():
    """The redemption path a parallel checkout would hit after losing the
    race: the counters are re-read under the row lock and refuse — and the
    ledger can never hold two rows for one voucher+order pair."""
    client = Client()
    buyer = _sign_in(client, 'buyer10@example.com')
    address_id = _add_address(client)
    _seller, store = _make_active_store('seller10@example.com', slug='store-ten')
    _product, variant = _make_product(store, price='200.00', stock=20)
    voucher = _platform_voucher(code='LOCKME', per_user_limit=1)

    _cart_with(buyer, variant, quantity=1)
    response = _checkout(client, address_id, 'LOCKME')
    assert response.status_code == 201, response.content
    order = Order.objects.get()

    plan = {
        'voucher': voucher,
        'eligible_subtotal': Decimal('200.00'),
        'discount_total': Decimal('20.00'),
    }
    with pytest.raises(promotion_services.VoucherError) as excinfo:
        promotion_services.redeem_voucher(plan, buyer, order)
    assert excinfo.value.code == 'voucher_user_limit'

    # Unique(voucher, order): one usage row per order, enforced by the DB.
    second = _platform_voucher(code='SECOND', per_user_limit=None)
    VoucherUsage.objects.create(
        voucher=second, user=buyer, order=order, discount_amount=Decimal('1.00')
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        VoucherUsage.objects.create(
            voucher=second, user=buyer, order=order, discount_amount=Decimal('1.00')
        )



