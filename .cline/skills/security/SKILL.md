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

The backend is live and session-authenticated, and **§20.1 is shipped** (2026): the project default is **deny by default** (`DEFAULT_PERMISSION_CLASSES = IsAuthenticated`, pinned `SessionAuthentication` — DRF's HTTP Basic default removed), and `tests/test_security_hardening.py::test_every_view_declares_its_own_permissions` walks the URLconf and **fails the gate** when a view class forgets to declare its permissions, so rule 2 below is enforced rather than trusted. Rate limiting is a blanket anon/user default plus `throttle_scope` buckets (`auth`, `register`, `checkout`, `message`) in front of the app-level login lockout (5 failures → 15 min); CORS is an allowlist **with `CORS_ALLOW_CREDENTIALS = True`** (without it, cross-origin session calls fail silently in production). Audit rows exist for refunds, returns/disputes, voucher redemption, store suspension, seller approval, staff role changes, user suspension, catalog moderation, order cancellation and payment failures.

The slice was opened by a real finding: the public tracking endpoint had no permission class and returned the buyer's name, phone, address, goods and the seller's notes to anyone holding a tracking number. Fixed — a bearer token is not an identity (rule 11 below).

`docs/SECURITY_CHECKLIST.md` records all eleven §20.1 items with a verdict and the file + test that proves each. Still open: **§20.2** abuse controls (spam, messaging abuse, suspicious-order detection, inventory abuse) and **§20.3** auditing the remaining sensitive operations (the §19.4 CSV exports are the known unaudited surface); production env values and a **shared cache** for throttling land with the deployment phase (LocMemCache is per-process, so multi-worker deploys need Redis before the rate limits mean anything).

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
10. **Deny by default, and prove it** — a view that does not declare its own permissions is private, and the URLconf guard test fails the gate when one forgets (§20.1).
11. **A bearer token is not an identity** — a public read (tracking number, reference code, public id) returns a *projection* with no buyer PII; the full record belongs to the owner, the fulfilling party and staff (§20.1).

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
| Sensitive data exposure | Serializers declare fields; no secrets in logs (C7, rule 7); public reads return a redacted projection (rule 11) |
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
- [ ] New/changed surface recorded in `docs/SECURITY_CHECKLIST.md` with the test that proves it
