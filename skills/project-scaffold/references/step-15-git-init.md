# Step 15 — Git init + branches + activate pre-commit

Initialize the git repo, create the long-lived branches, and activate pre-commit hooks (deferred from Step 13, since `pre-commit install` requires `.git/` to exist).

## Sequence

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

## Activate pre-commit hooks

```bash
pre-commit install
pre-commit autoupdate
```

`pre-commit install` writes `.git/hooks/pre-commit` so hooks fire on every commit. `pre-commit autoupdate` bumps hook revisions to current versions so the user doesn't start out on stale ones.

## Why we do this on `develop`, not `main`

Switching to `develop` after creating both branches means the user's first feature work happens on `develop` (and PRs back to `develop` like the rest of the workflow). `main` stays untouched until the first release-please PR.
