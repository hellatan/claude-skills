# release verification + failure alerting

A safety-net that fails loudly when a release *should* have been tagged but wasn't — the prerequisite for ever auto-merging release PRs, since it removes "a human happened to be watching the merge" as the only guard. Alerts post to a Discord channel.

It is also the **gate the tagged-only deploy hangs off**: the `Evaluate release outcome` step emits a `released` output that is `true` only when a tag was cut *and* confirmed on the remote, and the deploy step in `references/tagged-deploy.md` runs on nothing else. So this file isn't optional decoration — without it there is no trustworthy signal that a deploy is warranted.

Scaffold this **alongside release-please** (same condition — skip it when release-please is skipped). Three pieces:

1. `verify-tag` — steps appended to the `release-please.yml` job (see `references/release-please.md`).
2. `.github/workflows/release-health.yml` — a daily sweep + an on-demand self-test.
3. `.github/actions/discord-alert/action.yml` — a shared composite that posts the alert.

The Discord webhook secret is **optional**: the composite no-ops (with a warning) when it's unset, so scaffolding this is harmless even if the user never wires up alerting.

## Choosing the alert channel — ask, don't assume

`<ALERT_WEBHOOK_SECRET>` in the templates below is a **placeholder you fill in at scaffold time**. A Discord webhook URL points at exactly one channel, so the secret *is* the channel: which secret name a repo's workflows read is how that project picks where its alerts land.

**Name the destination channel in the test alert itself.** Substitute `<ALERT_CHANNEL_LABEL>` (a short token, e.g. `gh_errors`) and `<ALERT_CHANNEL>` (the channel as it reads in Discord, e.g. `#gh-errors`) alongside the secret name. A test that only says "alert pipe test" proves a message *arrived* but not that it arrived in the *right place* — a webhook copied from the wrong channel delivers a clean 204 and looks exactly like success. Naming the expected channel in the title and body makes a misroute obvious on sight instead of silently passing. Same for the PR-alerts arm.

Ask the user which secret to use and substitute it into all three files before writing them. Default to **`DISCORD_GH_ERRORS_WEBHOOK`** — the shared errors channel — when they have no preference; a project that wants its own channel (`DISCORD_<PROJECT>_ALERTS`, `DISCORD_DEPLOY_WEBHOOK`, …) just names a different secret. Keep the name identical across `release-please.yml` and `release-health.yml`; a mismatch means half the alerts silently no-op.

To repoint an existing repo later, either overwrite the secret's value with a different channel's webhook URL (name unchanged, nothing to edit) or rename it and update every `secrets.` reference in `.github/workflows/`.

## Choosing the sweep schedule — stagger it

`<CRON_MINUTE>` in the `release-health.yml` template is the second scaffold-time placeholder: pick an **arbitrary minute (1–59, never 0)** per repo. GitHub's scheduler delays — and under load skips — runs in congested slots, and `:00` of every hour is the most congested of all; a skipped run of a freeze-detector is the same silent failure it exists to catch, one level up. The hour is pinned at **08:00 UTC**, a quiet window (US asleep, Europe just starting), so only the minute varies. Vary it per repo (don't reuse one favorite minute across a fleet), and don't ask the user — no one cares when a daily sweep runs, only that it does.

## Why

release-please can merge a release PR, report the run as **success**, and still create **no tag** — e.g. a title-pattern/component mismatch (see the config gotchas in `references/release-please.md`; [googleapis/release-please#2214](https://github.com/googleapis/release-please/issues/2214)). The run is green, nothing is tagged, and a stuck `autorelease: pending` PR then aborts *all* future releases silently. Watching the merge by hand doesn't reliably catch a tag that fails to appear a minute later; a machine check does.

## 1. `verify-tag` — appended to `release-please.yml`

These steps go on the **same** `release-please` job (reusing its runner — no extra job/spin-up). They need `id: release` on the release-please-action step and a checkout for the local composite. The complete `release-please.yml` (with these steps folded in) is in `references/release-please.md`; the verify-specific steps are:

```yaml
# verify-tag — final goal of the whole release setup: a merged release PR MUST
# produce a tag. Catches two failure modes:
#   1. the release-please step failed outright (loud), and
#   2. a release PR merged, the step reported success, but NO tag was created
#      (the silent freeze — a title-pattern/component mismatch; see the config
#      section of release-please.md).
- name: Evaluate release outcome
  id: check
  if: always()
  env:
    RELEASE_OUTCOME: ${{ steps.release.outcome }}
    # Every output the action emitted, as JSON. Read the tags out of THIS, never
    # from steps.release.outputs.release_created / .tag_name — see the
    # namespaced-outputs trap below.
    OUTPUTS_JSON: ${{ toJSON(steps.release.outputs) }}
    # ⚠️ CORRECT ONLY WHILE THIS WORKFLOW'S SOLE TRIGGER IS `on: push`.
    # `github.event.head_commit` is null on any event that has no head commit
    # (workflow_dispatch, schedule, …). HEAD_MSG then reads empty,
    # is_release_merge stays false, and EVERY detection branch below becomes
    # unreachable dead code — a green run on the exact silent freeze this step
    # exists to catch. This has happened in practice: a repo added
    # `workflow_dispatch:` here as a manual re-fire and made the freeze detector
    # decorative in the same commit. If you add ANY non-push trigger, replace
    # this whole step with the drop-in below ("Adding workflow_dispatch").
    HEAD_MSG: ${{ github.event.head_commit.message }}
    REPO: ${{ github.repository }}
    GH_TOKEN: ${{ github.token }}
  run: |
    alert=false
    title=""
    detail=""
    # released=true ONLY when this run cut a tag AND the tag ref is confirmed on
    # the remote (the `-n "$tags"` clean branch below). The tagged-only deploy
    # step keys off this — a freeze/missing-ref case leaves it false, so an
    # untagged or phantom-tag commit is never shipped. See references/tagged-deploy.md.
    released=false
    head_line=$(printf '%s\n' "$HEAD_MSG" | head -n1)

    # Did this push merge a release PR? The release commit's subject is rendered
    # from the config's pull-request-title-pattern, so it is NOT always
    # "chore: release X.Y.Z" — see the component-in-title trap below.
    is_release_merge=false
    if printf '%s' "$head_line" | grep -Eq '^chore(\([^)]*\))?: release +([^ ]+ +)?v?[0-9]+\.[0-9]+\.[0-9]+'; then
      is_release_merge=true
    fi

    # Every tag this run cut, whether the output key is the root `tag_name` or a
    # namespaced `<path>--tag_name`. Covers single-package, non-root package, and
    # per-component monorepo tags (backend-v1.2.0) without knowing the config.
    tags=$(printf '%s' "$OUTPUTS_JSON" | jq -r 'to_entries[] | select(.key | endswith("tag_name")) | .value | select(. != null and . != "")')
    context="releases_created=$(printf '%s' "$OUTPUTS_JSON" | jq -r '.releases_created // "<empty>"'), paths_released=$(printf '%s' "$OUTPUTS_JSON" | jq -r '.paths_released // "<empty>"')"

    # Ground truth is the ref on the remote. Retried, so ref propagation lag right
    # after the tag is cut can't manufacture a false alarm.
    missing=""
    for tag in $tags; do
      found=false
      for attempt in 1 2 3; do
        if gh api "repos/${REPO}/git/ref/tags/${tag}" >/dev/null 2>&1; then
          found=true
          break
        fi
        if [ "$attempt" -lt 3 ]; then sleep 5; fi
      done
      if [ "$found" = "true" ]; then
        echo "OK: tag ${tag} exists."
      else
        missing="${missing} ${tag}"
      fi
    done

    if [ "$RELEASE_OUTCOME" = "failure" ]; then
      alert=true
      title="❌ ${REPO} — release-please step failed"
      detail="The release-please action failed. No release PR / tag / release was produced this run."
    elif [ "$is_release_merge" = "true" ] && [ -z "$tags" ]; then
      alert=true
      title="🟥 ${REPO} — release PR merged but NO TAG created"
      detail="Merged \`${head_line}\` but release-please reported no tag (${context}). This is the silent freeze — check the title-pattern/component config."
    elif [ -n "$missing" ]; then
      alert=true
      title="🟥 ${REPO} — release reported but tag missing"
      detail="release-please reported tag(s):${missing} but the ref does not exist on the remote (${context})."
    elif [ -n "$tags" ]; then
      echo "OK: tagged $(printf '%s' "$tags" | tr '\n' ' ') (${context})."
      released=true
    else
      echo "OK: no release expected this run (feature push or PR-only update)."
    fi

    {
      echo "alert=$alert"
      echo "title=$title"
      echo "released=$released"
      echo "detail<<EOF"
      echo "$detail"
      echo "EOF"
    } >> "$GITHUB_OUTPUT"

- name: Alert on failure
  if: ${{ always() && steps.check.outputs.alert == 'true' }}
  uses: ./.github/actions/discord-alert
  with:
    webhook: ${{ secrets.<ALERT_WEBHOOK_SECRET> }}
    title: ${{ steps.check.outputs.title }}
    description: |
      ${{ steps.check.outputs.detail }}

      **Commit:** [`${{ github.sha }}`](${{ github.server_url }}/${{ github.repository }}/commit/${{ github.sha }})
      **Repo:** ${{ github.server_url }}/${{ github.repository }}
      [View run](${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}) · [Release PRs](${{ github.server_url }}/${{ github.repository }}/pulls?q=is%3Apr+label%3A%22autorelease%3A+pending%22)

- name: Fail the run if a release was expected but missing
  if: ${{ always() && steps.check.outputs.alert == 'true' }}
  run: |
    echo "::error::release verification failed — see the alert"
    exit 1
```

Add `concurrency: { group: release-please, cancel-in-progress: false }` to `release-please.yml` too, so overlapping release runs serialize.

### ⚠️ Never read `steps.release.outputs.release_created` / `.tag_name` directly

Those unprefixed outputs exist **only when the manifest package sits at the repo root** (`"packages": { ".": … }`). `setPathOutput()` in release-please-action namespaces every per-package output for any other path:

```ts
if (path === '.') core.setOutput(key, value); // tag_name
else core.setOutput(`${path}--${key}`, value); // apps/web--tag_name
```

So in a repo whose package is `apps/web`, or any per-component monorepo (`backend`, `frontend` — both configs this skill scaffolds), both keys read back **empty** and a check built on them alerts "NO TAG created" on every single healthy release, forever. That is not hypothetical: it fired on a real 0.26.0 release that had tagged correctly, seconds after the tag was published in the same run.

Only `releases_created` (**plural**) and `paths_released` are top-level regardless of path, and neither carries a tag name — they're context in the alert body, not the signal. Hence `toJSON(steps.release.outputs)` + `endswith("tag_name")`: it finds the tag under whatever key the config produced, and the ref lookup on the remote is what actually decides pass/fail.

Related: `✔ No commits for path: <pkg>, skipping` in a release-merge run is **not** a failure signal — that's the *next* release PR having nothing to include, which is correct right after a release. Don't add an alert for it.

### ⚠️ The release-merge regex must tolerate a component in the title

`is_release_merge` is what arms the **silent-freeze** branch — the single most important check here. It matches the head commit's subject, and that subject is rendered from the config's `pull-request-title-pattern`, **not** fixed. A pattern carrying `${component}` produces a subject with the component name between "release" and the version:

```
chore(main): release  ingest-worker 0.7.0    # two spaces: ${component} renders with a leading space
chore(main): release 1.5.2                   # no component
```

A version-only pattern (`: release [0-9]`) silently fails to match the first form. `is_release_merge` stays `false`, the "merged but NO TAG created" branch becomes unreachable, and the repo gets a verification block that looks installed and cannot ever fire — the exact failure this whole file exists to prevent, reintroduced one level down. Note that this is **independent** of the namespaced-outputs trap above, and hits the same repos: a non-root package path is usually accompanied by `${component}` in the title pattern.

Hence the optional component group and the full `X.Y.Z` anchor:

```
^chore(\([^)]*\))?: release +([^ ]+ +)?v?[0-9]+\.[0-9]+\.[0-9]+
```

Requiring all three version parts is what keeps the optional group from swallowing ordinary commits — `chore: release notes cleanup` must not match. Verified against real release commits in both shapes, plus non-release subjects.

### ⚠️ This step is correct **only** while the workflow's sole trigger is `push`

`github.event.head_commit` is populated on `push` and on nothing else. Add `workflow_dispatch:` (or `schedule:`, or any other event) to `release-please.yml` and, on those runs, `head_commit` is **null** — so `HEAD_MSG` is empty, `head_line` is empty, `is_release_merge` stays `false`, and the `is_release_merge && -z tags` branch becomes **unreachable dead code**. The run is green. The silent freeze it exists to catch goes unreported.

This is not hypothetical. A repo added `workflow_dispatch:` to this exact workflow as a **manual re-fire** — the sane, obviously-correct thing to want, since a transient release-please failure otherwise has no recovery path but `gh run rerun`. The trigger shipped; the freeze detector became decorative in the same commit; nothing failed, so nothing surfaced it.

The bug and the reason for it are one edit apart, and the reason lives here rather than in `release-please.yml`, which is why the trigger looks free to add. If you add any non-push trigger, replace the whole `Evaluate release outcome` step with the version below.

### Adding `workflow_dispatch` — the drop-in replacement steps

> ### 🛑 Prerequisite: not on a workflow that carries the deploy step
>
> `references/tagged-deploy.md`'s `Deploy tagged release` step is gated on this file's `released` output and deploys **`github.sha`**. On a `workflow_dispatch` run `github.sha` is the tip of the **dispatched ref** — `develop` in a gitflow repo, since a dispatch defaults to the repo's default branch — while `target-branch: main` means release-please still tags `main`. And `released=true` **is** reachable on a dispatch: re-firing a stuck release is the whole point of the trigger, and that re-fire can cut and confirm the tag.
>
> So on a repo that has both, adding `workflow_dispatch:` means: dispatch → tag `v1.2.4` cut on `main` → `released=true` → **the deploy hook ships `develop`'s tip to production**, on a green run.
>
> The `commit_sha` output below does **not** fix this — it resolves main's tip only on the frozen path, and a tag-cutting dispatch doesn't take that path. Deploy-safe dispatch needs its own main-resolved sha for the deploy step, which is not scaffolded here.
>
> **Therefore:** add `workflow_dispatch` only to a `release-please.yml` with **no** deploy step (`vars.RENDER_DEPLOY=false` is *not* sufficient — it can be flipped on later from the settings UI with no file change). If the repo deploys, recover a stuck release with `gh run rerun <database-id>` instead, which replays the original `push` event and keeps `head_commit` populated.

This replaces `Evaluate release outcome` **and** `Alert on failure` — both are in the fence below, so copy it whole rather than hand-assembling from a diff. Three earlier attempts at this fallback each shipped a *different* defect, and every one of them was a green run on a frozen release:

1. **Read main's tip commit and use its subject.** Inverts the detector. After every healthy release, main's tip *is* the release commit, so it matches the `is_release_merge` pattern — every dispatch against a resting, healthy repo hits the `is_release_merge && -z tags` branch and fires the loudest alert in this file. It cries wolf on the most likely dispatch there is.
2. **Query the freeze signature, then re-derive the verdict from main's tip message.** Turns the false positive into a false *negative*, deterministically. `references/develop-to-main-pr.md` mandates a **merge commit** for the promotion PR, so once any promotion lands after a freeze, main's tip subject is `Merge pull request #N from <owner>/develop` and matches neither signal. The one dispatch meant to unstick a frozen release reports green.
3. **`::warning::` on a failed lookup.** Neither fails the run nor reaches Discord. On the one run whose job is detecting a freeze, "we could not tell" becomes indistinguishable from "nothing is wrong".

What the version below does instead:

- **Gates on the freeze signature, not on a commit message.** A **merged** release PR still labelled `autorelease: pending` is proof: release-please relabels to `autorelease: tagged` within seconds of a successful tag, so merged+pending means the tag never happened. (Open+pending is the *normal* state of an unmerged release PR — the `--state merged` filter is what keeps this from matching it.) This is the same query `release-health.yml`'s `pending-sweep` job already runs.
- **Sets a separate `frozen=true` from that query alone, and ORs it into the alert condition.** The signature *is* the verdict. A dispatch that **proved** a freeze must never report green because a cosmetic follow-up call blipped.
- **Names the stuck PR in the alert body, always.** main's tip commit is read only for readable context and is labelled as such — on the frozen path it is very often *not* the commit that merged the release PR (a later promotion merge, or an unrelated fix), so quoting it as the headline claim misattributes the freeze. The PR number is the evidence; the subject is colour.
- **Reads main's sha and subject in one `gh api` call.** Two calls let the sha half fail silently — `|| echo ""` then falls back to the dispatched ref's tip, reproducing the exact mislink `commit_sha` exists to prevent — and admit a race where main advances between them, pairing a subject with a different sha.
- **Retries the lookup 3× and *alerts* on total failure**, in its own branch placed **below** the tag branches — if this run cut and verified a tag, the outcome is known and a failed freeze lookup is moot. The `::error::` annotation is emitted **in that branch**, not at the lookup, so a run that ends healthy doesn't carry a red annotation.
- **Sends the lookup's stderr to a file, never `2>&1` into the value.** `gh` writes advisory bytes to stderr on *successful* calls; folded into the capture, they make `stuck_pr` non-empty on a healthy repo, which reads main's tip, matches the release commit, and fires exactly the false alarm this gate exists to remove.
- **Uses a random `GITHUB_OUTPUT` heredoc delimiter.** `lookup_err` is arbitrary third-party text going into a multi-line output; a literal `EOF` line in it would terminate the value early and let the rest parse as outputs — `released=true` / `alert=false` injected past a blind run. The base step doesn't need this (`head_line` is `head -n1`, so it cannot contain a newline); this one does.
- **Emits `commit_sha`** so the alert links the commit the verdict was read from rather than the dispatched ref's tip. See the prerequisite above for why this is *not* enough to make a deploying workflow dispatch-safe.

```yaml
- name: Evaluate release outcome
  id: check
  if: always()
  env:
    RELEASE_OUTCOME: ${{ steps.release.outcome }}
    OUTPUTS_JSON: ${{ toJSON(steps.release.outputs) }}
    # May be empty — this workflow has a non-push trigger. Everything the
    # `if [ -z "$HEAD_MSG" ]` block below does exists to cover that case.
    HEAD_MSG: ${{ github.event.head_commit.message }}
    REPO: ${{ github.repository }}
    GH_TOKEN: ${{ github.token }}
  run: |
    alert=false
    title=""
    detail=""
    released=false
    # frozen — set ONLY from the definitive freeze signature (a MERGED release
    # PR still labelled `autorelease: pending`). Kept separate from
    # is_release_merge because it is PROOF, not an inference from a commit
    # subject, and the alert branch below must not be able to lose it just
    # because the commit message it also wanted was unreadable.
    frozen=false
    # Appended to the freeze alert body. The PR number is the evidence; main's
    # tip subject quoted alongside it is only context, and on this path is
    # frequently NOT the commit that merged the release PR.
    frozen_note=""
    # Set when we could not establish whether a release is frozen. NOT the same
    # as "nothing is frozen" — it alerts, in its own branch below.
    lookup_failed=false
    lookup_err=""
    # The commit the verdict was actually read from. github.sha is wrong for
    # this on workflow_dispatch: it is the tip of the DISPATCHED ref, and a
    # gitflow repo's default branch is develop, so the alert would quote main's
    # release subject while linking an unrelated develop commit.
    main_sha=""

    # No head_commit on this event (workflow_dispatch/schedule). Establish the
    # verdict from the freeze SIGNATURE, and use main's tip only for wording.
    # Do NOT adopt main's tip as the signal: after every healthy release main's
    # tip IS the release commit and matches is_release_merge below, so every
    # dispatch against a resting repo would fire the loudest alert here.
    if [ -z "$HEAD_MSG" ]; then
      stuck_pr=""
      err_file="${RUNNER_TEMP:-/tmp}/release-pr-lookup.err"
      lookup_ok=false
      # `gh pr list` is GraphQL, which references/tagged-deploy.md's auto-merge
      # step deliberately avoids. That rule is exempted here, not forgotten: it
      # exists because GraphQL quota is per-USER and so can be drained by an
      # unrelated local `gh` session on the same account — which only bites the
      # PAT-authenticated calls. This step runs as GITHUB_TOKEN, whose budget is
      # per-REPO. release-health.yml's pending-sweep queries the same way.
      for attempt in 1 2 3; do
        # stderr to a FILE, never 2>&1 into the value: a successful gh call can
        # still write advisory bytes, which would make stuck_pr non-empty on a
        # healthy repo and fire a false freeze alarm.
        if stuck_pr=$(gh pr list --repo "$REPO" --state merged \
          --label "autorelease: pending" --limit 1 --json number \
          --jq '.[0].number // ""' 2>"$err_file"); then
          lookup_ok=true
          break
        fi
        lookup_err=$(cat "$err_file")
        stuck_pr=""
        echo "  merged release PR lookup FAILED (attempt ${attempt}/3): ${lookup_err}"
        if [ "$attempt" -lt 3 ]; then sleep 5; fi
      done

      if [ "$lookup_ok" != "true" ]; then
        # No ::error:: here — the branch ordering below may still resolve this
        # run as healthy (a tag was cut and verified), and a red annotation on a
        # green run trains people to ignore annotations. It is emitted in the
        # lookup_failed alert branch instead.
        lookup_failed=true
      elif [ -n "$stuck_pr" ]; then
        # The signature alone is the verdict. Everything after this point is
        # cosmetic — it cannot unset `frozen`.
        frozen=true
        frozen_note=$(printf '\n\n%s' "Freeze signature: merged release PR #${stuck_pr} is still labelled \`autorelease: pending\`. Any commit subject quoted above is main's tip, shown as context only — on this path it is often not the commit that merged the release PR.")
        echo "No head_commit on this event; merged release PR #${stuck_pr} is still 'autorelease: pending' — the release IS frozen."
        # ONE call for both fields. Two calls let the sha half fail silently and
        # fall back to the dispatched ref's tip — the exact mislink commit_sha
        # exists to prevent — and let main advance between them.
        if main_tip=$(gh api "repos/${REPO}/commits/main" --jq '.sha + "\t" + .commit.message' 2>/dev/null); then
          main_sha=${main_tip%%$'\t'*}
          HEAD_MSG=${main_tip#*$'\t'}
        else
          echo "::warning::Could not read main's tip commit; the alert will name the PR only."
          HEAD_MSG="merged release PR #${stuck_pr} (main's tip commit was unreadable)"
        fi
      else
        echo "No head_commit on this event, and no merged release PR is stuck at 'autorelease: pending' — nothing is frozen."
      fi
    fi
    head_line=$(printf '%s\n' "$HEAD_MSG" | head -n1)

    # Unchanged from the push-only version — see the component-in-title trap above.
    is_release_merge=false
    if printf '%s' "$head_line" | grep -Eq '^chore(\([^)]*\))?: release +([^ ]+ +)?v?[0-9]+\.[0-9]+\.[0-9]+'; then
      is_release_merge=true
    fi

    tags=$(printf '%s' "$OUTPUTS_JSON" | jq -r 'to_entries[] | select(.key | endswith("tag_name")) | .value | select(. != null and . != "")')
    context="releases_created=$(printf '%s' "$OUTPUTS_JSON" | jq -r '.releases_created // "<empty>"'), paths_released=$(printf '%s' "$OUTPUTS_JSON" | jq -r '.paths_released // "<empty>"')"

    missing=""
    for tag in $tags; do
      found=false
      for attempt in 1 2 3; do
        if gh api "repos/${REPO}/git/ref/tags/${tag}" >/dev/null 2>&1; then
          found=true
          break
        fi
        if [ "$attempt" -lt 3 ]; then sleep 5; fi
      done
      if [ "$found" = "true" ]; then
        echo "OK: tag ${tag} exists."
      else
        missing="${missing} ${tag}"
      fi
    done

    if [ "$RELEASE_OUTCOME" = "failure" ]; then
      alert=true
      title="❌ ${REPO} — release-please step failed"
      detail="The release-please action failed. No release PR / tag / release was produced this run."
    elif { [ "$is_release_merge" = "true" ] || [ "$frozen" = "true" ]; } && [ -z "$tags" ]; then
      # `frozen` is ORed in, not folded into is_release_merge: the proof must
      # reach this branch even when the commit subject is unreadable or is a
      # promotion merge commit that matches no pattern.
      alert=true
      title="🟥 ${REPO} — release PR merged but NO TAG created"
      detail="Merged \`${head_line}\` but release-please reported no tag (${context}). This is the silent freeze — check the title-pattern/component config.${frozen_note}"
    elif [ -n "$missing" ]; then
      alert=true
      title="🟥 ${REPO} — release reported but tag missing"
      detail="release-please reported tag(s):${missing} but the ref does not exist on the remote (${context})."
    elif [ -n "$tags" ]; then
      echo "OK: tagged $(printf '%s' "$tags" | tr '\n' ' ') (${context})."
      released=true
    elif [ "$lookup_failed" = "true" ]; then
      # Deliberately BELOW the tag branches: if this run cut and verified a tag,
      # the outcome is known and a failed freeze lookup is moot.
      echo "::error::Could not list merged release PRs after 3 attempts; freeze detection was blind this run."
      alert=true
      title="🟧 ${REPO} — could not determine whether a release is frozen"
      # Built with printf, not a multi-line string literal: a literal's
      # continuation lines carry this block's YAML indentation into the value,
      # which indents the code fence and stops it rendering in the alert.
      detail=$(printf '%s\n%s\n%s\n%s' \
        "This run had no head_commit (a manual dispatch), and listing merged \`autorelease: pending\` PRs failed on all 3 attempts — so freeze detection was blind. Nothing is known to be broken, but nothing is confirmed healthy either. Re-run, or check the release PRs by hand." \
        '```' "$lookup_err" '```')
    else
      echo "OK: no release expected this run (feature push or PR-only update)."
    fi

    # Random heredoc delimiter: `detail` can carry arbitrary third-party text
    # (gh's stderr). A literal `EOF` line inside it would close the value early
    # and let the remainder parse as outputs — an attacker-free but very real
    # way to inject `alert=false` / `released=true` past a blind run.
    delim="EOF_$(openssl rand -hex 8)"
    {
      echo "alert=$alert"
      echo "title=$title"
      echo "released=$released"
      echo "commit_sha=${main_sha:-$GITHUB_SHA}"
      echo "detail<<${delim}"
      echo "$detail"
      echo "${delim}"
    } >> "$GITHUB_OUTPUT"

- name: Alert on failure
  if: ${{ always() && steps.check.outputs.alert == 'true' }}
  uses: ./.github/actions/discord-alert
  with:
    webhook: ${{ secrets.<ALERT_WEBHOOK_SECRET> }}
    title: ${{ steps.check.outputs.title }}
    description: |
      ${{ steps.check.outputs.detail }}

      **Commit:** [`${{ steps.check.outputs.commit_sha }}`](${{ github.server_url }}/${{ github.repository }}/commit/${{ steps.check.outputs.commit_sha }})
      **Repo:** ${{ github.server_url }}/${{ github.repository }}
      [View run](${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}) · [Release PRs](${{ github.server_url }}/${{ github.repository }}/pulls?q=is%3Apr+label%3A%22autorelease%3A+pending%22)
```

`Fail the run if a release was expected but missing` is unchanged — it already keys off `steps.check.outputs.alert`.

## 2. `.github/workflows/release-health.yml`

```yaml
name: release-health

# Two jobs:
#  - self-test: on-demand, fires ONE sample alert to prove the pipe.
#  - pending-sweep: daily, flags any MERGED release PR stuck on
#    "autorelease: pending" (the deadlock that aborts all future releases).

on:
  schedule:
    - cron: "<CRON_MINUTE> 8 * * *" # 08:<CRON_MINUTE> UTC daily — off-peak hour, staggered minute
  workflow_dispatch:
    inputs:
      test_alert:
        description: "Fire a test alert and exit"
        type: boolean
        default: false

permissions:
  contents: read
  pull-requests: read

jobs:
  self-test:
    if: ${{ github.event_name == 'workflow_dispatch' && inputs.test_alert }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Send test alert
        uses: ./.github/actions/discord-alert
        with:
          webhook: ${{ secrets.<ALERT_WEBHOOK_SECRET> }}
          color: "3066993" # green — this is a test, not a real failure
          title: "✅ ${{ github.repository }} — <ALERT_CHANNEL_LABEL> pipe test"
          description: |
            Test alert from `release-health.yml`. If you can read this in **<ALERT_CHANNEL>**, delivery works.
            [View run](${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }})

      # Second channel, included ONLY when this repo also scaffolds the
      # main→develop back-merge (which alerts a different channel — see
      # references/main-to-develop-backmerge.md). Its real alert fires only on a
      # merge conflict, which cannot be manufactured on demand, so without this
      # step that webhook is the one credential in the whole setup with no way
      # to prove it works until the day it's needed. No `if:` guard is needed:
      # the composite no-ops with a warning when the secret is unset.
      - name: Send test alert — PR alerts channel
        uses: ./.github/actions/discord-alert
        with:
          webhook: ${{ secrets.<PR_ALERT_WEBHOOK_SECRET> }}
          color: "3066993"
          title: "✅ ${{ github.repository }} — <PR_ALERT_CHANNEL_LABEL> pipe test"
          description: |
            Test alert from `release-health.yml`. If you can read this in **<PR_ALERT_CHANNEL>**, delivery works.
            [View run](${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }})

  pending-sweep:
    if: ${{ github.event_name == 'schedule' || !inputs.test_alert }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: "Find stuck 'autorelease: pending' PRs"
        id: sweep
        env:
          GH_TOKEN: ${{ github.token }}
          REPO: ${{ github.repository }}
        run: |
          # The freeze signal is a MERGED release PR still labelled pending: the
          # label flips to "autorelease: tagged" within seconds of a healthy
          # merge, so a merged+pending PR means the tag never happened. (Open +
          # pending is the NORMAL state of an un-merged release PR — never flag those.)
          stuck=$(gh pr list -R "$REPO" --state merged --label "autorelease: pending" \
            --json number,title,url,mergedAt \
            --jq '[.[] | "• [#\(.number) \(.title)](\(.url)) — merged \(.mergedAt)"] | join("\n")')
          if [ -n "$stuck" ]; then
            echo "$stuck"
            {
              echo "alert=true"
              echo "detail<<EOF"
              echo "$stuck"
              echo "EOF"
            } >> "$GITHUB_OUTPUT"
          else
            echo "alert=false" >> "$GITHUB_OUTPUT"
            echo "no stuck pending release PRs."
          fi
      - name: Alert on failure
        if: steps.sweep.outputs.alert == 'true'
        uses: ./.github/actions/discord-alert
        with:
          webhook: ${{ secrets.<ALERT_WEBHOOK_SECRET> }}
          title: "🟥 ${{ github.repository }} — release PR stuck on autorelease: pending"
          description: |
            A **merged** release PR never got tagged, so it is stuck `pending`. **This aborts all future releases until cleared.**

            ${{ steps.sweep.outputs.detail }}

            Fix: relabel to `autorelease: tagged` + re-run, or tag by hand.
            **Repo:** ${{ github.server_url }}/${{ github.repository }}

      # A stuck release PR blocks EVERY future release, so the run must go red.
      # This is the fallback notification path: GitHub emails on a failed run by
      # default, so the finding reaches someone even with no webhook configured.
      # Without it the sweep found the problem and exited 0 — a green checkmark
      # on a frozen release pipeline, which is the exact failure this job exists
      # to catch.
      - name: Fail the run if a release PR is stuck
        if: steps.sweep.outputs.alert == 'true'
        run: |
          echo "::error::a merged release PR is stuck on 'autorelease: pending' — all future releases are blocked until it is cleared. See this run's summary."
          exit 1
```

## 3. `.github/actions/discord-alert/action.yml`

```yaml
name: discord-alert
description: Record an alert on the run summary, and push it to Discord when a webhook is configured.

inputs:
  webhook:
    description: Discord webhook URL — pass the repo's alert webhook secret (default DISCORD_GH_ERRORS_WEBHOOK)
    required: true
  title:
    description: Embed title
    required: true
  description:
    description: Embed description (Discord markdown)
    required: true
  color:
    description: Embed sidebar color (decimal). Default red.
    required: false
    default: "15158332"

runs:
  using: composite
  steps:
    - shell: bash
      env:
        WEBHOOK: ${{ inputs.webhook }}
        TITLE: ${{ inputs.title }}
        DESC: ${{ inputs.description }}
        COLOR: ${{ inputs.color }}
      run: |
        # Record the alert on the run itself FIRST, before any webhook call and
        # regardless of whether one is configured. The webhook is a PUSH channel,
        # not the system of record: a repo with no webhook — or one whose webhook
        # was revoked — must still be able to find out what happened, from the
        # run page, with no external service involved.
        if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
          {
            echo "### ${TITLE}"
            echo
            echo "${DESC}"
            echo
          } >> "$GITHUB_STEP_SUMMARY"
        fi

        if [ -z "$WEBHOOK" ]; then
          echo "::warning::${TITLE} — no alert webhook configured, so this was not sent to Discord. Full detail is in this run's summary."
          exit 0
        fi
        payload=$(jq -n --arg t "$TITLE" --arg d "$DESC" --argjson c "${COLOR:-15158332}" \
          '{embeds:[{title:$t, description:$d, color:$c}]}')
        code=$(curl -sS -o /dev/null -w '%{http_code}' -X POST \
          -H 'Content-Type: application/json' "$WEBHOOK" -d "$payload")
        echo "discord webhook responded: $code"
        case "$code" in
          2*) echo "alert delivered" ;;
          *)  echo "::error::discord webhook failed (HTTP $code)"; exit 1 ;;
        esac
```

## The webhook secret (optional — alerts no-op without it)

```bash
gh secret set <ALERT_WEBHOOK_SECRET> --repo <owner>/<repo>
```

Create the webhook on the channel the project's alerts should land in (Discord → Server Settings → Integrations → Webhooks → Copy Webhook URL) and paste it when prompted. The secret name is whatever was chosen above; the URL inside it is what selects the channel.

Unlike `RELEASE_PLEASE_TOKEN`, this is **not** required — the composite skips the Discord push (with a warning) when the secret is absent, so the release pipeline still functions. Say so in the summary rather than blocking on it.

### The fallback when there's no webhook — alerts must not depend on it

**A webhook must never be the only channel.** It's an external service reached over the network with a credential that can be unset, revoked, or pointed at a deleted channel — so making it the sole path puts a single point of failure in front of the machinery whose entire job is catching failures. The tiers, in the templates above:

| Tier | Configured | Where the alert surfaces |
| --- | --- | --- |
| 0 | nothing at all | `$GITHUB_STEP_SUMMARY` on the run page (full title + body) · `::warning::` / `::error::` annotation · **run goes red** → GitHub's own failure email |
| 1 | webhook secret | everything above, plus the Discord push |

Two rules that make tier 0 real, both of which were missing in the first version of these templates:

1. **Write `$GITHUB_STEP_SUMMARY` before the webhook call, unconditionally.** Not in the `else` branch. The summary is durable, renders as markdown on the run, needs no credential, and survives the webhook being wrong. Logging just the title on the no-webhook path (the original behaviour) throws away the part that says *what* is wrong.
2. **Any job whose finding is actionable must `exit 1`.** `pending-sweep` originally alerted and exited 0, so a stuck `autorelease: pending` PR — which blocks every future release — was found daily and discarded behind a green checkmark. A red run is the only notification that needs no setup whatsoever.

The corollary for the alert copy: the annotation should point at the summary rather than trying to cram the body into a single `::warning::` line, since annotations don't render multi-line markdown.

**But "optional" is exactly why it gets forgotten, and the failure mode is silence.** A repo with the workflows and no webhook looks identical to a healthy one: green runs, no alerts, and no alert is also what "nothing is wrong" looks like. Measured on one fleet, **only 1 of 13 repos** had the errors webhook set — every other repo had been no-opping its alerts since the day it was scaffolded, and nothing surfaced it. So:

- Put it in the **post-scaffold action list**, not just a summary line. Optional-but-forgotten is still broken.
- `ci-baseline-audit` check 10 catches this repo-wide after the fact — a workflow that references a secret the repo doesn't have. Scaffold-time is the cheap fix; the audit is the backstop.

### Prove it, don't assume it

Setting the secret is not evidence it works — a revoked webhook, a URL pasted from the wrong channel, or a truncated paste all store fine and fail silently later. GitHub secrets are write-only, so the only proof is delivery:

```bash
gh workflow run release-health.yml -R <owner>/<repo> --ref <default-branch> -f test_alert=true
```

Then confirm from the run log, **not** the run's conclusion — the job exits 0 either way, because a missing webhook is a deliberate no-op:

```bash
gh run view <run-id> -R <owner>/<repo> --log | grep -E 'alert delivered|skipping alert'
```

`alert delivered` only prints on a 2xx from Discord. `skipping alert` means the secret is empty. A green checkmark on its own tells you nothing.

## Activation timing (gitflow)

- `release-health.yml` runs on `schedule` / `workflow_dispatch`, which execute from the **default branch** — so it's live as soon as it lands on `develop`. Self-test it immediately: `gh workflow run release-health.yml -R <owner>/<repo> -f test_alert=true`.
- `verify-tag` lives in `release-please.yml` (`on: push: [main]`), so it **activates on the next develop→main promotion** and truly exercises on the next real release.

## Prettier note

The scaffolded `.prettierignore` (see `project-scaffold/references/configs/node-ts.md`) excludes `*.yml` / `*.yaml`, so prettier never touches workflow YAML and this is a non-issue for scaffolded repos. It only bites a repo that runs `prettier --check` over `.github` **without** that carve-out (`.github/**` isn't ignored by default) — there the emitted YAML must be prettier-clean or `format:check` fails on the scaffolding PR. These templates are formatted to prettier defaults (`printWidth: 100`, `tabWidth: 2`); if such a repo's `.prettierrc` differs, either add `*.yml`/`*.yaml` (or `.github/`) to its `.prettierignore` — the standard fix — or run `prettier --write` on the three emitted files before committing.

Separately, `CHANGELOG.md` and `.github/.release-please-manifest.json` must be in `.prettierignore` in every repo that runs `prettier --check .` — release-please rewrites both on every release PR and its output doesn't reliably satisfy prettier, so without the carve-out the release PR itself fails `format:check` and auto-merge freezes the release (see `release-please.md`, "Manifest — match current version").
