# Jeyvro Token Reference

Source of truth: `frontend/src/index.css`. Update this file when tokens change.

## Brand — moss (calm, desaturated green)

| Token | Hex |
|---|---|
| moss-50 | #f3f7f0 |
| moss-100 | #e4ecdc |
| moss-200 | #cad9bf |
| moss-300 | #a7c096 |
| moss-400 | #84a471 |
| moss-500 | #678a53 |
| moss-600 | #4f6d3f |
| moss-700 | #405734 |
| moss-800 | #35462c |
| moss-900 | #2d3b27 |
| moss-950 | #151f10 |

## Warm neutral — sand

| Token | Hex |
|---|---|
| sand-50 | #faf9f6 |
| sand-100 | #f2f0ea |
| sand-200 | #e5e1d6 |
| sand-300 | #d3ccbb |
| sand-400 | #b7ad97 |
| sand-500 | #a1937a |
| sand-600 | #89795f |
| sand-700 | #6e614c |
| sand-800 | #574e3f |
| sand-900 | #474035 |
| sand-950 | #2a261f |

## Dark surfaces — night (dark mode only)

| Token | Hex |
|---|---|
| night-700 | #2e3626 |
| night-800 | #232a1b |
| night-900 | #1a2015 |
| night-950 | #12160e |

## Semantic — success / warning / danger / info

Each is a full 50–950 ramp in `index.css`. Status use only:
- success-500 #4a8a53 · warning-500 #c28c40 · danger-500 #c26b62 · info-500 #5c8fb9
- Destructive buttons: `bg-danger-600 text-white hover:bg-danger-700`

## Shadows

| Token | Use |
|---|---|
| shadow-soft | resting cards, primary buttons |
| shadow-lift | hover elevation |
| shadow-pop | dialogs, elevated cards |
| shadow-dropdown | menus, popovers |

## Animations

`animate-fade-in` · `animate-slide-up` · `animate-scale-in` · `animate-indeterminate` · `animate-slide-in-left` · `animate-slide-in-right`

Keyframes live inside `@theme` in `index.css`.

## Fonts

- `font-sans` → Outfit (body)
- `font-display` → Plus Jakarta Sans (headings, titles)

## Canonical pairings (from Button.jsx / Modal.jsx)

- Primary CTA: `bg-moss-600 text-white shadow-soft hover:bg-moss-700 active:bg-moss-800`
- Focus: `outline-offset-2 outline-moss-600/60 focus-visible:outline-2`
- Dialog: `rounded-2xl border border-sand-200 bg-white shadow-pop dark:border-night-800 dark:bg-night-900`
- Backdrop: `bg-night-950/50 backdrop-blur-sm`
