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
    # EMPTY on any event that carries no head_commit — a manual dispatch, a
    # branch deletion. The freeze-proof block below is what covers that.
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
    # frozen — set ONLY from the definitive freeze signature (a MERGED release PR
    # still labelled `autorelease: pending`). Kept separate from is_release_merge
    # because it is PROOF, not an inference from a commit subject, and the alert
    # branch below must not be able to lose it just because the commit message it
    # also wanted was unreadable.
    frozen=false
    # Set when we could not establish whether a release is frozen. That is NOT
    # the same as "nothing is frozen" — it alerts, see the branch below.
    lookup_failed=false
    lookup_err=""
    # The release branch's SHA, resolved ONLY on the frozen path below — the one
    # path whose verdict is read from that branch. github.sha is wrong there: on
    # a workflow_dispatch it is the tip of the DISPATCHED ref, and gitflow-init
    # makes `develop` the default branch, so the alert would quote main's release
    # subject while linking an unrelated develop commit.
    main_sha=""
    # The merged, still-pending release PR — the freeze proof itself. Named in
    # the alert, because it is the only actionable fact in it.
    stuck_pr=""
    # The commit the WINNING branch read its verdict from. Assigned only by the
    # branch that actually read main (the frozen one); every other branch leaves
    # it empty and the run's own SHA is emitted instead. main_sha alone would
    # leak into e.g. the tag-missing branch, whose verdict came from tag refs.
    verdict_sha=""
    # An event with no head_commit leaves HEAD_MSG empty, which would make the
    # silent-freeze branch below (release merged, no tag) unreachable — a green
    # run on the exact failure a manual re-fire exists to diagnose.
    #
    # The fix is NOT to read main's tip and adopt it as the head commit. main's
    # tip is a STATE, not an event: after every HEALTHY release main's tip IS the
    # release commit and matches the release-title pattern below, so adopting it
    # unconditionally sets is_release_merge on every dispatch against a resting,
    # healthy repo and fires the loudest alert in this file ("release PR merged
    # but NO TAG created") on the healthiest possible state.
    #
    # So the verdict comes from the freeze PROOF instead: a MERGED release PR
    # still carrying `autorelease: pending`. release-please relabels that to
    # `autorelease: tagged` the moment tagging succeeds, so a merged+pending PR
    # means the tag never happened. Same query release-health.yml sweeps with.
    # (Open+pending is the NORMAL state of an unmerged release PR — the
    # `--state merged` filter is what keeps this from matching it.)
    #
    # A non-empty result is SUFFICIENT on its own, so it sets `frozen` directly,
    # and main's tip is then read ONLY for a human-readable subject in the alert.
    # If that read fails the verdict still stands: a dispatch that PROVED a
    # freeze must never report green because a cosmetic follow-up call blipped.
    #
    # Keeping the proof separate is load-bearing for a second, deterministic
    # reason: the promotion PR lands on main as a MERGE COMMIT (see
    # references/develop-to-main-pr.md), so once any promotion lands after the
    # freeze, main's tip subject is "Merge pull request #N from <owner>/develop"
    # — which matches neither the release-title pattern below nor a release
    # branch. Deriving the verdict from that message alone would report green on
    # the exact dispatch meant to unstick the release.
    #
    # Retried 3x like every other lookup here, and a lookup that fails all three
    # ALERTS rather than warning: `::warning::` neither fails the run nor reaches
    # Discord, so on the one run whose whole job is freeze detection, "we could
    # not tell" would be indistinguishable from "nothing is wrong".
    #
    # stderr goes to a FILE, never into the value: `2>&1` here would let any
    # advisory byte gh writes on an otherwise-successful call make `stuck_pr`
    # non-empty on a healthy repo, which then reads main's tip, matches the
    # release commit, and fires the very false alarm this gate exists to remove.
    #
    # `gh pr list` is GraphQL, and the auto-merge step in
    # references/tagged-deploy.md deliberately uses REST instead — that rule is
    # exempted here, not forgotten. It exists because GraphQL quota is per-USER,
    # which only bites the PAT-authenticated calls; this step runs as
    # GITHUB_TOKEN, whose budget is per-REPO. release-health.yml queries the same way.
    if [ -z "$HEAD_MSG" ]; then
      err_file="${RUNNER_TEMP:-/tmp}/release-pr-lookup.err"
      lookup_ok=false
      for attempt in 1 2 3; do
        if stuck_pr=$(gh pr list --repo "$REPO" --state merged \
          --label "autorelease: pending" --limit 1 --json number \
          --jq '.[0].number // ""' 2>"$err_file"); then
          lookup_ok=true
          break
        fi
        # Truncated: this reaches Discord as an embed description, which Discord
        # caps at 4096 chars and rejects with HTTP 400 beyond it — a long gh
        # error would kill the alert on the one run that needed it.
        lookup_err=$(head -n 5 "$err_file" | cut -c1-400)
        stuck_pr=""
        echo "  merged release PR lookup FAILED (attempt ${attempt}/3): ${lookup_err}"
        if [ "$attempt" -lt 3 ]; then sleep 5; fi
      done

      if [ "$lookup_ok" != "true" ]; then
        lookup_failed=true
        # Logged plainly here; the ::error:: annotation is emitted from the
        # branch below, so a run that went on to cut and verify a tag — where a
        # blind freeze lookup is moot — does not carry a red annotation on an
        # otherwise perfect release.
        echo "Could not list merged release PRs after 3 attempts; freeze detection is blind this run."
      elif [ -n "$stuck_pr" ]; then
        frozen=true
        echo "No head_commit on this event; merged release PR #${stuck_pr} is still 'autorelease: pending' — the release IS frozen."
        # Cosmetic only — the verdict is already decided. ONE call reads both
        # fields: two calls can straddle a push to main and pair the subject of
        # commit N with the sha of N+1, and a second call that fails on its own
        # would silently drop main_sha, sending the alert back to $GITHUB_SHA —
        # the dispatched-ref mislink this exists to prevent. Retried like every
        # other lookup here, and stderr goes to a file so a failure is
        # diagnosable from the log.
        main_err="${RUNNER_TEMP:-/tmp}/release-main-tip.err"
        main_tsv=""
        for attempt in 1 2 3; do
          if main_tsv=$(gh api "repos/${REPO}/commits/main" \
            --jq '[.sha, (.commit.message | split("\n")[0])] | @tsv' 2>"$main_err"); then
            break
          fi
          main_tsv=""
          echo "  main tip read FAILED (attempt ${attempt}/3): $(cat "$main_err")"
          if [ "$attempt" -lt 3 ]; then sleep 5; fi
        done
        if [ -n "$main_tsv" ]; then
          main_sha=$(printf '%s' "$main_tsv" | cut -f1)
          HEAD_MSG=$(printf '%s' "$main_tsv" | cut -f2)
        else
          echo "::warning::Could not read main's tip commit after 3 attempts ($(cat "$main_err")); the alert names the release PR instead of the commit subject."
          HEAD_MSG="(main's tip commit was unreadable)"
        fi
      else
        echo "No head_commit on this event, and no merged release PR is stuck at 'autorelease: pending' — nothing is frozen."
      fi
    fi

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
    elif { [ "$is_release_merge" = "true" ] || [ "$frozen" = "true" ]; } && [ -z "$tags" ]; then
      alert=true
      title="🟥 ${REPO} — release PR merged but NO TAG created"
      if [ "$frozen" = "true" ]; then
        # The proof, not the commit subject. head_line here is main's TIP, which
        # after any later promotion is "Merge pull request #N from <owner>/develop"
        # — naming it would point at a commit that is not a release merge and
        # send the reader to a config that is fine.
        verdict_sha="$main_sha"
        detail="Merged release PR [#${stuck_pr}](${GITHUB_SERVER_URL}/${REPO}/pull/${stuck_pr}) is still labelled \`autorelease: pending\`, so it was never tagged — every future release is blocked until it is cleared (${context}). main's tip is currently \`${head_line}\`. Check the title-pattern/component config, then clear #${stuck_pr} once the tag exists."
      else
        detail="Merged \`${head_line}\` but release-please reported no tag (${context}). This is the silent freeze — check the title-pattern/component config."
      fi
    elif [ -n "$missing" ]; then
      alert=true
      title="🟥 ${REPO} — release reported but tag missing"
      detail="release-please reported tag(s):${missing} but the ref does not exist on the remote (${context})."
    elif [ -n "$tags" ]; then
      echo "OK: tagged $(printf '%s' "$tags" | tr '\n' ' ') (${context})."
      released=true
    elif [ "$lookup_failed" = "true" ]; then
      # Deliberately BELOW the tag branches: if this run cut and verified a tag,
      # the outcome is known and a failed freeze lookup is moot — which is also
      # why the ::error:: annotation is raised here and not at the lookup itself.
      alert=true
      echo "::error::Could not determine whether a release is frozen; freeze detection was blind this run."
      title="🟧 ${REPO} — could not determine whether a release is frozen"
      detail="This run had no head_commit (a manual dispatch), and listing merged \`autorelease: pending\` PRs failed on all 3 attempts — so freeze detection was blind. Nothing is known to be broken, but nothing is confirmed healthy either. Re-run, or check the release PRs by hand.
    \`\`\`
    ${lookup_err}
    \`\`\`"
    else
      echo "OK: no release expected this run (feature push or PR-only update)."
    fi

    # Randomised delimiter: `detail` can carry gh stderr, and a line in it equal
    # to the delimiter would truncate the value and spill the rest as unparsable
    # output lines — failing the step AFTER the verdict was computed, so the
    # alert never sends.
    delim="EOF_$(date +%s)_${RANDOM}"
    {
      echo "alert=$alert"
      echo "title=$title"
      echo "released=$released"
      # The commit the winning branch read its verdict from, falling back to this
      # run's own SHA. On a dispatch that fallback is the tip of the DISPATCHED
      # ref, which is exactly why the frozen branch sets verdict_sha to main's
      # SHA rather than relying on it.
      echo "commit_sha=${verdict_sha:-$GITHUB_SHA}"
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

### ⚠️ An event with no `head_commit` must not be judged by main's tip

`is_release_merge` reads `github.event.head_commit.message`, and **not every event has one**. A `workflow_dispatch` carries no `head_commit` at all, so `HEAD_MSG` is empty, `is_release_merge` stays `false`, and the silent-freeze branch — the whole point of this file — is unreachable. The run then reports green on precisely the failure a manual re-fire exists to diagnose. The scaffolded trigger here is `push: branches: [main]` only, so the fallback is dormant on a fresh repo; it becomes load-bearing the moment a repo adds `workflow_dispatch` for manual re-fires, which is the standard recovery path when a release-please run dies transiently.

The tempting fix — read the release branch's tip and use its subject as the head commit — is **worse than the gap**. main's tip is a *state*, not an event: after every healthy release main's tip **is** the release commit and matches the release-title pattern, so adopting it unconditionally sets `is_release_merge` on every dispatch against a resting, healthy repo and fires the loudest alert in this file on the healthiest possible state. It also fails the other way: once any promotion merge lands after a freeze, main's tip subject is `Merge pull request #N from <owner>/develop` (the promotion PR is required to land as a merge commit — see `references/develop-to-main-pr.md`), which matches no release pattern, so a dispatch meant to unstick a frozen release reports green.

So the verdict comes from the **freeze proof**, not from a commit subject: a **merged** release PR still labelled `autorelease: pending`. release-please flips that label to `autorelease: tagged` within seconds of a successful tag, so merged + pending means the tag never happened — the same evidence `release-health.yml` fires a 🟥 alert and `exit 1` on. Five things make that gate trustworthy:

1. **`frozen` is its own variable**, ORed into the alert branch. It is proof, not an inference, and must not be lost because a *cosmetic* follow-up call (reading main's tip for a readable subject) failed.
2. **One `gh api` call reads both the SHA and the subject** (`--jq '[.sha, (.commit.message | split("\n")[0])] | @tsv'`). Two calls can straddle a push and pair commit N's subject with commit N+1's SHA; and a second call failing on its own would silently drop the SHA, sending the alert link back to `$GITHUB_SHA` — which on a dispatch is the tip of the *dispatched* ref, the exact mislink this avoids.
3. **gh stderr goes to a file, never `2>&1`.** Any advisory byte gh writes on an otherwise-successful call would make `stuck_pr` non-empty on a healthy repo, and the false alarm is back.
4. **A lookup that fails all three attempts alerts** (🟧, in its own branch *below* the tag branches) rather than warning. `::warning::` neither fails the run nor reaches Discord, so on the run whose entire job is freeze detection, "we could not tell" would look identical to "nothing is wrong". It sits below the tag branches because a run that cut and verified a tag already knows its outcome — a blind freeze lookup there is moot and must not redden a perfect release.
5. **`commit_sha` is emitted from `verdict_sha`**, which only the branch that actually read main sets; every other branch falls back to `$GITHUB_SHA`. A single `main_sha` leaking into, say, the tag-missing branch would link a commit that branch never looked at. The alert body links `steps.check.outputs.commit_sha`, not `github.sha`.

Two smaller ones in the same step: the `$GITHUB_OUTPUT` heredoc delimiter is **randomised** (`detail` can carry gh stderr, and a line equal to a fixed `EOF` truncates the value and fails the step *after* the verdict was computed, so the alert never sends), and gh stderr is **truncated** before it reaches `detail` (Discord rejects embed descriptions over 4096 chars with HTTP 400 — a long error would kill the alert on the one run that needed it).

**Known gap, deliberately left:** the freeze proof only runs when `HEAD_MSG` is empty. On an ordinary `push` to main, an *already*-frozen pipeline still reports green on every subsequent promotion merge, because that push's own head commit is a promotion merge and no tag was expected of it. `release-health.yml`'s daily sweep is what catches that case today. Lifting the proof out of the `if` so it runs on every event would close it; do that in one change across every repo running these steps rather than letting the canonical copy and the live workflows diverge.

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
