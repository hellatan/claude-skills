# Step 17 — Create GitHub repo + bootstrap push

Creates the remote on GitHub, sets it as `origin`, and pushes the initial scaffold to `main`, `develop`, and (if opted in) `stage`.

The push is bracketed by two **real halts** so the user can toggle Claude Code's auto-mode off before the push and back on after. Don't skip these gates with a text-only note — text gets skipped past mid-flow; the halts force a conscious action.

## Step 17a — PRE-PUSH GATE (halt for user action)

Print this message **verbatim** and wait for explicit `go` / `ok` / `proceed` before continuing. Don't auto-continue on silence.

> ⚠️ **Bootstrap push coming up** — the only time this skill pushes directly to `main`/`develop`. After this, every change goes through normal PRs.
>
> Claude Code's auto-mode safety classifier will intercept this push and won't surface an approval dialog (it's independent of your personal settings and can't be configured from inside the session). Your local pre-push hook, if you have one, is handled by the override env var Step 16 confirmed — that part is fine.
>
> **Please toggle auto-mode OFF now** (Shift-Tab in the CLI, or `/config`), then reply `go`. After the push, I'll prompt you to turn auto-mode back on.

If the user replies anything other than affirmative confirmation, stop and surface why they're hesitant — don't push.

## Step 17b — Push

```bash
gh repo create <name> --private --source=. --remote=origin

# Allow GitHub Actions to create + approve PRs on this repo.
# Default for new repos is OFF, which makes the first workflow run that calls
# `gh pr create` (or uses an action that creates PRs internally, like
# googleapis/release-please-action) fail with:
#   pull request create failed: GraphQL: GitHub Actions is not permitted to
#   create or approve pull requests (createPullRequest)
gh api repos/<owner>/<name>/actions/permissions/workflow --method PUT \
  --field default_workflow_permissions=write \
  --field can_approve_pull_request_reviews=true

# Bootstrap push — exception: this is the ONLY time pushing directly to
# protected branches is authorized. After this, all changes go through PRs.
ALLOW_PUSH_TO_PROTECTED=1 git push -u origin main
ALLOW_PUSH_TO_PROTECTED=1 git push -u origin develop
```

If staging was opted in:

```bash
ALLOW_PUSH_TO_PROTECTED=1 git push -u origin stage
```

If Step 16 detected a non-default override env var name, substitute it for `ALLOW_PUSH_TO_PROTECTED=1`.

If user picked **Public** in Step 7, replace `--private` with `--public`.

### Why the workflow-permissions API call

`release-please.yml` (scaffolded in Step 14) and any workflow that uses `GITHUB_TOKEN` to create PRs — auto-promote, label-driven backports, dependency bumps, anything that calls `gh pr create` from CI — needs the repo-level setting **"Allow GitHub Actions to create and approve pull requests"** to be on. GitHub's default for new repos is **off**, so without this call the very first PR-creating workflow run fails with `GraphQL: GitHub Actions is not permitted to create or approve pull requests (createPullRequest)`. For release-please specifically, the error doesn't surface until the first non-`chore:` commit lands on `main` (chore-only history produces no version-bump PR), so the failure can sit dormant for weeks before biting.

The flag names (`default_workflow_permissions=write`, `can_approve_pull_request_reviews=true`) are exact — both are required and both are easy to typo. Doing this immediately after `gh repo create`, before the first push, means the setting is in place before any workflow ever runs.

## Step 17c — POST-PUSH GATE (halt, tell user to re-enable auto-mode)

Print **verbatim** and wait for explicit reply (`on` / `continue` / `done`) before continuing to Step 18. Don't auto-continue.

> ✅ **Bootstrap push done.** `main` and `develop` are seeded on the remote.
>
> All subsequent operations (branch protection, default-branch swap, smoke test, future PRs) honor the workflow rules normally — no more direct pushes to protected branches from this skill.
>
> **You can toggle auto-mode back ON now** if you had it off. Reply `continue` when ready (or `on` once you've toggled it).

This gate exists because the post-push steps (branch protection, default-branch swap, smoke test) involve plenty of `gh api` and `npm` calls the user may prefer to have auto-mode handle — and there's no other natural pause where they'd remember to flip it back.

## The bootstrap exception (read carefully)

This is the **only** point at which `project-scaffold` pushes directly to protected branches. It exists because there's no way to seed `main` and `develop` on a brand-new remote without a direct push (PRs require a target branch to already exist).

**The exception is push-only and scoped to seeding the remote.** After Step 17 completes:

- All changes (including dep installs, fixups, follow-up commits) go through the standard PR → `develop` flow.
- Branch protection bypass is **never** authorized for merging PRs.
- The skill must not extend the bootstrap exception to any subsequent operation, even if a follow-up step "would be easier" with a direct push. Use a feature branch + PR instead.

## Why each push is its own command

Pushing all branches in one command (e.g., `git push -u origin main develop stage`) seems cleaner but obscures which branch failed if the override env var is wrong. Three separate commands surface failures cleanly and let the user/skill recover from a partial state.
