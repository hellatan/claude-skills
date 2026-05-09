---
name: gh-actions-init
description: Add GitHub Actions to an existing repo — scaffolds the CI structure (lint + typecheck + format check + build), wires release-please for automated versioning and changelogs from conventional commits, and drops a platform-agnostic deploy stub. Use when the user wants to "add CI", "set up GitHub Actions", "wire up release-please", "scaffold deploy workflow", or otherwise bring `.github/workflows/` to a project that doesn't have it yet. Detects existing workflows and extends them rather than replacing. Composes with `testing-init` (which owns the test jobs) and `project-scaffold` (which calls this internally for new projects).
---

# gh-actions-init

Adds the GitHub Actions umbrella to an existing project: CI structure, release-please, and a deploy stub. Extends existing workflows instead of replacing them. Composes with `testing-init` (test jobs) and `project-scaffold` (new-project orchestrator).

## When to trigger

User says any of:
- "add CI" / "set up CI" / "scaffold CI"
- "set up GitHub Actions / workflows"
- "add release-please" / "set up automated releases"
- "scaffold the deploy workflow"
- "wire up the CI/CD pipeline"

## When NOT to use

- Project already has working CI + release-please + deploy — extend manually.
- Bootstrapping a brand-new repo from scratch — use `project-scaffold` (which calls this internally).
- User only wants test runners — use `testing-init`.

## What this skill does NOT touch

- **Test jobs** in CI (unit / integration / e2e) — `testing-init`'s job. This skill scaffolds the *structural* CI jobs (lint, typecheck, format:check, build); test jobs are added separately by `testing-init`.
- **Pre-commit hooks** — separate concern.
- **Branch protection rules** — `gh api` work, not workflows. Future skill (`gitflow-init`).
- **CLAUDE.md** — separate skill.
- **Local test setup** — `testing-init`'s job.

---

## Flow

### 1. Detect stack and existing state

Read these without asking:

- `package.json` — Node project; inspect `dependencies` for framework, `engines.node`, existing `scripts` (look for `lint`, `format:check`, `typecheck`, `build`).
- `pyproject.toml` / `setup.py` — Python project; check for `[project].version`, dev dep groups.
- `.github/workflows/` — list existing workflows. For each:
  - Note the file name and the `jobs:` keys (so we don't duplicate).
- `package.json` `version` and any `pyproject.toml` `version` — the **starting manifest version** (release-please needs this to match).
- Default branch — `git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@'` (handles `master`, `trunk`, etc.).
- Branches — does `develop` exist on origin? If not, the project is `main`-only and CI triggers should reflect that.

Surface findings in one line: *"Detected: Next.js 16 + TS, default branch `develop`, package.json version 0.3.1, no existing workflows."*

See `references/detection.md` for the detection cheat-sheet.

### 2. Pick what to add

Three independent decisions:

**a. CI structure** — lint + typecheck + format:check + build jobs.

If `.github/workflows/ci.yml` exists (e.g., `testing-init` already created one with test jobs): extend by adding only missing structural jobs.

If it doesn't exist: create a fresh `ci.yml` with just the structural jobs. Test jobs are added separately by `testing-init`.

**b. release-please** — `release-please.yml` + `release-please-config.json` + `.release-please-manifest.json`.

If any of these already exist: skip the whole release-please piece (don't risk breaking a working release flow). Surface the skip in the report.

If they don't exist: scaffold all three. Manifest version must match `package.json` / `pyproject.toml` version exactly — read the current version, don't hardcode `0.0.0` (that's only for fresh `project-scaffold` runs).

**c. Deploy stub** — `deploy.yml`.

If it exists: skip with a "you already have a deploy workflow" note.

If it doesn't: scaffold the stub. Default-highlight Render.com (no vendor lock, fair pricing). Other platforms are commented out as alternatives. User fills in the actual deploy step.

### 3. Show summary, halt for confirmation

Render the plan as a fenced code block with emoji headers (same convention as `project-scaffold` Step 7):

```
🔍 Detected:        <stack + branch model + existing workflows>
🤖 CI structure:    <create new ci.yml | extend existing ci.yml: adding [jobs]>
🚀 release-please:  <scaffolding | skipped (already present)>
🚀 Deploy stub:     <scaffolding | skipped (already present)>
📝 Files to write:  <list>
📝 Files to extend: <list>
🌿 Branch triggers: <main only | main + develop | main + develop + stage>
```

End with: *"Reply 'yes' / 'go' / 'looks good' to proceed, or tell me what to change."*

### 4. **HALT for confirmation**

Same gate as `project-scaffold` and `testing-init`. Wait for explicit affirmative reply.

---

## Execution

### Step A: CI structure

See `references/ci-structure.md` for the per-stack job templates and the extend-vs-create logic.

Per-stack job set:
- **Node/TS**: `lint + typecheck` job, optional `format:check` (if `prettier` is in dev deps), `build` job.
- **Python**: `lint` job (ruff check + ruff format --check), `typecheck` job (mypy if it's installed), no build job (Python apps usually deploy source).
- **Fullstack**: matrix of both, gated by changed-paths if needed.

**Extend-mode rules** (when `ci.yml` exists):
- Add only jobs whose `name:` doesn't already appear.
- Don't change `on:` triggers if they exist — log a warning if they look stale (e.g., only `main` when `develop` exists).
- Match the existing file's indentation (default 2 spaces).
- Preserve any existing `concurrency:` or `permissions:` blocks.

### Step B: release-please

See `references/release-please.md`.

Three files:
1. `.github/workflows/release-please.yml` — the workflow.
2. `.github/release-please-config.json` — release type, package name, changelog path.
3. `.github/.release-please-manifest.json` — current version, **must match** `package.json` / `pyproject.toml`.

Skill behavior:
- If `package.json` has `"version": "0.3.1"`, manifest should be `{".": "0.3.1"}` so release-please's first PR generates a clean changelog from the most recent tag.
- For monorepos with separate frontend/backend versions: see `references/release-please.md` monorepo section.

### Step C: Deploy stub

See `references/deploy-stub.md`.

One file: `.github/workflows/deploy.yml`. Triggers on `v*.*.*` tag pushes (release-please creates these on release-PR merge). Render is highlighted as the default; other options (Fly.io, Railway, GHCR Docker push) are commented out.

### Step D: Smoke-validate

Don't run actual workflows from the skill (would require pushing). Instead:

- `actionlint .github/workflows/*.yml` if `actionlint` is installed (`brew install actionlint`); otherwise skip with a note.
- `gh workflow list` to confirm GitHub picks up the new workflows after first push.

Don't fail the skill if these tools aren't available — they're nice-to-haves.

### Step E: Report back

Print:
- ✅ What was added (file paths)
- ✅ What was extended (job names added to existing files)
- ✅ What was skipped and why (existing release-please, etc.)
- ⚠️ Anything that needs user attention (e.g., stale `on:` triggers in existing CI; missing `engines.node`)
- 📋 Next steps:

```
Next steps:
1. Push a feature branch and open a PR — confirm CI runs green
2. Fill in the deploy step in `.github/workflows/deploy.yml` (Render is highlighted as the default)
3. (If you don't have tests yet) Run `/testing-init` to add the test jobs that round out the 5-check pipeline
4. (If you want branch protection on main/develop) Set it up via GitHub UI or `gh api repos/{owner}/{repo}/branches/{branch}/protection`
5. Make your first conventional commit (`feat:`, `fix:`, etc.) — release-please tracks these for the next release PR
```

---

## Reference files

- `references/detection.md` — how to read stack + existing workflows + version state + branch model
- `references/ci-structure.md` — per-stack lint + typecheck + format:check + build jobs; extend-vs-create logic
- `references/release-please.md` — workflow, config, manifest; monorepo variant; tag-pattern gotchas
- `references/deploy-stub.md` — `deploy.yml` with Render highlighted; other platforms commented

## Why these defaults

- **Render.com over Vercel as the deploy default** — no vendor lock, fair pricing, runs on Docker/native, doesn't push the Next.js team's hosting agenda. Vercel is still listed (commented) for users who want it.
- **release-please over manual versioning** — drives off conventional commits, opens PRs you review, no manual tag/changelog work.
- **No build job for Python** — Python apps generally deploy source via container or buildpack; a separate `build` step adds CI time without value. Library projects can opt in by extending the workflow.
- **Idempotent on re-run** — skips files that exist, extends `ci.yml` jobs without duplicating, surfaces what was skipped.
- **Composes cleanly with `testing-init`** — neither skill stomps on the other's CI jobs. Run order doesn't matter.
