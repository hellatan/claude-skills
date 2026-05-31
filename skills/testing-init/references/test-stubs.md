# Test stubs

Smoke tests that pass on first run. These exercise the runner end-to-end so you know the install + config is correct, without prescribing project-specific test logic.

**Don't overwrite existing test files.** If a path already exists, skip and note it in the report.

## Node + Vitest — unit

`src/__tests__/smoke.test.ts`:

```typescript
import { describe, expect, it } from 'vitest';

describe('smoke', () => {
  it('passes', () => {
    expect(1).toBe(1);
  });
});
```

## Node + Vitest — integration (if scoped in)

`tests/integration/smoke.test.ts`:

```typescript
import { describe, expect, it } from 'vitest';

describe('integration smoke', () => {
  it('passes', () => {
    expect(true).toBe(true);
  });
});
```

(Without an existing integration target — db, external service, etc. — the stub is intentionally trivial. Replace with a real integration test as soon as the user has something to integrate against.)

## Node + Playwright — e2e

`e2e/smoke.spec.ts`:

```typescript
import { expect, test } from '@playwright/test';

test('homepage loads', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/.*/);
});
```

This loads the homepage and asserts a title exists — minimal but enough to confirm the dev server boots and Playwright can drive a browser. The `/.*/ ` regex passes for any non-empty title, so it works pre-feature.

For backend-only projects, skip e2e entirely.

## Python + pytest — unit

`tests/test_smoke.py`:

```python
def test_smoke():
    assert 1 == 1
```

If the project doesn't already have a `tests/` directory, create it and add an empty `tests/__init__.py` (some pytest configs need it for discovery; harmless to add).

## Python + pytest — integration (if scoped in)

`tests/integration/test_smoke.py`:

```python
import pytest


@pytest.mark.integration
def test_integration_smoke():
    assert True
```

The `integration` marker matches the `[tool.pytest.ini_options].markers` declared in `pyproject.toml`, so `pytest -m "not integration"` filters these out for fast local runs.
