# `deploy.yml` — Deploy stub

Platform-agnostic. The user fills in actual deploy commands based on their target. Supports an optional staging environment via the `stage` branch.

Path: `.github/workflows/deploy.yml`

## A note about tag patterns

Single-package release-please configs produce tags like `v1.2.0`. The default trigger `tags: ["v*.*.*"]` matches these.

**Fullstack monorepo** release-please configs (with separate frontend/backend packages) produce per-package tags like `frontend-v1.2.0` and `backend-v1.2.0` — NOT a single `v1.2.0`. The default trigger won't fire on those.

For monorepo, either:

**Option 1**: Set `include-component-in-tag: false` in `release-please-config.json` and pick **one** package as "the release" — clean for projects where frontend and backend always ship together.

**Option 2**: Change the deploy trigger to `tags: ["*-v*.*.*"]` and dispatch per-component:

```yaml
on:
  push:
    tags:
      - "*-v*.*.*"   # matches frontend-v1.2.0, backend-v1.2.0
      - "v*.*.*"     # also matches single-package tags

jobs:
  deploy-prod:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
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
      # TODO: dispatch to per-package deploy steps based on steps.which.outputs.package
```

The skill defaults to **Option 1** for simplicity (frontend and backend ship together). If user opts into per-component releases later, switch to Option 2.

---

## Prod-only (default — no staging)

```yaml
name: Deploy

on:
  push:
    tags:
      - "v*.*.*"

jobs:
  deploy-prod:
    name: Deploy to production
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4

      # TODO: Add your build step here (or download from CI artifact)
      # Example:
      # - uses: actions/setup-node@v4
      #   with:
      #     node-version: 22
      # - run: npm ci && npm run build

      # TODO: Add your deploy step here. Examples below — uncomment one:
      #
      # Vercel (most familiar, Next.js-native):
      #   - run: npx vercel deploy --prod --token=${{ secrets.VERCEL_TOKEN }}
      #
      # Render (easy setup, fair pricing, no vendor lock):
      #   - uses: johnbeynon/render-deploy-action@v0.0.8
      #     with:
      #       service-id: ${{ secrets.RENDER_SERVICE_ID }}
      #       api-key: ${{ secrets.RENDER_API_KEY }}
      #
      # Fly.io (good for backend services, distributed compute):
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

## With staging (when user opts in)

```yaml
name: Deploy

on:
  push:
    branches: [stage]
    tags:
      - "v*.*.*"

jobs:
  deploy-staging:
    name: Deploy to staging
    if: github.ref == 'refs/heads/stage'
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v4
      # TODO: staging deploy steps (typically point to a staging URL/instance)
      - run: echo "TODO — fill in deploy steps for staging"

  deploy-prod:
    name: Deploy to production
    if: startsWith(github.ref, 'refs/tags/v')
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4
      # TODO: prod deploy steps
      - run: echo "TODO — fill in deploy steps for production"
```

## Notes

- `environment: production` and `environment: staging` map to GitHub Environments. Set those up in repo settings → Environments to add per-env secrets and approval gates.
- The TODO comments include the most common deploy patterns. Pick one and uncomment.
- Don't put deploy secrets in the repo. Use `${{ secrets.NAME }}` and add them to the GitHub Environment.
- For monorepo deploys (frontend + backend), see the tag pattern note at the top of this file.
