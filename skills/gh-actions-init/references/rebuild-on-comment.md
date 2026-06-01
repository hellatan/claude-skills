````markdown
# /rebuild on comment

A ChatOps re-trigger: commenting `/rebuild` on a PR re-runs its failed CI (or kicks off CI fresh when none ran). Companion to `release-please.md` and `develop-to-main-pr.md`.

## Why this exists

GitHub does not fire workflows for events created by the default `GITHUB_TOKEN` (its guard against recursive Actions loops). PRs opened by `github-actions[bot]` — release-please's release PR and the `develop → main` PR — therefore never trigger the `pull_request` CI, and with strict branch protection they're stuck at "no checks reported." This workflow lets a maintainer re-run CI from the PR with a single comment. (The root fix is a PAT — see `release-please.md` / `develop-to-main-pr.md`; this is the universal manual fallback and a general "re-run flaky CI" affordance.)

## When to scaffold

- **Default-on for gitflow repos** (those with a `develop` branch) — that's where the bot-PR flows exist.
- Skip for `main`-only repos (no bot-PR gap to cover).
- The file must live on the **default branch** (`develop`) to be active, since `issue_comment` workflows only run from the default branch.
- Skip if `.github/workflows/ci-rebuild-on-comment.yml` already exists.

## Security

- Restricted to trusted commenters via `author_association` ∈ {OWNER, MEMBER, COLLABORATOR}, so outside contributors can't trigger it.
- It **never checks out PR-head code** — it only calls `gh run rerun` / `gh workflow run`, so there is no code-execution ("pwn request") vector despite running with repo secrets.
- An exact-match gate (trimmed body must equal `/rebuild`) stops prose that merely mentions `/rebuild` from firing a build.

## Workflow

`.github/workflows/ci-rebuild-on-comment.yml`:

```yaml
name: CI rebuild on comment

on:
  issue_comment:
    types: [created]

permissions:
  actions: write          # rerun / dispatch workflow runs
  contents: read
  pull-requests: write    # post the result comment
  issues: write           # 👀 reaction (PR comments use the issues reactions endpoint)

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
            gh pr comment "$PR" --body "🚀 Re-running ${#ids[@]} failed/cancelled run(s) for \`$head\`."
          else
            gh workflow run ci.yml --ref "$head"
            gh pr comment "$PR" --body "🚀 No prior run to re-run — dispatched \`ci.yml\` on \`$head\`."
          fi
```

**Adapt the dispatch fallback** (`gh workflow run ci.yml`) to the repo's actual CI workflow filename if it isn't `ci.yml` (e.g. a docs/skills repo whose CI is `validate.yml`). The target workflow must have `workflow_dispatch:` in its `on:` block (see `ci-structure.md`).

## Notes for the report

- Lives on `develop` (default branch) to be active.
- Pairs with the PAT setup: PAT fixes bot-PR CI automatically; `/rebuild` is the manual fallback for any red/missing run.
````
