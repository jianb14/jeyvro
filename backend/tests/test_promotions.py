"""Phase 16 gate tests — Promotions, Campaigns, and Vouchers (ROADMAP §16.1 & §16.2).

Verifies the server-side promotion engine:
1. Product discounts apply automatically to matching lines.
2. Flash sale promotions override regular prices during active windows.
3. Bundle discounts apply when quantity meets the threshold.
4. Free shipping promotions waive delivery fees.
5. Inactive / expired promotions do not apply.
6. Auto-promotions stack with vouchers cleanly.
7. Buy X get Y only fires once the buy quantity is met, caps its free
   units at `get_qty`, and stacks on what earlier rules left (§16.2).
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
from apps.catalog.models import Category, Inventory, Product, Variant
from apps.orders import services as order_services
from apps.orders.models import Order
from apps.promotions import services as promotion_services
from apps.promotions.models import (
    Campaign,
    Promotion,
    PromotionUsage,
    Voucher,
    VoucherDiscountType,
    VoucherScope,
)
from apps.stores.models import Store

pytestmark = pytest.mark.django_db
PASSWORD = 'Str0ng!Passw0rd'


def _make_store_and_product(name='Alpha Store', price=Decimal('100.00'), stock=10):
    user = User.objects.create_user(
        email=f'{name.lower().replace(" ", "")}@example.com',
        first_name=name,
        last_name='Seller',
        password=PASSWORD,
        is_seller=True,
    )
    store = Store.objects.create(
        user=user,
        name=name,
        slug=name.lower().replace(' ', '-'),
        status=Store.Status.ACTIVE,
    )
    cat = Category.objects.create(name='Gadgets', slug=f'gadgets-{name.lower().replace(" ", "-")}')
    prod = Product.objects.create(
        store=store,
        category=cat,
        title=f'{name} Product',
        slug=f'{name.lower().replace(" ", "-")}-prod',
        base_price=price,
        status=Product.Status.PUBLISHED,
    )
    variant = Variant.objects.create(
        product=prod,
        name='Default',
        sku=f'SKU-{name.replace(" ", "")}',
        price=price,
        is_default=True,
    )
    catalog_services.ensure_inventory(variant, initial_on_hand=stock)
    return user, store, prod, variant


def _add_product(store, name, price=Decimal('100.00'), stock=10):
    """A second product in an existing store (buy-X-get-Y needs a pair)."""
    prod = Product.objects.create(
        store=store,
        category=Category.objects.first(),
        title=name,
        slug=name.lower().replace(' ', '-'),
        base_price=price,
        status=Product.Status.PUBLISHED,
    )
    variant = Variant.objects.create(
        product=prod,
        name='Default',
        sku=f'SKU-{name.replace(" ", "")}',
        price=price,
        is_default=True,
    )
    catalog_services.ensure_inventory(variant, initial_on_hand=stock)
    return prod, variant



def test_product_discount_auto_evaluates():
    _user, store, prod, variant = _make_store_and_product('Store1', price=Decimal('200.00'))
    campaign = Campaign.objects.create(
        scope='seller',
        store=store,
        name='Storewide Promo Campaign',
    )
    promo = Promotion.objects.create(
        campaign=campaign,
        label='20% Off Storewide',
        kind='product_discount',
        discount_type='percentage',
        value=Decimal('20.00'),
    )

    lines = [promotion_services.line_entry(0, prod, 2, Decimal('200.00'), Decimal('400.00'))]
    eval_result = promotion_services.evaluate_store_lines(store, lines)

    assert eval_result['discount_total'] == Decimal('80.00')
    assert len(eval_result['applied']) == 1
    assert eval_result['applied'][0]['promotion'] == promo


def test_flash_sale_window_enforced():
    now = timezone.now()
    _user, store, prod, variant = _make_store_and_product('Store2', price=Decimal('100.00'))
    campaign = Campaign.objects.create(
        scope='seller',
        store=store,
        name='Flash Sale Campaign',
        starts_at=now - timedelta(days=2),
        ends_at=now - timedelta(days=1),
    )
    promo = Promotion.objects.create(
        campaign=campaign,
        label='Expired Flash Sale',
        kind='flash_sale',
        discount_type='fixed',
        value=Decimal('30.00'),
    )

    lines = [promotion_services.line_entry(0, prod, 1, Decimal('100.00'), Decimal('100.00'))]
    eval_result = promotion_services.evaluate_store_lines(store, lines)
    assert eval_result['discount_total'] == Decimal('0.00')
    assert len(eval_result['applied']) == 0

    # Make campaign active now
    campaign.ends_at = now + timedelta(days=1)
    campaign.save()
    eval_result2 = promotion_services.evaluate_store_lines(store, lines)
    assert eval_result2['discount_total'] == Decimal('30.00')


def test_bundle_discount_requires_min_quantity():
    _user, store, prod, variant = _make_store_and_product('Store3', price=Decimal('50.00'))
    campaign = Campaign.objects.create(
        scope='seller',
        store=store,
        name='Bundle Campaign',
    )
    Promotion.objects.create(
        campaign=campaign,
        label='Buy 3 Get 15% off',
        kind='bundle',
        min_qty=3,
        discount_type='percentage',
        value=Decimal('15.00'),
    )

    lines_2 = [promotion_services.line_entry(0, prod, 2, Decimal('50.00'), Decimal('100.00'))]
    res_2 = promotion_services.evaluate_store_lines(store, lines_2)
    assert res_2['discount_total'] == Decimal('0.00')

    lines_3 = [promotion_services.line_entry(0, prod, 3, Decimal('50.00'), Decimal('150.00'))]
    res_3 = promotion_services.evaluate_store_lines(store, lines_3)
    assert res_3['discount_total'] == Decimal('22.50')


def test_free_shipping_flag_set():
    _user, store, prod, variant = _make_store_and_product('Store4', price=Decimal('80.00'))
    campaign = Campaign.objects.create(
        scope='seller',
        store=store,
        name='Free Delivery Campaign',
    )
    Promotion.objects.create(
        campaign=campaign,
        label='Free Delivery Promo',
        kind='free_shipping',
        discount_type='fixed',
        value=Decimal('0.00'),
    )

    waiver = promotion_services.find_shipping_waiver(store, Decimal('80.00'))
    assert waiver is not None
    assert waiver.label == 'Free Delivery Promo'




def test_auto_promo_and_voucher_stack_in_order_creation():
    _store_user, store, _prod, variant = _make_store_and_product('Store5', price=Decimal('100.00'), stock=10)
    buyer = User.objects.create_user(
        email='buyer_stack@example.com',
        first_name='Buyer',
        last_name='Stack',
        password=PASSWORD,
    )
    address = buyer.addresses.create(
        full_name='Buyer Stack',
        phone='09171112233',
        line1='100 Rizal St',
        city='Manila',
        province='Metro Manila',
        postal_code='1000',
    )

    campaign = Campaign.objects.create(
        scope='seller',
        store=store,
        name='Auto 10 Campaign',
    )
    Promotion.objects.create(
        campaign=campaign,
        label='Store 10% Auto',
        kind='product_discount',
        discount_type='percentage',
        value=Decimal('10.00'),
    )

    voucher = Voucher.objects.create(
        code='SAVE20',
        title='Save 20',
        scope=VoucherScope.PLATFORM,
        discount_type=VoucherDiscountType.FIXED,
        value=Decimal('20.00'),
        min_spend=Decimal('50.00'),
    )

    cart = Cart.objects.create(user=buyer)
    cart.items.create(variant=variant, quantity=2)

    order = order_services.create_order(
        buyer,
        address_id=address.id,
        payment_method='cod',
        voucher_code='SAVE20',
    )

    assert order.subtotal == Decimal('200.00')
    assert order.promotion_discount == Decimal('20.00')
    assert order.discount_total == Decimal('20.00')
    assert order.voucher_code == 'SAVE20'
    assert order.grand_total == Decimal('200.00') + order.shipping_total - Decimal('40.00')

    assert PromotionUsage.objects.filter(order=order).count() == 1
    assert AuditLog.objects.filter(action='voucher.redeemed', object_id=str(order.id)).exists()


def test_seller_promotion_crud_api():
    client = Client()
    seller_user, store, _prod, _variant = _make_store_and_product('Store6')
    client.force_login(seller_user)

    res = client.post(
        '/api/v1/seller/promotions/',
        data={
            'name': 'Weekend Special',
            'kind': 'product_discount',
            'discount_type': 'percentage',
            'value': '15.00',
            'min_spend': '0.00',
            'target_type': 'all',
        },
        content_type='application/json',
    )
    assert res.status_code == 201
    promo_id = res.json()['id']
    assert res.json()['label'] == 'Weekend Special'

    patch_res = client.patch(
        f'/api/v1/seller/promotions/{promo_id}/',
        data={'is_active': False},
        content_type='application/json',
    )
    assert patch_res.status_code == 200
    assert patch_res.json()['is_active'] is False

    del_res = client.delete(f'/api/v1/seller/promotions/{promo_id}/')
    assert del_res.status_code == 200
    p = Promotion.objects.get(pk=promo_id)
    assert p.is_active is False


# --- Buy X get Y (§16.2) ------------------------------------------------------


def _bxgy(store, buy_product, get_product, **overrides):
    """A buy-X-get-Y rule: buy N of one product, get M of another % off."""
    data = {
        'campaign': Campaign.objects.create(
            scope='seller', store=store, name='BXGY Campaign'
        ),
        'label': 'Buy 2 Get 1',
        'kind': 'buy_x_get_y',
        'discount_type': 'percentage',
        'value': Decimal('50.00'),
        'buy_product': buy_product,
        'buy_qty': 2,
        'get_product': get_product,
        'get_qty': 1,
    }
    data.update(overrides)
    return Promotion.objects.create(**data)


def test_buy_x_get_y_discounts_the_get_product_once_the_buy_quantity_is_met():
    _user, store, buy_product, _buy_variant = _make_store_and_product(
        'BxgyStore', price=Decimal('200.00')
    )
    get_product, _variant = _add_product(store, 'Bxgy Gift', price=Decimal('100.00'))
    promo = _bxgy(store, buy_product, get_product)

    # 2 units of the buy product, 1 unit of the get product at 100.00.
    lines = [
        promotion_services.line_entry(
            0, buy_product, 2, Decimal('200.00'), Decimal('400.00')
        ),
        promotion_services.line_entry(
            1, get_product, 1, Decimal('100.00'), Decimal('100.00')
        ),
    ]
    result = promotion_services.evaluate_store_lines(store, lines)

    assert result['discount_total'] == Decimal('50.00')
    assert len(result['applied']) == 1
    assert result['applied'][0]['promotion'] == promo
    # Only the get line carries the badge, and only 50.00 of it.
    assert result['line_discounts'] == {1: Decimal('50.00')}
    assert result['labels'] == {1: 'Buy 2 Get 1'}


def test_buy_x_get_y_does_nothing_below_the_buy_quantity():
    _user, store, buy_product, _variant = _make_store_and_product(
        'BxgyStore2', price=Decimal('200.00')
    )
    get_product, _v2 = _add_product(store, 'Bxgy Gift Two', price=Decimal('100.00'))
    _bxgy(store, buy_product, get_product)  # needs 2 units of the buy product

    lines = [
        promotion_services.line_entry(
            0, buy_product, 1, Decimal('200.00'), Decimal('200.00')
        ),
        promotion_services.line_entry(
            1, get_product, 1, Decimal('100.00'), Decimal('100.00')
        ),
    ]
    result = promotion_services.evaluate_store_lines(store, lines)

    assert result['discount_total'] == Decimal('0.00')
    assert result['applied'] == []
    assert result['line_discounts'] == {}


def test_buy_x_get_y_only_discounts_as_many_get_units_as_it_promises():
    """`get_qty` caps the giveaway — three in the cart, one on the house."""
    _user, store, buy_product, _variant = _make_store_and_product(
        'BxgyStore3', price=Decimal('200.00')
    )
    get_product, _v2 = _add_product(store, 'Bxgy Gift Three', price=Decimal('100.00'))
    _bxgy(store, buy_product, get_product)  # 2 bought, 1 free unit

    lines = [
        promotion_services.line_entry(
            0, buy_product, 2, Decimal('200.00'), Decimal('400.00')
        ),
        promotion_services.line_entry(
            1, get_product, 3, Decimal('100.00'), Decimal('300.00')
        ),
    ]
    result = promotion_services.evaluate_store_lines(store, lines)

    # One of the three units (100.00 of the 300.00 line) at 50% off.
    assert result['discount_total'] == Decimal('50.00')
    assert result['line_discounts'] == {1: Decimal('50.00')}


def test_buy_x_get_y_stacks_only_on_what_earlier_rules_left():
    """Rules stack in id order against the remainder — never below zero."""
    _user, store, buy_product, _variant = _make_store_and_product(
        'BxgyStore4', price=Decimal('200.00')
    )
    get_product, _v2 = _add_product(store, 'Bxgy Gift Four', price=Decimal('100.00'))
    campaign = Campaign.objects.create(
        scope='seller', store=store, name='Storewide Campaign'
    )
    # Created first, so the storewide 10% runs before the BXGY rule.
    Promotion.objects.create(
        campaign=campaign,
        label='Storewide 10%',
        kind='product_discount',
        discount_type='percentage',
        value=Decimal('10.00'),
    )
    _bxgy(store, buy_product, get_product)

    lines = [
        promotion_services.line_entry(
            0, buy_product, 2, Decimal('200.00'), Decimal('400.00')
        ),
        promotion_services.line_entry(
            1, get_product, 1, Decimal('100.00'), Decimal('100.00')
        ),
    ]
    result = promotion_services.evaluate_store_lines(store, lines)

    # 10% of the whole store first (40.00 + 10.00), then 50% of what is
    # left on the get line (90.00 → 45.00).
    assert result['line_discounts'] == {0: Decimal('40.00'), 1: Decimal('55.00')}
    assert result['discount_total'] == Decimal('95.00')
    # The first rule to save a line keeps the badge.
    assert result['labels'][1] == 'Storewide 10%'
    assert len(result['applied']) == 2


def test_buy_x_get_y_rule_must_name_its_pair_and_stay_percentage():
    """The rule's shape is DB-constrained, not a service convention."""

    def _expect_integrity_error(factory):
        with pytest.raises(IntegrityError), transaction.atomic():
            factory()

    _user, store, buy_product, _variant = _make_store_and_product(
        'BxgyStore5', price=Decimal('200.00')
    )
    get_product, _v2 = _add_product(store, 'Bxgy Gift Five', price=Decimal('100.00'))

    # A buy-X-get-Y rule with no get product is nonsense.
    _expect_integrity_error(
        lambda: _bxgy(store, buy_product, None, get_qty=None)
    )
    # A fixed-amount BXGY is not supported by the engine.
    _expect_integrity_error(
        lambda: _bxgy(
            store,
            buy_product,
            get_product,
            discount_type='fixed',
            value=Decimal('25.00'),
        )
    )
    # A plain discount rule may not smuggle in the buy/get pair.
    campaign = Campaign.objects.create(
        scope='seller', store=store, name='Plain Campaign'
    )
    _expect_integrity_error(
        lambda: Promotion.objects.create(
            campaign=campaign,
            label='Not a BXGY',
            kind='product_discount',
            discount_type='percentage',
            value=Decimal('10.00'),
            buy_product=buy_product,
            buy_qty=2,
        )
    )


def test_seller_api_builds_a_buy_x_get_y_rule_and_refuses_bad_ones():
    """The desk can create the rule; a broken pair is a 400, never a 500."""
    client = Client()
    seller_user, store, buy_product, _variant = _make_store_and_product(
        'BxgyApi', price=Decimal('200.00')
    )
    get_product, _v2 = _add_product(store, 'Bxgy Api Gift', price=Decimal('100.00'))
    _other_user, _other_store, other_product, _ov = _make_store_and_product(
        'BxgyRival', price=Decimal('200.00')
    )
    client.force_login(seller_user)

    created = client.post(
        '/api/v1/seller/promotions/',
        data={
            'name': 'Buy 2 Get 1',
            'kind': 'buy_x_get_y',
            'discount_type': 'percentage',
            'value': '50.00',
            'buy_product_id': buy_product.id,
            'buy_qty': 2,
            'get_product_id': get_product.id,
            'get_qty': 1,
        },
        content_type='application/json',
    )
    assert created.status_code == 201, created.content
    body = created.json()
    assert body['kind'] == 'buy_x_get_y'
    assert body['buy_product_id'] == buy_product.id
    assert body['buy_qty'] == 2
    assert body['get_product_id'] == get_product.id
    assert body['get_qty'] == 1
    assert Promotion.objects.get(pk=body['id']).get_product_id == get_product.id

    def _post(**overrides):
        payload = {
            'name': 'Bad BXGY',
            'kind': 'buy_x_get_y',
            'discount_type': 'percentage',
            'value': '50.00',
            'buy_product_id': buy_product.id,
            'buy_qty': 2,
            'get_product_id': get_product.id,
            'get_qty': 1,
        }
        # A None override drops the key, so the serializer sees the field as
        # omitted rather than explicitly null.
        for key, value in overrides.items():
            if value is None:
                payload.pop(key, None)
            else:
                payload[key] = value
        return client.post(
            '/api/v1/seller/promotions/',
            data=payload,
            content_type='application/json',
        )

    # Half a rule is not a rule.
    missing = _post(get_product_id=None, get_qty=None)
    assert missing.status_code == 400
    assert missing.json()['error'] == 'validation_error'
    assert 'get_product_id' in missing.json()['field_errors']
    assert 'get_qty' in missing.json()['field_errors']

    # The engine only judges percentages for this kind.
    fixed = _post(discount_type='fixed')
    assert fixed.status_code == 400
    assert 'discount_type' in fixed.json()['field_errors']

    # A rival store's product is not this seller's to give away.
    foreign = _post(get_product_id=other_product.id)
    assert foreign.status_code == 400
    assert foreign.json()['error'] == 'unknown_product'

    # And the pair belongs to no other kind.
    assert _post(kind='product_discount').status_code == 400
    assert Promotion.objects.filter(campaign__name='Bad BXGY').count() == 0


