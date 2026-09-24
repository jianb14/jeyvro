---
name: frontend-ui
description: Build, edit, or refactor React components in the Jeyvro frontend (React 19 + Vite + Tailwind CSS v4, plain JSX). Use when creating or changing anything under frontend/src — components/ui or components/layout. Enforces project conventions: named exports only, cx() utility, forwardRef/useId on form controls, icons only from Icons.jsx, createPortal overlays with Escape handling, ARIA and keyboard support, and mandatory dark mode variants.
---

> **Source of truth:** [PROJECT_CONTEXT.md](../../PROJECT_CONTEXT.md) — when anything conflicts, the project context wins.

# Jeyvro Frontend UI

Instructions for building and editing React components in this workspace's `frontend/`.

## 1. Stack facts (do not assume otherwise)

- **Tailwind CSS v4, CSS-first config.** All design tokens live in `frontend/src/index.css` inside `@theme`. There is **no** `tailwind.config.js` — never create one.
- **Dark mode is class-based** (`@custom-variant dark (&:where(.dark, .dark *))`). Use `dark:` prefixed classes. Theme is persisted in `localStorage` under `jeyvro-theme` and initialized by an inline script in `frontend/index.html`.
- **Plain JavaScript (JSX), no TypeScript.** Props are destructured with inline defaults.
- Fonts: `font-sans` = Outfit (body), `font-display` = Plus Jakarta Sans (headings/titles).

## 2. File and export conventions

- UI primitives: `frontend/src/components/ui/<Name>.jsx`, one primary component per file, **named export**: `export function Card() {...}`. Never add `export default` to components (the only default export is the `App.jsx` entry).
- Related sub-components may share a file as additional named exports (see `Card.jsx`: Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter).
- Layout components: `frontend/src/components/layout/`.
- Class merging: always use `cx` from `lib/cx.js`. Never build class strings with template literals.
- **Icons: only from `frontend/src/components/ui/Icons.jsx`.** Never add an icon library. Icons take a numeric `size` prop and `className`.

## 3. Component anatomy (match existing patterns)

Follow `Button.jsx` / `Card.jsx`:

- Variant/size class maps as top-level consts above the component:
  ```jsx
  const VARIANTS = { primary: "bg-moss-600 text-white shadow-soft hover:bg-moss-700 ...", ... };
  const SIZES = { sm: "h-8 ...", md: "h-10 ...", lg: "h-12 ..." };
  ```
- Merge classes in this order: base → `VARIANTS[variant]` / `SIZES[size]` → **`className` last** so callers can override.
- Form controls: wrap with `forwardRef`, generate ids with `useId`, accept `className` (see `Input.jsx`, `Checkbox.jsx`, `Textarea.jsx`).
- Buttons: default `type="button"`; support `loading` (renders `Spinner`, disables); include `focus-visible:outline-2 outline-offset-2` and `disabled:pointer-events-none disabled:opacity-50`.
- Spread remaining props onto the root element (`{...props}`) after explicit ones.

## 4. Styling rules

- **Design tokens only.** Use moss/sand/night/semantic scales, `shadow-soft/lift/pop/dropdown`, and `animate-*` tokens. Never hardcode hex values or arbitrary bracket values (`bg-[#...]`) when a token exists — see the `design-tokens` skill.
- **Every component must have dark mode classes** for text, background, border, and hover/active states. A component without `dark:` variants is incomplete.
- Visible focus state required, consistent with `Button.jsx`: `outline-offset-2 outline-moss-600/60 focus-visible:outline-2`.
- Radius scale: `rounded-lg` (small controls), `rounded-xl` (md controls), `rounded-2xl` (cards/dialogs).
- Interactivity: touch target ≥ 44px (`h-10`/`h-11` + padding), `transition-colors duration-150`.

## 5. Overlays (Modal, Drawer, DropdownMenu, CommandPalette)

- Render through `createPortal` from `react-dom`.
- Lock scroll while open (`document.body.style.overflow = "hidden"` in an effect, restore on cleanup).
- Close on Escape via a document `keydown` listener, removed on cleanup.
- Backdrop `aria-hidden="true"`; panel `role="dialog" aria-modal="true"`.
- Icon-only close buttons need `aria-label`.

## 6. Accessibility baseline

- Associate labels with inputs (`htmlFor` + `useId`), wire `aria-invalid` and `aria-describedby` for errors; never convey status by color alone (icon + text).
- Heading hierarchy: one h1 per page, section titles h2, card titles h3 (matches `CardTitle`).

## 7. Validate your work

- The design-system playground was **retired in Phase 7** (no `src/sections/`, no `pages/DesignSystemPage.jsx`). A new or changed primitive is validated where it actually ships:
  - it must be used by a real route or feature — an unused primitive is not done;
  - non-trivial behaviour gets a Vitest test (`components/ui/Button.test.jsx` is the reference);
  - the `frontend-review` gates (a11y, dark mode, tokens, responsive) apply as usual.

Before declaring a component done, verify it against [docs/checklist.md](docs/checklist.md) and run the `frontend-review` skill (lint + build are mandatory).

Working on a multi-component feature or page instead of a single component? Use the `frontend-feature` skill (reuse-first pipeline) and the `ux-patterns` skill (which states to wire). Project orientation and the component inventory live in `jeyvro-project`.
