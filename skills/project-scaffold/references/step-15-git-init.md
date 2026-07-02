# Step 15 — Git init + branches + activate pre-commit

Initialize the git repo, activate pre-commit hooks (deferred from Step 13, since `pre-commit install` requires `.git/` to exist), apply auto-fixers to the working tree, then make the initial commit so it lands clean — no follow-up PR for trailing newlines, prettier formatting, etc.

## Sequence

```bash
git init -b main

# Verify the release-please manifest invariant BEFORE the initial commit.
# package.json version, pyproject.toml version, and
# .github/.release-please-manifest.json must all read 0.1.0. If any differ,
# release-please's first PR opens with a confusing "no changes since X" diff.
# The baseline is 0.1.0, NOT 0.0.0: an exact-0.0.0 manifest with no tag makes
# release-please bootstrap the first release to 1.0.0, ignoring the pre-major
# bump options (googleapis/release-please#2087).
if [[ -f package.json ]]; then
  node -e "process.exit(require('./package.json').version === '0.1.0' ? 0 : 1)" \
    || { echo "ABORT: package.json version must be 0.1.0 before initial commit (see references/configs/nextjs.md)"; exit 1; }
fi
if [[ -f .github/.release-please-manifest.json ]]; then
  grep -q '"0.1.0"' .github/.release-please-manifest.json \
    || { echo "ABORT: .release-please-manifest.json must read 0.1.0 before initial commit"; exit 1; }
fi

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

Run the auto-fixers *before* the initial commit. Generators like `create-next-app` produce files that don't satisfy the hooks (missing trailing newlines, non-prettier formatting), and the bootstrap-exception contract (Step 17) means post-commit fixes could only land via a pointless fixup PR on every new project.

## Why the version check exists

`create-next-app` initializes `package.json` with `"version": "0.1.0"`, which is exactly the baseline release-please needs. The skill's framework-config step (Step 11 / `references/configs/nextjs.md`) pins it (and seeds the manifest + any `pyproject.toml` at `0.1.0` too), but a hand-edit, a non-Next generator with a different default, or a missed pin can leave the three out of sync. Two ways a mismatch bites:

1. If `package.json` and `.release-please-manifest.json` disagree (one at `0.1.0`, the other at something else), release-please's very first PR generates a confusing "no changes since X" diff that lies about the project's release history before any code has shipped.
2. If the version files are left at `0.0.0` (the old, wrong baseline), release-please bootstraps the first release straight to `1.0.0` regardless of commit type. Canonical explanation + issue link: `gh-actions-init/references/release-please.md`, "Manifest — match current version".

Catching the mismatch *before* the initial commit means it surfaces in 5 seconds, not after the first attempt to cut a release.

## Caveats

- **Non-fixable hook violations** (a real ESLint error that `--fix` can't resolve, a real type error, a real ruff lint that requires a code change) will still block the commit. That's correct — the scaffold shouldn't ship broken code. If a hook fails non-fixably, surface it and stop; don't try to bypass.
- The `pre-commit autoupdate` step before the first run is intentional: it pulls current hook revisions before they have a chance to lag, so the user doesn't start out on stale hook versions.

## Why we do this on `develop`, not `main`

Switching to `develop` after creating both branches means the user's first feature work happens on `develop` (and PRs back to `develop` like the rest of the workflow). `main` stays untouched until the first release-please PR.
