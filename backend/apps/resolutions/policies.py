"""Return & dispute policy — the single home for post-order resolution rules.

Phase 17 owns what happens after an order is delivered (ROADMAP §17): the
return window, the reason catalogue, and the refund math a case is priced by.
Keeping it in one pure module means the customer surface, the seller desk,
the staff console, and the tests all read the same rules — no UI-side or
duplicated arithmetic, and every number is reproducible from order snapshots
alone (§9, §17.2).

Money rules (C6): Decimal only, rounded half-up to centavos at the final step,
never floating point.
"""
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings

CENT = Decimal('0.01')
ZERO = Decimal('0.00')


def return_window_days():
    """Days after delivery a customer may still request a return (§17.1).

    Env-driven like the payment window (§6 v1.13): deploy-time policy, not a
    hardcoded constant — `RETURNS_WINDOW_DAYS`, default 7.
    """
    try:
        days = int(getattr(settings, 'RETURNS_WINDOW_DAYS', 7))
    except (TypeError, ValueError):
        return 7
    return max(0, days)


def return_window_deadline(delivered_at):
    """The last moment an eligible return may be filed — or None."""
    if delivered_at is None:
        return None
    return delivered_at + timedelta(days=return_window_days())


def quantize_money(value):
    """Decimal → centavos (half-up), never a float."""
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def allocate_discount(line_totals, discount_total):
    """Split an order-level discount across lines, proportionally (§17.2).

    The order snapshots promotions and vouchers as *order-level* amounts
    (`promotion_discount` + `discount_total`), but a partial return refunds
    only some lines — so the discount those lines already enjoyed has to be
    attributed to them, or a refund could pay back money the customer never
    spent. Lines are apportioned by their share of the subtotal and the
    rounding remainder lands on the largest line, so the parts always sum to
    exactly the order-level total.
    """
    allocation = [ZERO] * len(line_totals)
    discount_total = quantize_money(discount_total or ZERO)
    subtotal = sum(line_totals, ZERO)
    if discount_total <= ZERO or subtotal <= ZERO or not line_totals:
        return allocation
    capped = min(discount_total, subtotal)
    allocated = ZERO
    for idx, line_total in enumerate(line_totals):
        if idx == len(line_totals) - 1:
            share = max(ZERO, capped - allocated)
        else:
            share = quantize_money(capped * (line_total / subtotal))
            share = min(share, capped - allocated)
        allocation[idx] = share
        allocated += share
    return allocation


def refundable_amount(line_total, allocated_discount, shipping_fee=ZERO):
    """What one returned line pays back: paid value, never negative (§17.2).

    A refund can never exceed what was actually collected for the line, so
    the attributed discount is subtracted from the line total and the result
    is floored at zero (a line fully absorbed by a promotion refunds nothing).
    """
    value = quantize_money(line_total) - quantize_money(allocated_discount)
    if value < ZERO:
        value = ZERO
    return quantize_money(value + quantize_money(shipping_fee or ZERO))
