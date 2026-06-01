# CI structure jobs (lint + typecheck + format:check + build)

The structural CI jobs that compose with `testing-init`'s test jobs to form the full 5-check pipeline. This skill writes only the *non-test* jobs.

## Node / TypeScript

`.github/workflows/ci.yml` — minimal version when no existing CI exists:

```yaml
name: CI

on:
  pull_request:
    branches: [main, develop]   # adjust per branch detection
  push:
    branches: [main, develop]
  workflow_dispatch:            # manual "rebuild now" + dispatch target for /rebuild

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  lint-typecheck:
    name: lint + typecheck
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-node@v6
        with:
          node-version: 22       # adjust if package.json pins engines.node
          cache: npm
      - run: npm ci
      - run: npm run lint
      - run: npm run format:check   # only if format:check exists in package.json
      - run: npm run typecheck

  build:
    name: production build
    runs-on: ubuntu-latest
    needs: [lint-typecheck]
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-node@v6
        with:
          node-version: 22
          cache: npm
      - run: npm ci
      - run: npm run build
      - uses: actions/upload-artifact@v7
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

Notes:
- `concurrency` cancels stale runs on the same PR.
- `build` depends on `lint-typecheck` so a broken lint doesn't waste build time.
- `if-no-files-found: ignore` on the artifact handles different framework outputs (Next → `.next/`, Vite → `dist/`, etc.).
- Skip `format:check` step if `prettier` isn't in dev deps or no `format:check` script exists.

## Python

```yaml
name: CI

on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [main, develop]
  workflow_dispatch:            # manual "rebuild now" + dispatch target for /rebuild

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  lint:
    name: lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with:
          python-version: '3.12'
      - run: pip install -e ".[dev]"
      - run: ruff check .
      - run: ruff format --check .

  typecheck:
    name: typecheck
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with:
          python-version: '3.12'
      - run: pip install -e ".[dev]"
      - run: mypy .
```

Notes:
- No `build` job — Python apps deploy source.
- Skip `typecheck` job if `mypy` isn't in dev deps.
- For uv-managed projects, replace `pip install -e ".[dev]"` with `uv sync`.

## Fullstack (Node frontend + Python backend)

Two strategies:

**a. Single workflow, no path filters** — both sides run on every push. Simple, slower.
**b. Path-filtered jobs** — frontend jobs only run if `frontend/**` changed, etc. Faster, more complex YAML.

Default to (a) for clarity. Surface (b) as an option if the user mentions slow CI.

```yaml
jobs:
  frontend-lint-typecheck:
    name: frontend lint + typecheck
    # ... Node steps, but:
    # - run: npm --prefix frontend ci
    # - run: npm --prefix frontend run lint
    # ...

  backend-lint-typecheck:
    name: backend lint + typecheck
    # ... Python steps, but operating in backend/

  build:
    name: production build
    needs: [frontend-lint-typecheck, backend-lint-typecheck]
    # ... build the side that needs it
```

## Extend-mode rules

When `ci.yml` already exists (e.g., `testing-init` ran first):

1. **Read the existing file** — preserve indentation style, top-level keys, comments.
2. **Identify existing job names** via `yq '.jobs | keys' .github/workflows/ci.yml` or grep fallback.
3. **For each new job**, check if `name:` already appears (in the YAML `name:` value, NOT the YAML key — the value is what shows up as the GH Actions check name). Skip if present.
4. **Don't change `on:` triggers** in an existing workflow. If they look stale (e.g., only `[main]` when the project also has `develop`), surface a warning, don't auto-fix.
5. **Match indentation** — read the first job in the file and match its leading-spaces level (typically 2 or 4).
6. **Append new jobs at the end** of the `jobs:` block, separated by a blank line.

If the existing `ci.yml` is structured very differently (e.g., uses reusable workflows, matrix strategies, etc.) and your simple append would conflict: **stop and ask**. Don't try to be clever.

## Job-name → branch-protection-context mapping

Each job's `name:` field is what GitHub branch protection uses as a "required status check context." The job names this skill writes match what `project-scaffold`'s branch protection script expects:

- `lint + typecheck`
- `production build`
- (Tests come from `testing-init`: `unit tests`, `integration tests`, `e2e tests`)

Don't rename these without also updating any branch protection contexts, or protection silently breaks (the new check is required but the new job isn't producing it).
