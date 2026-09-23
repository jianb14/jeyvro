---
name: deployment
description: Ship and operate Jeyvro in real environments — use when preparing production configuration, environment variables, Docker images, CI/CD pipelines, deploying Django, running PostgreSQL in production, serving static/media files, setting up logging, monitoring, or backups. Deployment consumes the security and backend-core rules; it never weakens them.
---

> **Source of truth:** [PROJECT_CONTEXT.md](../../PROJECT_CONTEXT.md) — when anything conflicts, the project context wins. Catalog entry: #14 in [SKILL_CATALOG.md](../../SKILL_CATALOG.md).

# Jeyvro Deployment & Operations

One responsibility: **getting Jeyvro onto real infrastructure and keeping it healthy** — environments, config, pipelines, runtime, and recovery. Code changes belong to the feature skills; security design to `security`; optimization to `performance-skill`.

## Purpose

A launch where nothing is improvised: configuration comes from the environment, every deploy passes the same gates as development, and data survives failures (backups that restore).

## Current honest state

No Django/infra exists yet (C5). This skill guides the setup choices now (settings split, `.env.example`, CI plan) and governs the actual launch later.

## When to use

- Production/staging configuration; environment variables; Docker
- CI/CD pipeline setup; release steps; migrations in production
- Static/media serving; logging; monitoring; backups

## When NOT to use

- Writing features or tests (the feature/`testing` skills) · security *design* (`security` — deployment consumes it) · performance tuning (`performance-skill`)

## Workflow

1. **Understand** — which environment changes (local → staging → production)? What does the release include?
2. **Inspect** — current settings/.env, pipeline state, infra choices already made; never re-decide silently.
3. **Plan** — config surface → build steps → migration plan (backup first) → release order → rollback plan; written before touching prod.
4. **Implement** — env-driven settings, pinned dependencies/images, pipeline stages mirroring the dev gates.
5. **Test** — CI green (lint → build → tests, §11); staging smoke of affected flows; migration applied on a restored backup copy first for risky ones.
6. **Review** — diffs of settings/infra like code; secrets audit (nothing new committed, C7).
7. **Fix** — in config/pipeline; a broken release rolls back first, debugs second.
8. **Verify** — checklist below.

## Rules (binding)

1. All configuration via environment variables — `DEBUG=False`, explicit `ALLOWED_HOSTS`, CORS allowlist in production; `.env` never committed; `.env.example` documents every variable (§10.4–10.5).
2. Secrets never enter images, logs, or CI output (C7); CI secrets live in the platform's secret store.
3. No production deploy with failing gates — the pipeline runs lint → build → tests (§11) on every push; main is always releasable.
4. Migrations are reviewed before production apply; destructive migrations require the owner's explicit instruction (see `backend-core` rule 2) and a fresh backup first.
5. Static files via the chosen pipeline (WhiteNoise/CDN); user media on object storage in production (§8, §17) — never on ephemeral disks.
6. PostgreSQL in production gets scheduled backups **with tested restores** — a backup that has never been restored is a hope, not a backup.
7. Logging is structured and sensitive-data-free (no tokens, passwords, full card data — C7); errors surface to monitoring (error tracking + uptime check minimum).
8. Docker images pin base + dependency versions; the image runs as a non-root user.

## Best practices

- Staging mirrors production config; surprises belong to parties, not launches.
- One-command deploy (script/pipeline) — manual steps drift.
- Rollback plan stated in every release note; keep the previous image/release ready.

## Common mistakes

- `DEBUG=True` or wildcard `ALLOWED_HOSTS`/CORS reaching production.
- Committing `.env` "temporarily" or baking secrets into Docker layers.
- Applying an unreviewed migration to a live database.
- Backups without restore tests.
- Monitoring that only checks the homepage while checkout is broken.

## Verification checklist

- [ ] Env-driven config; no secrets in repo/images/logs; `.env.example` current
- [ ] CI runs the full gates and blocks failing deploys
- [ ] Migrations reviewed; backup taken before risky applies
- [ ] Static/media serving matches the environment plan
- [ ] Backups scheduled **and** restore-tested
- [ ] Logging + monitoring live; no sensitive data logged
