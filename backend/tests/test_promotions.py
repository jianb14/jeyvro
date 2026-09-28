"""Phase 16 gate tests — Promotions, Campaigns, and Vouchers (ROADMAP §16.1 & §16.2).

Verifies the server-side promotion engine:
1. Product discounts apply automatically to matching lines.
2. Flash sale promotions override regular prices during active windows.
3. Bundle discounts apply when quantity meets the threshold.
4. Free shipping promotions waive delivery fees.
5. Inactive / expired promotions do not apply.
6. Auto-promotions stack with vouchers cleanly.
"""
from datetime import timedelta
from decimal import Decimal

import pytest
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


