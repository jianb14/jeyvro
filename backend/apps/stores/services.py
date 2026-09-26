"""Store services — every state transition lives here, never in views.

Rules honoured (PROJECT_CONTEXT §6 v1.2, marketplace-sellers):
- apply → application + store both pending; is_seller flips on approval only
- review/approve/reject and suspend/activate are staff-only, audit-logged
- sellers never self-approve; no transition happens by blind field writes
- seller dashboard aggregates are ALWAYS scoped to the seller's own store
  (§12.1; marketplace-sellers rule 4/5 — the frontend renders API truth)
"""
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, F, Sum
from django.db import transaction
from django.utils import timezone

from apps.audit.services import log_event
from apps.common.privacy import mask_name

from .models import SellerApplication, Store


def apply_as_seller(user, *, store_name, store_description='', contact_phone=''):
    """A customer applies to become a seller. Creates the pending
    application + pending store atomically (marketplace-sellers rule)."""
    with transaction.atomic():
        application = SellerApplication.objects.create(
            user=user,
            store=Store.objects.create(
                user=user,
                name=store_name,
                description=store_description,
                contact_email=user.email,
                contact_phone=contact_phone,
                status=Store.Status.PENDING,
            ),
            store_name=store_name,
            store_description=store_description,
            contact_phone=contact_phone,
            status=SellerApplication.Status.PENDING,
        )
    return application


def review_application(staff_user, application, *, decision, reason=''):
    """Staff approves or rejects a pending application (audit-logged).

    approve → store goes active and the user's is_seller flag flips true;
    reject → a reason is mandatory and the store stays pending (reapply
    by editing the store profile and resubmitting).
    """
    if application.status != SellerApplication.Status.PENDING:
        raise ValueError('This application was already reviewed.')
    if application.user_id == staff_user.pk:
        raise ValueError('Staff cannot review their own application.')

    with transaction.atomic():
        application.status = decision
        application.reviewed_by = staff_user
        application.reviewed_at = timezone.now()
        if decision == SellerApplication.Status.REJECTED:
            if not reason.strip():
                raise ValueError('A rejection reason is required.')
            application.rejection_reason = reason
        application.save(update_fields=[
            'status', 'reviewed_by', 'reviewed_at',
            'rejection_reason', 'updated_at',
        ])

        store = application.store
        if decision == SellerApplication.Status.APPROVED:
            store.status = Store.Status.ACTIVE
            seller = application.user
            seller.is_seller = True
            seller.save(update_fields=['is_seller', 'updated_at'])
        else:
            store.status = Store.Status.PENDING
        store.save(update_fields=['status', 'updated_at'])

        log_event(
            staff_user,
            f'seller_application_{decision}',
            application,
            detail={
                'store_id': store.pk,
                'store_slug': store.slug,
                'applicant_id': application.user_id,
                'reason': reason,
            },
        )
    return application


def suspend_store(staff_user, store, *, reason=''):
    """Staff suspends an active store (audit-logged). Data is kept; the
    storefront just becomes invisible to the public (§6 v1.2)."""
    if store.status != Store.Status.ACTIVE:
        raise ValueError('Only active stores can be suspended.')

    with transaction.atomic():
        store.status = Store.Status.SUSPENDED
        store.suspended_at = timezone.now()
        store.save(update_fields=['status', 'suspended_at', 'updated_at'])
        log_event(staff_user, 'store_suspended', store, detail={'reason': reason})
    return store


def activate_store(staff_user, store, *, reason=''):
    """Staff re-activates a suspended store (audit-logged)."""
    if store.status != Store.Status.SUSPENDED:
        raise ValueError('Only suspended stores can be re-activated.')

    with transaction.atomic():
        store.status = Store.Status.ACTIVE
        store.suspended_at = None
        store.save(update_fields=['status', 'suspended_at', 'updated_at'])
        log_event(staff_user, 'store_activated', store, detail={'reason': reason})
    return store


def build_seller_dashboard(store):
    """Seller home aggregates — scoped to exactly one store (§12.1).

    Every number comes from the store's own rows (SellerOrder / OrderItem /
    Product / Inventory, all indexed by store) and the frontend renders it
    as API truth — it never estimates sales itself (marketplace-sellers
    rule 5). The scope is part of every query, so one seller's numbers can
    never leak into another's dashboard (rule 4/ownership).
    """
    from apps.catalog.models import Product, Variant
    from apps.orders.models import OrderItem, OrderStatus, SellerOrder

    sales_excluded = (
        OrderStatus.CANCELLED,
        OrderStatus.REFUNDED,
        OrderStatus.REFUND_PENDING,
    )
    live_orders = SellerOrder.objects.filter(store=store).exclude(
        status__in=sales_excluded
    )
    sales = live_orders.aggregate(orders=Count('id'), gross=Sum('total'))
    orders_count = sales['orders'] or 0
    gross = sales['gross'] or Decimal('0.00')
    units_sold = OrderItem.objects.filter(
        seller_order__store=store
    ).exclude(
        seller_order__status__in=sales_excluded
    ).aggregate(units=Sum('quantity'))['units'] or 0

    cutoff = timezone.now() - timedelta(days=30)
    recent = live_orders.filter(created_at__gte=cutoff).aggregate(
        orders=Count('id'), gross=Sum('total')
    )
    recent_units = OrderItem.objects.filter(
        seller_order__store=store,
        seller_order__created_at__gte=cutoff,
    ).exclude(
        seller_order__status__in=sales_excluded
    ).aggregate(units=Sum('quantity'))['units'] or 0

    order_status_counts = {
        row['status']: row['count']
        for row in SellerOrder.objects.filter(store=store)
        .values('status').annotate(count=Count('id'))
    }
    product_status_counts = {
        row['status']: row['count']
        for row in Product.objects.filter(store=store)
        .values('status').annotate(count=Count('id'))
    }

    low_stock_rows = (
        Variant.objects.filter(product__store=store)
        .exclude(product__status=Product.Status.ARCHIVED)
        .select_related('product', 'inventory')
        .filter(
            inventory__on_hand__lte=(
                F('inventory__low_stock_threshold') + F('inventory__reserved')
            )
        )
        .order_by('inventory__on_hand')
    )
    low_stock_items = [
        {
            'variant_id': variant.id,
            'product_id': variant.product_id,
            'product_title': variant.product.title,
            'sku': variant.sku,
            'available': variant.inventory.available,
            'low_stock_threshold': variant.inventory.low_stock_threshold,
        }
        for variant in low_stock_rows[:5]
        if getattr(variant, 'inventory', None) is not None
    ]

    recent_orders = [
        {
            'id': seller_order.id,
            'order_number': seller_order.order.number,
            'status': seller_order.status,
            'item_count': sum(
                item.quantity for item in seller_order.items.all()
            ),
            'total': float(seller_order.total),
            'customer': mask_name(seller_order.order.ship_to_name),
            'placed_at': seller_order.created_at.isoformat(),
        }
        for seller_order in (
            SellerOrder.objects.filter(store=store)
            .select_related('order')
            .prefetch_related('items')
            .order_by('-created_at')[:5]
        )
    ]

    open_statuses = (
        OrderStatus.PLACED, OrderStatus.AWAITING_PAYMENT, OrderStatus.PAID,
        OrderStatus.PROCESSING, OrderStatus.PACKED, OrderStatus.SHIPPED,
        OrderStatus.IN_TRANSIT, OrderStatus.OUT_FOR_DELIVERY,
    )
    open_orders = sum(
        count for status, count in order_status_counts.items()
        if status in open_statuses
    )

    return {
        'store': {
            'name': store.name,
            'slug': store.slug,
            'status': store.status,
        },
        'products': {
            'total': sum(product_status_counts.values()),
            'by_status': product_status_counts,
        },
        'sales': {
            'orders': orders_count,
            'units_sold': units_sold,
            'gross': float(gross),
            'average_order_value': (
                float(gross / orders_count) if orders_count else 0.0
            ),
            'last_30_days': {
                'orders': recent['orders'] or 0,
                'units_sold': recent_units,
                'gross': float(recent['gross'] or Decimal('0.00')),
            },
        },
        'orders': {
            'total': sum(order_status_counts.values()),
            'open': open_orders,
            'by_status': order_status_counts,
        },
        'inventory': {
            'low_stock_count': low_stock_rows.count(),
            'low_stock_items': low_stock_items,
        },
        'recent_orders': recent_orders,
        # Phase 14 owns reviews — the slot ships now so the dashboard shape
        # is stable when reviews land (12.1 "recent reviews").
        'recent_reviews': [],
    }