---
name: frontend-responsive
description: Apply Jeyvro's mobile-first responsive discipline — use when building or changing page layouts, grids, or navigation, when choosing Tailwind breakpoint prefixes, when fixing horizontal overflow or touch-target spacing, or when making anything hold at phone/tablet/desktop widths (~360 / ~768 / ~1280px). Verification verdicts stay with frontend-review Gate 3.
---

> **Source of truth:** [PROJECT_CONTEXT.md](../../PROJECT_CONTEXT.md) — when anything conflicts, the project context wins. Catalog entry: #19 in [SKILL_CATALOG.md](../../SKILL_CATALOG.md).

# Jeyvro Responsive & Mobile-First

One responsibility: **how layouts are authored so they are mobile-first and hold at every width**. Jeyvro serves the Philippine market (PROJECT_CONTEXT §3) — phone-first is the default, not an afterthought.

## Purpose

Every Jeyvro screen works one-handed on a ~360px phone first, then enhances cleanly to tablet and desktop — with no overflow, no squeezed content, and no hover-only affordances.

## When to use

- Building or changing any page layout, grid, or navigation
- Choosing `sm:` / `md:` / `lg:` prefixes (or tempted by `max-*` overrides)
- Fixing horizontal overflow, clipping, or cramped touch targets
- Responsive tables, cards, or media

## When NOT to use

- Verdicts on whether responsive work passes (`frontend-review` Gate 3)
- Breakpoint *behavior* like which feedback pattern shows (`ux-patterns`)
- Touch-target *styling inside primitives* (`frontend-ui` — the ≥44px scale lives there)

## Workflow

1. **Understand** — what must the mobile layout do first? What is the content priority?
2. **Inspect** — check the reference patterns (`routes/Home.jsx`, `routes/Browse.jsx`) and existing grid usage before inventing one.
3. **Plan** — mobile base layout → list the enhancements per breakpoint (`sm`/`md`/`lg`).
4. **Implement** — author the base layer for small screens; add min-width prefixes upward.
5. **Test** — gates (`npm.cmd run lint` / `build`) + manually verify ~360 / ~768 / ~1280.
6. **Review** — `frontend-review` Gate 3.
7. **Fix** — address findings.
8. **Verify** — checklist below.

## Authoring rules (binding)

1. **Base layer = mobile.** Stacked layout first; enhance with `sm:` / `md:` / `lg:`. Never desktop-first with `max-*` overrides.
2. **Reference grids:** page shell `mx-auto max-w-7xl px-4 sm:px-6 lg:px-8`; card grids `grid gap-5 md:grid-cols-2` / `lg:grid-cols-3`.
3. **DOM order = content order.** Layout changes come from flex/grid utilities — never visually reflow reading order between breakpoints.
4. **Touch-first:** targets ≥ 44px, adjacent targets spaced ≥ `gap-2`; every hover affordance has a touch/keyboard equivalent.
5. **Media never overflows:** `max-w-full h-auto` + explicit dimensions or aspect ratio (also prevents layout shift — see `frontend-performance`).
6. **Navigation:** mobile uses the `Drawer` pattern, desktop inline links — one source of truth for nav items, two presentations.
7. **Tables on mobile** scroll horizontally inside a wrapper with a visible affordance — never squeeze columns until they wrap.
8. **No horizontal scroll at ~360px — ever.**

## Best practices

- Test at ~360px *while building*, not after — overflow found late costs the most.
- Prefer grid/flex gaps over fixed widths; let content define height.
- Keep primary actions reachable one-handed (bottom half of mobile screens).

## Common mistakes

- Writing desktop layout then patching with `max-sm:` overrides.
- Hiding content on mobile with `hidden md:block` when it is actually essential.
- Hover-only reveals (tooltips/menus) with no tap path.
- Fixed pixel widths (`w-[320px]`) on flexible containers.
- Breaking heading hierarchy to make mobile text smaller — use type scale, not level swaps.

## Verification checklist

- [ ] ~360 / ~768 / ~1280 all hold — nothing clipped or cramped
- [ ] No horizontal overflow at any width; all media contained
- [ ] Base (unprefixed) classes describe the mobile layout
- [ ] Touch targets ≥ 44px, spaced, primary actions one-handed reachable
- [ ] DOM/reading order logical when layout is linearized
- [ ] Dark mode correct at every width
