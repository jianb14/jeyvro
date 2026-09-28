"""Voucher & promotion services (Phase 16 â€” ROADMAP Â§16.1 and Â§16.2).

The single source of voucher truth: lookup, verdicts (window, spend floor,
counting limits, first-order, targeting), the discount math, and the atomic
redemption ledger write. `orders.services.create_order` calls
`evaluate_voucher` inside its own transaction and `redeem_voucher` right
after the Order row exists â€” the preview endpoint shares the exact same
service, so a checked-out order can never disagree with the preview (Â§6:
the client never calculates), and the counters are re-checked under a row
lock so parallel checkouts cannot double-spend a limited code (Â§16 Gate).

Section 16.2 adds the automatic promotion engine: `evaluate_store_lines`
applies every live campaign rule (product discount, flash sale, bundle,
buy-X-get-Y) to one store's lines, and `find_shipping_waiver` decides the
free-shipping verdict. The SAME functions run at cart read, checkout
preview, voucher evaluation, and order creation â€” the four server-truth
choke points â€” so no two surfaces can ever disagree about what a promotion
is worth. Promotions are windowed price rules with no counters (nothing to
race), and `record_promotion_usages` writes the append-only audit ledger.
"""
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.audit import services as audit_services
from apps.orders.models import Order

from .models import (
    Promotion,
    PromotionKind,
    PromotionUsage,
    Voucher,
    VoucherDiscountType,
    VoucherScope,
    VoucherUsage,
)

MONEY = Decimal('0.01')


class VoucherError(ValueError):
    """Customer-safe voucher rejection â€” code + message, never a stack."""

    def __init__(self, message, *, code='voucher_rejected'):
        super().__init__(message)
        self.code = code


def normalize_code(code):
    return (code or '').strip().upper()


def find_voucher(code):
    """Case-insensitive lookup â€” codes are stored uppercase at write time."""
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
    """Server-side discount math â€” the only implementation in the codebase.

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
    """Full verdict â†’ redemption plan, shared by preview and checkout.

    `store_lines` is built from live server truth â€” [{'store': Store,
    'subtotal': Decimal, 'lines': [(product, line_total), â€¦]}] â€” the cart
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
    """Writes the redemption ledger row under a row lock (Â§16 Gate).

    Runs inside `create_order`'s transaction, right after the Order row
    exists. The voucher row is locked and every counter re-checked, so two
    parallel checkouts with the same code serialize here: the loser sees the
    fresh counts and is rejected, which rolls its order back â€” usage limits
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


# --- Automatic promotion engine (Â§16.2) -------------------------------------


def _promotion_window_filter(now):
    """Live-window Q for a campaign: open start, not yet ended (either null)."""
    return (
        (Q(campaign__starts_at__isnull=True) | Q(campaign__starts_at__lte=now))
        & (Q(campaign__ends_at__isnull=True) | Q(campaign__ends_at__gte=now))
    )


def active_promotions(store, *, now=None):
    """Live rules that can hit one store's lines â€” platform + that store's.

    Campaign `is_active` and the window gate the whole group; `Promotion.
    is_active` pauses a single rule. Deterministic id order keeps stacked
    discounts reproducible across every choke point.
    """
    now = now or timezone.now()
    return (
        Promotion.objects.filter(is_active=True, campaign__is_active=True)
        .filter(_promotion_window_filter(now))
        .filter(Q(campaign__store__isnull=True) | Q(campaign__store=store))
        .select_related('campaign')
        .prefetch_related('target_rules')
        .order_by('id')
    )


def load_active_promotions(*, now=None):
    """Every live rule for product labels â€” store scope is checked per product."""
    now = now or timezone.now()
    return list(
        Promotion.objects.filter(is_active=True, campaign__is_active=True)
        .filter(_promotion_window_filter(now))
        .select_related('campaign')
        .prefetch_related('target_rules')
        .order_by('id')
    )


def find_shipping_waiver(store, subtotal, *, now=None):
    """The free-shipping rule waiving this store's flat fee, else None.

    Runs after `orders.services.compute_shipping_fee` â€” the threshold and
    the promotion are independent offers and either one makes shipping free.
    """
    subtotal = _money(subtotal)
    for promo in active_promotions(store, now=now):
        if promo.kind != PromotionKind.FREE_SHIPPING:
            continue
        if subtotal >= promo.min_spend:
            return promo
    return None


def line_entry(idx, product, quantity, unit_price, line_total):
    """One engine input row â€” callers pass exactly what they will snapshot."""
    return {
        'item_id': idx,
        'product': product,
        'quantity': quantity,
        'unit_price': unit_price,
        'line_total': _money(line_total),
    }


def _eligible_entries(promo, entries, remaining):
    """Lines this rule can discount â€” targeting rows, else the whole scope."""
    rules = promo.target_rules.all()
    return [
        entry
        for entry in entries
        if _line_matches(rules, entry['product'])
        and remaining[entry['item_id']] > 0
    ]


def _book(entry, amount, remaining, line_discounts, labels, label):
    """Subtracts `amount` from one line and books it + the badge everywhere."""
    item_id = entry['item_id']
    remaining[item_id] -= amount
    line_discounts[item_id] = line_discounts.get(item_id, Decimal('0.00')) + amount
    labels.setdefault(item_id, label)  # first rule that saved the line wins
    return amount


def _apply_percent(promo, entries, remaining, line_discounts, labels):
    """Percentage off each remaining line â€” exact money per line (Â§16.2)."""
    amount = Decimal('0.00')
    for entry in entries:
        discount = _money(
            remaining[entry['item_id']] * promo.value / Decimal('100')
        )
        discount = min(discount, remaining[entry['item_id']])
        if discount > 0:
            amount += _book(
                entry, discount, remaining, line_discounts, labels, promo.label
            )
    return amount


def _apply_fixed(promo, entries, remaining, line_discounts, labels):
    """One PHP pot split proportionally across the eligible lines.

    Shares round to money; any drift cents land on the largest line, clamped
    to what that line still costs â€” the pot can only be under-distributed by
    a cent, never over (never over-discount)."""
    pot = min(promo.value, sum(remaining[e['item_id']] for e in entries))
    if pot <= 0:
        return Decimal('0.00')
    total = sum(remaining[e['item_id']] for e in entries)
    shares = [_money(pot * remaining[e['item_id']] / total) for e in entries]
    drift = pot - sum(shares)
    if drift != 0:
        biggest = max(
            range(len(entries)), key=lambda i: remaining[entries[i]['item_id']]
        )
        shares[biggest] = min(
            max(shares[biggest] + drift, Decimal('0.00')),
            remaining[entries[biggest]['item_id']],
        )
    amount = Decimal('0.00')
    for entry, share in zip(entries, shares):
        if share > 0:
            amount += _book(
                entry, share, remaining, line_discounts, labels, promo.label
            )
    return amount


def _apply_bxgy(promo, entries, remaining, line_discounts, labels):
    """Buy N of A, get up to M units of B at `value`% off (Â§16.2).

    The buy side counts units across every line of the buy product in this
    store; the get side discounts whole units of the get product, capped at
    `get_qty`, against what earlier rules left on the line."""
    buy_units = sum(
        e['quantity'] for e in entries if e['product'].id == promo.buy_product_id
    )
    if buy_units < promo.buy_qty:
        return Decimal('0.00')
    units_left = promo.get_qty
    amount = Decimal('0.00')
    for entry in entries:
        if units_left <= 0:
            break
        if entry['product'].id != promo.get_product_id:
            continue
        take = min(units_left, entry['quantity'])
        remaining_line = remaining[entry['item_id']]
        if remaining_line <= 0:
            continue
        portion = _money(remaining_line * take / entry['quantity'])
        discount = min(
            _money(portion * promo.value / Decimal('100')), remaining_line
        )
        if discount > 0:
            amount += _book(
                entry, discount, remaining, line_discounts, labels, promo.label
            )
            units_left -= take
    return amount


def evaluate_store_lines(store, lines, *, now=None):
    """Applies every live promotion to one store's lines (Â§16.2).

    `lines` is a list of `line_entry` rows. Rules stack in creation order
    against what earlier rules left on each line, so the sum of discounts can
    never exceed the subtotal. Returns `line_discounts` per item id, the
    per-rule `applied` totals for the ledger, `labels` per item id, and the
    store's `discount_total` â€” identical output at every choke point.
    """
    remaining = {entry['item_id']: entry['line_total'] for entry in lines}
    line_discounts = {}
    labels = {}
    applied = []
    discount_total = Decimal('0.00')

    for promo in active_promotions(store, now=now):
        if promo.kind == PromotionKind.FREE_SHIPPING:
            continue  # shipping is judged by find_shipping_waiver, not lines

        if promo.kind == PromotionKind.BUY_X_GET_Y:
            rule_amount = _apply_bxgy(promo, lines, remaining, line_discounts, labels)
        else:
            eligible = _eligible_entries(promo, lines, remaining)
            eligible_sum = sum(remaining[e['item_id']] for e in eligible)
            if eligible_sum <= 0 or eligible_sum < promo.min_spend:
                continue
            if promo.kind == PromotionKind.BUNDLE:
                units = sum(e['quantity'] for e in eligible)
                if units < promo.min_qty:
                    continue
            if promo.discount_type == VoucherDiscountType.PERCENTAGE:
                rule_amount = _apply_percent(
                    promo, eligible, remaining, line_discounts, labels
                )
            else:
                rule_amount = _apply_fixed(
                    promo, eligible, remaining, line_discounts, labels
                )

        if rule_amount > 0:
            applied.append({'promotion': promo, 'amount': _money(rule_amount)})
            discount_total += rule_amount

    return {
        'line_discounts': line_discounts,
        'applied': applied,
        'labels': labels,
        'discount_total': _money(discount_total),
    }


def record_promotion_usages(order, user, store_plans):
    """Append-only ledger write for one order (Â§16.2) â€” beside the voucher one.

    One row per rule per store: the summed line discounts, plus the waived
    flat fee for a free-shipping rule (only when the store actually charged
    a fee â€” a threshold already made it free, so the promo gave nothing).
    One `promotion.applied` audit event records the whole picture.
    """
    rows = []
    for plan in store_plans:
        store = plan['store']
        for entry in plan['promo']['applied']:
            rows.append((entry['promotion'], store, entry['amount']))
        if plan['waiver'] is not None and plan['waived_fee'] > 0:
            rows.append((plan['waiver'], store, plan['waived_fee']))
    if not rows:
        return []

    usages = [
        PromotionUsage.objects.create(
            promotion=promotion, user=user, order=order, store=store,
            discount_amount=amount,
        )
        for promotion, store, amount in rows
    ]
    audit_services.log_event(
        user,
        'promotion.applied',
        order,
        {
            'promotion_discount': str(order.promotion_discount),
            'promotions': [
                {
                    'id': promotion.id,
                    'kind': promotion.kind,
                    'label': promotion.label,
                    'store_id': store.id,
                    'amount': str(amount),
                }
                for promotion, store, amount in rows
            ],
        },
    )
    return usages


def build_store_lines(cart_items):
    """Groups cart lines by store for the preview endpoint (Â§16.1) â€” and runs
    them through the Â§16.2 promotion engine first.

    Checkout builds the same structure from its re-validated line plan, so
    the preview can never judge a voucher against different truth: a voucher
    is worth its discount against what the customer actually pays for the
    lines after automatic promotions have taken their cut.
    """
    grouped = {}
    for item in cart_items:
        product = item.variant.product
        unit_price = _money(Decimal(item.variant.price))
        line_total = _money(unit_price * item.quantity)
        entry = grouped.setdefault(product.store_id, {'store': product.store, 'raw': []})
        entry['raw'].append((product, item.quantity, unit_price, line_total))

    result = []
    for entry in grouped.values():
        engine_lines = [
            line_entry(idx, product, quantity, unit_price, line_total)
            for idx, (product, quantity, unit_price, line_total)
            in enumerate(entry['raw'])
        ]
        promo = evaluate_store_lines(entry['store'], engine_lines)
        lines = [
            (
                product,
                line_total - promo['line_discounts'].get(idx, Decimal('0.00')),
            )
            for idx, (product, _quantity, _unit_price, line_total)
            in enumerate(entry['raw'])
        ]
        result.append({
            'store': entry['store'],
            'subtotal': _money(sum(line_total for _product, line_total in lines)),
            'lines': lines,
        })
    return result


# --- Product promotion labels (Â§16.4 backend shape) ---------------------------


def _promotion_affects_product(promo, product):
    """Scope + targeting check for one product.

    Platform campaigns cover every store, seller campaigns only their own
    store; targeting rows then narrow the rule further (no rows = whole
    scope). BXGY targets its buy/get pair; free shipping is store-level, so
    any card inside the scope may carry the label."""
    campaign = promo.campaign
    if campaign.store_id is not None and campaign.store_id != product.store_id:
        return False
    if promo.kind == PromotionKind.BUY_X_GET_Y:
        return product.id in (promo.buy_product_id, promo.get_product_id)
    if promo.kind == PromotionKind.FREE_SHIPPING:
        return True
    return _line_matches(promo.target_rules.all(), product)


def promotion_label_for(product, promotions, *, display_price):
    """The best live badge for one product â€” None when no rule applies.

    Percentage product discounts and flash sales also carry `promo_price`
    (the number the card should show); quantity rules and free shipping
    carry the label only â€” their worth depends on what else is in the cart.
    Highest percent wins; ties go to the older rule, so the badge never
    flickers between two equally good offers."""
    best = None
    best_rank = None
    for promo in promotions:
        if not _promotion_affects_product(promo, product):
            continue
        percent = None
        promo_price = None
        if (
            promo.kind in (PromotionKind.PRODUCT_DISCOUNT, PromotionKind.FLASH_SALE)
            and promo.discount_type == VoucherDiscountType.PERCENTAGE
        ):
            percent = float(promo.value)
            promo_price = float(
                _money(
                    display_price * (Decimal('100') - promo.value) / Decimal('100')
                )
            )
        elif (
            promo.kind != PromotionKind.FREE_SHIPPING
            and promo.discount_type == VoucherDiscountType.PERCENTAGE
        ):
            percent = float(promo.value)
        rank = (percent if percent is not None else -1.0, -promo.id)
        if best_rank is None or rank > best_rank:
            best_rank = rank
            best = {
                'kind': promo.kind,
                'label': promo.label,
                'campaign': promo.campaign.name,
                'ends_at': (
                    promo.campaign.ends_at.isoformat()
                    if promo.campaign.ends_at
                    else None
                ),
                'percent': percent,
                'promo_price': promo_price,
            }
    return best



def resolve_product_promotion_label(product):
    """Facade for catalog serializers: returns badge text or None."""
    promotions = load_active_promotions()
    best = promotion_label_for(
        product,
        promotions,
        display_price=Decimal(str(getattr(product, 'base_price', '0.00'))),
    )
    return best['label'] if best else None

