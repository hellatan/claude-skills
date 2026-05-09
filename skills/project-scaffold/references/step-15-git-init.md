# Step 15 — Git init + branches + activate pre-commit

Initialize the git repo, activate pre-commit hooks (deferred from Step 13, since `pre-commit install` requires `.git/` to exist), apply auto-fixers to the working tree, then make the initial commit so it lands clean — no follow-up PR for trailing newlines, prettier formatting, etc.

## Sequence

```bash
git init -b main

# Activate hooks BEFORE the initial commit so the initial commit lands clean.
pre-commit install
pre-commit autoupdate

# Apply auto-fixers (end-of-file-fixer, prettier --write, eslint --fix, ruff --fix)
# to the working tree. The first run typically modifies files (e.g.,
# create-next-app's .gitignore and public/*.svg ship without trailing
# newlines). `|| true` because pre-commit exits non-zero whenever a hook
# modifies a file, even though that's exactly what we want on this first pass.
git add .
pre-commit run --all-files || true
git add .

# Now commit — hooks re-run as the actual pre-commit gate, find nothing left
# to fix, and the commit lands cleanly.
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

## Why this order matters

The naive order (commit first, install hooks after) bakes a trivial fixup PR into every scaffold:

1. `create-next-app` (and other generators) produce files that don't satisfy the hooks (missing trailing newlines, slightly different prettier formatting, etc.).
2. The initial commit captures these files as-is because no hooks have been installed yet.
3. The user's first `pre-commit run` then finds dozens of "issues" the auto-fixers happily resolve — but they're now sitting as uncommitted changes on top of the initial scaffold commit.
4. Per the bootstrap-exception contract (Step 17), the only way to land them is via a feature branch + PR.

That PR adds nothing of value and is friction for every new project. Running the auto-fixers *before* the initial commit eliminates it.

## Caveats

- **Non-fixable hook violations** (a real ESLint error that `--fix` can't resolve, a real type error, a real ruff lint that requires a code change) will still block the commit. That's correct — the scaffold shouldn't ship broken code. If a hook fails non-fixably, surface it and stop; don't try to bypass.
- The `pre-commit autoupdate` step before the first run is intentional: it pulls current hook revisions before they have a chance to lag, so the user doesn't start out on stale hook versions.

## Why we do this on `develop`, not `main`

Switching to `develop` after creating both branches means the user's first feature work happens on `develop` (and PRs back to `develop` like the rest of the workflow). `main` stays untouched until the first release-please PR.
