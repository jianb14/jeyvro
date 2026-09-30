# JEYVRO — Project Context (Single Source of Truth)

> Version 1.17 · v1.17 changelog: §6 seller analytics slice (Phase 19.2) — `GET /api/v1/seller/analytics/?from=&to=` now serves one store's period figures (gross sales, orders, revenue, products sold, best sellers, voucher performance reconciled to the `VoucherUsage` ledger, published-review metrics) from the reporting aggregates at the store grain, with **ownership** resolved from the session instead of a group (no `store_id` parameter to forge; a seller without a store gets 404, everyone else 403) and the stock served as a **live snapshot** labeled as one; a review-only day earns a zero-money `DailyStoreMetric` row so the rollups never miss a day the records support, and the Phase 12 `/seller` dashboard stays untouched per marketplace-sellers rule 4 (documented deferral — the new page is `/seller/analytics`).
> Version 1.16 · v1.16 changelog: §6 analytics & reporting rules added (Phase 19 slices v0–v1) — every number a dashboard shows is now served from a **reporting aggregate** the rebuild command derives from the transactional records and can recompute on demand, so "the metrics reconcile" is checkable instead of asserted; the definitions are pinned (GMV, revenue, and commission — the store slice's merchandise net of the discounts that store itself funded, shipping excluded, at the rate in force when the money was **captured**), access is group-gated with finance owning the financial figures and a store seeing only its own, and exports are CSV only — Excel and PDF stay deliberately unbuilt rather than faked, because both would need a new runtime dependency (C3).
> Version 1.15 · v1.15 changelog: §6 returns, refunds & disputes rules added (Phase 17 slices v1–v3) — the adjudicable `ReturnCase` (server-verified eligibility, window snapshotted at filing, per-line quantity caps, seller response with staff override, reverse parcel, and receipt-time line-scoped restock through the append-only stock ledger), the payout that never precedes the parcel (finance/administrator only, goods-received gated, capped against the case then the payment, the case following its own refund through the provider seam), and the `Dispute` escalation whose statements/evidence take their party from the caller and whose staff ruling demands a reason and freezes the record.
> Version 1.14 · v1.14 changelog: §6 automatic promotion engine and discount funding rules added (Phase 16.2–16.3) — one per-line engine judges every live campaign rule (product discount, flash sale, bundle floor, free-shipping waiver, buy-X-get-Y) identically at the cart, preview, voucher and checkout choke points; and funding: every discount names its funder (platform / store / both), settled **server-side at redemption** as `platform_amount` + `seller_amount` that always re-add to the discount (shared = 50/50, the odd cent to the platform), DB-constrained, and never changing what the customer pays.
> Version 1.13 · v1.13 changelog: §6 platform-settings rules added (Phase 13.6) — the marketplace's configuration is one audited singleton row: administrator-written (finance may set the commission rate), DB-constraint-backed bounds, shipping defaults that seed new stores only, a COD switch checkout obeys with full rollback, a platform-owned payment-expiry window, and new-account notification defaults that never overwrite existing preferences; the public subset (name + support contact) serves the storefront chrome.
> Version 1.12 · v1.12 changelog: §4 order/payment operations added (Phase 13.5) — the read-only staff oversight console: orders (list + full snapshot), shipments/parcels, and the return/refund/dispute request intake are group-gated and server-filtered, payment & refund reads are support/finance/administrator, and issuing a refund is tightened to finance/administrator only.
> Version 1.11 · v1.11 changelog: §6 catalog rule completed (Phase 13.4) — the staff catalogue console (every status, server-filtered), reason-gated takedowns whose reason stays seller-visible, and audited operations/administrator category & brand management; the product queue is now moderator/administrator per §4.
> Version 1.10 · v1.10 changelog: §4 staff administration rules added (Phase 13 slices v1–v2) — the six-group least-privileged staff permission matrix, plus role/account-status change rules: administrator-only, refused for your own account and for superuser accounts, the last administrator cannot be demoted, suspension revokes live sessions, and every change writes an AuditLog row.
> Version 1.9 · v1.9 changelog: §6 fulfillment & post-purchase rules added (Phases 10–11) — per-store parcels with carrier adapters, append-only tracking events and parent-order status aggregation (COD is captured at delivery), then the customer surface on top: owner-scoped history/detail/receipt, an audit-derived order timeline with whitelisted copy, server verdicts for cancellation and reorder, and return/refund/issue request intake that Phase 17 adjudicates.
> Version 1.8 · v1.8 changelog: §6 payments & refund rules added (Phase 9) — one server-priced payment record per order, COD collected at delivery, adapter-seam online payments that expire after 24h, signed idempotent webhooks, and balance-checked refunds reversing an append-only ledger.
> Version 1.7 · v1.7 changelog: §6 checkout, shipping & order rules added (Phase 8) — per-store flat shipping with free-shipping thresholds, signed-in checkouts with immutable address snapshots, and checkout-time inventory reservation.
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

### Staff Permission Matrix (Phase 13, §13.1)

Staff power is group-based and least-privileged (rule 1 of `marketplace-admin` & `security` rule 3). Superusers bypass group checks; all other staff require membership in the named Django `Group`.

| Group | Key | Responsibilities & Authorized Actions |
|---|---|---|
| **Support** | `support` | Read-only oversight across users, orders, payments, shipments, and customer inquiries; intake-request review. Cannot approve sellers, moderate products, suspend stores, or issue refunds. |
| **Moderator** | `moderator` | Seller application review (`approve` / `reject`), store suspension & reactivation, product review & moderation (publish / reject / unpublish), review moderation (hide/restore + report resolution). |
| **Finance** | `finance` | Payment oversight, manual refund settlement (Phase 9/13), payout records & settlement, commission adjustments, financial reporting. |
| **Operations** | `operations` | Shipment carrier overrides, logistics status reconciliation, fulfillment dispute mediation, category & brand management. |
| **Administrator** | `administrator` | Full operational control: all powers of support + moderator + finance + operations, plus staff role assignment, user suspension, and marketplace settings. |
| **Super Administrator** | `super_administrator` | Technical governance: raw database administration, secret rotation, disaster recovery, emergency locks (`is_superuser=True`). |

Every sensitive action (application review, store suspension, product moderation, refunds, settings edits, role changes) writes an `AuditLog` row: `(actor, action, object_type, object_id, detail, timestamp)`.

Role and account-status changes follow the same least-privilege shape (Phase 13 slices v1–v2):

- Only administrators (or superusers) assign or remove staff groups and suspend/reactivate accounts. The API refuses changes to your own account, to superuser accounts, and any demotion that would remove the marketplace's last administrator.
- Suspension revokes live sessions — a suspended account is locked out immediately (Django's session auth rejects inactive users), not at its next login.
- Every role change (`staff_group_assigned` / `staff_group_removed`) and status change (`user_suspended` / `user_reactivated`) is viewable in the audit trail (§13.7) with its reason.

## 5. Core Features

### Customer
Register/login/logout · browse products · search · filter & sort · categories · product details · variants · cart · wishlist · checkout · payments · order tracking · reviews & ratings · seller messaging · profile & address book · notifications.

### Seller
Seller registration · store profile management · product CRUD · product image upload · variants · inventory · order processing · customer messaging · sales dashboard · store settings.

### Admin/Staff
User & seller management · product & category management · order oversight · payments & seller payouts · review moderation · marketplace settings · reports & analytics · staff permissions · audit logs.

## 6. Marketplace Features (cross-cutting)

- **Catalog:** product = title, description, images, category, price, variants (size/color with own stock/price), store, rating. Staff moderation completes the loop (Phase 13.4): moderators own publish/reject/unpublish — a staff takedown demands a reason, stores it on the product (seller-visible), and writes an `AuditLog` row; operations/administrator own the category tree and brand records through the same audited service paths.
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
- **Checkout & shipping (Phase 8):** checkout requires a signed-in customer and a validated shipping address — the guest cart merges into the account cart at login first (guests are prompted to sign in and cannot place orders). Shipping is charged **per store**, because each seller ships their own parcel: a store carries a flat fee (`shipping_flat_fee`) plus an optional free-shipping threshold applied to that store's subtotal. Order totals are `Σ store subtotals + Σ store shipping fees`, computed on the backend from server truth on every read and again at order creation — the client never sends prices, fees, or totals. Tax is not computed yet (`tax_total = 0`, slot reserved in the payload); COD carries no extra fee in this phase.
- **Orders:** explicit lifecycle (placed → awaiting payment → paid → shipped → delivered → completed / cancelled / refunded) with audit trail. Creating an order is **one transaction**: every cart line is re-validated against the live product, variant, stock, and price, then everything is **snapshotted** (product title, variant label, unit price, store, shipping address, shipping fee) and inventory is **reserved** (`reserved += qty`, reusing the row-locked inventory services). One parent `Order` plus one `SellerOrder` per store (each with its own items and shipping fee); snapshots are immutable, so later product, price, or address changes never alter an existing order. Reservations commit at `paid` (COD marks `paid` at delivery) and release on cancellation; unpaid online orders release after 24 hours.
- **Payments & refunds (Phase 9):** every order creates exactly one `Payment` (public `JVPAY-…` reference) whose amount is the server-computed order total — checkout picks a **method** (`cod`, `card`, `gcash`, `maya`), never an amount or a status, and a method with no configured gateway refuses the whole order (nothing partial is ever written). Orders start `awaiting_payment`: COD is collected at delivery (staff confirmation commits the reservation and marks the order + seller orders `paid`), while online methods run through the adapter registry (COD is itself an adapter; PayMongo/GCash/Maya plug in behind it) and **expire after the configured window** (default 24h — the `expire_payments` command releases stock and cancels the order). Payment status is server-authoritative (`pending → paid / failed / expired / cancelled / partially_refunded / refunded`), and every transition writes a `PaymentAttempt` row plus **append-only ledger rows** (`PaymentTransaction`: captures split per store so payouts can be derived later; refunds are debits; rows are never edited or deleted). Webhooks are **signature-verified before any state change** and idempotent per `(provider, event_id)` — duplicate deliveries are acknowledged and change nothing, and a gateway-claimed amount must equal the server amount or the capture is refused and recorded as failed. Refunds are balance-checked against the captured amount (full or partial); a full refund restores stock, reverses the ledger, and moves the order to `refunded` (Phase 17 builds the return flow on top). System-driven transitions (webhooks, cron) are audit-logged with a null actor — never attributed to a person.
- **Fulfillment & delivery (Phase 10):** each `SellerOrder` fulfills separately — `Shipment` parcels carry a carrier (adapter registry: `manual` now, JTex/LBC/NinjaVan later), a unique tracking number, package info, and an **append-only `TrackingEvent` timeline**; partial shipments are allowed and the parent order's status is **aggregated** from its seller slices, never set by hand. Delivery is the money moment for COD: confirming the last parcel delivered marks the order paid through the Phase 9 service, so the ledger stays the single source of money truth.
- **Customer account & post-purchase (Phase 11):** customers see and act on their **own orders only** — history, detail, receipt, timeline, tracking, cancel, reorder, and request intake are owner-scoped at the query level (no IDOR). The **order timeline derives from the append-only AuditLog**: whitelisted actions are mapped to customer-safe copy, and raw audit payloads never cross the wire. The **receipt renders only immutable snapshots** (later catalog, price, or address edits never move it). **Reorder** re-validates every line against live catalog/stock truth and reports skipped lines with reasons instead of silently dropping them. **Cancellation eligibility is a server verdict** (`can_cancel`, pre-payment only — paid orders go through refunds/returns). Return/refund/issue requests are **intake records only** (`OrderRequest`): eligibility is server-verified (delivered slice / captured payment / open order), duplicates are refused, customers may withdraw pending requests, and Phase 17 owns adjudication, restocking, and any money movement.
- **Platform settings (Phase 13.6):** the marketplace's platform-wide configuration is one server-side singleton row (`PlatformSettings`, pinned to pk 1): platform name + support email, the commission rate (0–100 — finance or administrator may set it; stored now, consumed by the commission engine when it lands), shipping defaults that seed each **newly created** store without ever touching existing ones, feature switches (`cod_enabled` — when off the checkout option greys out and `start_payment` refuses COD with a full rollback; `payment_expiry_hours` — the online-payment window now lives in the DB row and drives `expires_at`, with the env setting only seeding the row's first creation), and the notification defaults applied when a new account's `NotificationPreference` row is first created (an existing per-user row always wins). Reads are administrator/finance/operations, general edits are administrator-only; every change writes an `AuditLog` row with a per-field from→to diff; DB CheckConstraints back the serializer bounds; the anonymous subset (`platform_name`, `support_email`) is served read-only for the storefront chrome.
- **Reviews & ratings (Phase 14):** reviews are written only by **verified buyers** — `services.create_review` proves the caller owns a delivered/completed `OrderItem` for that product before the row exists, and the client never vouches for itself; one review per (user, product) is backed by a DB unique constraint and a rating `CheckConstraint`. Product and store `rating_average`/`rating_count` are **server-computed inside every review transaction** (create/edit/hide/restore/flag) — the frontend renders them and never recalculates. Moderation is staff-only (`moderator`/`administrator` via `InStaffGroup`): hiding demands a reason, is audit-logged (`review_hidden`/`review_restored`), and pulls the row off the public list and out of the aggregates; restore returns it (including clearing `FLAGGED`). Abuse reports (one per user per review) auto-flag at **3 distinct reporters**; staff resolve reports. Sellers reply **once per review to their own store's rows only** (public copy on the product page) and can never hide anything. Eligibility is a server verdict (`can_review`, `reason`, `order_number`, `review_id`) that drives the write/edit form.
- **Messaging & notifications (Phase 15):** conversations are **participant-scoped** (`Conversation`: buyer ↔ store seller, or buyer ↔ support) and may carry **order and/or product context**; starting a thread reuses the caller's open thread for the same customer/store/order/product, so the product-page and order-page entry points cannot duplicate a thread. Read state is **per participant** (`customer_last_read_at` / `seller_last_read_at` / `support_last_read_at`) — unread counts are derived on every read and opening a thread marks it read server-side; the client never keeps its own counter. Every request re-verifies access (`can_access_conversation`: the buyer, the store's owner, or `support`/`moderator`/`administrator` staff), sending a message notifies the counterpart through the notification service (the per-side mute flags suppress it), and a participant can **report** a thread (`ConversationReport`, status → `reported`, audit-logged) for moderation. Attachments are URL-based for now (`Message.attachment_url`) until the media phase. Notifications are one row per user (`Notification`, categories `orders` / `messaging` / `promotions` / `system`) written by the receiving flows and gated by the user's `NotificationPreference` row for email; in-app they surface through the navbar bell — unread count polled every 30 s, per-item and mark-all read, and navigation through the notification's `action_url`. The UI is one shared inbox (`ConversationInbox`) rendered at `/account/messages` (buyer) and `/seller/messages` (seller), with `MessageStoreButton` providing the product-page ("Message store"), order-page ("Contact seller") and order-support ("Contact support") starters. Still open: the remaining §15.3 event hooks (registration, seller decisions, payment/refund updates), §15.1 mute toggles and a staff report console, and the §15.4 Celery/Redis worker tier — email currently sends synchronously from `create_notification`.
- **Vouchers & promotions (Phase 16.1):** vouchers are **server-verified discount definitions** — platform or seller scope (a DB constraint guarantees seller vouchers carry a store and platform vouchers do not), percentage or fixed value with `min_spend`, an optional `max_discount` cap, `usage_limit`, `per_user_limit`, `first_order_only`, a start/end window, and product/category targeting rows (no rows = everything in scope). The client only ever sends the **code**: `evaluate_voucher` judges it against live server truth — the preview endpoint and checkout share the exact same service, so the two can never disagree — and `create_order` subtracts the server-computed discount from `grand_total`, snapshotting `voucher_code`/`discount_total` on the order while the payment collects the discounted amount. Redemption writes one append-only `VoucherUsage` row per voucher per order **inside the checkout transaction under a row lock**, with counters re-checked there — a limited code cannot be double-spent, the losing side of a race rolls its whole order back, and a `voucher.redeemed` AuditLog row records the exact money. Every rule is DB-constraint backed (`backend/tests/test_vouchers.py` + `test_vouchers_race.py`).
- **Automatic promotions (Phase 16.2):** discounts a customer never has to type are judged **per line by one engine** — `evaluate_store_lines` walks every live `Campaign` rule (product discount, flash sale, bundle quantity floor, free-shipping waiver, and buy-X-get-Y) against what earlier rules left on each line, so stacked discounts can never exceed a line's own subtotal. The **same function** runs at all four server-truth choke points (cart read, checkout preview, voucher evaluation, order creation), so no surface can quote a discount another one will not honour; the order snapshots the verdict as `promotion_discount` beside the voucher's `discount_total` in one `grand_total`, and an append-only `PromotionUsage` row plus a `promotion.applied` audit event record what each rule actually gave. Buy-X-get-Y is DB-constrained (a `buy_x_get_y` rule carries both the buy and the get product with positive quantities, and no other kind carries either) and only ever discounts the get product's units, capped by `get_qty` and by what earlier rules left on that line.
- **Discount funding (Phase 16.3):** every discount names **who pays for it** — the platform, the store, or both (`Voucher.funded_by`) — and the split is settled **server-side at redemption, never by the client**. A platform-funded discount is the platform's whole cost, a seller-funded one is the store's, and a **shared** discount is split **50/50 with any odd cent carried by the platform**, so the two shares always add back up to exactly the discount. Every `VoucherUsage` row snapshots both shares (`platform_amount`, `seller_amount`) under DB constraints, and a seller- or shared-funded voucher must be store-scoped (a platform-scope voucher has no store to charge). Funding **never changes what the customer pays** — the buyer always receives the full discount; it only decides which side absorbs the cost once the order settles. Seller payouts and commission reporting consume these shares when that tier lands.
- **Returns, refunds & disputes (Phase 17):** `apps.resolutions` turns an `OrderRequest` intake (Phase 11) into an **adjudicable `ReturnCase`**. Eligibility and the return window (`RETURNS_WINDOW_DAYS`, default 7) are **server verdicts** computed from fulfillment snapshots and served at `GET /api/v1/orders/<number>/return-eligibility`, and the deadline is **snapshotted onto the case**, so a later policy change can neither reopen nor quietly expire a live case. Filing sends only a reason, a note, line quantities and an optional intake link — the remaining-quantity cap, the duplicate guard, the restock default (damaged/defective lines stay off the shelf unless the seller says so) and the **refund due** are all decided server-side inside one row-locked transaction. Refund arithmetic is apportioned from order snapshots (order-level promotion/voucher discounts follow the lines that enjoyed them; a slice's shipping fee comes back only when that whole slice returns), but the resolution service **never touches the ledger** — it calls `payments.services.refund(..., restock=False, return_case=case)`. `Refund.restock` keeps a manual staff refund (which does return the lines to the shelf) distinct from a case-paid payout (receipt already did), and `Refund.return_case` keeps the money record's lineage to the case that authorised it. `POST /api/v1/admin/returns/<reference>/refund` is **finance/administrator only** and callable **only on a case whose goods were received** — money never precedes the parcel; the amount defaults to the case's remaining balance, partial settlements are capped against the case and then against the payment's own refundable balance, and in-flight gateway refunds count as already committed so a second payout cannot double-pay. The case follows its own money through the provider seam: COD settles synchronously, a hosted gateway stays `pending` until its signature-verified webhook confirms, and only then does the case reach `refunded`; a refused or unconfigured gateway **rolls the whole payout back** (no `Refund` row, no "issued" event). **Disputes** escalate in the same app: a `Dispute` (`JVDSP-…`, order- or slice-scoped) records the reason and the buyer's opening statement and may link both the intake it answers and the `ReturnCase` it contests (rejecting a return can be contested); statements and evidence are **append-only** child rows whose **party is derived from the caller** — buyer, store owner or staff, never taken from the client — with one open dispute per slice, a seller response, staff notes, a staff claim (`under_review`, idempotent) then a ruling (`buyer_favor`/`seller_favor` with a **mandatory reason**) that **freezes the record** (statements, evidence, withdrawal and a second ruling all refused) and notifies both sides. The buyer may withdraw their own dispute while it is undecided. Every movement writes the customer-safe timeline row **and** the `AuditLog` row; no money moves inside a dispute — a buyer win is settled through the refund payout above (§17.1–§17.3, `backend/tests/test_returns.py`).
- **Entity relationships (the domain map every marketplace skill builds on):** `Store` (owned by 1 seller) → many `Products` → many `Variants` + `Images` · `Category` tree → Products · `Cart` (1 customer or 1 guest session) → `CartItems` → Variant · Checkout → `Order` → `SellerOrders` (one per store) → `OrderItems` (immutable snapshots, store-scoped) → `Payments` (ledger + status) → seller payout records · Inventory lives per `Variant` (transactional decrement at purchase, restore on cancel) · `Review` (1 per user+product, verified buyers) → Product → seller rating · `WishlistItem` (customer ↔ product) · `Conversation` (customer ↔ store, per order/product) → `Messages` · `Notification` (per user) · `Voucher` (platform/seller) → `VoucherEligibility` (product/category targets) + `VoucherUsage` (one ledger row per order, carrying the funding split) · `Campaign` (scope + window) → `Promotion` rules → `PromotionTarget` rows + `PromotionUsage` (one ledger row per promotion, store and order) · `Order` / `SellerOrder` → `OrderRequest` (Phase 11 intake) → `ReturnCase` (verdict, reverse parcel, `ReturnItem` restock ledger, refund attribution) → `ReturnEvent` timeline · `Dispute` (order- or slice-scoped) → `DisputeStatement` / `DisputeEvidence` / `DisputeEvent` · `AuditLog` (staff actions) · reporting aggregates (`DailyPlatformMetric` / `DailyStoreMetric` / `DailyProductMetric`, Phase 19 — derived from the records above by the rebuild command, rebuildable and never hand-edited). Role scopes (customer / seller / staff / administrator) per §4 — staff power is group-based, administrator is the full-control group.
- **Seller analytics (Phase 19.2):** the same aggregates at the store grain, served by `GET /api/v1/seller/analytics/?from=&to=` — range totals (gross sales, orders, revenue, products sold, commission), the daily store series, best sellers (`top_products` filtered by `store_id`), voucher performance (`voucher_redemptions`/`voucher_discount`, apportioned across every store an order carried so the parts re-add to the `VoucherUsage` ledger), published-review metrics (`review_rating_avg` is **null**, never zero, when nothing was reviewed), and the stock as a **live snapshot** labeled as one rather than a period metric. Access is **ownership-scoped, not group-scoped**: the store is resolved from the session (`Store.user == request.user`), there is no `store_id` parameter to forge, a seller with no store gets 404, and everyone else 403 — while the Phase 12 `/seller` dashboard stays untouched (marketplace-sellers rule 4, documented deferral): the page is `/seller/analytics`, fed by `fetchSellerAnalytics` in `src/data/seller.js`, which renders the server's numbers and never re-derives one.

- **Analytics & reporting (Phase 19):** a dashboard never queries the transactional tables — every figure it shows is read from a **reporting aggregate** (§17). `apps.reporting` keeps daily rollup rows (`DailyPlatformMetric` for the marketplace, `DailyStoreMetric` per store, `DailyProductMetric` per product and store) that the `rebuild_reporting` command **derives** from the records above; they are **rebuildable and never hand-edited**, so dropping a date range and recomputing it must reproduce the same rows — that, not a promise, is the mechanism behind the Phase 19 gate "the metrics reconcile with the transactional data". Each metric has exactly one definition. **GMV** sums the `grand_total` of the orders placed in the period whose status was not cancelled. **Revenue** is money actually collected net of what was given back — the ledger's capture credits minus its refund debits. **Commission** is the platform's cut of a store's merchandise: `SellerOrder.subtotal` less the discounts **that store itself funded** (`VoucherUsage.seller_amount` for the slice, plus the `PromotionUsage` rows of seller-scoped campaigns — a platform-funded discount was never the seller's revenue, and shipping is not merchandise), multiplied by `PlatformSettings.commission_rate_percent` **as it stood when the money was captured**, with the applied rate stored on the aggregate so a later rate change can never rewrite settled history, rounded half-up and leaving the odd cent on the platform's side exactly as shared funding already does (§16.3). An **active customer** is one who placed at least one non-cancelled order in the period; an **active seller** is a store that received one. Commission follows the ledger and not the badge — it is earned on **capture**, and a refund reverses its share proportionally. Reads are group-gated per §4 and read-only: the **financial** figures (GMV, revenue, commission, refund amounts) and **every export** belong to `finance` and `administrator`, exactly as §4 already assigns financial reporting and settlement; the **operational** metrics (order status, fulfillment, returns, support, seller performance) are visible to `support`, `operations`, `finance` and `administrator`, the groups that already oversee those records. **Seller analytics are strictly owner-scoped** — a store reads its own numbers and nothing else, enforced server-side like every other ownership check. Exports are **CSV only**, written with the standard library, served through the same permission gate as the data they expose, and recorded in the audit trail; Excel and PDF stay deliberately unticked rather than approximated, because both need a runtime dependency and C3 does not permit one without the owner's decision.


## 7. Frontend Architecture Expectations

Stack: React · Vite · JavaScript/JSX (no TypeScript for now) · Tailwind CSS v4 (CSS-first `@theme`, no tailwind.config.js) · React Router.

```
frontend/src/
  routes/             marketplace pages — thin, compose features
  features/           per-domain modules (auth/, cart/, wishlist/, reviews/, …)
                      holding logic, hooks, and feature-specific components —
                      created per-domain as features are built (auth, cart,
                      wishlist, seller/checkout and reviews are live)
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

- **App-per-domain:** `accounts`, `stores`, `catalog`, `cart`, `orders`, `payments`, `platform`, `reviews`, `messaging`, `notifications`, `analytics`, `audit`.
- **API:** versioned under `/api/v1/`, JSON-only, DRF viewsets + serializers; model fields are never exposed without a serializer.
- **Response envelopes:** list → `{count, items}`; single → object; error → `{error, detail?, field_errors?}`; not found → JSON 404 (never HTML).
- **Business logic** lives in service layers/model methods — not views — so it is testable in isolation.
- **Validation:** DRF serializer validation + model constraints; frontend validation is UX only, never security.
- **Permissions:** DRF permission classes per role + object-level checks (sellers touch only their store; customers only their own orders).
- **Media:** product images validated (type, size) and stored via Django's media handling (local in dev, object storage in prod).

## 9. Database Architecture Expectations

- PostgreSQL is the primary database (SQLite never in production). Django ORM + migrations; no raw SQL in views.
- Core entities: User, Store, Product, ProductVariant, ProductImage, Category, Cart, CartItem, Order, SellerOrder, OrderItem, Payment, PaymentAttempt, Refund, PaymentTransaction, WebhookEvent, Review, WishlistItem, Address, Conversation, Message, Notification, AuditLog, PlatformSettings.
- Rules: FK constraints on every relation with explicit `on_delete` (PROTECT for money/legal, CASCADE/SET_NULL where safe); indexes on browse paths (category, store, price, created); unique constraints where meaningful (one review per (user, product)); money as Decimal — never float.
- OrderItem snapshots title/price at purchase time (immutable).
- Payment ledger rows (`PaymentTransaction`) are append-only; balances are always recomputed sums of those rows, never stored counters.
- AuditLog records who changed what and when for staff actions and critical transactions; system-driven entries (webhook, cron) carry a null actor.

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


