---
name: marketplace-community
description: Develop the Jeyvro community domain — use when building product reviews, product and seller ratings, the wishlist, buyer-seller messaging, or in-app notifications. Covers backend and frontend for these areas; rules live in PROJECT_CONTEXT §6 (verified buyers, one review per user and product, moderation).
---

> **Source of truth:** [PROJECT_CONTEXT.md](../../PROJECT_CONTEXT.md) — when anything conflicts, the project context wins. Catalog entry: #24 in [SKILL_CATALOG.md](../../SKILL_CATALOG.md).

# Jeyvro Marketplace — Community Domain (Reviews · Ratings · Wishlist · Messaging · Notifications)

One responsibility: **how to develop the trust and communication features** — reviews, ratings, wishlist, buyer-seller messaging, and notifications — across backend and frontend. These features run on the relationships from the §6 domain map (Review → Product → seller rating; Conversation per order/product).

## Purpose

Customers trust the marketplace (verified reviews, real ratings) and stay connected (messages, notifications) — with moderation kept clean and spam impossible.

## Current honest state

Frontend has `ReviewCard`, `Rating`, wishlist mocks; no backend yet. Backend build order puts `reviews` → `messaging` → `notifications` after `payments` (per `backend-feature`).

## When to use

- Review create/edit/moderation; product + seller ratings
- Wishlist add/remove/browse
- Customer ↔ store conversations (per order or per product)
- In-app notifications (unread badge) and their triggers

## When NOT to use

- Order status/tracking (that data feeds reviews' verified-buyer check but belongs to `marketplace-orders`) · payment disputes (`payments-skill`) · generic primitives (`frontend-ui`)

## Workflow

1. **Understand** — §6 Reviews/Messaging/Notifications rules; roles: customer writes/receives, seller responds (own store), staff moderates.
2. **Inspect** — `ReviewCard`/`Rating` primitives, existing review mock shapes, conversation/notification patterns.
3. **Plan** — backend per `backend-core`/`backend-api` (unique constraint (user, product); verified-buyer service check); frontend per `frontend-feature`/`ux-patterns`.
4. **Implement** — moderation states, rating aggregates, notification triggers.
5. **Test** — verified-buyer enforcement, one-review-per-user constraint, moderation permissions, message scoping (deny paths).
6. **Review** — §6 traced; aggregates derive server-side only.
7. **Fix** — in services.
8. **Verify** — checklist below.

## Rules (binding)

1. **Verified buyers only** — the backend confirms purchase from order history before a review is accepted (§6); never trust a client claim of purchase.
2. One review per (user, product) — enforced by a database unique constraint (§9), not just validation.
3. Rating aggregates are computed server-side (product average; seller rating derives from product reviews, §6) — the frontend displays, never recomputes.
4. Reviews are moderateable by staff; moderation changes are audit-logged; sellers cannot delete reviews of their own products.
5. Wishlist is private per customer — only its owner reads it.
6. Messaging: conversations are scoped per order or product and participant-only (customer + that store's seller); staff access follows moderation rules and is audit-logged.
7. Notifications are in-app first with an unread badge (§6); triggers are defined per domain event (order updates, seller replies) — no notification spam; email digests come later.

## Best practices

- Rating aggregate updates ride the review service transaction — never a scheduled "fix the averages" job.
- Reuse `ReviewCard`/`Rating`/`Badge` (unread) primitives; new UI only via `frontend-ui`.
- Seed reviews match the frontend contract shapes and realistic PH-buyer tone.

## Common mistakes

- Accepting reviews without a server-side purchase check.
- Recomputing averages in the frontend from the review list.
- Sellers editing/hiding their own product reviews.
- Conversations readable by anyone with the URL (missing participant check).
- A notification for every trivial event — users mute spam.

## Verification checklist

- [ ] Verified-buyer check server-side; unique (user, product) constraint in place
- [ ] Rating aggregates server-computed; moderation + audit trail works
- [ ] Wishlist private; conversations participant-scoped (deny paths tested)
- [ ] Notification triggers defined per domain event; unread badge wired
- [ ] All UX states wired (`ux-patterns`); seed matches contract
