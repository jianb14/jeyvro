# Jeyvro — Security Checklist (Phase 20.1)

> The artifact the ROADMAP §20.1 gate asks for ("Security checklist
> complete"). One row per review item, each with a **verdict** and the place it
> is *proven* — a file and a test name, never a promise. Anything not yet true
> says so and why.
>
> Reviewed: Phase 20.1 (deny-by-default, throttling, CORS/CSRF, the tracking
> PII finding). Suite at review time: **336 backend tests**, 189 frontend,
> lint/build/migrations green.
>
> One lesson earned here, worth keeping: the suite runs with throttling lifted,
> so it passed **336 tests while the live server 500'd on every request** — a
> bare `'120'` is not a DRF rate string, and it only fails when a throttle is
> actually instantiated. A live smoke is not optional, and
> `test_every_configured_rate_is_a_real_drf_rate` now keeps that class of
> mistake in CI.

| # | Item | Verdict | Proven by |
|---|---|---|---|
| 1 | Authentication review | ✅ Session auth pinned; **HTTP Basic removed** (DRF's default list enables it and this API never intends it) | `config/settings.py` `DEFAULT_AUTHENTICATION_CLASSES`; `test_security_hardening.py::test_only_session_authentication_is_accepted` |
| 2 | Authorization review | ✅ **Deny by default** — the project default is `IsAuthenticated`, and every routed view class declares its own permissions or overrides `get_permissions` | `config/settings.py`; `test_every_view_declares_its_own_permissions` (walks the URLconf, fails the gate when a new view forgets) |
| 3 | IDOR review | ✅ Ownership is re-verified at the object fetch, and **a bearer token is not an identity** — see finding below | `apps/accounts/permissions.py` (`IsOwner`), `IsSeller`, staff querysets; deny-path tests per domain; `test_public_tracking_never_returns_buyer_pii`, `test_the_whole_record_is_for_the_buyer_the_seller_and_staff` |
| 4 | CSRF review | ✅ `SessionAuthentication` enforces CSRF on unsafe methods; `SameSite=Lax` cookies; `CSRF_TRUSTED_ORIGINS` is an explicit allowlist | `test_an_unsafe_method_without_a_csrf_token_is_refused` (`enforce_csrf_checks=True`) |
| 5 | CORS review | ✅ Allowlist (never `*`), **`CORS_ALLOW_CREDENTIALS = True`** — without it `credentials: 'include'` fails cross-origin while the allowlist still looks right; explicit headers/methods | `test_cors_answers_only_allowlisted_origins_and_allows_credentials` |
| 6 | XSS review | ✅ React escapes by default; **zero** `dangerouslySetInnerHTML` / `innerHTML =` in `frontend/src`; the API answers JSON only (no HTML templates) | repository-wide search; no HTML-rendering surface exists |
| 7 | SQL injection review | ✅ **ORM only** — zero `cursor().execute` / `RawSQL` / `.extra(` / `raw(` in `backend/`; search is PostgreSQL full-text through the ORM (Phase 18.1) | repository-wide search; `apps/search` uses `SearchVector`/`SearchQuery` |
| 8 | Input validation review | ✅ Every write is serializer → service; the client never supplies prices, fees, totals, permissions or refund amounts; money is `Decimal` end to end (C6) | `backend/apps/*/serializers.py` + per-domain tests; the §19 rollups exist because the derivation is server-side |
| 9 | File upload review | ✅ Extension allowlist + 5 MB cap + **magic-byte sniffing** (no Pillow, C3) + request-wide 6 MB memory cap | `apps/catalog/services.py::validate_image_file`, `ALLOWED_IMAGE_EXTS`; `DATA_UPLOAD_MAX_MEMORY_SIZE`; catalog upload tests |
| 10 | Rate limiting | ✅ Blunt default (anon + user) plus **scopes** on the surfaces worth abusing: `auth` (login, verification resend, password reset), `register`, `checkout`, `message` | `test_rate_limiting_refuses_a_flood_on_the_auth_surface`, `test_the_surfaces_worth_abusing_carry_tight_scopes`; suite runs unthrottled (`tests/conftest.py`) so no gate depends on a clock |
| 11 | Brute-force protection | ✅ Two layers: the app-level lockout (5 failures → 15 min, per email) **and** the `auth` throttle bucket in front of it | `apps/accounts/services.py` (`MAX_FAILED_LOGINS`, `LOCKOUT_SECONDS`, `is_locked_out`); `apps/accounts/views.py::LoginView` |

## Finding fixed in this review — public tracking leaked buyer PII

`GET /api/v1/shipments/track/<tracking_number>/` had **no permission class**
(it inherited the old project-wide `AllowAny`) and returned the full
`serialize_shipment()` payload: **`recipient_name`, `recipient_phone`,
`shipping_address_text`**, the goods, the shipping fee and the seller's own
`package_notes`. Anyone holding a tracking number could read who the parcel
belongs to and where they live — while the order's address is supposed to be
on a privacy ladder (§6 v1.7) and the project refuses even to say whether an
email exists.

**Fix:** `serialize_tracking_status()` — the public projection carries the
journey (carrier, status, shipped/estimated/delivered, events reduced to
`status` + `occurred_at`) and nothing else. The full record is the order
owner's, the fulfilling seller's and staff's, decided by `_may_read_full_shipment()`.
A signed-in stranger is redacted, not refused: public tracking is a feature;
leaking the buyer through it was the bug.

## Known gaps carried forward (honest, not hidden)

- **Production environment values** (allowed origins, `DEBUG=False`,
  `ALLOWED_HOSTS`, `SECURE_*` cookie flags, a shared cache for throttling)
  land with the deployment phase (Phase 23). LocMemCache is per-process, so a
  multi-worker deploy needs a shared cache before the rate limits mean
  anything.
- **20.2 abuse controls** (spam, messaging abuse, suspicious-order detection,
  inventory abuse) are the next slice; the throttling above is the floor, not
  the answer.
- **20.3 auditing is done** — `docs/AUDIT_COVERAGE.md` is the matrix of every
  sensitive operation and the action it writes. It closed three real gaps: the
  §19.4 CSV exports (`analytics.exported` — actor, report, range, row count), a
  seller's own price edits (`product_price_changed` / `variant_price_changed`,
  with before/after) and the seller store profile, where `PATCH /stores/my/store`
  changed the **shipping fee** with no record at all (now
  `store_profile_updated`, written by `stores.services.update_own_profile`).
  What is still missing is **not** coverage but custody: audit retention, a
  signed export, and alerting on money actions all land with Phase 23.
- **Login/logout/auth events** are deliberately not in that matrix — they
  belong to a security log, not the business audit trail.
