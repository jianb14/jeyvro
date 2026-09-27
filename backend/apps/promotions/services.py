"""Voucher services (Phase 16 — ROADMAP §16.1).

The single source of voucher truth: lookup, verdicts (window, spend floor,
counting limits, first-order, targeting), the discount math, and the atomic
redemption ledger write. `orders.services.create_order` calls
`evaluate_voucher` inside its own transaction and `redeem_voucher` right
after the Order row exists — the preview endpoint shares the exact same
service, so a checked-out order can never disagree with the preview (§6:
the client never calculates), and the counters are re-checked under a row
lock so parallel checkouts cannot double-spend a limited code (§16 Gate).
"""
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils import timezone

from apps.audit import services as audit_services
from apps.orders.models import Order

from .models import Voucher, VoucherDiscountType, VoucherScope, VoucherUsage

MONEY = Decimal('0.01')


class VoucherError(ValueError):
    """Customer-safe voucher rejection — code + message, never a stack."""

    def __init__(self, message, *, code='voucher_rejected'):
        super().__init__(message)
        self.code = code


def normalize_code(code):
    return (code or '').strip().upper()


def find_voucher(code):
    """Case-insensitive lookup — codes are stored uppercase at write time."""
    normalized = normalize_code(code)
    if not normalized:
        return None
    return Voucher.objects.filter(code=normalized).first()


def _money(amount):
    return Decimal(amount).quantize(MONEY, rounding=ROUND_HALF_UP)


def _window_verdict(voucher, now):
    """(message, code) when the window is closed, else (None, None)."""
    if not voucher.is_active:
        return 'This voucher is no longer available.', 'voucher_inactive'
    if voucher.starts_at and now < voucher.starts_at:
        return 'This voucher has not started yet.', 'voucher_not_started'
    if voucher.ends_at and now > voucher.ends_at:
        return 'This voucher has expired.', 'voucher_expired'
    return None, None


def _line_matches(rules, product):
    """No rows = everything in scope; rows match on product or its category."""
    if not rules:
        return True
    for rule in rules:
        if rule.product_id == product.id:
            return True
        if rule.category_id is not None and rule.category_id == product.category_id:
            return True
    return False


def compute_discount(voucher, eligible_subtotal):
    """Server-side discount math — the only implementation in the codebase.

    Percentage: value% of the eligible subtotal, optionally capped by
    `max_discount`. Fixed: the flat amount. Either way the discount is
    rounded to money, never above the eligible subtotal, never negative.
    """
    eligible = _money(eligible_subtotal)
    if eligible <= 0:
        return Decimal('0.00')
    if voucher.discount_type == VoucherDiscountType.PERCENTAGE:
        discount = eligible * voucher.value / Decimal('100')
    else:
        discount = voucher.value
    if voucher.max_discount is not None:
        discount = min(discount, voucher.max_discount)
    discount = _money(discount)
    if discount > eligible:
        discount = eligible
    if discount < 0:
        discount = Decimal('0.00')
    return discount


def _has_prior_order(user):
    return Order.objects.filter(user=user).exists()


def evaluate_voucher(code, user, store_lines):
    """Full verdict → redemption plan, shared by preview and checkout.

    `store_lines` is built from live server truth — [{'store': Store,
    'subtotal': Decimal, 'lines': [(product, line_total), …]}] — the cart
    for the preview endpoint, the re-validated checkout plan for orders.
    Returns {'voucher', 'eligible_subtotal', 'discount_total'} or raises
    VoucherError with a customer-safe code (the exact reason is surfaced).
    """
    voucher = find_voucher(code)
    if voucher is None:
        raise VoucherError('That voucher code was not found.', code='voucher_not_found')

    message, error_code = _window_verdict(voucher, timezone.now())
    if message:
        raise VoucherError(message, code=error_code)

    if voucher.first_order_only and _has_prior_order(user):
        raise VoucherError(
            'This voucher is only valid on a first order.',
            code='voucher_first_order_only',
        )

    if voucher.per_user_limit is not None:
        used = VoucherUsage.objects.filter(voucher=voucher, user=user).count()
        if used >= voucher.per_user_limit:
            raise VoucherError(
                'You have already used this voucher.', code='voucher_user_limit'
            )

    if voucher.usage_limit is not None:
        redeemed = VoucherUsage.objects.filter(voucher=voucher).count()
        if redeemed >= voucher.usage_limit:
            raise VoucherError(
                'This voucher has reached its usage limit.',
                code='voucher_usage_limit',
            )

    scoped = store_lines
    if voucher.scope == VoucherScope.SELLER:
        scoped = [
            entry for entry in store_lines if entry['store'].pk == voucher.store_id
        ]
        if not scoped:
            raise VoucherError(
                f'This voucher only applies to {voucher.store.name} items.',
                code='voucher_store_mismatch',
            )

    rules = list(voucher.eligibility_rules.all())
    eligible_subtotal = Decimal('0.00')
    for entry in scoped:
        for product, line_total in entry['lines']:
            if _line_matches(rules, product):
                eligible_subtotal += line_total
    eligible_subtotal = _money(eligible_subtotal)

    if eligible_subtotal <= 0:
        raise VoucherError(
            'None of the items in your cart qualify for this voucher.',
            code='voucher_no_eligible_items',
        )
    if eligible_subtotal < voucher.min_spend:
        raise VoucherError(
            f'Spend at least PHP {voucher.min_spend:.2f} to use this voucher.',
            code='voucher_min_spend',
        )

    discount_total = compute_discount(voucher, eligible_subtotal)
    if discount_total <= 0:
        raise VoucherError(
            'This voucher yields no discount on this cart.',
            code='voucher_no_discount',
        )

    return {
        'voucher': voucher,
        'eligible_subtotal': eligible_subtotal,
        'discount_total': discount_total,
    }


@transaction.atomic
def redeem_voucher(plan, user, order):
    """Writes the redemption ledger row under a row lock (§16 Gate).

    Runs inside `create_order`'s transaction, right after the Order row
    exists. The voucher row is locked and every counter re-checked, so two
    parallel checkouts with the same code serialize here: the loser sees the
    fresh counts and is rejected, which rolls its order back — usage limits
    and totals can never diverge. `VoucherUsage` is append-only; the audit
    row records code, scope, and the exact money involved.
    """
    voucher = Voucher.objects.select_for_update().get(pk=plan['voucher'].pk)

    if voucher.usage_limit is not None:
        if VoucherUsage.objects.filter(voucher=voucher).count() >= voucher.usage_limit:
            raise VoucherError(
                'This voucher has reached its usage limit.',
                code='voucher_usage_limit',
            )
    if voucher.per_user_limit is not None:
        used = VoucherUsage.objects.filter(voucher=voucher, user=user).count()
        if used >= voucher.per_user_limit:
            raise VoucherError(
                'You have already used this voucher.', code='voucher_user_limit'
            )

    usage = VoucherUsage.objects.create(
        voucher=voucher,
        user=user,
        order=order,
        store=voucher.store,
        discount_amount=plan['discount_total'],
    )
    audit_services.log_event(
        user,
        'voucher.redeemed',
        order,
        {
            'code': voucher.code,
            'scope': voucher.scope,
            'discount_total': str(plan['discount_total']),
            'eligible_subtotal': str(plan['eligible_subtotal']),
        },
    )
    return usage


def build_store_lines(cart_items):
    """Groups cart lines by store for the preview endpoint (§16.1).

    Checkout builds the same structure from its re-validated line plan, so
    the preview can never judge a voucher against different truth.
    """
    grouped = {}
    for item in cart_items:
        product = item.variant.product
        line_total = _money(Decimal(item.variant.price) * item.quantity)
        entry = grouped.setdefault(
            product.store_id,
            {'store': product.store, 'subtotal': Decimal('0.00'), 'lines': []},
        )
        entry['subtotal'] += line_total
        entry['lines'].append((product, line_total))
    return list(grouped.values())
