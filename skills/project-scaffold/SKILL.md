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

## Requires

Both `/testing-init` and `/gh-actions-init` must be installed (Step E delegates to them). See `references/sister-skills-dependency.md`.

---

## Flow

Run these steps in order. **Ask questions one at a time.** For decision points where the skill has a strong default, state the default and only wait for an override.

### 0. Verify sister skills are installed (fail fast)

Before Step 1, confirm `/testing-init` and `/gh-actions-init` are in the available-skills list. If either is missing, abort with the message in `references/sister-skills-dependency.md` — don't ask the user any questions until the dependency is satisfied.

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

Render the plan as a fenced code block with emoji-prefixed group headers (not a markdown bullet section). Show only choices made for *this* user's project. End with: *"Reply 'yes' / 'go' / 'looks good' to proceed, or tell me what to change."*

See `references/step-7-summary-template.md` for the layout and rules.

### 8. **HALT — REAL CONFIRMATION GATE**

This is its own dedicated step. **Do not proceed under any circumstances** until the user replies with explicit affirmative confirmation (e.g. "yes", "go", "proceed", "looks good", "ok").

If running in Claude Code with auto-mode enabled, **still halt here** by using a real pausing primitive — ask the user with a question that requires a response, not just instruction text. The user must consciously approve the destructive steps that follow (creating a GitHub repo, applying branch protection, running git commands).

If the user says anything other than affirmative confirmation, ask what they'd like to change and loop back to the relevant step.

---

## Execution

Once confirmed, proceed through these steps without further halts (unless something fails).

### Step A: Create directory + base files

`mkdir -p <parent>/<name>`, `cd` in. **For Next.js projects, run `create-next-app` FIRST with `--skip-git`** — see `references/configs/nextjs.md` for the exact flags and post-scaffold cleanup (delete the stub `CLAUDE.md`, keep `AGENTS.md`).

Write to repo root:
- `CLAUDE.md` — see `references/claude-md-templates.md`
- `.gitignore` — see `references/gitignores.md`
- `README.md` — minimal: `# <project-name>` + one-line description placeholder
- `.editorconfig` — see `references/configs/editorconfig.md`
- `.pre-commit-config.yaml` — see `references/configs/precommit-unified.md`

For fullstack: create `frontend/` and `backend/` subdirs. For Python: create `<package_name>/__init__.py` and (if FastAPI) `<package_name>/main.py` — see `references/configs/python-fastapi.md`. For TS without Next.js: stub `src/index.ts` (Node) or `src/main.tsx` (Vite) so `tsc --noEmit` has something to check.

**After writing all configs, run `npx prettier --write .` once** so create-next-app's `eslint.config.mjs` and other unformatted files don't trip CI's `format:check` on first push.

### Step B: Stack-specific config files

All templates are in `references/configs/`. Pick by stack:

| Stack | Files to write | Reference |
|---|---|---|
| Next.js | `package.json`, `tsconfig.json`, `eslint.config.mjs`, `.prettierrc`, `.prettierignore`, `next.config.ts` | `configs/nextjs.md` |
| Node backend (Fastify) | `package.json`, `tsconfig.json`, `eslint.config.js`, `.prettierrc` | `configs/nodejs-backend.md` |
| Python backend (FastAPI) | `pyproject.toml`, `.python-version` | `configs/python-fastapi.md` |
| Fullstack | Per-side configs in `frontend/` + `backend/` *plus* root coordination layer (root `package.json`, root pre-commit, root `.gitignore`) | both refs above |
| Research | `pyproject.toml` (ruff + jupyter only), `.python-version` | `configs/python-fastapi.md` (lighter variant) |

**Install framework deps for real** — don't reference a tool in scripts without `npm install` / `pip install` first. Each reference doc lists its install commands.

**Monorepo gotcha:** ESLint's flat config resolves from CWD. If `eslint.config.mjs` lives in `frontend/`, pre-commit hooks must `cd frontend` first. Handled by `configs/precommit-unified.md`.

### Step C: Root-level command runner

So users can run lint/test/build from one place without Make (which isn't cross-platform). The canonical command is **`check:all`** — runs everything CI would run.

- **Any project with Node:** root `package.json` with proxying scripts. See `references/configs/root-package-scripts.md` for the full template per stack.
- **Python-only:** scaffold `scripts/dev.py` instead. See `references/configs/python-dev-script.md`.

### Step D: Pre-commit hooks (single unified system at root)

**Default to `pre-commit` for everything** — drop husky. Install: `pip install pre-commit` (or `uv add --dev pre-commit`). Generate `.pre-commit-config.yaml` at repo root per stack — see `references/configs/precommit-unified.md`.

The config dispatches by file pattern: staging only Python files runs only Python hooks, staging only TS files runs only TS hooks, mixing runs both. All from root.

**Do NOT run `pre-commit install` yet** — it requires `.git/`. Step F handles activation after `git init`.

### Step E: Tests + GitHub Actions (delegate to sister skills)

Run `/testing-init`'s execution phase, then `/gh-actions-init`'s. Treat the stack as already-known and skip their detection + summary-halt gates (project-scaffold's Step 8 covered those).

See `references/step-E-delegate.md` for what each sister skill owns, the manifest-version invariant, and the full sub-skill protocol.

### Step F: Git init with main + develop (+ optional stage)

Initialize git, create `main` + `develop` (+ `stage` if opted in), check out `develop`, and activate pre-commit hooks (deferred from Step D since `pre-commit install` needs `.git/` to exist).

See `references/step-F-git-init.md` for the bash sequence.

### Step G: Detect global pre-push hooks before pushing

Before Step H pushes to `main`/`develop`, check whether the user has a global pre-push hook that might block protected-branch pushes. If one exists, ask about override env var conventions before attempting the push — surfacing this *before* Step H keeps the bootstrap atomic.

See `references/step-G-prepush-hooks.md` for the detection commands and the verbatim warning message.

### Step H: Create GitHub repo and push

Create the remote with `gh repo create`, then push `main`, `develop`, and (if opted in) `stage` using the override env var Step G confirmed. **This is the only step in the entire skill that pushes directly to protected branches** — the exception is push-only, scoped to seeding the remote, and never extends to subsequent operations.

See `references/step-H-create-repo-push.md` for the bash sequence and the full bootstrap-exception contract.

### Step I: Branch protection (skip if free-tier private)

Skip entirely if Step 6 showed free-tier + private repo. Otherwise apply protection to `main`, `develop`, and (if staging enabled) `stage`, requiring the CI status checks to pass.

See `references/step-I-branch-protection.md` for the bash function and the 403-fallback message.

### Step J: Set develop as default branch

```bash
gh repo edit --default-branch develop
```

PRs default to merging into `develop`. `main` only gets touched by release-please's release PRs.

### Step K: Smoke test (verify the scaffold actually works)

Before declaring success, run the full smoke sequence from the project root: install deps → lint → typecheck → `pre-commit run --all-files` → test → build → `check:all`. **Don't use empty commits** — invoke hooks directly so there's no commit cleanup needed.

If any step fails, report the specific failure and offer to fix. See `references/step-K-smoke-test.md` for the full bash sequence and common failure modes.

### Step L: Report back

Print a status block (local path, GitHub URL, current branch, files created, branch protection status, smoke test results) followed by the verbatim "Next steps" + "Useful commands" block.

See `references/step-L-report-template.md` for the exact template.

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

### Owned by this skill

- `references/sister-skills-dependency.md` — what Step 0 checks for and why
- `references/step-E-delegate.md` — delegation order, sub-skill responsibilities, manifest-version invariant, sub-skill protocol
- `references/step-F-git-init.md` — git init + branch creation + pre-commit activation sequence
- `references/step-G-prepush-hooks.md` — global pre-push hook detection + warning message
- `references/step-H-create-repo-push.md` — `gh repo create` + bootstrap push sequence + bootstrap-exception contract
- `references/claude-md-templates.md` — CLAUDE.md per stack
- `references/gitignores.md` — `.gitignore` per stack
- `references/step-7-summary-template.md` — emoji-grouped pre-execution summary
- `references/step-I-branch-protection.md` — `gh api` protection script + 403 fallback
- `references/step-K-smoke-test.md` — full smoke sequence + failure-mode cheatsheet
- `references/step-L-report-template.md` — verbatim final report + "Next steps" block
- `references/configs/` — per-stack bootstrap config templates
  - `editorconfig.md`, `nextjs.md`, `nodejs-backend.md`, `python-fastapi.md`
  - `precommit-unified.md`, `root-package-scripts.md`, `python-dev-script.md`
- `references/explainers/concepts.md` — plain-English concept explainers

### Owned by sister skills (Step E delegates here)

- **`/testing-init`** — test runners + configs + smoke stubs + test scripts + test jobs in `ci.yml`. Templates: `skills/testing-init/references/{runners,test-stubs,scripts,ci-test-job}.md`.
- **`/gh-actions-init`** — CI structural jobs + release-please + deploy stub. Templates: `skills/gh-actions-init/references/{detection,ci-structure,release-please,deploy-stub}.md`.

## When NOT to use this skill

- User wants to add CLAUDE.md to an *existing* repo — just edit the file, no scaffolding
- User is doing a one-off prototype with no GitHub intent — skip gh + protection steps
- User explicitly says they don't want `develop` — fall back to `main`-only
- User explicitly says they don't want CI yet — skip workflow creation, leave the rest
