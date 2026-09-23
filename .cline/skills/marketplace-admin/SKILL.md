---
name: marketplace-admin
description: Develop the Jeyvro admin/staff marketplace management — use when building staff dashboards, user and seller management, product/category/order/payment oversight, review moderation, marketplace settings, reports and analytics, staff permission groups, or audit log views. Distinguishes staff (group-based power) from administrator (full control) per PROJECT_CONTEXT §4; sensitive actions are always audit-logged.
---

> **Source of truth:** [PROJECT_CONTEXT.md](../../PROJECT_CONTEXT.md) — when anything conflicts, the project context wins. Catalog entry: #25 in [SKILL_CATALOG.md](../../SKILL_CATALOG.md).

# Jeyvro Marketplace — Admin & Staff Management

One responsibility: **how to develop the staff side of the marketplace** — oversight of users, sellers, catalog, orders, payments, reviews, and settings, plus staff permission groups and the audit log. Administrators hold full control; staff power is group-based and least-privileged (§4).

## Purpose

Give the operator team safe, audited control of the marketplace: they can see and moderate everything, act only within their group's powers, and every sensitive action leaves a trail.

## Current honest state

No Django admin/staff UI yet. Django admin registration lands with the scaffold (`backend-core`); the staff dashboard frontend follows the first domains (`admin-panel-skill` was the planned split — created by owner request; staff dashboard build order per `backend-feature`/`frontend-feature`).

## When to use

- Staff/admin dashboards and management screens (users, sellers, products, categories, orders, payments)
- Review moderation surfaces; marketplace settings; reports & analytics
- Staff permission groups (support / moderator / administrator); audit log views

## When NOT to use

- Seller-facing store management (`marketplace-sellers`) · customer features (`marketplace-community`) · permission *patterns* (`security` — this skill applies them) · payout money math (`payments-skill`)

## Workflow

1. **Understand** — which staff group needs this surface, and what may it change (§4)? What must be audit-logged?
2. **Inspect** — existing models/admin registrations, group definitions, audit patterns before extending.
3. **Plan** — read surfaces first; write actions go through domain services (`backend-feature`) — never new side-door logic.
4. **Implement** — group-gated permissions (with `security`), Django admin registration where sensible, staff UI per `frontend-feature`/`ux-patterns`.
5. **Test** — per-group allow/deny paths (support ≠ moderator ≠ administrator), audit records written for every sensitive action.
6. **Review** — least privilege confirmed; every surface scoped to its group.
7. **Fix** — in services/permissions, never viewset hacks.
8. **Verify** — checklist below.

## Rules (binding)

1. Administrator = the full-control group; staff powers are group-based and least-privileged — a new capability means a deliberate group decision (§4, `security` rule 3).
2. Staff actions go through the same domain services as everyone else — no staff-only shortcuts that bypass validation, transactions, or the audit trail.
3. Every sensitive staff action (role/group changes, store status, refunds, deletions, settings changes, moderation) writes an AuditLog row: who, what, when (§9, §10.7).
4. Marketplace settings changes are explicit, validated, audit-logged, and read by domains through settings services — never hardcoded or scattered.
5. Reports & analytics read from reporting aggregates (§17) — staff dashboards never run heavy live OLTP queries.
6. Staff views are oversight-first: read broadly, write narrowly, confirm destructive actions (`ux-patterns` decision tree 2).
7. Staff UI never exposes secrets, full customer credentials, or payment details beyond what the operation needs (C7, §10).

## Best practices

- Build the audit log view early — it is the safety net for everything else in this skill.
- Django admin for staff internal work; the custom staff dashboard for daily operations — both respect the same groups.
- Group changes themselves are audit-logged (who promoted whom).

## Common mistakes

- Giving a support group moderator powers "for convenience".
- Staff endpoints missing permission classes (public by accident).
- Actions performed outside domain services (skipping transactions/audit).
- Live aggregate queries on big tables freezing the dashboard.
- Settings edited in code instead of through the audited settings surface.

## Verification checklist

- [ ] Group-based permissions enforced; per-group deny paths tested
- [ ] Every sensitive action audit-logged (including group changes)
- [ ] Staff actions use domain services — no bypass paths
- [ ] Settings changes validated + audited; analytics from reporting data
- [ ] Destructive UI actions confirmed (`ux-patterns`); no secrets exposed
