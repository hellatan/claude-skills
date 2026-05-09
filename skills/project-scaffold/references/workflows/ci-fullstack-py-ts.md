# `ci.yml` — Fullstack (Python BE + TS FE)

5-check pipeline for the most common fullstack combo. Status check names match branch protection `contexts` exactly.

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

      # Backend
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - working-directory: backend
        run: |
          pip install -e ".[dev]"
          ruff check .
          ruff format --check .
          mypy .

      # Frontend
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - working-directory: frontend
        run: |
          npm ci
          npm run lint
          npm run format:check
          npm run typecheck

  unit:
    name: unit tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - working-directory: backend
        run: |
          pip install -e ".[dev]"
          pytest -m "not integration and not e2e"
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - working-directory: frontend
        run: |
          npm ci
          npm run test:unit

  integration:
    name: integration tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - working-directory: backend
        run: |
          pip install -e ".[dev]"
          pytest -m integration

  e2e:
    name: e2e tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - working-directory: frontend
        run: |
          npm ci
          npx playwright install --with-deps
          npm run test:e2e

  build:
    name: production build
    runs-on: ubuntu-latest
    needs: [lint-typecheck, unit]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - working-directory: backend
        run: |
          pip install build
          python -m build
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - working-directory: frontend
        run: |
          npm ci
          npm run build
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
