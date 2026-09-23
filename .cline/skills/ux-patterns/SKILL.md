---
name: ux-patterns
description: Choose the right UX behavior when building Jeyvro frontend UI — use when deciding between toast vs alert vs modal confirmation, when wiring loading, empty, or error states, when designing form submission and validation UX, when picking placement for feedback, or when judging motion and interaction polish. Grounded in the existing Jeyvro components (Alert, Toast, Modal, EmptyState, Skeleton, Spinner, Progress) and the calm-by-design philosophy.
---

> **Source of truth:** [PROJECT_CONTEXT.md](../../PROJECT_CONTEXT.md) — when anything conflicts, the project context wins.

# Jeyvro UX Patterns

Behavior decisions for Jeyvro UI — what to show, when, and where. Pairs with the `frontend-ui` skill (how to build it) and `design-tokens` (how to style it).

## Golden rules

1. **Never leave the user guessing.** Every async action gets a pending → result state. Every empty list gets an `EmptyState`. Every failure gets visible, specific feedback.
2. **Calm by design.** No gradients, no bouncing, no confetti. Motion uses the existing tokens (`animate-fade-in`, `animate-slide-up`, `animate-scale-in`) at their baked-in durations. If an animation draws attention to itself, remove it.
3. **Feedback lives near the action.** Inline (`Alert`) next to the thing that failed; `Toast` for outcomes of actions initiated elsewhere; never a modal just to say "success".
4. **Destructive actions get a `Modal` confirm** with a specific title ("Delete address?") — never a bare click, never browser `confirm()`.

## Async states (wire all of them)

| State | Use | Notes |
|---|---|---|
| Loading (first) | `Skeleton` matching final layout | Prefer over `Spinner` for known shapes; `Spinner` only for unknown-duration in-place waits or button `loading` |
| Loading (action) | Button `loading` prop | Disables the button; never double-fire |
| Empty | `EmptyState` with icon + title + description + one action | "No results" must offer a next step (clear filters), not a dead end |
| Error | Inline `Alert tone="danger"` with a specific message | Say what failed and what to try; "Something went wrong" alone is not enough |
| Success | `Toast` (transient) | Auto-dismiss ~4s; the record itself shows the new state |

## Feedback chooser

| Situation | Reach for |
|---|---|
| Field-level validation problem | Inline error under the input (`Input` `error` prop) |
| Form-level failure (e.g. submit rejected) | `Alert tone="danger"` above/below the form |
| Action succeeded (saved, added to cart, copied) | `Toast` via `useToasts()` from `lib/useToasts.js` |
| Destructive or irreversible action | `Modal` confirm with explicit verb + object, destructive `Button variant="destructive"` |
| Ongoing status (upload %, processing) | `Progress` (determinate with value; `indeterminate` only when % is unknown) |
| Persistent status (order state, account state) | `Badge` / `OrderStatusBadge` — never a toast for persistent state |
| Hint on hover/focus | `Tooltip` — supplementary info only, never the only place an essential label lives |

## Form UX

- Validate on blur/submit, not on every keystroke; clear errors as the user fixes them.
- Keep the submit button enabled and show what's missing on submit (disabling hides the reason nothing happened). Exception: network actions may use `loading` to prevent double submits.
- Preserve user input on failure — never clear a form because submission failed.
- Required vs optional: mark the rare optional field, not every required one.
- Errors use `aria-invalid` + `aria-describedby` (see `frontend-review` skill, Gate 1).

## Empty / zero-data UX

- First-use empty states teach: explain the value + one primary action ("Add your first address").
- No-results empty states offer a reset ("Clear filters").
- Never render a blank region — a skeleton or empty state always beats white space.

## Detailed decision trees

See [docs/decisions.md](docs/decisions.md) when the situation is ambiguous (mixed feedback, nested overlays, optimistic updates).
