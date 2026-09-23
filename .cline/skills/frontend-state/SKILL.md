---
name: frontend-state
description: Decide where state lives in the Jeyvro frontend — use when managing component state, form state, lifting state up, deriving values, putting search/filter/sort/pagination in the URL (useSearchParams), doing optimistic updates, or deciding between local state and a global store. Does not cover how data is fetched (the data-layer skill owns accessors).
---

> **Source of truth:** [PROJECT_CONTEXT.md](../../PROJECT_CONTEXT.md) — when anything conflicts, the project context wins. Catalog entry: #18 in [SKILL_CATALOG.md](../../SKILL_CATALOG.md).

# Jeyvro Frontend State

One responsibility: **where each piece of client state lives** — so no fact has two homes, filters survive navigation, and no state library is added without need. Fetching server data stays with the `data-layer` skill; rendering stays with `frontend-ui`.

## Purpose

Keep state minimal, local by default, and recoverable — the user can refresh, hit Back, or share a link without losing their place, and the mock→API swap never breaks component state.

## When to use

- Adding any `useState` / derived value / form state
- Wiring search, filters, sort, or pagination
- Deciding whether to lift state, use Context, or add a state library
- Optimistic updates and rollback
- Any "where should this value live?" question

## When NOT to use

- Fetching or mocking server data (`data-layer`)
- Loading/empty/error *presentation* (`ux-patterns`)
- New components (`frontend-ui`)

## Workflow

1. **Understand** — what fact changes, and who needs it (this component? siblings? the URL? the server?).
2. **Inspect** — is it server data (→ accessor + status flags) or client state (→ continue)? What state already exists nearby?
3. **Plan** — place it on the ladder below; lowest rung that works wins.
4. **Implement** — controlled inputs, functional updates, URL params for shareable state.
5. **Test** — gates: `npm run lint` + `npm run build` (`npm.cmd` on this machine); interact through the flow.
6. **Review** — `frontend-review` (Gate 5 covers render costs).
7. **Fix** — address findings.
8. **Verify** — checklist below.

## The placement ladder (stop at the first rung that works)

1. **Local `useState`** in the component that owns the interaction.
2. **Lift to the nearest common parent** — only when two siblings genuinely need it.
3. **Derive, never store** — totals, filtered lists, validity: computed during render.
4. **URL = state** for shareable/restorable facts (search `q`, filters, sort, page) via `useSearchParams`.
5. **Server state lives in the accessors** — components keep only loading/empty/error/success flags.
6. **Global store / Context** — only the theme pattern today (`lib/useTheme.js`); anything more needs the owner's approval (C3).

## Rules (binding)

1. Controlled inputs by default (`value` + `onChange`); preserve input on failed submits.
2. One state object per form; field errors clear as the user fixes them.
3. Updates depending on previous state use the functional form (`setQty(prev => prev + 1)`).
4. Never mirror props into state — derive instead.
5. Never store both the source list *and* a hand-computed filtered/total version.
6. Filter/search/sort/pagination state goes in the URL, not component state.
7. Async calls happen in event handlers via accessors — never `setState` directly inside effect bodies (lint rejects it).
8. Optimistic updates only for easily reversible actions; on failure roll back + `Toast` (danger) per `ux-patterns` decision tree 4.
9. No global state library without the owner's explicit approval (C3).

## Best practices

- Name state after what it holds (`selectedVariantId`), not its type (`data`, `flag`).
- Reset transient state (page number, drafts) when its meaning changes — e.g. new search resets to page 1, in event handlers.
- Keep URL params canonical (`?q=shoes&sort=price&page=2`) so links look intentional.

## Common mistakes

- `useState(props.value)` to "initialize" from props — guaranteed sync bugs.
- Storing the filtered list instead of the filter — two sources of truth.
- Component-only filter state — Back/refresh wipes the user's place.
- Reaching for Redux/Zustand/app-wide Context for cart before any real cross-page need exists.
- Duplicating server data into client copies that then drift.

## Verification checklist

- [ ] Every piece of state sits on the lowest ladder rung that works
- [ ] Nothing derived is stored; nothing mirrored from props
- [ ] Search/filter/sort/pagination are URL-driven and survive refresh + Back
- [ ] Form inputs controlled; input preserved on failed submit
- [ ] No direct `setState` inside effect bodies; functional updates where dependent
- [ ] No new state library added (C3)
