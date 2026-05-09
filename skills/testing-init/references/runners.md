# Runner configs + dev deps

## Node + Vitest (unit)

### Install

Plain Node/TS:
```bash
npm install --save-dev vitest
```

React (Next.js, Vite-React, etc.):
```bash
npm install --save-dev vitest @vitejs/plugin-react jsdom @testing-library/react @testing-library/jest-dom
```

### `vitest.config.ts`

Plain Node/TS (backend, library):
```typescript
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'node',
    globals: true,
    exclude: ['**/node_modules/**', '**/dist/**', '**/build/**', '**/e2e/**'],
  },
});
```

React (frontend):
```typescript
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    exclude: ['**/node_modules/**', '**/dist/**', '**/.next/**', '**/e2e/**'],
  },
});
```

**Critical: `**/e2e/**` exclude is required.** Without it, `npm run test` tries to run Playwright `*.spec.ts` files with Vitest and crashes — Vitest's default exclude doesn't cover `e2e/` because it's outside the `__tests__/` convention.

---

## Node + Playwright (e2e)

### Install

```bash
npm install --save-dev @playwright/test
npx playwright install --with-deps  # browsers; slow first time, idempotent
```

### `playwright.config.ts`

```typescript
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  use: {
    baseURL: 'http://localhost:3000',
  },
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
  },
});
```

Adjust `baseURL` and `webServer.command` if the project's dev server runs on a different port or via a different command.

For backend-only projects with no UI: skip Playwright entirely.

---

## Python + pytest

### Install

Add to `pyproject.toml`:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
]
```

Or for uv-managed projects:

```toml
[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
]
```

Then:
```bash
pip install -e ".[dev]"   # standard
uv sync                   # uv-managed
```

### `[tool.pytest.ini_options]` block in `pyproject.toml`

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--strict-markers",
    "--strict-config",
    "-ra",
]
markers = [
    "integration: marks integration tests (deselect with '-m \"not integration\"')",
    "e2e: marks end-to-end tests (deselect with '-m \"not e2e\"')",
]
```

The marker setup lets users filter:
- `pytest -m "not integration"` — unit only
- `pytest -m "integration"` — integration only
- `pytest` — everything

---

## Why these picks

- **Vitest over Jest** — faster (native Vite), native ESM/TS, smaller config. Jest's edge is plugin ecosystem; most projects don't need it.
- **Playwright over Cypress** — multi-browser, built-in runner, no separate dashboard process.
- **pytest** — Python's de facto standard. Don't introduce `nose` / `unittest` boilerplate unless the user explicitly asks.
