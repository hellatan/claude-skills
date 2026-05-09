---
name: project-scaffold
description: Bootstrap a new project repo with prescriptive defaults — opinionated framework picks (Next.js, FastAPI), lean CLAUDE.md, sensible git workflow (main + develop, optional stage), unified pre-commit hooks at root, GitHub Actions CI (5-check pipeline), release-please for automated releases, deploy workflow stub, and a private GitHub repo under the user's authenticated gh account. Use this skill whenever the user wants to scaffold, bootstrap, initialize, or set up a new project, repo, or codebase — even if they don't explicitly say "scaffold." Triggers on phrases like "new repo," "start a new project," "bootstrap [name]," "set up a project," or "init a repo with claude config."
---

# project-scaffold

Bootstraps a new project repo with prescriptive, opinionated defaults. The goal is a project that's wired correctly end-to-end on day one — feature → develop → main → tag → deploy works out of the box, with sensible framework picks already made for users who don't have strong opinions.

## Core philosophy: prescriptive defaults, named overrides

For every decision the skill makes:

1. **Pick the best default** based on the user's stated project type.
2. **State it as a fact**, not a question: "Going with X for Y — [one-line outcome explanation]."
3. **Offer a named override**: "If you specifically need [alternative], say so now."
4. **Allow trivial confirmation**: "Otherwise reply 'ok' or hit enter."

Most users don't have strong opinions on most decisions. Even users who could answer often don't want to — decision fatigue is real. Naming alternatives gives experienced users a clean exit without forcing newbies to learn what they don't know yet. Outcome-based explanations beat jargon-based labels every time.

**Avoid jargon when explaining defaults.** Describe what the user gets, not the architectural buzzword. "Free interactive API docs" beats "automatic OpenAPI generation." "Handles your whole web app in one framework" beats "covers SSR and API routes."

## When to trigger

User says any of:
- "scaffold a new repo / project"
- "bootstrap [project-name]"
- "set up a new [stack] project"
- "init a new repo"
- "new project with claude config"

---

## Flow

Run these steps in order. **Ask questions one at a time.** For decision points where the skill has a strong default, state the default and only wait for an override.

### 1. Project name + location

Ask:
- Project name (becomes repo name and directory name)
- Parent directory (default: current working directory)

Verify the target directory doesn't already exist before proceeding.

Compute the **package name** here too: convert the project name to snake_case for Python (e.g. `my-project` → `my_project`). This name will be propagated consistently to:
- `pyproject.toml` `name` field
- The actual package directory + `__init__.py`
- `uvicorn <package>.main:app` references in CLAUDE.md
- Test discovery paths

### 2. Project type

Ask:

> What is this project?
> - **frontend** — a website or web app that users interact with in their browser
> - **backend** — a server that handles data, APIs, or background work (no visible UI)
> - **fullstack** — both: a website *plus* a server it talks to
> - **library** — code meant to be reused by other projects (published as a package)
> - **research** — exploratory work, notebooks, scripts — no app or website to deploy

### 3. Framework selection (prescriptive)

Apply the prescriptive-defaults pattern. Don't ask what they want — tell them what you're using.

**For frontend or fullstack with a frontend:**

> Going with **Next.js** for the frontend — it's the most flexible choice and handles your whole web app in one framework (pages, APIs, the works). If you specifically need something else (Vite + React, SvelteKit, Vue, etc.), say so now. Otherwise reply "next is fine" or just hit enter.

**For backend or fullstack with a backend, ask the language first IF context is unclear:**

For the backend language question, **don't be prescriptive about Python vs Node** — instead, prompt the user to describe the project's purpose, then diagnose:

> What does the backend mainly do? (e.g. "serves an API for the frontend", "runs charting calculations", "processes uploaded data", "does ML inference"). I'll pick the right language based on use case.

Use the description to recommend:
- **Charting, data analysis, ML, scientific computing, quant work, anything numerical-heavy** → recommend Python with reasoning ("Python's ecosystem for numerical work is unmatched — pandas, numpy, scipy, matplotlib all live here. You'd fight Node.js the whole way.")
- **APIs, web services, real-time, general business logic** → recommend Node with reasoning ("Node is great for HTTP APIs and shares the language with your TypeScript frontend, which means easier type sharing.")
- **If they explicitly state a language preference** → respect it but flag if it seems mismatched ("You said Node, but you mentioned charting — are you sure? Python would be much easier here.")

**Then commit to the framework:**

For Python backend:
> Going with **FastAPI** — modern, fast, and gives you free interactive API docs. If you specifically need Django (heavier, comes with admin UI and built-in user accounts) or Flask (tiny and barebones — you build everything yourself), say so now. Otherwise reply "fastapi is fine" or just hit enter.

For Node backend (when not collapsed into Next.js):
> Going with **Fastify** — modern, fast, type-friendly. If you specifically need Express (the classic, more middleware available) or Hono (works on edge runtimes), say so now. Otherwise reply "fastify is fine" or just hit enter.

**Important: for Node + Node fullstack, default to collapsing into Next.js alone.**

> For a fullstack JS/TS project, going with **just Next.js** — its built-in API routes handle the backend, so you don't need a separate Node service. Simpler to deploy, easier to share types between frontend and backend.
>
> If you specifically need a separate backend (e.g. you'll have multiple frontends, heavy background jobs, or websockets), say so now. Otherwise reply "ok" or hit enter.

### 4. Layout decision (fullstack only)

This decision depends on the backend language.

**Node + Node fullstack (when user opts for separate backend, not Next.js-only):**

> Going with **npm workspaces** for the layout — `frontend/` and `backend/` share dependencies and let you import types between them, with one `npm install` at the root. This is what npm workspaces was built for.
>
> The repo root also holds the shared coordination layer: pre-commit hooks, CI workflow, gitignore, and project docs.
>
> If you specifically want them as **two completely independent projects** (separate installs, no shared imports — easier to split into separate repos later), say so now. Otherwise reply "ok" or hit enter.

**Node + Python fullstack:**

> Going with **two independent projects under one repo** — `frontend/` (Node) and `backend/` (Python) keep their own dependencies, install commands, and configs. The repo root holds the shared stuff: pre-commit hooks (catches lint + format errors on both sides before commit), CI workflow, gitignore, and project docs.
>
> Reply "ok" or hit enter to proceed.

(No alternative offered — workspaces literally can't help when one side is Python.)

### 5. Staging branch

Ask:

> Want a "staging" branch before production?
>
> A staging branch is like a dress rehearsal — code goes there first, deploys to a separate copy of your site only you can see, and you click around to make sure nothing's broken before it goes live to real users. If you're solo or just starting out, you can skip this and add it later.
>
> - `yes` — set up a `stage` branch with its own protected workflow (lifecycle becomes feature → develop → stage → main)
> - `no` — go straight from develop → production (default)

### 6. GitHub repo

Ask:

> Public or private repo?
>
> - **Public** — anyone on the internet can see the code (still need permission to *change* it). Free GitHub plan includes branch protection.
> - **Private** — only people you invite can see it. Branch protection requires GitHub Pro (~$4/mo) or making the repo public.

Then verify gh auth and account plan **up front**:

```bash
gh auth status
gh api user --jq .plan.name 2>/dev/null
```

If the user picked private and is on free tier, **warn now, not later**:

> Heads up — your account is on the free tier, so branch protection won't apply to a private repo. The local pre-commit hooks and CLAUDE.md git rules still protect you, and CI still runs on PRs (you'll just *be able* to merge a failing PR if you ignore the red X). Want to make it public instead, or proceed?

### 7. Show summary, halt for confirmation

Print a plain-English summary of everything about to happen. Group by category (project, stack, branches, code quality, CI, deploy, GitHub) and use plain language — no jargon. Show only the choices made for *this* user's project (don't list options they didn't pick). End with: *"Reply 'yes' / 'go' / 'looks good' to proceed, or tell me what to change."*

### 8. **HALT — REAL CONFIRMATION GATE**

This is its own dedicated step. **Do not proceed under any circumstances** until the user replies with explicit affirmative confirmation (e.g. "yes", "go", "proceed", "looks good", "ok").

If running in Claude Code with auto-mode enabled, **still halt here** by using a real pausing primitive — ask the user with a question that requires a response, not just instruction text. The user must consciously approve the destructive steps that follow (creating a GitHub repo, applying branch protection, running git commands).

If the user says anything other than affirmative confirmation, ask what they'd like to change and loop back to the relevant step.

---

## Execution

Once confirmed, proceed through these steps without further halts (unless something fails).

### Step A: Create directory + base files

```bash
mkdir -p <parent>/<name>
cd <parent>/<name>
```

**For projects using Next.js, run `create-next-app` FIRST** (before writing root files), since it creates the project layout. Use the `--skip-git` flag so the skill controls git init in Step F. After `create-next-app`:

- For frontend-only at repo root: clean up `create-next-app`'s leftovers — delete the stub `CLAUDE.md` (skill writes its own), keep `AGENTS.md` (useful Next-specific context).
- For fullstack with frontend in subdir: same cleanup but in `frontend/` (delete `frontend/CLAUDE.md`, keep `frontend/AGENTS.md`).

See `references/configs/nextjs.md` for the full create-next-app command and post-scaffold steps.

**Then** write these to repo root:
- `CLAUDE.md` — see `references/claude-md-templates.md`
- `.gitignore` — see `references/gitignores.md`
- `README.md` — minimal, just `# <project-name>` and a one-line description placeholder
- `.editorconfig` — see `references/configs/editorconfig.md`
- `.pre-commit-config.yaml` — see `references/configs/precommit-unified.md`

For fullstack: also create `frontend/` and `backend/` subdirs (frontend already exists if Next.js was used).

For Python projects: create the actual package directory based on the snake_case name from Step 1:
```bash
mkdir -p <package_name>
touch <package_name>/__init__.py
```

If FastAPI: also write `<package_name>/main.py` with a stub:
```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "ok"}
```

For TypeScript projects without Next.js: write a stub `src/index.ts` (Node) or `src/main.tsx` (Vite/React) so `tsc --noEmit` doesn't fail on empty input. Next.js's own scaffold creates the entry points (`app/page.tsx` etc.).

After writing all the configs, run `npx prettier --write .` once to format any files (including `eslint.config.mjs` from create-next-app) that aren't yet prettier-formatted. Otherwise CI's `format:check` fails on first push.

### Step B: Stack-specific config files

Based on the stack chosen, write the appropriate config files. **All templates are in `references/configs/`** — read the relevant ones and write them into the project.

| Stack | Config files to write |
|---|---|
| Next.js (frontend or fullstack-collapsed) | `package.json` (with Next.js + React deps installed), `tsconfig.json` (Next.js preset), `eslint.config.js`, `.prettierrc`, `.prettierignore`, `next.config.js` |
| Node backend (Fastify) | `package.json`, `tsconfig.json`, `eslint.config.js`, `.prettierrc` |
| Python backend (FastAPI) | `pyproject.toml` (with FastAPI + uvicorn + dev deps), `.python-version` |
| Fullstack (any combo) | Both sets in `frontend/` and `backend/` subdirs PLUS root coordination layer (root `package.json` with cross-stack scripts, root pre-commit config, root `.gitignore` covering both) |
| Library | Stack-appropriate config + publishing setup |
| Research | `pyproject.toml` (lighter — just ruff + jupyter), `.python-version` |

**Critical for monorepo/fullstack:** ensure ESLint flat config (`eslint.config.js`) is generated **at the location where lint-staged will invoke it** — for fullstack with frontend in subdir, the workspace config is in `frontend/`, but for ESLint to resolve correctly when called from root, the pre-commit hooks must `cd` into the right directory (handled in `references/configs/precommit-unified.md`).

**Install actual framework dependencies, not just the config that references them.** Don't generate a `package.json` that says `"dev": "vite"` if Vite isn't installed. Run the install commands during scaffold:

For Next.js:
```bash
npx create-next-app@latest <project-or-frontend-dir> --typescript --eslint --app --src-dir --import-alias "@/*" --use-npm --no-tailwind
```

For Fastify:
```bash
npm install fastify
npm install --save-dev typescript tsx @types/node
```

For FastAPI:
```toml
# Add to pyproject.toml dependencies:
dependencies = [
  "fastapi>=0.115",
  "uvicorn[standard]>=0.32",
]
```

### Step C: Root-level command runner

Scaffold root commands so users can run lint/test/build from one place without needing Make (which isn't cross-platform).

**For any project with a Node component (frontend, fullstack, or Node backend):**

Generate a root `package.json` with proxying scripts. See `references/configs/root-package-scripts.md` for the full template per stack. Example for Node+Python fullstack:

```json
{
  "name": "<project-name>-root",
  "private": true,
  "version": "0.0.0",
  "scripts": {
    "lint": "npm run lint:frontend && npm run lint:backend",
    "lint:frontend": "npm --prefix frontend run lint",
    "lint:backend": "cd backend && ruff check . && mypy .",
    "format": "npm run format:frontend && npm run format:backend",
    "format:frontend": "npm --prefix frontend run format",
    "format:backend": "cd backend && ruff format .",
    "typecheck": "npm run typecheck:frontend && npm run typecheck:backend",
    "typecheck:frontend": "npm --prefix frontend run typecheck",
    "typecheck:backend": "cd backend && mypy .",
    "test": "npm run test:frontend && npm run test:backend",
    "test:frontend": "npm --prefix frontend test",
    "test:backend": "cd backend && pytest",
    "build": "npm run build:frontend && npm run build:backend",
    "build:frontend": "npm --prefix frontend run build",
    "build:backend": "cd backend && python -m build",
    "dev": "npm run dev:frontend & npm run dev:backend",
    "dev:frontend": "npm --prefix frontend run dev",
    "dev:backend": "cd backend && uvicorn <package>.main:app --reload",
    "check:all": "npm run lint && npm run typecheck && npm run test"
  }
}
```

**For Python-only projects:** scaffold `scripts/dev.py` instead — npm wouldn't be installed. See `references/configs/python-dev-script.md`.

Either way, the canonical command is `check:all` — runs everything CI would run.

### Step D: Pre-commit hooks (single unified system at root)

**Default to `pre-commit` for everything**, regardless of stack. Drop husky entirely — it's the wrong tool for polyglot repos and doesn't add anything for single-language ones that pre-commit can't do.

Install the package:

```bash
pip install pre-commit  # or: uv add --dev pre-commit
```

Generate `.pre-commit-config.yaml` at repo root based on which stacks are present. See `references/configs/precommit-unified.md` for the full per-stack template.

**Do NOT run `pre-commit install` yet** — it requires `.git/` to exist. The skill calls `pre-commit install` at the end of Step F (after `git init`), then `pre-commit autoupdate` to bump hook revs to current versions.

The config dispatches by file pattern — staging only Python files runs only Python hooks, staging only TS files runs only TS hooks, mixing runs both. All from root.

### Step E: GitHub Actions workflows

Write workflows to `.github/workflows/`:

1. **`ci.yml`** — the 5-check pipeline (lint+typecheck, unit, integration, e2e, build). Pick the right variant from `references/workflows/`:
   - `ci-node.md` — Node/TS only (including Next.js-only and Node-only backend)
   - `ci-python.md` — Python only
   - `ci-fullstack-py-ts.md` — Python BE + TS FE
   - `ci-fullstack-node-ts.md` — Node BE + TS FE (separate from Next.js-only)

2. **`release-please.yml`** — runs on push to `main`, opens/updates a release PR; on merge of release PR, tags + creates GitHub release. See `references/workflows/release-please.md`.

3. **`deploy.yml`** — triggers on tag push (and optionally on push to `develop` for staging if user opted in). Platform-agnostic stub. See `references/workflows/deploy.md`.

Also write `.github/release-please-config.json` and `.github/.release-please-manifest.json`. Manifest starts at `0.0.0` so the first release-please PR cleanly bumps to `0.1.0`. The `pyproject.toml` and `package.json` initial version must match — set both to `0.0.0` at scaffold time.

**Critical: scaffold actually-passing test stubs so CI doesn't fail on first push.**

Without test stubs, the CI pipeline fails on `vitest: command not found` or empty pytest collection. Scaffold:

- **Node/TS unit test stub:** `src/__tests__/smoke.test.ts` with `expect(1).toBe(1)`
- **Node/TS e2e test stub:** Playwright config + `e2e/smoke.spec.ts` that loads a page or does `expect(true).toBeTruthy()`
- **Node/TS integration test stub:** can be skipped with `echo "no integration tests yet" && exit 0` in the workflow until user adds real ones
- **Python unit test stub:** `tests/test_smoke.py` with `def test_smoke(): assert 1 == 1`
- **Python integration/e2e:** marker-based, stubs with the markers so collection succeeds even with no tests

**Install the test runners as dev deps**, not just reference them in scripts:

- Node: `vitest`, `@playwright/test`
- Python: `pytest`, `pytest-cov`

### Step F: Git init with main + develop (+ optional stage)

```bash
git init -b main
git add .
git commit -m "chore: initial scaffold"
git branch develop
```

If staging was opted in:
```bash
git branch stage
```

Switch to `develop`:
```bash
git checkout develop
```

**Now activate pre-commit hooks** (deferred from Step D because `pre-commit install` requires `.git/` to exist):

```bash
pre-commit install
pre-commit autoupdate
```

`autoupdate` bumps hook revisions to current versions so the user doesn't start out on stale ones.

### Step G: Detect global pre-push hooks before pushing

Check if the user has a global pre-push hook that might block bootstrap pushes:

```bash
git config --global core.hooksPath
ls -la $(git config --global core.hooksPath)/pre-push 2>/dev/null
```

If a hook exists, **warn the user explicitly**:

> 👀 Detected a global git hook at `<path>` that may block pushing to `main`/`develop`. The bootstrap push needs to seed those branches once before normal protection rules kick in. After this initial push, all future changes go through the normal Pull Request flow.
>
> If your hook supports an override env var (commonly `ALLOW_PUSH_TO_PROTECTED=1`), I'll use it for the bootstrap push only. Confirm the env var name your hook expects, or let me know if it's something else.

Wait for confirmation before pushing.

### Step H: Create GitHub repo and push

```bash
gh repo create <name> --private --source=. --remote=origin

# Bootstrap push — exception: this is the ONLY time pushing directly to
# protected branches is authorized. After this, all changes go through PRs.
ALLOW_PUSH_TO_PROTECTED=1 git push -u origin main
ALLOW_PUSH_TO_PROTECTED=1 git push -u origin develop

if staging_enabled:
  ALLOW_PUSH_TO_PROTECTED=1 git push -u origin stage
```

**The bootstrap exception is push-only, scoped to seeding the remote.** After this point:
- All changes (including dep installs, fixups, follow-up commits) go through the standard PR → develop flow
- Branch protection bypass is **never** authorized for merging PRs
- The skill must not extend the bootstrap exception to any subsequent operation

### Step I: Branch protection (skip if free-tier private)

Skip this step entirely if Step 6's check showed free-tier + private. Otherwise:

Apply protection to `main`, `develop`, and (if staging enabled) `stage`. Require the CI checks to pass:

```bash
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)

protect_branch() {
  local branch=$1
  gh api -X PUT "repos/$REPO/branches/$branch/protection" --input - <<'EOF'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["lint + typecheck", "unit tests", "integration tests", "e2e tests", "production build"]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "required_approving_review_count": 0,
    "dismiss_stale_reviews": false,
    "require_code_owner_reviews": false
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
EOF
}

protect_branch main
protect_branch develop
if staging_enabled:
  protect_branch stage
```

**If protection fails with 403:**

> ⚠️ Branch protection couldn't be applied — GitHub returned a **403 (forbidden — your account/plan isn't allowed to do this)**. Branch protection requires GitHub Pro for private repos. You have three options:
>
> 1. Make the repo public (everything works, free): `gh repo edit --visibility public`
> 2. Upgrade to GitHub Pro (~$4/mo) — branch protection works on private repos
> 3. Skip it for now (your local pre-commit hooks + global git rules still protect you, and CI still runs on PRs — you just *can* merge a failing PR if you ignore the red X)

### Step J: Set develop as default branch

```bash
gh repo edit --default-branch develop
```

PRs default to merging into `develop`. `main` only gets touched by release-please's release PRs.

### Step K: Smoke test (verify the scaffold actually works)

Before declaring success, run a smoke test from the project root. **Don't use empty commits** — invoke hooks directly so there's no commit cleanup needed.

```bash
# 1. Verify deps install cleanly
if [[ -f package.json ]]; then npm install; fi
if [[ -f pyproject.toml ]]; then pip install -e ".[dev]"; fi

# 2. Verify linter finds its config and runs
npm run lint 2>&1 | tail -20  # if Node
ruff check . 2>&1 | tail -20  # if Python

# 3. Verify typecheck passes
npm run typecheck 2>&1 | tail -20  # if TS
mypy . 2>&1 | tail -20  # if Python

# 4. Verify hooks fire correctly (without making a commit)
pre-commit run --all-files

# 5. Verify test runner finds tests and they pass
npm run test 2>&1 | tail -20  # if Node
pytest 2>&1 | tail -20  # if Python

# 6. Verify production build succeeds
# This catches server-component issues, env-var misses, broken imports,
# and other failures that lint/typecheck/test don't catch.
npm run build 2>&1 | tail -20  # if Node
python -m build 2>&1 | tail -20  # if Python

# 7. Verify check:all (the canonical "run everything CI would run") passes
npm run check:all 2>&1 | tail -20  # if Node
python scripts/dev.py check:all 2>&1 | tail -20  # if Python-only
```

If any step fails, report the specific failure and offer to fix. Common failure modes:

- ESLint can't find config → may need root-level config for monorepo layouts
- `tsc --noEmit` fails on empty `src/` → may need stub source files
- Test runner not installed → may need to install vitest/pytest as dev deps
- `format:check` fails on `eslint.config.mjs` → run `npx prettier --write .` after writing `.prettierrc`
- mypy fails on imports → check `additional_dependencies` in `.pre-commit-config.yaml`
- `npm run build` fails on Next.js scaffold → check for missing env vars or bad server-component imports

### Step L: Report back

Show the user:

- ✅ Local path
- ✅ GitHub URL (`gh repo view --web` to open in browser)
- ✅ Current branch (should be `develop`)
- ✅ Files + workflows created
- ✅ Branch protection status (applied / skipped with reason)
- ✅ Smoke test results
- 📋 **Next steps** (copy verbatim):

```
Next steps:
1. Push a feature branch and open a PR to develop to confirm CI runs green
2. Fill in the deploy target in `.github/workflows/deploy.yml`
3. Replace the smoke test stubs with real tests as you build features
4. When ready to release, merge develop → main; release-please will open a release PR

Useful commands (run from repo root):
- `npm run check:all` — run everything CI would run
- `npm run dev` — start dev servers
- `pre-commit run --all-files` — manually run all pre-commit hooks
```

---

## The full lifecycle

This is what the scaffold enables out of the box:

1. **Start a new feature** — make a new branch off `develop`, name it something like `feat/dark-mode`. Work on it locally.
2. **Commit your changes** — pre-commit hooks check your code as you commit. Bad code doesn't even get committed.
3. **Open a Pull Request** — push your branch to GitHub and open a PR targeting `develop`. CI runs all 5 checks. The PR can't merge until they're all green.
4. **Merge to develop** — once CI is green and you're happy, merge. Your code is now on `develop`.
5. **Time to release** (skipping `stage` if not enabled, otherwise `develop` → `stage` → `main`) — open a PR from `develop` → `main`. Same checks run.
6. **Release-please takes over** — once merged to `main`, release-please opens a "release PR" with a changelog and a version bump (decided by your commit messages). You review it, merge it.
7. **Tag + deploy** — release-please tags the commit (e.g. `v1.4.0`), creates a GitHub Release, and the deploy workflow kicks off automatically.

---

## Why these defaults (one-line each)

- **Lean `CLAUDE.md`** (50–120 lines): bloat weakens the whole file
- **`main` + `develop` (+ optional `stage`)**: PRs target `develop`, `main` release-only
- **Branch protection on all release branches**: hard stops, not soft rules
- **Pre-commit at root, polyglot**: faster feedback, lower CI cost, one config for fullstack
- **5-check CI pipeline**: matches a standard production pipeline; each step gates on the prior
- **Release-please + conventional commits**: removes manual versioning
- **Deploy stub**: targets vary too much to ship a real implementation
- **Private by default**: easier to flip to public later than the reverse
- **Next.js for frontend / FastAPI for Python BE**: opinionated batteries-included defaults
- **`check:all` as the "run everything" command**: cross-platform, no Make required

## Reference files

- `references/claude-md-templates.md` — CLAUDE.md per stack
- `references/gitignores.md` — `.gitignore` per stack
- `references/configs/` — all per-stack config files
  - `editorconfig.md`
  - `nextjs.md` — Next.js-specific config and install commands
  - `nodejs-backend.md` — Fastify config
  - `python-fastapi.md` — FastAPI config
  - `precommit-unified.md` — single root pre-commit config per stack combo
  - `root-package-scripts.md` — root `package.json` script templates per stack
  - `python-dev-script.md` — `scripts/dev.py` for Python-only projects
- `references/workflows/` — all GitHub Actions workflow files
  - `ci-node.md`
  - `ci-python.md`
  - `ci-fullstack-py-ts.md`
  - `ci-fullstack-node-ts.md`
  - `release-please.md`
  - `deploy.md`
- `references/explainers/` — plain-English concept explainers to surface during scaffold
  - `concepts.md`

## When NOT to use this skill

- User wants to add CLAUDE.md to an *existing* repo — just edit the file, no scaffolding
- User is doing a one-off prototype with no GitHub intent — skip gh + protection steps
- User explicitly says they don't want `develop` — fall back to `main`-only
- User explicitly says they don't want CI yet — skip workflow creation, leave the rest
