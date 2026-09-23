# JEYVRO — Skill Catalog

> Subordinate to [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) and [SKILL_ARCHITECTURE.md](SKILL_ARCHITECTURE.md) — on any conflict, those win (project context first).
> Version 1.5 · 27 entries: 25 existing skills — the catalog is COMPLETE (every approved skill now exists; future additions follow the SKILL_ARCHITECTURE trigger rules).

## 0. Priority Levels

- **ESSENTIAL** — required for normal Jeyvro development.
- **RECOMMENDED** — highly useful for common development tasks.
- **OPTIONAL** — advanced/future functionality; created only when its trigger fires (no speculative skills, per SKILL_ARCHITECTURE §0.4).

## 1. Existing Skills (Tier 1–2) — already validated against the codebase; do not rewrite

### 1. jeyvro-project — ESSENTIAL
Category: Core Development / Orientation
Purpose: single entry point for workspace orientation.
Scope: stack, commands (incl. Windows `npm.cmd` quirk), folder map, 47-component inventory, routes-vs-design-system rules.
When to use: session start; "where/how/what stack" questions; routing to the right specialist skill.
When NOT: as carrier of project facts (PROJECT_CONTEXT owns those) or deep conventions.
Dependencies: none (root). Used by: everything.

### 2. design-tokens — ESSENTIAL
Category: UI/UX · Tailwind CSS
Purpose: correct token usage in all frontend styling.
Scope: `@theme` tokens, moss/sand/night palette roles, light→dark pairs, shadows/radius/animations, Tailwind v4 CSS-first rules.
When to use: any styling work; token changes; fixing hardcoded hex/arbitrary values.
When NOT: component logic, UX behavior, review verdicts.
Dependencies: none. Used by: frontend-ui, frontend-feature, frontend-review.

### 3. ux-patterns — ESSENTIAL
Category: UI/UX · Accessibility
Purpose: right feedback in the right place + accessibility build rules.
Scope: async states (Skeleton/EmptyState/Alert/Toast), modal/drawer behavior, keyboard/focus/≥44px touch targets, breakpoints 360/768/1280.
When to use: any feature build; behavior questions; loading/empty/error/success wiring.
When NOT: token values, code style, verification (frontend-review owns that).
Dependencies: none. Used by: frontend-ui, frontend-feature, frontend-review.

### 4. frontend-ui — ESSENTIAL
Category: Frontend · React
Purpose: build and extend the UI primitives in `components/ui`.
Scope: React conventions (named exports, `forwardRef`, `useId`, `cx()`), Icons as the only icon source, design-system registration.
When to use: new primitive; modifying an existing component; icon work.
When NOT: pages/flows (frontend-feature), data fetching (data-layer), token definitions (design-tokens).
Dependencies: design-tokens, ux-patterns.

### 5. data-layer — ESSENTIAL
Category: Frontend · API Integration
Purpose: components never fetch — all data flows through accessors.
Scope: `src/data/` accessor pattern, response envelopes (`{count, items}`, `{error}`), product shape, mock→Django swap path.
When to use: fetching/mocking/wiring data; API contract design; the mock→API swap.
When NOT: backend implementation, UI code.
Dependencies: none. Shares the API contract with backend-api (mirror, never redefine).

### 6. frontend-feature — ESSENTIAL
Category: Frontend · Marketplace Features
Purpose: end-to-end page/flow builds (customer, seller, admin UI).
Scope: routes, composition of primitives + accessors + ux states, feature checklists.
When to use: any customer/seller/admin page or flow (product pages, cart UI, checkout UI, storefront, profile…).
When NOT: new primitives (frontend-ui), tokens (design-tokens), backend, contract redesign without data-layer.
Dependencies: design-tokens, ux-patterns, frontend-ui, data-layer. Gated by: frontend-review.

### 7. frontend-review — ESSENTIAL
Category: Frontend · QA Gate
Purpose: pre-done review against all frontend conventions.
Scope: checklist review, a11y verification (`docs/a11y.md`), performance verification (bundle, render behavior).
When to use: before declaring frontend work done; regression checks.
When NOT: writing code or tests (testing owns test-writing).
Dependencies: design-tokens, frontend-ui, ux-patterns.

### 18. frontend-state — ESSENTIAL
Category: Frontend · State Management
Purpose: where each piece of client state lives (local → lift → derive → URL → server → global).
Scope: useState discipline, derived values, form state, `useSearchParams` for filters/search/sort/pagination, optimistic updates, functional updates.
When to use: adding state, wiring filters/URL state, deciding local vs global, "where should this value live?".
When NOT: fetching data (data-layer), feedback presentation (ux-patterns), building primitives (frontend-ui).
Dependencies: data-layer, ux-patterns.

### 19. frontend-responsive — ESSENTIAL
Category: Frontend · Responsive · Mobile-first
Purpose: mobile-first layout authoring that holds at ~360 / ~768 / ~1280.
Scope: base-layer-first authoring, min-width breakpoints, reference grids, touch-first spacing, DOM order, overflow prevention.
When to use: any layout/grid/navigation work; overflow fixes; breakpoint choices.
When NOT: review verdicts (frontend-review Gate 3), in-primitive touch sizing (frontend-ui).
Dependencies: design-tokens, ux-patterns.

### 20. frontend-performance — ESSENTIAL
Category: Frontend · Performance
Purpose: everyday speed discipline — dependencies, renders, media, effects, bundle honesty.
Scope: C3 dependency rule, stable keys, measured-only memoization, image dimensions/lazy-loading, React.lazy policy, effect hygiene, build-output checks.
When to use: adding imports/dependencies, list renders, media, effects, reading build output.
When NOT: review verdicts (frontend-review Gate 5), deep profiling (future performance-skill trigger), backend performance.
Dependencies: data-layer, ux-patterns.

## 2. Backend Skills (Tier 3) — existing (backend & database phase)

### 8. backend-core — ESSENTIAL
Category: Backend · Python · Django · Database · PostgreSQL
Purpose: Django project structure and data modeling.
Scope: scaffold, apps-per-domain (§8), settings/.env split, models + migrations, constraints/indexes/Decimal money (§9), Python style, admin registration.
When to use: backend startup; adding/changing models; Django configuration.
When NOT: HTTP layer (backend-api), domain flows (backend-feature), permission patterns (security).
Dependencies: PROJECT_CONTEXT §8–§9. Used by: backend-api, backend-feature, deployment.

### 9. backend-api — ESSENTIAL
Category: Backend · Django REST Framework · API Development
Purpose: design and implement the versioned JSON API.
Scope: routers/viewsets, serializers (never raw model fields), `/api/v1`, envelopes, pagination, JSON 404s, throttling hooks.
When to use: building/changing endpoints; contract alignment.
When NOT: frontend accessors (data-layer owns the contract view), business-logic internals.
Dependencies: backend-core, data-layer (contract), security. Used by: backend-feature.

### 10. security — ESSENTIAL
Category: Security · Authentication · Authorization
Purpose: one home for all security enforcement (PROJECT_CONTEXT §10).
Scope: session/JWT decision, password policy, rate limiting, DRF permission classes, object-level ownership, group-based staff roles, IDOR checks, CORS/CSRF, secrets/.env, audit logging.
When to use: any auth/permissions/secrets work; mandatory reading for admin, payments, and backend features.
When NOT: login-page UX (frontend-feature), infrastructure (deployment).
Dependencies: backend-core. Mandatory for: backend-api, backend-feature, deployment.

### 11. backend-feature — ESSENTIAL
Category: Multi-Vendor Marketplace (backend side)
Purpose: the repeatable per-domain playbook — accounts, catalog, cart, orders, payments, reviews, messaging, notifications, audit.
Scope: model + constraints → migration → service layer → serializer → viewset + permissions → tests → seed (aligned with the frontend contract).
When to use: implementing any backend domain (categories #16–#28).
When NOT: redefining domain rules (PROJECT_CONTEXT §6 owns them), generic conventions.
Dependencies: backend-core, backend-api, security, testing.

## 3. Process & Operations Skills (Tier 4) — existing (advanced/supporting phase)

### 12. git-workflow — ESSENTIAL (from repo init)
Category: Git and GitHub
Purpose: version control conventions.
Scope: init inside `Jeyvro/` only (C4 — never the stray home-root repo), branches `feat/…`/`fix/…`, commit style, PR + self-review, `.gitignore` (`.env`!).
When to use: any repository operation.
When NOT: deployment concerns.
Dependencies: jeyvro-project. Used by: deployment.

### 13. testing — ESSENTIAL
Category: Testing · Debugging
Purpose: test strategy and the debugging method.
Scope: pytest/DRF (models, permissions, money flows — §11: no order/payment merge without tests), Vitest/RTL later, E2E later; reproduce → isolate → fix → regression test.
When to use: writing tests; bug fixes; money-flow changes.
When NOT: review verdicts (frontend-review), feature code.
Dependencies: backend-feature, frontend conventions. Gates: backend-feature.

### 14. deployment — ✅ created (advanced/supporting phase)
Category: DevOps · Deployment
Purpose: shipping Jeyvro to real infrastructure.
Scope: env separation, prod settings, static/media serving, prod PostgreSQL, object storage, HTTPS, backups, release steps.
When to use: launch; environment/production changes.
When NOT: daily development; performance tuning.
Dependencies: backend-core, security, git-workflow.

## 4. Marketplace Skills & Resolved Optional Entries (all triggers fired)

> Resolved optional entries: **#15 `ai-tooling` — ✅ created** (advanced/supporting phase) · **#16 `payments-skill` — ✅ created as #26 below** · **#17 `admin-panel-skill` — ✅ superseded by `marketplace-admin` (#25)** · **#27 `performance-skill` — ✅ created** (fired deep-performance split).

### 21. marketplace-catalog — ESSENTIAL
Category: Marketplace · Product Management · Categories · Variants · Inventory · Product Discovery · Search · Filtering
Purpose: develop the catalog domain (products, categories, variants, images, stock, discovery) end-to-end.
Scope: backend recipe + frontend flow for product CRUD, category tree, variants, image upload, stock, server-side search/filter/sort.
When to use: any product/variant/category/inventory/search work.
When NOT: cart/checkout/orders (marketplace-orders), reviews (marketplace-community), generic rules (backend-core/frontend-ui).
Dependencies: backend-feature, backend-api, backend-core, frontend-feature, data-layer.

### 22. marketplace-orders — ESSENTIAL
Category: Marketplace · Cart · Checkout · Orders · Inventory (order-time)
Purpose: develop the buying flow — cart, checkout, orders/order-items, lifecycle, order-time inventory.
Scope: server-side totals recompute, immutable snapshots, single-transaction checkout with stock locks, lifecycle state machine, order tracking UI.
When to use: any cart/checkout/order/inventory-at-purchase work.
When NOT: payment capture/ledger/webhooks (payments-skill), catalog modeling (marketplace-catalog).
Dependencies: backend-feature, backend-core, backend-api, security, frontend-feature, ux-patterns, frontend-state.

### 23. marketplace-sellers — ESSENTIAL
Category: Marketplace · Seller Management · Seller Stores · Seller Analytics
Purpose: develop seller onboarding, store profiles/moderation, and seller analytics.
Scope: registration, store model + ownership, moderation states, dashboards from reporting aggregates.
When to use: any seller/store/dashboard/moderation work.
When NOT: product management inside stores (marketplace-catalog), payout math (payments-skill).
Dependencies: backend-feature, security, backend-api, frontend-feature.

### 24. marketplace-community — ESSENTIAL
Category: Marketplace · Reviews · Ratings · Wishlist · Messaging · Notifications
Purpose: develop trust and communication features (reviews, ratings, wishlist, messaging, notifications).
Scope: verified-buyer enforcement, unique review constraint, server-side rating aggregates, moderation, private wishlist, participant-scoped conversations, notification triggers.
When to use: any review/rating/wishlist/messaging/notification work.
When NOT: order status/tracking (marketplace-orders), payment disputes (payments-skill).
Dependencies: backend-feature, backend-api, security, frontend-feature, ux-patterns.

### 25. marketplace-admin — ESSENTIAL
Category: Marketplace · Admin Marketplace Management
Purpose: develop the staff side — oversight dashboards, moderation, settings, reports, staff groups, audit views.
Scope: group-gated staff surfaces, Django admin registration, audit-logged sensitive actions, reporting aggregates.
When to use: any staff/admin/management/moderation/settings/audit work.
When NOT: seller-facing store management (marketplace-sellers), permission patterns (security).
Dependencies: backend-feature, security, backend-api, frontend-feature, ux-patterns.

### 26. payments-skill — ESSENTIAL (trigger fired — created)
Category: Marketplace · Payments · Marketplace Commissions
Purpose: develop money movement — ledger, COD, gateway adapters, webhooks, refunds, payouts, commissions.
Scope: ledger records + status, verified captures, idempotent signature-verified webhooks, adapter interface, server-computed commissions, record-derived payouts.
When to use: any payment/refund/payout/commission work.
When NOT: order lifecycle/snapshots (marketplace-orders), refund permissions (marketplace-admin).
Dependencies: backend-feature, backend-core, security, testing, marketplace-orders.

### 17. admin-panel-skill — ✅ superseded by `marketplace-admin` (#25)

### 27. performance-skill — ✅ created (advanced/supporting phase)
Category: Performance (API · Database · Caching)
Purpose: measured optimization of endpoints, queries, caching, and media serving.
Scope: N+1 fixes at the queryset layer, evidence-backed indexes, §17 hot-path caching with invalidation, pagination/throttling, media sizing, perf regression tests.
When to use: slow endpoints/pages, query plans, cache introduction, image/media serving efficiency.
When NOT: frontend render/bundle work (`frontend-performance`), modeling-time index rules (`backend-core`).
Dependencies: backend-core, backend-api, deployment.

## 5. Catalog Review (duplicate / overlap / breadth / missing checks)

| Check | Result |
|---|---|
| Duplicates | None — every skill has a unique responsibility. |
| Overlaps | 3 potential overlaps, each with a resolution rule: (1) `backend-api` ↔ `data-layer` = shared contract, defined once, mirrored only; (2) `frontend-review` ↔ `testing` = judge vs build; (3) a11y build (`ux-patterns`) vs a11y verify (`frontend-review/docs/a11y.md`) — one home each. |
| Too broad | `backend-feature` is the widest — mitigated: domain rules stay in PROJECT_CONTEXT §6, and `payments-skill` is a ready split trigger. |
| Too narrow | None — cart/wishlist/messaging deliberately have no skills (layer skills handle them). |
| Missing | None vs. the 39 categories. Considered and rejected: SEO (single-market PH, §16 C6), i18n (fixed currency/language), seeding (inside backend-feature), error handling (inside backend-api + ux-patterns). |
| Unnecessary | None — every skill owns at least one category. |
| Incorrect dependencies | Corrected during review: (1) `testing` gates `backend-feature` (feature depends on testing, not vice versa); (2) `frontend-review` is a *gate*, not a dependency, of `frontend-feature`; (3) `ai-tooling` keeps a minimal dependency (jeyvro-project). |

## 6. Dependency Map

```
PROJECT_CONTEXT.md + SKILL_ARCHITECTURE.md     ← sources of truth (all skills)
│
├─ jeyvro-project (root, no deps)
│
├─ FRONTEND CHAIN
│   design-tokens ──┐
│   ux-patterns ───┤→ frontend-ui → frontend-feature → [frontend-review gate]
│   data-layer ────┘        │
│                          └────────→ frontend-review
│
├─ BACKEND CHAIN
│   backend-core → security → backend-api → backend-feature
│        │             │           │             │
│        └────────────┴───────────┴── [testing gate]
│                          │
│   data-layer (contract) ─┘ (backend-api mirrors the API shapes)
│
└─ PROCESS / OPERATIONS
    git-workflow → deployment ← backend-core + security
    ai-tooling (standalone)
    marketplace-catalog → backend-feature + backend-api + frontend-feature
    marketplace-orders → backend-feature + security (consumes payments-skill)
    marketplace-sellers / community / admin → backend-feature + security
    payments-skill → backend-feature + marketplace-orders + security
    performance-skill → backend-core + backend-api
```

Core flow: `jeyvro-project → design-tokens / ux-patterns → frontend-ui → frontend-feature → data-layer → backend-core → security → backend-api → backend-feature → testing (gate) → deployment (ship)`.

## 7. Finalized List — skills to actually create

**Do NOT create (already exist, 25):** jeyvro-project · design-tokens · ux-patterns · frontend-ui · data-layer · frontend-feature · frontend-review · git-workflow · testing · frontend-state · frontend-responsive · frontend-performance · backend-core · security · backend-api · backend-feature · marketplace-catalog · marketplace-orders · marketplace-sellers · marketplace-community · marketplace-admin · payments-skill · deployment · ai-tooling · performance-skill

**Create (7 definite, in order):**

| # | Skill | Priority | Create when |
|---|---|---|---|
| 1 | `backend-core` | ESSENTIAL | ✅ created — backend & database phase |
| 2 | `security` | ESSENTIAL | ✅ created — backend & database phase |
| 3 | `backend-api` | ESSENTIAL | ✅ created — backend & database phase |
| 4 | `git-workflow` | ESSENTIAL | ✅ created — core phase |
| 5 | `backend-feature` | ESSENTIAL | ✅ created — backend & database phase |
| 6 | `testing` | ESSENTIAL | ✅ created — core phase |
| 7 | `deployment` | ✅ created — advanced/supporting phase |

**Trigger-fired skills (all resolved):** `ai-tooling` ✅ · `payments-skill` ✅ (#26) · `admin-panel-skill` ✅ (#25) · `performance-skill` ✅ (#27)

**Totals: 27 catalog entries — 25 skills exist, 2 superseded/merged (#16 → #26, #17 → #25). Nothing left to write: the approved Jeyvro skill system is complete.**