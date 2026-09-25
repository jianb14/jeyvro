---
name: marketplace-orders
description: Develop the Jeyvro transaction flow — use when building the cart, checkout, orders and order items, order lifecycle, or the order-time inventory decrement/restore. Covers both backend (services, snapshots, transactions) and frontend (cart UI, checkout steps, order tracking); rules live in PROJECT_CONTEXT §6.
---

> **Source of truth:** [PROJECT_CONTEXT.md](../../PROJECT_CONTEXT.md) — when anything conflicts, the project context wins. Catalog entry: #22 in [SKILL_CATALOG.md](../../SKILL_CATALOG.md).

# Jeyvro Marketplace — Orders Domain (Cart → Checkout → Orders)

One responsibility: **how to develop the buying flow** — cart, checkout, orders/order-items, lifecycle states, and order-time inventory. Rules live in §6; payments live in `payments-skill`.

## Purpose

Turn a customer's cart into trustworthy orders: server-computed totals, immutable purchase snapshots, correct multi-store scoping, and inventory that can never go negative.

## Current honest state

Cart, checkout, orders, payments, and fulfillment are **live** (Phases 7–10): `apps/cart` (session-keyed guest carts merged into the account cart at login), server-computed checkout with per-store shipping and order-time reservation, `apps/orders` (Order / SellerOrder / OrderItem snapshots, fulfillment services, and the `carriers/` adapter registry with append-only tracking events), and `apps/payments` (adapter seam, ledger, webhooks). **Phase 11 added the customer post-purchase surface**: order history/detail endpoints with an audit-derived timeline, immutable receipt data, reorder re-validation, the server's `can_cancel` verdict, and return/refund/issue request intake (`OrderRequest` — adjudication lands with Phase 17). Frontend: `/orders`, `/orders/:number`, `/orders/:number/receipt`, all wired through `data/orders.js`.

**Rules live in PROJECT_CONTEXT §6 (v1.9):** checkout is signed-in only with a validated shipping address; shipping is a per-store flat fee plus an optional threshold; totals are server-computed; order creation is one transaction that snapshots everything and reserves stock; fulfillment is per store with partial shipments, carrier adapters, append-only tracking, and COD captured at delivery; customer post-purchase reads and actions are owner-scoped, server-verdict-driven, and receipt data is immutable.

## When to use

- Cart data model + cart UI; checkout steps (address → shipping → payment → review)
- Order/order-item models, lifecycle transitions, order tracking
- Inventory decrement at purchase and restore on cancellation

## When NOT to use

- Payment capture/ledger/webhooks (`payments-skill`) · product/variant modeling (`marketplace-catalog`) · generic rules (`backend-core`)

## Workflow

1. **Understand** — §6 Cart/Checkout/Orders rules + the §6 entity map; roles: customer buys, seller fulfills their items, staff oversees.
2. **Inspect** — existing cart/order code and the frontend cart components (`CartItem`, `CartSummary`, `Stepper`); reuse first.
3. **Plan** — cart model → checkout service (recompute, snapshot, decrement in ONE transaction) → order lifecycle transitions → frontend steps per `frontend-feature`/`ux-patterns`.
4. **Implement** — services own totals, snapshots, stock; views thin (`backend-api`).
5. **Test** — money flows are §11 priority 1: totals recompute, snapshot immutability, concurrent stock (row locks), cancel-restore.
6. **Review** — no client-trusted math anywhere; every §6 order state reachable and audited.
7. **Fix** — in the checkout/inventory services.
8. **Verify** — checklist below.

## Rules (binding)

1. The cart is server-side and per-user; **totals are recomputed on the backend at checkout** — client prices/quantities are never trusted (§6, §10.1).
2. Checkout runs recompute + snapshot + inventory decrement inside one transaction with `select_for_update` on stock rows (`backend-core` rule 6).
3. `OrderItems` snapshot title/price/store at purchase time and are immutable (§9).
4. Multi-vendor scoping: sellers see and fulfill only their store's order items; customers only their own orders.
5. Lifecycle transitions are explicit service functions per §6 states (placed → awaiting payment → paid → shipped → delivered → completed / cancelled / refunded) with an audit trail — no ad-hoc status writes.
6. Cancelled/restocked flows restore inventory transactionally; never negative stock.
7. Frontend checkout keeps input state per `frontend-state` (URL/step state), uses `Stepper`, and never computes displayed totals independently of the API.
8. Post-purchase surfaces (history, timeline, receipt, reorder, request intake) are owner-scoped and driven by server verdicts — `can_cancel`, request eligibility, and live availability for reorder are never guessed client-side (§6 v1.9).

## Best practices

- One checkout service entry point — every rule (totals, stock, snapshot) is inherited by all callers.
- Show lifecycle via `OrderStatusBadge`/`Timeline` primitives; states come from the API, never guessed client-side.
- Test concurrent checkout of the last item — the classic race.

## Common mistakes

- Storing computed totals on the cart and trusting them later.
- Decrementing stock after payment confirmation instead of inside the checkout transaction (oversell window).
- Letting a seller endpoint return other stores' items.
- Free-form status strings instead of the §6 state machine.

## Verification checklist

- [ ] Totals recomputed server-side at checkout; client math absent
- [ ] Snapshots immutable; per-store scoping deny paths tested
- [ ] Stock decrement/restore transactional; no negative stock (concurrency tested)
- [ ] Lifecycle transitions explicit + audit-logged
- [ ] Frontend uses API state only; all UX states wired (`ux-patterns`)
- [ ] Post-purchase surfaces owner-scoped; receipt data immutable; reorder reports skipped lines
