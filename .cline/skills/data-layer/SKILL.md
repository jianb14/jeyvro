---
name: data-layer
description: Rules for data access in the Jeyvro marketplace — use when fetching, mocking, or wiring product, order, or user data, when designing API contracts for the Django backend, when connecting components to data, or when preparing the mock-to-API swap. Covers the frontend accessor pattern in src/data, the planned Django REST contract under /api/v1, and the one-file swap path from mock accessors to the real API.
---

> **Source of truth:** [PROJECT_CONTEXT.md](../../PROJECT_CONTEXT.md) — when anything conflicts, the project context wins.

# Jeyvro Data Layer

One rule above all: **components never fetch and never import mock data directly.** All data flows through async accessor functions in `frontend/src/data/`.

## Architecture (accessors → Django API)

```
React component → accessor (frontend/src/data/*.js)
                     └─ fetch("/api/v1/...") → Django REST Framework
Django (live): apps per domain → PostgreSQL
```

- The mock era is over (C5): every accessor talks to the real Django API. Keep the accessor boundary anyway — it is the single swap/repair point and keeps components framework-agnostic.
- The Vite dev server proxies `/api` → `http://localhost:8000` (Django `manage.py runserver`; see `frontend/vite.config.js`) — same-origin calls, no CORS setup in dev.
- Live accessors: `auth.js`, `products.js` (catalog), `stores.js`, `cart.js`, `wishlist.js`. Shared plumbing (`fetch`, cookies, CSRF, the §8 error convention) lives in `lib/api.js`.

## REST contract (Django, /api/v1 — live)

| Endpoint | Returns |
|---|---|
| `GET /api/v1/catalog/products/?q=&store=&category=&sort=&page=` | `{ count, items: Product[] }` |
| `GET /api/v1/catalog/products/:slug/` | `Product` or `404 { error }` |
| `GET /api/v1/cart/` · `DELETE` (clear) | cart payload (`owner/items/groups/totals`) |
| `POST /api/v1/cart/items` · `PATCH/DELETE /api/v1/cart/items/:id` | the recomputed cart payload |
| `GET/POST /api/v1/wishlist/` · `DELETE /api/v1/wishlist/items/:slug` | `{ count, items }` / item object |
| stores, auth, orders, reviews | designed per-feature under `/api/v1/` (§8 of the project context) |

**Product shape (the frontend contract, mapped in `products.js#mapProduct`):** `id, seed, title, price, originalPrice?, discount?, rating, sold, stock, store, storeSlug, verified?, isNew?, category, categorySlug, image, images[], variants[]`.

## Adding a new data need (today)

1. **Backend first** — the endpoint exists under `/api/v1/` with the §8 envelopes before the UI consumes it.
2. **Add the accessor** in `frontend/src/data/<resource>.js` — Promise-based, mapping API shapes to the component contract (numbers parsed here, never in components).
3. In the component: call the accessor in an event handler/effect; wire loading (Skeleton) / empty (EmptyState) / error (Alert) / success (Toast) per the `ux-patterns` skill.
4. Never let a component import `fetch` directly or reach past its accessor.

## Rules

- New data needs an accessor — never `fetch` inside a component.
- Future endpoints follow the project-context envelopes (`{count, items}`, JSON 404s, `{error}`) — no one-off shapes.
- Accessor files are the single swap point; keep them framework-agnostic (Promises only).

