"""Privacy-safe customer display helpers (Phase 12.5 — marketplace-sellers).

A seller sees the minimum needed to fulfil an order and nothing more (§10):
no emails, no full names before the order is accepted, masked phone numbers,
and the full delivery address only once the seller starts processing the
order. One implementation, shared by the seller order serializer and the
seller dashboard.
"""


def mask_name(full_name):
    """'Maria Santos' → 'Maria S.'; a single word stays whole (it is the
    least identifying half anyway once paired with the order context)."""
    parts = (full_name or '').split()
    if not parts:
        return ''
    if len(parts) == 1:
        return parts[0]
    return f'{parts[0]} {parts[-1][0]}.'


def mask_phone(phone):
    """'09171234567' → '•••••••4567' — last 4 visible for oral confirmation."""
    digits = ''.join(ch for ch in (phone or '') if ch.isdigit())
    if not digits:
        return ''
    return '•' * max(0, len(digits) - 4) + digits[-4:]
