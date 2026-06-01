# CI re-trigger ergonomics — design

**Date:** 2026-05-31
**Status:** Approved (brainstorming) → ready for implementation plan
**Home skill:** `gh-actions-init` (CI/release owner). `project-scaffold` inherits via its existing delegation to `gh-actions-init`.

## Problem

GitHub does not fire workflows for events created by the default `GITHUB_TOKEN` (its guard against recursive Actions loops). Both bot-created PR flows in this convention are affected:

- **release-please** PRs (`chore: release X.Y.Z`)
- **develop → main** PRs (opened by `develop-to-main-pr.yml`)

Both are opened by `github-actions[bot]` using `GITHUB_TOKEN`, so the `pull_request`-triggered CI never runs on them. With `main` branch protection requiring the CI status check (strict), these PRs are stuck with "no checks reported" and can't satisfy the required check without a manual nudge (observed live: this repo's release PR #40).

There is also no ergonomic "rebuild now" affordance for re-running flaky or failed CI from the PR itself.

## Goals

1. A free, universal manual re-trigger knob on CI workflows.
2. A `/rebuild` PR-comment ChatOps trigger that re-runs failed/stuck CI (and covers the bot-PR no-run case).
3. Documented PAT/App-token wiring that fixes the bot-PR-no-CI problem at the root.
4. Dogfood all three into this repo's own workflows.

## Non-goals

- Replacing branch protection or `strict` status checks.
- Running untrusted PR-head code in the privileged comment context (explicitly avoided — see Security).
- A general ChatOps framework (only `/rebuild`; no `/deploy`, `/merge`, etc.).

## Decisions (pinned during brainstorming)

| Decision | Choice |
|---|---|
| `workflow_dispatch` on CI | **Always-on** (added to the template unconditionally) |
| `/rebuild` comment workflow | **Default-on for gitflow repos** (auto-scaffolded, not opt-in) |
| PAT/App-token wiring | **Documented + commented-out** `token:` line (user supplies the secret) |
| Trigger guard | `author_association` ∈ {OWNER, MEMBER, COLLABORATOR} |
| Rebuild scope | **All failed/incomplete runs** on the PR head; dispatch `ci.yml` if none ran |
| Phrase match | **Exact** — trimmed comment body must equal `/rebuild` |
| Comment-logic location | **Separate** `ci-rebuild-on-comment.yml` (not folded into `ci.yml`) |

## Components

### 1. `workflow_dispatch` on CI workflows (always-on)

Edit `gh-actions-init/references/ci-structure.md`: add `workflow_dispatch:` to the `on:` block of both the Node/TS and Python `ci.yml` templates.

```yaml
on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [main, develop]
  workflow_dispatch:        # manual "rebuild now" + dispatch fallback target
```

Enables `gh workflow run ci.yml --ref <branch>` from CLI/UI and serves as the fallback target for the comment workflow's no-run case.

### 2. `/rebuild` comment workflow (default-on for gitflow repos)

New reference `gh-actions-init/references/rebuild-on-comment.md` documenting the workflow and its when-to-scaffold rule. Scaffolds `.github/workflows/ci-rebuild-on-comment.yml`:

```yaml
name: CI rebuild on comment

on:
  issue_comment:
    types: [created]

permissions:
  actions: write          # rerun / dispatch workflow runs
  contents: read
  pull-requests: write    # post the result comment
  issues: write           # 👀 reaction on the comment (PR comments use the issues reactions endpoint)

concurrency:
  group: rebuild-${{ github.event.issue.number }}
  cancel-in-progress: false

jobs:
  rebuild:
    if: >
      github.event.issue.pull_request &&
      contains(fromJSON('["OWNER","MEMBER","COLLABORATOR"]'), github.event.comment.author_association) &&
      startsWith(github.event.comment.body, '/rebuild')
    runs-on: ubuntu-latest
    steps:
      - name: Enforce exact match
        id: gate
        env:
          BODY: ${{ github.event.comment.body }}
        run: |
          # Trim whitespace; must equal exactly "/rebuild"
          trimmed="$(printf '%s' "$BODY" | tr -d '\r' | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
          if [[ "$trimmed" == "/rebuild" ]]; then
            echo "ok=true" >> "$GITHUB_OUTPUT"
          else
            echo "ok=false" >> "$GITHUB_OUTPUT"
            echo "Comment was not exactly '/rebuild' — ignoring."
          fi

      - name: Acknowledge with 👀
        if: steps.gate.outputs.ok == 'true'
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: gh api repos/${{ github.repository }}/issues/comments/${{ github.event.comment.id }}/reactions -f content=eyes

      - name: Re-run failed CI (or dispatch if nothing ran)
        if: steps.gate.outputs.ok == 'true'
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          PR: ${{ github.event.issue.number }}
        run: |
          head="$(gh pr view "$PR" --json headRefName -q .headRefName)"
          mapfile -t ids < <(gh run list --branch "$head" --limit 20 \
            --json databaseId,status,conclusion \
            -q '.[] | select(.status!="in_progress" and (.conclusion=="failure" or .conclusion=="cancelled" or .conclusion=="timed_out")) | .databaseId')
          if [[ ${#ids[@]} -gt 0 ]]; then
            for id in "${ids[@]}"; do gh run rerun "$id" --failed || gh run rerun "$id"; done
            msg="🚀 Re-running ${#ids[@]} failed/cancelled run(s) for \`$head\`."
          else
            # No reusable run (e.g. bot-authored PR never triggered CI) → dispatch fresh.
            gh workflow run ci.yml --ref "$head"
            msg="🚀 No prior run to re-run — dispatched \`ci.yml\` on \`$head\`."
          fi
          gh pr comment "$PR" --body "$msg"
```

When-to-scaffold rule (documented in the reference): scaffold this only for **gitflow** repos (those with a `develop` branch), since that is exactly where bot-PR flows exist. `main`-only repos don't need it. The workflow file must exist on the **default branch** (`develop`) to be active.

### 3. PAT/App-token wiring (documented, both bot workflows)

Add a section to **both** `gh-actions-init/references/release-please.md` and `gh-actions-init/references/develop-to-main-pr.md`:

- A commented `# token: ${{ secrets.RELEASE_PLEASE_PAT }}` line in the relevant `with:` / step.
- Setup note: create a **fine-grained PAT** scoped to the repo with **Contents: read/write** + **Pull requests: read/write**, add it as repo secret `RELEASE_PLEASE_PAT`; note that a PAT belongs to a person and **expires** (renewal needed), with a GitHub App as the no-expiry alternative for shared/long-lived setups.
- Explain *why*: a PAT makes the bot's PRs "user-authored" so CI fires automatically — the root fix that `/rebuild` otherwise patches manually.

### 4. Dogfood into this repo (`claude-skills`)

In the same PR, apply all three to this repo's own workflows:
- `workflow_dispatch:` added to `.github/workflows/validate.yml`.
- New `.github/workflows/ci-rebuild-on-comment.yml`, with the dispatch fallback targeting `validate.yml` (this repo's CI workflow) instead of `ci.yml`.
- PAT-note comment lines added to `.github/workflows/release-please.yml` and `.github/workflows/develop-to-main-pr.yml`.

### 5. Docs

- `gh-actions-init/SKILL.md`: short subsection describing the CI re-trigger pieces + the new reference in the reference list.
- Scaffold summary (the emoji code block, `step-08-summary-template.md` / `project-scaffold`): add a `🔁 CI re-trigger: /rebuild comment + workflow_dispatch` line when gitflow.

## Security

- The comment workflow runs in the privileged base context with secrets. It is restricted to trusted `author_association` (OWNER/MEMBER/COLLABORATOR) so outside contributors can't trigger it.
- It **never checks out PR-head code** — it only calls `gh run rerun` / `gh workflow run`, so there is no "pwn request" code-execution vector.
- Exact-match gate prevents accidental triggering from prose.

## Error handling

- Non-matching comments: gate step sets `ok=false`; subsequent steps skip. No reaction, no comment (silent ignore).
- `gh run rerun` on a non-rerunnable run: per-run failure is tolerated (`|| gh run rerun "$id"`), loop continues.
- No reusable runs: dispatch path posts an explanatory comment.

## Testing

- `./scripts/validate.sh` — skills frontmatter/structure lint (must pass).
- YAML well-formedness check on the new workflow file.
- Behavioral path (comment → rerun/dispatch) can only be verified on a live PR; documented as a **manual post-merge smoke check**, not faked in CI.

## Composition across skills

- `gh-actions-init` owns and writes all workflow templates and references.
- `project-scaffold` requires no new logic: it already delegates CI/release setup to `gh-actions-init`, so the new pieces flow through automatically. Only its summary line (component 5) is touched.
