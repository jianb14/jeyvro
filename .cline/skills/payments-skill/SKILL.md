---
name: payments-skill
description: Develop the Jeyvro payments domain — use when building the payment ledger and status flow, Cash-on-Delivery, gateway adapters (PayMongo/GCash/Maya), webhooks, refunds, seller payouts, or marketplace commissions. Money facts are ledger records computed server-side; the gateway is never trusted blindly. The dedicated-money-domain split from backend-feature (SKILL_ARCHITECTURE §6).
---

> **Source of truth:** [PROJECT_CONTEXT.md](../../PROJECT_CONTEXT.md) — when anything conflicts, the project context wins. Catalog entry: #26 in [SKILL_CATALOG.md](../../SKILL_CATALOG.md).

# Jeyvro Marketplace — Payments Domain

One responsibility: **how to develop money movement** — the payment ledger, COD, gateway adapters, webhooks, refunds, seller payouts, and marketplace commissions. Created by owner request (the trigger from SKILL_ARCHITECTURE §6); the actual gateway adapter build still lies ahead.

## Purpose

Every peso has a record: payments are ledger entries with explicit status, verified server-side — so refunds, payouts, and commissions are always derived from truth, never typed in.

## Current honest state

Live since Phase 9: `apps/payments` ships the domain (`Payment`/`PaymentAttempt`/`Refund`/`PaymentTransaction` ledger/`WebhookEvent`), the adapter registry (`adapters/` — COD first, a generic hosted-gateway seam for the future PayMongo/GCash/Maya integrations), signed idempotent webhooks, and the `expire_payments` cron command. Commissions/payout aggregation (§13) build on the per-store capture ledger rows that already exist.

## When to use

- Payment records, status flow, ledger design
- COD handling; gateway-adapter interface; webhooks; refunds
- Seller payouts; marketplace commission records

## When NOT to use

- Order lifecycle/snapshots/inventory (`marketplace-orders` — this skill consumes its services) · staff permission to issue refunds (`marketplace-admin`) · generic modeling (`backend-core`)

## Workflow

1. **Understand** — §6 Payments/Orders rules + §6 domain map (Order → Payments → payout records); which events move money?
2. **Inspect** — order services and totals computation first — payments verify against them, never against client figures.
3. **Plan** — ledger schema → adapter interface → status transitions → webhook flow → commission records → payout aggregation; tests planned per §11 money gates.
4. **Implement** — adapter interface + COD first; ledger service; webhook endpoint (signature-verified, idempotent).
5. **Test** — §11 priority: capture, failed capture, double-webhook (idempotency), refund + inventory restore, commission math, payout aggregation.
6. **Review** — every money transition has a ledger row + audit trail; no unverified gateway claims.
7. **Fix** — in payment services.
8. **Verify** — checklist below.

## Rules (binding)

1. Every payment is a ledger record with explicit status (pending → paid / failed → refunded) — never a flag or a log line (§6).
2. **Never trust the gateway or the client blindly:** capture amounts are verified against server-computed order totals before marking paid; webhook payloads are signature-verified; unverified claims change nothing.
3. Webhooks are idempotent — the same event twice must not double-charge, double-refund, or duplicate records.
4. Gateway access goes through one adapter interface — domain code never calls a gateway SDK directly (§6, §17); COD is the first adapter (mark paid on delivery per the §6 lifecycle).
5. **Marketplace commissions** are computed server-side from order totals at capture time (rate from staff-managed marketplace settings) and written as ledger records — never derived afterwards by hand.
6. **Seller payouts derive from order/payment/commission records** — never manually keyed amounts (§6 v1.1 rule); payout summaries are read-only aggregates.
7. Refunds run through payment services + order lifecycle (`marketplace-orders`), restore inventory transactionally, reverse their ledger entries, and are audit-logged (§9/§10.7).
8. Money is `Decimal` (C6); every money transition is concurrency-safe (row locks / idempotency keys) — no double captures or refunds under parallel requests.

## Best practices

- Adapter interface first, COD second, real gateways later — the seam is the whole point.
- Log gateway request/response references (IDs), never secrets or full credentials (C7).
- Reconcile: a ledger that can be replayed into the same balances is the goal.

## Common mistakes

- Marking an order paid because the client said so, or on an unverified webhook.
- Non-idempotent webhooks creating duplicate payments/refunds.
- Commissions applied inconsistently across gateways (per-adapter math instead of one service).
- Payout figures typed into an admin form.
- Float math creeping into fees.

## Verification checklist

- [ ] Ledger record + status per payment; verified totals before "paid"
- [ ] Webhooks signature-verified and idempotent (double-send tested)
- [ ] Commissions computed at capture, stored as ledger records
- [ ] Payouts derived from records only; refund flow restores inventory + reverses ledger
- [ ] Decimal money; concurrency/idempotency tests pass (§11)
