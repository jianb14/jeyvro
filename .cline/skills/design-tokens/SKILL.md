---
name: design-tokens
description: Apply the Jeyvro design system when styling frontend UI. Use when choosing colors, shadows, radii, fonts, or animations in frontend/src, editing the @theme tokens in frontend/src/index.css, adding new design tokens, or fixing hardcoded hex/arbitrary values. Covers moss/sand/night palettes, semantic colors (success, warning, danger, info), soft shadows, animation tokens, light-to-dark mappings, and Tailwind CSS v4 CSS-first configuration.
---

> **Source of truth:** [PROJECT_CONTEXT.md](../../PROJECT_CONTEXT.md) — when anything conflicts, the project context wins.

# Jeyvro Design Tokens

Rules for using the design system defined in `frontend/src/index.css` (`@theme`, Tailwind CSS v4).

## Hard rules

1. **Never hardcode hex/rgb colors or arbitrary values** (`bg-[#4f6d3f]`, `text-[#2a261f]`) when a token exists.
2. **Never create `tailwind.config.js`** — this is Tailwind v4 CSS-first config; tokens live in the `@theme` block of `frontend/src/index.css`.
3. New tokens are added **only** as new `--color-*` / `--shadow-*` / `--animate-*` variables inside `@theme`, following the existing naming (`--color-<scale>-<50..950>`).
4. Every color pairing needs a `dark:` equivalent. There is no dark theme without one.

## Palette roles

| Scale | Role |
|---|---|
| `moss` (brand green) | Primary actions, links, active/selected states, focus outlines. CTA pairing: `bg-moss-600 text-white`, hover `bg-moss-700`, active `bg-moss-800`. |
| `sand` (warm neutral) | Light mode neutrals: page bg `sand-50`, headings `sand-900`, body `sand-500/600`, borders `sand-200/300`, hover fills `sand-100`. |
| `night` (dark surfaces) | Dark mode only: page `dark:bg-night-950`, cards `dark:bg-night-900`, borders `dark:border-night-800`, hover fills `dark:bg-night-800`. |
| `success` / `warning` / `danger` / `info` | Status only — never decoration. `danger-600` drives destructive buttons. |

## Light → dark mapping (use these exact pairs)

| Light | Dark |
|---|---|
| `bg-sand-50` (page) | `dark:bg-night-950` |
| `bg-white` (cards/dialogs) | `dark:bg-night-900` |
| `text-sand-900` (headings) | `dark:text-sand-100` |
| `text-sand-500` / `text-sand-600` (body/muted) | `dark:text-sand-400` / `dark:text-sand-300` |
| `border-sand-200` / `border-sand-300` | `dark:border-night-800` / `dark:border-night-700` |
| `hover:bg-sand-100` | `dark:hover:bg-night-800` |

## Other tokens

- **Shadows:** `shadow-soft` (resting), `shadow-lift` (hover), `shadow-pop` (dialogs/elevated cards), `shadow-dropdown` (menus).
- **Animations:** `animate-fade-in`, `animate-slide-up`, `animate-scale-in` (dialogs), `animate-slide-in-left/right` (drawers), `animate-indeterminate` (progress). Duration/easing are baked into the tokens — do not add one-off `animate-[...]` values.
- **Radius:** `rounded-lg` (sm) / `rounded-xl` (md) / `rounded-2xl` (cards, dialogs).
- **Type:** `font-display` for headings/titles, `font-sans` for everything else.
- **Selection/dark variant:** `.dark` class on `<html>`; the custom variant is already defined in `index.css`.

## Adding or changing tokens

1. Edit only the `@theme` block in `frontend/src/index.css`.
2. Follow naming: `--color-<scale>-<50..950>`; semantic scales keep the full 50–950 ramp.
3. Update [docs/palette.md](docs/palette.md) so the reference stays truthful.
4. Verify with `npm run build` in `frontend/`.
