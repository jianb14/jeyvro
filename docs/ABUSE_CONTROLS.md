# Abuse controls coverage (§20.2)

The honest answer to one question: **for a given abuse surface, what stops it,
where, and what is recorded when it fires?** This file is that answer.

`backend/tests/test_abuse_controls.py` is the machine-checked half: it drives
the paths below and asserts the outcomes named here, so this page cannot
quietly rot into fiction.

## The one principle: the system queues, it does not censor

This slice had a single design decision, and everything else follows from it.

> An automatic rule **never refuses a write, never edits text, never deletes
> anything, and never tells the author they were caught.** It files one flag
> row and hands the decision to a human.

The reason is a false positive. A ruleset that punishes ordinary customers is
worse than no ruleset, and a marketplace that mutes its own buyers in a
language its rules were not written for is a product failure, not a safety
win. So the cost of being wrong is deliberately small and visible:

| Instead of… | The system… | So a false positive costs… |
| --- | --- | --- |
| Rejecting the review | creates it, status `FLAGGED` | a queue row and staff minutes |
| Rewriting the text | stores it verbatim | nothing — the words are untouched |
| Deleting the message | stores it, thread → `reported` | nothing — the evidence survives |
| Hiding it from its author | leaves it readable to them | the author's right to speak |
| Silently dropping the rating | excludes it from the aggregate | a rating that waits for a human |

The author's own copy stays readable to them. They are not told they were
censored, because they were not — a moderator may yet restore it, and a
silent "your review is hidden" with no appeal is the thing this avoids.

## Deliberate omissions

Three things a moderation feature usually ships with are **absent on
purpose**, and each absence is a decision rather than an oversight:

- **No profanity or slur list.** Word blocklists are language-specific. A
  Filipino/Tagalog corpus contains words an English-derived list calls abusive
  and vice versa, so a blocklist mutes ordinary Filipino customers. The rules
  here are *structural* — properties of the text — not lexical.
- **No third-party or model-based filtering.** Calling an external service
  turns a local decision into an availability dependency and ships customer
  text to a third party. Every rule is a pure function: no database, no
  network, no settings lookup at import time.
- **No automatic permanent penalties.** A rule that trips puts content in a
  queue. It never suspends an account, because "this pattern looks like spam"
  is weaker evidence than "this person is abusing the platform," and only a
  human can weigh that.

## The rules

`apps/moderation/rules.py`. `evaluate(text, kind=...)` returns
`{'flagged': bool, 'rules': [...], 'detail': str}`.

`kind` genuinely changes the outcome, and the caller states it rather than
the ruleset guessing:

| Rule | Fires on | Review | Message | Rationale |
| --- | --- | --- | --- | --- |
| `link` | a URL, `www.`, or a bare domain | ✅ | ✅ (own-domain exempt) | Off-product advertising is the commonest spam shape. A seller quoting their own storefront to their buyer is conversation, not advertising. |
| `contact` | an email, or a phone number *with intent words* | ✅ | ❌ | Contact details addressed to strangers is spam in a **public review**; the same text in a private message is a customer telling a seller how to reach them. |
| `shouting` | >20 letters and >70% capitals | ✅ | ✅ | Both a length and a ratio floor are required, so `OK`, `LOL` and `USB-C`/`HDMI` pass. |

### What the rules deliberately do *not* catch

The false-positive guards are as much of this slice as the catches, and each
one is a test:

| Text | Why it is **not** flagged |
| --- | --- |
| `Order JV-20260926-ABCD2345 arrived late` | A 4-digit block is not a phone number. Order numbers use letter groups that never form a 7–15 digit run. |
| `Tracking JVTRK-20260926-0001 took 5 days` | Same reason. |
| `Size 2.5kg … I ordered 4 pcs` | Measurements and small counts are not contact details. |
| `The USB-C port and HDMI output work` | Acronyms are not shouting. |
| `You can see it at https://jeyvro.com/store/x` (message) | Quoting the platform is normal in a private thread. |
| `my email is me@shop.com` (message) | Giving a seller your address is contact, not advertising. A domain that is the *tail of an email* is not a link. |



## Where each control is enforced

| Surface | Control | Enforcement point | On a hit |
| --- | --- | --- | --- |
| Review create | `link`/`contact`/`shouting` | `reviews/services.py::create_review`, **after** the row exists | review `FLAGGED`, `ContentFlag`, `content_flagged` audit |
| Review edit | same rules | `reviews/services.py::update_review` (a clean review can be edited into spam) | re-flag, existing row reopens |
| Review rating | flagged reviews excluded | aggregates count `PUBLISHED` only | the spam cannot vote while it waits |
| Message send | `link`/`shouting` | `messaging/services.py::send_message`, **after** the row exists | message stored, thread → `reported`, `ContentFlag` |
| Thread start | `conversation` throttle (20/hour) | `CustomerConversationListView` | 429 |
| Messaging | user block | `messaging/services.py::_assert_not_blocked` | `PermissionDenied` (403) |
| Thread start | user block | `start_or_get_conversation`, before the row exists | `PermissionDenied` (403) |
| Staff triage | dismiss / confirm | `moderation/services.py::resolve_flag` | `content_flag_dismissed` / `content_flag_confirmed` |
| Checkout | whole-order unit ceiling | `orders/services.py::create_order`, inside the cart lock, **before** any pricing or reservation | `CheckoutError(order_units_exceeded)`; nothing written |

**The throttle is write-only.** The inbox list and the thread starter are the
same endpoint, so a plain `ScopedRateThrottle` cannot tell a read from a
write — and a 20/hour cap on *reading* the inbox would be a speed bump on
ordinary use (§10.2). `WriteOnlyScopedRateThrottle`
(`apps/messaging/throttling.py`) waves safe methods through and counts only
unsafe ones.

## Slice v2: unpaid COD orders holding stock

An unpaid **cash-on-delivery** order holds its stock reservation **forever**.
`Payment.expires_at` is `None` for COD and `payments.services
.expire_overdue_payments` explicitly `.exclude(method=PaymentMethod.COD)`, so
the `expire_payments` cron never touches it. The only exits are the customer
cancelling or a seller marking it delivered/failed — so a seller's `available`
count can be pinned down indefinitely by orders nobody intends to pay for.

Excluding COD from *payment* expiry is correct and stays: cash is due at
delivery, so the payment has no window. The gap was that the **reservation**
was bound to that same window.

**The fix is a report, not a reaper.** An unpaid COD order may be a real parcel
in transit to a slow buyer, so it is never cancelled automatically — killing it
would be worse than the leak. Instead the order surfaces to staff, who release
it by hand.

| Endpoint | Who | What |
| --- | --- | --- |
| `GET /api/v1/admin/stale-cod/` | support, operations, administrator | orders holding stock past the window (`?q=`) |
| `POST /api/v1/admin/stale-cod/<number>/release/` | support, operations, administrator | release the reservation, with a reason |

- The window is `ORDERS_COD_RESERVATION_REVIEW_DAYS` (default 7) and is a
  **review** threshold, never a cancellation timer.
- The list is narrow on purpose, because a row that does not belong on it is a
  real order someone might wrongly release: COD only, payment still `pending`,
  order still pre-fulfilment, and **no parcel dispatched on any store slice**. A
  parcel in transit is a sale that already happened — releasing its stock would
  sell the same unit twice.
- `release_stale_cod_reservation` **re-checks the stale verdict at the moment of
  the action**, not from the rendered list, so an order that shipped between the
  list render and the click is refused.
- The release **cancels the order with the stock**; releasing stock while an
  order still claims it would double-sell. A reason is mandatory, and the action
  writes `order.cod_reservation_released`.

## The per-order total-units ceiling (§20.2 v3)

`MAX_LINE_QUANTITY` (99) is a cap on **one line**, so it never bounded a basket:
20 lines of 99 is 1,980 units, and one checkout could reserve that much stock
across many stores at once.

| | |
| --- | --- |
| `ORDERS_MAX_ORDER_UNITS` | default **200**, read from settings at call time |
| Enforced in | `orders.services.create_order`, inside the cart lock, **before** any pricing or reservation |
| Error | `CheckoutError(code='order_units_exceeded')` — names both numbers and tells the customer to split the order |
| Published on | `GET /api/v1/cart/` → `totals.max_order_units` and `totals.over_unit_ceiling` (advisory) |

- The cart read publishes the ceiling so the UI can warn **before** checkout. It
  is advisory only; the binding check is on the server, in `create_order`, where
  the cart is re-read under lock — so a client that ignores the hint still
  cannot get past it.
- The refusal happens before anything is written, so an over-limit cart reserves
  no stock and writes no partial order.
- The boundary is **inclusive**: exactly `N` units passes. A `>` that should have
  been `>=` would refuse a legal order and stop a customer buying a single line.
- The per-line cap still stands independently. The two are separate policies.
- **No audit row.** A refused checkout is not a state change — nothing was
  created, no stock moved, so there is nothing to record and the refusal adds no
  row to §6's matrix. `docs/AUDIT_COVERAGE.md` says so in writing rather than
  leaving the absence to be discovered as a hole.

**The false-positive guard is the point of this control.** The default sits well
above an ordinary basket and above a real bulk buyer's restock — a sari-sari store
buying 180 units across two lines is ordinary trade and must go through
untouched. The ceiling is a backstop against *one checkout reserving a catalog's
worth of stock*, not a limit on ordinary trade; a ceiling that punished the
legitimate wholesale customer would be worse than having none. It is configurable
so operations can raise it for a real wholesale account without a deploy, and the
tests assert the 180-unit restock, the inclusive boundary, and the configurability
as contracts rather than leaving them to hope.

## Not yet covered — the rest of slice v3, and slice v4 (open)

These are the §20.2 gaps that remain, listed so the page never implies the
phase is finished. **Slice v3 is half done**: the per-order total-units ceiling
above shipped, and the suspicious-order foundation below is the other half.

- **Suspicious-order signals** — high-value COD on a new account, many
  distinct shipping addresses, repeat abandon/cancel. Same contract as this
  slice: flag for a human, never auto-block the buyer.
- **Account abuse** — disposable-email domains, a new-account purchase ceiling,
  email verification before a high-value COD order.

## Blocks

A block is **user-scoped, not conversation-scoped**: a buyer who blocks a
seller is refusing that person, and must not escape the block by opening a
fresh thread on a different product. `store` is context for the console; the
block resolves through the user, so it survives a rename.

- `POST/GET /api/v1/conversation-blocks/`,
  `DELETE /api/v1/conversation-blocks/<id>/`
- One row per (blocker, blocked) — a DB unique constraint, and a self-block is
  refused by a `CheckConstraint`.
- The refusal is **silent** to the blocked party. Telling a spammer their
  block landed is free information for them.
- **Staff are never a counterparty.** A support agent must be able to answer a
  buyer whose thread is messy, and nobody may block their way out of a dispute.
- A user may only read and delete **their own** blocks; another user's block
  is `404`, never `403`, so ids cannot be probed.

## The staff queue

| Endpoint | Who | What |
| --- | --- | --- |
| `GET /api/v1/admin/moderation/flags/` | support, moderator, administrator | the worklist (`?status=open\|dismissed\|confirmed\|all`, `?kind=`) |
| `POST /api/v1/admin/moderation/flags/<id>/resolve/` | moderator, administrator | `dismiss` or `confirm` |

The default worklist is the **open** pile; `open_count` is that same pile's size,
so the staff console badge never counts work that is already done. An unknown
`status` or `kind` is a `400` rather than an empty list — a typo'd filter must not
read as "nothing to review", and an unknown flag id is a `404`.

Support may **look**; only a moderator may **act** — resolving a flag hides or
restores a customer's review, which is the moderator/administrator power §4
already grants over reviews.

- `dismiss` — the rule misfired. The review returns **through the reviews
  service**, so the product and store rating aggregates are recomputed (§6
  rule 3). A restored review can never come back with a rating that disagrees
  with the rows behind it.
- `confirm` — it was abuse. Demands a written reason; hides the review through
  the same service, so the aggregates follow.
- One flag row per subject, so repeated edits cannot manufacture a queue of
  duplicates. Re-flagging a dismissed row **reopens** it, because content that
  has since acquired a link is new information.
- The listing carries **rules and ids, never the text**. Staff open the review
  or conversation where it already lives; copying the body here would create a
  second copy of customer PII to redact, retain and eventually leak (§10.1).

## Audit actions

| Action | Actor | When |
| --- | --- | --- |
| `content_flagged` | the author | a rule fired |
| `content_flag_reopened` | the author | a resolved flag fired again |
| `content_flag_dismissed` | staff | the rule misfired |
| `content_flag_confirmed` | staff | the content was abuse |
| `conversation_blocked` | the blocker | a block was created |
| `conversation_unblocked` | the blocker | a block was lifted |

## What is deliberately NOT here

Carried forward, not overlooked:

- **Voucher and promotion abuse** — already solid. `usage_limit`,
  `per_user_limit`, `first_order_only`, an append-only `VoucherUsage` ledger
  and row-locked redemption make it race-safe. Nothing was ever needed here.
- **Inventory / quantity abuse** — *closed.* The two halves arrived as slice
  v2 (a stale-COD reservation can no longer pin stock forever) and slice v3
  (above — one checkout can no longer reserve a catalog's worth): what remains
  from the original list is detection, not prevention.
- **Suspicious-order detection** — real gap, the other half of slice v3. It
  needs persistence and a risk model, not a content rule.
- **Account abuse** (per-email registration caps, disposable-domain checks) —
  real gap, deferred to slice v4.
- **Alerting, retention, and signed audit export** — deferred to Phase 23.
