# `ci.yml` — Python

The 5-check pipeline for FastAPI or single-Python projects. Each job's `name:` must match the branch protection `contexts` exactly.

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
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: pip install -e ".[dev]"
      - run: ruff check .
      - run: ruff format --check .
      - run: mypy .

  unit:
    name: unit tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: pip install -e ".[dev]"
      - run: pytest -m "not integration and not e2e" --cov

  integration:
    name: integration tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: pip install -e ".[dev]"
      - run: pytest -m integration

  e2e:
    name: e2e tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: pip install -e ".[dev]"
      - run: pytest -m e2e

  build:
    name: production build
    runs-on: ubuntu-latest
    needs: [lint-typecheck, unit]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: pip install build
      - run: python -m build
      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/
          retention-days: 7
```

## Notes

- The `pytest` markers (`integration`, `e2e`) come from the `[tool.pytest.ini_options]` block in `pyproject.toml`.
- For research projects, simplify drastically — typically just lint + a smoke-test job.
- For projects using `uv`: replace `pip install -e ".[dev]"` with `uv sync --dev` and add an `astral-sh/setup-uv@v3` step.
