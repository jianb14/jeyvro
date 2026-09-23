---
name: backend-api
description: Design and implement the Jeyvro REST API with Django REST Framework — use when creating or changing endpoints under /api/v1, writing or changing serializers, viewsets, routers, request validation, pagination, error envelopes, or status codes, or aligning the API with the frontend data contract. Does not cover models/migrations (backend-core), permission patterns (security), or domain business rules (backend-feature).
---

> **Source of truth:** [PROJECT_CONTEXT.md](../../PROJECT_CONTEXT.md) — when anything conflicts, the project context wins. Catalog entry: #9 in [SKILL_CATALOG.md](../../SKILL_CATALOG.md).

# Jeyvro Backend API — DRF Layer

One responsibility: **the HTTP contract** — how requests come in, how they are validated, and how responses go out (§8). Data modeling lives in `backend-core`; who may call what in `security`; what the business does in `backend-feature`.

## Purpose

A versioned, predictable JSON API: every input validated server-side, every response in a known envelope, and a contract the frontend accessors mirror without surprises.

## Current honest state

No endpoints exist yet — the API is designed here first, then mirrored by the `frontend/src/data/` accessors (the `data-layer` skill). The Vite dev proxy already targets Django on port 8000.

## When to use

- Creating/changing endpoints, viewsets, routers under `/api/v1`
- Serializers: declared fields, nested reads, request validation
- Envelopes, pagination, JSON 404s, status codes
- Aligning response shapes with the frontend contract

## When NOT to use

- Models/migrations (`backend-core`) · permission design (`security` — this skill *applies* it) · domain rules (`backend-feature`) · frontend accessors (`data-layer`)

## Workflow

1. **Understand** — which frontend flow consumes this endpoint? What does the data-layer contract already promise?
2. **Inspect** — existing serializers/viewsets in the domain; the §8 envelopes; existing patterns before new ones.
3. **Plan** — route, method, serializer, permission (with `security`), envelope, status codes; new shapes are written into the contract first.
4. **Implement** — thin viewset; validation in serializers; business logic called from the service layer, never inside views.
5. **Test** — DRF request tests: happy path, validation failure (`{error, field_errors?}`), auth denied, not found (JSON 404).
6. **Review** — contract mirror check (shapes identical to the data-layer promise); no raw model fields exposed.
7. **Fix** — contract drift is fixed on both sides in one change — never silently on one.
8. **Verify** — checklist below.

## Rules (binding)

1. Versioned `/api/v1/`, JSON only — HTML errors never leave Django, JSON 404s included (§8).
2. Model fields are **never** exposed without a serializer; serializers declare fields explicitly.
3. Envelopes: list → `{count, items}`; single → object; error → `{error, detail?, field_errors?}` — one-off shapes forbidden (§8).
4. **All request validation is server-side** — serializer + model constraints; frontend validation is UX only (§10.1).
5. Views stay thin: parse → validate → call service → serialize. Business logic lives in service layers, testable without HTTP (§8).
6. Every viewset gets an explicit permission class (see the `security` skill); nothing ships "public" by accident.
7. Status codes are honest: 400 validation, 401/403 auth, 404 missing, 201 created — never 200 with an error body.
8. The API mirrors the data-layer contract — shapes are defined once; drift is a bug fixed immediately.

## Best practices

- Separate read and write serializers when shapes diverge — don't overload one.
- Nested writes are handled in services, not serializer gymnastics.
- Pagination on every list endpoint from day one — `{count, items}` depends on it.

## Common mistakes

- Trusting client-computed totals/prices from the request body — recompute on the backend, always (§6).
- `fields = "__all__"` exposure of model internals.
- Returning HTML 404/500 pages to API consumers.
- Business logic accumulating inside viewsets until untestable.
- Changing a response shape without updating the frontend accessor contract.

## Verification checklist

- [ ] Endpoint under `/api/v1` with explicit permission class
- [ ] Serializer-declared fields only; no `__all__`
- [ ] Envelopes + status codes per §8; JSON 404 confirmed
- [ ] Validation failures return `{error, field_errors?}` — tested
- [ ] Contract matches the data-layer promise; no client-trusted money math
- [ ] Business logic in services; views thin
