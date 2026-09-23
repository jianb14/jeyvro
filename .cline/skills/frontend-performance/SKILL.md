---
name: frontend-performance
description: Keep the Jeyvro frontend fast by discipline — use when adding imports or dependencies, rendering lists, deciding on memo/useMemo/useCallback/React.lazy, handling images and layout shift, writing effects, or checking build output for bundle regressions. Deep profiling beyond these rules waits for the performance-skill trigger (SKILL_ARCHITECTURE §6).
---

> **Source of truth:** [PROJECT_CONTEXT.md](../../PROJECT_CONTEXT.md) — when anything conflicts, the project context wins. Catalog entry: #20 in [SKILL_CATALOG.md](../../SKILL_CATALOG.md).

# Jeyvro Frontend Performance

One responsibility: **everyday speed discipline** — the rules that keep the app fast by default, so the pre-launch `performance-skill` trigger (SKILL_ARCHITECTURE §6) never fires from preventable mistakes. Deep profiling is out of scope until that trigger fires.

## Purpose

Jeyvro stays fast on real Philippine mobile connections: no accidental dependency bloat, no render storms, no layout shift from lazy images, no motion that costs frames.

## When to use

- Adding any import or (with approval) dependency
- Rendering or re-ordering lists
- Tempted by `memo` / `useMemo` / `useCallback` / `React.lazy`
- Placing images or media
- Writing effects or animations
- Reading `npm run build` output

## When NOT to use

- Pass/fail review verdicts (`frontend-review` Gate 5 runs this checklist)
- Token-driven motion choices (`design-tokens` / `ux-patterns` motion budget)
- Deep profiling, caching strategy, or backend performance (future `performance-skill` / backend skills)

## Workflow

1. **Understand** — what changed that could affect speed: dependencies? render count? media? effects?
2. **Inspect** — check existing patterns first; read the current `npm run build` output as the baseline.
3. **Plan** — apply the rules below; flag anything that needs `React.lazy` or code-splitting.
4. **Implement** — stable keys, no default memoization, dimensioned images, lean effects.
5. **Test** — gates: `npm.cmd run lint` / `build`; compare build output against the baseline.
6. **Review** — `frontend-review` Gate 5.
7. **Fix** — address findings or measured regressions.
8. **Verify** — checklist below.

## Rules (binding)

1. **Dependencies:** no new runtime dependency without the owner's approval (C3); imports stay within existing libraries. Every import ships to users.
2. **Data:** fetching only via accessors in effects/handlers — never in render, never with direct `setState` inside effect bodies (`data-layer` rules).
3. **Lists:** stable, unique `key`s (never array index for reorderable/filterable data).
4. **Memoization:** `memo` / `useMemo` / `useCallback` only with a measured reason (known-slow render, referential-dependency problem) — never by default.
5. **Images/media:** explicit dimensions or aspect ratio (no layout shift); lazy-load only below-fold media (`loading="lazy"`).
6. **Code-splitting:** `React.lazy` per heavy *route-level* section only when genuinely heavy — not per small component.
7. **Effects:** no per-frame style mutations; clean up listeners/observers; effects own *synchronization*, not derived data.
8. **Motion:** existing `animate-*` tokens only — they are already budgeted (`ux-patterns` motion budget).
9. **Bundle honesty:** `npm run build` must show no unexpected new large chunks; investigate regressions before finishing.

## Best practices

- Record the baseline build size before a feature; compare after — regressions are visible, not vibes.
- Real mobile devices/CPUs, not only a fast desktop dev machine.
- Cheap by default: derive in render before reaching for `useMemo`.

## Common mistakes

- `memo()`-wrapping everything "for performance" — adds comparison cost and code noise with no measured win.
- Importing a library for one function (a date format, a class merge) instead of writing it or using `lib/`.
- Images with no dimensions — the page jumps as they load (Cumulative Layout Shift).
- `React.lazy` for tiny components — split overhead exceeds the savings.
- Index keys on filterable lists — wrong-item bugs that also cost reconciliation.

## Verification checklist

- [ ] No new runtime dependency without approval (C3); imports minimal
- [ ] Fetching only via accessors in effects/handlers
- [ ] Stable `key`s on all lists; memoization only with measured reason
- [ ] Media dimensioned (no layout shift); below-fold media lazy
- [ ] Effects clean up after themselves; no per-frame mutations
- [ ] `npm run build` clean — no unexpected chunk regressions vs. baseline
