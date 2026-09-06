# Node.js Backend (Fastify)

Use this only when the user explicitly opted for a separate Node backend instead of the Next.js-only fullstack default (which handles backend via API routes).

## Install

```bash
npm init -y
npm install fastify
npm install --save-dev \
  typescript \
  tsx \
  @types/node \
  vitest \
  @ianvs/prettier-plugin-sort-imports \
  prettier \
  eslint \
  @eslint/js \
  typescript-eslint \
  eslint-config-prettier
```

## `package.json` scripts

```json
{
  "name": "<project-name>",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "tsx watch --env-file=.env src/index.ts",
    "build": "tsc",
    "start": "node --env-file-if-exists=.env dist/index.js",
    "lint": "eslint .",
    "lint:fix": "eslint . --fix",
    "format": "prettier --write .",
    "format:check": "prettier --check .",
    "typecheck": "tsc --noEmit",
    "test": "vitest run",
    "test:unit": "vitest run --dir src",
    "test:integration": "vitest run --dir tests/integration",
    "check:all": "npm run lint && npm run format:check && npm run typecheck && npm run test"
  }
}
```

## Environment — the file is `.env`

Nothing in this stack reads an env file on its own: bare `node` and `tsx` both leave
`process.env` alone, so without a flag every `process.env.X` is `undefined` with no error.
Node's own `--env-file` is the loader — no `dotenv` dependency needed (Node >= 20.12). `tsx`
forwards the flag through to node, verified on tsx 4 / Node 24.

The two scripts want different behaviour, which is why the flags differ:

- **`dev` uses `--env-file=.env`** — it *hard-errors* (`node: .env: not found`, non-zero exit)
  when the file is missing. That is the right failure for local dev: the developer has not
  copied `.env.example` yet, and the error names the exact file to create.
- **`start` uses `--env-file-if-exists=.env`** — in production the values come from the
  platform (a container env, a systemd `EnvironmentFile=`, a host dashboard) and there is
  usually no `.env` on disk at all. This form prints a one-line notice on stdout and
  continues. Never use `--env-file=` here; it would make every deploy fail.

Ship a committed `.env.example` whose first line names the file to create. `.env.local` is
not a thing in this stack — Node has no notion of it.

## `tsconfig.json`

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022"],
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true,
    "noFallthroughCasesInSwitch": true,
    "esModuleInterop": true,
    "resolveJsonModule": true,
    "skipLibCheck": true,
    "outDir": "dist",
    "rootDir": "src",
    "declaration": true,
    "sourceMap": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src", "tests"],
  "exclude": ["node_modules", "dist"]
}
```

## `eslint.config.js`

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
      // Require braces on every control statement, even single-line bodies.
      // ESLint inserts the braces (autofixable); Prettier then formats the block.
      curly: ['error', 'all'],
    },
  },
  {
    ignores: ['dist/', 'build/', 'node_modules/', 'coverage/'],
  },
);
```

## `.prettierrc`

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

This produces type imports first (alphabetized), then a blank line, then value imports (alphabetized within their groups: built-ins → third-party → `@/*` aliases → relative). See `node-ts.md` for the full output example.

## `.prettierignore`

```
node_modules/
dist/
build/
coverage/
*.lock
package-lock.json

# release-please owns and rewrites both of these on every release PR — keep prettier off them.
CHANGELOG.md
.github/.release-please-manifest.json

# Prettier's YAML formatting mangles hand-maintained GitHub Actions workflow
# files (reflowing inline comments) for zero benefit — skip all YAML.
*.yml
*.yaml
```

The release-please carve-outs and the YAML rationale are the same as the shared config — see `node-ts.md`, "`.prettierignore`".

## Stub source file

`src/index.ts`:
```typescript
import Fastify from 'fastify';

const app = Fastify({ logger: true });

app.get('/', async () => ({ status: 'ok' }));

const start = async () => {
  try {
    await app.listen({ port: 3000, host: '0.0.0.0' });
  } catch (err) {
    app.log.error(err);
    process.exit(1);
  }
};

start();
```

## Stub test

`src/__tests__/smoke.test.ts`:
```typescript
import { describe, it, expect } from 'vitest';

describe('smoke', () => {
  it('passes', () => {
    expect(1).toBe(1);
  });
});
```
