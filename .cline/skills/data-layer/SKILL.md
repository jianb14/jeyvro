---
name: data-layer
description: Rules for data access in the Jeyvro marketplace — use when fetching, mocking, or wiring product, order, or user data, when designing API contracts for the Django backend, when connecting components to data, or when preparing the mock-to-API swap. Covers the frontend accessor pattern in src/data, the planned Django REST contract under /api/v1, and the one-file swap path from mock accessors to the real API.
---

> **Source of truth:** [PROJECT_CONTEXT.md](../../PROJECT_CONTEXT.md) — when anything conflicts, the project context wins.

# Jeyvro Data Layer

One rule above all: **components never fetch and never import mock data directly.** All data flows through async accessor functions in `frontend/src/data/`.

## Architecture (mock now → Django later)

```
React component → accessor (frontend/src/data/*.js)
                     ├─ today:   mock array + simulated latency
                     └─ future:  fetch("/api/v1/...") → Django REST Framework
Django (to be built): apps per domain → PostgreSQL
```

- The frontend accessors return Promises and simulate latency (~450ms) so loading/empty/error states are genuinely exercised.
- The Vite dev server proxies `/api` → `http://localhost:8000` (Django `manage.py runserver`; see `frontend/vite.config.js`) — same-origin calls, no CORS setup in dev.

## Planned REST contract (Django, /api/v1)

| Endpoint (planned) | Returns |
|---|---|
| `GET /api/v1/products?q=&store=&category=` | `{ count, items: Product[] }` |
| `GET /api/v1/products/:id` | `Product` or `404 { error }` |
| cart, orders, reviews, auth | designed per-feature under `/api/v1/` (§8 of the project context) |

**Product shape (the current frontend contract — keep identical):** `id, seed, title, price, originalPrice?, discount?, rating, sold, stock, store, verified?, isNew?, category`.

## Connecting a page to data (today)

1. Add/extend accessors in `frontend/src/data/<resource>.js` — Promise-based, with simulated delay.
2. In the component: call the accessor in an effect; wire loading (Skeleton) / empty (EmptyState) / error (Alert) / success (Toast) per the `ux-patterns` skill.
3. State resets triggered by user actions (search, filter changes) happen in **event handlers** — never synchronous setState inside effect bodies (the lint rules reject it).

## The swap (mock → Django API)

1. **Build the Django API first** (app-per-domain, DRF viewsets, envelopes per §8 of the project context).
2. **Frontend:** replace each accessor body in `frontend/src/data/*.js` with `fetch("/api/v1/...")` returning the same shapes (throw on `!res.ok` so error states fire). Components, skeletons, empty states, and error handling stay untouched.
3. If a response shape must change, change it in the accessor — never in the component.

## Rules

- New data needs an accessor — never `fetch` inside a component.
- Future endpoints follow the project-context envelopes (`{count, items}`, JSON 404s, `{error}`) — no one-off shapes.
- Accessor files are the single swap point; keep them framework-agnostic (Promises only).

