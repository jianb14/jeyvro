---
name: git-workflow
description: Rules for version control in the Jeyvro project — use when initializing the git repository, creating branches, staging or committing changes, writing commit messages, preparing pull requests, or deciding what must never be committed. Covers the Jeyvro-only repo rule (never the stray home-root repo), branch and commit conventions, pre-commit gates, and the self-review.
---

> **Source of truth:** [PROJECT_CONTEXT.md](../../PROJECT_CONTEXT.md) — when anything conflicts, the project context wins. Catalog entry: #12 in [SKILL_CATALOG.md](../../SKILL_CATALOG.md).

# Jeyvro Git Workflow

One responsibility: **how Jeyvro changes are versioned, branched, committed, and shared** — so history stays reviewable and no secret or junk file ever enters the repo. Building code, writing tests, and deploying belong to other skills; this skill owns version-control actions only.

## Purpose

Give every Jeyvro change a clean, reviewable place in history: correct repo, correct branch, small honest commits, and a self-reviewed diff — while making it structurally impossible to commit secrets or use the wrong repository.

## When to use

- Initializing the Jeyvro git repository
- Starting or finishing any change: branch, stage, commit, PR
- Writing or reviewing commit messages
- Deciding what belongs in `.gitignore`
- Any question about branches, history, or the GitHub flow

## When NOT to use

- Deploying or releasing (the `deployment` skill, once created)
- Writing tests or deciding "done" (the `testing` skill)
- Questions about what the project *is* or where things live (`jeyvro-project`)

## Workflow

Follow the universal loop (PROJECT_CONTEXT §14), instantiated for version control:

1. **Understand** — what single logical change is this? If it is two changes, plan two commits (or two branches).
2. **Inspect** — run `git status` and `git diff` before staging anything; verify the repo with `git rev-parse --show-toplevel` — it must end in `Desktop/Jeyvro`, never the home root.
3. **Plan** — pick the branch name: `feat/<area>-<change>` or `fix/<area>-<change>` (`chore/…` for tooling/docs only).
4. **Implement** — commit small and focused as the work progresses; never batch unrelated edits into one commit.
5. **Test** — gates must pass before committing: lint → build → tests (when they exist). Never commit red.
6. **Review** — self-review the full staged diff (`git diff --staged`) top to bottom: secrets, debug leftovers, unrelated files.
7. **Fix** — unpushed mistakes: `git commit --amend`. Already pushed/shared: a new follow-up commit, never history rewriting.
8. **Verify** — `git status` is clean, `git log --oneline` reads as a coherent story, and the tree contains only intended files.

## Rules (binding)

1. Initialize git **only inside** `C:\Users\Christian R\OneDrive\Desktop\Jeyvro`. A stray zero-commit repo exists at the user-home root (`C:/Users/Christian R`) — **never use it** (PROJECT_CONTEXT §15, C4).
2. Repo initialization requires the owner's explicit approval first.
3. `.gitignore` exists **before the first commit** — it must cover `.env`, `node_modules/`, `dist/`, `__pycache__/`, `.venv/`, `*.log`.
4. Never commit secrets, `.env`, credentials, dumps, or build output — even to private repos (C7).
5. Branch names: `feat/…`, `fix/…`, `chore/…`. One branch = one concern; keep branches short-lived.
6. Commit messages: imperative summary ≤ 72 chars, optional body explaining *why* — e.g. `feat(cart): add line-item quantity stepper`.
7. The gates (lint → build → tests) pass before every commit — never commit red.
8. Never mix unrelated changes in one commit; split or stage selectively (`git add -p`).
9. Never force-push shared branches or rewrite published history.

## Merge conflicts, code review & repository hygiene

- **Conflicts:** understand both intents before resolving — never mechanically "take mine/take theirs"; re-run the gates after every resolution (the merge is untested until lint+build+tests pass).
- **Code review:** PRs stay small and single-concern (rule 5/8); the reviewer (agent or human) checks the §14 rules + the relevant skill's checklist — review comments are addressed by commits, never by force-push.
- **Repository hygiene:** `.gitignore` stays current with the stack (frontend now, Django artifacts later); no stray debug files, dumps, or editor junk; releases are tagged (`vX.Y.Z`); deleted features leave no dead files behind.

## Best practices

- First commit is `.gitignore` + scaffold: `chore: initialize Jeyvro repository`.
- Commit early in small pieces — a series of honest commits beats one giant one.
- Read the diff with fresh eyes before committing; you are your first reviewer.
- Keep `main`/`master` always working: all real work happens on branches.
- Push to a GitHub remote only when the owner approves it.

## Common mistakes

- Running `git init` in the home folder or OneDrive Desktop root — creating/using the stray repo. Always verify the toplevel path first.
- Committing `.env`, `node_modules/`, or `dist/` because `.gitignore` was missing.
- "WIP" mega-commits mixing several unrelated changes.
- Committing without running the gates — broken commits in history.
- "Fixing" git problems by deleting the folder — repo problems are fixed with git, not by starting over.

## Verification checklist

- [ ] `git rev-parse --show-toplevel` points inside `…\Desktop\Jeyvro`
- [ ] `.gitignore` covers `.env`, `node_modules/`, `dist/`, `__pycache__/`, `.venv/`, `*.log`
- [ ] `git status` shows only intended files staged
- [ ] Lint + build (and tests, when they exist) pass before committing
- [ ] Diff self-reviewed: no secrets, no debug leftovers, no unrelated edits
- [ ] Commit message: imperative, ≤ 72-char summary, body explains why when non-obvious
