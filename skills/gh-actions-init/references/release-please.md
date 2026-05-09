# release-please

Automates versioning, changelogs, tags, and GitHub releases via PRs driven by conventional commits. Three files:

1. `.github/workflows/release-please.yml` — the workflow
2. `.github/release-please-config.json` — release type + package config
3. `.github/.release-please-manifest.json` — current versions per package

## How it works

1. Push to `main` (typically by merging `develop` → `main`).
2. release-please scans new conventional commits since the last release.
3. It opens (or updates) a "release PR" with a generated `CHANGELOG.md` and a version bump.
4. When you merge the release PR, release-please tags the commit (e.g. `v1.2.0`) and creates a GitHub Release.
5. The tag push triggers `deploy.yml`.

## Workflow

`.github/workflows/release-please.yml`:

```yaml
name: release-please

on:
  push:
    branches: [main]

permissions:
  contents: write
  pull-requests: write

jobs:
  release-please:
    runs-on: ubuntu-latest
    steps:
      - uses: googleapis/release-please-action@v5
        with:
          config-file: .github/release-please-config.json
          manifest-file: .github/.release-please-manifest.json
```

Adjust `branches:` if the project's release branch isn't `main` (rare).

## Config — single package (most common)

`.github/release-please-config.json`:

```json
{
  "release-type": "node",
  "packages": {
    ".": {
      "release-type": "node",
      "package-name": "<project-name>",
      "changelog-path": "CHANGELOG.md",
      "include-component-in-tag": false
    }
  },
  "pull-request-title-pattern": "chore: release ${version}",
  "include-v-in-tag": true,
  "separate-pull-requests": false
}
```

`release-type` options:
- `node` — for Node/TS projects, bumps `package.json`
- `python` — for Python projects, bumps `pyproject.toml`
- `simple` — manifest-only, no language-specific version file

## Config — fullstack monorepo (frontend + backend)

```json
{
  "packages": {
    "backend": {
      "release-type": "python",
      "package-name": "<project>-backend"
    },
    "frontend": {
      "release-type": "node",
      "package-name": "<project>-frontend"
    }
  },
  "include-v-in-tag": true,
  "include-component-in-tag": false,
  "separate-pull-requests": false
}
```

**Important: `include-component-in-tag: false` matters.** Without it, release-please produces tags like `frontend-v1.2.0` and `backend-v1.2.0`, which don't match `deploy.yml`'s default `v*.*.*` trigger pattern. With it, frontend and backend release together under a single `v1.2.0` tag.

If the project needs independent release cadences, drop the line and update the deploy trigger — see `references/deploy-stub.md`.

## Manifest — match current version

`.github/.release-please-manifest.json`:

```json
{
  ".": "0.3.1"
}
```

The version here **must match** the project's current version in `package.json` / `pyproject.toml`. If they diverge, release-please's first PR generates a confusing changelog.

For brand-new projects (`project-scaffold` flow): start at `0.0.0` so the first release-please PR cleanly bumps to `0.1.0` (assuming the first batch of commits includes a `feat:`).

For retrofitting an existing project: read the current version from the project file and use it. Don't reset to `0.0.0` — that would lie about the project's history.

Monorepo manifest:

```json
{
  "backend": "0.3.1",
  "frontend": "0.3.1"
}
```

## Conventional commits cheat sheet

release-please decides version bumps from commit messages:

| Prefix | Bump | Example |
|---|---|---|
| `feat:` | minor (0.X.0) | `feat: add dark mode` |
| `fix:` | patch (0.0.X) | `fix: handle null user` |
| `feat!:` / `BREAKING CHANGE:` | major (X.0.0) | `feat!: drop legacy API` |
| `chore:` / `docs:` / `refactor:` / `test:` / `ci:` | none (shows in changelog) | `chore: bump deps` |

If the project doesn't already enforce conventional commits, surface this in the report — release-please depends on the convention to do its job. Optional follow-up: `precommit-init` could add a commit-message hook (`commitlint`) but that's a separate concern.

## Why we skip release-please if any of the three files exist

release-please's state is a delicate combo of these three files plus the project's actual git history. If a previous release-please setup has been running, its manifest version is the only correct starting point — we shouldn't overwrite it. If a config exists but the workflow doesn't (or vice versa), there's likely an in-progress migration we shouldn't disturb.

When skipping, surface this in the report:
> Skipped release-please scaffolding — `.github/release-please-config.json` already exists. If the existing setup is broken, edit it manually rather than asking me to regenerate it.
