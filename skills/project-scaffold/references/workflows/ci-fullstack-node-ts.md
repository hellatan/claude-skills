# `ci.yml` — Fullstack (Node BE + TS FE, npm workspaces)

5-check pipeline for Node + Node fullstack with npm workspaces. Status check names match branch protection `contexts` exactly.

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
      - run: npm run test --workspaces --if-present

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
          if [[ -d backend/tests/integration ]]; then
            npm --workspace=backend run test:integration
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
      - run: npm --workspace=frontend run test:e2e

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
            backend/dist/
            frontend/.next/
            frontend/dist/
            frontend/out/
          retention-days: 7
          if-no-files-found: ignore
```

## Notes

- npm workspaces means one `npm ci` at root installs everything across all workspaces — no per-workspace install needed.
- `--workspaces --if-present` runs scripts that exist in any workspace, skipping ones that don't have a given script.
- For non-workspaces fullstack (two independent Node projects), use the Python+TS fullstack pattern but swap Python for Node — separate `npm ci` per directory.
