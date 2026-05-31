---
name: precommit-init
description: Add pre-commit hooks at the repo root to an existing project — installs the `pre-commit` package, generates a `.pre-commit-config.yaml` per stack (Python-only, Node-only, fullstack), activates the git hook, and runs `pre-commit autoupdate` so the user starts on current hook revisions. Use when the user wants to "add pre-commit", "set up pre-commit hooks", "add lint hooks", "set up commit hooks", or otherwise wire pre-commit into a repo that doesn't have it yet. Idempotent — won't overwrite existing config without asking.
---

# precommit-init

Adds [pre-commit](https://pre-commit.com/) hooks at the repo root to an existing project. One unified config covers polyglot repos (e.g., Python backend + TS frontend) — no more husky+lint-staged for Node-only repos and a separate Python pre-commit for Python-only ones.

## When to trigger

User says any of:
- "add pre-commit / pre-commit hooks / commit hooks"
- "set up lint hooks"
- "scaffold pre-commit"
- "polyglot lint setup"

## When NOT to use

- Repo already has `.pre-commit-config.yaml` working — extend manually instead.
- Brand-new project — `project-scaffold` calls this skill internally for Step 13.
- User explicitly wants husky + lint-staged — different tool, this skill won't install it.

## Why pre-commit and not husky

| | husky + lint-staged | pre-commit |
|---|---|---|
| Origin | Node ecosystem | Python ecosystem |
| Polyglot repos | Awkward — write shell to dispatch by file extension | Native — each hook declares which file types it runs on |
| Updates | Manual | `pre-commit autoupdate` bumps everything |
| Hook ecosystem | DIY | Versioned community-maintained hooks per language |

Verdict: pre-commit wins for polyglot, ties or wins for single-language. This skill defaults to pre-commit always.

---

## Flow

### 1. Detect stack

Read these without asking:

```bash
[[ -f package.json ]] && stack_node=true
[[ -f pyproject.toml || -f setup.py || -f setup.cfg ]] && stack_python=true
[[ -f .pre-commit-config.yaml ]] && existing_config=true

# Frontend layout? (helps with the bash wrapper for ESLint cwd)
[[ -d frontend ]] && [[ -f frontend/package.json ]] && fullstack_subdirs=true

# Is pre-commit installed already?
command -v pre-commit >/dev/null && have_precommit=true
```

Surface findings: *"Detected: TypeScript (root `package.json`) + Python (`backend/pyproject.toml`), fullstack subdirs. Will write a polyglot config that dispatches by file path."*

### 2. Handle existing config

If `.pre-commit-config.yaml` already exists, **stop**:

> Found an existing `.pre-commit-config.yaml`. Extending it automatically risks breaking your current hook setup. Three options:
> 1. I print the recommended config — you merge by hand.
> 2. I overwrite (you keep a backup at `.pre-commit-config.yaml.bak`).
> 3. Skip — keep your current config as-is.

Wait for the user to pick. Don't merge configs algorithmically.

### 3. Pick config variant

Prescriptive — based on stack detection:

- **Python-only** → ruff + mypy + standard pre-commit-hooks
- **Node-only** → ESLint + Prettier + typecheck (via `language: system` so the project's installed tools run with the project's full config)
- **Fullstack** (Python backend + TS frontend) → both, dispatched by file path; ESLint hook `cd`s into `frontend/` to find its flat config (a known monorepo gotcha — see `references/precommit-config.md`)
- **Node + Node fullstack** (npm workspaces) → polyglot Node config

### 4. Show summary, halt for confirmation

Render the plan as a code block with emoji headers (same convention as other skills):

```
🔍 Detected:        <stack summary>
📝 Config variant:  <python | node | fullstack-py-ts | fullstack-node>
📂 Files to write:  .pre-commit-config.yaml
📦 Packages:        pre-commit (via pip / uv)
🔌 Hook activation: pre-commit install + pre-commit autoupdate
```

End with: *"Reply 'yes' / 'go' / 'looks good' to proceed, or tell me what to change."*

### 5. **HALT for confirmation**

Same gate as other skills. Wait for explicit affirmative reply.

---

## Execution

### 6. Install the `pre-commit` package

Skip if already installed (Step 1 detection). Otherwise:

```bash
pip install pre-commit
# or, for uv-managed projects:
uv add --dev pre-commit
```

For Node-only repos with no Python: still use `pip install pre-commit` (it's a small Python tool, doesn't pollute the Node project — pre-commit itself runs out-of-tree). Surface this in the report so the user knows why pip ran.

### 7. Write `.pre-commit-config.yaml`

Pick the variant from `references/precommit-config.md`:

- "Config: Python-only"
- "Config: Node-only"
- "Config: Python + TS Fullstack"
- "Config: Node + Node Fullstack (npm workspaces)"

The fullstack variants include the critical `bash -c` wrapper for ESLint that strips the `frontend/` prefix from staged paths — without it, eslint errors with "no files matching pattern" when invoked from root.

For **mypy-using** Python configs, the `additional_dependencies:` block must include the project's runtime deps (FastAPI, Pydantic, etc.) so mypy can resolve imports. The reference doc spells out the right starter list.

### 8. Activate the hook

```bash
pre-commit install
```

This requires `.git/` to exist. If not (rare on existing repos), surface the issue and stop.

### 9. Bump hook revs

```bash
pre-commit autoupdate
```

Bumps every hook in the config to its current revision so the user doesn't start on stale ones. Idempotent on repeat runs.

### 10. Smoke test

```bash
pre-commit run --all-files
```

This may fix end-of-file-fixer / trailing-whitespace issues on existing files. **Don't fail the smoke test if it does that** — those are intentional auto-fixes. Surface them in the report and ask if the user wants to commit them.

### 11. Report back

- ✅ Stack detected
- ✅ Config variant + file written
- ✅ Hook activated, autoupdate ran
- ⚠️ Any auto-fixes applied during smoke test (e.g., EOF fixes on existing files)
- 📋 Next steps:

```
Next steps:
1. Review and commit any auto-fixes applied during the smoke run
2. Make a real commit — pre-commit fires automatically on staged files
3. Bypass with `git commit --no-verify` only in emergencies (project conventions usually forbid this)
```

---

## Reference files

- `references/precommit-config.md` — full per-stack `.pre-commit-config.yaml` templates + the bash-wrapper detail for fullstack subdir layouts

## Why these defaults

- **`language: system` for ESLint/Prettier hooks** (Node configs) — runs the project's installed tools with the project's full config. The `mirrors-eslint` repo uses an isolated env that doesn't see local plugins, so it produces wrong results on real configs.
- **Don't put tests in pre-commit** — tests belong in CI. Pre-commit should be fast (<5s ideally). Even unit tests via pre-commit slow commits enough to discourage frequent commits.
- **Idempotent** — running this skill twice is safe: it skips the install if already present, refuses to overwrite an existing config without explicit consent, and `pre-commit autoupdate` is a no-op when revs are current.
