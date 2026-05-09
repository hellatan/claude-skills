# release-please

Automates versioning, changelogs, tags, and GitHub releases via PRs driven by conventional commits.

## How it works

1. Push to `main` (typically by merging `develop` → `main`, or `develop` → `stage` → `main` if staging is enabled).
2. release-please scans new conventional commits since the last release.
3. It opens (or updates) a "release PR" with a generated `CHANGELOG.md` and version bump.
4. When you merge the release PR, release-please tags the commit (e.g. `v1.2.0`) and creates a GitHub Release.
5. The tag push triggers `deploy.yml`.

## `.github/workflows/release-please.yml`

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
      - uses: googleapis/release-please-action@v4
        with:
          config-file: .github/release-please-config.json
          manifest-file: .github/.release-please-manifest.json
```

## `.github/release-please-config.json`

For a single-package repo (most common):

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

For **fullstack** repos with separate frontend/backend:

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

**Important: `include-component-in-tag: false` matters here.** Without it, release-please produces tags like `frontend-v1.2.0` and `backend-v1.2.0`, which don't match `deploy.yml`'s default `v*.*.*` trigger pattern. With it, release-please produces a single `v1.2.0` tag — frontend and backend always release together.

If the project needs to release frontend and backend on independent cadences, drop `include-component-in-tag: false` and update `deploy.yml`'s tag pattern (see `deploy.md` for the alternate pattern).

## `.github/.release-please-manifest.json`

**Always start at `0.0.0`.** This way the first real release-please PR cleanly bumps to `0.1.0` (assuming the first batch of commits includes a `feat:`).

Single package:
```json
{
  ".": "0.0.0"
}
```

Monorepo:
```json
{
  "backend": "0.0.0",
  "frontend": "0.0.0"
}
```

## Critical: keep manifest in sync with project files

The manifest version (`0.0.0`) **must match** the version in:
- `package.json` (`"version": "0.0.0"`)
- `pyproject.toml` (`version = "0.0.0"`)

If they diverge, release-please's first PR generates a confusing changelog. The skill must scaffold all three with `0.0.0`.

## Conventional commits cheat sheet

release-please reads commit messages to decide version bumps:

- `feat: ...` → minor bump (0.X.0)
- `fix: ...` → patch bump (0.0.X)
- `feat!: ...` or `fix!: ...` or footer with `BREAKING CHANGE:` → major bump (X.0.0)
- `chore:`, `docs:`, `style:`, `refactor:`, `test:`, `ci:` → no version bump, but show in changelog

The CLAUDE.md template already says "conventional commits required" — this is why.
