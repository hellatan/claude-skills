---
name: release-workflow-init
description: Bring the standard git + release workflow to a bare or framework-less repo in one step — git init + initial commit + private GitHub repo if needed, then gitflow branches + protection (via gitflow-init) and release-please + trimmed CI (via gh-actions-init). Use when the user wants to "set up the release workflow", "add gitflow + release-please", "bootstrap the git/release workflow on this repo", or set up branches + CI + releases on a repo that has no app framework. For framework apps (Next.js/FastAPI) use project-scaffold instead.
---

# release-workflow-init

Thin orchestrator that brings this project's git + release workflow to a **bare or
framework-less repo** (a skill repo, a docs repo, a tiny utility with one helper
script) in a single invocation. It fills the bootstrap gap that `gitflow-init`
assumes already exists, then delegates the real work to `gitflow-init` and
`gh-actions-init`. It writes no workflow YAML itself.

## When to trigger

User says any of:
- "set up the release workflow on this repo"
- "add gitflow + release-please"
- "bootstrap the git/release workflow"
- "set up branches + CI + releases" on a repo with no app framework

## When NOT to use

- **Framework app** (Next.js / FastAPI / similar) — use `project-scaffold`, which
  already wires git + release as part of bootstrapping the app.
- Repo already has `main` + `develop` + release-please working — extend manually.
- User only wants one piece — call `gitflow-init` or `gh-actions-init` directly.

## What this skill does NOT touch

- Tests (`testing-init`), pre-commit hooks (`precommit-init`), CLAUDE.md
  (`claude-md-init`).
- App or framework scaffolding of any kind.
- Branch-protection or release-please logic itself — it **delegates** to the two
  existing skills rather than re-implementing them.

---

## Flow

### 1. Detect repo state (read-only, no prompts)

```bash
is_repo=$(git rev-parse --is-inside-work-tree 2>/dev/null || echo false)
has_commits=$(git rev-parse HEAD >/dev/null 2>&1 && echo true || echo false)
has_remote=$(git remote get-url origin >/dev/null 2>&1 && echo true || echo false)
has_pkg_json=$([ -f package.json ] && echo true || echo false)
has_pyproject=$([ -f pyproject.toml ] && echo true || echo false)
# Does pyproject declare a real package version? (decides release-type below)
pyproj_has_version=$(grep -qE '^[[:space:]]*version[[:space:]]*=' pyproject.toml 2>/dev/null && echo true || echo false)
```

Surface one line, e.g.: *"Detected: not a git repo, no remote, ruff-only pyproject
(no `[project].version`) → release-type `simple`."*

### 2. Bootstrap gap (only what's missing)

This is the orchestrator's core value-add — the steps `gitflow-init` assumes are
already done (it explicitly does **not** run `git init` and requires commits on a
default branch plus an `origin` remote).

**2a. Not a git repo → init + first commit on `main`:**

```bash
git init -b main
# Baseline .gitignore; add language lines as relevant (.venv/, __pycache__/, node_modules/)
printf '%s\n' '.DS_Store' '.venv/' '__pycache__/' '*.pyc' 'node_modules/' '.claude/settings.local.json' > .gitignore
git add -A
git commit -m "chore: initial commit"
```

Respect the repo's git identity — never pass `--author` or override the committer.

**2b. No GitHub remote → create one (HALT first):**

⚠️ **GitHub-mutating. Confirm with the user before running** — repo name (default =
current directory name) and visibility (default = **private**):

> *"Create GitHub repo `<owner>/<name>` (private) and push `main`? (yes / change name / public)"*

After an explicit affirmative:

```bash
gh repo create <name> --private --source=. --remote=origin --push
```

Never run `gh auth refresh/login` or change token scopes. If `gh` reports a missing
scope, print the exact command and let the user run it.

### 3. Delegate branches + protection → `gitflow-init`

Invoke the `gitflow-init` skill. It creates `develop`, applies branch protection, and
sets `develop` as the GitHub default branch. Keep its own HALT-for-confirmation gate.
The prerequisite it assumes — commits on `main` + an `origin` remote — is now
satisfied by Step 2.

### 4. Delegate CI + release-please → `gh-actions-init`

Invoke the `gh-actions-init` skill. For a Python or no-language repo it already emits
**no build job** (CI stays trimmed) and already mandates `target-branch: main` in
`release-please.yml`. Tell it which **release-type** to use at its release-please step:

| Repo has | release-type | manifest seed |
| --- | --- | --- |
| `package.json` | `node` | match `package.json` version |
| `pyproject.toml` with `[project].version` | `python` | match that version |
| neither, OR a ruff-only `pyproject.toml` (no `[project].version`) | `simple` | `.github/.release-please-manifest.json` = `{".": "0.1.0"}` |

For `simple`, `release-please-config.json` uses `"release-type": "simple"`, omits
`package-name`, and sets **both** `pull-request-title-pattern` and
`group-pull-request-title-pattern` to the same value (see
`gh-actions-init/references/release-please.md` — the verified single-package shape).
Seed `0.1.0`, never `0.0.0`.

### 5. Report back

Print a consolidated summary:
- ✅ git: initialized / already a repo (initial commit SHA)
- ✅ remote: created `<owner>/<name>` (private) / already present
- ✅ branches + protection (from `gitflow-init`)
- ✅ CI + release-please: release-type `<node|python|simple>`, `target-branch: main`
- 📋 Next steps: make a first conventional commit; (optional) add a fine-grained PAT so
  CI runs on release PRs; run `/testing-init` or `/precommit-init` if wanted.

---

## Why these defaults

- **Orchestrate, don't re-implement.** `gitflow-init` and `gh-actions-init` are
  verified end-to-end; this skill only adds the bootstrap they assume and a
  release-type decision, so it inherits their fixes instead of duplicating them.
- **`release-type: simple` for framework-less repos.** There's no language version
  file to bump; release-please tracks the manifest + `CHANGELOG.md` from conventional
  commits.
- **`target-branch: main` always.** `gitflow-init` makes `develop` the default branch;
  an unset `target-branch` silently manages `develop` and never tags `main`.
- **Private by default.** Matches `project-scaffold`; the user can opt into public.
- **Idempotent.** Every bootstrap step is guarded by Step 1 detection, and the
  delegated skills skip/extend what already exists — safe to re-run.
