# Node / TypeScript Generic Configs

Shared reference for Next.js and Fastify scaffolds. The framework-specific files (`nextjs.md`, `nodejs-backend.md`) will reference parts of this when building the actual config.

---

## `.prettierrc` — type-imports-first

Includes `@ianvs/prettier-plugin-sort-imports` to enforce **type imports first, value imports second**, both alphabetized within their group.

```json
{
  "semi": true,
  "singleQuote": true,
  "trailingComma": "all",
  "printWidth": 100,
  "tabWidth": 2,
  "arrowParens": "always",
  "endOfLine": "lf",
  "plugins": ["@ianvs/prettier-plugin-sort-imports"],
  "importOrder": [
    "<TYPES>^(node:)",
    "<TYPES>",
    "<TYPES>^[.]",
    "",
    "<BUILTIN_MODULES>",
    "<THIRD_PARTY_MODULES>",
    "",
    "^@/(.*)$",
    "",
    "^[./]"
  ],
  "importOrderTypeScriptVersion": "5.0.0"
}
```

Required dev dep:
```bash
npm install --save-dev @ianvs/prettier-plugin-sort-imports
```

### What this produces

```ts
// Type imports — grouped first, sorted within their group
import type { Server } from 'node:http';
import type { FC, ReactNode } from 'react';
import type { User } from '@/types/user';
import type { Props } from './types';

// Value imports — second
import { readFile } from 'node:fs/promises';
import { useEffect, useState } from 'react';
import { Button } from '@/components/Button';
import { formatDate } from './utils';
```

### Why prettier and not eslint

`eslint-plugin-import`'s `import/order` rule can also sort, but it fights with prettier on whitespace and doesn't cleanly separate type vs value imports. Doing it in prettier means the sort is deterministic, runs as part of `format`, and pre-commit catches it on every commit. ESLint still owns `@typescript-eslint/consistent-type-imports` (forces `import type` when imports are type-only) — the two work together.

---

## `.prettierignore`

```
node_modules/
dist/
build/
.next/
out/
coverage/
*.lock
package-lock.json
```

---

## `eslint.config.js` — flat config (ESLint 9+)

```js
import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import prettier from 'eslint-config-prettier';

export default tseslint.config(
  js.configs.recommended,
  ...tseslint.configs.recommended,
  prettier,
  {
    rules: {
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
      '@typescript-eslint/consistent-type-imports': 'error',
    },
  },
  {
    ignores: ['dist/', 'build/', '.next/', 'out/', 'node_modules/', 'coverage/'],
  },
);
```

Required dev deps:
```bash
npm install --save-dev eslint @eslint/js typescript-eslint eslint-config-prettier
```

### Important: ESLint config-at-cwd (monorepo gotcha)

ESLint 9's flat config looks for `eslint.config.js` (or `.mjs`/`.ts`) **in the current working directory** — not in any parent.

For **fullstack repos with frontend in subdir**, this means:

- `frontend/eslint.config.js` works fine when running `eslint` from `frontend/`
- It does NOT work when pre-commit runs eslint from repo root
- The pre-commit hook must `cd frontend && npx eslint <files>` (handled in `precommit-unified.md`)

If you ever see "no config found" errors, double-check where eslint was invoked from.
