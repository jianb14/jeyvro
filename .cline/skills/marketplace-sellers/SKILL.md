---
name: marketplace-sellers
description: Develop the Jeyvro seller domain — use when building seller registration, store profiles and settings, store status and staff moderation of stores, seller sales dashboards and analytics, or any seller-side store management for the marketplace. Covers backend and frontend for these areas; multi-vendor rules live in PROJECT_CONTEXT §4/§6.
---

> **Source of truth:** [PROJECT_CONTEXT.md](../../PROJECT_CONTEXT.md) — when anything conflicts, the project context wins. Catalog entry: #23 in [SKILL_CATALOG.md](../../SKILL_CATALOG.md).

# Jeyvro Marketplace — Sellers Domain

One responsibility: **how to develop seller management and stores** — seller onboarding, store profiles, store moderation, and seller analytics — across backend and frontend. The multi-vendor heart of Jeyvro: every seller is a user with a store (§4), never a parallel account type.

## Purpose

Sellers register, run their own storefront, and see their own numbers — while staff moderate store quality and no seller ever sees another's data.

## Current honest state

Backend `stores` app is **live** (Phase 4): `SellerApplication` + `Store` models, moderation service (audit-logged via the early `audit` foundation), `/api/v1/stores/` endpoints (apply, my/store, public storefront, staff review queue). Frontend has the real flows: `/sell` application, account "My store" settings tab, `/store/:slug` public page. Still ahead: seller sales dashboard/analytics (order events must exist first) and validated file uploads for store media.

## When to use

- Seller registration flow; becoming-a-seller on an existing customer account (§4: a user can be both)
- Store profile/settings (name, description, logo, status), store pages
- Seller sales dashboard / analytics
- Staff-side store moderation (approve/suspend)

## When NOT to use

- Product/variant management inside the store (`marketplace-catalog`) · payout money math (`payments-skill`) · generic modeling (`backend-core`)

## Workflow

1. **Understand** — §4 roles + §6 domain map (Store → Products; seller sees only their store); which flows: registration, moderation, dashboard?
2. **Inspect** — existing store/seller models, `StoreCard`/layout primitives, mock store data shapes.
3. **Plan** — backend: store model + ownership → service → serializer → viewset (per `backend-core`/`backend-api`); frontend: seller pages per `frontend-feature`.
4. **Implement** — store-scoped endpoints; dashboard aggregates read-only.
5. **Test** — ownership deny-paths (seller A ≠ store B), moderation permissions, dashboard aggregates correctness.
6. **Review** — §6/§4 traced; contract mirrors data-layer store shapes.
7. **Fix** — in services.
8. **Verify** — checklist below.

## Rules (binding)

1. A seller IS a user with a store — never a duplicate seller/account model (inspect first, §14).
2. A seller touches only the store they own — every store endpoint re-verifies ownership (deny path tested, `security` skill).
3. Store status changes (pending → approved → suspended) are staff actions through the moderation service — audit-logged (§9/§10.7); sellers never self-approve.
4. Seller analytics are **aggregates derived from order/payment events** — served from reporting data, never computed live from heavy OLTP queries per request (§17), and strictly scoped to the seller's own store.
5. Dashboard numbers are read-only API truth — the frontend never estimates sales, revenue, or ratings itself.
6. Store media (logo) validated like product images (type/size, §8).

## Best practices

- Registration creates the store in a pending state — staff moderation flips it live (audit-logged).
- Reuse `StoreCard` and dashboard primitives; new UI only via `frontend-ui`.
- Seed store data mirrors the frontend contract shapes.

## Common mistakes

- A "seller profile" model duplicating the user or store.
- Sales numbers computed in the frontend from raw lists.
- Moderation actions without audit records.
- One seller's dashboard leaking another store's aggregates.

## Verification checklist

- [ ] No duplicate seller/store models; ownership verified per endpoint
- [ ] Moderation transitions explicit + audit-logged; sellers cannot self-approve
- [ ] Analytics scoped to own store, served from reporting data
- [ ] Frontend displays API truth only; all UX states wired
- [ ] Store media validated; seed matches contract shapes
