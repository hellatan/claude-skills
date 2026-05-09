# Step E — Test stubs (so CI doesn't fail on first push)

Without test stubs, the scaffolded CI pipeline fails on `vitest: command not found` or empty pytest collection. Scaffold these placeholders so the first push is green.

## Stubs by stack

- **Node/TS unit:** `src/__tests__/smoke.test.ts` with `expect(1).toBe(1)`
- **Node/TS e2e:** `playwright.config.ts` + `e2e/smoke.spec.ts` that loads a page or asserts `expect(true).toBeTruthy()`
- **Node/TS integration:** can be skipped with `echo "no integration tests yet" && exit 0` in the workflow until user adds real ones (the CI variant in `references/workflows/ci-node.md` already handles this)
- **Python unit:** `tests/test_smoke.py` with `def test_smoke(): assert 1 == 1`
- **Python integration/e2e:** marker-based stubs so collection succeeds even with no tests

## Install the runners as dev deps

Don't just reference them in scripts — actually install:

- Node: `vitest`, `@playwright/test`, `@vitejs/plugin-react`, `jsdom`, `@testing-library/react`, `@testing-library/jest-dom`
- Python: `pytest`, `pytest-cov`

See `references/configs/nextjs.md` for the full Next.js dev-deps list and the Vitest/Playwright config templates.

## Initial-version invariant

The `package.json` / `pyproject.toml` `version` field, `.github/.release-please-manifest.json`, and any other version reference must all be `0.0.0` at scaffold time. release-please's first PR then cleanly bumps to `0.1.0` (assuming the first commit batch includes a `feat:`).
