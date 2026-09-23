---
name: performance-skill
description: Measure and optimize Jeyvro API, database, and caching performance — use when diagnosing slow endpoints or pages, fixing N+1 queries, adding or verifying indexes, introducing caching, tuning pagination, or optimizing image/media serving on the backend. The fired deep-performance split (SKILL_ARCHITECTURE §6); the frontend-side counterpart is the frontend-performance skill.
---

> **Source of truth:** [PROJECT_CONTEXT.md](../../PROJECT_CONTEXT.md) — when anything conflicts, the project context wins. Catalog entry: #27 in [SKILL_CATALOG.md](../../SKILL_CATALOG.md).

# Jeyvro Performance — API · Database · Caching

One responsibility: **measured optimization of the server side** — endpoints, queries, caching, and media serving. Client-side runtime belongs to `frontend-performance`; schema *rules* (indexes at modeling time) to `backend-core`.

## Purpose

Jeyvro stays fast as the marketplace grows: endpoints respond on real PH mobile connections, the database stops doing stupid work, and caching is deliberate — never a mystery cache.

## Current honest state

No Django exists yet (C5) — nothing to profile. These rules bind from the scaffold onward; the modeling-time rules (indexes on browse paths, Decimal, constraints) already live in `backend-core`.

## When to use

- A slow endpoint/page (measured, not vibes)
- N+1 suspicion; query plans; index decisions
- Introducing caching for product detail / category lists (§17)
- Pagination and throttling tuning; image/media serving efficiency

## When NOT to use

- Frontend render/bundle work (`frontend-performance`) · deciding indexes *while modeling* (`backend-core` rule 5 — this skill verifies them in action) · speculative optimization with no number

## Workflow

1. **Understand** — what is slow, for whom, since when? (endpoint, query, page?)
2. **Inspect** — measure first: query counts (`django-debug-toolbar`/logging), timings, `EXPLAIN ANALYZE` on the offending query; find the baseline.
3. **Plan** — the smallest change that fixes the measured problem: query shape → index → cache (in that order).
4. **Implement** — fix querysets (`select_related`/`prefetch_related`), add the justified index/cache, tighten serializer fields.
5. **Test** — the regression test proves the N+1/count is gone; full gates pass; compare timings against the baseline.
6. **Review** — no correctness traded for speed (constraints/transactions untouched); cache invalidation reviewed.
7. **Fix** — iterate on measurement, never on feeling.
8. **Verify** — checklist below.

## Rules (binding)

1. **No optimization without a measurement** — name the baseline (queries, ms) before changing anything.
2. Fix N+1 at the queryset layer (`select_related` for FKs, `prefetch_related` for M2M/reverse) — not by caching symptoms.
3. New indexes require `EXPLAIN` evidence; verify they are actually used (§9 indexes are planned at modeling — this is their runtime audit).
4. Caching only the §17 hot paths (product detail, category lists) with explicit invalidation on save; **never cache per-user data in shared caches**.
5. Every list endpoint stays paginated (`{count, items}`, §8) — unbounded queries are bugs, not features.
6. Throttling protects heavy public endpoints (search, auth) — configured with `security`, not ad hoc.
7. Media: thumbnails/generated sizes served via storage/CDN (§17) — never ship originals to phones.
8. Caching/optimization never bypasses the money rules: totals, stock, and permissions are still computed fresh server-side (§6, §10.1).

## Best practices

- Re-measure after every change; keep a small perf log (problem → baseline → fix → result).
- Optimize the browse path first (home, category, product detail) — that is where every customer goes.
- `only()`/`values()`/lean serializers for list endpoints; full serializers for detail.

## Common mistakes

- Caching a queryset that still executes N+1 — the cache memorizes the slowness.
- Adding indexes nobody's query uses (write cost, zero win).
- Shared-cache poisoning with per-user (cart, wishlist) data.
- "Optimizing" by removing validation/constraints — correctness is not a rounding error.
- Trusting a fast dev machine with 200 rows; test with realistic seed volume.

## Verification checklist

- [ ] Baseline measured and recorded before any change
- [ ] N+1 fixed at the queryset layer; query count regression-tested
- [ ] Indexes evidence-backed (`EXPLAIN`); cache invalidation correct
- [ ] Per-user data never shared-cached; money math still server-fresh
- [ ] Pagination/throttling intact; media served in right sizes
- [ ] Gates pass; timings improved vs. baseline
