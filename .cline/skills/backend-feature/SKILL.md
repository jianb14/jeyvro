---
name: backend-feature
description: Implement one Jeyvro marketplace domain end-to-end on the backend — use when building accounts, stores, catalog, cart, orders, payments, reviews, wishlist, messaging, notifications, or audit features, or when deciding where a domain's business logic lives. Domain rules live in PROJECT_CONTEXT §6 — this skill implements them; it never redefines them.
---

> **Source of truth:** [PROJECT_CONTEXT.md](../../PROJECT_CONTEXT.md) — when anything conflicts, the project context wins. Catalog entry: #11 in [SKILL_CATALOG.md](../../SKILL_CATALOG.md).

# Jeyvro Backend Feature — Domain Playbook

One responsibility: **the repeatable recipe for shipping one marketplace domain on the backend**. Jeyvro is a multi-vendor marketplace: every domain is ownership-scoped (each product/order/review belongs to a store or a user), and every critical rule is enforced server-side (§6, §10).

## Purpose

Ship consistent domains fast — the same shape of model, service, API, permissions, and tests every time — so the tenth domain is as predictable as the first.

## Current honest state

Backend is live: `accounts` (full auth stack, Phase 3), `stores` (seller/store foundation with the early `audit` app, Phase 4), `catalog` (products/variants/inventory with validated uploads, Phase 5), and `cart` (server cart + private wishlist with guest-session carts and the login merge, Phase 7) — each with services, serializers, permissions, and tests. The frontend mock→API swap is done for auth/stores/catalog, and cart/wishlist are wired to the live API from day one. Next domain in the build order: `orders` (Phase 8) — it consumes the cart service and the catalog stock services.

## When to use

- Building/extending any marketplace domain on the backend (accounts, stores, catalog, cart, orders, payments, reviews, wishlist, messaging, notifications, audit)
- Deciding where a domain's business logic lives (service layer)
- Multi-vendor scoping: store ownership, order snapshots, inventory

## When NOT to use

- Schema conventions (`backend-core`) · HTTP shape details (`backend-api`) · permission *patterns* (`security`) — this skill composes them · frontend flows (`frontend-feature`)

## Workflow (per domain)

1. **Understand** — read the domain's rules in PROJECT_CONTEXT §6 first; §6 is the spec. What does the frontend contract expect?
2. **Inspect** — existing apps/models/services that overlap; reuse beats new (§14).
3. **Plan** — model + constraints → migration → service functions → serializer → viewset + permissions → tests; the plan is written before code.
4. **Implement** — per `backend-core` (model), `backend-api` (HTTP), `security` (permissions).
5. **Test** — §11: models, permissions, and money flows tested; **no order/payment logic merges without tests** (the `testing` skill gates this).
6. **Review** — ownership scoping checked per endpoint; every §6 rule traced to code or a test.
7. **Fix** — gaps are fixed where they belong (service layer), never as viewset hacks.
8. **Verify** — checklist below.

## Rules (binding)

1. **§6 is the spec** — order lifecycle, checkout recompute, snapshots, verified-buyer reviews: implemented as written, never re-invented per domain.
2. **Never trust client calculations** — prices, totals, payments, inventory, and permissions are recomputed/verified on the backend (§6, §10.1).
3. Multi-vendor scoping on every query: sellers see/touch only their store's data; customers only their own records.
4. Business logic lives in service functions/model methods — views and serializers stay thin.
5. Checkout recomputes totals server-side; OrderItems snapshot title/price at purchase time and are immutable (§6, §9).
6. Inventory decrements run inside transactions with row locks (see `backend-core` rule 6).
7. Payments use the gateway-adapter interface with a ledger record + status per payment (§6); the dedicated `payments-skill` split happens when the real gateway adapter is built (SKILL_ARCHITECTURE §6).
8. Every domain ships with tests before merge (§11) and its seed data matches the frontend contract shapes.
9. Inspect existing services before writing new ones — one rule, one implementation (never duplicate discount/totals logic across domains).

## Best practices

- Build order: `accounts` → `stores` → `catalog` → `cart` → `orders` → `payments` → `reviews` → `messaging`/`notifications` → `audit`.
- Close each domain with seed data + one manual smoke through the real frontend flow (the mock→API swap lands via `data-layer`).
- Domain services are importable across domains — `orders` consumes the `cart` totals service; it never re-reads client prices.

## Common mistakes

- Copying another domain's viewset and inlining logic instead of extracting a service.
- A seller endpoint returning other stores' products/orders (missing store scoping).
- Storing computed totals on the cart instead of recomputing at checkout.
- Skipping the verified-buyer check when creating reviews (§6).
- Building `payments` ad hoc before the adapter interface exists.

## Verification checklist

- [ ] Every §6 domain rule traced to code or a test
- [ ] All money/inventory math server-side; snapshots immutable
- [ ] Store/customer ownership scoping verified per endpoint (deny path tested)
- [ ] Business logic in services; views/serializers thin
- [ ] Tests pass: models + permissions + money flows (§11)
- [ ] Contract aligned with the data-layer accessors; seed matches shapes
