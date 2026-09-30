# JEYVRO — Master Development Roadmap

> This file is the master build-order document for JEYVRO.
>
> It defines the sequence of work required to build JEYVRO from its
> current frontend foundation into a complete, production-ready,
> multi-vendor marketplace.
>
> Companion: `../.cline/PROJECT_CONTEXT.md`
>
> **Source of truth:** `PROJECT_CONTEXT.md` defines what JEYVRO is, its
> architecture, constraints, conventions, and non-negotiable rules. This
> file defines **when and in what order** the system is built.
>
> **Rule:** If the build order changes, update this file first, then
> update affected skills and project documentation.

## Status Tracker

> Update the Status column after every phase gate passes. Legend: ⬜ Not started · 🔄 In progress · ✅ Done.

| # | Phase | Status |
|---|---|---|
| 0 | Product & System Foundation | 🔄 Partially pre-existing (PROJECT_CONTEXT v1.1) |
| 1 | Repository & Development Infrastructure | ✅ Done — GitHub connected (jianb14/jeyvro), pushed & verified; only backend-linter item deferred to tooling pass |
| 2 | Backend Foundation & Database | 🔄 Foundation verified (Django+DRF+PG live, migrations, tests) — media/filtering/sorting land with their feature phases |
| 3 | Authentication, Users & Access Control | 🔄 Core verified (11/11 backend tests + live E2E) — session expiry settings & staff-endpoint permissions land with later phases |
| 4 | Seller & Store Foundation | ✅ Done — stores app + audit foundation, 19/19 backend tests, lint/build green, live E2E smoke (apply→approve→storefront) passed; logo/banner are URL-based until the media phase |
| 5 | Catalog, Products & Inventory | ✅ Done — catalog app (products/variants/inventory/validated uploads), 26/26 tests, live smoke (create→publish→public) passed, mock→API swap done; variant image selection lands with Phase 6 |
| 6 | Customer Shopping & Discovery | ✅ Done — marketplace navbar (server search + API categories), Home sections, /products browse (URL-driven filters/sort/pagination), category pages, /product/:slug detail (gallery, variant picker, quantity, store info, related), storefront product shelves, recently-viewed foundation; lint/build green, 9/9 frontend tests, 29/29 backend tests, live smoke passed. Add-to-cart / buy-now / wishlist shipped as real features in Phase 7 (row 7); variant-level image selection (§5.3) remains open |
| 7 | Cart & Wishlist | ✅ Done — server-side `apps/cart` (Cart/CartItem/WishlistItem with exactly-one-owner + one-row-per-(cart,variant)/(user,product) DB constraints): session-keyed guest carts merged at login, quantity-only lines with price/stock/totals re-resolved server-side on every read, store-grouped payloads, private product-level wishlist; `/cart` + `/wishlist` pages with cart/wishlist data accessors, CartContext/WishlistContext, wishlist heart + quick-add variant resolution on every ProductCard; 15/15 cart tests, 44/44 backend tests, 5 files/15 frontend tests, lint/build green. On this machine `npm run test` must run through a space-free path (`subst X:`) — see the testing skill |
| 8 | Checkout, Shipping Calculation & Order Creation | ✅ Done — `apps/orders` live (Order/SellerOrder/OrderItem snapshots, server-side flat fee + threshold shipping, transactional stock reservation & release on cancel), /checkout + /orders/:number frontend routes, 27 backend tests + race condition gate passed, Vitest (63/63) & build green |
| 9 | Payments & Financial Transactions | ✅ Done — `apps/payments` domain (Payment, PaymentAttempt, Refund, append-only PaymentTransaction ledger, WebhookEvent), gateway adapter interface (COD live, generic hosted-gateway seam for PayMongo/GCash/Maya), signature-verified idempotent webhooks, online payment expiry cron command, full & partial stock-restoring refunds, Checkout step 3 + OrderDetail payment cards; 89/89 backend tests (45 tests for money flows + race gates) & 27/27 frontend tests passed, lint & build green |
| 10 | Order Fulfillment & Delivery | ✅ Done — `apps/orders` shipments (carrier adapter registry, tracking numbers, append-only tracking events), seller process/pack/ship endpoints, partial shipments + parent-order status aggregation, COD capture on delivery; 7/7 fulfillment tests passed (commit `2afb1cf`) |
| 11 | Customer Account & Order Management | ✅ Done — owner-scoped history/detail/receipt, audit-derived timeline with whitelisted copy, reorder + cancel verdicts, return/refund/issue intake (`OrderRequest`; Phase 17 adjudicates); 11.1 panels live since Phase 3; Contact seller/support deferred to Phase 15 (documented) |
| 12 | Seller Operations & Seller Dashboard | ✅ Done — seller dashboard aggregates (sales/orders/low-stock), product/variant editor with lifecycle + bulk ops, inventory console (append-only movements), seller order flow (process/pack/ship) with the §12.5 privacy ladder, store settings; gate tests `backend/tests/test_seller_operations.py` + `frontend/src/data/seller.test.js`; §12.6 messaging deferred to Phase 15 (documented) |
| 13 | Admin, Staff & Platform Operations | ✅ Done — Slice v1: seeded staff groups, seller approvals, store oversight, audit viewer. Slice v2: staff directory + audited role assignment (self/superuser/last-admin guards) and user management with session-revoking suspension. Slice v3: moderator catalog console (publish/reject + reason-gated takedown) and audited operations/administrator category & brand management. Slice v4: read-only order/payment operations console (order & shipment oversight, return/refund/dispute intake, payment/refund trail) with refund issuance tightened to finance/administrator. Slice v5: platform settings (`/staff/settings` — marketplace/commission/shipping/feature/notification as one audited singleton; COD gate, platform-owned payment window, new-store shipping seeds, new-account notification defaults); finance/operations now carry real §4 surfaces and the phase Gate is closed. Deferred: 13.3 seller verification (not yet scoped) and store *content* management (deliberate — seller-owned) |
| 14 | Reviews, Ratings & Trust | ✅ Done — `apps/reviews` (verified-buyer `create_review` proving a delivered/completed order item, one review per user+product DB constraint, server-computed product/store `rating_average`/`rating_count` inside every review transaction), staff moderation (`InStaffGroup` hide with reason + audit, restore, report auto-flag at 3 distinct reporters), seller reply (once, own store), eligibility verdict driving the edit form; `backend/tests/test_reviews.py` + frontend review UI/tests; seller-reply notification wired with Phase 15 (§15.3) |
| 15 | Messaging & Notifications | 🔄 Slice v1 shipped — `apps/messaging` (participant-scoped `Conversation` with order/product context and reuse-or-create threads, `Message`, per-participant read state, unread counts, report → moderation status, store-owner + staff access checks) and `apps/notifications` (`Notification` + `NotificationPreference` email gating via `GET`/`PUT /api/v1/notification-preferences`); endpoints `/api/v1/conversations/…`, `/api/v1/seller/conversations/`, `/api/v1/notifications/…`; UI `ConversationInbox` at `/account/messages` + `/seller/messages`, `MessageStoreButton` (product/order/support starters), `NotificationBell` badge with `action_url` navigation; §15.3 wired for order placed / shipment / new message / review reply; gate 3/4 (Background jobs waits on §15.4). Open: attachment uploads, mute toggles, staff report console, remaining §15.3 events |
| 16 | Promotions, Vouchers & Campaigns | 🔄 Slices v1–v3 shipped — `apps/promotions` (platform/seller vouchers — percentage or fixed with min spend, max-discount cap, usage + per-user limits, start/end window, first-order rule, product/category targeting rows), `POST /api/v1/vouchers/validate/` previews a code against the caller's live cart through the same service checkout uses, and redemption is atomic inside `create_order`: the row-locked `VoucherUsage` ledger plus `voucher.redeemed` audit keep counters and discounts race-condition safe and auditable, and orders snapshot `voucher_code`/`discount_total` with the payment collecting the discounted total. Slice v2: automatic promotions (`services.evaluate_store_lines` — product discount, flash sale, bundle threshold, free-shipping waiver, buy-X-get-Y) priced into cart, checkout preview and orders as `promotion_discount` (checkout preview parity fixed), seller CRUD at `/api/v1/seller/promotions/`, and the §16.4 UI — cart promotion labels, checkout voucher entry, order/receipt discount rows, `/seller/promotions` desk. Slice v3: §16.3 funding settled server-side at redemption — `split_funding` splits every discount into `platform_amount`/`seller_amount` on the ledger (shared = 50/50, odd cent to the platform) under DB constraints, plus BXGY engine coverage. Slice v4 closes the last §16.4 gaps: the buyer **Voucher Center** at `/vouchers` (public, scope tabs, copy-to-clipboard over the public-safe `GET /api/v1/vouchers/` shape — no client-side discount math), and the staff **Campaign & Promotion Console** at `/staff/campaigns` (campaigns table with `promotion_count`, a create-platform-campaign modal the server forces to `scope=platform` with a `campaign.created` audit row, and a platform-wide promotions oversight tab that keeps deactivated rules visible). Access follows §4: campaign management is operations/administrator, promotion oversight adds finance — the console fetches each list only when the caller's role may read it. Covered by `backend/tests/test_promotions.py` (13 tests) + `frontend/src/data/promotions.test.js` (18 tests) |
| 17 | Returns, Refunds & Disputes | ✅ Done — `apps/resolutions` (slices v1–v3). v1 return cases: server-verified eligibility and a return window snapshotted per case, per-line quantity caps, seller response, staff intervention/override, reverse-parcel tracking, and receipt-time line-scoped restock through the append-only stock ledger; refund arithmetic computed server-side from order snapshots (order-level discounts apportioned to the lines that enjoyed them, shipping back only on a fully returned slice), and the linked `OrderRequest` resolved by the case that answers it. v2 money movement: the case prices, `apps.payments` moves — `Refund.restock`/`Refund.return_case` keep manual refunds and case-paid payouts honest, `POST /api/v1/admin/returns/<ref>/refund` is finance/administrator-only and callable only after goods are received, partial settlements cap against the case then the payment, and the case follows its refund through the provider seam (`on_refund_settled`/`on_refund_failed`) with a refused gateway rolling the whole payout back. v3 disputes: `Dispute` (`JVDSP-…`) with append-only statements/evidence whose party is derived from the caller, staff claim + ruling with a mandatory reason that freezes the record, buyer withdrawal, and timeline + audit rows on every movement. Covered by `backend/tests/test_returns.py` (18 gate tests) |
| 18 | Search, Recommendations & Discovery | 🔄 §18.1 v1 shipped — `apps.search` live on `GET /api/v1/search/` (ranked PostgreSQL full-text over a weighted `tsvector`, composed filters, OR-counted facets, pagination, `pg_trgm` typo rescue) + `GET /api/v1/search/suggest/` (autocomplete), both public and permission-safe through one `searchable_products` chokepoint; frontend `/search` (URL-driven filters/sort/pagination, store/category companion strips, fuzzy disclosure) + navbar autocomplete on `src/data/search.js`. `backend/tests/test_search.py` (36 tests) + `frontend/src/data/search.test.js` (7 tests). §18.2 indexing strategy and §18.3 discovery still open |
| 18b | Search, Recommendations & Discovery (cont.) | ✅ §18.3 Discovery — `GET /api/v1/search/recommendations/` (public, `?kind=`) serves five shelves from one ranking entry point, each reading back through the same `searchable_products` chokepoint: `trending` (units in a 30-day window) and `popular` (all-time units) fall back to newest because a quiet marketplace still needs a homepage, while `related` (category, then brand, best-rated first), `similar` (nearest by the same `pg_trgm` machinery the typo rescue uses) and `personalized` (categories/brands of the shopper's own `seen=` history ranked by how well they sell) return fewer items rather than padded ones. Frontend: Home swaps the old discount-sorted "trending" placeholder for real Trending + Best sellers rails and adds "Recommended for you" from the browser's own recently-viewed list (no account, no server-side profile), and the product page gains a "Similar finds" rail beside "You might also like" with no card repeated across the two. Covered by `backend/tests/test_recommendations.py` (24 tests) + `frontend/src/data/search.test.js` (14 tests) |
| 19 | Analytics & Reporting | ✅ Done — §19.1 platform money, §19.2 seller analytics (`/seller/analytics`, ownership-scoped; Phase 12 dashboard untouched per marketplace-sellers rule 4), §19.3 operational analytics (`DailyOperationsMetric`/`DailyStoreOpsMetric` + `admin/analytics/operations/` & `performance/`), §19.4 reports (five CSV exports at `admin/analytics/export/<report>/`, gate baked into the route) — all served from `apps.reporting` rollups written only by `manage.py rebuild_reporting`. Gate passed (reconciliation proven by partition + cross-table checks; §4 matrix on every read and export). **Deferred, documented:** Excel/PDF export (C3 — needs a new runtime dependency; a fake .xlsx is worse than none) and the Phase 12 dashboard extension (rule 4). Suite at the gate: 325 backend + 189 frontend tests, lint/build/migrations green |
| 20 | Security, Compliance & Abuse Prevention | 🔄 §20.1 application security done — deny-by-default permissions + session-only auth, rate limiting (blanket + `auth`/`register`/`checkout`/`message` scopes) in front of the login lockout, CORS credentials fix, and the **public-tracking PII leak fixed** (a tracking number is a bearer token, not an identity); `docs/SECURITY_CHECKLIST.md` records all 11 items with evidence, `backend/tests/test_security_hardening.py` (11 tests), suite at review time: 336 backend tests + 189 frontend, lint/build/migrations green. §20.3 auditing done — `docs/AUDIT_COVERAGE.md` is the matrix of every sensitive operation and its action, three gaps closed (`analytics.exported` for the §19.4 CSVs, `product_price_changed`/`variant_price_changed`, and `store_profile_updated`, which turned a bare serializer save on the seller's shipping fee into an audited service), `backend/tests/test_audit_coverage.py` (7 tests). **§20.2 slice v1 (spam & messaging) done** — `apps.moderation` (pure content rules, one `ContentFlag` per subject, staff queue where support reads and only a moderator decides) on a **queue-never-censor** contract: a rule files a flag for a human and never rejects, edits, deletes or informs the author, so a false positive costs a queue row rather than a review. Messaging gained user-scoped `ConversationBlock`s and a write-only `conversation` throttle on thread starts. `docs/ABUSE_CONTROLS.md` + `backend/tests/test_abuse_controls.py` (60 tests) prove the catches *and* the false-positive guards; voucher abuse was already solid and needed nothing. **§20.2 slice v2 (stale-COD reservations) done** — an unpaid COD order held its stock reservation forever (payment expiry correctly excludes COD, and the reservation was wrongly bound to that same window); the fix is a staff worklist plus a manual, audited, reason-required release (`order.cod_reservation_released`) that never auto-cancels a possibly-in-transit parcel. Suite at this gate: **403 backend tests**, migrations + system check clean. Still open in §20.2: the per-order total-units ceiling + suspicious-order detection (slice v3), account abuse (slice v4) |
| 21 | Testing & Quality Assurance | ⬜ Not started |
| 22 | Performance & Scalability | ⬜ Not started |
| 23 | Deployment & Production Infrastructure | ⬜ Not started |
| 24 | AI & Advanced Marketplace Features | ⬜ Post-v1.0 |
| 25 | Final Production Audit | ⬜ Not started |

------------------------------------------------------------------------

## 0. How to Use This Roadmap

### Development rules

1.  Read `PROJECT_CONTEXT.md` and this roadmap before starting a new
    development task.
2.  Work top-to-bottom within each phase.
3.  Do not start a phase before its required dependencies are complete.
4.  A checkbox is checked only after the feature is implemented **and
    verified**.
5.  Never mark work complete because an AI agent claims it is complete.
6.  Every feature must include appropriate validation, error handling,
    permissions, and tests.
7.  Security is continuous. It is not postponed until the final phase.
8.  Backend business rules are authoritative. Never trust
    client-calculated prices, permissions, inventory, totals, discounts,
    or payment states.
9.  Keep frontend and backend responsibilities clearly separated.
10. Preserve existing working functionality when adding new features.
11. Do not introduce unnecessary dependencies.
12. Do not create duplicate implementations of the same business rule.
13. Keep API contracts documented and stable.
14. Prefer small, verifiable increments over large unverified changes.
15. Run the phase gate before moving to the next phase.

### Standard phase gate

At minimum, depending on the phase:

``` text
Frontend:
- npm run lint
- npm run build

Backend:
- python manage.py check
- migrations check
- test suite
- development server smoke test

Full-stack:
- API integration verification
- browser smoke test
- relevant E2E test
```

A phase is complete only when its gate passes.

------------------------------------------------------------------------

# 1. JEYVRO System Dependency Chain

The overall dependency order is:

``` text
Product Foundation
        ↓
Development Infrastructure
        ↓
Backend Foundation + Database
        ↓
Authentication + Access Control
        ↓
Seller + Store Foundation
        ↓
Catalog + Products + Inventory
        ↓
Customer Shopping + Discovery
        ↓
Cart + Wishlist
        ↓
Checkout + Shipping Calculation
        ↓
Payments + Financial Transactions
        ↓
Orders + Fulfillment + Delivery
        ↓
Customer Account + Order Management
        ↓
Seller Operations
        ↓
Admin + Staff + Platform Operations
        ↓
Reviews + Trust
        ↓
Messaging + Notifications
        ↓
Promotions + Vouchers
        ↓
Returns + Refunds + Disputes
        ↓
Search + Recommendations
        ↓
Analytics + Reporting
        ↓
Security + Abuse Prevention
        ↓
Testing + QA
        ↓
Performance + Scalability
        ↓
Production Infrastructure
        ↓
AI + Advanced Features
        ↓
Final Production Audit
```

### Why this order exists

-   The platform needs a stable product/system specification before
    implementation.
-   Backend and database foundations must exist before complex business
    domains.
-   Authentication and authorization must exist before ownership-scoped
    data.
-   Sellers and stores must exist before seller-owned products.
-   Catalog and inventory must exist before cart and checkout.
-   Checkout must exist before real orders and payments.
-   Order and fulfillment data must exist before reviews, returns,
    seller finance, and many notifications.
-   Admin operations depend on the underlying platform domains.
-   Search, analytics, AI, and optimization should build on stable
    transactional data.
-   Production hardening must verify the complete system rather than
    compensate for missing architecture.

------------------------------------------------------------------------

# 2. Phase 0 — Product & System Foundation

## Objective

Define the complete JEYVRO product before implementing the full
marketplace.

> **Single source of truth (PROJECT_CONTEXT §18):** the rules and lifecycles this phase defines must be written into `PROJECT_CONTEXT.md` — never into this roadmap; this file only references them. Known gaps PROJECT_CONTEXT does not yet cover: commission rules (seller registration/verification and store rules landed in PROJECT_CONTEXT v1.2; voucher + promotion + funding rules in v1.14; returns/refunds/disputes rules in v1.15). Add the remaining ones to PROJECT_CONTEXT first, then check the boxes below.

### 0.1 Product definition

-   [ ] Define JEYVRO product vision
-   [ ] Define marketplace purpose
-   [ ] Define target customer experience
-   [ ] Define seller experience
-   [ ] Define platform/admin experience
-   [ ] Define core marketplace value proposition
-   [ ] Define supported product categories
-   [ ] Define platform boundaries and out-of-scope features

### 0.2 User roles

-   [ ] Customer
-   [ ] Seller
-   [ ] Support Staff
-   [ ] Moderator
-   [ ] Finance/Ops Staff
-   [ ] Administrator
-   [ ] Super Administrator

### 0.3 Marketplace business rules

-   [x] Seller registration rules
-   [x] Seller verification rules
-   [x] Store ownership rules
-   [x] Product ownership rules
-   [x] Product publishing rules
-   [x] Inventory rules
-   [x] Pricing rules
-   [x] Discount rules
-   [x] Voucher rules — §6 (PROJECT_CONTEXT v1.14): server-verified codes judged by one service shared by preview and checkout, a row-locked atomic redemption ledger, the automatic promotion rules judged per line at every choke point, and §16.3 funding settled server-side into `platform_amount`/`seller_amount`
-   [ ] Commission rules
-   [ ] Payout rules
-   [x] Shipping rules — per-store flat fee (`shipping_flat_fee`) + optional per-store free-shipping threshold; COD carries no extra fee; tax slot reserved (§6 v1.7)
-   [ ] Cancellation rules
-   [ ] Return rules
-   [ ] Refund rules
-   [ ] Dispute rules
-   [ ] Review rules
-   [ ] Messaging rules
-   [ ] Notification rules
-   [ ] Moderation rules

### 0.4 Lifecycle definitions

-   [ ] Account lifecycle
-   [x] Seller lifecycle
-   [x] Store lifecycle
-   [ ] Product lifecycle
-   [ ] Inventory lifecycle
-   [x] Cart lifecycle — server cart stores quantities only; prices, stock and totals are recomputed on every read (§6 v1.5/v1.7)
-   [x] Checkout lifecycle — signed-in customer + validated address, server-computed totals, order created in one transaction (§6 v1.7)
-   [ ] Payment lifecycle
-   [x] Order lifecycle — placed → awaiting payment → paid → shipped → delivered → completed / cancelled / refunded; snapshots immutable, reservations commit at `paid` (§6 v1.7)
-   [ ] Shipment lifecycle
-   [ ] Return lifecycle
-   [ ] Refund lifecycle
-   [ ] Dispute lifecycle
-   [ ] Payout lifecycle
-   [ ] Review lifecycle

### 0.5 Permission matrix

-   [ ] Define role permissions
-   [ ] Define object ownership rules
-   [ ] Define staff permissions
-   [ ] Define admin-only actions
-   [ ] Define financial permissions
-   [ ] Define moderation permissions
-   [ ] Define support permissions

### 0.6 Architecture documentation

-   [ ] Define frontend architecture
-   [ ] Define backend architecture
-   [ ] Define database domains
-   [ ] Define API conventions
-   [ ] Define authentication strategy
-   [ ] Define media strategy
-   [ ] Define background-job strategy
-   [ ] Define search strategy
-   [ ] Define caching strategy
-   [ ] Define deployment architecture

### Gate

-   [ ] Product specification reviewed
-   [ ] Permission matrix reviewed
-   [ ] Core lifecycle diagrams reviewed
-   [ ] Architecture reviewed
-   [ ] No unresolved critical business rule

**Skills:** backend-core, marketplace-catalog, marketplace-orders, marketplace-sellers, marketplace-admin

------------------------------------------------------------------------

# 3. Phase 1 — Repository & Development Infrastructure

## Objective

Establish a clean, reproducible development environment.

### 1.1 Repository

-   [x] Initialize Git inside the `Jeyvro/` project only
-   [x] Configure Git identity and branch strategy
-   [x] Add `.gitignore`
-   [x] Exclude `node_modules`
-   [x] Exclude build output
-   [x] Exclude `.env`
-   [x] Exclude Python virtual environments
-   [x] Exclude `__pycache__`
-   [x] Exclude local database files
-   [x] Create initial commit
-   [x] Connect repository to GitHub
-   [x] Push verified initial state

### 1.2 Frontend

-   [x] Verify React + Vite
-   [x] Verify Tailwind CSS
-   [x] Verify routing
-   [x] Verify linting
-   [x] Verify production build
-   [x] Establish frontend folder conventions
-   [x] Establish component conventions
-   [x] Establish feature-module conventions
-   [x] Establish API/data-access conventions

### 1.3 Backend

-   [x] Create Django environment
-   [x] Create backend project
-   [x] Configure Django REST Framework
-   [x] Configure PostgreSQL
-   [x] Configure environment variables
-   [x] Create `.env.example`
-   [x] Configure development settings
-   [x] Configure production settings structure
-   [x] Configure CORS/CSRF strategy

### 1.4 Tooling

-   [ ] Configure backend linting/formatting
-   [x] Configure frontend linting/formatting
-   [x] Add backend test framework (pytest)
-   [x] Add frontend test framework (Vitest + Testing Library)
-   [x] Add test commands
-   [x] Document local setup
-   [x] Document environment variables

> **Note:** Phase 1 is complete. The backend items (1.3, pytest, docs, backend gate items) were delivered during **Phase 2** and are checked here on verified evidence (Django check, migrations on real PostgreSQL, live health smoke, pytest). "Connect repository to GitHub" and "Push verified initial state" completed 2026-09-24 (origin: github.com/jianb14/jeyvro, local/remote hashes verified identical, 0 secrets pushed). Remaining unchecked: "Configure backend linting/formatting" only (needs a C3-approved tool like ruff — deferred to a tooling pass).

### Gate

-   [x] Git repository clean
-   [x] Frontend lint passes
-   [x] Frontend build passes
-   [x] Django check passes
-   [x] PostgreSQL connection works
-   [x] Test harness executes

**Skills:** git-workflow, backend-core, frontend-feature, testing

------------------------------------------------------------------------

# 4. Phase 2 — Backend Foundation & Database

## Objective

Build the shared backend architecture before business-heavy features.

### 2.1 Backend architecture

-   [x] API root structure
-   [x] API versioning
-   [x] Shared serializers/utilities
-   [x] Exception handling
-   [x] Validation conventions
-   [x] Pagination
-   [ ] Filtering
-   [ ] Sorting
-   [x] API response conventions
-   [x] API error conventions
-   [x] Logging foundation
-   [ ] Request correlation strategy

### 2.2 Database conventions

-   [x] UUID strategy
-   [x] Created/updated timestamps
-   [x] Soft-delete policy where appropriate
-   [x] Unique constraints
-   [x] Database indexes
-   [x] Foreign-key conventions
-   [x] Decimal/money handling
-   [x] Timezone handling
-   [x] Status field conventions
-   [x] Historical/audit strategy

### 2.3 Domain app structure

Create and document boundaries for:

-   [x] `accounts`
-   [x] `stores`
-   [x] `catalog`
-   [ ] `inventory`
-   [x] `cart`
-   [x] `orders`
-   [x] `payments`
-   [ ] `shipping`
-   [x] `reviews`
-   [x] `notifications`
-   [x] `messaging`
-   [ ] `promotions`
-   [ ] `returns`
-   [ ] `finance`
-   [x] `analytics`
-   [x] `audit`

> **Note on app boundaries:** PROJECT_CONTEXT §8 (source of truth) defines the
> app list: accounts, stores, catalog, cart, orders, payments, reviews,
> messaging, notifications, analytics, audit. `inventory` folds into
> `catalog`, `shipping` into `orders`; `promotions`, `returns`, and `finance`
> land with their phases (16, 17) — each documented in PROJECT_CONTEXT first
> if it needs its own app. The 5 unchecked names are re-evaluated then.

### 2.4 Media foundation

> Media validation and storage are implemented with the first real file
> upload (seller product images, Phase 12) — documented in
> `backend/CONVENTIONS.md`. Deferred deliberately, not forgotten.

-   [ ] Image validation
-   [ ] File size validation
-   [ ] MIME/type validation
-   [ ] Safe file naming
-   [ ] Development media storage
-   [ ] Production storage abstraction

### Gate

-   [x] Architecture imports cleanly
-   [x] Initial migrations run
-   [x] Database constraints verified
-   [x] API error handling verified
-   [ ] Media validation tested

**Skills:** backend-core, backend-api, security

------------------------------------------------------------------------

# 5. Phase 3 — Authentication, Users & Access Control

## Objective

Create the identity and authorization layer used by every protected
domain.

### 3.1 User system

-   [x] Custom User model
-   [x] Customer profile
-   [x] Seller profile foundation
-   [x] Staff/admin role foundation
-   [x] Avatar support
-   [x] Account status
-   [x] Email address handling
-   [x] Phone number handling

### 3.2 Authentication

-   [x] Registration
-   [x] Login
-   [x] Logout
-   [x] Session/token strategy
-   [ ] Refresh/expiration strategy
-   [x] Email verification
-   [x] Password reset
-   [x] Change password
-   [x] Login throttling
-   [x] Failed-login handling

### 3.3 Authorization

-   [x] Role-based access control
-   [x] Object-level permissions
-   [x] Ownership checks
-   [x] Protected frontend routes
-   [x] Protected API endpoints
-   [ ] Staff permissions
-   [ ] Admin permissions

### 3.4 Customer account

-   [x] Profile page
-   [x] Account settings
-   [x] Security settings
-   [x] Address book foundation
-   [x] Notification preferences

### Gate

-   [x] Register → login → authenticated session
-   [x] Logout works
-   [x] Password reset works
-   [x] Unauthorized API access blocked
-   [x] Ownership checks tested
-   [x] Auth E2E smoke test passes

> **Note:** session-based auth chosen (same-origin SPA via the Vite proxy;
> JWT would be a new dependency — revisit under C3 when a mobile/PWA client
> arrives, §17). Unchecked items: "Refresh/expiration strategy" (explicit
> `SESSION_COOKIE_AGE` settings — next session), and Staff/Admin endpoint
> permissions (the `IsStaff`/`InStaffGroup` classes exist and are tested as
> classes, but they bind when the first staff endpoints arrive — Phase 13).
> Auth decisions are recorded in `backend/CONVENTIONS.md`.

**Skills:** security, backend-api, frontend-feature, backend-feature

------------------------------------------------------------------------

# 6. Phase 4 — Seller & Store Foundation

## Objective

Establish the multi-vendor side before seller-owned catalog data.

### 4.1 Seller application

-   [x] Become-a-seller flow
-   [x] Seller application model
-   [x] Seller information
-   [x] Verification status
-   [x] Admin review status
-   [x] Approval/rejection
-   [x] Rejection reason
-   [x] Seller activation/deactivation

### 4.2 Store

-   [x] Store model
-   [x] Store ownership
-   [x] Store slug
-   [x] Store name
-   [x] Store logo
-   [x] Store banner
-   [x] Store description
-   [x] Store policies
-   [x] Store status
-   [x] Public storefront

### 4.3 Seller settings

-   [x] Store profile
-   [x] Contact information
-   [x] Shipping settings foundation
-   [x] Return policy
-   [x] Store settings

### Gate

-   [x] Customer can apply as seller
-   [x] Admin can approve/reject
-   [x] Approved seller receives store
-   [x] Seller can edit store
-   [x] Public storefront works
-   [x] Unauthorized users cannot modify another store

**Skills:** marketplace-sellers, security, backend-feature, frontend-feature

------------------------------------------------------------------------

# 7. Phase 5 — Catalog, Products & Inventory

## Objective

Build the marketplace product system.

### 5.1 Catalog

-   [x] Category
-   [x] Subcategory
-   [x] Brand
-   [x] Product attributes
-   [x] Category hierarchy
-   [x] Category ordering/status

### 5.2 Product

-   [x] Product model
-   [x] Store ownership
-   [x] Product title
-   [x] Description
-   [x] SKU
-   [x] Base price
-   [x] Product status
-   [x] Product images
-   [x] Product attributes
-   [x] Product metadata

### 5.3 Variants

-   [x] Variant model
-   [x] Variant SKU
-   [x] Variant price
-   [x] Variant attributes
-   [ ] Variant image
-   [x] Variant status

### 5.4 Inventory

-   [x] Inventory record
-   [x] Available quantity
-   [x] Reserved quantity
-   [x] Low-stock threshold
-   [x] Stock adjustment
-   [x] Stock movement history
-   [x] Inventory transaction
-   [x] Stock reservation
-   [x] Stock release
-   [x] Transaction-safe decrement
-   [x] Transaction-safe restore

### 5.5 Product lifecycle

-   [x] Draft
-   [x] Pending review
-   [x] Published
-   [x] Unpublished
-   [x] Rejected
-   [x] Archived
-   [x] Out of stock

### 5.6 Seed data

-   [x] Seed categories
-   [x] Seed brands
-   [x] Seed stores
-   [x] Seed products
-   [x] Seed variants
-   [x] Seed inventory

### Gate

-   [x] Seller can create product
-   [x] Product can contain variants
-   [x] Product images upload safely
-   [x] Inventory updates correctly
-   [x] Stock cannot become invalid
-   [x] Public catalog only exposes valid products

**Skills:** marketplace-catalog, backend-feature

------------------------------------------------------------------------

# 8. Phase 6 — Customer Shopping & Discovery

## Objective

Build the main customer browsing experience.

### 6.1 Home

-   [x] Header
-   [x] Search
-   [x] Category navigation
-   [x] Hero/content sections
-   [x] Featured products
-   [x] Trending products
-   [x] Featured stores
-   [x] Promotional sections
-   [x] Recently viewed foundation
-   [x] Responsive states

### 6.2 Browse

-   [x] Category page
-   [x] Product listing
-   [x] Filters
-   [x] Sorting
-   [x] Pagination
-   [x] Loading states
-   [x] Empty states
-   [x] Error states

### 6.3 Product detail

-   [x] Product gallery
-   [x] Variant picker
-   [x] Price
-   [x] Discount display
-   [x] Stock indicator
-   [x] Quantity
-   [x] Add to cart
-   [x] Buy now
-   [x] Wishlist
-   [x] Store information
-   [x] Related products foundation

### 6.4 Storefront

-   [x] Store header
-   [x] Store information
-   [x] Store products
-   [x] Store rating foundation
-   [x] Store policies

### Gate

-   [x] Customer can browse products
-   [x] Search/browse results work
-   [x] Product details load correctly
-   [x] Variant selection works
-   [x] Stock state is accurate
-   [x] Responsive customer flow verified

**Skills:** frontend-feature, marketplace-catalog, frontend-responsive

------------------------------------------------------------------------

# 9. Phase 7 — Cart & Wishlist

## Objective

Create a reliable multi-vendor shopping basket.

### 7.1 Cart

-   [x] Server-side cart
-   [x] Cart items
-   [x] Add item
-   [x] Update quantity
-   [x] Remove item
-   [x] Clear cart
-   [x] Cart totals
-   [x] Variant validation
-   [x] Stock validation
-   [x] Price revalidation
-   [x] Multi-seller grouping
-   [x] Guest cart strategy
-   [x] Guest → account cart merge

### 7.2 Wishlist

-   [x] Wishlist
-   [x] Add item
-   [x] Remove item
-   [x] Wishlist page
-   [x] Wishlist state on ProductCard

### Gate

-   [x] Cart survives navigation
-   [x] Cart is server-authoritative
-   [x] Invalid stock cannot be purchased
-   [x] Multi-seller cart works
-   [x] Guest cart merge works
-   [x] Wishlist works

**Skills:** marketplace-orders, data-layer

------------------------------------------------------------------------

# 10. Phase 8 — Checkout, Shipping Calculation & Order Creation

## Objective

Build the critical checkout flow without trusting client-side totals.

> **Rules (PROJECT_CONTEXT §6 v1.7):** checkout is signed-in only, with a validated
> shipping address (guests merge their cart at login first); shipping is a per-store
> flat fee plus an optional per-store free-shipping threshold; totals are
> `Σ store subtotals + Σ store shipping fees`, computed server-side; order creation
> snapshots everything and reserves stock in one transaction, writing one parent
> `Order` plus one `SellerOrder` per store.

### 8.1 Address

-   [x] Address model
-   [x] Add address
-   [x] Edit address
-   [x] Delete address
-   [x] Default address
-   [x] Address validation
-   [x] Address snapshot for orders

### 8.2 Checkout

-   [x] Checkout session
-   [x] Cart validation
-   [x] Product validation
-   [x] Variant validation
-   [x] Stock validation
-   [x] Price revalidation
-   [x] Discount calculation foundation
-   [x] Shipping calculation
-   [x] Tax/fee architecture if applicable
-   [x] Final total calculation
-   [x] Order preview

### 8.3 Multi-vendor order creation

-   [x] Parent order
-   [x] Seller order/sub-order
-   [x] Order item snapshot
-   [x] Price snapshot
-   [x] Product title snapshot
-   [x] Variant snapshot
-   [x] Shipping snapshot
-   [x] Transaction-safe order creation
-   [x] Inventory reservation/decrement

### Gate

-   [x] Checkout cannot trust client totals
-   [x] Invalid cart cannot checkout
-   [x] Inventory is protected from race conditions
-   [x] Multi-seller order creates correct seller orders
-   [x] Order snapshots are immutable
-   [x] Backend tests for money flows pass (PROJECT_CONTEXT §11)

**Skills:** marketplace-orders, backend-core, security, testing

------------------------------------------------------------------------

# 11. Phase 9 — Payments & Financial Transactions

## Objective

Build payment architecture independently from the UI.

### 9.1 Payment domain

-   [x] Payment method
-   [x] Payment record
-   [x] Payment attempt
-   [x] Payment transaction
-   [x] Payment status
-   [x] Payment reference
-   [x] Payment ledger
-   [x] Failure handling
-   [x] Expiration handling

### 9.2 Payment methods

-   [x] Cash on Delivery
-   [x] Online payment abstraction
-   [x] Payment gateway adapter architecture
-   [x] Future PayMongo integration point
-   [x] Future GCash/Maya integration point

### 9.3 Webhooks

-   [x] Webhook endpoint
-   [x] Signature verification
-   [x] Idempotency
-   [x] Duplicate event handling
-   [x] Payment state reconciliation

### 9.4 Refund foundation

-   [x] Refund transaction model
-   [x] Full refund
-   [x] Partial refund
-   [x] Refund status

### Gate

-   [x] COD order flow works
-   [x] Payment states are server-authoritative
-   [x] Duplicate payment events are safe
-   [x] Webhooks are verified
-   [x] Financial records are auditable
-   [x] Backend tests for money flows pass (PROJECT_CONTEXT §11)

**Skills:** payments-skill, security, backend-feature

------------------------------------------------------------------------

# 12. Phase 10 — Order Fulfillment & Delivery

## Objective

Build the operational lifecycle after an order is created.

### 10.1 Order lifecycle

-   [x] Pending
-   [x] Awaiting payment
-   [x] Paid
-   [x] Processing
-   [x] Packed
-   [x] Shipped
-   [x] In transit
-   [x] Out for delivery
-   [x] Delivered
-   [x] Completed
-   [x] Cancelled
-   [x] Refund pending
-   [x] Refunded

### 10.2 Shipment

-   [x] Shipment model
-   [x] Shipment items
-   [x] Shipping method
-   [x] Shipping fee
-   [x] Package information
-   [x] Tracking number
-   [x] Carrier abstraction
-   [x] Shipment status
-   [x] Tracking history
-   [x] Delivery confirmation

### 10.3 Multi-seller fulfillment

-   [x] Separate seller fulfillment
-   [x] Separate shipments
-   [x] Partial shipment handling
-   [x] Parent order status aggregation

### Gate

-   [x] Seller can process orders
-   [x] Shipment can be created
-   [x] Tracking is visible
-   [x] Delivered state is recorded
-   [x] Parent order correctly aggregates seller shipments
-   [x] Backend tests for money flows pass (PROJECT_CONTEXT §11)

**Skills:** marketplace-orders, backend-feature

------------------------------------------------------------------------

# 13. Phase 11 — Customer Account & Order Management

## Objective

Complete the customer post-purchase experience.

### 11.1 Account

-   [x] Profile
-   [x] Addresses
-   [x] Security
-   [x] Notification preferences
-   [x] Account status

### 11.2 Orders

-   [x] Order history
-   [x] Order detail
-   [x] Seller-order detail
-   [x] Shipment tracking
-   [x] Order timeline
-   [x] Receipt
-   [x] Download/print receipt
-   [x] Reorder

### 11.3 Customer actions

-   [x] Cancel eligible order
-   [x] Request return
-   [x] Request refund
-   [x] Report issue
-   [x] Contact seller — live via Phase 15 (`MessageStoreButton` on the order's seller slice)
-   [x] Contact support — live via Phase 15 (same control, support-scoped thread)

> 11.3 returns/refunds/issues are **intake records** (`OrderRequest`):
> owner-scoped, server-verified eligibility (delivered slice / captured
> payment / open order), duplicates refused, and customers may withdraw
> pending requests. Adjudication, restocking, and any money movement belong
> to the Phase 17 returns flow. Receipt "download" is the browser print
> dialog (Save as PDF) — no extra dependency. The order timeline is
> derived from the append-only AuditLog with whitelisted customer-safe
> copy; raw audit payloads never cross the wire.

### Gate

-   [x] Customer can fully manage post-purchase lifecycle
-   [x] Unauthorized orders cannot be accessed
-   [x] Receipt contains correct immutable data

**Skills:** frontend-feature, marketplace-orders

------------------------------------------------------------------------

# 14. Phase 12 — Seller Operations & Seller Dashboard

## Objective

Give sellers complete operational control over their stores.

### 12.1 Dashboard

-   [x] Overview
-   [x] Sales summary
-   [x] Order summary
-   [x] Inventory alerts
-   [x] Recent orders
-   [x] Recent reviews

> **Slice v1 (done):** `GET /api/v1/stores/my/dashboard` returns the seller
> home aggregates (sales, orders, low-stock alerts, recent orders) and the
> `recent_reviews` slot — the section renders an honest empty state until
> Phase 14 ships the review model.

### 12.2 Products

-   [x] Product list
-   [x] Create product
-   [x] Edit product
-   [x] Delete/archive product
-   [x] Variants
-   [x] Images
-   [x] Bulk operations where appropriate

> **Slice v1 (done):** `/seller/products` runs on the seller-scoped catalog API
> (`/api/v1/catalog/my/products/` with `q`/`status` filters, variants, images,
> the `submit`/`unpublish`/`archive` lifecycle actions and the per-id bulk
> endpoint). Delete resolves to archive/deactivate whenever order history
> exists, and status is service-owned — never a free PATCH.

### 12.3 Inventory

-   [x] Stock management
-   [x] Stock adjustments
-   [x] Low-stock alerts
-   [x] Inventory history

> **Slice v1 (done):** `/api/v1/catalog/my/stock` serves the seller inventory
> console (`?q=`, `?low_stock=1`, `?variant_id=` history): adjustments are
> append-only StockMovement rows and thresholds are set per variant, so the
> dashboard's low-stock alerts and the history view read the same truth.

### 12.4 Orders

-   [x] Incoming orders
-   [x] Order details
-   [x] Accept/process
-   [x] Pack
-   [x] Ship
-   [x] Update fulfillment status

> **Slice v1 (done):** `/api/v1/seller/orders/` (store-scoped, `q`/`status`
> filters) drives `/seller/orders`: detail, `process` (accept), `pack` and
> `ship`, with the `can_*` flags taken straight from the domain service so the
> buttons can never drift from the fulfillment state machine.

### 12.5 Seller customers

-   [x] Customer order context
-   [ ] Customer communication
-   [x] Privacy-safe customer information

> **Slice v1 (done):** seller order payloads carry the §12.5 privacy ladder —
> masked name/phone, no address and never an email before acceptance, revealed
> exactly at `process` — plus the order context fulfillment needs.
> "Customer communication" is the messaging thread, so it closes with §12.6.

### 12.6 Seller messaging

-   [x] Conversation list
-   [x] Chat view
-   [x] Buyer ↔ seller conversations
-   [x] Order/product context

> **Closed by Phase 15 (§15.1) Slice v1:** `/seller/messages` renders the shared
> `ConversationInbox` (conversation list + thread + reply + report) against
> `GET /api/v1/seller/conversations/`, which is store-owner scoped
> (`store__user=request.user`). §12.5 "Customer communication" and the Phase 11
> "Contact seller / Contact support" entry points ship in the same slice, so
> nothing was built twice. Remaining messaging items — mute toggles, a staff
> report console, and the §15.3 event hooks beyond orders/messages — are
> tracked in Phase 15.

### 12.7 Store settings

-   [x] Store profile
-   [x] Policies
-   [x] Shipping settings
-   [x] Return settings
-   [x] Store status

> **Slice v1 (done):** `/seller/settings` edits the profile, policies, flat
> shipping fee/free-shipping threshold and return policy through
> `GET/PATCH /api/v1/stores/my/store`. Store status stays platform-owned
> (pending → active is a staff decision, suspension is a staff action), so the
> page surfaces it read-only.

### Gate

-   [x] Seller can operate store end-to-end
-   [x] Seller cannot access another seller's data
-   [x] Seller order workflow works
-   [x] Seller inventory stays synchronized

> **Slice v1 (done):** `backend/tests/test_seller_operations.py` proves the gate
> — dashboard aggregates are scoped to the owning store, cross-store order
> detail is a 404, delete falls back to archive/deactivate when order history
> exists, stock stays append-only, and the customer privacy ladder flips
> exactly at acceptance. Frontend coverage lives in
> `frontend/src/data/seller.test.js`.

**Skills:** marketplace-sellers, marketplace-orders, frontend-feature

------------------------------------------------------------------------

# 15. Phase 13 — Admin, Staff & Platform Operations

## Objective

Build the platform control center.

### 13.1 Staff access

-   [x] Support role
-   [x] Moderator role
-   [x] Finance role
-   [x] Operations role
-   [x] Administrator role
-   [x] Super administrator role
-   [x] Permission assignment
-   [x] Permission audit

> **Slice v1 (done):** the six canonical groups are seeded idempotently
> (`manage.py seed_staff_groups`, `--promote <email> --group <name>`) and the
> permission matrix is written into PROJECT_CONTEXT §4. Support (read-only
> oversight), moderator (application review, store suspension, product
> moderation) and administrator (full operational control) gate real endpoints
> today; finance and operations groups exist but their surfaces (payouts,
> carrier overrides, catalog management) land in later slices — permission
> assignment and role-change auditing follow with them.
>
> **Slice v2 (done):** role administration is live — the administrator-only
> staff directory (`GET /api/v1/auth/admin/staff/`) plus `roles/assign` /
> `roles/remove` run through the accounts services, so every change is
> audit-logged (`staff_group_assigned` / `staff_group_removed`) and visible in
> the audit viewer. Guards: self- and superuser-target changes are refused,
> unknown groups are rejected, no one can remove the marketplace's last
> administrator, and removing a user's final staff group clears `is_staff`.
> Finance/operations surfaces (payouts, carrier overrides, catalog management)
> still land in their own slices.
>
> **Slice v5 (done):** finance and operations now carry real §4 surfaces,
> which completes this section: finance reads payments/refunds and adjusts
> the platform commission rate (13.5/13.6); operations manages taxonomy,
> reads shipments, and reads the settings row (13.4–13.6). Each path is
> group-gated and deny-tested in its slice's gate file.

### 13.2 User management

-   [x] User list
-   [x] User detail
-   [x] Search/filter
-   [x] Account status
-   [x] Account actions

> **Slice v2 (done):** `GET /api/v1/auth/admin/users/` (+ `?q=` / `?status=` /
> `?role=`, `{count, items}` envelope) and the per-id detail serve the
> `/staff/users` console. Support has read-only oversight; suspension and
> reactivation are administrator actions that revoke live sessions immediately
> (a suspended account is locked out mid-session, not at its next login) and
> write `user_suspended` / `user_reactivated` audit rows with their reason.
> Coverage: `backend/tests/test_staff_management.py` + `frontend/src/data/staff.test.js`.

### 13.3 Seller management

-   [x] Seller applications
-   [ ] Verification
-   [x] Approvals
-   [x] Rejections
-   [x] Seller suspension
-   [x] Seller reactivation
-   [ ] Store management

> **Slice v1 (done):** `GET /api/v1/stores/admin/applications/` (+`?status=`,
> `?q=`) and the review endpoint run through the audited moderation service —
> approval flips the store active and the applicant to `is_seller`, rejection
> demands a reason, self-review is refused, and every decision writes an
> AuditLog row. `GET /api/v1/stores/admin/stores/` adds the directory plus the
> suspend/reactivate transitions. The `/staff` console renders the approval
> queue, the store directory and the audit viewer. Store *content* management
> stays seller-owned, so the last item stays open deliberately.

### 13.4 Catalog management

-   [x] Products
-   [x] Categories
-   [x] Brands
-   [x] Moderation
-   [x] Product status

> **Slice v1 (done):** the moderator console (`/staff/catalog`) lists every
> status behind `GET /api/v1/catalog/admin/products/` (q / status / store /
> category filters, `{count, items}` envelope, light rows with store identity
> and counts) and completes the Phase 5 review loop: publish/reject through
> the review endpoint (rejection demands a reason) plus the reason-gated
> staff takedown (`POST .../unpublish`) — the reason is stored on the product
> so the seller sees why it disappeared, and every decision writes an
> AuditLog row. Categories & brands are managed at `/staff/taxonomy` through
> the audited operations/administrator CRUD (`admin/categories`,
> `admin/brands`); cycles, duplicate brands, and non-empty category deletes
> are refused server-side. Group gating follows §4: the product queue moved
> from any-staff to moderator/administrator, taxonomy writes are
> operations/administrator. Coverage: `backend/tests/test_staff_catalog.py`
> + `frontend/src/data/staff.test.js`.

### 13.5 Order/payment operations

-   [x] Order oversight
-   [x] Payment oversight
-   [x] Shipment oversight
-   [x] Refund oversight
-   [x] Return oversight
-   [x] Dispute oversight

> **Slice v4 (done):** the read-only operations console. `/staff/orders`
> lists every order (`GET /api/v1/admin/orders/` — q / status / payment /
> store filters) with the full snapshot at `GET /api/v1/admin/orders/<number>/`
> (customer email, line items, per-store slices), plus parcel oversight
> (`GET /api/v1/admin/shipments/` — q / status / carrier with tracking-event
> counts) and the Phase 11 intake queue (`GET /api/v1/admin/requests/` —
> q / kind / status: the return, refund, and dispute queues). `/staff/payments`
> carries the money view: `GET /api/v1/payments/admin/payments/` (q / status /
> method, refunded totals) and `GET /api/v1/payments/admin/refunds/` (the
> refund trail with the issuing staff member). Every surface is §4
> group-gated (orders/requests: support/finance/operations/administrator,
> shipments: support/operations/administrator, payments/refunds read:
> support/finance/administrator) and nothing mutates state — refund
> *issuance* stays a payments-service action, now tightened to
> finance/administrator. Gate tests: `backend/tests/test_staff_orders.py`;
> accessor coverage in `frontend/src/data/staff.test.js`.

### 13.6 Platform settings

-   [x] Marketplace settings
-   [x] Commission settings
-   [x] Shipping settings
-   [x] Feature settings
-   [x] Notification settings

> **Slice v5 (done):** one audited singleton row (`PlatformSettings`, pinned
> to pk 1) behind `GET/PATCH /api/v1/admin/settings/` and
> `PATCH /api/v1/admin/settings/commission/`. Marketplace identity (name +
> support email; the anonymous subset at `GET /api/v1/platform/public/` feeds
> the storefront footer), a 0–100 commission rate finance or administrator may
> set (§4), shipping defaults that seed every **newly created** store without
> touching existing ones, feature switches — the COD switch makes checkout
> refuse the method with a full rollback (no order, payment, or reservation),
> and the online-payment window now lives in the DB row and drives `expires_at`
> (env only seeds the row's first creation) — and notification defaults applied
> only when a new account's preference row is first created (existing per-user
> rows always win). Reads are administrator/finance/operations; general edits
> are administrator-only; every write lands an `AuditLog` row with a per-field
> from→to diff; DB CheckConstraints back the serializer bounds. Console:
> `/staff/settings`. Gate tests: `backend/tests/test_platform_settings.py`;
> accessor coverage in `frontend/src/data/staff.test.js` + `platform.test.js`.

### 13.7 Audit

-   [x] AuditLog model
-   [x] Sensitive staff actions logged
-   [x] Actor
-   [x] Action
-   [x] Target
-   [x] Timestamp
-   [x] Metadata
-   [x] Audit viewer
-   [x] Audit filtering

> **Slice v1 (done):** the model shipped early (Phase 4) and Slice v1 adds the
> viewer — `GET /api/v1/audit/events/` ({count, items}, group-gated to
> administrator/operations/moderator) with actor / action / object_type /
> object_id filters, rendered at `/staff/audit`.

### Gate

-   [x] Every sensitive admin action is permission-protected
-   [x] Audit records are created
-   [x] Staff cannot exceed assigned permissions
-   [x] Admin cannot accidentally bypass ownership/security rules

> **Slice v5 status:** all four lines are now proven for the whole phase —
> per-group allow/deny paths are tested across every staff surface
> (support, moderator, finance, operations, administrator each hit their
> exact allow and deny routes, settings included), every write goes through
> the domain services (no side doors), each sensitive action lands an
> AuditLog row carrying its change detail, and the ownership/security
> rules are deny-tested end to end in the 13.4–13.6 gate files. The 13.3
> seller-verification item remains open and deliberately out of scope for
> this phase; store *content* management stays seller-owned.

**Skills:** marketplace-admin, security, backend-feature

------------------------------------------------------------------------

# 16. Phase 14 — Reviews, Ratings & Trust

## Objective

Build a trustworthy review ecosystem.

> **Slice v1 (done):** `apps.reviews` ships the whole loop end to end.
> Verified-buyer gate (`services._eligible_item` proves a delivered/
> completed OrderItem — the client never vouches for itself), DB
> `UniqueConstraint(user, product)` + rating `CheckConstraint`, server
> computed `Product.rating_average/rating_count` and
> `Store.rating_average/rating_count` rewritten inside every review
> transaction, photo links (up to 4), owner edits, staff-only moderation
> (hide demands a reason, audit-logged `review_hidden`/`review_restored`,
> restore also clears FLAGGED), abuse reports with a 3-distinct-reporter
> auto-flag threshold and report resolution, one-per-review seller replies
> (own store only), and the eligibility endpoint (`can_review`, `reason`,
> `order_number`, `review_id`) the write form renders from. Frontend:
> `ProductReviews` section on `/product/:slug` (list + eligibility-driven
> write/edit form + report modal), seller reviews desk at `/seller/reviews`,
> staff queue at `/staff/reviews` (group-gated nav), dashboard
> `recent_reviews`, and product/store rating fields in the public shapes.

### 14.1 Product reviews

-   [x] Review model
-   [x] Rating
-   [x] Text review
-   [x] Image attachments
-   [x] Verified purchase
-   [x] One eligible review per purchase/item
-   [x] Review editing rules

### 14.2 Seller ratings

-   [x] Seller rating calculation
-   [x] Seller rating display
-   [x] Rating aggregation

### 14.3 Moderation

-   [x] Report review
-   [x] Review moderation
-   [x] Remove/hide review
-   [x] Seller reply
-   [x] Abuse detection foundation

### Gate

-   [x] Only eligible customers can review
-   [x] Rating aggregation is accurate
-   [x] Moderation works
-   [x] Review abuse is controlled

**Skills:** marketplace-community, security

------------------------------------------------------------------------

# 17. Phase 15 — Messaging & Notifications

## Objective

Build communication between customers, sellers, and JEYVRO support.

### 15.1 Messaging

-   [x] Conversation model
-   [x] Message model
-   [x] Customer ↔ seller
-   [x] Customer ↔ support
-   [x] Order context
-   [x] Product context
-   [x] Read state
-   [ ] Attachments
-   [x] Report conversation
-   [ ] Block/mute where appropriate
-   [ ] Moderation access

> **Slice v1 (done):** `apps/messaging` — `Conversation` (buyer ↔ store seller
> or buyer ↔ support, optional order/product context, plus a per-side mute flag)
> and `Message` (body, system flag, `attachment_url`). `POST /api/v1/conversations/`
> reuses the caller's open thread for the same customer + store/order/product, so
> the product-page and order-page entry points can never duplicate a thread.
> The inbox is `GET /api/v1/conversations/` (buyer),
> `GET /api/v1/seller/conversations/` (store owner),
> `GET /api/v1/conversations/<id>/`, `POST .../messages/`, `POST .../read/` and
> `POST .../report/`; every one re-checks `can_access_conversation` — the buyer,
> the store's owner, or `support` / `moderator` / `administrator` staff.
> Read state is per participant (`customer_last_read_at` /
> `seller_last_read_at` / `support_last_read_at`), unread counts are derived
> server-side and opening a thread marks it read. Reporting writes a
> `ConversationReport`, sets the thread to `reported` and audit-logs it.
> UI: shared `ConversationInbox` (list + thread + reply + report, selection via
> `?id=`) at `/account/messages` and `/seller/messages`, with
> `MessageStoreButton` as the product ("Message store"), order ("Contact
> seller") and support ("Contact support") starter.
> **Still open:** attachment *uploads* (the field exists; storage lands with the
> media phase), mute toggles (the flags exist and already suppress the
> new-message notification, but nothing exposes them yet), and a staff console
> for reported threads (staff can read them; the review screen is Phase 20).

### 15.2 Notifications

-   [x] Notification model
-   [x] In-app notifications
-   [x] Unread count
-   [x] Mark as read
-   [x] Mark all as read
-   [x] Notification categories
-   [x] Notification preferences

> **Slice v1 (done):** `apps/notifications` — `Notification` (category, title,
> message, `action_url`, read flag) and `NotificationPreference` (per-category
> email opt-out, seeded from the platform defaults on first use, edited in the
> account settings panel through `GET`/`PUT /api/v1/notification-preferences`).
> `/api/v1/notifications/` (list, `?unread=1`, `?category=`), `.../unread-count/`,
> `POST .../<id>/read/` and `POST .../read-all/`. The email side respects the
> preference row and sends synchronously (worker tier is §15.4). The navbar bell
> (`NotificationBell`) polls the unread count every 30 s, marks items/all read
> and navigates through `action_url`.

### 15.3 Notification events

-   [ ] Registration
-   [ ] Verification
-   [ ] Seller application
-   [ ] Seller approval/rejection
-   [x] Order placed
-   [ ] Payment confirmed
-   [ ] Order processing
-   [x] Order shipped
-   [x] Order delivered
-   [ ] Return update
-   [ ] Refund update
-   [x] New message
-   [ ] Promotion
-   [ ] Security event

> **Wired so far:** order placed (§8 checkout → `ORDERS`, linking to
> `/orders/<number>`), shipment in transit / out for delivery / delivered (§8.4
> status updates, same link), new message (§15.1 — suppressed when the recipient
> muted the thread) and the seller's reply to a review (§14). Verification,
> password reset and staff suspension already send their own account emails from
> `apps/accounts/services.py`.
> **Next slice:** in-app registration/verification rows, seller application and
> its approval/rejection, payment confirmed and refund updates (the payment
> service already emits audit events at exactly those transitions),
> processing/packed, then return updates with the §11.3 workflow and promotions
> with §16.

### 15.4 Background jobs

-   [ ] Celery/worker architecture
-   [ ] Redis where appropriate
-   [ ] Email delivery jobs
-   [ ] Notification jobs
-   [ ] Retry strategy
-   [ ] Failure handling

> **Deferred (Slice v2):** notification email sends synchronously from
> `notifications.services.create_notification`, and payment expiry runs from the
> `expire_overdue_payments` management command rather than a scheduler. The
> services around them are already transaction-safe and idempotent (a duplicate
> capture or replayed webhook changes nothing), so moving them onto a worker tier
> is a transport change: the seam is the single `create_notification` call site
> plus the existing management commands.

### Gate

-   [x] Messages are permission-scoped
-   [x] Notifications are generated correctly
-   [x] Read state works
-   [ ] Background jobs are retry-safe

> The first three are verified by `tests/test_messaging.py` (participant and
> staff access, deny paths for strangers, unread counts and read-marking) and
> `tests/test_notifications.py` (categories, unread count, per-item and mark-all
> read, email preference gating); the fourth waits on §15.4.

**Skills:** marketplace-community, backend-feature

------------------------------------------------------------------------

# 18. Phase 16 — Promotions, Vouchers & Campaigns

## Objective

Build the marketplace promotion engine.

> **Slice v1 (done):** `apps.promotions` ships the voucher engine end to end.
> `Voucher` — platform/seller scope (a DB constraint guarantees seller
> vouchers carry a store and platform vouchers do not), percentage or fixed
> value with `min_spend`, an optional `max_discount` cap, `usage_limit`,
> `per_user_limit`, `first_order_only`, a start/end window, and funding
> attribution — plus two companions: `VoucherEligibility` (product/category
> targeting rows; no rows means everything in scope) and `VoucherUsage` (the
> append-only redemption ledger, one row per voucher per order).
> `POST /api/v1/vouchers/validate/` judges a code against the caller's live
> cart through the exact service checkout uses, so the preview can never
> disagree with the order. `orders.services.create_order` accepts a
> `voucher_code`, re-evaluates it against the re-validated checkout lines,
> subtracts the server-computed discount from `grand_total` (snapshotted as
> `voucher_code` + `discount_total` on the order), and writes the ledger row
> under a row lock — counters are re-checked there, so a limited code cannot
> be double-spent, the loser of a race rolls back whole, and every discount
> is audit-logged (`voucher.redeemed`). Every rule is DB-constraint backed
> and covered by `backend/tests/test_vouchers.py` + `test_vouchers_race.py`.

> **Slice v2 (done):** the automatic promotion engine behind §16.2 — `Campaign`
> / `Promotion` / `PromotionUsage` judged per line by
> `promotions.services.evaluate_store_lines` (product discount, flash sale,
> bundle threshold, free-shipping waiver), seller-scoped CRUD at
> `/api/v1/seller/promotions/`, and the verdict carried as
> `promotion_discount` on cart, checkout preview and order (netted against the
> voucher's `discount_total` in one `grand_total`). The §16.4 UI lands with it:
> cart promotion labels, checkout voucher entry, order/receipt discount rows and
> the seller promotions desk.

### 16.1 Voucher engine

-   [x] Platform vouchers
-   [x] Seller vouchers
-   [x] Product vouchers
-   [x] Category vouchers
-   [x] Percentage discount
-   [x] Fixed discount
-   [x] Minimum spend
-   [x] Maximum discount
-   [x] Usage limit
-   [x] Per-user limit
-   [x] Start/end date
-   [x] Eligibility rules
-   [x] First-order rules

### 16.2 Promotions

-   [x] Product discounts
-   [x] Flash sale
-   [x] Campaign
-   [x] Free shipping promotion
-   [x] Bundle discount
-   [x] Buy X Get Y architecture

> Discounts are judged by `apps.promotions.services.evaluate_store_lines`
> (per-line entries, campaign windows, targeting rows, quantity thresholds)
> and reach the cart as server numbers: `apps.cart.serializers` exposes a
> per-line `promotion_savings` + `promotion_label`, a store-level
> `promotion_discount`, and the net `items_total`. Checkout waives the shipping
> fee when a `free_shipping` promotion qualifies
> (`promotion_services.find_shipping_waiver`), and
> `orders.services.create_order` snapshots the result as
> `Order.promotion_discount` — already subtracted from `grand_total`, next to
> the voucher's `discount_total`. Covered by `backend/tests/test_promotions.py`
> (auto product discount, flash-sale window, bundle threshold, free-shipping
> waiver, promo+voucher stacking in one order, seller CRUD API) and
> `tests/test_checkout.py::test_checkout_preview_grand_total_is_net_of_auto_promotions`
> (preview parity). Buy X get Y is no longer a declaration: `_apply_bxgy`
> counts the buy product's units across the store slice, and once `buy_qty`
> is met it discounts whole units of the get product at `value`% off, capped
> by `get_qty` *and* by what earlier rules left on that line, so stacking
> still cannot over-discount a line. The pair is DB-constrained (a
> `buy_x_get_y` rule carries both products with positive quantities, no other
> kind may carry either, and the rule is percentage-only) — shipped and
> pinned by four tests in `backend/tests/test_promotions.py` (threshold, cap,
> stacking order, constraints). The seller desk can build the rule for real:
> `PromotionCreateSerializer` takes the buy/get pair, refuses a half-pair, a
> fixed amount, or the pair on any other kind with field errors, and the view
> re-checks that both products belong to the seller's own store (§10.3) before
> writing anything — the same scoping the product/category targets now get,
> so a rival's product id is a 400 rather than a foreign row.

### 16.3 Funding

-   [x] Seller-funded
-   [x] Platform-funded
-   [x] Shared-funded

> **Slice v3 (shipped):** funding is no longer a note in the field —
> `Voucher.funded_by` is now settled **server-side at redemption**.
> `promotions.services.split_funding` is the only implementation: a
> platform-funded discount is the platform's whole cost, a seller-funded one
> is the store's, and a **shared** discount is split **50/50 with the odd cent
> carried by the platform**, so the two shares always re-add to the exact
> discount. `redeem_voucher` writes both shares onto every `VoucherUsage` row
> (`platform_amount` / `seller_amount`) inside the same locked transaction that
> spends the code, and the `voucher.redeemed` audit row records the split
> beside the discount. Two DB constraints back it: a seller- or shared-funded
> voucher must be **store-scoped** (a platform-scope voucher has no store to
> charge, while a store's own code may still be platform-subsidised), and the
> ledger refuses any row whose shares do not balance to the discount.
> **Funding never changes what the customer pays** — the buyer always gets the
> full discount; the split only decides who absorbs it once the order settles,
> and seller payouts/commission reporting consume these shares when that tier
> lands. Rules are in PROJECT_CONTEXT §6 (v1.14); covered by four new tests in
> `backend/tests/test_vouchers.py`.

### 16.4 Promotion UI

-   [ ] Voucher center
-   [x] Product promotion labels
-   [x] Checkout voucher selection
-   [x] Seller promotion management
-   [ ] Admin campaign management

> **Shipped:** the cart renders the engine's own verdict — a promotion chip on
> the line (`frontend/src/components/ui/CartItem.jsx`), a Promotions row and the
> server's net `items_total` in `CartSummary`; checkout takes a code
> (`POST /api/v1/vouchers/validate/` for the inline verdict, then `?voucher_code=`
> on the preview and `voucher_code` on order creation), shows Promotions and
> Voucher rows above the total, and drops a code the server refuses on a later
> re-price instead of displaying a discount that will not exist; order detail and
> the receipt print the promotion + voucher lines from the order snapshot; and
> `/seller/promotions` lists, creates, toggles and deactivates store-wide
> promotions (`frontend/src/routes/seller/SellerPromotions.jsx` over
> `frontend/src/data/promotions.js`, with the NAV entry in `SellerLayout`).
> Checkout preview parity (`build_checkout_preview`) now subtracts
> `promotion_discount` and prices an optional `voucher_code` through the same
> service the order uses, so the summary can never quote a total the order
> undercuts. The wire contracts are pinned by
> `frontend/src/data/promotions.test.js` (voucher verdict + seller CRUD only
> ever send a code or a rule, never an amount) and `frontend/src/data/cart.test.js`
> (`promotion_discount` / `items_total` mapped straight off the engine's numbers).
>
> **Open:** the browse-side voucher center (the public endpoint
> `GET /api/v1/vouchers/` exists, no UI yet) and the staff campaign console.

### Gate

-   [x] Promotion rules calculated server-side
-   [x] Invalid vouchers rejected
-   [x] Voucher usage is race-condition safe
-   [x] Discount calculations are auditable

> Verified by `tests/test_vouchers.py` (server-side verdicts and discount
> math, unknown/expired/inactive/min-spend/targeting/limit rejections with
> their error codes, ledger + audit rows, model CheckConstraints) and
> `tests/test_vouchers_race.py` (two parallel checkouts on a
> one-redemption voucher — exactly one wins, the loser rolls back whole).

**Skills:** marketplace-orders, backend-feature

------------------------------------------------------------------------

# 19. Phase 17 — Returns, Refunds & Disputes

## Objective

Build the complete post-order resolution system.

### 17.1 Returns

-   [x] Return request
-   [x] Return reason
-   [x] Return eligibility
-   [x] Return window
-   [x] Seller response
-   [x] Admin intervention
-   [x] Return shipment
-   [x] Return status

> **Slice v1 (shipped):** `apps/resolutions` turns the Phase 11 intake into an
> adjudicable `ReturnCase`. Eligibility and the return window
> (`RETURNS_WINDOW_DAYS`, default 7) are server verdicts served at
> `GET /api/v1/orders/<number>/return-eligibility`, computed from fulfillment
> snapshots, and the deadline is *snapshotted* onto the case so a later policy
> change can neither reopen nor quietly expire a live case. Filing
> (`POST /api/v1/orders/<number>/returns`) sends only a reason, a note, line
> quantities and an optional intake link — the remaining-quantity cap, the
> duplicate guard, the restock default (damaged/defective lines do not go back
> on the shelf unless the seller says so) and the refund due are all decided
> server-side inside one row-locked transaction. The seller desk
> (`/api/v1/seller/returns/…`) answers approve/reject with a reason, books the
> reverse parcel (`JVRTN-…` tracking minted server-side), and records receipt:
> the only place stock moves, once per line (`restocked_at` is the idempotency
> marker), through the row-locked catalog service so the append-only movement
> history stays the single inventory truth. Whole-order cases (a return
> spanning several stores) are staff-only, and a staff ruling on a case a
> seller already decided is stored as an override with its own timeline event
> and audit row. Every transition writes both a `ReturnEvent` (the
> customer-safe timeline) and an `AuditLog` row, and the linked `OrderRequest`
> becomes `resolved` once the case is decided.
>
> Refund *arithmetic* lands with the case (`refund_due`: line value minus the
> order-level promotion/voucher discounts apportioned to the lines that
> enjoyed them, plus a slice's shipping fee only when that whole slice comes
> back) but **no money moves in this slice** — the payout is §17.2 and
> disputes are §17.3. Covered by `backend/tests/test_returns.py`.

### 17.2 Refunds

-   [x] Full refund
-   [x] Partial refund
-   [x] Refund calculation
-   [x] Refund approval
-   [x] Refund transaction
-   [x] Refund status
-   [x] Payment-provider refund integration point

> **Slice v2 (shipped):** the case *prices* what it owes (slice v1) and
> `apps.payments` *moves* it — the resolution service never touches the
> ledger, it calls `payment_services.refund(payment, amount, …,
> restock=False, return_case=case)`. The new `Refund.restock` flag is what
> keeps the two honest: a manual staff refund still returns the whole order's
> lines to the shelf on settlement (unchanged Phase 9 behaviour), while a
> case-paid refund reverses the ledger without double-restocking what receipt
> already returned, and `Refund.return_case` keeps the money record's lineage
> to the case that authorised it.
>
> `POST /api/v1/admin/returns/<reference>/refund` is the payout, gated to
> **finance/administrator** — the same §4 rule that already restricts manual
> refunds — and it is callable only on a case whose goods were received, so
> money never precedes the parcel. `amount` is optional (defaults to the
> case's remaining balance) and supports partial settlements: the cap is
> re-checked server-side against the case, then against the payment's own
> refundable balance. Pending gateway refunds count as *committed* the moment
> they are requested, so a second payout cannot double-pay while the first is
> in flight.
>
> The case follows its own money through the existing provider seam: COD
> settles synchronously, a hosted gateway stays `pending` until its
> signature-verified webhook confirms, and only then does the case reach
> `refunded` (`on_refund_settled` / `on_refund_failed` → timeline event +
> `AuditLog` row + customer notification). A refused or unconfigured gateway
> rolls the whole payout back — no `Refund` row, no "issued" event, money
> unmoved. Covered by `backend/tests/test_returns.py` (14 gate tests).

### 17.3 Disputes

-   [x] Dispute creation
-   [x] Evidence
-   [x] Customer statement
-   [x] Seller statement
-   [x] Staff review
-   [x] Resolution
-   [x] Resolution reason
-   [x] Audit trail

> **Slice v3 (shipped):** the buyer escalation workflow lives in the same
> `apps/resolutions` app — a `Dispute` (`JVDSP-…`, order- or slice-scoped)
> records the reason and the buyer's opening statement, with optional links
> to the Phase 11 intake it answers *and* the `ReturnCase` it escalates
> (rejecting a return can be contested). Opening
> (`POST /api/v1/orders/<number>/disputes`) is owner-scoped, refuses a
> second open dispute for the same slice, and writes a `DisputeEvent` plus
> an `AuditLog` row and a seller notification. Statements and evidence are
> append-only child rows (`DisputeStatement` / `DisputeEvidence`, URL-based
> like `Message.attachment_url` until the media phase) whose **party is
> derived from the caller** — buyer, store owner or staff — never taken
> from the client; the buyer adds them at `/api/v1/disputes/<ref>/…`, the
> store answers with one statement + optional evidence at
> `/api/v1/seller/disputes/<ref>/respond`, and support leaves notes at
> `/api/v1/admin/disputes/<ref>/statements`. Staff (`support`/`operations`/
> `administrator`, §4) claim a case (`…/review` → `under_review`,
> idempotent) and rule it (`…/resolve` → `buyer_favor`/`seller_favor` with
> a **mandatory reason**), which freezes the record (statements, evidence,
> withdrawal and a second ruling all refused), resolves the linked intake,
> and notifies both sides. The buyer may withdraw their own dispute while
> it is undecided. Every movement writes the timeline row *and* the audit
> row; money never moves here — a buyer win is settled through the §17.2
> payout (finance/administrator). Covered by `backend/tests/test_returns.py`
> (4 dispute gate tests, 18 total).

### Gate

-   [x] Eligible return can be requested
-   [x] Seller/admin can process return
-   [x] Refund state is consistent with payment state
-   [x] Disputes are auditable
-   [x] Unauthorized users cannot alter disputes
-   [x] Backend tests for money flows pass (PROJECT_CONTEXT §11)

**Skills:** marketplace-orders, backend-feature, payments-skill

------------------------------------------------------------------------

# 20. Phase 18 — Search, Recommendations & Marketplace Discovery

## Objective

Create scalable product discovery.

### 18.1 Search

-   [x] Keyword search
-   [x] Search by product
-   [x] Search by store
-   [x] Search by category
-   [x] Autocomplete
-   [x] Search suggestions
-   [x] Typo-tolerance strategy
-   [x] Search filters
-   [x] Search sorting
-   [x] Faceted search

> **Slice v1 (done):** `apps.search` ships the whole §18.1 surface on
> `GET /api/v1/search/` (ranked, filtered, sorted, faceted, paginated) and
> `GET /api/v1/search/suggest/` (autocomplete). Both are public — a shopper
> searches before they have an account — and permission-safe *by construction*:
> one function produces the searchable set (`searchable_products`, published
> products from active stores), so results, facets, and suggestions all share a
> single chokepoint and no non-sellable row is reachable through any of them.
> Ranking is PostgreSQL full-text (`ts_rank` over a weighted `tsvector` — title
> beats description, which beats category/brand, which beats store), not
> insertion order; filters (store, category, brand, price, rating, availability)
> compose, and the shelf
> price used by the price filter and the price sort is the same
> cheapest-active-variant rule the catalog renders, so the two can never
> disagree. Facets are OR-counted — each facet lifts its own filter before
> counting — so selecting one facet never zeroes its siblings. Typo tolerance is
> layered: a `pg_trgm` similarity pass runs *only* when the strict pass returns
> nothing, and when it fires the facet counts are rebuilt from the rescued set.
> Covered by `backend/tests/test_search.py` (36 tests).
> **Slice v1 frontend (done):** `/search` is the results page and the navbar box is
> its entry point — one service backs both, so autocomplete and the full page can
> never disagree on what matches. `src/data/search.js` is the only access point:
> products ride the catalog's own `mapProduct` (a search card and a browse card
> are literally the same shape) and facet rows are flattened into a camelCase
> contract, so no render code touches the API's snake_case. The dropdown reads
> `/suggest/` — prefix matches, *not* ranked results, because a shopper typing
> "bask" needs "Basket" while still mid-word — debounced 250 ms, keyboard
> navigable (ArrowUp/ArrowDown/Escape with one running index across all groups),
> and any failure closes the panel rather than raising an error banner on a
> keystroke; Enter still submits, so a broken suggest endpoint degrades to a plain
> search box. Every piece of discovery state (query, each filter, sort, page)
> lives in the URL, so a narrowed search is shareable and reloadable, and the
> counts beside each filter come from the service's OR-facets — picking a
> category never zeroes its siblings. A keyword search additionally answers with
> the companion "Stores matching" / "Categories matching" strips, and a typo
> rescue is disclosed through `fuzzy` instead of being passed off as an exact
> match. Covered by `frontend/src/data/search.test.js` (7 tests); the frontend
> suite is 16 files / 124 tests, lint and build green.
> Deferred to v2/§18.2: index strategy (GIN/`SearchVectorField`), catalog's
> legacy `?q=` `icontains` path migrating onto this service, and search
> analytics.

### 18.2 Search infrastructure

-   [x] PostgreSQL search foundation
-   [ ] Search indexing strategy
-   [ ] Meilisearch/Elasticsearch abstraction if needed
-   [ ] Index synchronization
-   [ ] Search analytics

> **Slice v1 (done):** the foundation is PostgreSQL's own full-text stack —
> weighted `tsvector`/`ts_rank` computed on the fly, plus the `pg_trgm`
> extension (enabled by `apps/search/migrations/0001_enable_pg_trgm.py`, and a
> *trusted* extension since PG 13 so it needs no superuser) for the typo
> fallback. No external engine is warranted at this scale, and the service layer
> is the seam a Meilisearch/Elasticsearch adapter would replace later.
> **Index strategy is deliberately deferred:** it is measured work, not guessed
> work, and there is no query pattern to measure against yet.

### 18.3 Discovery

-   [x] Trending products
-   [x] Popular products
-   [x] Recently viewed
-   [x] Related products
-   [x] Similar products
-   [x] Personalized recommendations foundation

> **Backend (done):** `GET /api/v1/search/recommendations/` is public and
> permission-safe by the same construction as §18.1 — `?kind=` picks one of
> five rankings and every one of them re-reads through `searchable_products()`,
> so a shelf is never a second, sloppier product pipeline. The kind decides the
> *ranking*, never the *visibility*.
>
> The five kinds deliberately degrade in two different ways. A *ranking*
> (`trending`, `popular`) orders everything, so it falls back to newest when
> there is nothing to rank — a marketplace with three orders still needs a
> homepage. A *neighbourhood* (`related`, `similar`, `personalized`) makes a
> claim about each product it shows, so it returns fewer items rather than padded
> ones: a shelf labelled "related" containing an unrelated product is worse than
> a shelf that is short. `similar` in particular is never topped up, because a
> product sharing no trigram with the seed is not similar to it however good it
> is.
>
> `trending` is units sold inside a 30-day window, `popular` is all-time units,
> and both exclude cancelled/refunded orders via the same `NON_SELLING_STATUSES`
> list `apps.orders` defines — a returned product cannot sit at the top of
> trending. When nothing sold recently every windowed count is `NULL`, and
> trending degrades to popular on its own rather than emptying out.
>
> `personalized` is the whole personalization *foundation*: the shopper's
> history travels with the request as `seen=` and is discarded with it, so it
> works for a signed-out visitor, needs no per-user row to leak or delete, and
> cannot quietly become a tracking system. A seed that no longer resolves is a
> `404` rather than a `500` (it is resolved inside the same validation `try`),
> and a `kind` that needs a subject but was not given one names the missing
> parameter instead of quietly serving the default shelf.
> Covered by `backend/tests/test_recommendations.py` (24 tests).
>
> **Frontend (done):** Home's "Trending products" was a placeholder that sorted
> by discount and called itself trending — now that order data exists it is
> replaced outright by the real ranking, beside a "Best sellers" rail, and a
> "Recommended for you" rail that appears only once the browser has a
> recently-viewed history to rank. The product page keeps "You might also like"
> and gains "Similar finds" beside it, with no card rendered in both.
> `src/data/search.js` is still the only access point, so a shelf card and a
> search card are the same `mapProduct` shape; kinds that would obviously 400
> (`related` with no seed, `personalized` with no history) resolve to an empty
> shelf in the browser rather than a failed request, while a genuine failure
> still surfaces. Covered by `frontend/src/data/search.test.js` (14 tests).
>
> **Deferred:** `recently viewed` stays client-side (no cross-device history),
> and collaborative per-user filtering is deliberately not started — it needs
> the account system this stateless foundation was designed to avoid.

### Gate

-   [x] Search returns relevant products
-   [x] Filters work together
-   [x] Search remains permission-safe
-   [ ] Index synchronization works

**Skills:** marketplace-catalog, performance-skill

------------------------------------------------------------------------

# 21. Phase 19 — Analytics & Reporting

## Objective

Provide useful operational and business intelligence.

### 19.1 Platform analytics

-   [x] Gross merchandise value
-   [x] Orders
-   [x] Revenue
-   [x] Commission
-   [x] Refunds
-   [x] Active customers
-   [x] Active sellers
-   [x] Product activity

> **Backend (done):** `apps.reporting` holds three derived rollup tables
> (`DailyPlatformMetric`, `DailyStoreMetric`, `DailyProductMetric`) and
> `manage.py rebuild_reporting [--from --to]` is their **only** writer — a
> dashboard never queries the transactional tables (§17), and every figure is a
> pure function of the records, so the rebuild is idempotent by construction
> (verified on the real database, not just fixtures: same rows, same primary
> keys, and 28,578.00 GMV reconciling exactly against the non-cancelled
> `grand_total` of the orders it describes).
>
> The definitions are pinned to §6 v1.16 and nothing derives them twice: **GMV**
> is the `grand_total` of orders placed whose status is not cancelled;
> **revenue** is the ledger's capture credits minus its refund debits;
> **commission** is the store slice's merchandise (its own net subtotal, so the
> discounts *that store* funded are the only ones removed, shipping excluded)
> times `PlatformSettings.commission_rate_percent` **as it stood when the money
> was captured** — the applied rate is stored on the row, so a later rate change
> cannot rewrite settled history, and the dev database shows the rule biting:
> 28,578.00 of GMV with nothing captured earns 0.00 of commission, because
> commission follows the ledger and not the badge. Active customers/sellers are
> per-day counts and are exposed as such (`customer_days`/`seller_days`), since
> summing days cannot honestly be called distinct people.
>
> Reads are group-gated per §4 and read-only: `summary`, `stores` and
> `stores/<id>` belong to `finance`/`administrator`; `products` is open to the
> read-only oversight groups too, and the whole matrix was exercised over HTTP
> against the dev host — finance and administrator 200 everywhere, support and
> operations 200 on product activity and 403 on the money three, a signed-in
> customer and an anonymous visitor 403 everywhere, and a reversed, malformed or
> over-long range a 400 rather than a silently clamped answer.
> Covered by `backend/tests/test_reporting.py` (9 tests); the suite that
> contains it is 302 tests, green in 87s.
>
> **Frontend (done):** `/staff/analytics` reads the aggregates through
> `src/data/staff.js` and adds no arithmetic of its own. The link is shown to
> every group that may read *something* on the page, and the page hides the
> money cards rather than the link, so a support operator still gets product
> activity instead of a guaranteed 403.

### 19.2 Seller analytics

-   [x] Sales
-   [x] Orders
-   [x] Revenue
-   [x] Products sold
-   [x] Best-selling products
-   [x] Inventory performance
-   [x] Review metrics
-   [x] Voucher performance

> **Backend (done):** `GET /api/v1/seller/analytics/?from=&to=` serves one
> seller's own period figures from the same rollups staff read: the range
> totals (gross sales, orders, revenue, products sold, commission), the daily
> store series, `top_products(store_id=…)` best sellers, voucher performance
> (`voucher_redemptions` / `voucher_discount` — apportioned across every store
> an order carried, so the parts re-add to the `VoucherUsage` ledger), review
> metrics (published rows only; `review_rating_avg` is **null**, not zero, when
> nothing was reviewed), and the store's stock as a **live snapshot** labeled
> as one. Ownership is resolved from the session (`Store.user ==
> request.user`) — there is no `store_id` parameter to forge, a seller with no
> store gets 404, and everyone else 403 — and the range runs through the same
> `_range` validator (default trailing 30 days, max 366, 400 on a bad range).
> `rebuild` stays idempotent over the new voucher/review columns, and a
> review-only day still earns a zero-money store row. Covered by
> `backend/tests/test_seller_analytics.py` (9 tests); `test_reporting.py` and
> `test_seller_operations.py` stay green alongside it.
>
> **Frontend (done):** `/seller/analytics` (new page + NAV entry in
> `SellerLayout`) reads the aggregates through `src/data/seller.js`
> (`fetchSellerAnalytics`) and adds no arithmetic of its own: headline stat
> cards, the daily series with bars scaled against the busiest day, best
> sellers, voucher/review cards, and the inventory snapshot. Per
> **marketplace-sellers rule 4 the Phase 12 `/seller` dashboard is deliberately
> untouched** — documented deferral: the dashboard keeps its operational view
> and analytics lands beside it as its own page.

### 19.3 Operational analytics

-   [x] Order status metrics
-   [x] Fulfillment metrics
-   [x] Return metrics
-   [x] Refund metrics
-   [x] Support metrics
-   [x] Seller performance

> **Backend (done):** two new rollup tables carry the operational grain —
> `DailyOperationsMetric` (one marketplace day) and `DailyStoreOpsMetric` (one
> store-day) — written by the same `manage.py rebuild_reporting` pass, in the
> same transaction as the money they sit beside, and recomputed from the records
> like every other §19 table. `GET /api/v1/admin/analytics/operations/` serves
> the range totals + daily series; `…/performance/` serves per-store
> operational totals, both group-gated to the read-only oversight groups
> (support / operations / finance / administrator — moderator included in
> neither, §4).
>
> Every definition is pinned because a dashboard must never guess at one:
> **order status** buckets the orders *created that day* by where they stand as
> of the rebuild (`open` = anything not delivered/completed/cancelled/refunded;
> the four buckets always re-add to the day's creations, and `orders_cancelled`
> mirrors the platform row exactly — two derivations, cross-checked);
> **fulfillment** counts parcels created (the seller's ship act — no code path
> writes `Shipment.shipped_at`, so creation is the dispatch signal) and
> `delivered_at`; **returns** count cases filed, and decisions taken by *event
> kind* (approved / rejected / admin override) bucketed by the status the case
> moved to — the kind, because every timeline row records the case's status at
> its moment, so a goods-received row also carries "approved"; **refunds**
> count `Refund` rows issued and, separately, the ledger's refund **debits**
> that settled the money; **support** counts requests, conversations, messages,
> disputes opened and staff rulings (a buyer's withdrawal is not a ruling).
> **Seller performance** attributes only records that name a store slice — a
> whole-order record belongs to the platform grain alone and is never split to
> make a store look busier than it was. Covered by
> `backend/tests/test_operations_analytics.py` (7 gate tests: derivation,
> bucket/partition reconciliation, store attribution, §4 gating, range
> validation, rebuild idempotency, support counts).
>
> **Frontend (done):** `/staff/analytics` grows an **Operations** section (6
> stat cards + the daily operational table) and a **Seller performance** table,
> read through `src/data/staff.js` (`fetchStaffAnalyticsOperations`,
> `fetchStaffAnalyticsPerformance`). The load is role-shaped like the rest of
> the page — a role that may not read operations never fires the request that
> would 403 — and the page renders the server's counts as given, dividing
> nothing itself, so no rate can ever be "roughly right"
> (marketplace-admin rule 5).

### 19.4 Reports

-   [x] Dashboard reports
-   [x] Date filtering
-   [x] Export CSV
-   [ ] Export Excel
-   [ ] Export PDF where appropriate

> **Backend (done):** five reports — `summary`, `stores`, `products`,
> `operations`, `performance` — at
> `GET /api/v1/admin/analytics/export/<report>/?from=&to=`, each answering
> `text/csv` with a `Content-Disposition` filename that names the range
> (`jeyvro-<report>-<start>-<end>.csv`). The body is the CSV rendering of the
> **same serializer output the JSON endpoint serves**, read from the same
> rollups with no limit, so a report cannot show a number the API does not and
> money leaves as the server's exact decimal string — never a float. The gate
> is **part of the route** (`as_view(report=…, required_groups=…)`), not a query
> parameter: the money reports (`summary`, `stores`) are finance/administrator,
> the oversight reports (products, operations, performance) are the read-only
> groups, and moderator/customer/anonymous are refused everywhere (§4). The
> range is validated exactly as the reads are (§8): a reversed, malformed or
> over-long range is a 400, never a silently clamped file. An empty range still
> exports its header (a header-only file is a truthful answer; an empty body
> looks like a broken download), a store name full of commas and quotes is
> quoted per RFC 4180 so it stays one cell, and a range over 5,000 rows is
> refused with `export_too_large` rather than truncated into a file that looks
> complete. Covered by `backend/tests/test_reports_analytics.py` (6 gate tests).
>
> **Frontend (done):** `/staff/analytics` grows an **Export CSV** row of
> download links that follow the page's range and the caller's own gate —
> `staffAnalyticsCsvUrl()` builds the URL and a download is a plain navigation,
> so the session cookie travels with it and the page never assembles a file.
>
> **Deferred (deliberate, not forgotten):** Excel and PDF stay unchecked. Both
> need a new runtime dependency to write honestly (C3), and a mislabelled text
> file pretending to be a spreadsheet is worse than no export — the same pin
> §6 v1.16 recorded when §19.1 chose CSV only. Revisit with the tooling pass.

### Gate

-   [x] Metrics reconcile with transactional data
-   [x] Financial reports are consistent
-   [x] Permissions prevent unauthorized analytics access

> **Gate (passed):** reconciliation is a *mechanism*, not a promise —
> `rebuild_reporting` recomputes every rollup from the records, and the gate
> tests prove it three ways: the §19.1 totals re-add to the order snapshots and
> the ledger, the §19.2 seller day re-adds to the store's own rows (identical to
> the staff drill-down payload), and the §19.3 status buckets **partition** the
> orders created that day while `orders_cancelled` cross-checks the platform
> row — two independent derivations of one day that must agree. Financial
> consistency rides the same derivation (commission at the capture-time rate on
> the store's net merchandise; the export writes the server's exact decimal),
> and access is proven by the §4 matrix on **every** read and export: finance
> and administrator 200 on the money, support and operations 200 on product
> activity / operations / performance and 403 on the money, moderator 403 on the
> money, operations and every export, and a signed-in customer and an anonymous
> visitor 403 everywhere. Suite at the gate: **325 backend tests** and **189
> frontend tests**, lint, build, migration check and `git diff --check` green.

**Skills:** marketplace-admin, performance-skill

------------------------------------------------------------------------

# 22. Phase 20 — Security, Compliance & Abuse Prevention

## Objective

Perform continuous and dedicated security hardening.

### 20.1 Application security

-   [x] Authentication review
-   [x] Authorization review
-   [x] IDOR review
-   [x] CSRF review
-   [x] CORS review
-   [x] XSS review
-   [x] SQL injection review
-   [x] Input validation review
-   [x] File upload review
-   [x] Rate limiting
-   [x] Brute-force protection

> **Finding, fixed (the reason this slice exists):** the public tracking
> endpoint `GET /api/v1/shipments/track/<tracking_number>/` declared **no
> permission class** — it inherited the old project-wide `AllowAny` — and
> returned the full parcel record: **`recipient_name`, `recipient_phone`,
> `shipping_address_text`**, the goods, the shipping fee and the seller's own
> `package_notes`. Anyone holding a tracking number could read who the parcel
> belongs to and where they live, while the order's address sits on a §6 privacy
> ladder and the project refuses even to confirm whether an email exists. A
> tracking number is a **bearer token, not an identity**: the public projection
> (`serialize_tracking_status`) now carries the journey — carrier, status,
> shipped/estimated/delivered, events reduced to `status` + `occurred_at` — and
> nothing else, while the whole record belongs to the order owner, the
> fulfilling seller and staff. A signed-in stranger is redacted rather than
> refused: public tracking is a feature; leaking the buyer through it was the
> bug.
>
> **Deny by default (§10.1):** `DEFAULT_PERMISSION_CLASSES` is
> `IsAuthenticated` and `DEFAULT_AUTHENTICATION_CLASSES` is
> `SessionAuthentication` alone (DRF's default list also enables HTTP Basic,
> which this API never intends). An AST sweep of every view found exactly **two**
> classes relying on the global default — the tracking view above (now explicit)
> and the method-aware review list (already correct) — and the full suite came
> back green, so the flip closed nothing public. The two real gaps it closed:
> a view that forgets to declare permissions is now **private**, and
> `test_security_hardening.py::test_every_view_declares_its_own_permissions`
> walks the URLconf and fails the gate when a new view forgets to speak for
> itself (backend-api rule 6, enforced rather than trusted).
>
> **Rate limiting & brute force (§10.2):** a blunt default (anon + user, env-
> configurable) plus `throttle_scope` buckets on the surfaces worth abusing —
> `auth` (login, verification resend, password reset), `register`, `checkout`,
> `message` — in front of the existing app-level lockout (5 failures → 15
> minutes). Two DRF details were worth knowing and are now proven by tests:
> a `ScopedRateThrottle` only bites when it is in `throttle_classes` (a view
> without `throttle_scope` is a no-op), and DRF binds throttle config at
> **import time**, so the suite lifts throttling by patching the attribute the
> views read (`tests/conftest.py`) instead of the settings dict — no gate
> depends on a wall clock.
>
> **CSRF & CORS (§10.4):** `CORS_ALLOW_CREDENTIALS = True` (it defaulted to
> False, which would have broken every cross-origin session request in
> production while the allowlist still looked correct), explicit
> headers/methods, and both proven by tests: an unlisted origin gets no header,
> a listed one gets it *with* credentials, and an unsafe method on a session
> without the token is refused.
>
> **The gate artifact:** `docs/SECURITY_CHECKLIST.md` records all eleven items
> with a verdict and the file + test that proves each, plus the gaps carried
> forward honestly (production env values and a shared cache for throttling land
> with Phase 23; 20.3 auditing and 20.2 abuse slice v1 have since landed — see
> `docs/AUDIT_COVERAGE.md` and `docs/ABUSE_CONTROLS.md`).
> Covered by `backend/tests/test_security_hardening.py` (11 tests).

### 20.2 Marketplace abuse

-   [x] Spam prevention — *slice v1* (see below)
-   [x] Review abuse prevention — *slice v1*
-   [x] Messaging abuse prevention — *slice v1*
-   [x] Voucher abuse prevention — **already satisfied** before this phase:
        `usage_limit`, `per_user_limit` and `first_order_only` on the voucher,
        an append-only `VoucherUsage` ledger, and a row-locked redemption inside
        `create_order` make it race-safe and audited
        (`voucher.redeemed`). Nothing was added here.
-   [x] Inventory abuse prevention — *slice v2* (the stale-COD reservation, below)
-   [ ] Suspicious order detection foundation — slice v3
-   [ ] Per-order total-units ceiling — slice v3
-   [ ] Account abuse controls — slice v4

> **Slice v1 (done) — spam & messaging.** The slice is built on one decision:
> **the system queues, it does not censor.** An automatic rule never refuses a
> write, never edits text, never deletes anything, and never tells the author
> they were caught; it files one `ContentFlag` row and hands the decision to a
> human. The reason is the false positive — a ruleset that punishes ordinary
> customers is worse than none, so the cost of being wrong is deliberately a
> queue row rather than a deleted review. `apps/moderation` holds the rules
> (pure functions, no DB/network/settings at import), the flag model (one row
> per subject, `CheckConstraint` for exactly one subject, partial unique
> constraints so repeated edits cannot manufacture duplicates) and a staff
> queue where **support may look but only a moderator may act** (§4). Three
> rules fire: a **link** (off-platform advertising; a seller's own storefront
> quoted in a private message is exempt), **contact details** (an email, or a
> phone number *with intent words* — the `JV-20260926-ABCD2345` order number a
> reviewer quotes is deliberately not one), and **shouting** (both a length
> and a ratio floor, so `OK` and `USB-C`/`HDMI` pass). A flagged review is
> parked as `FLAGGED` — not `PUBLISHED`, so it stays out of the rating
> aggregates until a human clears it — while a flagged message is *stored* and
> its thread moved to `reported`, because deleting evidence of abuse would be
> the one unforgivable outcome. Rejection never happens and the author's own
> copy stays readable to them. **Deliberate omissions, each a decision:** no
> profanity or slur list (word blocklists are language-specific and would mute
> ordinary Filipino/Tagalog prose — the rules are *structural*, not lexical),
> no third-party or model-based filtering (an availability dependency that
> ships customer text off-platform), and no automatic permanent penalties (a
> rule that trips puts content in a queue; only a human weighs "this looks
> like spam" against "this person is abusing the platform"). Messaging also
> gained **user blocks** (`ConversationBlock`, user-scoped rather than
> thread-scoped so a new thread on another product is not an escape hatch,
> silent to the blocked party, revocable, audited, and never applicable to
> staff — nobody may block their way out of a dispute) and a `conversation`
> throttle on thread *starts*, which the `message` scope never covered. The
> throttle is **write-only** (`WriteOnlyScopedRateThrottle`): the inbox list
> and the starter are one endpoint, and a 20/hour cap on *reading* would be a
> speed bump on ordinary use (§10.2). `docs/ABUSE_CONTROLS.md` is the coverage
> matrix; `backend/tests/test_abuse_controls.py` (60 tests) drives it, and the
> false-positive guards are asserted as first-class contracts alongside the
> catches. Audit: `content_flagged`, `content_flag_reopened`,
> `content_flag_dismissed`, `content_flag_confirmed`, `conversation_blocked`,
> `conversation_unblocked`.
>
> **Slice v2 (done) — the stale-COD reservation.** The slice was opened by a
> probe, not a hunch: an unpaid cash-on-delivery order held its stock
> reservation **forever**, because `Payment.expires_at` is `None` for COD and
> `expire_overdue_payments` explicitly excludes that method. One abandoned order
> could therefore pin a seller's `available` count down indefinitely. Excluding
> COD from *payment* expiry is **correct and stays** — cash is due at delivery,
> so the payment has no window; the defect was that the reservation was bound to
> that same window. The fix is deliberately a **report, not a reaper**: an unpaid
> COD order may be a real parcel in transit to a slow buyer, and cancelling it
> automatically would be worse than the leak. So `GET /api/v1/admin/stale-cod/`
> and a staff release action (support/operations/administrator) exist, the list
> excludes any order with a parcel **dispatched on any store slice** (releasing
> the stock of a parcel in transit would sell the same unit twice), the release
> **re-checks the stale verdict at the moment of the action** rather than
> trusting the rendered list, it cancels the order together with the stock,
> demands a reason and audits `order.cod_reservation_released`.
> `ORDERS_COD_RESERVATION_REVIEW_DAYS` (default 7) is a review threshold, never a
> cancellation timer. No migration. Suite at this gate: **403 backend tests**.

> **Deferred, not overlooked:** the per-order total-units ceiling
> (`MAX_LINE_QUANTITY = 99` is per *line*, so a 20-line cart is 1,980 units) and
> suspicious-order detection (both slice v3 — they need persistence and a risk
> model, not a content rule), account abuse (slice v4), and audit retention /
> signed export / alerting (Phase 23).

### 20.3 Sensitive operations

-   [x] Financial actions audited
-   [x] Permission changes audited
-   [x] Seller status changes audited
-   [x] Refund actions audited
-   [x] Admin actions audited

> **Slice v1 (done):** `docs/AUDIT_COVERAGE.md` is the coverage matrix — every
> sensitive operation, the exact `action` name it writes, who the actor is, and
> the test that proves it, plus the operations **deliberately not** audited with
> the reason. Three gaps were closed, and the slice was opened by correcting a
> plan: **shipment status transitions were already audited** (`shipment.status_updated`
> ships inside the same atomic block as the status write, so the delivery-triggered
> COD capture commits with the record of the transition) — the one *known* gap was
> the §19.4 CSV exports, and reading the code turned up two more nobody had listed.
>   * **`analytics.exported`** — a CSV is the rare sensitive operation with no
>     domain object to hang itself on (nothing changed; a file went out), so
>     `audit.log_event` now takes an explicit `object_type`/`object_id` and
>     **raises** when it gets neither — a blank-subject row is a trail that
>     proves nothing. Every served export records actor, report, range and the
>     row count the file actually carries; a refused (403) or malformed (400)
>     request writes nothing, because nothing left the building.
>   * **`product_price_changed` / `variant_price_changed`** — a seller's own
>     price edit is money the moment a buyer is asked for it, and it keeps its
>     `from`/`to`. A retitle is not audited: a trail of every copy edit is noise.
>   * **`store_profile_updated`** — `PATCH /stores/my/store` was a bare
>     serializer save, so a seller could change the shipping fee with no record
>     at all. The write moved into `stores.services.update_own_profile`, which
>     keeps the fee's before/after and refuses a seller touching another store
>     (the module's own "transitions live in services, never in views" rule).
>
> No migration: the audit model is unchanged. Covered by
> `backend/tests/test_audit_coverage.py` (7 tests) — including one scenario
> across domains asserting the matrix's action names, so the document cannot
> rot into fiction.

### Gate

-   [ ] Security checklist complete
-   [ ] Permission tests pass
-   [ ] Abuse controls verified — *slices v1/v2 done*; v3/v4 remain
-   [x] Sensitive operations produce audit records

> **Note:** the gate stays open — "security checklist complete" and "permission
> tests pass" are still §20.1 items, and §20.2 is **partly** done: slice v1
> (spam, review and messaging abuse) shipped and is proven by
> `docs/ABUSE_CONTROLS.md` + `tests/test_abuse_controls.py`, and **slice v2**
> (the stale-COD reservation) shipped in `79aa255`, while **slices v3/v4**
> (suspicious orders, the per-order quantity ceiling, account abuse) remain
> — "abuse controls verified" cannot be ticked until they do. Audit
> **retention, export and alerting** are honestly deferred to the deployment
> phase (Phase 23), as are production env values and a shared cache for
> throttling.

**Skills:** security, backend-feature

------------------------------------------------------------------------

# 23. Phase 21 — Testing & Quality Assurance

## Objective

Verify the entire marketplace, not only individual pages.

### 21.1 Backend tests

-   [ ] Model tests
-   [ ] Serializer tests
-   [ ] API tests
-   [ ] Permission tests
-   [ ] Authentication tests
-   [ ] Inventory tests
-   [ ] Cart tests
-   [ ] Checkout tests
-   [ ] Payment tests
-   [ ] Order tests
-   [ ] Shipping tests
-   [ ] Return tests
-   [ ] Refund tests
-   [ ] Promotion tests
-   [ ] Finance tests

### 21.2 Frontend tests

-   [ ] Component tests
-   [ ] Form tests
-   [ ] Route tests
-   [ ] State tests
-   [ ] API integration tests
-   [ ] Loading states
-   [ ] Error states
-   [ ] Empty states

### 21.3 E2E tests

#### Customer journey

-   [ ] Register
-   [ ] Login
-   [ ] Browse
-   [ ] Search
-   [ ] Product
-   [ ] Add to cart
-   [ ] Checkout
-   [ ] Payment
-   [ ] Order
-   [ ] Tracking
-   [ ] Delivery
-   [ ] Review

#### Seller journey

-   [ ] Apply
-   [ ] Approval
-   [ ] Store setup
-   [ ] Product creation
-   [ ] Inventory
-   [ ] Receive order
-   [ ] Fulfill
-   [ ] Ship
-   [ ] Message customer
-   [ ] Handle return
-   [ ] View earnings

#### Admin journey

-   [ ] Login
-   [ ] Review seller
-   [ ] Manage catalog
-   [ ] Manage orders
-   [ ] Review payment
-   [ ] Process refund
-   [ ] Moderate review
-   [ ] Manage disputes
-   [ ] Review analytics
-   [ ] Inspect audit logs

### 21.4 Regression

-   [ ] Full regression suite
-   [ ] Critical money-path regression
-   [ ] Permission regression
-   [ ] Mobile regression

### Gate

-   [ ] Automated tests pass
-   [ ] Critical E2E flows pass
-   [ ] No unresolved critical regression

**Skills:** testing

------------------------------------------------------------------------

# 24. Phase 22 — Performance & Scalability

## Objective

Make JEYVRO reliable as data and traffic increase.

### 22.1 Database

-   [ ] Index review
-   [ ] Query optimization
-   [ ] N+1 query review
-   [ ] `select_related` review
-   [ ] `prefetch_related` review
-   [ ] Transaction review
-   [ ] Slow-query review

### 22.2 API

-   [ ] Pagination
-   [ ] Response optimization
-   [ ] Caching
-   [ ] Rate limiting
-   [ ] Query limits
-   [ ] Bulk operation review

### 22.3 Frontend

-   [ ] Bundle optimization
-   [ ] Lazy loading
-   [ ] Image optimization
-   [ ] Route-level loading
-   [ ] API caching where appropriate

### 22.4 Infrastructure

-   [ ] Background jobs
-   [ ] CDN
-   [ ] Object storage
-   [ ] Database backup strategy
-   [ ] Monitoring
-   [ ] Load testing

### Gate

-   [ ] Performance baseline documented
-   [ ] Critical pages meet target performance
-   [ ] Critical APIs optimized
-   [ ] Load test results reviewed

**Skills:** performance-skill, backend-core, frontend-performance

------------------------------------------------------------------------

# 25. Phase 23 — Deployment & Production Infrastructure

## Objective

Deploy JEYVRO safely and reproducibly.

### 23.1 Production

-   [ ] Production Django settings
-   [ ] Production React build
-   [ ] PostgreSQL production
-   [ ] Environment variables
-   [ ] Secret management
-   [ ] Static files
-   [ ] Media storage
-   [ ] Object storage
-   [ ] CDN
-   [ ] HTTPS
-   [ ] Domain

### 23.2 Deployment

-   [ ] Docker
-   [ ] Deployment configuration
-   [ ] Database migrations
-   [ ] Migration safety process
-   [ ] CI/CD
-   [ ] Staging environment
-   [ ] Production environment
-   [ ] Rollback strategy

### 23.3 Operations

-   [ ] Application logging
-   [ ] Error tracking
-   [ ] Health checks
-   [ ] Uptime monitoring
-   [ ] Database backups
-   [ ] Backup verification
-   [ ] Recovery procedure
-   [ ] Incident procedure

### 23.4 Documentation

-   [ ] README
-   [ ] Local setup guide
-   [ ] API documentation
-   [ ] Environment variable guide
-   [ ] Deployment guide
-   [ ] Database/migration guide
-   [ ] Troubleshooting guide
-   [ ] Architecture documentation

### Gate

-   [ ] Staging deployment works
-   [ ] Production deployment works
-   [ ] HTTPS works
-   [ ] Database backup verified
-   [ ] Rollback procedure tested
-   [ ] Monitoring works

**Skills:** deployment, security

------------------------------------------------------------------------

# 26. Phase 24 — AI & Advanced Marketplace Features

## Objective

Add AI only after the transactional marketplace is stable.

### 24.1 Customer AI

-   [ ] AI shopping assistant
-   [ ] Product discovery assistance
-   [ ] Natural-language product search
-   [ ] Product comparison assistance
-   [ ] Customer support assistance

### 24.2 Seller AI

-   [ ] Product title suggestions
-   [ ] Product description generation
-   [ ] Category suggestions
-   [ ] Attribute suggestions
-   [ ] Seller support assistant

### 24.3 Recommendation systems

-   [ ] Related-product recommendations
-   [ ] Personalized recommendations
-   [ ] Behavioral recommendations
-   [ ] Recommendation evaluation

### 24.4 AI safety

-   [ ] Prevent fabricated product data
-   [ ] Ground AI responses in JEYVRO data
-   [ ] Permission-aware AI access
-   [ ] Rate limits
-   [ ] AI logging
-   [ ] AI failure handling
-   [ ] Human escalation path

### Gate

-   [ ] AI features do not control authoritative transactions
-   [ ] AI cannot bypass permissions
-   [ ] AI responses are grounded in platform data
-   [ ] AI failures do not break core shopping flows

**Skills:** security, frontend-feature, marketplace-catalog

------------------------------------------------------------------------

# 27. Phase 25 — Final Production Audit

## Objective

Verify JEYVRO as a complete system from every actor's perspective.

### 25.1 Customer complete journey

-   [ ] Register
-   [ ] Verify account
-   [ ] Login
-   [ ] Manage profile
-   [ ] Manage addresses
-   [ ] Browse
-   [ ] Search
-   [ ] Filter
-   [ ] View product
-   [ ] Select variant
-   [ ] Wishlist
-   [ ] Add to cart
-   [ ] Apply voucher
-   [ ] Checkout
-   [ ] Select shipping
-   [ ] Pay
-   [ ] Receive order
-   [ ] Track shipment
-   [ ] Cancel eligible order
-   [ ] Request return
-   [ ] Request refund
-   [ ] Open dispute
-   [ ] Message seller
-   [ ] Contact support
-   [ ] Review product
-   [ ] Manage notifications
-   [ ] View receipt

### 25.2 Seller complete journey

-   [ ] Register
-   [ ] Apply as seller
-   [ ] Submit verification
-   [ ] Receive approval
-   [ ] Configure store
-   [ ] Create products
-   [ ] Add variants
-   [ ] Upload images
-   [ ] Manage inventory
-   [ ] Receive order
-   [ ] Process order
-   [ ] Pack
-   [ ] Ship
-   [ ] Track fulfillment
-   [ ] Message buyer
-   [ ] Respond to review
-   [ ] Handle return
-   [ ] Handle dispute
-   [ ] Create vouchers
-   [ ] Run promotions
-   [ ] View analytics
-   [ ] View commissions
-   [ ] View payouts

### 25.3 Staff/Admin complete journey

-   [ ] Login
-   [ ] Manage users
-   [ ] Review seller applications
-   [ ] Manage sellers
-   [ ] Manage stores
-   [ ] Manage categories
-   [ ] Moderate products
-   [ ] Oversee orders
-   [ ] Oversee payments
-   [ ] Manage refunds
-   [ ] Manage returns
-   [ ] Manage disputes
-   [ ] Moderate reviews
-   [ ] Manage promotions
-   [ ] Manage vouchers
-   [ ] Manage commissions
-   [ ] Record/process payouts
-   [ ] View analytics
-   [ ] View reports
-   [ ] Manage notifications
-   [ ] Manage staff permissions
-   [ ] Review audit logs
-   [ ] Manage platform settings

### 25.4 Engineering verification

-   [ ] Frontend lint passes
-   [ ] Frontend build passes
-   [ ] Backend checks pass
-   [ ] Database migrations are clean
-   [ ] Automated tests pass
-   [ ] E2E tests pass
-   [ ] Security review passes
-   [ ] Permission review passes
-   [ ] Performance review passes
-   [ ] Accessibility review passes
-   [ ] Responsive review passes
-   [ ] Production deployment verified
-   [ ] Backup verified
-   [ ] Monitoring verified
-   [ ] Documentation complete

------------------------------------------------------------------------

# 28. Build Milestones & v1.0 Boundary

The phases are the full journey; these milestones are the points where the product becomes genuinely usable and shippable.

- **M1 — First sellable version (end of Phase 10):** a customer can register, browse, fill a cart, check out with COD, and track the order end-to-end. First version worth demoing.
- **M2 — Sellers can operate (end of Phase 12):** sellers onboard, list products with variants/images, manage inventory, process orders, and message buyers *(the messaging leg ships with Phase 15 §15.1 — §12.6 is a documented deferral, not a Phase 12 gap)*.
- **M3 — Platform is governable (end of Phase 13):** staff manage users/stores/catalog, oversee orders and payments, record payouts, and sensitive actions are audit-logged.
- **v1.0 — Production launch (end of Phase 23 + Phase 25 audit):** deployed, secured, monitored, backed up; the Phase 25 audit passes in full.
- **Post-v1.0:** Phase 24 (AI & advanced features) and any deferred scale work. Phase 24 never blocks the Definition of Done.

A milestone never skips a phase gate; the Definition of Done and the Completion Rule always outrank milestones.

--------

# 29. Cross-Phase Non-Negotiable Rules

These rules apply to every phase.

## Security

-   Never trust client-provided prices.
-   Never trust client-provided totals.
-   Never trust client-provided permissions.
-   Never trust client-provided inventory.
-   Never expose another user's private data.
-   Never allow seller access outside their own store.
-   Never allow customer access outside their own orders.
-   Never allow staff to exceed assigned permissions.
-   Validate all uploaded files.
-   Protect sensitive operations with authorization and audit logging.

## Money

All monetary calculations must be server-side.

Use appropriate decimal/money handling.

Never use floating-point arithmetic for authoritative monetary values.

Financial state changes must be transactional and auditable.

## Inventory

Inventory changes must be concurrency-safe.

Use database transactions and row locking where appropriate.

Never allow checkout to bypass stock validation.

## Orders

Orders must preserve immutable snapshots of relevant purchase data.

Product changes after purchase must not rewrite historical order
information.

## APIs

Use versioned APIs.

Keep response formats consistent.

Validate input.

Return predictable error structures.

## Frontend

The frontend must never become the source of truth for business rules.

Use reusable components.

Handle:

``` text
Loading
Success
Empty
Error
Unauthorized
Forbidden
```

## UI/UX

-   Responsive
-   Accessible
-   Consistent
-   Professional
-   No unnecessary visual effects
-   No gradients unless explicitly approved by the project design system
-   No excessive shadows
-   No random one-off component styles
-   Preserve the JEYVRO design system

## AI Development

AI agents must:

1.  Read project context.
2.  Read the roadmap.
3.  Inspect existing code.
4.  Identify dependencies.
5.  Plan before modifying.
6.  Make the smallest appropriate change.
7.  Run verification.
8.  Report exactly what changed.
9.  Never mark unchecked work as complete.
10. Never silently rewrite unrelated code.

------------------------------------------------------------------------

# 30. Definition of Done — JEYVRO

JEYVRO is considered **industry-complete** only when the system supports
the complete marketplace lifecycle:

``` text
CUSTOMER
Account
→ Discovery
→ Product
→ Cart
→ Checkout
→ Payment
→ Order
→ Shipment
→ Delivery
→ Review
→ Return/Refund/Dispute when applicable
```

``` text
SELLER
Application
→ Verification
→ Store
→ Catalog
→ Inventory
→ Orders
→ Fulfillment
→ Shipping
→ Reviews
→ Messaging
→ Promotions
→ Returns/Disputes
→ Analytics
→ Finance
→ Payouts
```

``` text
PLATFORM
Users
→ Sellers
→ Catalog
→ Orders
→ Payments
→ Shipping
→ Returns
→ Refunds
→ Disputes
→ Reviews
→ Promotions
→ Finance
→ Analytics
→ Moderation
→ Audit
→ Security
→ Settings
```

And the engineering system must be:

``` text
Secure
Tested
Responsive
Accessible
Performant
Observable
Documented
Deployable
Recoverable
Maintainable
```

------------------------------------------------------------------------

# 31. Roadmap Completion Rule

The roadmap is not complete because every checkbox is checked.

It is complete only when:

1.  The complete customer lifecycle works.
2.  The complete seller lifecycle works.
3.  The complete platform/admin lifecycle works.
4.  Financial transactions are authoritative and auditable.
5.  Inventory is concurrency-safe.
6.  Permissions are enforced server-side.
7.  Critical workflows have automated tests.
8.  Production deployment is reproducible.
9.  Backups and recovery have been verified.
10. Security, performance, accessibility, and responsive reviews have
    passed.
11. Documentation reflects the actual implementation.
12. No critical known gap remains undocumented.

------------------------------------------------------------------------

# 32. Final Roadmap Order

``` text
0.  Product & System Foundation
1.  Repository & Development Infrastructure
2.  Backend Foundation & Database
3.  Authentication, Users & Access Control
4.  Seller & Store Foundation
5.  Catalog, Products & Inventory
6.  Customer Shopping & Discovery
7.  Cart & Wishlist
8.  Checkout, Shipping Calculation & Order Creation
9.  Payments & Financial Transactions
10. Order Fulfillment & Delivery
11. Customer Account & Order Management
12. Seller Operations & Seller Dashboard
13. Admin, Staff & Platform Operations
14. Reviews, Ratings & Trust
15. Messaging & Notifications
16. Promotions, Vouchers & Campaigns
17. Returns, Refunds & Disputes
18. Search, Recommendations & Marketplace Discovery
19. Analytics & Reporting
20. Security, Compliance & Abuse Prevention
21. Testing & Quality Assurance
22. Performance & Scalability
23. Deployment & Production Infrastructure
24. AI & Advanced Marketplace Features
25. Final Production Audit
```

**This is the master build order. Do not skip ahead simply because a
later feature is visually easier.**
