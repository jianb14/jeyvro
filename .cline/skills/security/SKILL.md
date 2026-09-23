---
name: security
description: Enforce Jeyvro authentication, authorization, and backend security — use when setting up login/sessions/JWT, password policy, rate limiting, DRF permission classes, object-level ownership checks, staff groups, IDOR protection, CORS/CSRF, secrets handling, or audit logging, and whenever touching any auth or permission code. Mandatory reading for backend-api, backend-feature, deployment, and any admin work.
---

> **Source of truth:** [PROJECT_CONTEXT.md](../../PROJECT_CONTEXT.md) — when anything conflicts, the project context wins. Catalog entry: #10 in [SKILL_CATALOG.md](../../SKILL_CATALOG.md).

# Jeyvro Security — Auth, Permissions & Hardening

One responsibility: **how Jeyvro decides who you are and what you may touch** — the single home for all authn/authz/hardening patterns (PROJECT_CONTEXT §10). Login *screens* belong to `frontend-feature`; production secrets rotation belongs to `deployment`.

## Purpose

Every request is verified server-side: the backend — never the frontend — decides prices, payments, inventory, roles, and ownership (§10.1).

## Current honest state

No backend exists yet (C5). The first security tasks with the scaffold: the auth decision (sessions vs JWT), then permission infrastructure **before the first domain endpoint ships**.

## When to use

- Auth setup (session/JWT decision, password policy, rate limiting on auth endpoints)
- DRF permission classes, object-level ownership checks, staff group design
- CORS/CSRF, secrets handling, audit logging of sensitive actions
- Reviewing any change that touches auth, roles, ownership, or money paths

## When NOT to use

- Login/registration UI (`frontend-feature`) · host-level infra (`deployment`) · modeling users (`backend-core` owns models; this skill owns their permission behavior)

## Workflow

1. **Understand** — what data/action is protected? Who legitimately needs it (role + ownership)?
2. **Inspect** — existing permission classes, groups, and ownership patterns; read the current enforcement before changing it.
3. **Plan** — permission class + object-level check + audit points; write the deny-case test first.
4. **Implement** — least privilege; deny until explicitly allowed.
5. **Test** — 401 unauthenticated, 403 wrong role, 403/404 wrong owner — every path (§11).
6. **Review** — every touched endpoint: explicit permission class + object check + audit trail.
7. **Fix** — a permission gap is a launch blocker, not a TODO.
8. **Verify** — checklist below.

## Rules (binding)

1. **The backend validates everything security-sensitive** — prices, payments, inventory, permissions. Frontend checks are UX, never security (§10.1, §14.6).
2. Every endpoint declares an explicit permission class; object-level ownership checks throughout — sellers touch only their store, customers only their own orders.
3. Staff power is group-based (support/moderator/admin) and least-privileged — never a blanket `is_staff` free-for-all (§4).
4. IDOR protection: every object fetch re-verifies ownership — "does order X belong to *this* user?" (§10.3).
5. Passwords use Django's hashing; no custom crypto; auth endpoints are rate-limited (§10.2).
6. CORS is an explicit allowlist — `*` never in production; CSRF enabled wherever sessions apply (§10.4).
7. Secrets live only in `.env` — never committed, never in logs or chat output (C7, §10.5).
8. Sensitive staff actions (role changes, refunds, deletions, settings changes) write AuditLog rows (§9, §10.7).
9. Modifying any auth/authz code requires re-reviewing the whole permission surface touched — not just the diff line.

## Best practices

- Deny by default: `DEFAULT_PERMISSION_CLASSES = IsAuthenticated` project-wide; opt out per-endpoint deliberately.
- One shared object-permission class (e.g. `IsStoreOwner`) reused across domains — never re-implemented per viewset.
- Test the **deny** path for every permission — the deny path is the product.

## Common mistakes

- Trusting an ID from the client without an ownership check (IDOR).
- Serializing `is_staff`/role fields to non-staff users.
- Checking the role in the frontend and calling it secured.
- Adding an endpoint and forgetting the permission class.
- Logging tokens or secrets while "debugging".

## Threat coverage map (OWASP index)

The patterns above (plus `backend-core`/`backend-api`/`backend-feature` rules) cover the OWASP basics — use this map when reviewing any change for a specific threat:

| Threat | Where it is enforced |
|---|---|
| Broken access control / IDOR | Object-level ownership checks (rule 2, 4) + deny-path tests |
| Injection (SQL) | ORM-only rule (`backend-core` rule 8) — no string-built SQL |
| XSS | React escaping by default; no `dangerouslySetInnerHTML`; ORM-templated Django responses; uploads sanitized (§8) |
| CSRF | Django middleware + session policy (rule 6) |
| CORS misconfig | Explicit allowlist, never `*` in prod (rule 6; `deployment` enforces in env) |
| Auth failures | Password hashing, rate limiting on auth endpoints (rule 5) |
| Sensitive data exposure | Serializers declare fields; no secrets in logs (C7, rule 7) |
| Broken file uploads | Type/size validation + storage rules (§8; `marketplace-catalog` rule 5) |
| Rate/abuse | Throttling on auth + heavy public endpoints (`backend-api`) |
| Missing audit | AuditLog on sensitive actions (rule 8) |

New threat classes get added here first, then enforced in the owning skill.

## Verification checklist

- [ ] Explicit permission class on every touched endpoint; deny path tested
- [ ] Object-level ownership verified per request
- [ ] Staff groups least-privileged; sensitive actions audit-logged
- [ ] No secrets in code/logs/diffs; CORS allowlist correct
- [ ] Auth endpoints rate-limited; password handling default
- [ ] Allow **and** deny paths covered by tests
