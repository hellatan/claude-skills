# `ci.yml` — Node / TypeScript

The 5-check pipeline for Next.js or single-Node projects. Each job's `name:` must match the branch protection `contexts` exactly.

Path: `.github/workflows/ci.yml`

```yaml
name: CI

on:
  pull_request:
    branches: [develop, stage, main]
  push:
    branches: [develop, stage, main]

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  lint-typecheck:
    name: lint + typecheck
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm
      - run: npm ci
      - run: npm run lint
      - run: npm run format:check
      - run: npm run typecheck

  unit:
    name: unit tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm
      - run: npm ci
      - run: npm run test:unit

  integration:
    name: integration tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm
      - run: npm ci
      - name: Run integration tests (or pass if none)
        run: |
          if [[ -d tests/integration ]] || [[ -d src/__tests__/integration ]]; then
            npm run test:integration
          else
            echo "No integration tests yet — passing"
          fi

  e2e:
    name: e2e tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm
      - run: npm ci
      - run: npx playwright install --with-deps
      - run: npm run test:e2e

  build:
    name: production build
    runs-on: ubuntu-latest
    needs: [lint-typecheck, unit]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm
      - run: npm ci
      - run: npm run build
      - uses: actions/upload-artifact@v4
        with:
          name: build-output
          path: |
            .next/
            dist/
            build/
            out/
          retention-days: 7
          if-no-files-found: ignore
```

## Notes

- `concurrency` cancels stale runs when new commits are pushed to the same PR.
- `build` depends on `lint-typecheck` and `unit` — saves CI time if those fail.
- `if-no-files-found: ignore` on artifact upload handles different framework outputs (Next.js → `.next/`, Vite → `dist/`, etc.).
- Integration tests pass with a graceful fallback if no `tests/integration` dir exists, so newly scaffolded projects don't fail CI before the user has written any.
