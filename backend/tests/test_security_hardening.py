"""Phase 20.1 gate tests — application-security hardening (ROADMAP §20.1).

Contracts proven here:

1. **A tracking number is a bearer token, not an identity.** The public
   projection carries the journey and nothing else: no recipient, no phone,
   no address, no goods, no seller's handling notes. The whole record belongs
   to the order owner, the fulfilling seller and staff — the finding this slice
   was opened for.
2. **Deny by default** (§10.1): the project default is `IsAuthenticated`, and
   *every* DRF view class declares its own permissions or overrides
   `get_permissions` — the guard test fails the gate when a new view forgets,
   so nothing can ship public by accident (backend-api rule 6).
3. **The public surface is still public** — the flip closed nothing it should
   not have.
4. **CSRF is live**: an unsafe method on a session is refused without the
   token, and CORS answers only allowlisted origins — with credentials, which
   is what session auth over `credentials: 'include'` needs.
5. **Rate limiting refuses a flood**, and the endpoints worth abusing carry a
   tight `throttle_scope` on top of the generous per-user allowance.
"""
from decimal import Decimal

import pytest
from django.apps import apps as django_apps
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.test import Client, override_settings
from django.urls import get_resolver
from django.utils import timezone

from apps.accounts.models import Address, User
from apps.cart.models import Cart
from apps.catalog import services as catalog_services
from apps.catalog.models import Product, Variant
from apps.orders import services as order_services
from apps.stores.models import Store

from django.conf import settings

pytestmark = pytest.mark.django_db

PASSWORD = 'Str0ng!Passw0rd'
TRACK = '/api/v1/shipments/track/'
LOGIN = '/api/v1/auth/login'


def _make_user(email, *, group=None, is_staff=False):
    user = User.objects.create_user(
        email=email,
        password=PASSWORD,
        first_name=email.split('@')[0].capitalize(),
        last_name='User',
        is_staff=is_staff or bool(group),
    )
    if group:
        grp, _ = Group.objects.get_or_create(name=group)
        user.groups.add(grp)
    return user


def _client_for(user, **kwargs):
    client = Client(**kwargs)
    client.force_login(user)
    return client


def _shipped_parcel():
    """A real checkout driven to a dispatched parcel (§8, §10) with PII on it."""
    seller = _make_user('hardeningseller@example.com')
    store = Store.objects.create(
        user=seller,
        name='Hardening Store',
        status=Store.Status.ACTIVE,
        shipping_flat_fee=Decimal('50.00'),
    )
    seller.is_seller = True
    seller.save(update_fields=['is_seller'])
    product = Product.objects.create(
        store=store,
        title='Hardening Product',
        base_price=Decimal('500.00'),
        status=Product.Status.PUBLISHED,
    )
    variant = Variant.objects.create(
        product=product, name='Default', price=Decimal('500.00'), is_default=True
    )
    catalog_services.ensure_inventory(variant, initial_on_hand=20)

    buyer = _make_user('hardeningbuyer@example.com')
    address = Address.objects.create(
        user=buyer,
        full_name='Private Buyer',
        phone='09171234567',
        line1='9 Kalayaan Street',
        city='Quezon City',
        province='Metro Manila',
        postal_code='1100',
    )
    cart = Cart.objects.create(user=buyer)
    cart.items.create(variant=variant, quantity=1)
    order = order_services.create_order(buyer, address.id, payment_method='cod')
    seller_order = order.seller_orders.first()
    order_services.mark_seller_order_processing(seller_order, actor=seller)
    order_services.mark_seller_order_packed(seller_order, actor=seller)
    shipment = order_services.create_shipment(
        seller_order,
        carrier_code='manual',
        package_notes='Fragile — buyer asked to call before delivery',
        package_weight_grams=250,
        actor=seller,
    )
    return shipment, buyer, seller


# --- §20.1 the finding: a tracking number is not an identity -----------------


def test_public_tracking_never_returns_buyer_pii():
    """The journey is public; the person behind it is not (20.1)."""
    shipment, _buyer, _seller = _shipped_parcel()
    body = Client().get(f'{TRACK}{shipment.tracking_number}/').json()

    assert body['tracking_number'] == shipment.tracking_number
    assert body['status']
    assert 'shipped_at' in body and 'delivered_at' in body

    for private in (
        'recipient_name',
        'recipient_phone',
        'shipping_address_text',
        'package_notes',
        'items',
        'shipping_fee',
        'package_weight_grams',
    ):
        assert private not in body, private

    # Even the event prose stays back — status and timestamp are the journey.
    for event in body['tracking_events']:
        assert set(event) == {'status', 'occurred_at'}


def test_the_whole_record_is_for_the_buyer_the_seller_and_staff():
    shipment, buyer, seller = _shipped_parcel()
    admin = _make_user('hardeningadmin@example.com', group='administrator')
    url = f'{TRACK}{shipment.tracking_number}/'

    for user in (buyer, seller, admin):
        body = _client_for(user).get(url).json()
        assert body['recipient_name'] == 'Private Buyer'
        assert body['shipping_address_text']
        assert body['items']

    # A signed-in stranger is still a stranger: redacted rather than 403 —
    # public tracking is a feature; leaking the buyer through it was the bug.
    stranger = _make_user('hardeningstranger@example.com')
    assert 'recipient_name' not in _client_for(stranger).get(url).json()


# --- §20.1 deny by default (§10.1) ------------------------------------------


def test_the_project_default_is_deny():
    assert settings.REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES'] == [
        'rest_framework.permissions.IsAuthenticated'
    ]


def test_only_session_authentication_is_accepted():
    """DRF's default would also enable HTTP Basic; this API is session-only,
    and a Basic header must not be a way in."""
    import base64

    from rest_framework.authentication import BasicAuthentication, SessionAuthentication
    from rest_framework.views import APIView

    assert APIView.authentication_classes == [SessionAuthentication]
    assert BasicAuthentication not in APIView.authentication_classes

    buyer = _make_user('hardeningbasic@example.com')
    credentials = base64.b64encode(
        f'{buyer.email}:{PASSWORD}'.encode()
    ).decode()
    refused = Client().get(
        '/api/v1/auth/me', HTTP_AUTHORIZATION=f'Basic {credentials}'
    )
    assert refused.status_code in (401, 403)


def _routed_view_classes():
    """Every DRF view class the URLconf actually routes (not an unused import)."""
    from rest_framework.views import APIView

    def walk(patterns):
        for entry in patterns:
            callback = getattr(entry, 'callback', None)
            for candidate in (
                getattr(callback, 'cls', None),
                getattr(callback, 'view_class', None),
            ):
                if isinstance(candidate, type) and issubclass(candidate, APIView):
                    yield candidate
            nested = getattr(entry, 'url_patterns', None)
            if nested is None:
                nested = getattr(getattr(entry, 'pattern', None), 'url_patterns', None)
            if nested:
                yield from walk(nested)

    return set(walk(get_resolver().url_patterns))


def test_every_view_declares_its_own_permissions():
    """The guard: a new view that forgets to speak cannot ship (rule 6)."""
    classes = _routed_view_classes()
    assert len(classes) > 40, 'the URLconf walk found suspiciously few views'

    undeclared = sorted(
        f'{view.__module__}.{view.__name__}'
        for view in classes
        # Only our own code is ours to police; DRF's router root is framework
        # territory and declares its own defaults.
        if view.__module__.startswith('apps.')
        and 'permission_classes' not in view.__dict__
        and view.__dict__.get('get_permissions') is None
    )
    assert undeclared == []


def test_the_public_surface_is_still_public():
    """Deny-by-default must not have closed what is public by design."""
    _shipped_parcel()
    product = Product.objects.get(title='Hardening Product')
    anon = Client()
    for url in (
        '/api/v1/catalog/products/',
        f'/api/v1/catalog/products/{product.slug}/',
        f'/api/v1/catalog/products/{product.slug}/reviews/',
        '/api/v1/stores/public/',
    ):
        assert anon.get(url).status_code == 200, url
    # Tracking an unknown number is a 404 by design, not a 401.
    assert anon.get(f'{TRACK}JVTRK-NOT-A-REAL-NUMBER/').status_code == 404


# --- §20.1 CSRF & CORS (§10.4) -----------------------------------------------


def test_an_unsafe_method_without_a_csrf_token_is_refused():
    """With session auth, CSRF is the only thing between a cookie and a state
    change — so it is proven, not assumed."""
    buyer = _make_user('hardeningcsrf@example.com')
    client = _client_for(buyer, enforce_csrf_checks=True)
    refused = client.post(
        '/api/v1/cart/items',
        {'variant_id': 1, 'quantity': 1},
        content_type='application/json',
    )
    assert refused.status_code == 403


def test_cors_answers_only_allowlisted_origins_and_allows_credentials():
    """The allowlist decides — and the SPA's `credentials: 'include'` needs
    Allow-Credentials to come along, or every cross-origin session call fails
    while the allowlist still looks correct."""
    allowed = 'http://localhost:5173'
    granted = Client().get('/api/v1/catalog/products/', HTTP_ORIGIN=allowed)
    assert granted['Access-Control-Allow-Origin'] == allowed
    assert granted['Access-Control-Allow-Credentials'] == 'true'

    refused = Client().get(
        '/api/v1/catalog/products/', HTTP_ORIGIN='http://evil.example'
    )
    assert 'Access-Control-Allow-Origin' not in refused


# --- §20.1 rate limiting (§10.2) ---------------------------------------------


def test_rate_limiting_refuses_a_flood_on_the_auth_surface(monkeypatch):
    """DRF binds throttle config at import time, so the test patches what the
    views actually read — the class attribute and the rate table."""
    from rest_framework.throttling import (
        AnonRateThrottle,
        ScopedRateThrottle,
        SimpleRateThrottle,
    )
    from rest_framework.views import APIView

    monkeypatch.setattr(
        APIView, 'throttle_classes', [ScopedRateThrottle, AnonRateThrottle]
    )
    monkeypatch.setattr(
        SimpleRateThrottle,
        'THROTTLE_RATES',
        {'anon': '100/min', 'user': '100/min', 'auth': '3/min'},
    )
    cache.clear()

    client = Client()
    codes = [
        client.post(
            LOGIN,
            {'email': 'nobody@example.com', 'password': 'wrong-password'},
            content_type='application/json',
        ).status_code
        for _ in range(5)
    ]
    assert codes[0] != 429  # the first attempts are judged, not refused
    assert 429 in codes  # then the bucket runs dry
    cache.clear()


def test_the_surfaces_worth_abusing_carry_tight_scopes():
    from rest_framework.throttling import SimpleRateThrottle

    from apps.accounts import views as account_views
    from apps.messaging import views as messaging_views
    from apps.orders import views as order_views

    assert account_views.LoginView.throttle_scope == 'auth'
    assert account_views.RegisterView.throttle_scope == 'register'
    assert order_views.CheckoutOrderView.throttle_scope == 'checkout'
    assert messaging_views.SendMessageView.throttle_scope == 'message'

    # Every scope has a rate, and the blanket allowance stays generous —
    # throttling is not a speed bump on ordinary reading (§10.2).
    rates = SimpleRateThrottle.THROTTLE_RATES
    for scope in ('anon', 'user', 'auth', 'register', 'checkout', 'message'):
        assert scope in rates, scope
    assert int(rates['user'].split('/')[0]) >= 60
    assert int(rates['auth'].split('/')[0]) <= 20


def test_every_configured_rate_is_a_real_drf_rate():
    """`count/period` or it is not a rate at all.

    Found the hard way: a suite that lifts throttling passed 335 tests while
    the live server 500'd on *every* request, because a bare `'120'` fails
    `parse_rate` only when a throttle is actually instantiated. This test
    parses each configured rate with the same rule DRF uses, so CI catches the
    shape even though the suite never trips a bucket.
    """
    from rest_framework.throttling import SimpleRateThrottle

    for scope, rate in SimpleRateThrottle.THROTTLE_RATES.items():
        number, period = rate.split('/')  # a bare number raises here
        assert int(number) > 0, scope
        assert period[0] in 'smhd', scope  # second/m/hour/day

