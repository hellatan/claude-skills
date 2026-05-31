# Detection cheat-sheet

How to read project state without asking the user. All these are read-only operations.

## Stack

```bash
# Node / TS / JS
[[ -f package.json ]] && stack_node=true

# Python
[[ -f pyproject.toml || -f setup.py || -f setup.cfg ]] && stack_python=true

# Combined: fullstack
$stack_node && $stack_python && stack=fullstack
```

For Node, inspect `package.json`:

```bash
jq -r '.dependencies | keys[]' package.json   # framework: next, react, fastify, express, vue, ...
jq -r '.engines.node // "unset"' package.json  # node version pin
jq -r '.scripts | keys[]' package.json         # existing scripts: lint, format:check, typecheck, build
jq -r '.version' package.json                  # current version (for release-please manifest)
```

Useful framework signals:
- `next` in deps → Next.js (single-app fullstack-collapsed)
- `react` in deps without `next` → Vite + React or similar
- `fastify` / `express` / `koa` / `hono` → backend service, no UI
- `vue` / `svelte` → other frontend frameworks (skill still works, just needs different lint config — surface this)

For Python, inspect `pyproject.toml`:

```bash
# Read with python (always available) since yq/tomlq aren't standard:
python3 -c "import tomllib, sys; d=tomllib.load(open('pyproject.toml','rb')); print(d.get('project',{}).get('version','unset'))"
python3 -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); print(' '.join(d.get('project',{}).get('dependencies',[])))"
```

Useful Python framework signals:
- `fastapi` → FastAPI app
- `django` → Django app (skill should warn — Django has its own opinions about CI)
- `flask` → Flask app
- (no framework) → library or script

## Existing workflows

```bash
ls -1 .github/workflows/*.yml 2>/dev/null
```

For each existing workflow, identify the jobs:

```bash
for wf in .github/workflows/*.yml; do
  echo "=== $wf ==="
  # yq is the cleanest if installed:
  yq '.jobs | keys' "$wf" 2>/dev/null \
    || grep -E '^  [a-z][a-z0-9-]*:$' "$wf"   # fallback: top-level job names
done
```

Workflows to detect:
- `ci.yml` — main CI. May already have test jobs from `testing-init`. Add only structural jobs (lint+typecheck+build); skip if same-named job exists.
- `release-please.yml` — if present, **skip the entire release-please piece**. Don't risk breaking a working release flow.
- `deploy.yml` — if present, skip with a note.
- Other workflows (e.g. `validate.yml`, `link-check.yml`, hand-written CI) — leave them alone.

## release-please state

Three files form release-please's state:

1. `.github/workflows/release-please.yml` — the action invocation
2. `.github/release-please-config.json` — release type, packages, changelog path
3. `.github/.release-please-manifest.json` — current versions per package

If **any** of these exist, treat release-please as already configured and skip. Don't try to merge configs — too many ways to break the user's release history.

If none exist, scaffold all three. The manifest version must match the project's current `version`:

```bash
# Node:
node_version=$(jq -r '.version' package.json)

# Python:
python_version=$(python3 -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")
```

If neither has a version (older Python projects sometimes don't), default to `0.1.0` — *not* `0.0.0`. An exact-`0.0.0` manifest with no tag makes release-please bootstrap the first release to `1.0.0` regardless of commit type ([googleapis/release-please#2087](https://github.com/googleapis/release-please/issues/2087); see `references/release-please.md`). Also surface a warning that the user should set `version` in their project file.

## Default branch + branch model

```bash
default_branch=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
# Common values: main, master, develop, trunk

has_develop=$(git ls-remote --heads origin develop | grep -q . && echo true || echo false)
has_stage=$(git ls-remote --heads origin stage | grep -q . && echo true || echo false)
```

CI trigger logic:

| Default branch | `develop` exists? | `on.push.branches` |
|---|---|---|
| `main` or `master` | no | `[main]` (or `[master]`) |
| `main` | yes | `[main, develop]` |
| `main` | yes + `stage` exists | `[main, develop, stage]` |
| `develop` | yes (own default) | `[develop, main]` |

Same array for `on.pull_request.branches`.

## Existing scripts (Node)

These determine which CI jobs are wirable. If `npm run lint` doesn't exist, the lint job will fail — surface this and offer to skip the lint job *or* add the script first (see `references/ci-structure.md`).

```bash
has_lint=$(jq -e '.scripts.lint' package.json >/dev/null && echo true || echo false)
has_typecheck=$(jq -e '.scripts.typecheck' package.json >/dev/null && echo true || echo false)
has_format_check=$(jq -e '.scripts["format:check"]' package.json >/dev/null && echo true || echo false)
has_build=$(jq -e '.scripts.build' package.json >/dev/null && echo true || echo false)
```

## Python equivalents

For Python, the corresponding tools matter:
- `ruff` in dev deps → ruff check + ruff format --check available
- `mypy` in dev deps → typecheck job wirable
- (No specific build tool for app projects — skip build job.)
