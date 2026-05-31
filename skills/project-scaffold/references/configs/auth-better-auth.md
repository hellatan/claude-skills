# Authentication — Better Auth (opt-in, requires a database)

Scaffolded only when the user answered **yes** to a database at Step 4 **and** **yes** to "Add authentication?". Auth is never offered without a database — Better Auth persists users and sessions, so it depends on the Drizzle setup in `database-drizzle.md`.

**Better Auth is the default. Auth.js / NextAuth stays selectable but is never led with** — same posture as CSS Modules vs Tailwind. Generate the Auth.js path only when the user explicitly picks it.

## Better Auth (default)

- Install:
  ```bash
  npm install better-auth
  ```
- Runs in the **Node runtime** (the route handler below), so it works with the plain `postgres-js` driver from `database-drizzle.md` — no edge/serverless driver needed.

`src/lib/auth.ts`:

```ts
import { betterAuth } from 'better-auth';
import { drizzleAdapter } from 'better-auth/adapters/drizzle';
import { getDb } from '@/db';

export const auth = betterAuth({
  database: drizzleAdapter(getDb(), { provider: 'pg' }),
  emailAndPassword: { enabled: true },
  // socialProviders: { github: { clientId: ..., clientSecret: ... } },  // add as needed
});
```

`src/app/api/auth/[...all]/route.ts`:

```ts
import { toNextJsHandler } from 'better-auth/next-js';
import { auth } from '@/lib/auth';

export const { GET, POST } = toNextJsHandler(auth);
```

`src/lib/auth-client.ts`:

```ts
import { createAuthClient } from 'better-auth/react';

export const authClient = createAuthClient({
  baseURL: process.env.NEXT_PUBLIC_APP_URL,
});
```

### Schema generation flows through Drizzle

Better Auth owns its table shapes but does **not** get its own migration tool. Generate the schema, then run it through the one Drizzle pipeline from `database-drizzle.md`:

```bash
npx @better-auth/cli generate --output src/db/auth-schema.ts
npm run db:generate    # Drizzle picks up the new tables
npm run db:migrate
```

Re-export the generated tables from `src/db/schema.ts` (`export * from './auth-schema';`) so drizzle-kit sees them. Single source of truth, single migration history.

### `.env.example` (committed)

```
# Better Auth — generate the secret with: openssl rand -base64 32
BETTER_AUTH_SECRET=
BETTER_AUTH_URL=http://localhost:3000
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

In production the secret is a `sync: false` secret on the deploy target — this is the `AUTH_SECRET` placeholder already present in the Render blueprint (`gh-actions-init/references/deploy-stub.md`); rename it to `BETTER_AUTH_SECRET` and set `BETTER_AUTH_URL` to the prod URL.

## Auth.js / NextAuth (alternative — only when explicitly chosen)

- Install:
  ```bash
  npm install next-auth@beta @auth/drizzle-adapter
  ```
- `src/auth.ts`:
  ```ts
  import NextAuth from 'next-auth';
  import { DrizzleAdapter } from '@auth/drizzle-adapter';
  import { getDb } from '@/db';

  export const { handlers, auth, signIn, signOut } = NextAuth({
    adapter: DrizzleAdapter(getDb()),
    providers: [/* add providers, e.g. GitHub */],
  });
  ```
- Route handler `src/app/api/auth/[...nextauth]/route.ts`: `export { GET, POST } from '@/auth';`'s handlers (`export const { GET, POST } = handlers;`).
- Env: `AUTH_SECRET` (`npx auth secret`), plus per-provider `AUTH_<PROVIDER>_ID` / `AUTH_<PROVIDER>_SECRET`.
- The adapter's tables still flow through the same Drizzle `db:generate`/`db:migrate` pipeline.

## Why Better Auth is the default

- TS-native and owns its schema with a first-class Drizzle adapter — types line up with the rest of the stack.
- No provider lock-in; email/password works out of the box, social providers are additive config.
- Works cleanly against any of the Step 4 hosts (Neon, Render, Supabase, local) over the universal `postgres-js` connection.

Auth.js has more OAuth-provider presets and a larger community, so it stays available — but it's heavier and less TS-first, so never lead with it.
