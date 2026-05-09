# Deploy stub

Platform-agnostic. Triggers on `v*.*.*` tag pushes (which release-please creates when its release PR merges). User fills in the actual deploy step.

## Default tag pattern

Single-package release-please configs produce `v1.2.0` tags — matched by `tags: ['v*.*.*']`.

Monorepo configs with `include-component-in-tag: false` (the default this skill scaffolds) also produce single `v1.2.0` tags — same trigger works.

Monorepo configs with per-component tags (`frontend-v1.2.0`, `backend-v1.2.0`) need a different trigger pattern — see the "Per-component releases" section at the bottom.

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

## Per-component releases (advanced monorepo)

If the user opts out of `include-component-in-tag: false` and wants `frontend-v1.2.0` / `backend-v1.2.0` tags:

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

Default to the single-tag flow unless the user explicitly asks for per-component.

## Notes for the report

- `environment: production` and `environment: staging` map to GitHub Environments. Set those up in **repo settings → Environments** to add per-env secrets and approval gates.
- Deploy secrets use `${{ secrets.NAME }}` and live on the GitHub Environment, not in the repo.
- The TODO comments in the scaffolded file include the most common deploy patterns. The user picks one.
