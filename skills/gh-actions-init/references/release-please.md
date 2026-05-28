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
  "$schema": "https://raw.githubusercontent.com/googleapis/release-please/main/schemas/config.json",
  "packages": {
    ".": {
      "release-type": "node",
      "include-component-in-tag": false,
      "bump-minor-pre-major": true,
      "bump-patch-for-minor-pre-major": false
    }
  },
  "include-v-in-tag": true,
  "pull-request-title-pattern": "chore: release${component} ${version}",
  "group-pull-request-title-pattern": "chore: release${component} ${version}"
}
```

This exact shape was verified end-to-end on a throwaway repo: a real `feat` commit produced a `chore: release X.Y.Z` PR that, on merge, automatically created a clean `vX.Y.Z` tag + GitHub release with zero manual steps. Two non-obvious requirements make it work:

- **No `package-name`.** With an explicit `package-name` *and* `include-component-in-tag: false`, release-please expects the package's component in the merged release-PR title to associate the release — but `include-component-in-tag: false` strips the component from the title. They never match, so release-please logs `PR component: undefined does not match configured component: <name>` and **silently skips creating the tag/release** ([googleapis/release-please#2214](https://github.com/googleapis/release-please/issues/2214)). Omitting `package-name` makes release-please match by path (`.`) instead, which round-trips correctly and still yields clean `vX.Y.Z` tags. (`changelog-path` is also omitted — `CHANGELOG.md` is the default.)
- **`group-pull-request-title-pattern` is required, not just `pull-request-title-pattern`.** In grouped mode (`separate-pull-requests: false`, the default) release-please titles the release PR from the **group** pattern, not the per-package one. If only `pull-request-title-pattern` is set, the group pattern defaults to a version-less `chore: release main`; a release PR whose title lacks `${version}` can't be parsed on merge, so the release strands ([googleapis/release-please#2712](https://github.com/googleapis/release-please/issues/2712)). Set both to the same value. `${component}` renders empty for a single root package, so titles read `chore: release 0.1.2` and tags read `v0.1.2`.

`release-type` options (the per-package `release-type` above):
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

> **Unverified — likely needs the same fix as the single-package block.** Only the single-package config above was verified end-to-end. This monorepo block still carries `package-name` and has no `group-pull-request-title-pattern`, so it probably strands the first release the same way the single-package block did (see #2214 / #2712 above). It almost certainly needs `bump-minor-pre-major` / `bump-patch-for-minor-pre-major` per package, a `group-pull-request-title-pattern` with `${version}`, and the `package-name` lines reconsidered — but the exact shape for the per-component-tag case hasn't been tested, so it's left as-is here rather than changed blind. Fix and verify before relying on it.

## Manifest — match current version

`.github/.release-please-manifest.json`:

```json
{
  ".": "0.1.0"
}
```

The version here **must match** the project's current version in `package.json` / `pyproject.toml`. If they diverge, release-please's first PR generates a confusing changelog.

For brand-new projects (`project-scaffold` flow): start at `0.1.0` — **not `0.0.0`**. When the manifest reads exactly `0.0.0` and no git tag exists yet, release-please hardcodes the first release to `1.0.0` regardless of commit type, ignoring the `bump-minor-pre-major` / `bump-patch-for-minor-pre-major` options ([googleapis/release-please#2087](https://github.com/googleapis/release-please/issues/2087); hit live on `hellatan/getoffthecouch`, where one `fix:` commit produced a release PR proposing `1.0.0`). Seeding the manifest + `package.json` / `pyproject.toml` at a normal pre-1.0 version like `0.1.0` sidesteps the bootstrap entirely; release-please then computes the first release as a normal bump from that baseline — a `feat:` → `0.2.0`, a `fix:` → `0.1.1`. The `0.1.0` seed paired with the corrected single-package config above is the exact combination verified end-to-end on a throwaway repo.

For retrofitting an existing project: read the current version from the project file and use it. Don't reset it — that would lie about the project's history.

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
