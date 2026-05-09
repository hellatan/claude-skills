# Step H — Create GitHub repo + bootstrap push

Creates the remote on GitHub, sets it as `origin`, and pushes the initial scaffold to `main`, `develop`, and (if opted in) `stage`.

## Sequence

```bash
gh repo create <name> --private --source=. --remote=origin

# Bootstrap push — exception: this is the ONLY time pushing directly to
# protected branches is authorized. After this, all changes go through PRs.
ALLOW_PUSH_TO_PROTECTED=1 git push -u origin main
ALLOW_PUSH_TO_PROTECTED=1 git push -u origin develop
```

If staging was opted in:

```bash
ALLOW_PUSH_TO_PROTECTED=1 git push -u origin stage
```

If Step G detected a non-default override env var name, substitute it for `ALLOW_PUSH_TO_PROTECTED=1`.

If user picked **Public** in Step 6, replace `--private` with `--public`.

## The bootstrap exception (read carefully)

This is the **only** point at which `project-scaffold` pushes directly to protected branches. It exists because there's no way to seed `main` and `develop` on a brand-new remote without a direct push (PRs require a target branch to already exist).

**The exception is push-only and scoped to seeding the remote.** After Step H completes:

- All changes (including dep installs, fixups, follow-up commits) go through the standard PR → `develop` flow.
- Branch protection bypass is **never** authorized for merging PRs.
- The skill must not extend the bootstrap exception to any subsequent operation, even if a follow-up step "would be easier" with a direct push. Use a feature branch + PR instead.

## Why each push is its own command

Pushing all branches in one command (e.g., `git push -u origin main develop stage`) seems cleaner but obscures which branch failed if the override env var is wrong. Three separate commands surface failures cleanly and let the user/skill recover from a partial state.
