---
name: backend-core
description: Structure and model the Jeyvro Django backend — use when scaffolding the Django project, creating or changing apps, models, fields, relationships, constraints, indexes, migrations, or transactions, writing Python for the backend, optimizing ORM queries, or deciding how data integrity is enforced in PostgreSQL. Does not cover the HTTP/API layer (backend-api), permission patterns (security), or per-domain business logic (backend-feature).
---

> **Source of truth:** [PROJECT_CONTEXT.md](../../PROJECT_CONTEXT.md) — when anything conflicts, the project context wins. Catalog entry: #8 in [SKILL_CATALOG.md](../../SKILL_CATALOG.md).

# Jeyvro Backend Core — Django Structure & Data

One responsibility: **how the Django project is structured and how data is modeled so integrity is enforced by the database itself**. HTTP lives in `backend-api`; permission patterns in `security`; domain recipes in `backend-feature`.

## Purpose

Give Jeyvro a backend where every money/legal fact is protected by constraints and transactions — so no bug, bad client, or code path can corrupt marketplace data.

## Current honest state

Django is **not yet scaffolded** (PROJECT_CONTEXT C5). The first task under this skill is the scaffold: `backend/` project + venv + PostgreSQL settings + `.env.example`, then app-per-domain (§8). Until then, this skill guides the design; nothing runs yet.

## When to use

- Scaffolding/configuring the Django project; the settings/`.env` split
- Creating/changing apps, models, fields, relationships, constraints, indexes
- Writing/applying migrations; transactions; ORM query optimization
- Any Python written for the backend

## When NOT to use

- Endpoints/serializers (`backend-api`) · auth/permission *patterns* (`security`) · per-domain business rules (`backend-feature`) · deployment (the `deployment` skill)

## Workflow

1. **Understand** — which entities/relationships does this change involve? Which §9 rules apply?
2. **Inspect** — read existing models/migrations first; never plan a new model before checking what exists.
3. **Plan** — schema change → migration plan; on_delete, indexes, and constraints decided *before* writing code.
4. **Implement** — model + constraints + migration; Python per PEP 8 / Django style.
5. **Test** — `makemigrations --check --dry-run` clean; tests + runserver smoke (§14.7).
6. **Review** — read the generated migration diff like code; look for destructive operations.
7. **Fix** — anything destructive or accidental → regenerate; never hand-edit an applied migration.
8. **Verify** — checklist below.

## Rules (binding)

1. **Inspect existing models before creating new ones** — duplication forbidden; extend or reuse first (§14). One entity, one model (e.g. a seller IS a user with a store — never a parallel "seller account" model).
2. **No destructive migrations** (drop table/column, data-losing type changes) **without the owner's explicit instruction** — and only with an agreed data-preservation plan.
3. PostgreSQL is the primary database; SQLite never in production. Money/quantities are `DecimalField` — never float (§9, C6).
4. Every FK has explicit `on_delete` — `PROTECT` for money/legal records (Order, Payment, OrderItem), `CASCADE`/`SET_NULL` only where genuinely safe (§9).
5. Indexes on browse paths (category, store, price, created); unique constraints where meaningful (one review per (user, product)).
6. Multi-step money operations (checkout, refunds, inventory decrement) run inside `transaction.atomic()` with `select_for_update()` on stock rows.
7. Integrity is enforced by database constraints — never only by serializer or form validation.
8. ORM only — no raw SQL in views; `raw()`/`extra()` only with a measured, reviewed reason.
9. Secrets in `.env` (never committed); `.env.example` documents every variable (§10.5).
10. New Python dependency needs the owner's approval (C3).

## Best practices

- App-per-domain per §8 (accounts, stores, catalog, cart, orders, payments, reviews, messaging, notifications, analytics, audit) — where a model lives decides where its logic lives later.
- Model methods and services own invariants (stock cannot go negative) so every caller inherits them.
- Migrations: small, ordered, reviewable — one schema concern per migration.
- Add indexes when a query pattern is known — not speculatively.

## Common mistakes

- Duplicating an existing model (a second "store" or "seller profile") instead of extending.
- Float for money; missing `on_delete`; missing unique constraint.
- Editing a migration that was already applied elsewhere.
- "Fixing" data by running a destructive migration instead of writing a data migration.
- Business logic inside `save()` overrides that belongs in a service layer.

## Verification checklist

- [ ] Existing models inspected; no duplication
- [ ] Migration generated, reviewed, non-destructive (or explicitly approved with a data plan)
- [ ] Decimal money; explicit `on_delete`; §9 indexes/constraints in place
- [ ] Multi-step money paths wrapped in transactions with row locks
- [ ] `makemigrations --check`, tests, runserver smoke pass
- [ ] `.env` variables documented in `.env.example`; nothing secret committed
