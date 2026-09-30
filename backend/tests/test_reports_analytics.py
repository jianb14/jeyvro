"""Phase 19.4 gate tests — the report exports (ROADMAP §19.4).

Contracts proven here:

1. **One definition**: every export is the CSV rendering of the *same
   serializer output* the JSON endpoints serve, so a report can never show a
   number the API does not — and money leaves as the server's exact decimal
   string, never a float.
2. **The gate is the route, not a parameter**: a money report (summary,
   stores) is `finance`/`administrator`; the oversight reports (products,
   operations, performance) are the read-only groups too; moderator, a
   customer and an anonymous visitor are refused everywhere (§4).
3. **Ranges are validated and named** the same way the reads are (§8): a
   reversed, malformed or over-long range is a 400, never a silently clamped
   file, and the filename carries the range that was exported.
4. **Honest files**: an empty range still exports its header, quoting survives
   commas and quotes in a store name, and a range too large for a spreadsheet
   is refused with a 400 rather than truncated into a file that looks complete.
"""
import csv
import re
from datetime import timedelta
from decimal import Decimal
from io import StringIO

import pytest
from django.contrib.auth.models import Group
from django.test import Client
from django.utils import timezone

from apps.accounts.models import Address, User
from apps.cart.models import Cart
from apps.catalog import services as catalog_services
from apps.catalog.models import Product, Variant
from apps.orders import services as order_services
from apps.reporting import exports
from apps.reporting import services as reporting_services
from apps.stores.models import Store

pytestmark = pytest.mark.django_db

PASSWORD = 'Str0ng!Passw0rd'
EXPORT = '/api/v1/admin/analytics/export/'
MONEY_REPORTS = ('summary', 'stores')
OPS_REPORTS = ('products', 'operations', 'performance')
ALL_REPORTS = MONEY_REPORTS + OPS_REPORTS


def _make_user(email, *, group=None):
    user = User.objects.create_user(
        email=email,
        password=PASSWORD,
        first_name=email.split('@')[0].capitalize(),
        last_name='User',
        is_staff=bool(group),
    )
    if group:
        grp, _ = Group.objects.get_or_create(name=group)
        user.groups.add(grp)
    return user


def _client_for(user):
    client = Client()
    client.force_login(user)
    return client


def _store(name='Report Store', price='500.00'):
    """An active store with one published, stocked variant, and its seller."""
    slug = re.sub(r'\W+', '-', name.lower()).strip('-') or 'report-store'
    seller = _make_user(f'owner-{slug}@example.com')
    store = Store.objects.create(
        user=seller,
        name=name,
        status=Store.Status.ACTIVE,
        shipping_flat_fee=Decimal('50.00'),
    )
    seller.is_seller = True
    seller.save(update_fields=['is_seller'])
    product = Product.objects.create(
        store=store,
        title=f'Report Product {store.pk}',
        base_price=Decimal(price),
        status=Product.Status.PUBLISHED,
    )
    variant = Variant.objects.create(
        product=product, name='Default', price=Decimal(price), is_default=True
    )
    catalog_services.ensure_inventory(variant, initial_on_hand=20)
    return seller, store, product, variant


def _delivered_order(buyer_email='reportbuyer@example.com', variant=None, name='Report Store'):
    """A real checkout driven all the way to a delivered parcel (§8, §10)."""
    buyer = _make_user(buyer_email)
    address = Address.objects.create(
        user=buyer,
        full_name='Report Buyer',
        phone='09171234567',
        line1='9 Kalayaan Street',
        city='Quezon City',
        province='Metro Manila',
        postal_code='1100',
    )
    if variant is None:
        _seller, _store_obj, _product, variant = _store(name)
    cart = Cart.objects.create(user=buyer)
    cart.items.create(variant=variant, quantity=1)
    order = order_services.create_order(buyer, address.id, payment_method='cod')
    for seller_order in order.seller_orders.all():
        seller = seller_order.store.user
        order_services.mark_seller_order_processing(seller_order, actor=seller)
        order_services.mark_seller_order_packed(seller_order, actor=seller)
        shipment = order_services.create_shipment(
            seller_order, carrier_code='manual', package_notes='Report fixture',
            package_weight_grams=250, actor=seller,
        )
        order_services.update_shipment_status(
            shipment, 'delivered', actor=seller
        )
    order.refresh_from_db()
    return order


def _rows(response):
    """The CSV body parsed back — the way a spreadsheet would read it."""
    return list(csv.reader(StringIO(response.content.decode('utf-8'))))


# --- §19.4 the exports ---------------------------------------------------------


def test_every_report_exports_the_rows_the_api_serves():
    _delivered_order()
    day = timezone.localdate()
    reporting_services.rebuild(start=day, end=day)
    finance = _client_for(_make_user('reportsfinance@example.com', group='finance'))
    params = {'from': str(day), 'to': str(day)}

    summary = finance.get(f'{EXPORT}summary/', params)
    assert summary.status_code == 200, summary.content
    assert summary['Content-Type'].startswith('text/csv')
    assert 'filename="jeyvro-summary-' in summary['Content-Disposition']
    header, row = _rows(summary)[0], _rows(summary)[1]
    assert header[0] == 'Day'
    assert row[0] == str(day)
    # The money cell is the server's exact decimal string, never a float.
    assert row[header.index('GMV')] == '550.00'  # 500.00 goods + 50.00 shipping
    assert row[header.index('Revenue')] == '550.00'

    operations = _rows(finance.get(f'{EXPORT}operations/', params))
    assert operations[1][operations[0].index('Parcels delivered')] == '1'
    assert operations[1][operations[0].index('Orders completed')] == '1'

    stores = _rows(finance.get(f'{EXPORT}stores/', params))
    assert stores[1][stores[0].index('Store')] == 'Report Store'
    assert stores[1][stores[0].index('Gross sales')] == '550.00'

    products = _rows(finance.get(f'{EXPORT}products/', params))
    assert products[1][products[0].index('Product')].startswith('Report Product')
    assert products[1][products[0].index('Units sold')] == '1'

    performance = _rows(finance.get(f'{EXPORT}performance/', params))
    assert performance[1][performance[0].index('Parcels delivered')] == '1'


def test_exports_are_gated_per_report():
    """The gate is the route: a money report never reaches an oversight group."""
    support = _client_for(_make_user('reportssupport@example.com', group='support'))
    finance = _client_for(_make_user('reportsfinance2@example.com', group='finance'))
    for report in MONEY_REPORTS:
        assert support.get(f'{EXPORT}{report}/').status_code == 403, report
        assert finance.get(f'{EXPORT}{report}/').status_code == 200, report
    for report in OPS_REPORTS:
        assert support.get(f'{EXPORT}{report}/').status_code == 200, report
        assert finance.get(f'{EXPORT}{report}/').status_code == 200, report

    moderator = _client_for(_make_user('reportsmoderator@example.com', group='moderator'))
    for report in ALL_REPORTS:
        assert moderator.get(f'{EXPORT}{report}/').status_code == 403, report

    customer = _make_user('reportscustomer@example.com')
    assert _client_for(customer).get(f'{EXPORT}summary/').status_code == 403
    assert Client().get(f'{EXPORT}operations/').status_code == 403


def test_the_export_range_is_validated_and_named():
    finance = _client_for(_make_user('reportsrange@example.com', group='finance'))
    day = timezone.localdate()

    inverted = finance.get(
        f'{EXPORT}summary/', {'from': str(day), 'to': str(day - timedelta(days=3))}
    )
    assert inverted.status_code == 400
    assert inverted.json()['error'] == 'invalid_range'
    assert finance.get(f'{EXPORT}summary/', {'from': 'yesterday'}).status_code == 400
    assert finance.get(
        f'{EXPORT}summary/', {'from': str(day - timedelta(days=400))}
    ).status_code == 400

    first = day - timedelta(days=6)
    ok = finance.get(
        f'{EXPORT}operations/', {'from': str(first), 'to': str(day)}
    )
    assert ok.status_code == 200, ok.content
    assert f'jeyvro-operations-{first}-{day}.csv' in ok['Content-Disposition']


def test_quoting_survives_a_name_with_commas_and_quotes():
    """A store named `Kalinga, "Crafts" Ltd` is one cell, not four columns."""
    tricky = 'Kalinga, "Crafts" Ltd'
    _delivered_order(buyer_email='trickybuyer@example.com', name=tricky)
    day = timezone.localdate()
    reporting_services.rebuild(start=day, end=day)

    finance = _client_for(_make_user('reportsquoting@example.com', group='finance'))
    response = finance.get(f'{EXPORT}stores/')
    assert response.status_code == 200
    rows = _rows(response)
    store_cell = rows[0].index('Store')
    assert rows[1][store_cell] == tricky
    # One cell, not four columns — the row has exactly as many fields as the
    # header, and the raw body carries the RFC 4180 doubled quotes.
    assert len(rows[1]) == len(rows[0])
    assert f'"{tricky.replace(chr(34), chr(34) * 2)}"' in response.content.decode(
        'utf-8'
    )


def test_an_empty_range_still_exports_its_header():
    """Header-only is a truthful answer; an empty body looks like a broken file."""
    finance = _client_for(_make_user('reportsempty@example.com', group='finance'))
    response = finance.get(f'{EXPORT}summary/')
    assert response.status_code == 200
    rows = _rows(response)
    assert len(rows) == 1
    assert 'GMV' in rows[0]
    assert 'Commission' in rows[0]


def test_an_oversized_export_is_refused_rather_than_truncated(monkeypatch):
    _delivered_order()
    day = timezone.localdate()
    reporting_services.rebuild(start=day, end=day)

    finance = _client_for(_make_user('reportsbig@example.com', group='finance'))
    monkeypatch.setattr(exports, 'MAX_EXPORT_ROWS', 0)
    response = finance.get(f'{EXPORT}summary/')
    assert response.status_code == 400
    assert response.json()['error'] == 'export_too_large'
