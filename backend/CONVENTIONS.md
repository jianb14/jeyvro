# JEYVRO Backend Conventions (Phase 2 foundation decisions)

> Binding per PROJECT_CONTEXT §18: rules live here once; skills reference
> them. Source of truth for WHAT stays PROJECT_CONTEXT.md.

## Database (§2.2 decisions)

- **PKs / UUID strategy:** internal PKs use `BigAutoField`. Public-facing
  identifiers (slug/UUID in URLs) are added per model when first exposed —
  decided with the model, never retrofitted silently.
- **Timestamps:** every business model inherits `apps.common.TimeStampedModel`
  (`created_at` / `updated_at`).
- **Soft delete:** not global. Only domains that legally need it (returns,
  disputes) get it — decided with that domain. Default is hard delete with an
  audit-log row.
- **Unique constraints:** enforced at the database level, e.g. one review per
  (user, product) (backend-core rule 7) — never only in serializers.
- **Indexes:** added when a query pattern is known — browse paths first
  (category, store, price, `created_at`) (backend-core rule 5).
- **Foreign keys:** every FK declares `on_delete` explicitly; `PROTECT` for
  money/legal records (Order, Payment, OrderItem) (backend-core rule 4).
- **Money:** `DecimalField(max_digits=12, decimal_places=2)` — never float
  (C6). Totals are recomputed server-side at checkout (§6); client math is
  never trusted (§10.1).
- **Timezone:** `USE_TZ = True` (stored UTC); `TIME_ZONE = 'Asia/Manila'`
  for display (C6).
- **Status fields:** `models.TextChoices` on the owning model; transitions
  happen only in service functions, never by blind field writes (§6).
- **Audit/history:** no third-party history library (C3). The dedicated
  `audit` app (Phase 13) receives event rows written by domain services.

## API (§2.1 decisions)

- **Versioning:** `/api/v1/` only; per-domain `urls.py` included from
  `config.urls`.
- **Response envelopes:** list → `{count, items}`; single → object;
  errors → `{error, detail?, field_errors?}` — one-off shapes forbidden (§8).
- **Pagination:** `CountItemsPagination` (default 20, `page_size` ≤ 100) on
  every list endpoint from day one.
- **Errors:** DRF exceptions flow through
  `apps.common.exceptions.jeyvro_exception_handler`; unhandled crashes and
  404s outside DRF return JSON via `config.urls` handlers — HTML errors never
  leave Django (§8).
- **Validation:** serializer-declared fields + model constraints; all request
  validation is server-side (§10.1). Frontend validation is UX only.
- **Permissions:** every viewset declares its permission class explicitly
  (backend-api rule 6) — nothing ships public by accident.

## Media (§2.4)

Development stores uploads under local `media/`; production moves to
object storage + CDN (§17). Validation rules (type/size/MIME/safe names) are
implemented with the first file upload (seller images, Phase 12).
