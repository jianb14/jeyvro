---
name: testing
description: Test strategy and the debugging method for Jeyvro — use when writing or running tests, fixing any bug, changing money flows (cart totals, checkout, inventory, refunds, payments), deciding whether work is done, or investigating a failing or flaky test. Covers today's lint+build gates, the mandatory pytest/DRF gates once Django exists, what to test first, and the reproduce→isolate→fix→regression-test loop.
---

> **Source of truth:** [PROJECT_CONTEXT.md](../../PROJECT_CONTEXT.md) — when anything conflicts, the project context wins. Catalog entry: #13 in [SKILL_CATALOG.md](../../SKILL_CATALOG.md).

# Jeyvro Testing & Debugging

One responsibility: **how correctness is proven** — what the quality gates are, how tests are written, and how bugs are chased to root cause. Feature skills *write code*; this skill decides *how that code is proven*. Convention/a11y/perf review verdicts stay with `frontend-review`.

## Purpose

Make "done" mean something: every Jeyvro change passes declared gates, money flows are always test-covered, and no bug is closed without a regression test proving it stays closed.

## When to use

- Writing any test (backend pytest/DRF once Django exists; Vitest/RTL when introduced; E2E later)
- Before merging any change touching orders, payments, cart totals, inventory — **money flows** (PROJECT_CONTEXT §11)
- Fixing any bug (the debugging loop below)
- Deciding whether any work is "done" (the gates)

## When NOT to use

- Reviewing conventions, a11y, or performance verdicts (`frontend-review` judges those)
- Writing the feature code itself (the feature skills)
- Deployment smoke/setup procedures (the `deployment` skill, once created)

## Current honest state (PROJECT_CONTEXT §11)

- **Backend (live):** from `backend/`, run `"%LOCALAPPDATA%\jeyvro-venv\Scripts\python.exe" -m pytest -q` — pytest + pytest-django against PostgreSQL. Models, services, permissions, and money flows are covered app-by-app (`tests/test_*.py`; 44 tests as of Phase 7). Run the full suite before closing a phase.
- **Frontend (live):** from `frontend/`, `npm run lint`, `npm run test`, `npm run build` (use `npm.cmd` on this machine). Vitest + jsdom + Testing Library: accessor tests (`src/data/*.test.js`) assert the wire contract with a stubbed `fetch`; component tests assert rendered behavior (no implementation details).
- **Gotcha:** on this machine the frontend gates must be run through a space-free path — see *Environment gotcha* below, or every suite fails with a misleading Vitest error.
- **Later:** Playwright E2E for checkout.

## Workflow

Follow the universal loop (PROJECT_CONTEXT §14), instantiated for a bug fix:

1. **Understand** — expected vs. actual behavior; who hit it, where, and since when.
2. **Inspect** — reproduce it reliably first (exact steps + data); read the relevant code paths before touching anything.
3. **Plan** — find the root cause, not the first plausible symptom; choose the smallest safe fix.
4. **Implement** — fix the cause, and write the regression test that fails on the old code and passes on the new.
5. **Test** — run the full gates: lint → build → tests. The new test passes; neighboring tests must not break.
6. **Review** — confirm the fix changed nothing unrelated; UI diffs go through `frontend-review`.
7. **Fix** — address anything the review or tests surfaced.
8. **Verify** — gates green + a manual smoke of the affected flow + the regression test now lives in the suite.

(For new features the same loop applies, with tests written alongside the feature at steps 4–5 — not bolted on afterwards.)

## What to test (priority order)

1. **Money flows** — cart totals recomputed on the backend, checkout order snapshots, inventory decrement, refunds (§6, §11).
2. **Permissions & ownership** — object-level access (order X belongs to this user — IDOR checks).
3. **Validation** — invalid input rejected with `{error, field_errors?}` envelopes.
4. **Business rules from PROJECT_CONTEXT §6** — tested as specified there, never re-derived differently.
5. **UI async states** — loading/empty/error/success wiring (once frontend tests exist).

## Rules (binding)

1. Never claim "done" without running the applicable gates (§14.7: lint + build frontend; tests + runserver smoke backend).
2. No order/payment logic merges without tests once the backend exists (§11).
3. Every bug fix ships with a regression test (once a test runner exists for that side).
4. Prove current behavior with a test *before* refactoring; prove nothing changed after.
5. Never add test dependencies without the owner's approval (C3) — pytest/pytest-django and Vitest/Testing Library are already approved and installed; new *runtime* dependencies still need approval.

## Environment gotcha: Vitest fails when the project path contains a space

Symptom (Vitest 5.0.1 + Vite 8 + jsdom, Node 24, Windows): **every** suite dies right after the RUN banner with

`Error: Vitest failed to find the current suite.` or `TypeError: Cannot read properties of undefined (reading 'config')`

reported at the first `describe(...)` in a test file **and** at the first `afterEach(...)` in `src/test/setup.js` — every file collected `0 test`, and it reproduces in a minimal node-environment config with no plugins and no setup files.

That is a **path** problem, not a code problem: the space in `C:\Users\Christian R\OneDrive\Desktop\Jeyvro` breaks Vitest's module-identity mapping, so the runner's state and the test file's `import { describe } from 'vitest'` end up as two different module instances. Ruled out by probes: jsdom, the React plugin, setup files, `globalSetup`, the vite cache, pool/isolate settings, a stale or partially-installed `node_modules`, and an interfering `npm run dev` server.

Workaround — run the gates through a space-free drive mapping (`subst` needs no admin and changes nothing on disk):

```powershell
subst X: "C:\Users\Christian R\OneDrive\Desktop\Jeyvro"
cd X:\frontend
npm.cmd run test    # same files, green
npm.cmd run lint
npm.cmd run build
subst X: /d         # optional cleanup
```

Evidence: the identical tree passes every suite from `X:\frontend` (~6s) and fails identically from the space-containing path. Lint and build are unaffected by the path — only Vitest's runner is.
6. Test behavior through public interfaces (API endpoints, rendered component output) — not internal private functions.
7. Never weaken, skip, or delete a test to get green — fix the code, or raise the rule change with the owner and update PROJECT_CONTEXT first.
8. Debug with evidence: read and cite the actual error/log in the fix — never guess-and-push.

## Best practices

- Arrange–Act–Assert; one behavior per test; names read as sentences: `test_checkout_recomputes_totals_from_db_prices`.
- Keep tests fast and deterministic — no sleeps; control time/randomness deliberately.
- Seed realistic PH-market data (₱ prices) so money-formatting bugs surface early.
- When a test fails, read the entire failure output before changing any code.

## Common mistakes

- Testing implementation details instead of behavior — tests that break on every refactor.
- Writing the regression test but accidentally asserting the buggy behavior.
- "It works on my machine" — gates not actually run.
- Skipping the reproduction step and "fixing" symptoms — the bug returns.
- Treating frontend-only validation tests as security proof — the backend is the final line (§10).

## Verification checklist

- [ ] Bug reproduced with exact steps before any fix
- [ ] Root cause identified — not just the visible symptom
- [ ] Regression test added: fails on old code, passes on new
- [ ] All gates run and green: lint → build → tests (when they exist)
- [ ] Manual smoke of the affected flow done
- [ ] No test weakened, skipped, or deleted to get green
