# JEYVRO — AI Skill Architecture

> Subordinate to [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) — on any conflict, the project context wins.
> Version 1.1 · v1.1 changelog: Tier 2 expanded (frontend-state/responsive/performance) · Tier 3 exists (backend & database phase) · Tier 5 added (6 marketplace domain skills by owner request) · payments-skill and admin-panel-skill triggers fired/created · phase table updated.
> Version 1.0 · This document defines how the Jeyvro skill system is organized: what each skill owns, what it must never absorb, and when a new skill may be created. It is the map; SKILL.md files are the territory.

## 0. Design Rules (how every category decision was made)

1. **One responsibility per skill.** If a skill needs "and also…", it is two skills — or the second half belongs somewhere else.
2. **Layer beats domain.** Marketplace domains (cart, orders, payments…) are implemented through layer skills (`frontend-feature` / `backend-feature`); their *business rules* live in PROJECT_CONTEXT §6 — never duplicated into skills.
3. **Fold, don't fork, tool-specific concerns.** React → `frontend-ui`. Tailwind → `design-tokens`. Python/PostgreSQL → `backend-core`. A separate skill per technology would overlap 1:1 with an existing layer skill.
4. **No speculative skills** (same spirit as constraint C3): a skill is created only when its subject is about to be built. Future skills below carry explicit triggers.
5. **Reuse-first:** the 7 existing skills stay as-is; this architecture slots new skills around them.
6. **Build vs judge separation:** "how-to" skills build; "quality-gate" skills review. Never both in one skill.

## 1. Complete Hierarchy

```
Tier 0 — Sources of truth (not skills)
  PROJECT_CONTEXT.md          what is true (§1–§18)
  SKILL_ARCHITECTURE.md       this file — how skills are organized (§18 of the project context)

Tier 1 — Orientation
  jeyvro-project              (exists) workspace map, stack, commands, inventories

Tier 2 — Frontend (all exist)
  design-tokens               visual language: @theme tokens, Tailwind v4, dark mode
  ux-patterns                 behavior: feedback placement, a11y (build side), responsive
  frontend-ui                 React component conventions + components/ui primitives
  data-layer                  data access contract: accessors, mock→API swap, envelopes
  frontend-feature            full frontend features (pages/flows) end-to-end
  frontend-state              client state placement: local→lift→derive→URL→server
  frontend-responsive         mobile-first layout authoring (~360/768/1280)
  frontend-performance        everyday speed discipline: deps, renders, media, bundle
  frontend-review             frontend QA gate (owns a11y + performance verification)

Tier 3 — Backend (all exist — backend & database phase)
  backend-core                (exists) structure, settings, models, migrations, ORM, transactions
  backend-api                 (exists) DRF HTTP layer: /api/v1, serializers, viewsets, envelopes
  backend-feature             (exists) per-domain implementation playbook (accounts … notifications)
  security                    (exists) authn + authz + hardening (owns categories 14, 15, 29)

Tier 4 — Process & operations (all exist)
  testing                     (exists) test strategy, pytest/Vitest, debugging method
  git-workflow                (exists) repo init inside Jeyvro/, branches, commits, PRs
  deployment                  (exists) environments, Docker, CI/CD, logging, monitoring, backups
  ai-tooling                  (exists) MCP servers/tools, agent context, task decomposition
  performance-skill           (exists) API/database/caching optimization (fired split)

Named future splits — none currently; new skills follow the trigger rules in §0.4

Tier 5 — Marketplace domains (all exist — created by owner request)
  marketplace-catalog         products, categories, variants, images, stock, discovery
  marketplace-orders          cart, checkout, orders, lifecycle, order-time inventory
  marketplace-sellers         seller onboarding, stores, moderation, seller analytics
  marketplace-community       reviews, ratings, wishlist, messaging, notifications
  marketplace-admin           staff oversight, settings, reports, groups, audit
  payments-skill              ledger, COD, gateways, webhooks, refunds, payouts, commissions
```

## 2. Evaluation of the 39 Requested Categories

Verdicts: **keep** (a skill owns it) · **combine** (merged into another) · **divide** (split across skills) · **defer** (future skill with a trigger).

| # | Category | Verdict | Home & reason |
|---|---|---|---|
| 1 | Core Development | keep | `jeyvro-project` (exists) — orientation, stack, commands, dev-conventions entry point. |
| 2 | Project Architecture | combine → #1 | Facts live in PROJECT_CONTEXT §7–§9; `jeyvro-project` links them. A separate skill would duplicate the source of truth. |
| 3 | UI/UX | divide (done) | `design-tokens` (visual language) + `ux-patterns` (behavior). Two genuinely different responsibilities. |
| 4 | Frontend | keep (container) | `frontend-ui` + `frontend-feature` + `data-layer` + `frontend-review` — the container is Tier 2, not a skill. |
| 5 | React | combine → #4 | `frontend-ui` owns React conventions; they have no life outside component building. |
| 6 | Tailwind CSS | combine → #3 | `design-tokens` owns Tailwind v4 — the CSS-first `@theme` config *is* the token system. |
| 7 | Backend | divide → 3 skills | `backend-core` (structure/data) · `backend-api` (HTTP) · `backend-feature` (domain playbook). |
| 8 | Python | combine → #7 | `backend-core` owns style + conventions; no Python exists outside Django here. |
| 9 | Django | keep (part of #7) | `backend-core`. |
| 10 | Django REST Framework | keep (part of #7) | `backend-api`. |
| 11 | Database | combine → #7 | Modeling rules in `backend-core`; principles stay in PROJECT_CONTEXT §9. |
| 12 | PostgreSQL | combine → #7 | Schema/migrations in `backend-core`; production ops → `deployment`. |
| 13 | API Development | divide by side | `backend-api` implements; `data-layer` owns the frontend contract view (accessors, envelopes, swap). |
| 14 | Authentication | combine → #29 | `security`. |
| 15 | Authorization | combine → #29 | `security` (object-level ownership, staff groups). |
| 16 | Multi-Vendor Marketplace | divide by layer | NOT a skill: implemented via `backend-feature` + `frontend-feature`; rules stay in PROJECT_CONTEXT §6. |
| 17 | Product Management | keep (part of #16) | Catalog domain → layer skills. |
| 18 | Product Discovery | keep (part of #16) | Search/filter/browse domain → layer skills. |
| 19 | Cart | keep (part of #16) | Cart domain → layer skills; totals rule lives in §6. |
| 20 | Checkout | keep (part of #16) | Checkout domain → layer skills; flow + snapshot rule in §6. |
| 21 | Orders | keep (part of #16) | Order lifecycle states are defined in §6 — skills implement, never redefine. |
| 22 | Payments | ✅ created | `payments-skill` — ledger, COD, gateway adapters, webhooks, refunds, payouts, commissions (marketplace phase). |
| 23 | Inventory | keep (part of #16) | Inventory domain → layer skills. |
| 24 | Reviews & Ratings | keep (part of #16) | Reviews domain → layer skills. |
| 25 | Wishlist | keep (part of #16) | Wishlist domain → layer skills. |
| 26 | Messaging | keep (part of #16) | Messaging domain → layer skills. |
| 27 | Notifications | keep (part of #16) | Notifications domain → layer skills. |
| 28 | Admin System | ✅ created | `marketplace-admin` — staff oversight, moderation, settings, groups, audit (marketplace phase). |
| 29 | Security | keep | `security` — one home for authn, authz, and hardening (PROJECT_CONTEXT §10). |
| 30 | Testing | keep | `testing` — mandatory gates; no order/payment merge without tests (§11). |
| 31 | Debugging | combine → #30 | Debugging is a method (reproduce → isolate → fix → regression test), owned by `testing`. |
| 32 | Git and GitHub | keep | `git-workflow` — repo init inside `Jeyvro/` only (C4), branches, commits, PRs, review, hygiene. |
| 33 | DevOps | combine → #34 | No meaningful boundary between DevOps and deployment at this scale. |
| 34 | Deployment | keep | `deployment` — environments, Docker, CI/CD, logging, monitoring, backups. |
| 35 | Performance | ✅ created (split) | `performance-skill` (API/database/caching) + `frontend-performance` (React/bundle side). |
| 36 | Accessibility | combine (split home) | Build rules in `ux-patterns`, verification in `frontend-review/docs/a11y.md`. A11y is a property of every skill, not a place. |
| 37 | AI Integration | ✅ created | `ai-tooling` — MCP servers/tools, agent context, task decomposition, integration approval. |
| 38 | AI Agents | ✅ created | → `ai-tooling`. |
| 39 | MCP | ✅ created | → `ai-tooling` (least-privileged MCP servers, owner-approved). |

**Combine summary:** 2→1 · 5→4 · 6→3 · 8+9+11+12→7 · 10+13(impl)→backend-api · 14+15+29→security · 31→30 · 33→34 · 37+38+39→ai-tooling.
**Divide summary:** 3→2 skills · 4→4 skills · 7→3 skills · 13→2 sides · 16–28 → by layer, never one-skill-per-domain.

## 3. Skill Descriptions (Purpose · Scope · Responsibilities · In / Out · Dependencies)

### Tier 1–2 — Existing (unchanged)

**jeyvro-project** — *Orientation.*
Purpose: fresh-session navigation without re-asking the user. Scope: stack, commands, folder map, component inventory, routes-vs-design-system rules. Responsibilities: orient; route every request to the right specialist skill.
Belongs in: workspace facts. NOT: project facts (PROJECT_CONTEXT owns them), any conventions.
Depends on: nothing (root). Used by: everything.

**design-tokens** — *Visual language.*
Purpose: correct token usage in all frontend styling. Scope: `@theme` tokens, palette roles, light→dark pairs, shadows/radius/animations, Tailwind v4 CSS-first rules.
Belongs in: Tailwind CSS (#6), color/shadow/animation tokens. NOT: component structure, UX behavior, page styling decisions.
Depends on: nothing. Used by: frontend-ui, frontend-feature, frontend-review.

**ux-patterns** — *Interaction behavior.*
Purpose: which feedback goes where (loading/empty/error/success), accessibility build rules, responsive checks. Scope: async-state patterns, focus/keyboard/touch rules, mobile breakpoints.
Belongs in: UI/UX behavior (#3), a11y build side (#36). NOT: token values, code style, review verdicts.
Depends on: nothing. Used by: frontend-ui, frontend-feature, frontend-review.

**frontend-ui** — *React components.*
Purpose: build/extend the ~47 primitives in `components/ui`. Scope: React conventions (named exports, `forwardRef`, `useId`, `cx()`), Icons as the only icon source, design-system registration.
Belongs in: React (#5), component primitives. NOT: page/flow assembly, data fetching, token definitions.
Depends on: design-tokens, ux-patterns. Used by: frontend-feature.

**data-layer** — *Data access contract.*
Purpose: components never fetch; everything flows through `src/data/` accessors. Scope: accessor pattern, mock→API swap, response envelopes, product shape.
Belongs in: API Development — frontend side (#13). NOT: backend implementation, UI.
Depends on: nothing. Used by: frontend-feature, backend-api (contract mirror).

**frontend-feature** — *Frontend features.*
Purpose: build a marketplace page/flow end-to-end (product pages, cart UI, checkout UI, seller/storefront, profile…). Scope: routes, composition of primitives + accessors + ux states, feature checklists.
Belongs in: domain UIs (#16–#28 frontend side). NOT: new primitives (frontend-ui), backend, contract changes without data-layer.
Depends on: design-tokens, ux-patterns, frontend-ui, data-layer. Gated by: frontend-review.

**frontend-review** — *Frontend QA gate.*
Purpose: review diffs against all frontend conventions before "done". Scope: checklist review, a11y verification (`docs/a11y.md`), performance verification (bundle, render behavior).
Belongs in: quality gates, a11y/perf verification (#35, #36 verify side). NOT: writing features or tests.
Depends on: design-tokens, frontend-ui, ux-patterns.

### Tier 3 — Backend (future)

**backend-core** — *Django structure & data.*
Purpose: how the Django project is structured and how data is modeled. Scope: scaffold, apps-per-domain (§8), settings/.env split, models + migrations, constraints/indexes/Decimal money (§9), Python style, admin registration.
Belongs in: Backend/Python/Django/Database/PostgreSQL (#7–#12). NOT: HTTP layer, domain flows, security patterns.
Depends on: PROJECT_CONTEXT §8–§9. Used by: backend-api, backend-feature, deployment.

**backend-api** — *DRF HTTP layer.*
Purpose: design and implement the versioned JSON API. Scope: routers/viewsets, serializers (never expose raw model fields), `/api/v1`, envelopes `{count, items}` / `{error}`, pagination, JSON 404s, throttling hooks.
Belongs in: DRF (#10), API implementation (#13). NOT: the frontend contract view (data-layer owns that), business-logic internals.
Depends on: backend-core, data-layer (contract), security. Used by: backend-feature.

**backend-feature** — *Domain playbook.*
Purpose: the repeatable recipe for one marketplace domain, backend side (accounts, catalog, cart, orders, payments, reviews, messaging, notifications, audit). Scope per domain: model + constraints → migration → service layer (business logic) → serializer → viewset + permissions → tests → seed aligning with the frontend contract.
Belongs in: Multi-Vendor domains #16–#27 backend side, Admin (#28 backend). NOT: domain *rules* (PROJECT_CONTEXT §6 defines them), generic conventions.
Depends on: backend-core, backend-api, security, testing.

**security** — *Authn + authz + hardening.*
Purpose: one home for how Jeyvro enforces security (PROJECT_CONTEXT §10). Scope: authentication setup (session/JWT decision, password policy, rate limiting), authorization patterns (DRF permission classes, object-level ownership, group-based staff roles), validation doctrine, IDOR checks, CORS/CSRF, secrets/`.env`, audit logging of sensitive actions.
Belongs in: Authentication (#14), Authorization (#15), Security (#29). NOT: login-page UX (frontend-feature), deployment infra.
Depends on: backend-core. Mandatory reading for: backend-api, backend-feature, deployment, any admin work.

### Tier 4 — Process & operations (all exist)

**testing** — *Tests & debugging method.*
Purpose: test strategy and how tests are written. Scope: pytest/DRF (models, permissions, money flows — mandatory per §11), Vitest/RTL when frontend tests start, E2E later; the debugging method: reproduce → isolate → fix → regression test.
Belongs in: Testing (#30), Debugging (#31). NOT: review verdicts (frontend-review), feature code.
Depends on: backend-feature, frontend skills. Gates: backend-feature.

**git-workflow** — *Version control.*
Purpose: how changes are versioned and shared. Scope: init inside `Jeyvro/` only (C4 — never the stray home-root repo), branches `feat/…`/`fix/…`, commit conventions, PR + self-review, `.gitignore` (`.env`!).
Belongs in: Git/GitHub (#32). NOT: deployment.
Depends on: jeyvro-project. Used by: deployment.

**deployment** — *Shipping & operations.*
Purpose: getting Jeyvro onto real infrastructure. Scope: env separation, prod settings, static/media serving, PostgreSQL in prod, object storage, HTTPS, backups, release steps.
Belongs in: DevOps + Deployment (#33–#34). NOT: performance optimization, security design (consumes it).
Depends on: backend-core, security, git-workflow.

**ai-tooling** — *AI environment extensions.*
Purpose: configure non-code AI capabilities. Scope: MCP server config for Cline, agent workflow conventions, any AI integrations the owner adopts.
Belongs in: AI Integration / AI Agents / MCP (#37–#39). NOT: behavior laws (PROJECT_CONTEXT §14 owns them).
Depends on: jeyvro-project.

## 4. Dependency Graph

```
PROJECT_CONTEXT.md ──────────────────── every skill (source of truth)
SKILL_ARCHITECTURE.md ───────────────── every skill (organization rules)

jeyvro-project ──────────────────────── root pointer to all skills

frontend:
  design-tokens ──→ frontend-ui ──→ frontend-feature ──→ frontend-review
  ux-patterns ─────→ frontend-ui, frontend-feature, frontend-review
  data-layer ──────→ frontend-feature, backend-api (shared contract)

backend:
  backend-core ──→ backend-api ──→ backend-feature
  security ──────→ backend-api, backend-feature, deployment
  testing ───────→ gates backend-feature (no order/payment merge without tests)

operations:
  git-workflow ──→ deployment
  deployment ←── backend-core + security + git-workflow
```

Rules: a skill depends only on skills **upstream** in its tier flow — no circular dependencies. `data-layer` ↔ `backend-api` share the API contract: shapes are defined once (PROJECT_CONTEXT §8 + data-layer); `backend-api` mirrors them and never redefines.

## 5. Potential Overlaps to Avoid (explicit bans)

1. **A `react` skill** — forbidden; React conventions live in `frontend-ui`.
2. **A `tailwind` skill** — forbidden; Tailwind lives in `design-tokens`.
3. **A `database`/`postgresql` skill** — forbidden; modeling lives in `backend-core`, principles in PROJECT_CONTEXT §9.
4. **One skill per marketplace domain** (cart-skill, order-skill, …) — forbidden; they would duplicate §6 and drift on every rule change. Domains go through `backend-feature`/`frontend-feature`.
5. **Security rules scattered across skills** — forbidden; `security` owns the patterns, all others reference it.
6. **Test-writing rules inside `frontend-review`** — review may *require* tests; `testing` owns *how to write* them.
7. **Git commands inside other skills** — only `git-workflow`.
8. **A11y split-brain** — build rules live in `ux-patterns` only; `frontend-review/docs/a11y.md` links and verifies, never redefines.
9. **API envelope redefinition** — envelopes have one home (PROJECT_CONTEXT §8 / data-layer); `backend-api` mirrors.
10. **A separate `devops` skill** — forbidden at this scale; DevOps concerns live in `deployment`.

## 6. Recommended Skill Boundaries & Split Triggers

| Boundary rule | Explanation |
|---|---|
| Structure vs HTTP vs Domain | `backend-core` (models/settings) and `backend-api` (HTTP) are split because they change for different reasons — schema changes vs contract changes. `backend-feature` composes both per domain. |
| Build vs judge | `frontend-feature`/`backend-feature` build; `frontend-review`/`testing` judge. Never one skill doing both. |
| Rules vs recipes | Business rules live in PROJECT_CONTEXT §6; skills carry only *how to implement* them. |
| Divide a skill when… | one skill would need separate docs per sub-topic, change for unrelated reasons, or exceed ~2 screenfuls of rules. |

**Named future splits (create only when the trigger fires):**

1. **payments-skill** — ✅ created (owner request fired the trigger): ledger, COD, gateway adapters, webhooks, refunds, payouts, commissions.
2. **admin-panel-skill** — ✅ superseded by `marketplace-admin` (staff dashboards, moderation, settings, groups, audit) — created by owner request.
3. **performance-skill** — ✅ fully created (advanced/supporting phase): API/database/caching optimization, complementing `frontend-performance`.
4. **ai-tooling** — ✅ created (advanced/supporting phase): MCP servers/tools, agent context management, task decomposition.

## 7. Final Recommended Architecture (phased)

**39 categories → 25 skills + 2 sources of truth — the approved architecture is fully implemented.** No category unowned; no skill with two jobs.

| Phase | When | Skills created | Running total |
|---|---|---|---|
| **Phase 0 — foundation** | ✅ done | 7 existing skills + this document | 7 |
| **Core phase** | ✅ done | `git-workflow`, `testing` | 9 |
| **Frontend phase** | ✅ done | `frontend-state`, `frontend-responsive`, `frontend-performance` | 12 |
| **Backend & database phase** | ✅ done | `backend-core`, `security`, `backend-api`, `backend-feature` | 16 |
| **Marketplace domain phase** | ✅ done | `marketplace-catalog`, `marketplace-orders`, `marketplace-sellers`, `marketplace-community`, `marketplace-admin`, `payments-skill` | 22 |
| **Advanced/supporting phase** | ✅ done | `deployment`, `ai-tooling`, `performance-skill` (+ OWASP map in `security`, conflicts/review in `git-workflow`) | 25 |
| **Trigger-based** | complete | deep-profiling `performance-skill` ✅ created | **25 — complete** |

Every skill — existing or future — follows PROJECT_CONTEXT §18: opens with the source-of-truth line, lives at `.cline/skills/<name>/SKILL.md`, YAML frontmatter with `name` + a trigger-condition `description`, and never contradicts or duplicates the project context.