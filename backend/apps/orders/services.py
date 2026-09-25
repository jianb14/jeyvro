"""Order services — checkout validation, order creation, cancellation (§6).

Everything money- or stock-critical happens here, inside one transaction:
the cart is re-validated against live server truth, the order is snapshotted
(immutably), stock is reserved through the row-locked catalog services (the
only place stock changes), and the cart is cleared. Views stay thin (§8).
"""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from django.utils.crypto import get_random_string

from apps.accounts.models import Address
from apps.audit import services as audit_services
from apps.cart import services as cart_services
from apps.cart.models import Cart
from apps.catalog import services as catalog_services
from apps.payments import services as payment_services
from apps.payments.models import PaymentMethod

from .models import Order, OrderItem, SellerOrder

# Unambiguous alphabet for order numbers (no O/0, I/1, lookalikes).
ORDER_NUMBER_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'


class CheckoutError(ValueError):
    """Customer-safe checkout rejection — code + message, never a stack."""

    def __init__(self, message, *, code='checkout_rejected'):
        super().__init__(message)
        self.code = code


def compute_shipping_fee(store, subtotal):
    """Per-store shipping truth (§6 v1.7): flat fee, free at/above threshold.

    Returns (fee, is_free). A null threshold means the flat fee always
    applies; reaching the threshold waives it without touching the subtotal.
    """
    fee = store.shipping_flat_fee or Decimal('0.00')
    threshold = store.free_shipping_threshold
    if threshold is not None and subtotal >= threshold:
        return Decimal('0.00'), True
    return fee, False


def _generate_order_number():
    """Unique public identifier: JV-YYYYMMDD-XXXXXXXX (CONVENTIONS §2.2)."""
    date = timezone.now().strftime('%Y%m%d')
    for _ in range(10):
        candidate = f'JV-{date}-{get_random_string(8, ORDER_NUMBER_ALPHABET)}'
        if not Order.objects.filter(number=candidate).exists():
            return candidate
    raise RuntimeError('Could not allocate a unique order number.')


def create_order(user, address_id, payment_method=PaymentMethod.COD):
    """Creates the parent order + one SellerOrder per store — one transaction.

    Re-validates every cart line against live product/variant/stock/price
    truth (the client sends only an address and a payment method — never
    prices or totals), snapshots everything, reserves stock with row locks,
    starts the payment, then clears the cart. Any failure raises
    CheckoutError and rolls the whole thing back, so an invalid line or an
    unpayable method can never produce a partial order.
    """
    address = Address.objects.filter(pk=address_id, user=user).first()
    if address is None:
        raise CheckoutError('Choose a valid shipping address.', code='invalid_address')

    with transaction.atomic():
        # Lock the cart row: two parallel submits (double-click) serialize
        # here — the second one finds an empty cart and is rejected.
        cart = Cart.objects.select_for_update().filter(user=user).first()
        items = (
            list(
                cart.items.select_related(
                    'variant',
                    'variant__inventory',
                    'variant__product',
                    'variant__product__store',
                )
            )
            if cart is not None
            else []
        )
        if not items:
            raise CheckoutError('Your cart is empty.', code='empty_cart')

        groups = {}
        for item in items:
            variant = item.variant
            product = variant.product
            purchasable, available, reason = cart_services.variant_purchase_state(variant)
            if not purchasable:
                raise CheckoutError(
                    f'{product.title}: {reason}', code='line_unavailable'
                )
            if item.quantity > available:
                raise CheckoutError(
                    f'{product.title}: only {available} left in stock.',
                    code='insufficient_stock',
                )
            groups.setdefault(product.store, []).append(item)

        subtotal = Decimal('0.00')
        shipping_total = Decimal('0.00')
        savings_total = Decimal('0.00')
        store_plans = []
        for store, store_items in groups.items():
            store_subtotal = Decimal('0.00')
            store_savings = Decimal('0.00')
            store_lines = []
            for item in store_items:
                variant = item.variant
                price = variant.price
                compare_at = variant.product.compare_at_price
                if compare_at is not None and compare_at <= price:
                    compare_at = None
                line_total = price * item.quantity
                store_subtotal += line_total
                if compare_at is not None:
                    store_savings += (compare_at - price) * item.quantity
                store_lines.append((item, price, compare_at, line_total))
            fee, _is_free = compute_shipping_fee(store, store_subtotal)
            subtotal += store_subtotal
            shipping_total += fee
            savings_total += store_savings
            store_plans.append((store, store_lines, store_subtotal, fee))

        tax_total = Decimal('0.00')  # §6: tax is not computed yet — slot reserved
        grand_total = subtotal + shipping_total + tax_total

        order = Order.objects.create(
            number=_generate_order_number(),
            user=user,
            status=Order.Status.PLACED,
            ship_to_name=address.full_name,
            ship_to_phone=address.phone,
            shipping_line1=address.line1,
            shipping_line2=address.line2,
            shipping_city=address.city,
            shipping_province=address.province,
            shipping_postal_code=address.postal_code,
            subtotal=subtotal,
            shipping_total=shipping_total,
            savings_total=savings_total,
            tax_total=tax_total,
            grand_total=grand_total,
        )

        for store, store_lines, store_subtotal, fee in store_plans:
            seller_order = SellerOrder.objects.create(
                order=order,
                store=store,
                store_name=store.name,
                status=SellerOrder.Status.PLACED,
                subtotal=store_subtotal,
                shipping_fee=fee,
                total=store_subtotal + fee,
            )
            for item, price, compare_at, line_total in store_lines:
                variant = item.variant
                OrderItem.objects.create(
                    seller_order=seller_order,
                    product=variant.product,
                    variant=variant,
                    product_title=variant.product.title,
                    product_slug=variant.product.slug,
                    variant_name=variant.name,
                    sku=variant.sku,
                    unit_price=price,
                    compare_at_price=compare_at,
                    quantity=item.quantity,
                    line_total=line_total,
                )
                # The race gate: row-locked reservation; another checkout
                # that took the last unit makes this raise and roll back.
                try:
                    catalog_services.reserve_stock(variant, item.quantity)
                except ValueError as exc:
                    raise CheckoutError(
                        f'{variant.product.title}: {exc}',
                        code='insufficient_stock',
                    ) from exc

        cart.items.all().delete()

        # Payments (§6 v1.8): every order is immediately awaiting payment —
        # COD collects on delivery, online payments start through the adapter
        # seam. A method that cannot be paid is refused before anything moves.
        try:
            payment = payment_services.start_payment(order, payment_method)
        except payment_services.PaymentError as exc:
            raise CheckoutError(str(exc), code=exc.code) from exc
        order.status = Order.Status.AWAITING_PAYMENT
        order.save(update_fields=['status', 'updated_at'])
        order.seller_orders.update(
            status=SellerOrder.Status.AWAITING_PAYMENT, updated_at=timezone.now()
        )

        audit_services.log_event(
            user,
            'order.placed',
            order,
            detail={
                'number': order.number,
                'grand_total': str(order.grand_total),
                'stores': len(store_plans),
                'payment_method': payment.method,
                'payment': payment.reference,
            },
        )
    return order


def cancel_order(user, number):
    """Customer cancellation before payment — releases the reservations (§6).

    Only `placed` / `awaiting_payment` orders can be cancelled here; after
    payment, refunds are the path (Phase 17). Every line's reservation is
    released through the row-locked catalog service, then both the parent
    and the per-store orders are marked cancelled — one transaction.
    """
    with transaction.atomic():
        order = (
            Order.objects.select_for_update()
            .filter(number=number, user=user)
            .first()
        )
        if order is None:
            raise Order.DoesNotExist(f'Order {number} not found.')
        if order.status not in (Order.Status.PLACED, Order.Status.AWAITING_PAYMENT):
            raise CheckoutError(
                'This order can no longer be cancelled.', code='not_cancellable'
            )
        items = OrderItem.objects.filter(
            seller_order__order=order
        ).select_related('variant')
        for item in items:
            catalog_services.release_stock(item.variant, item.quantity)
        order.status = Order.Status.CANCELLED
        order.save(update_fields=['status', 'updated_at'])
        order.seller_orders.update(
            status=SellerOrder.Status.CANCELLED, updated_at=timezone.now()
        )
        # A still-pending payment is voided with its order (§6 v1.8).
        payment_services.cancel_pending_payment(order, actor=user)
        audit_services.log_event(
            user, 'order.cancelled', order, detail={'number': order.number}
        )
    return order

