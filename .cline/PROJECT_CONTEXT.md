# JEYVRO — Project Context (Single Source of Truth)

> Version 1.6 · v1.6 changelog: §11 corrected to reality — the frontend test gate is live (Vitest + Testing Library, run via a space-free path on this machine) and the backend pytest gate is mandatory; no new marketplace rules this phase.
> Version 1.5 · v1.5 changelog: §6 cart & wishlist rules added (Phase 7) — guest session carts with login merge, line prices/stock/totals always server-resolved, wishlist private and product-level.
> Version 1.4 · v1.4 changelog: C5 corrected to reality — the frontend mock→API swap is complete (Phase 6); no new marketplace rules this phase.
> Version 1.3 · Approved by the project owner.
> v1.3 changelog: §6 product publishing, inventory, and pricing/discount rules added (Phase 5).
> v1.2 changelog: §6 seller verification, store lifecycle, and store ownership rules added (Phase 4).
> v1.1 changelog: git-repo status corrected (§15, C4) · seller payouts added (§5, §6, §17) · §7 `features/` marked as target structure · §18 added (how skills reference this document).
> This document is the source of truth for every Jeyvro skill, rule, and AI session.
> On any conflict, this file wins. When reality changes, update this file first, then the affected skills.

## 1. Project Overview

Jeyvro is a modern, production-ready **multi-vendor e-commerce marketplace**. Independent sellers register and run their own stores — products, variants, inventory, orders, and customer communication. Customers browse, search, and buy from those stores with cart, checkout, payments, order tracking, reviews, and messaging. Staff administer the whole marketplace.

Two properly separated applications:

- **Frontend:** React SPA (Vite, Tailwind CSS, React Router)
- **Backend:** Django + Django REST Framework API
- **Database:** PostgreSQL

They communicate through a versioned JSON API only.

## 2. Project Goals

- **G1** — Ship a complete, production-ready multi-vendor marketplace.
- **G2** — Original identity: premium, clean, professional. Never a Shopee/Lazada/TikTok Shop/Amazon clone (those are pattern references only).
- **G3** — Maintainable and scalable: new features without rewrites.
- **G4** — Secure by default: the backend is the final line of defense.
- **G5** — Great developer experience for humans and AI agents: clear conventions, self-documenting structure.

## 3. Target Users

- **Customers** — shoppers (Philippine market, mobile-first) buying handpicked local goods.
- **Sellers** — small businesses and artisan shops running their own storefronts.
- **Admin/Staff** — marketplace operators: support, moderation, catalog, analytics.

## 4. User Roles

| Role | Account | Scope |
|---|---|---|
| Customer | registered | own cart, wishlist, orders, reviews, messages, profile, addresses, notifications |
| Seller | registered + store | own store, products, variants, inventory, orders, sales, customer messages |
| Admin/Staff | staff flag / groups | users, sellers, products, categories, orders, payments, review moderation, settings, reports, staff permissions, audit logs |

Rules:

- A user can be both customer and seller.
- Staff permissions are group-based (e.g. support, moderator, admin) — not all-or-nothing.
- Role and ownership checks are enforced by the backend on every request, never by the UI alone.

## 5. Core Features

### Customer
Register/login/logout · browse products · search · filter & sort · categories · product details · variants · cart · wishlist · checkout · payments · order tracking · reviews & ratings · seller messaging · profile & address book · notifications.

### Seller
Seller registration · store profile management · product CRUD · product image upload · variants · inventory · order processing · customer messaging · sales dashboard · store settings.

### Admin/Staff
User & seller management · product & category management · order oversight · payments & seller payouts · review moderation · marketplace settings · reports & analytics · staff permissions · audit logs.

## 6. Marketplace Features (cross-cutting)

- **Catalog:** product = title, description, images, category, price, variants (size/color with own stock/price), store, rating.
- **Cart:** per-user and server-side; totals are recomputed on the backend at checkout — client prices are never trusted.
- **Checkout:** address → shipping → payment → review; creates an Order that snapshots prices and items at purchase time.
- **Payments:** gateway-adapter interface (start with Cash-on-Delivery; PayMongo/GCash/Maya later); every payment has a ledger record and status.
- **Seller payouts:** every seller balance derives from order/payment records (never manually keyed); payouts start as manual, admin-recorded settlements that are audit-logged (§9), moving to automated gateway settlement later (§17).
- **Seller verification (Phase 4):** a registered customer applies as a seller (store name, description, contact) → the application and the store both start `pending` → staff approve (store goes `active`) or reject (a reason is required; the applicant may reapply). Sellers never self-approve — every review is a staff action.
- **Store lifecycle & ownership (Phase 4):** `pending → active → suspended` — staff-only transitions through the moderation service, audit-logged (§9); one user owns exactly one store, and every store endpoint re-verifies ownership server-side (§10.3). Suspended/pending stores are invisible on public storefronts but keep their data.
- **Product publishing (Phase 5):** lifecycle `draft → pending_review → published → unpublished / rejected / archived`; "out of stock" is a **derived display state** (every variant at zero available), never a stored status. Sellers own draft→pending_review, unpublish, and archive; staff own pending_review→published / rejected (reason required, audit-logged). The public catalog exposes published products from active stores only.
- **Inventory (Phase 5):** stock lives **per variant only** — never duplicated on the product; available = on_hand − reserved. Every change runs inside a transaction with row locks (`select_for_update`) and appends a StockMovement row (append-only history); stock can never go negative (DB CHECK constraint). Order-time reservation/commit lands with Phase 8 and reuses these services.
- **Pricing & discounts (Phase 5):** money is Decimal(12,2) — never float (C6). The displayed price is resolved server-side (lowest active variant price, falling back to the product base price) and never trusted from the client; discounts derive from `compare_at_price` and are computed server-side, never stored client-side.
- **Cart (Phase 7):** the cart is server-side — one cart per customer or per guest session (session-keyed; exactly one owner enforced by the database). Guest carts merge into the account cart at login, quantities summed in one transaction. Cart lines store **quantities only**: unit prices and stock are resolved server-side on every read and recomputed again at checkout, and totals (subtotal, savings, item count) are computed by the backend and only rendered by the client. Add/update validate variant, product, store, and live stock; carts group by store for multi-vendor display.
- **Wishlist (Phase 7):** private per customer and product-level — owner-scoped queries with one row per (user, product) enforced by a DB constraint. Availability is derived server-side: saved products that leave the catalog show as unavailable instead of being silently deleted.
- **Orders:** explicit lifecycle (placed → awaiting payment → paid → shipped → delivered → completed / cancelled / refunded) with audit trail.
- **Reviews:** verified buyers only; moderateable; seller ratings derive from product reviews.
- **Messaging:** buyer ↔ seller conversations per order or per product.
- **Notifications:** in-app first (unread badge); email digests later.
- **Entity relationships (the domain map every marketplace skill builds on):** `Store` (owned by 1 seller) → many `Products` → many `Variants` + `Images` · `Category` tree → Products · `Cart` (1 customer or 1 guest session) → `CartItems` → Variant · Checkout → `Order` → `OrderItems` (immutable snapshots, store-scoped) → `Payments` (ledger + status) → seller payout records · Inventory lives per `Variant` (transactional decrement at purchase, restore on cancel) · `Review` (1 per user+product, verified buyers) → Product → seller rating · `WishlistItem` (customer ↔ product) · `Conversation` (customer ↔ store, per order/product) → `Messages` · `Notification` (per user) · `AuditLog` (staff actions). Role scopes (customer / seller / staff / administrator) per §4 — staff power is group-based, administrator is the full-control group.

## 7. Frontend Architecture Expectations

Stack: React · Vite · JavaScript/JSX (no TypeScript for now) · Tailwind CSS v4 (CSS-first `@theme`, no tailwind.config.js) · React Router.

```
frontend/src/
  routes/             marketplace pages — thin, compose features
  features/           per-domain modules (auth/, cart/, wishlist/, …) holding
                      logic, hooks, and feature-specific components — created
                      per-domain as features are built (auth, cart and wishlist
                      are live; seller/checkout land with their phases)
  components/ui/      GENERIC primitives only (no cart/order-specific code)
  components/layout/  app-wide chrome (Navbar, Footer)
  data/               THE only data access point — async accessors
  lib/                utilities (cx, useTheme, useToasts, formatters, api client)
```

- The existing design system is the UI foundation: moss/sand/night + semantic tokens, ~45 primitives in `components/ui/`, dark mode via the `.dark` class. Details live in the `design-tokens` and `frontend-ui` skills.
- New pages follow `routes/Home.jsx`: accessors for data, skeletons while loading, EmptyState for zero results, Alert for errors, Toast for successes.
- Token-only styling: never hardcode colors/shadows/animations when a token exists.
- Icons only from `components/ui/Icons.jsx`.
- Local state by default; server state flows through accessors; avoid global client-state libraries until genuinely needed.

## 8. Backend Architecture Expectations

Stack: Python · Django · Django REST Framework · PostgreSQL. Status: **to be built** (see §16, C5).

- **App-per-domain:** `accounts`, `stores`, `catalog`, `cart`, `orders`, `payments`, `reviews`, `messaging`, `notifications`, `analytics`, `audit`.
- **API:** versioned under `/api/v1/`, JSON-only, DRF viewsets + serializers; model fields are never exposed without a serializer.
- **Response envelopes:** list → `{count, items}`; single → object; error → `{error, detail?, field_errors?}`; not found → JSON 404 (never HTML).
- **Business logic** lives in service layers/model methods — not views — so it is testable in isolation.
- **Validation:** DRF serializer validation + model constraints; frontend validation is UX only, never security.
- **Permissions:** DRF permission classes per role + object-level checks (sellers touch only their store; customers only their own orders).
- **Media:** product images validated (type, size) and stored via Django's media handling (local in dev, object storage in prod).

## 9. Database Architecture Expectations

- PostgreSQL is the primary database (SQLite never in production). Django ORM + migrations; no raw SQL in views.
- Core entities: User, Store, Product, ProductVariant, ProductImage, Category, Cart, CartItem, Order, OrderItem, Payment, Review, WishlistItem, Address, Conversation, Message, Notification, AuditLog.
- Rules: FK constraints on every relation with explicit `on_delete` (PROTECT for money/legal, CASCADE/SET_NULL where safe); indexes on browse paths (category, store, price, created); unique constraints where meaningful (one review per (user, product)); money as Decimal — never float.
- OrderItem snapshots title/price at purchase time (immutable).
- AuditLog records who changed what and when for staff actions and critical transactions.

## 10. Security Expectations

1. Backend validation is final — never trust frontend-only checks for prices, stock, roles, or ownership.
2. Auth: Django session auth (or JWT if justified), hashed passwords (Django default), rate limiting on auth endpoints.
3. IDOR protection: every endpoint verifies ownership (does order X belong to this user?).
4. CORS allowlist (never `*` in production); CSRF protection where applicable.
5. Secrets in `.env` (never committed); `.env.example` in repo; no credentials in logs or chat output.
6. OWASP basics: ORM-only queries, XSS-safe rendering, sanitized uploads.
7. Least-privilege staff roles; sensitive staff actions are audit-logged.

## 11. Testing Expectations

- **Backend (mandatory — live):** pytest/DRF tests for models, serializers, permissions, and money flows (cart totals, checkout, inventory decrement, refunds). No order/payment logic merges without tests. Run `"%LOCALAPPDATA%\jeyvro-venv\Scripts\python.exe" -m pytest -q` from `backend/`.
- **Frontend (live gate):** `npm run lint` + `npm run test` + `npm run build` from `frontend/`. Vitest + Testing Library cover data accessors and components; Playwright E2E for checkout comes later. **On this machine the test gate must run through a space-free path** (`subst X: <repo>` then `cd X:\frontend`) — the space in the repo path breaks Vitest's module identity and fails every suite with a misleading error (see the `testing` skill).
- Test before refactoring; every bug fix ships with a regression test.

## 12. UI/UX Principles

- "Calm by design": clean, spacious, strong hierarchy — own identity on moss/sand/night; never a Shopee/Lazada clone.
- Avoid: gradients, excessive shadows, excessive animations, visual clutter.
- Feedback lives in the right place (see `ux-patterns`): inline Alert for form failures, Toast for action results, Modal confirm for destructive actions, Skeleton for loading, EmptyState with a next step.
- Accessibility: WCAG AA contrast, full keyboard support, visible focus, associated labels, ≥44px touch targets, never color-only status.
- Mobile-first responsive; layouts verified at ~360 / 768 / 1280px.

## 13. Coding Principles

**Frontend:** named exports; `cx()` for class merging (className last); `forwardRef` + `useId` on form controls; const maps for variants; small function components; no duplicate primitives; token-only styling.

**Backend:** PEP 8 / Django style; thin views + service functions; DRF idioms; small focused commits; DRY but do not abstract prematurely.

**Both:** no dead code or leftover commented blocks; every new dependency needs explicit user approval (see C3).

## 14. AI-Agent Behavior (binding for every skill)

1. Read before write — inspect relevant files before editing.
2. Plan complex changes before implementing; execute in small verifiable steps.
3. Reuse-first: inventory existing components/utils before creating anything new.
4. Never rewrite working code without reason; never duplicate functionality; never add dependencies without approval.
5. Preserve existing behavior; refactors pass the same gates as new features.
6. Security-sensitive logic is validated on the backend; never present client-side validation as sufficient.
7. Validate work by running it: lint + build (frontend), tests + runserver smoke (backend) — never claim done without running the checks.
8. Never expose secrets; never commit `.env`.
9. When reality drifts from this document, update this document first, then affected skills.
10. When an outcome is ambiguous or irreversible, surface the decision to the user before acting — in the user's language, with the trade-off stated.

## 15. Development Workflow

- Monorepo layout: `frontend/` + `backend/` (the Django project, once scaffolded) + `docs/` as needed.
- Git: feature branches (`feat/…`, `fix/…`), small commits, self-review of diffs. The repo lives inside `Jeyvro/` (GitHub: `jianb14/jeyvro`); a stray zero-commit repo at the user-home root (`C:/Users/Christian R`) exists — **never use it**.
- Dev run: frontend `npm run dev` (Vite, proxies `/api` → Django on port 8000); backend venv + `manage.py runserver` (port 8000) once Django exists.
- Gates per change: lint → build → (tests when they exist) → manual smoke of affected flows.
- Windows notes on this machine: use `npm.cmd` in PowerShell; redirect shell output to a log file when capture is unreliable.

## 16. Important Constraints

- **C1:** Never copy the exact look/layout of Shopee, Lazada, TikTok Shop, Instagram, or Amazon. Patterns are fine; cloning is not.
- **C2:** JavaScript/JSX (no TypeScript) unless the owner explicitly revisits.
- **C3:** No new runtime dependency without explicit user approval.
- **C4:** Git repo initialized inside `Jeyvro/` (GitHub: `jianb14/jeyvro`) — keep changes small and separable. A stray zero-commit repo exists at the user-home root (`C:/Users/Christian R`) — it must not be used.
- **C5:** Backend exists (Django + DRF + PostgreSQL, `backend/`). All frontend accessors in `frontend/src/data/` talk to the real Django API — the mock→API swap is complete (auth, stores, catalog; Phase 6 closed the last one; no mock accessors remain). **Django is the sole approved backend target — no other backend stack.**
- **C6:** Currency is PHP ₱ (Philippine market) — Decimal on the backend, formatted via the `Price` component on the frontend.
- **C7:** Secrets never appear in code, logs, or AI responses.

## 17. Future Scalability Considerations

- Data swap: mock accessors → Django API at a single choke point (`data/`); see the `data-layer` skill.
- Search: PostgreSQL full-text first → Meilisearch at scale.
- Media: local storage → S3-compatible object storage + CDN.
- Async work: Celery + Redis for emails, notifications, image processing.
- Caching: product-detail and category-list caching.
- Payments: gateway adapters (PayMongo/GCash/Maya) behind one interface; automated seller payouts/settlements ride the same adapters.
- Analytics: reporting schema fed by order events, not heavy OLTP queries.
- API-first design leaves doors open for a mobile/PWA client.

## 18. How Skills Reference This Document (binding convention)

1. Every Jeyvro `SKILL.md` opens with: `> **Source of truth:** [PROJECT_CONTEXT.md](../../PROJECT_CONTEXT.md) — when anything conflicts, the project context wins.` (path resolves from `.cline/skills/<name>/` to this file).
2. Skills carry *how-to* detail; this document carries *what is true*. Never duplicate project facts into skills — link instead, so facts have exactly one home.
3. When reality changes, update this document first, then the affected skills (§14, rule 9).
4. A new skill must not contradict this document; if it needs a new project rule, the rule is added here first, then the skill may reference it.
5. Future skills follow the same layout: `.cline/skills/<skill-name>/SKILL.md` (+ optional `docs/`), YAML frontmatter with `name` and a `description` written as trigger conditions ("use when…").
6. The skill map — what exists, what owns which category, and when a new skill may be created — lives in [SKILL_ARCHITECTURE.md](SKILL_ARCHITECTURE.md), with the per-skill catalog (purpose, scope, when-to-use, priorities) in [SKILL_CATALOG.md](SKILL_CATALOG.md). Both are subordinate to this document.


