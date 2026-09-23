---
name: ai-tooling
description: Configure and govern the Jeyvro AI agent environment — use when setting up or reviewing MCP servers and tools for Cline, managing agent context (which files/skills to load), decomposing large tasks across skills, or approving any new AI integration. Behavior rules live in PROJECT_CONTEXT §14 — this skill configures the environment; it never re-legislates behavior.
---

> **Source of truth:** [PROJECT_CONTEXT.md](../../PROJECT_CONTEXT.md) — when anything conflicts, the project context wins. Catalog entry: #15 in [SKILL_CATALOG.md](../../SKILL_CATALOG.md).

# Jeyvro AI Tooling — Agents · MCP · Context

One responsibility: **the AI agent's environment** — MCP servers/tools, context management, and integration approval. *How the agent behaves* (understand → inspect → plan → implement → test → review → fix → verify, reuse-first, secrets-safe) is already binding law in PROJECT_CONTEXT §14 and §18 — referenced here, never duplicated.

## Purpose

The agent always works with the right context (the source docs + the right skill), with tools that are least-privileged and approved — so AI speed never costs security or consistency.

## Current honest state

The agent runs as Cline in VS Code on this Windows machine; **no MCP servers are configured yet**. The routing system (PROJECT_CONTEXT §18 → SKILL_CATALOG) is the context strategy that already works.

## When to use

- Adding/configuring MCP servers or agent tools
- Questions of context: what should the agent load for this task?
- Decomposing a large request into skill-boundary-sized tasks
- Approving/reviewing any new AI integration (C3 spirit)

## When NOT to use

- Behavior/ethics/security rules (PROJECT_CONTEXT §10, §14 — already binding) · feature work (the domain skills)

## Workflow

1. **Understand** — what does the task need: which domain(s), which data, which tools?
2. **Inspect** — load context in the fixed order: PROJECT_CONTEXT → SKILL_CATALOG routing → the specific skills; inspect the repo areas involved (§14.1).
3. **Plan** — decompose by skill boundaries (one skill's territory per step); name the verification for each step.
4. **Implement** — work step by step, using approved tools only.
5. **Test** — per the `testing`/domain skills' gates (§14.7).
6. **Review** — context was sufficient? tools misused? §14 rules held?
7. **Fix** — reload the correct skill/context; never improvise around a missing tool.
8. **Verify** — checklist below.

## Rules (binding)

1. Behavior follows PROJECT_CONTEXT §14 (the 10 agent rules) — this skill adds environment policy, not new behavior laws.
2. Context order is fixed: **PROJECT_CONTEXT → SKILL_CATALOG routing → specific skills → repo inspection**. Never substitute a whole-repo dump for routing; never work from memory when the doc exists.
3. MCP servers/tools are added **only with the owner's explicit approval** (C3 spirit), least-privileged: a database MCP gets read-only credentials; a filesystem MCP is scoped to the workspace.
4. Secrets never pass through MCP servers, tool configs, or agent logs (C7).
5. Tool output is verified before acting on it — a tool result is evidence, not truth (same standard as §14.7).
6. Task decomposition respects skill boundaries — one responsibility per step, each with its own verification; if a step needs two skills, it is two steps.
7. Unavailable tool ≠ blocked work: state what is missing, ask the owner — never fake or approximate a tool result.

## Best practices

- For any non-trivial task, name the skills you will follow *before* starting — it is the cheapest review.
- Keep MCP configs in version-controlled, secret-free files; document each server's scope next to its config.
- Re-read the source docs when reality drifts — §14 rule 9 (update docs first) applies to tooling changes too.

## Common mistakes

- Skipping PROJECT_CONTEXT and working from assumptions.
- Granting an MCP server write/production credentials "for convenience".
- One mega-task mixing five domains instead of five verifiable steps.
- Trusting tool output without looking at the result.
- Logging prompts/context containing secrets.

## Verification checklist

- [ ] Context loaded in the fixed order (docs → catalog routing → skills → repo)
- [ ] Task decomposed along skill boundaries, each step verifiable
- [ ] MCP/tools approved, least-privileged, secret-free
- [ ] Tool outputs verified before use; missing tools surfaced, never faked
- [ ] §14 behavior rules held throughout
