# Optional CI test job

Only invoked if the user opted in at flow Step 4. Two paths:

## Path 1: `.github/workflows/ci.yml` already exists

**Extend it, don't replace.** Add the test jobs, preserving any existing jobs (lint, build, etc.). Detect existing jobs by name first:

```bash
existing_jobs=$(yq '.jobs | keys' .github/workflows/ci.yml 2>/dev/null || echo "")
```

(If `yq` isn't installed, just read the file and grep.)

For each scope the user chose, add the matching job *if it doesn't already exist*:

### Unit (always)

```yaml
  unit:
    name: unit tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-node@v6   # for Node projects
        with:
          node-version: 22
          cache: npm
      - run: npm ci
      - run: npm run test:unit
```

For Python:
```yaml
  unit:
    name: unit tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with:
          python-version: '3.12'
      - run: pip install -e ".[dev]"
      - run: pytest -m "not integration and not e2e"
```

### Integration (if scoped in)

```yaml
  integration:
    name: integration tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-node@v6
        with:
          node-version: 22
          cache: npm
      - run: npm ci
      - run: npm run test:integration
```

Python equivalent: `pytest -m integration`.

### E2E (if scoped in, Node only)

```yaml
  e2e:
    name: e2e tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-node@v6
        with:
          node-version: 22
          cache: npm
      - run: npm ci
      - run: npx playwright install --with-deps
      - run: npm run test:e2e
```

## Path 2: No `.github/workflows/ci.yml` yet

Create a minimal one with just the test jobs the user chose. Don't include lint/typecheck/build — those belong to `gh-actions-init` (which can extend this CI later).

```yaml
name: CI

on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [main, develop]

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  # ... only the test jobs the user opted into
```

## Top-of-file conventions

- `concurrency.cancel-in-progress: true` — cancels stale runs when new commits push to the same PR.
- `cache: npm` — speeds up Node installs by ~10s.
- `node-version: 22` — current LTS at scaffold time. Update if the project pins a different version in `engines.node` or `.nvmrc`.

## Match existing branch names

If the repo uses `master` or some other default branch instead of `main`, use that in the `on.push.branches` / `on.pull_request.branches` arrays. Detect with:

```bash
git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@'
```
