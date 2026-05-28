# Step 14 — Delegate to sister skills

`project-scaffold` doesn't own test-runner or workflow templates. Step 14 delegates to two specialized skills, in order. Both detect each other's outputs and only add what's missing, so run order is unambiguous.

## Order

1. **Run `/testing-init`'s execution phase first.** It owns:
   - Test runner installs (Vitest + Playwright for Node, pytest for Python; React projects also get `@testing-library/react` + `jsdom`).
   - Runner configs (`vitest.config.ts`, `playwright.config.ts`, `[tool.pytest.ini_options]` block in `pyproject.toml`).
   - Passing smoke-test stubs.
   - `test` / `test:unit` / `test:integration` / `test:e2e` scripts.
   - Test jobs in `.github/workflows/ci.yml` (creates the file if it doesn't exist).

2. **Run `/gh-actions-init`'s execution phase second.** It owns:
   - Structural CI jobs (lint + typecheck + format:check + build) — appended to the `ci.yml` `testing-init` just wrote.
   - `release-please.yml` + `release-please-config.json` + `.release-please-manifest.json`.
   - `deploy.yml` with the deploy-target picker.

## Manifest-version invariant (new projects)

For brand-new projects (this skill's path), the release-please manifest must start at `0.0.1` — **not `0.0.0`**. A manifest of exactly `0.0.0` with no git tag makes release-please bootstrap the first release to `1.0.0` regardless of commit type (the `bump-minor-pre-major` / `bump-patch-for-minor-pre-major` options are ignored in that case — [googleapis/release-please#2087](https://github.com/googleapis/release-please/issues/2087); hit live on `hellatan/getoffthecouch`). Seeding at `0.0.1` makes the first PR compute normally: a `feat:` → `0.1.0`, a `fix:` → `0.0.2`. `package.json` / `pyproject.toml` `version` must match the manifest. Step 11 already sets both to `0.0.1`; just confirm `gh-actions-init` reads that current value rather than starting from a different default.

## Sub-skill protocol when invoked from project-scaffold

The sister skills have their own detection and summary-halt steps designed for retrofitting existing projects. When invoked from `project-scaffold`, those steps are redundant:

- **Skip their detection step** — the stack is already known from project-scaffold's Step 2 (project name) and Step 4 (framework selection). Pass it forward instead of re-detecting.
- **Skip their summary-halt step** — project-scaffold's Step 9 confirmation already gathered the user's "go" for the entire scaffold. Re-prompting would be friction.
- **Run their execution + smoke-test + report steps as documented.**
- **Surface their reports inline** — fold them into project-scaffold's Step 21 final report rather than printing two separate reports back-to-back.
