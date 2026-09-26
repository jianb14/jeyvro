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
| 13 | Admin, Staff & Platform Operations | 🔄 In progress — Slice v1: seeded staff groups, seller approvals, store oversight, audit viewer. Slice v2: staff directory + audited role assignment (self/superuser/last-admin guards) and user management with session-revoking suspension. Slice v3: moderator catalog console (publish/reject + reason-gated takedown) and audited operations/administrator category & brand management. Slice v4: read-only order/payment operations console (order & shipment oversight, return/refund/dispute intake, payment/refund trail) with refund issuance tightened to finance/administrator. Remaining: platform settings (13.6), finance/operations surfaces |
| 14 | Reviews, Ratings & Trust | ⬜ Not started |
| 15 | Messaging & Notifications | ⬜ Not started |
| 16 | Promotions, Vouchers & Campaigns | ⬜ Not started |
| 17 | Returns, Refunds & Disputes | ⬜ Not started |
| 18 | Search, Recommendations & Discovery | ⬜ Not started |
| 19 | Analytics & Reporting | ⬜ Not started |
| 20 | Security, Compliance & Abuse Prevention | ⬜ Not started |
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

> **Single source of truth (PROJECT_CONTEXT §18):** the rules and lifecycles this phase defines must be written into `PROJECT_CONTEXT.md` — never into this roadmap; this file only references them. Known gaps PROJECT_CONTEXT does not yet cover: commission rules, voucher rules, and returns/refunds/disputes rules (seller registration/verification and store rules landed in PROJECT_CONTEXT v1.2). Add the remaining ones to PROJECT_CONTEXT first, then check the boxes below.

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
-   [ ] Voucher rules
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
-   [ ] Contact seller — arrives with Phase 15 (Messaging & Notifications)
-   [ ] Contact support — arrives with Phase 15 (Messaging & Notifications)

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

-   [ ] Conversation list
-   [ ] Chat view
-   [ ] Buyer ↔ seller conversations
-   [ ] Order/product context

> **Deferred to Phase 15 (§15.1):** messaging ships as one system — the
> Conversation/Message models, customer ↔ seller *and* customer ↔ support,
> read state, attachments and moderation access. Phase 11 already surfaces the
> "Contact seller — arrives with Phase 15" entry points and §12.5 "Customer
> communication" closes with the same slice, so nothing is built twice.

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
-   [ ] Finance role
-   [ ] Operations role
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

-   [ ] Marketplace settings
-   [ ] Commission settings
-   [ ] Shipping settings
-   [ ] Feature settings
-   [ ] Notification settings

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
-   [ ] Admin cannot accidentally bypass ownership/security rules

> **Slice v1 status:** the four gate lines are proven for everything shipped so
> far — per-group allow/deny paths are tested (`support` reads but cannot act,
> `moderator` reviews and suspends, `administrator` sees the audit log), every
> write goes through the domain services (no side doors), and each sensitive
> action lands an AuditLog row. The last line stays open until the remaining
> staff surfaces (finance, operations, catalog, settings) exist and carry the
> same tests.

**Skills:** marketplace-admin, security, backend-feature

------------------------------------------------------------------------

# 16. Phase 14 — Reviews, Ratings & Trust

## Objective

Build a trustworthy review ecosystem.

### 14.1 Product reviews

-   [ ] Review model
-   [ ] Rating
-   [ ] Text review
-   [ ] Image attachments
-   [ ] Verified purchase
-   [ ] One eligible review per purchase/item
-   [ ] Review editing rules

### 14.2 Seller ratings

-   [ ] Seller rating calculation
-   [ ] Seller rating display
-   [ ] Rating aggregation

### 14.3 Moderation

-   [ ] Report review
-   [ ] Review moderation
-   [ ] Remove/hide review
-   [ ] Seller reply
-   [ ] Abuse detection foundation

### Gate

-   [ ] Only eligible customers can review
-   [ ] Rating aggregation is accurate
-   [ ] Moderation works
-   [ ] Review abuse is controlled

**Skills:** marketplace-community, security

------------------------------------------------------------------------

# 17. Phase 15 — Messaging & Notifications

## Objective

Build communication between customers, sellers, and JEYVRO support.

### 15.1 Messaging

-   [ ] Conversation model
-   [ ] Message model
-   [ ] Customer ↔ seller
-   [ ] Customer ↔ support
-   [ ] Order context
-   [ ] Product context
-   [ ] Read state
-   [ ] Attachments
-   [ ] Report conversation
-   [ ] Block/mute where appropriate
-   [ ] Moderation access

### 15.2 Notifications

-   [ ] Notification model
-   [ ] In-app notifications
-   [ ] Unread count
-   [ ] Mark as read
-   [ ] Mark all as read
-   [ ] Notification categories
-   [ ] Notification preferences

### 15.3 Notification events

-   [ ] Registration
-   [ ] Verification
-   [ ] Seller application
-   [ ] Seller approval/rejection
-   [ ] Order placed
-   [ ] Payment confirmed
-   [ ] Order processing
-   [ ] Order shipped
-   [ ] Order delivered
-   [ ] Return update
-   [ ] Refund update
-   [ ] New message
-   [ ] Promotion
-   [ ] Security event

### 15.4 Background jobs

-   [ ] Celery/worker architecture
-   [ ] Redis where appropriate
-   [ ] Email delivery jobs
-   [ ] Notification jobs
-   [ ] Retry strategy
-   [ ] Failure handling

### Gate

-   [ ] Messages are permission-scoped
-   [ ] Notifications are generated correctly
-   [ ] Read state works
-   [ ] Background jobs are retry-safe

**Skills:** marketplace-community, backend-feature

------------------------------------------------------------------------

# 18. Phase 16 — Promotions, Vouchers & Campaigns

## Objective

Build the marketplace promotion engine.

### 16.1 Voucher engine

-   [ ] Platform vouchers
-   [ ] Seller vouchers
-   [ ] Product vouchers
-   [ ] Category vouchers
-   [ ] Percentage discount
-   [ ] Fixed discount
-   [ ] Minimum spend
-   [ ] Maximum discount
-   [ ] Usage limit
-   [ ] Per-user limit
-   [ ] Start/end date
-   [ ] Eligibility rules
-   [ ] First-order rules

### 16.2 Promotions

-   [ ] Product discounts
-   [ ] Flash sale
-   [ ] Campaign
-   [ ] Free shipping promotion
-   [ ] Bundle discount
-   [ ] Buy X Get Y architecture

### 16.3 Funding

-   [ ] Seller-funded
-   [ ] Platform-funded
-   [ ] Shared-funded

### 16.4 Promotion UI

-   [ ] Voucher center
-   [ ] Product promotion labels
-   [ ] Checkout voucher selection
-   [ ] Seller promotion management
-   [ ] Admin campaign management

### Gate

-   [ ] Promotion rules calculated server-side
-   [ ] Invalid vouchers rejected
-   [ ] Voucher usage is race-condition safe
-   [ ] Discount calculations are auditable

**Skills:** marketplace-orders, backend-feature

------------------------------------------------------------------------

# 19. Phase 17 — Returns, Refunds & Disputes

## Objective

Build the complete post-order resolution system.

### 17.1 Returns

-   [ ] Return request
-   [ ] Return reason
-   [ ] Return eligibility
-   [ ] Return window
-   [ ] Seller response
-   [ ] Admin intervention
-   [ ] Return shipment
-   [ ] Return status

### 17.2 Refunds

-   [ ] Full refund
-   [ ] Partial refund
-   [ ] Refund calculation
-   [ ] Refund approval
-   [ ] Refund transaction
-   [ ] Refund status
-   [ ] Payment-provider refund integration point

### 17.3 Disputes

-   [ ] Dispute creation
-   [ ] Evidence
-   [ ] Customer statement
-   [ ] Seller statement
-   [ ] Staff review
-   [ ] Resolution
-   [ ] Resolution reason
-   [ ] Audit trail

### Gate

-   [ ] Eligible return can be requested
-   [ ] Seller/admin can process return
-   [ ] Refund state is consistent with payment state
-   [ ] Disputes are auditable
-   [ ] Unauthorized users cannot alter disputes
-   [ ] Backend tests for money flows pass (PROJECT_CONTEXT §11)

**Skills:** marketplace-orders, backend-feature, payments-skill

------------------------------------------------------------------------

# 20. Phase 18 — Search, Recommendations & Marketplace Discovery

## Objective

Create scalable product discovery.

### 18.1 Search

-   [ ] Keyword search
-   [ ] Search by product
-   [ ] Search by store
-   [ ] Search by category
-   [ ] Autocomplete
-   [ ] Search suggestions
-   [ ] Typo-tolerance strategy
-   [ ] Search filters
-   [ ] Search sorting
-   [ ] Faceted search

### 18.2 Search infrastructure

-   [ ] PostgreSQL search foundation
-   [ ] Search indexing strategy
-   [ ] Meilisearch/Elasticsearch abstraction if needed
-   [ ] Index synchronization
-   [ ] Search analytics

### 18.3 Discovery

-   [ ] Trending products
-   [ ] Popular products
-   [ ] Recently viewed
-   [ ] Related products
-   [ ] Similar products
-   [ ] Personalized recommendations foundation

### Gate

-   [ ] Search returns relevant products
-   [ ] Filters work together
-   [ ] Search remains permission-safe
-   [ ] Index synchronization works

**Skills:** marketplace-catalog, performance-skill

------------------------------------------------------------------------

# 21. Phase 19 — Analytics & Reporting

## Objective

Provide useful operational and business intelligence.

### 19.1 Platform analytics

-   [ ] Gross merchandise value
-   [ ] Orders
-   [ ] Revenue
-   [ ] Commission
-   [ ] Refunds
-   [ ] Active customers
-   [ ] Active sellers
-   [ ] Product activity

### 19.2 Seller analytics

-   [ ] Sales
-   [ ] Orders
-   [ ] Revenue
-   [ ] Products sold
-   [ ] Best-selling products
-   [ ] Inventory performance
-   [ ] Review metrics
-   [ ] Voucher performance

### 19.3 Operational analytics

-   [ ] Order status metrics
-   [ ] Fulfillment metrics
-   [ ] Return metrics
-   [ ] Refund metrics
-   [ ] Support metrics
-   [ ] Seller performance

### 19.4 Reports

-   [ ] Dashboard reports
-   [ ] Date filtering
-   [ ] Export CSV
-   [ ] Export Excel
-   [ ] Export PDF where appropriate

### Gate

-   [ ] Metrics reconcile with transactional data
-   [ ] Financial reports are consistent
-   [ ] Permissions prevent unauthorized analytics access

**Skills:** marketplace-admin, performance-skill

------------------------------------------------------------------------

# 22. Phase 20 — Security, Compliance & Abuse Prevention

## Objective

Perform continuous and dedicated security hardening.

### 20.1 Application security

-   [ ] Authentication review
-   [ ] Authorization review
-   [ ] IDOR review
-   [ ] CSRF review
-   [ ] CORS review
-   [ ] XSS review
-   [ ] SQL injection review
-   [ ] Input validation review
-   [ ] File upload review
-   [ ] Rate limiting
-   [ ] Brute-force protection

### 20.2 Marketplace abuse

-   [ ] Spam prevention
-   [ ] Review abuse prevention
-   [ ] Messaging abuse prevention
-   [ ] Voucher abuse prevention
-   [ ] Inventory abuse prevention
-   [ ] Suspicious order detection foundation
-   [ ] Account abuse controls

### 20.3 Sensitive operations

-   [ ] Financial actions audited
-   [ ] Permission changes audited
-   [ ] Seller status changes audited
-   [ ] Refund actions audited
-   [ ] Admin actions audited

### Gate

-   [ ] Security checklist complete
-   [ ] Permission tests pass
-   [ ] Abuse controls verified
-   [ ] Sensitive operations produce audit records

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
