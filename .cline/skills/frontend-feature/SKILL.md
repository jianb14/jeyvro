---
name: frontend-feature
description: Build a complete Jeyvro frontend feature, page, section, or flow end-to-end — use when asked to create a new page, dashboard, form flow, product area, or any UI composed of multiple components. Runs the reuse-first pipeline, wires routes and data accessors, wires all UX states, and finishes with the mandatory frontend-review verification (lint + build). Completion is blocked until lint and build pass.
---

> **Source of truth:** [PROJECT_CONTEXT.md](../../PROJECT_CONTEXT.md) — when anything conflicts, the project context wins.

# Frontend Feature Pipeline

End-to-end workflow for features/pages in the Jeyvro `frontend/`. Orientation and inventory live in the `jeyvro-project` skill; component rules in `frontend-ui`; tokens in `design-tokens`; behavior decisions in `ux-patterns`.

## Step 1 — Clarify scope (before writing code)

Ask only what you cannot infer: which user goal this serves, what data exists (real vs demo), and where it will be seen. If the request maps to an existing section, extend it instead of duplicating.

## Step 2 — Reuse-first inventory (mandatory)

List the existing components that already solve parts of this feature — check the inventory in the `jeyvro-project` skill. **Rules:**

- A primitive already exists → compose it; never re-implement a button, input, modal, or toast.
- Nothing fits → build a new primitive in `components/ui/` following the `frontend-ui` skill, then use it.
- New compositions specific to this feature (e.g. `CheckoutSummary`) go in `components/ui/` too if reusable, or stay local to the feature section if not.

## Step 3 — Compose the layout

- Follow existing composition patterns: `MarketplaceSection.jsx` (product grid + cart + checkout flow) and `WorkspaceSection.jsx` (upload + drawer + command palette) are the reference implementations.
- Page grid: `mx-auto max-w-7xl px-4 sm:px-6 lg:px-8`; card grids collapse `grid gap-5 md:grid-cols-2` / `lg:grid-cols-3`.
- Data flows through async accessors from `src/data/` (see the `data-layer` skill) — never fetch inside components, never import mock arrays directly.
- States per `ux-patterns`: loading (Skeleton), empty (EmptyState), error (Alert), success (Toast) — the accessors simulate latency, so these states genuinely fire.
- Where state lives → `frontend-state` skill · responsive/mobile-first authoring → `frontend-responsive` skill · speed discipline → `frontend-performance` skill.

## Step 4 — Route and showcase

1. **Marketplace pages:** create `src/routes/<Name>.jsx` (see `routes/Home.jsx` as the reference), add a `<Route>` in `App.jsx`, and link it from the app header.
2. **New UI primitives** (if any) go in `components/ui/` per the `frontend-ui` skill, showcased in `src/sections/`, and registered in `pages/DesignSystemPage.jsx` (`NAV_SECTIONS` **and** page body).

## Step 5 — Review (mandatory gate)

Run the `frontend-review` skill before declaring done: accessibility gates, design-system compliance, responsive check, and `npm run lint` + `npm run build` (use `npm.cmd` on this Windows machine). **No feature is "done" with failing lint or build.**

Full per-step checklist: [docs/feature-checklist.md](docs/feature-checklist.md)
