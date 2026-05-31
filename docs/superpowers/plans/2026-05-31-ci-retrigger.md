# CI Re-trigger Ergonomics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give scaffolded gitflow repos (and this repo) a manual CI re-trigger via `workflow_dispatch`, a default-on `/rebuild` PR-comment workflow, and documented PAT wiring so bot-authored PRs (release-please, develop→main) get CI automatically.

**Architecture:** All template work lives in `gh-actions-init` (which `project-scaffold` already delegates to). Three additive pieces — a `workflow_dispatch` trigger on CI, a new `ci-rebuild-on-comment.yml` from a new reference doc, and PAT notes on both bot-PR workflows — then the same three dogfooded into this repo's own `.github/workflows/`.

**Tech Stack:** GitHub Actions YAML, `gh` CLI, the repo's `scripts/validate.sh` skill linter, Python `yaml` for well-formedness checks.

**Spec:** `docs/superpowers/specs/2026-05-31-ci-retrigger-design.md`

**Conventions:** Conventional commits. Co-author trailer `Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>`. Work stays on branch `feat/ci-retrigger-ergonomics`. Never push to develop/main; push the feature branch with an explicit refspec.

---

## File Structure

**Template edits (gh-actions-init — inherited by project-scaffold):**
- Modify `skills/gh-actions-init/references/ci-structure.md` — add `workflow_dispatch:` to both `on:` blocks.
- Create `skills/gh-actions-init/references/rebuild-on-comment.md` — the `/rebuild` workflow + when-to-scaffold + security.
- Modify `skills/gh-actions-init/references/release-please.md` — PAT note + commented `token:` line.
- Modify `skills/gh-actions-init/references/develop-to-main-pr.md` — PAT note + commented `GH_TOKEN` swap.
- Modify `skills/gh-actions-init/SKILL.md` — new decision (e), summary line, reference-list entry.
- Modify `skills/project-scaffold/references/step-08-summary-template.md` — `🔁 CI re-trigger` line.

**Dogfood (this repo's own workflows):**
- Modify `.github/workflows/validate.yml` — add `workflow_dispatch:`.
- Create `.github/workflows/ci-rebuild-on-comment.yml` — dispatch fallback targets `validate.yml`.
- Modify `.github/workflows/release-please.yml` — commented PAT `token:` line.
- Modify `.github/workflows/develop-to-main-pr.yml` — commented PAT `GH_TOKEN` note.

---

## Task 1: Add `workflow_dispatch` to the CI template (both stacks)

**Files:**
- Modify: `skills/gh-actions-init/references/ci-structure.md` (Node `on:` ~lines 12-16; Python `on:` ~lines 72-76)

- [ ] **Step 1: Edit the Node/TS `on:` block**

Find (under `## Node / TypeScript`):
```yaml
on:
  pull_request:
    branches: [main, develop]   # adjust per branch detection
  push:
    branches: [main, develop]
```
Replace with:
```yaml
on:
  pull_request:
    branches: [main, develop]   # adjust per branch detection
  push:
    branches: [main, develop]
  workflow_dispatch:            # manual "rebuild now" + dispatch target for /rebuild
```

- [ ] **Step 2: Edit the Python `on:` block**

Find (under `## Python`):
```yaml
on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [main, develop]
```
Replace with:
```yaml
on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [main, develop]
  workflow_dispatch:            # manual "rebuild now" + dispatch target for /rebuild
```

- [ ] **Step 3: Verify both were added**

Run: `grep -c 'workflow_dispatch:' skills/gh-actions-init/references/ci-structure.md`
Expected: `2`

- [ ] **Step 4: Validate skills still lint**

Run: `./scripts/validate.sh`
Expected: ends with `All skills valid.`

- [ ] **Step 5: Commit**

```bash
git add skills/gh-actions-init/references/ci-structure.md
git commit -m "feat(gh-actions-init): add workflow_dispatch to ci.yml template

Enables 'gh workflow run ci.yml' manual rebuilds and serves as the
dispatch fallback target for the /rebuild comment workflow.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 2: Create the `rebuild-on-comment.md` reference

**Files:**
- Create: `skills/gh-actions-init/references/rebuild-on-comment.md`

- [ ] **Step 1: Write the reference file**

Create `skills/gh-actions-init/references/rebuild-on-comment.md` with exactly:

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

- [ ] **Step 2: Verify file exists and contains the workflow**

Run: `grep -c 'issue_comment\|/rebuild\|author_association' skills/gh-actions-init/references/rebuild-on-comment.md`
Expected: a number `>= 3`

- [ ] **Step 3: Validate skills lint**

Run: `./scripts/validate.sh`
Expected: `All skills valid.`

- [ ] **Step 4: Commit**

```bash
git add skills/gh-actions-init/references/rebuild-on-comment.md
git commit -m "feat(gh-actions-init): add /rebuild comment-trigger reference

New ci-rebuild-on-comment.yml template: re-runs failed CI (or dispatches
when none ran) on a /rebuild PR comment, guarded by author_association,
exact-match gated, never checks out PR-head code.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 3: Wire the new piece into `gh-actions-init/SKILL.md`

**Files:**
- Modify: `skills/gh-actions-init/SKILL.md` (decision list ~line 78; summary block ~line 117; reference list ~line 178)

- [ ] **Step 1: Add decision (e) after the develop→main decision**

Find:
```
**d. develop → main auto-PR** — `develop-to-main-pr.yml`.

Only relevant when `develop` exists AND there's no `stage` branch (gitflow without staging). Auto-opens/refreshes a draft `develop → main` PR so releases never wait on someone remembering to open it manually. Skip for `main`-only repos and for repos with a `stage` branch (staging topology needs a different two-workflow setup — leave a note). Skip if the file already exists.
```
Insert immediately after it:
```

**e. /rebuild comment trigger** — `ci-rebuild-on-comment.yml`.

Default-on for gitflow repos (where `develop` exists). Lets a maintainer re-run failed CI from a PR by commenting `/rebuild` — covers bot-authored PRs (release-please, develop→main) that `GITHUB_TOKEN` never triggers CI for. Skip for `main`-only repos and if the file already exists. See `references/rebuild-on-comment.md`.
```

- [ ] **Step 2: Add the summary line**

Find:
```
🔁 develop→main PR: <scaffolding | skipped (main-only / staging / already present)>
📝 Files to write:  <list>
```
Replace with:
```
🔁 develop→main PR: <scaffolding | skipped (main-only / staging / already present)>
🔁 /rebuild trigger: <scaffolding | skipped (main-only / already present)>
📝 Files to write:  <list>
```

- [ ] **Step 3: Add the reference-list entry**

Find:
```
- `references/develop-to-main-pr.md` — `develop-to-main-pr.yml`: auto-opens/refreshes the draft `develop → main` release PR (gitflow without staging)
```
Insert immediately after it:
```
- `references/rebuild-on-comment.md` — `ci-rebuild-on-comment.yml`: `/rebuild` PR-comment re-runs failed CI (gitflow); pairs with the PAT setup
```

- [ ] **Step 4: Verify edits**

Run: `grep -c 'rebuild-on-comment\|/rebuild' skills/gh-actions-init/SKILL.md`
Expected: a number `>= 3`

- [ ] **Step 5: Validate + commit**

```bash
./scripts/validate.sh
git add skills/gh-actions-init/SKILL.md
git commit -m "docs(gh-actions-init): document /rebuild comment trigger

Adds decision (e), summary line, and reference-list entry for the
default-on ci-rebuild-on-comment.yml.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 4: PAT/App-token notes on both bot-PR workflow references

**Files:**
- Modify: `skills/gh-actions-init/references/release-please.md` (with-block ~line 36-39)
- Modify: `skills/gh-actions-init/references/develop-to-main-pr.md` (Prerequisite section ~line 12)

- [ ] **Step 1: Add commented `token:` line to the release-please workflow block**

In `release-please.md`, find:
```yaml
      - uses: googleapis/release-please-action@v5
        with:
          config-file: .github/release-please-config.json
          manifest-file: .github/.release-please-manifest.json
```
Replace with:
```yaml
      - uses: googleapis/release-please-action@v5
        with:
          # token: ${{ secrets.RELEASE_PLEASE_PAT }}   # see "Why a PAT" below — uncomment to make CI run on release PRs
          config-file: .github/release-please-config.json
          manifest-file: .github/.release-please-manifest.json
```

- [ ] **Step 2: Add the "Why a PAT" section to release-please.md**

In `release-please.md`, find:
```
Adjust `branches:` if the project's release branch isn't `main` (rare).
```
Insert immediately after it:
```

## Why a PAT (so CI runs on release PRs)

By default release-please opens its PR as `github-actions[bot]` using `GITHUB_TOKEN`. GitHub deliberately does **not** fire workflows for `GITHUB_TOKEN`-created events (recursion guard), so the `pull_request` CI never runs on the release PR — and with strict branch protection it can't satisfy a required check. Two ways out:

1. **Fine-grained PAT (recommended for personal repos).** Create one scoped to the repo with **Contents: read/write** + **Pull requests: read/write**, add it as repo secret `RELEASE_PLEASE_PAT`, and uncomment the `token:` line above. The release PR is then "authored by you" and triggers CI normally. Caveat: a PAT belongs to a person and **expires** — you'll renew it on the schedule you pick.
2. **GitHub App token** (no expiry, not tied to a person) — more setup; better for shared/long-lived repos.

If you don't wire either, use the `/rebuild` comment workflow (`rebuild-on-comment.md`) to kick CI manually on each release PR.
```

- [ ] **Step 3: Add the PAT note to develop-to-main-pr.md**

In `develop-to-main-pr.md`, find the end of the Prerequisite section:
```
```bash
gh api -X PUT repos/{owner}/{repo}/actions/permissions/workflow \
  -F default_workflow_permissions=write \
  -F can_approve_pull_request_reviews=true
```
```
Insert immediately after that fenced block:
```

### Why CI doesn't run on this PR by default (and the PAT fix)

This PR is opened by `github-actions[bot]` via `GITHUB_TOKEN`, and GitHub does not fire workflows for `GITHUB_TOKEN`-created events — so the `develop → main` PR gets no CI checks. To make CI run, give the `gh pr create`/`gh pr edit` steps a PAT instead of the default token: add a fine-grained PAT (Contents + Pull requests: read/write) as secret `RELEASE_PLEASE_PAT` and set it on the relevant steps:

```yaml
        env:
          # GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}            # default: PR gets no CI
          GH_TOKEN: ${{ secrets.RELEASE_PLEASE_PAT }}        # PAT: PR is user-authored → CI runs
```

Otherwise, comment `/rebuild` on the PR (`rebuild-on-comment.md`) to run CI manually. Same PAT works for both this workflow and release-please.
```

- [ ] **Step 4: Verify**

Run: `grep -l 'RELEASE_PLEASE_PAT' skills/gh-actions-init/references/release-please.md skills/gh-actions-init/references/develop-to-main-pr.md`
Expected: both file paths printed.

- [ ] **Step 5: Validate + commit**

```bash
./scripts/validate.sh
git add skills/gh-actions-init/references/release-please.md skills/gh-actions-init/references/develop-to-main-pr.md
git commit -m "docs(gh-actions-init): document PAT wiring for bot-PR CI

Both release-please and develop-to-main PRs are bot-authored and miss CI
under GITHUB_TOKEN. Add commented token lines + a 'why a PAT' note to each.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 5: Add the `🔁 CI re-trigger` line to the project-scaffold summary

**Files:**
- Modify: `skills/project-scaffold/references/step-08-summary-template.md` (GitHub Actions group ~lines 36-38)

- [ ] **Step 1: Edit the summary layout**

Find:
```
🤖 GitHub Actions (auto-runs on every PR):
   - lint + typecheck → unit tests → integration tests → e2e tests → build
   - Releases handled automatically by release-please
```
Replace with:
```
🤖 GitHub Actions (auto-runs on every PR):
   - lint + typecheck → unit tests → integration tests → e2e tests → build
   - Releases handled automatically by release-please
🔁 CI re-trigger:                               ← include only for gitflow repos (develop exists)
   - Comment `/rebuild` on a PR to re-run failed CI; `workflow_dispatch` for manual runs
```

- [ ] **Step 2: Verify**

Run: `grep -c 'CI re-trigger\|/rebuild' skills/project-scaffold/references/step-08-summary-template.md`
Expected: a number `>= 2`

- [ ] **Step 3: Validate + commit**

```bash
./scripts/validate.sh
git add skills/project-scaffold/references/step-08-summary-template.md
git commit -m "docs(project-scaffold): add CI re-trigger line to summary

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 6: Dogfood — add `workflow_dispatch` to this repo's `validate.yml`

**Files:**
- Modify: `.github/workflows/validate.yml`

- [ ] **Step 1: Edit the `on:` block**

Find:
```yaml
on:
  pull_request:
    branches: [develop, main]
  push:
    branches: [develop, main]
```
Replace with:
```yaml
on:
  pull_request:
    branches: [develop, main]
  push:
    branches: [develop, main]
  workflow_dispatch:        # manual rebuild + dispatch target for /rebuild
```

- [ ] **Step 2: Verify YAML is well-formed**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/validate.yml'))" && echo OK`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/validate.yml
git commit -m "ci: add workflow_dispatch to validate.yml

Enables manual reruns and the /rebuild dispatch fallback (Task 7).

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 7: Dogfood — create this repo's `ci-rebuild-on-comment.yml`

**Files:**
- Create: `.github/workflows/ci-rebuild-on-comment.yml`

- [ ] **Step 1: Write the workflow (dispatch fallback targets `validate.yml`)**

Create `.github/workflows/ci-rebuild-on-comment.yml` with exactly:

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
            gh workflow run validate.yml --ref "$head"
            gh pr comment "$PR" --body "🚀 No prior run to re-run — dispatched \`validate.yml\` on \`$head\`."
          fi
```

- [ ] **Step 2: Verify YAML is well-formed**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci-rebuild-on-comment.yml'))" && echo OK`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci-rebuild-on-comment.yml
git commit -m "ci: add /rebuild comment workflow

Comment /rebuild on a PR to re-run failed CI (or dispatch validate.yml
when none ran). Guarded by author_association, exact-match gated.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 8: Dogfood — PAT note comments in this repo's bot-PR workflows

**Files:**
- Modify: `.github/workflows/release-please.yml`
- Modify: `.github/workflows/develop-to-main-pr.yml`

- [ ] **Step 1: Add commented `token:` to release-please.yml**

Find:
```yaml
      - uses: googleapis/release-please-action@v5
        with:
          config-file: .github/release-please-config.json
          manifest-file: .github/.release-please-manifest.json
```
Replace with:
```yaml
      - uses: googleapis/release-please-action@v5
        with:
          # token: ${{ secrets.RELEASE_PLEASE_PAT }}   # uncomment + add the secret to make CI run on release PRs (GITHUB_TOKEN-authored PRs don't trigger workflows)
          target-branch: main
          config-file: .github/release-please-config.json
          manifest-file: .github/.release-please-manifest.json
```
(Note: `target-branch: main` is already present in this repo's file — preserve it; only the commented `token:` line is new, placed first under `with:`.)

- [ ] **Step 2: Add commented PAT note to develop-to-main-pr.yml**

In `.github/workflows/develop-to-main-pr.yml`, find the `permissions:` block near the top:
```yaml
permissions:
  pull-requests: write
  contents: read
```
Insert immediately after it:
```yaml

# To make CI run on the develop → main PR this workflow opens, give the
# gh steps a PAT instead of GITHUB_TOKEN (bot-authored PRs don't trigger
# workflows): add secret RELEASE_PLEASE_PAT and set
# GH_TOKEN: ${{ secrets.RELEASE_PLEASE_PAT }} on the "Open or refresh PR" step.
```

- [ ] **Step 3: Verify both YAML files still parse**

Run:
```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/release-please.yml')); yaml.safe_load(open('.github/workflows/develop-to-main-pr.yml'))" && echo OK
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/release-please.yml .github/workflows/develop-to-main-pr.yml
git commit -m "ci: document PAT option on bot-PR workflows

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 9: Final verification, push, and PR

- [ ] **Step 1: Full skills lint**

Run: `./scripts/validate.sh`
Expected: `All skills valid.`

- [ ] **Step 2: All changed/new workflow YAML parses**

Run:
```bash
for f in .github/workflows/validate.yml .github/workflows/ci-rebuild-on-comment.yml .github/workflows/release-please.yml .github/workflows/develop-to-main-pr.yml; do
  python3 -c "import yaml,sys; yaml.safe_load(open('$f'))" && echo "$f OK"
done
```
Expected: all four print `OK`.

- [ ] **Step 3: Confirm the spec's pieces are all present**

Run:
```bash
grep -rl 'workflow_dispatch' skills/gh-actions-init/references/ci-structure.md .github/workflows/validate.yml
test -f skills/gh-actions-init/references/rebuild-on-comment.md && echo "ref OK"
test -f .github/workflows/ci-rebuild-on-comment.yml && echo "dogfood workflow OK"
grep -l RELEASE_PLEASE_PAT skills/gh-actions-init/references/release-please.md skills/gh-actions-init/references/develop-to-main-pr.md
```
Expected: paths + `ref OK` + `dogfood workflow OK`.

- [ ] **Step 4: Push the feature branch (explicit refspec — never push to develop/main)**

Run: `git push origin feat/ci-retrigger-ergonomics:feat/ci-retrigger-ergonomics`

- [ ] **Step 5: Open the PR against develop**

Run:
```bash
gh pr create --base develop --head feat/ci-retrigger-ergonomics \
  --title "feat(gh-actions-init): CI re-trigger ergonomics (/rebuild + workflow_dispatch + PAT notes)" \
  --body "Implements docs/superpowers/specs/2026-05-31-ci-retrigger-design.md. Adds workflow_dispatch to the CI template, a default-on /rebuild comment workflow (new reference), PAT wiring notes on both bot-PR flows, and dogfoods all three into this repo's workflows. See the spec for design + decisions."
```

- [ ] **Step 6: Manual post-merge smoke check (note for the human, not automated)**

After merge to develop and the next PR, comment `/rebuild` on an open PR and confirm a 👀 reaction appears and CI re-runs/dispatches. Behavioral path can only be verified live.

---

## Self-Review

**Spec coverage:**
- Component 1 (workflow_dispatch always-on) → Task 1 (template) + Task 6 (dogfood). ✓
- Component 2 (`/rebuild` default-on, new reference) → Task 2 (reference) + Task 3 (SKILL wiring) + Task 7 (dogfood). ✓
- Component 3 (PAT on both bot workflows) → Task 4 (templates) + Task 8 (dogfood). ✓
- Component 4 (dogfood) → Tasks 6/7/8. ✓
- Component 5 (docs: SKILL subsection + scaffold summary) → Task 3 + Task 5. ✓
- Security / error-handling / exact-match → embedded in Task 2 & Task 7 workflow bodies. ✓
- Testing (validate.sh + YAML parse + manual smoke) → Tasks 1-9 verification steps + Task 9 Step 6. ✓

**Placeholder scan:** No TBD/TODO; every workflow body and edit shows full content. ✓

**Consistency:** Workflow body is identical between the template (Task 2) and dogfood (Task 7) except the dispatch fallback target (`ci.yml` vs `validate.yml`) — intentional and called out. `RELEASE_PLEASE_PAT` secret name used consistently across Tasks 4 and 8. The `if:` pre-filter (`startsWith`) plus the exact-match bash gate together implement the "exact match" decision consistently. ✓
