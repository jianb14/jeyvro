"""Phase 20.3 gate tests — sensitive operations are audited (§20.3).

Contracts proven here:

1. **An export is audited.** A CSV leaves the building with the money in it,
   so the row says *who* took *what*: actor, report, range and row count. Only
   a served file leaves a trace — a refused or invalid request exports nothing.
2. **An audit event may belong to no domain record** — an export has no row to
   hang itself on — and then it must name its subject explicitly; a row with
   neither is refused rather than stored blank.
3. **The coverage matrix is real.** One scenario drives several sensitive
   operations across domains and asserts each writes its documented action, so
   `docs/AUDIT_COVERAGE.md` cannot quietly rot into fiction.
"""
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from django.test import Client
from django.utils import timezone

from apps.accounts.models import Address, User
from apps.accounts import services as account_services
from apps.audit.models import AuditLog
from apps.audit.services import log_event
from apps.cart.models import Cart
from apps.catalog import services as catalog_services
from apps.catalog.models import Product, Variant
from apps.orders import services as order_services
from apps.payments import services as payment_services
from apps.platform import services as platform_services
from apps.reporting import services as reporting_services
from apps.stores import services as store_services
from apps.stores.models import Store

pytestmark = pytest.mark.django_db

PASSWORD = 'Str0ng!Passw0rd'
EXPORT = '/api/v1/admin/analytics/export/'


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


def _delivered_order():
    """A real checkout driven to a delivered parcel — the audit-rich path."""
    seller = _make_user('auditseller@example.com')
    store = Store.objects.create(
        user=seller,
        name='Audit Store',
        status=Store.Status.ACTIVE,
        shipping_flat_fee=Decimal('50.00'),
    )
    seller.is_seller = True
    seller.save(update_fields=['is_seller'])
    product = Product.objects.create(
        store=store,
        title='Audit Product',
        base_price=Decimal('500.00'),
        status=Product.Status.PUBLISHED,
    )
    variant = Variant.objects.create(
        product=product, name='Default', price=Decimal('500.00'), is_default=True
    )
    catalog_services.ensure_inventory(variant, initial_on_hand=20)

    buyer = _make_user('auditbuyer@example.com')
    address = Address.objects.create(
        user=buyer,
        full_name='Audit Buyer',
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
        seller_order, carrier_code='manual', actor=seller
    )
    order_services.update_shipment_status(shipment, 'delivered', actor=seller)
    return order, shipment, store, buyer


# --- §20.3 the export is audited ---------------------------------------------


def test_an_export_records_who_took_what():
    order, _shipment, _store, _buyer = _delivered_order()
    day = timezone.localdate()
    reporting_services.rebuild(start=day, end=day)

    finance = _make_user('auditfinance@example.com', group='finance')
    response = _client_for(finance).get(
        f'{EXPORT}summary/', {'from': str(day), 'to': str(day)}
    )
    assert response.status_code == 200, response.content

    event = AuditLog.objects.get(action='analytics.exported')
    assert event.actor == finance
    # No domain row to hang it on, so the subject is named explicitly.
    assert event.object_type == 'reporting.export'
    assert event.object_id == 'summary'
    assert event.detail == {
        'report': 'summary',
        'from': str(day),
        'to': str(day),
        'rows': 1,
    }
    # The audited row count is the one the file actually carries.
    assert len(response.content.decode().strip().splitlines()) - 1 == 1
    assert order is not None  # the scenario that produced the rows


def test_an_oversight_group_export_is_audited_too():
    _delivered_order()
    day = timezone.localdate()
    reporting_services.rebuild(start=day, end=day)

    support = _make_user('auditsupport@example.com', group='support')
    assert _client_for(support).get(f'{EXPORT}operations/').status_code == 200
    event = AuditLog.objects.get(action='analytics.exported')
    assert event.actor == support
    assert event.object_id == 'operations'


def test_a_refused_or_invalid_export_leaves_no_trace():
    """Nothing left the building, so nothing should look like it did."""
    _delivered_order()
    before = AuditLog.objects.count()

    moderator = _make_user('auditmoderator@example.com', group='moderator')
    assert _client_for(moderator).get(f'{EXPORT}summary/').status_code == 403

    day = timezone.localdate()
    finance = _client_for(_make_user('auditmoney@example.com', group='finance'))
    assert finance.get(
        f'{EXPORT}summary/', {'from': str(day), 'to': 'yesterday'}
    ).status_code == 400

    assert AuditLog.objects.count() == before
    assert not AuditLog.objects.filter(action='analytics.exported').exists()


# --- §20.3 an audit event with no domain object ------------------------------


def test_an_objectless_audit_event_must_name_its_subject():
    staff = _make_user('auditwriter@example.com', group='administrator')

    with pytest.raises(ValueError):
        log_event(staff, 'something.happened')  # neither object nor subject

    log_event(
        staff,
        'something.happened',
        detail={'note': 'no domain row for this one'},
        object_type='reporting.export',
        object_id='stores',
    )
    event = AuditLog.objects.get(action='something.happened')
    assert (event.object_type, event.object_id) == ('reporting.export', 'stores')

    # The ordinary path is unchanged: the object names itself.
    store = Store.objects.create(
        user=_make_user('auditstoreseller@example.com'),
        name='Audit Named Store',
        status=Store.Status.ACTIVE,
    )
    log_event(staff, 'store_touched', store)
    named = AuditLog.objects.get(action='store_touched')
    assert named.object_type == 'stores.store'
    assert named.object_id == str(store.pk)


# --- §20.3 the matrix is real, not fiction ------------------------------------


def test_the_documented_sensitive_operations_each_write_their_action():
    """One scenario across domains; the actions the matrix lists must appear."""
    order, shipment, store, buyer = _delivered_order()
    admin = _make_user('auditadmin@example.com', group='administrator')

    # Money: a refund settles and the ledger reversal is audited.
    payment_services.mark_paid(order.payment, source='test')
    payment_services.refund(
        order.payment,
        order.payment.amount,
        reason='Audit coverage fixture',
        actor=admin,
    )

    # Permissions: a staff role is granted (the canonical group row first —
    # the service refuses a name it cannot resolve, §4's matrix).
    Group.objects.get_or_create(name='support')
    account_services.assign_staff_group(admin, buyer, group_name='support')

    # Seller status: a store is suspended.
    store_services.suspend_store(admin, store, reason='Audit coverage fixture')

    # Platform settings: the commission rate is changed.
    platform_services.apply_update(
        admin,
        changes={'commission_rate_percent': Decimal('5.00')},
        scope='commission',
    )

    # Fulfillment: the parcel's status transitions (and delivery) are audited.
    # The service re-fetches the row under its lock, so the local instance is
    # stale until it is refreshed — the audit row is written either way.
    shipment.refresh_from_db()
    assert shipment.status == 'delivered'

    for action in (
        'order.placed',
        'shipment.created',
        'shipment.status_updated',
        'payment.captured',
        'refund.settled',
        'staff_group_assigned',
        'store_suspended',
        'platform_settings_update',
    ):
        assert AuditLog.objects.filter(action=action).exists(), action

    # And the trail can say who did it.
    assert AuditLog.objects.filter(
        action='refund.settled', actor=admin
    ).exists()
    assert AuditLog.objects.filter(
        action='store_suspended', actor=admin
    ).exists()


# --- §20.3 a seller's own money terms are audited -----------------------------


def test_a_seller_price_change_records_the_before_and_the_after():
    """A price is money the moment a buyer is asked for it (§20.3)."""
    seller = _make_user('auditpriceseller@example.com')
    seller.is_seller = True
    seller.save(update_fields=['is_seller'])
    store = Store.objects.create(
        user=seller, name='Audit Price Store', status=Store.Status.ACTIVE
    )
    product = Product.objects.create(
        store=store,
        title='Priced Thing',
        base_price=Decimal('500.00'),
        status=Product.Status.PUBLISHED,
    )
    variant = Variant.objects.create(
        product=product, name='Default', price=Decimal('500.00'), is_default=True
    )

    catalog_services.update_product(
        seller, product.pk,
        title='Priced Thing (now with a better title)',
        base_price=Decimal('450.00'),
    )
    events = AuditLog.objects.filter(action='product_price_changed')
    assert events.count() == 1, 'a retitle alone must not be audited as money'
    assert events.get().detail == {
        'field': 'base_price',
        'from': '500.00',
        'to': '450.00',
    }

    catalog_services.update_variant(
        seller, product.pk, variant.pk, price=Decimal('425.00')
    )
    variant_event = AuditLog.objects.get(action='variant_price_changed')
    assert variant_event.actor == seller
    assert variant_event.object_type == 'catalog.variant'
    assert variant_event.detail == {
        'product': product.pk,
        'from': '500.00',
        'to': '425.00',
    }

    # Saving the same price again is not a change and writes nothing.
    catalog_services.update_product(seller, product.pk, base_price=Decimal('450.00'))
    assert AuditLog.objects.filter(action='product_price_changed').count() == 1


def test_a_seller_changing_their_shipping_fee_is_audited():
    """The fee decides what a buyer is charged — it keeps its before/after."""
    seller = _make_user('auditfeeseller@example.com')
    seller.is_seller = True
    seller.save(update_fields=['is_seller'])
    Store.objects.create(
        user=seller,
        name='Audit Fee Store',
        status=Store.Status.ACTIVE,
        shipping_flat_fee=Decimal('50.00'),
    )
    client = _client_for(seller)

    response = client.patch(
        '/api/v1/stores/my/store',
        {'shipping_flat_fee': '75.00', 'description': 'Faster, same store.'},
        content_type='application/json',
    )
    assert response.status_code == 200, response.content
    assert response.json()['shipping_flat_fee'] == 75.0

    event = AuditLog.objects.get(action='store_profile_updated')
    assert event.actor == seller
    assert event.object_type == 'stores.store'
    assert event.detail['money'] == {
        'shipping_flat_fee': {'from': '50.00', 'to': '75.00'},
    }
    assert event.detail['changed'] == ['description', 'shipping_flat_fee']

    # A copy edit records the field name and no money at all.
    # (`ordering` is newest-first, so `.first()` is the row just written.)
    client.patch(
        '/api/v1/stores/my/store',
        {'description': 'Even faster, same fee.'},
        content_type='application/json',
    )
    assert AuditLog.objects.filter(action='store_profile_updated').count() == 2
    copy_edit = AuditLog.objects.filter(action='store_profile_updated').first()
    assert copy_edit.detail == {
        'changed': ['description'],
        'money': {},
    }

    # A seller still cannot touch somebody else's store.
    other = _make_user('auditotherstore@example.com')
    other.is_seller = True
    other.save(update_fields=['is_seller'])
    stranger_store = Store.objects.create(
        user=other, name='Someone Else', status=Store.Status.ACTIVE
    )
    with pytest.raises(PermissionError):
        store_services.update_own_profile(
            seller, stranger_store, changes={'shipping_flat_fee': '0.00'}
        )
