# Next.js Scaffold

Default frontend (and "fullstack-collapsed") choice. Use `create-next-app` for the actual scaffold so we don't have to maintain a hand-rolled boilerplate.

## Install

For a frontend-only project, scaffold at repo root:

```bash
npx create-next-app@latest . \
  --typescript \
  --eslint \
  --app \
  --src-dir \
  --import-alias "@/*" \
  --use-npm \
  --no-tailwind \
  --no-turbopack \
  --skip-git
```

Flags explained:
- `--typescript` — TypeScript out of the box
- `--eslint` — ESLint configured
- `--app` — App Router (the modern Next.js paradigm)
- `--src-dir` — code lives in `src/` (cleaner separation)
- `--import-alias "@/*"` — `@/components/Button` style imports
- `--no-tailwind` — leave styling choice to the user (they can add Tailwind, CSS modules, styled-components, etc.)
- `--no-turbopack` — skip Turbopack prompt; project can opt in later if desired
- `--skip-git` — skill handles `git init` at the repo root in Step 15 (otherwise create-next-app initializes its own `.git/` and conflicts with later git-init)

For a fullstack project where the frontend is in a subdirectory:

```bash
npx create-next-app@latest frontend \
  --typescript \
  --eslint \
  --app \
  --src-dir \
  --import-alias "@/*" \
  --use-npm \
  --no-tailwind \
  --no-turbopack \
  --skip-git
```

## Post-scaffold cleanup (BEFORE other customizations)

`create-next-app` leaves behind files the skill needs to handle:

- **`AGENTS.md`** — Next 16+ ships this as a heads-up about breaking changes for AI tools. Keep it as-is, it's useful context for any LLM working on the project.
- **`CLAUDE.md`** — Next 16+ ships a stub. **Delete it** — the skill writes its own CLAUDE.md at repo root in Step 10. Keeping the Next stub creates two CLAUDE.md files (subdir vs root) that conflict.
- **`.git/`** — should not exist if `--skip-git` was passed. If it does (older create-next-app), remove it before the skill's `git init`:
  ```bash
  rm -rf .git AGENTS.md CLAUDE.md  # adjust based on which exist
  ```

For the **subdir** install path, this cleanup happens in `frontend/`:
```bash
rm -rf frontend/.git frontend/CLAUDE.md
# Keep frontend/AGENTS.md — it's useful Next-specific context
```

## Post-scaffold customizations

After `create-next-app` runs, the skill should:

1. **Install additional dev deps** that match the rest of the toolchain:

```bash
npm install --save-dev \
  prettier \
  @ianvs/prettier-plugin-sort-imports \
  vitest \
  @vitejs/plugin-react \
  jsdom \
  @testing-library/react \
  @testing-library/jest-dom \
  @playwright/test
```

**Do NOT install** `@eslint/js`, `typescript-eslint`, or `eslint-config-prettier` — they conflict with `eslint-config-next`'s pinned versions and produce ERESOLVE errors. Next's flat config already provides everything they'd add (except `@typescript-eslint/consistent-type-imports`, which works fine when extending Next's config without those packages).

2. **Extend the default `eslint.config.mjs`** that `create-next-app` generates rather than replacing it. Add the `@typescript-eslint/consistent-type-imports` rule via Next's config:

```js
// eslint.config.mjs (extending what create-next-app generated)
import { FlatCompat } from '@eslint/eslintrc';

const compat = new FlatCompat({ baseDirectory: import.meta.dirname });

const eslintConfig = [
  ...compat.extends('next/core-web-vitals', 'next/typescript'),
  {
    rules: {
      '@typescript-eslint/consistent-type-imports': 'error',
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
    },
  },
  {
    ignores: ['.next/', 'out/', 'dist/', 'node_modules/', 'coverage/'],
  },
];

export default eslintConfig;
```

3. **Write `.prettierrc`** with the type-imports-first sort plugin (see `node-ts.md`).

4. **Run `npx prettier --write .` once after writing `.prettierrc`** to reformat `eslint.config.mjs` and any other files `create-next-app` left in non-prettier style. Otherwise CI's `format:check` will fail on first push, and the skill's smoke test in Step 20 would only catch it after several minutes of confusion.

5. **Set initial version to `0.0.0`** in `package.json` so release-please's first release PR cleanly bumps to `0.1.0`.

6. **Add scripts** for the canonical commands:

```json
{
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "format": "prettier --write .",
    "format:check": "prettier --check .",
    "typecheck": "tsc --noEmit",
    "test": "vitest run",
    "test:unit": "vitest run --dir src",
    "test:integration": "vitest run --dir tests/integration",
    "test:e2e": "playwright test",
    "check:all": "npm run lint && npm run format:check && npm run typecheck && npm run test"
  }
}
```

7. **Scaffold smoke-test stubs** so CI doesn't fail on first push:

`src/__tests__/smoke.test.ts`:
```typescript
import { describe, it, expect } from 'vitest';

describe('smoke', () => {
  it('passes', () => {
    expect(1).toBe(1);
  });
});
```

`e2e/smoke.spec.ts` (after `npx playwright install --with-deps`):
```typescript
import { test, expect } from '@playwright/test';

test('homepage loads', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/.*/);
});
```

`playwright.config.ts`:
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

8. **Vitest config** (`vitest.config.ts`):
```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    // Exclude Playwright e2e tests — they have their own runner
    exclude: ['**/node_modules/**', '**/dist/**', '**/.next/**', '**/e2e/**'],
  },
});
```

**Important:** without the `**/e2e/**` exclude, `npm run test` tries to run Playwright `*.spec.ts` files with Vitest and crashes. Vitest's default exclude doesn't cover `e2e/` because it's outside `__tests__/` convention.
