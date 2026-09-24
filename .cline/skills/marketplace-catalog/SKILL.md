---
name: marketplace-catalog
description: Develop the Jeyvro catalog domain — use when building product management, categories, product variants, product images, inventory/stock, product discovery, search, or filtering/sorting for the marketplace. Covers both Django (backend-feature recipe) and React (frontend-feature flow) for these areas; domain rules live in PROJECT_CONTEXT §6.
---

> **Source of truth:** [PROJECT_CONTEXT.md](../../PROJECT_CONTEXT.md) — when anything conflicts, the project context wins. Catalog entry: #21 in [SKILL_CATALOG.md](../../SKILL_CATALOG.md).

# Jeyvro Marketplace — Catalog Domain

One responsibility: **how to develop the catalog domain** — products, categories, variants, images, stock, and product discovery (search/filter/sort) — across backend and frontend. Business *rules* stay in PROJECT_CONTEXT §6; this skill is the development instruction.

## Purpose

Sellers manage rich product data (variants, images, stock) while customers discover it fast through server-side search and filtering — without duplicating entities or trusting the client.

## Current honest state

Backend `catalog` app is **live** (Phase 5): Category tree, Brand, Product (full lifecycle with staff publish/reject, audit-logged), Variant (auto-SKU, own price/stock via Inventory OneToOne, DB CHECK against negative availability), StockMovement append-only history, validated image upload (FileField + magic bytes — no Pillow per C3). Public browse/search/filter/sort are server-side over a display-price annotation. `data/products.js` now talks to the real API (mock→API swap done, shape-compatible). Ahead: variant-level image selection and customer browsing UI (Phase 6), order-time reservation consumption (Phase 8).

## When to use

- Building product CRUD, category tree, variants, image upload, stock management
- Search, filtering, sorting, category browsing (customer side)
- Any "product/variant/inventory" backend or frontend work

## When NOT to use

- Cart/checkout/orders (`marketplace-orders`) · reviews (`marketplace-community`) · generic modeling rules (`backend-core`) · generic UI primitives (`frontend-ui`)

## Workflow

1. **Understand** — read the §6 Catalog rule + domain map (§6 entity relationships); which roles act here (seller manages, customer browses)?
2. **Inspect** — existing models/components for products/variants/categories; never create a parallel entity.
3. **Plan** — backend: model + constraints → migration → service → serializer → viewset (per `backend-core`/`backend-api`); frontend: page flow per `frontend-feature` + accessors.
4. **Implement** — ownership-scoped endpoints; server-side search/filter/pagination.
5. **Test** — variant/stock constraints, search correctness, scoping deny-paths (§11).
6. **Review** — contract mirrors the data-layer product shape; §6 rules traced.
7. **Fix** — in services, not viewsets.
8. **Verify** — checklist below.

## Rules (binding)

1. One entity, one model — inspect before creating; a variant is NOT a second product (§14, §6).
2. Variants carry their own price/stock; the product price shown is resolved server-side from the selected variant — never trusted from the client.
3. Search, filter, and sort run **server-side** with pagination (`{count, items}`) — never client-filter a full catalog.
4. Inventory is per-variant; stock checks and decrements happen in transactions at order time (see `marketplace-orders`) — stock display is read-only truth from the backend.
5. Product images are validated (type/size) and stored via Django media handling (§8).
6. Seller endpoints are store-scoped: a seller manages only their products (deny path tested, `security` skill).
7. Category tree changes are migrations-level facts — never hardcode categories in the frontend.

## Best practices

- Index browse paths early: category, store, price, created (§9) — search/filter depend on them.
- Reuse `ProductCard`/`ProductGrid`/`StockIndicator`/`VariantPicker` primitives; new UI only via `frontend-ui`.
- Seed data mirrors the frontend contract shape exactly (the `data-layer` swap stays trivial).

## Common mistakes

- Modeling a variant as a product copy; storing stock on both product and variant.
- Client-side filtering of the whole catalog "because the mock data is small".
- Forgetting store scoping — one seller sees another's products.
- Hardcoded category lists in components.

## Verification checklist

- [ ] No duplicate product/variant/category models; §6 rules traced
- [ ] Variants own price/stock; server resolves display price
- [ ] Search/filter/sort server-side, paginated, indexed
- [ ] Store scoping enforced + deny path tested
- [ ] Images validated; seed matches the frontend contract
