# Deploy stub

Platform-agnostic. Triggers on `v*.*.*` tag pushes (which release-please creates when its release PR merges). User fills in the actual deploy step.

## Default tag pattern

Single-package release-please configs produce `v1.2.0` tags — matched by `tags: ['v*.*.*']`. A fullstack app shipped as a single unit (the single-package config applied at the repo root) uses this trigger too.

The fullstack-monorepo config in `references/release-please.md` produces **per-component** tags — `frontend-v1.2.0`, `backend-v1.2.0` — because independently-versioned packages can't share one component-less tag without stranding (see that file for the verified config and why). So a monorepo deploy needs the per-component trigger in the "Per-component releases" section below, **not** `v*.*.*`.

## Standard `deploy.yml` (prod-only, no staging)

`.github/workflows/deploy.yml`:

```yaml
name: Deploy

on:
  push:
    tags:
      - 'v*.*.*'

jobs:
  deploy-prod:
    name: Deploy to production
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v6

      # ─── HOW TO USE THIS FILE ───────────────────────────────────────
      # 1. Pick a deploy target from the list below and uncomment its block.
      # 2. Each platform needs you to fetch credentials from its dashboard
      #    (e.g., a service ID and API key for Render, a token for Vercel).
      # 3. Add each credential as a GitHub secret:
      #    repo → Settings → Environments → "production" → Add secret.
      #    The secret names must match the `${{ secrets.NAME }}` references
      #    in the block you uncommented.
      # 4. Replace the placeholder `echo "TODO ..."` line at the bottom with
      #    your build step (if your platform doesn't build for you).
      # 5. To trigger a deploy: push a tag like `v0.1.0` (release-please
      #    does this automatically when you merge a release PR).
      # 6. Watch the run under the "Actions" tab on GitHub. If it fails,
      #    the error usually points to a missing secret or wrong service ID.
      #
      # Not sure which platform to pick?
      # - You have a Next.js app and want zero-config: Vercel.
      # - You want fair pricing without lock-in, runs anything: Render.com.
      # - Backend services with global routing or CLI-first workflows: Fly.io.
      # - Already have a VPS/Linux box you control: SSH/rsync.
      # - Multi-service Docker setups (Kubernetes, ECS, etc.): GHCR.
      # ────────────────────────────────────────────────────────────────

      # TODO: Build step (or download from CI artifact). Example:
      # - uses: actions/setup-node@v6
      #   with:
      #     node-version: 22
      #     cache: npm
      # - run: npm ci && npm run build

      # TODO: Deploy step. Pick one and uncomment:
      #
      # Render.com:
      #   - uses: johnbeynon/render-deploy-action@v0.0.8
      #     with:
      #       service-id: ${{ secrets.RENDER_SERVICE_ID }}
      #       api-key: ${{ secrets.RENDER_API_KEY }}
      #
      # Vercel:
      #   - run: npx vercel deploy --prod --token=${{ secrets.VERCEL_TOKEN }}
      #
      # Fly.io:
      #   - uses: superfly/flyctl-actions/setup-flyctl@master
      #   - run: flyctl deploy --remote-only
      #     env:
      #       FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
      #
      # Railway:
      #   - uses: bervProject/railway-deploy@main
      #     with:
      #       railway_token: ${{ secrets.RAILWAY_TOKEN }}
      #       service: ${{ secrets.RAILWAY_SERVICE_NAME }}
      #
      # Docker push to GHCR:
      #   - uses: docker/login-action@v3
      #     with:
      #       registry: ghcr.io
      #       username: ${{ github.actor }}
      #       password: ${{ secrets.GITHUB_TOKEN }}
      #   - uses: docker/build-push-action@v6
      #     with:
      #       push: true
      #       tags: ghcr.io/${{ github.repository }}:${{ github.ref_name }}
      #
      # SSH/rsync to a server:
      #   - run: |
      #       echo "${{ secrets.DEPLOY_KEY }}" > deploy_key
      #       chmod 600 deploy_key
      #       rsync -avz -e "ssh -i deploy_key" dist/ user@host:/var/www/app/
      - run: echo "TODO — fill in deploy steps for production"
```

## With staging (when project uses a `stage` branch)

Detect via `git ls-remote --heads origin stage`. If `stage` exists, scaffold this variant instead:

```yaml
name: Deploy

on:
  push:
    branches: [stage]
    tags:
      - 'v*.*.*'

jobs:
  deploy-staging:
    name: Deploy to staging
    if: github.ref == 'refs/heads/stage'
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v6
      # TODO: staging deploy steps (typically point to a staging URL/instance)
      - run: echo "TODO — fill in deploy steps for staging"

  deploy-prod:
    name: Deploy to production
    if: startsWith(github.ref, 'refs/tags/v')
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v6
      # TODO: prod deploy steps
      - run: echo "TODO — fill in deploy steps for production"
```

## Render Blueprint (`render.yaml`) — opt-in, only when the target is Render

**Generate this only when the user's deploy target is Render.** If they're on Vercel, Fly, Railway, a VPS, or undecided, do **not** write a `render.yaml` — there's nothing to gain from a Render-specific file on a non-Render deploy. In that case ship only the platform-neutral `deploy.yml` stub above.

When Render *is* the target, a `render.yaml` Blueprint is dramatically better than dashboard clickops: it encodes the services in the repo, Render provisions them on apply, and prompts for the `sync: false` secrets. The dashboard becomes read-only state instead of the source of truth.

**Before writing the file, ask whether this is a free plan or a paid plan** — it changes the `plan:` values you seed (and there is no way to infer it). Seed accordingly:

| | Free | Paid |
|---|---|---|
| web service `plan:` | `free` | `starter` (bump to `standard`+ as needed) |
| Postgres `plan:` | `free` | `basic-256mb` (smallest paid tier) |
| Caveat | Free Postgres **expires after 30 days** and free web services spin down when idle — fine for demos, not for anything that must stay up. | No expiry; charged monthly. |

`render.yaml` (Next.js + Postgres example — **paid plan** shown; swap the two `plan:` lines to `free` for a free-tier blueprint, and adjust services/env to the project):

```yaml
databases:
  - name: <project>-db
    plan: basic-256mb        # paid: smallest tier. Free tier = `free`, but it expires after 30 days.
    region: oregon
    postgresMajorVersion: "16"

services:
  - type: web
    name: <project>-web
    runtime: node
    plan: starter            # paid: smallest always-on tier. Free tier = `free` (spins down when idle).
    region: oregon
    branch: main             # deploy from main (release-please tags live here)
    autoDeploy: false        # let deploy.yml / tag pushes drive deploys, not every commit
    buildCommand: npm ci && npm run db:migrate && npm run build
    startCommand: npm start
    healthCheckPath: /        # point at an endpoint that returns 200 unauthenticated
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: <project>-db
          property: connectionString
      - key: NODE_ENV
        value: production
      # Secrets — Render prompts for these on apply (never commit values):
      - key: AUTH_SECRET
        sync: false
```

Conventions to bake in:
- **Service naming**: `<project>-db`, `<project>-web`, `<project>-worker`, etc. (the `<project>-` prefix is required.)
- **`autoDeploy: false`** so deploys are driven by tags/`deploy.yml`, not every push to `main`.
- **`sync: false`** for every secret (auth secrets, API keys, credentials) — Render prompts for them on apply rather than reading from the repo.
- **Idempotent build steps** — anything in `buildCommand` (e.g. `db:migrate`, a seed) must be safe to re-run on every deploy.
- `region` is a placeholder — confirm with the user; don't assume Oregon.
- `plan` follows the free-vs-paid answer from the question above — never assume the tier; ask, then seed both the web and Postgres `plan:` lines to match.

With a Blueprint in place, `deploy.yml` still owns *when* to redeploy (trigger Render's deploy on tag push via its API/CLI); the Blueprint owns *what exists* in production.

For other known targets the equivalent IaC file is the natural analogue (Fly → `fly.toml`, Railway → `railway.toml`); generate it the same opt-in way. Vercel is mostly dashboard-driven, so `vercel.json` is optional.

## Per-component releases (standard for the fullstack monorepo)

The fullstack-monorepo release-please config produces per-component tags (`frontend-v1.2.0`, `backend-v1.2.0`), so a monorepo deploy uses this trigger:

```yaml
on:
  push:
    tags:
      - '*-v*.*.*'   # matches frontend-v1.2.0, backend-v1.2.0
      - 'v*.*.*'     # also matches single-package tags

jobs:
  deploy-prod:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - name: Determine which package
        id: which
        run: |
          tag="${GITHUB_REF#refs/tags/}"
          if [[ "$tag" =~ ^frontend-v ]]; then
            echo "package=frontend" >> $GITHUB_OUTPUT
          elif [[ "$tag" =~ ^backend-v ]]; then
            echo "package=backend" >> $GITHUB_OUTPUT
          else
            echo "package=all" >> $GITHUB_OUTPUT
          fi
      - run: echo "Deploying ${{ steps.which.outputs.package }}"
      # TODO: dispatch to per-package deploy steps
```

Use the single-tag `v*.*.*` flow only for single-package projects (or a fullstack app shipped as one unit via the single-package-at-root config). True frontend+backend monorepos use this per-component trigger.

## Notes for the report

- `environment: production` and `environment: staging` map to GitHub Environments. Set those up in **repo settings → Environments** to add per-env secrets and approval gates.
- Deploy secrets use `${{ secrets.NAME }}` and live on the GitHub Environment, not in the repo.
- The TODO comments in the scaffolded file include the most common deploy patterns. The user picks one.
