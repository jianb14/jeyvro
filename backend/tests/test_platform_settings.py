"""Phase 13.6 gate tests — platform settings (§6 v1.13, §4 matrix).

Contracts proven here:
1. Reads are administrator/finance/operations; everyone else — other
   staff groups, customers, anonymous — gets 403.
2. General edits are administrator-only; the commission rate is also
   finance's to change (§4); every edit writes an AuditLog row carrying
   the per-field from→to diff and the row stays a singleton.
3. Validation is server-side: rate, fees, window, name and email refuse
   out-of-range input with the {error, field_errors} envelope.
4. Consumers obey the row: COD shuts checkout down entirely (rollback
   proven — no order, payment, or reservation survives), the payment
   window drives `expires_at`, new stores seed from the shipping
   defaults, new accounts seed from the notification defaults.
5. The public endpoint leaks only the platform name and support contact.
"""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from django.test import Client
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.catalog import services as catalog_services
from apps.catalog.models import Inventory, Product, Variant
from apps.orders.models import Order
from apps.payments.models import Payment
from apps.platform.models import PlatformSettings
from apps.platform.services import get_settings
from apps.stores import services as store_services
from apps.stores.models import Store

pytestmark = pytest.mark.django_db

PASSWORD = 'Str0ng!Passw0rd'
SETTINGS = '/api/v1/admin/settings/'
COMMISSION = '/api/v1/admin/settings/commission/'
PUBLIC = '/api/v1/platform/public/'
REGISTER = '/api/v1/auth/register'
LOGIN = '/api/v1/auth/login'
ADDRESSES = '/api/v1/auth/addresses/'
CART_ITEMS = '/api/v1/cart/items'
CHECKOUT = '/api/v1/checkout/'
CHECKOUT_ORDERS = '/api/v1/checkout/orders'
PREFERENCES = '/api/v1/auth/notification-preferences'

ADDRESS_PAYLOAD = {
    'full_name': 'Pilar Buyer',
    'phone': '09171234567',
    'line1': '12 Mabini Street',
    'line2': '',
    'city': 'Quezon City',
    'province': 'Metro Manila',
    'postal_code': '1100',
}


def _make_user(email, *, group=None, is_staff=None):
    user = User.objects.create_user(
        email=email,
        password=PASSWORD,
        first_name=email.split('@')[0].capitalize(),
        last_name='User',
        is_staff=group is not None if is_staff is None else is_staff,
    )
    if group:
        grp, _ = Group.objects.get_or_create(name=group)
        user.groups.add(grp)
    return user


def _client_for(user):
    client = Client()
    client.force_login(user)
    return client


def _patch(client, payload, path=SETTINGS):
    return client.patch(path, payload, content_type='application/json')


def _admin():
    return _make_user('settingsadmin@example.com', group='administrator')


def _catalog():
    """An active store with one published, stocked variant."""
    seller = _make_user('settingsseller@example.com')
    store = Store.objects.create(
        user=seller,
        name='Settings Store',
        status=Store.Status.ACTIVE,
        shipping_flat_fee=Decimal('0.00'),
    )
    product = Product.objects.create(
        store=store,
        title='Settings Product',
        base_price=Decimal('299.00'),
        status=Product.Status.PUBLISHED,
    )
    variant = Variant.objects.create(
        product=product, name='Default', price=Decimal('299.00'), is_default=True,
    )
    catalog_services.ensure_inventory(variant, initial_on_hand=5)
    return store, variant


def _buyer(client, email='settingsbuyer@example.com'):
    """Registers + signs in the buyer and returns their address id."""
    credentials = {'email': email, 'password': PASSWORD}
    register = client.post(REGISTER, credentials, content_type='application/json')
    assert register.status_code == 201, register.content
    login = client.post(LOGIN, credentials, content_type='application/json')
    assert login.status_code == 200, login.content
    response = client.post(
        ADDRESSES, ADDRESS_PAYLOAD, content_type='application/json'
    )
    assert response.status_code == 201, response.content
    return response.json()['id']


def _add_to_cart(client, variant):
    response = client.post(
        CART_ITEMS,
        {'variant_id': variant.id, 'quantity': 1},
        content_type='application/json',
    )
    assert response.status_code == 200, response.content


def _checkout(client, address_id, method=None):
    payload = {'address_id': address_id}
    if method is not None:
        payload['payment_method'] = method
    return client.post(CHECKOUT_ORDERS, payload, content_type='application/json')


# --- 13.6.1 Permission matrix ----------------------------------------------

def test_settings_reads_are_group_gated():
    for group in ('administrator', 'finance', 'operations'):
        user = _make_user(f'read{group}@example.com', group=group)
        response = _client_for(user).get(SETTINGS)
        assert response.status_code == 200, response.content
        body = response.json()
        assert body['platform_name'] == 'Jeyvro'
        assert body['cod_enabled'] is True
        assert body['payment_expiry_hours'] == 24

    for group in ('support', 'moderator'):
        user = _make_user(f'read{group}@example.com', group=group)
        assert _client_for(user).get(SETTINGS).status_code == 403

    customer = _make_user('readcustomer@example.com', is_staff=False)
    assert _client_for(customer).get(SETTINGS).status_code == 403
    assert Client().get(SETTINGS).status_code == 403


def test_general_edits_are_administrator_only_and_audited():
    for group in ('finance', 'operations', 'support'):
        user = _make_user(f'edit{group}@example.com', group=group)
        response = _patch(_client_for(user), {'platform_name': 'Nope'})
        assert response.status_code == 403, response.content
    assert get_settings().platform_name == 'Jeyvro'

    admin = _admin()
    response = _patch(_client_for(admin), {
        'platform_name': 'Jeyvro PH',
        'support_email': 'help@jeyvro.ph',
    })
    assert response.status_code == 200, response.content
    body = response.json()
    assert body['platform_name'] == 'Jeyvro PH'
    assert body['support_email'] == 'help@jeyvro.ph'
    assert body['updated_by_email'] == admin.email

    settings_obj = PlatformSettings.objects.get()  # exactly one row
    assert settings_obj.platform_name == 'Jeyvro PH'
    assert settings_obj.updated_by_id == admin.pk

    event = AuditLog.objects.filter(action='platform_settings_update').get()
    assert event.actor_id == admin.pk
    assert event.detail['scope'] == 'general'
    assert event.detail['changes']['platform_name'] == {
        'from': 'Jeyvro', 'to': 'Jeyvro PH',
    }
    assert event.detail['changes']['support_email']['to'] == 'help@jeyvro.ph'


def test_finance_can_adjust_commission_only():
    finance = _make_user('settingsfinance@example.com', group='finance')

    denied = _patch(_client_for(finance), {'platform_name': 'Nope'})
    assert denied.status_code == 403, denied.content
    assert get_settings().platform_name == 'Jeyvro'

    accepted = _patch(
        _client_for(finance), {'commission_rate_percent': '7.50'}, COMMISSION
    )
    assert accepted.status_code == 200, accepted.content
    assert accepted.json()['commission_rate_percent'] == '7.50'
    assert PlatformSettings.objects.get().commission_rate_percent == Decimal('7.50')

    event = AuditLog.objects.filter(action='platform_settings_update').get()
    assert event.detail['scope'] == 'commission'
    assert event.detail['changes']['commission_rate_percent'] == {
        'from': '0.00', 'to': '7.50',
    }

    # Administrator shares the commission path; other groups do not.
    admin = _admin()
    assert _patch(
        _client_for(admin), {'commission_rate_percent': '5.00'}, COMMISSION
    ).status_code == 200
    for group in ('support', 'operations', 'moderator'):
        user = _make_user(f'rate{group}@example.com', group=group)
        assert _patch(
            _client_for(user), {'commission_rate_percent': '1.00'}, COMMISSION
        ).status_code == 403


# --- 13.6.2 Server-side validation -----------------------------------------

def test_validation_refuses_out_of_range_values():
    admin = _client_for(_admin())
    cases = [
        ({'commission_rate_percent': '101'}, 'commission_rate_percent'),
        ({'commission_rate_percent': '-0.01'}, 'commission_rate_percent'),
        ({'default_shipping_flat_fee': '-1.00'}, 'default_shipping_flat_fee'),
        ({'default_free_shipping_threshold': '-1.00'}, 'default_free_shipping_threshold'),
        ({'payment_expiry_hours': 0}, 'payment_expiry_hours'),
        ({'payment_expiry_hours': 169}, 'payment_expiry_hours'),
        ({'platform_name': ''}, 'platform_name'),
        ({'support_email': 'not-an-email'}, 'support_email'),
    ]
    for payload, field in cases:
        path = COMMISSION if 'commission' in next(iter(payload)) else SETTINGS
        response = _patch(admin, payload, path)
        assert response.status_code == 400, (payload, response.content)
        body = response.json()
        assert body['error'] == 'validation_error'
        assert field in body['field_errors'], (payload, body)

    settings_obj = get_settings()  # nothing slipped through
    assert settings_obj.commission_rate_percent == Decimal('0.00')
    assert settings_obj.payment_expiry_hours == 24
    assert settings_obj.platform_name == 'Jeyvro'


# --- 13.6.3 Feature switches drive real consumers ---------------------------

def test_cod_switch_gates_checkout_and_rolls_back():
    admin = _client_for(_admin())
    store, variant = _catalog()
    client = Client()
    address_id = _buyer(client)
    _add_to_cart(client, variant)

    preview = client.get(CHECKOUT).json()
    options = {option['id']: option for option in preview['payment_methods']}
    assert options['cod']['available'] is True

    flipped = _patch(admin, {'cod_enabled': False})
    assert flipped.status_code == 200, flipped.content
    assert flipped.json()['cod_enabled'] is False

    preview = client.get(CHECKOUT).json()
    options = {option['id']: option for option in preview['payment_methods']}
    assert options['cod']['available'] is False
    assert 'switched off' in options['cod']['description']

    # The whole order refuses to exist — nothing partial survives.
    refused = _checkout(client, address_id)  # no method → COD default
    assert refused.status_code == 400, refused.content
    assert refused.json()['error'] == 'payment_method_unavailable'
    assert Order.objects.count() == 0
    assert Payment.objects.count() == 0
    assert Inventory.objects.get(variant=variant).reserved == 0

    # Switch it back on and checkout works again.
    assert _patch(admin, {'cod_enabled': True}).status_code == 200
    accepted = _checkout(client, address_id)
    assert accepted.status_code == 201, accepted.content
    assert accepted.json()['payment']['method'] == 'cod'


def test_payment_window_comes_from_the_platform_row(settings):
    from apps.payments.services import payment_expiry_hours

    assert payment_expiry_hours() == 24  # the row's default window

    settings.PAYMENTS_GATEWAY_SANDBOX = True
    admin = _client_for(_admin())
    assert _patch(admin, {'payment_expiry_hours': 2}).status_code == 200
    assert payment_expiry_hours() == 2

    store, variant = _catalog()
    client = Client()
    address_id = _buyer(client)
    _add_to_cart(client, variant)
    response = _checkout(client, address_id, 'gcash')
    assert response.status_code == 201, response.content

    payment = Payment.objects.get(
        reference=response.json()['payment']['reference']
    )
    window = payment.expires_at - payment.created_at
    assert timedelta(hours=1, minutes=55) <= window <= timedelta(hours=2, minutes=5)


def test_shipping_defaults_seed_new_stores_only():
    before = store_services.apply_as_seller(
        _make_user('seedbefore@example.com'), store_name='Before Change'
    )
    assert before.store.shipping_flat_fee == Decimal('0.00')
    assert before.store.free_shipping_threshold is None

    admin = _client_for(_admin())
    response = _patch(admin, {
        'default_shipping_flat_fee': '49.00',
        'default_free_shipping_threshold': '500.00',
    })
    assert response.status_code == 200, response.content

    after = store_services.apply_as_seller(
        _make_user('seedafter@example.com'), store_name='After Change'
    )
    assert after.store.shipping_flat_fee == Decimal('49.00')
    assert after.store.free_shipping_threshold == Decimal('500.00')

    # Stores created before the change keep exactly what they had.
    before.store.refresh_from_db()
    assert before.store.shipping_flat_fee == Decimal('0.00')
    assert before.store.free_shipping_threshold is None


def test_notification_defaults_apply_to_new_rows_only():
    existing = _make_user('notified@example.com')
    own_choice = _client_for(existing).get(PREFERENCES).json()
    assert own_choice['promotions_email'] is False  # model default

    admin = _client_for(_admin())
    response = _patch(admin, {
        'default_promotions_email': True,
        'default_order_updates_email': False,
    })
    assert response.status_code == 200, response.content

    fresh = _client_for(_make_user('notified2@example.com')).get(PREFERENCES)
    assert fresh.status_code == 200, fresh.content
    assert fresh.json()['promotions_email'] is True
    assert fresh.json()['order_updates_email'] is False

    # The first account's own row was never overwritten by the platform.
    again = _client_for(existing).get(PREFERENCES).json()
    assert again['promotions_email'] is False
    assert again['order_updates_email'] is True


# --- 13.6.4 Public subset + singleton ---------------------------------------

def test_public_endpoint_serves_only_name_and_contact():
    admin = _client_for(_admin())
    assert _patch(admin, {
        'platform_name': 'Jeyvro PH',
        'support_email': 'help@jeyvro.ph',
    }).status_code == 200
    finance = _make_user('publicfinance@example.com', group='finance')
    assert _patch(
        _client_for(finance), {'commission_rate_percent': '5.00'}, COMMISSION
    ).status_code == 200

    response = Client().get(PUBLIC)
    assert response.status_code == 200, response.content
    body = response.json()
    assert set(body) == {'platform_name', 'support_email'}
    assert body == {'platform_name': 'Jeyvro PH', 'support_email': 'help@jeyvro.ph'}


def test_settings_stay_a_singleton_across_updates():
    admin = _client_for(_admin())
    assert _patch(admin, {'platform_name': 'One'}).status_code == 200
    finance = _make_user('singleton@example.com', group='finance')
    assert _patch(
        _client_for(finance), {'commission_rate_percent': '3.00'}, COMMISSION
    ).status_code == 200

    assert PlatformSettings.objects.count() == 1
    settings_obj = PlatformSettings.objects.get()
    assert settings_obj.platform_name == 'One'
    assert settings_obj.commission_rate_percent == Decimal('3.00')
    assert settings_obj.updated_by_id == finance.pk
    assert timezone.now() - settings_obj.updated_at < timedelta(minutes=5)


