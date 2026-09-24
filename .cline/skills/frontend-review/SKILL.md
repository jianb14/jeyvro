---
name: frontend-review
description: Review and quality-check frontend changes in the Jeyvro workspace before declaring them done. Use when asked to check, review, verify, or finalize work in frontend/ — covers accessibility (keyboard, ARIA, contrast, touch targets), design system compliance, responsive layout, light plus dark mode, basic performance checks, and mandatory verification by running npm run lint and npm run build in frontend/. Completion is blocked until lint and build both pass.
---

> **Source of truth:** [PROJECT_CONTEXT.md](../../PROJECT_CONTEXT.md) — when anything conflicts, the project context wins.

# Frontend Review

Quality gate for any frontend work in this workspace. Run this **before** declaring frontend changes done — it is a hard requirement, not a suggestion.

## Process

1. Identify the added/changed files under `frontend/src`.
2. If the change touches interactive components, forms, or overlays, read [docs/a11y.md](docs/a11y.md) for detailed patterns.
3. Check every gate below against the actual code — read the files, do not guess.
4. Run the mandatory verification (Gate 4).
5. Output the report in the required format.

## Gate 1 — Accessibility

- [ ] Every interactive element reachable and operable by keyboard (Tab / Shift+Tab / Enter / Space / Escape)
- [ ] Visible focus state (`focus-visible` outline or ring)
- [ ] Icon-only buttons have `aria-label`
- [ ] Form labels associated (`htmlFor`/`id`); errors use `aria-invalid` + `aria-describedby`
- [ ] Overlays: `role="dialog"`, `aria-modal="true"`, Escape closes, body scroll locked, rendered via `createPortal`
- [ ] Status never color-only (icon + text)
- [ ] Touch targets ≥ 44px
- [ ] Heading hierarchy (single h1, no skipped levels)

## Gate 2 — Design system compliance

- [ ] No hardcoded hex/arbitrary color values — moss/sand/night/semantic tokens only (see `design-tokens` skill)
- [ ] `dark:` variants present for all new/changed color, border, and hover classes
- [ ] `cx()` used for class merging (no template literals); named exports; icons only from `Icons.jsx`

## Gate 3 — Responsive

- [ ] Layouts hold at mobile (~360px), tablet (~768px), desktop (~1280px)
- [ ] No horizontal overflow at small widths; grids collapse with `sm:`/`md:`/`lg:` prefixes like the existing pages and grids (`routes/Home.jsx`, `routes/Browse.jsx`)

## Gate 4 — Verification (mandatory)

Run from the `frontend/` directory:

```
npm run lint
npm run build
```

> **Windows note (this machine):** if PowerShell blocks `npm` with an `npm.ps1 ... running scripts is disabled` error, use `npm.cmd` instead (`npm.cmd run lint`, `npm.cmd run build`) — do not change the user's execution policy. When shell output is not visible, redirect output to a temp log file, then read that file to get the real result.

- Both must exit cleanly. Fix every error before finishing.
- **Never claim a command passed without running it.** If a check cannot run (e.g. environment blocked), state that explicitly in the report as "not run" and explain why.

## Gate 5 — Performance basics

Checklist lives in the `frontend-performance` skill — verify each of its checklist items against the diff (dependencies/C3, accessor-only fetching, stable keys, no default memoization, dimensioned media, token-only motion, clean build output). Deep performance work waits for the `performance-skill` trigger (SKILL_ARCHITECTURE §6).

## Report format

```
## Frontend Review Report
- Files reviewed: <list>
- Accessibility: PASS/FAIL — <notes>
- Design system: PASS/FAIL — <notes>
- Responsive: PASS/FAIL — <notes>
- Performance basics: PASS/FAIL — <notes>
- Lint: PASS/FAIL (or NOT RUN + reason)
- Build: PASS/FAIL (or NOT RUN + reason)
- Issues found: <numbered list with file paths>
- Fixes applied: <list>
```
