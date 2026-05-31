# Database — Drizzle ORM (opt-in)

Scaffolded only when the user answers **yes** to "Does this project need a database?" at Step 4. Skipped entirely for frontend-only, research, and library projects. Postgres is the assumed engine; Drizzle is the ORM regardless of host.

## What to scaffold

- **Drizzle ORM + drizzle-kit + drizzle-zod.** drizzle-zod generates Zod insert/select schemas from the Drizzle tables, which keeps validation in step with the stated Next.js + Drizzle + **Zod** stack.
- Install:
  ```bash
  npm install drizzle-orm postgres drizzle-zod
  npm install --save-dev drizzle-kit
  ```
- Files:
  - `drizzle.config.ts` (repo root, or `frontend/` in a subdir layout)
  - `src/db/schema.ts` — table definitions
  - `src/db/index.ts` — the client/connection
  - `drizzle/` — generated migrations (committed)
- npm scripts (add to the project `package.json`):
  ```json
  {
    "db:generate": "drizzle-kit generate",
    "db:migrate": "drizzle-kit migrate",
    "db:push": "drizzle-kit push",
    "db:studio": "drizzle-kit studio"
  }
  ```
  `db:migrate` is what the deploy `buildCommand` runs on every release (see the Render blueprint in `gh-actions-init/references/deploy-stub.md`); it must stay idempotent.

## Driver: universal `postgres-js`

Use **`postgres-js`** (`drizzle-orm/postgres-js`) for **every** host — Neon, Render, Supabase, and local. It speaks plain Postgres over the host's connection string, supports transactions (which Better Auth needs — see `auth-better-auth.md`), and avoids per-host driver branching. The only per-host difference is the value of `DATABASE_URL`.

> Neon's serverless/WebSocket driver (`@neondatabase/serverless` + `drizzle-orm/neon-serverless`) is an **opt-in** for deployments that must run on an edge runtime. Next.js route handlers and Better Auth run in the Node runtime, so the plain `postgres-js` path is the right default. Only reach for the serverless driver if the user explicitly targets edge.

`src/db/index.ts` (lazy singleton — never read `process.env` at module top-level so the build doesn't require a live `DATABASE_URL`; this matches the scaffold's env-lazy-init convention):

```ts
import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';
import * as schema from './schema';

let _db: ReturnType<typeof drizzle<typeof schema>> | undefined;

export function getDb() {
  if (!_db) {
    const url = process.env.DATABASE_URL;
    if (!url) throw new Error('DATABASE_URL is not set');
    // `prepare: false` is required behind a transaction pooler (Neon -pooler, Supabase :6543).
    _db = drizzle(postgres(url, { prepare: false }), { schema });
  }
  return _db;
}
```

`drizzle.config.ts`:

```ts
import { defineConfig } from 'drizzle-kit';

export default defineConfig({
  schema: './src/db/schema.ts',
  out: './drizzle',
  dialect: 'postgresql',
  dbCredentials: { url: process.env.DATABASE_URL! },
});
```

`src/db/schema.ts` ships with one illustrative table so `db:generate` produces a first migration:

```ts
import { pgTable, serial, text, timestamp } from 'drizzle-orm/pg-core';
import { createInsertSchema, createSelectSchema } from 'drizzle-zod';

export const examples = pgTable('examples', {
  id: serial('id').primaryKey(),
  label: text('label').notNull(),
  createdAt: timestamp('created_at').defaultNow().notNull(),
});

export const insertExampleSchema = createInsertSchema(examples);
export const selectExampleSchema = createSelectSchema(examples);
```

## `.env.example` (committed) + connection strings

Add to the committed `.env.example`:

```
# Postgres connection string. Use a POOLED URL behind a transaction pooler in prod.
DATABASE_URL=
```

Per-host guidance — seed the comment for the host the user picked:

| Host (Step 4 choice) | Where the URL comes from | Notes |
|---|---|---|
| **Neon** (default) | neon.tech → project → **Pooled** connection string (host contains `-pooler`) | Serverless, branchable, generous free tier. Use the pooled URL; keep `prepare: false`. |
| **Render Postgres** | render.yaml `fromDatabase` wires it automatically; locally copy the External URL | Pairs with the `databases:` block in `deploy-stub.md`. Free tier expires after 30 days. |
| **Supabase** | Project → Settings → Database → **Connection pooler** URI (port `6543`, pgbouncer) | Use the pooler URI in prod, not the direct `5432` URL. `prepare: false` required. |
| **Local Docker** | `postgres://postgres:postgres@localhost:5432/<project>` | Ship a `docker-compose.yml` with a `postgres:18` service so `npm run db:push` works offline. |

## Host choice → deploy blueprint

The Step 4 host answer determines which `render.yaml` variant `gh-actions-init` emits (see `gh-actions-init/references/deploy-stub.md`):

- **Render Postgres** → a `databases:` block + `DATABASE_URL` via `fromDatabase`.
- **Neon / Supabase / local** → no `databases:` block; `DATABASE_URL` is a `sync: false` secret pointing at the external host.

## Migration pipeline (single path)

One pipeline owns the schema: edit `src/db/schema.ts` → `npm run db:generate` (writes SQL to `drizzle/`) → `npm run db:migrate`. When auth is added, Better Auth's generated tables flow through this **same** `db:generate`/`db:migrate` pipeline — no second migration tool (see `auth-better-auth.md`).
