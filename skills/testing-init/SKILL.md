---
name: testing-init
description: Add a testing pipeline to an existing repo — installs runners (Vitest/Playwright/pytest), scaffolds passing test stubs, wires up `npm run test` / `pytest` / equivalent scripts, and optionally adds the matching CI workflow. Use when the user wants to "add tests," "set up a testing pipeline," "scaffold vitest/pytest/playwright," or otherwise bring a testing layer to a project that doesn't have one yet. Detects stack from `package.json` / `pyproject.toml`. Skips work that already exists (idempotent).
---

# testing-init

Adds a testing pipeline to an existing project. Detects the stack, picks prescriptive defaults, scaffolds runners + configs + passing test stubs, and (optionally) wires the matching CI workflow.

## When to trigger

User says any of:
- "add tests / a testing pipeline / a test setup"
- "set up vitest / playwright / pytest"
- "I want to start writing tests"
- "scaffold tests for this project"

## When NOT to use

- Project already has a working test setup that's running green — extend it manually instead of replacing.
- Bootstrapping a brand-new repo from scratch — use `project-scaffold` (which calls this internally for new projects).

---

## Flow

### 1. Detect stack

Read these files (don't ask the user):

- `package.json` — Node project. Inspect `dependencies` for framework (`next`, `react`, `fastify`, `express`, `vue`, etc.) and `engines.node` if set.
- `pyproject.toml` / `setup.py` / `setup.cfg` — Python project.
- `tsconfig.json` — confirms TypeScript.
- File extensions in `src/` / project root — confirms language.

Surface what you found in one line: *"Detected: Next.js 16 + TypeScript. I'll use Vitest for unit tests and Playwright for e2e — say so if you'd rather different runners."*

For ambiguous detection (e.g., both `package.json` and `pyproject.toml` present, or no source files yet), ask **once** to disambiguate.

### 2. Pick runners (prescriptive defaults)

State the picks as facts, name overrides:

| Stack | Default runners | Common alternatives |
|---|---|---|
| Node + TypeScript | **Vitest** (unit), **Playwright** (e2e) | Jest (unit, heavier), Cypress (e2e, heavier) |
| Node + React | Vitest + `@testing-library/react` + `jsdom` (unit), Playwright (e2e) | same as above |
| Node + Fastify / Express (no UI) | Vitest (unit + integration); skip e2e | Mocha + Chai |
| Python | **pytest** (unit + integration), **pytest-cov** (coverage) | unittest (stdlib only — heavier boilerplate) |

If user gives no override: proceed with defaults.

### 3. Pick scope

Ask once:

> What scope of tests? (defaults to all three for fullstack, unit-only for libraries.)
> - `unit` — fastest, runs on every commit
> - `unit + integration` — adds slower tests against real dependencies
> - `unit + integration + e2e` — full pyramid; e2e needs a browser (Playwright handles install)
> - skip e2e if backend has no UI

### 4. Optional: also wire CI

Ask:

> Want me to also add a GitHub Actions workflow that runs these tests on every PR? (Y/n — recommend yes; takes 30 extra seconds and means broken tests block merges.)

If user says yes AND `.github/workflows/ci.yml` already exists, **extend** it (add a job, don't replace). If it doesn't exist, create a minimal one. See `references/ci-test-job.md`.

If user wants the full release-please + deploy stack later, point them at `gh-actions-init`.

### 5. Show summary, halt for confirmation

Render the plan as a fenced code block with emoji headers (same convention as `project-scaffold`'s Step 8). Show only choices made.

```
🔍 Detected:        <stack summary>
🧪 Test runners:    <runners chosen>
📂 Scope:           <unit | unit + integration | unit + integration + e2e>
📦 New dev deps:    <list of packages to install>
📝 Files to write:  <list of new files>
📝 Files to modify: <list of files to extend>
🤖 CI:              <extend ci.yml | create ci.yml | skipped>
```

End with: *"Reply 'yes' / 'go' / 'looks good' to proceed, or tell me what to change."*

### 6. **HALT for confirmation**

Same gate as `project-scaffold` — wait for explicit affirmative reply before any install or file write.

---

## Execution

### 7. Install dev deps

Per stack:
- Node: `npm install --save-dev <runners>` — see `references/runners.md` for the exact list per stack.
- Python: add to `[project.optional-dependencies].dev` (or `[dependency-groups].dev` for uv) in `pyproject.toml`, then `pip install -e ".[dev]"` (or `uv sync`).

### 8. Write runner configs

- Node + Vitest: `vitest.config.ts` (with React plugin if React detected, jsdom env if frontend).
- Node + Playwright: `playwright.config.ts`.
- Python + pytest: `[tool.pytest.ini_options]` block in `pyproject.toml`.

All templates: `references/runners.md`.

### 9. Write test stubs

Smoke tests that pass and exercise the runner end-to-end. See `references/test-stubs.md` for the per-stack stub bodies.

- Node unit: `src/__tests__/smoke.test.ts`
- Node e2e: `e2e/smoke.spec.ts`
- Node integration (if scoped in): `tests/integration/smoke.test.ts`
- Python unit: `tests/test_smoke.py`
- Python integration (if scoped in): `tests/integration/test_smoke.py` with a marker

**Don't overwrite existing test files.** If a path already exists, skip and note it in the report.

### 10. Wire scripts

- Node: extend `package.json` `"scripts"` with `test`, `test:unit`, `test:integration`, `test:e2e` (only the scopes the user chose). See `references/scripts.md`.
- Python: extend `scripts/dev.py` if it exists (project-scaffold projects have one), otherwise document the raw commands in the report.

### 11. (Optional) Wire CI

Only if user opted in at Step 4. See `references/ci-test-job.md`.

### 12. Smoke-run the new tests

- Node: `npm run test` (and `npm run test:e2e` if e2e in scope — Playwright will install browsers on first run; warn the user that takes ~30s).
- Python: `pytest`.

If anything fails, **stop and report**. Don't claim success on red.

### 13. Report back

Print:
- ✅ What was installed
- ✅ What was scaffolded (file paths)
- ✅ What was extended (scripts added, CI job added)
- ✅ Smoke run results
- 📋 Next steps:

```
Next steps:
1. Replace the smoke-test stubs with real tests as you build features
2. Run `npm run test` (or `pytest`) locally before pushing
3. (If CI not yet added) Run `/gh-actions-init` to add the matching CI workflow + release-please + deploy stub
```

---

## Reference files

- `references/runners.md` — Vitest, Playwright, pytest configs + dev-dep install commands
- `references/test-stubs.md` — passing smoke-test stubs per stack and scope
- `references/scripts.md` — `package.json` scripts and `scripts/dev.py` extensions
- `references/ci-test-job.md` — extending or creating `.github/workflows/ci.yml`

## Why these defaults

- **Vitest over Jest** — faster, native ESM, native TS, smaller config surface. Jest's only edge is a marginally bigger ecosystem of plugins, which most projects don't need.
- **Playwright over Cypress** — runs against multiple browsers, has built-in test runner, doesn't require a separate dashboard process.
- **pytest** — Python's de facto standard. `pytest-cov` for coverage. Don't introduce nose/unittest unless the user asks.
- **Idempotent on re-run** — skip files that exist, surface what was skipped, never overwrite the user's existing tests.
