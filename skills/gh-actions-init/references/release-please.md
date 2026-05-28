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

A monorepo tracks each package's version independently, so its tags must be **per-component** (`backend-v1.2.0`, `frontend-v1.2.0`) and each package needs its **own** release PR. This exact shape was verified end-to-end (see the note at the end of this section):

```json
{
  "$schema": "https://raw.githubusercontent.com/googleapis/release-please/main/schemas/config.json",
  "separate-pull-requests": true,
  "packages": {
    "backend": {
      "release-type": "python",
      "package-name": "<project>-backend",
      "component": "backend"
    },
    "frontend": {
      "release-type": "node",
      "component": "frontend"
    }
  },
  "include-v-in-tag": true,
  "pull-request-title-pattern": "chore: release ${component} ${version}"
}
```

The single-package fixes above do **not** transfer verbatim — the per-component-tag case behaves differently in three ways, each confirmed live:

- **Per-component tags are mandatory; you cannot collapse the monorepo into one `v1.2.0` tag.** `include-component-in-tag` is left at its default (`true`), so each package tags as `backend-v…` / `frontend-v…`. The tempting "release everything under one `v1.2.0` tag" via `include-component-in-tag: false` only survives while *every* release bumps *all* packages in lockstep. The first commit that touches a single package diverges their versions, and release-please then can't map the component-less tag back to the one package that bumped — it logs `There are untagged, merged release PRs outstanding - aborting` and **silently creates no tag or release**. (Verified: a symmetric first release tagged a single `v0.2.0` cleanly, but a later backend-only `fix:` merged with **no** `v0.2.1` produced — the release stranded.)
- **Keep `package-name` on the Python package.** Unlike the node single-package block (which *removes* it), `package-name` is **required** for non-node release types, so `backend` keeps it; `frontend` (node) doesn't need it. `component` is set on both so the tags read `backend-v…` / `frontend-v…` rather than the full package name.
- **`separate-pull-requests: true`, not grouped.** Grouped mode (the default) puts both packages in one release PR, but a single title can't carry two different per-component versions, so it renders version-less (`chore: release`) and can't be associated on merge — the release strands with the same `untagged … aborting` error (verified). Separate PRs each carry their own `${component} ${version}`, parse on merge, and tag independently. No `group-pull-request-title-pattern` is needed because there is no grouped PR.

**Tags are `backend-v1.2.0` / `frontend-v1.2.0`, so `deploy.yml` must trigger on the per-component pattern (`*-v*.*.*`), not `v*.*.*`** — see `references/deploy-stub.md`.

**Caveat — merge sibling release PRs one at a time.** When more than one package has a pending release (notably the very first release, where everything bumps at once), each is its own PR editing the shared `.release-please-manifest.json`. Merging one makes the others conflict, and release-please leaves an already-open PR's branch as-is (`PR … remained the same`) rather than rebasing it onto the moved `main`. Recovery is clean and confirmed: **close** the conflicted sibling PR and let release-please **recreate** it against the new `main` on its next run — the recreated PR merges without conflict and tags correctly.

> **Want one `v1.2.0` tag instead (app shipped as a single unit)?** If frontend and backend always deploy together, skip the per-component setup entirely and use the **single-package config above** with the repo root as the one package (`"."`). release-please then bumps the root version file and cuts a single `v1.2.0` tag for the whole repo, keeping the default `v*.*.*` deploy trigger; the per-package version files just aren't tracked individually, which is fine when you never ship them apart. This sidesteps every per-component footgun listed above.

**Verified end-to-end.** On a throwaway frontend(node)+backend(python) repo seeded at `0.1.0`/`0.1.0`, a `feat` touching both packages opened two release PRs (`chore: release backend 0.2.0`, `chore: release frontend 0.2.0`); merging them — closing and letting release-please recreate the second to clear the manifest conflict — produced clean `backend-v0.2.0` and `frontend-v0.2.0` tags + GitHub releases with no manual version edits. The two strand modes called out above (`include-component-in-tag: false` divergence; grouped version-less title) were each reproduced live on parallel throwaway repos to confirm they are real, not theoretical.

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

Monorepo manifest — one entry per package, keyed by the package's path (matching the `packages` keys in the config):

```json
{
  "backend": "0.3.1",
  "frontend": "0.3.1"
}
```

The same `0.0.0` → `1.0.0` bootstrap trap applies per package, so brand-new monorepos seed each entry at `0.1.0` (not `0.0.0`), matching each package's `pyproject.toml` / `package.json`. Retrofits use each package's current version.

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
