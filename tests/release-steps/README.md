# release-steps

Executes the shell steps embedded in
[`../../skills/gh-actions-init/references/release-verification.md`](../../skills/gh-actions-init/references/release-verification.md).

```bash
npm run test:release-steps          # or: ./scripts/test-release-steps.sh
```

## Prerequisites

`python3` (3.9+) with **PyYAML**, plus `jq`, `git`, `curl`, `tar` and
**ShellCheck** — all required. `jq` because the step under test pipes its outputs
through it; ShellCheck because actionlint silently drops its entire shell-analysis
layer without it and still reports clean, so a negative control here fails rather
than quietly losing that coverage. `actionlint` is fetched at a pinned version
(checksum-verified) into a gitignored `.cache/` if the local one is absent or a
different version.

## Why this exists

That reference file is the declared **canonical copy** of the `Evaluate release
outcome` step that lives inside `release-please.yml` in several downstream repos.
It is shell inside YAML inside Markdown, which means:

- `scripts/validate.sh` never looks at it — it checks skill structure.
- actionlint never looks at it — the file is Markdown, not a workflow.

So the canonical copy was the only code in the repo that nothing executed, and it
drifted: it shipped a freeze detector that structurally could not fire on a
`workflow_dispatch`, because `HEAD_MSG` (`github.event.head_commit.message`) is
empty on an event with no head commit. A green CI run said nothing about it.

## What runs

| Piece | What it does |
|---|---|
| `extract_step.py` | Parses the Markdown's fenced ` ```yaml ` blocks (or a real workflow `.yml`) and returns a named step **whole** — `run`, `env`, `shell`. |
| `run_cases.py` | Writes the `run:` body to a temp file, puts `stub/` first on `PATH`, builds the environment **from the step's own `env:` block**, runs it under the shell the step declares, parses `$GITHUB_OUTPUT` (including `key<<DELIM` blocks) and asserts `alert` / `released` / `title` / `detail` / `commit_sha`. |
| `run_cases.py --mutants` | Breaks one behaviour at a time and asserts the cases that name it actually go **red**. |
| `lint_reference.py` | Assembles a throwaway git repo from the fenced `yaml` blocks (placeholders substituted; the file's ```` ```bash ```` blocks are **not** covered), runs pinned actionlint + `bash -n` over every `run:` body, checks the producer/consumer output wiring, then repeats the pass on deliberately broken copies as negative controls. |
| `stub/gh`, `stub/sleep` | A fake `gh` that **models** the queries (see below) and a no-op `sleep` so retry loops run instantly. |

Three seams are deliberately closed, because each is a way an instrument can be
blind while looking busy:

1. **The `env:` block is inside the test boundary.** The environment is built from
   what the step declares, and an expression the harness does not model is a hard
   error rather than a silently-unset variable. Deleting `GH_TOKEN:` or
   `OUTPUTS_JSON:` from the reference turns cases red instead of being papered
   over by a harness that supplies its own correct env.
2. **`stub/gh` honours the query, it does not hand back the answer.** The modelled
   world always contains an *open* `autorelease: pending` PR (the normal resting
   state of an unmerged release PR) and an unlabelled merged PR. A freeze query
   that drops `--state merged` or the label filter therefore gets a *wrong*
   answer, the way it would against real GitHub — rather than the right one from a
   stub that ignored its arguments. `gh` also refuses to run unauthenticated.
3. **`lint_reference.py` checks the wiring between steps.** The case suite drives
   one `run:` body; it asserts what the step *writes*, never that anyone reads it.
   The wiring check pairs the outputs written against the `steps.check.outputs.*`
   the consumer steps read, so reverting the alert's commit link to `github.sha`
   fails even though every case still passes.

## The cases

23 cases over the event/state cross product, because the two events differ in the
one input the verdict used to depend on:

- **`workflow_dispatch`** (no `head_commit`, so `HEAD_MSG` is empty) × healthy /
  frozen / frozen-with-a-promotion-merge-on-main / frozen-with-an-unreadable-main-tip /
  frozen-with-a-main-tip-that-writes-stderr / frozen-with-a-retried-main-tip /
  frozen-with-a-retried-PR-lookup / PR-lookup-fails-3× / PR-lookup-fails-with-an-`EOF`-line-in-stderr /
  PR-lookup-fails-with-9000-bytes-of-stderr / PR-lookup-writes-stderr-but-succeeds /
  tagged-with-a-failed-lookup.
- **`push`** (subject present) × freeze / freeze-with-a-component-in-the-title /
  `chore: release notes cleanup`-is-not-a-release / a-release-shaped-line-in-the-body /
  tagged / tagged-with-namespaced-outputs / tagged-with-tag-ref-propagation-lag /
  missing-tag / ordinary / release-please-action-failed /
  a-prior-release-is-frozen-and-a-promotion-merge-lands.

Several exist specifically because they are the cases a *plausible* implementation
gets wrong: `frozen+promotion-merge-on-main` is green under any verdict re-derived
from main's tip subject; `pr-lookup-writes-stderr-but-succeeds` is red under any
lookup that captures stderr with `2>&1`; `tagged-namespaced-outputs` is red under
any reader of `.tag_name` (the failure that actually fired on a real release);
`chore-release-prose` is red under a loosened release-subject regex.

## Mutants — why a green suite is not enough

A suite that passes proves nothing about whether it *could* fail. `--mutants`
applies anchored substitutions one behaviour at a time — each asserted to match
exactly once, so a mutant that stops matching is a hard error rather than a silent
skip — and requires the cases that name that behaviour to go red. A mutant that
reddens *every* case is rejected too: breaking the script outright proves nothing
about which behaviour any individual case observes.

21 mutants, covering the freeze gate (`freeze-lookup-never-runs`,
`frozen-not-ored-into-alert`, `freeze-query-drops-state-merged`,
`freeze-query-drops-pending-label`, `blind-lookup-reports-healthy`), the three
retry loops (`pr-lookup-`, `main-tip-`, `tag-ref-retry-collapsed`), stderr
handling (`pr-lookup-`/`main-tip-stderr-merged-into-value`,
`gh-stderr-not-truncated`, `output-delimiter-fixed-EOF`), the tag logic
(`tag-ref-never-verified`,
`namespaced-tag-outputs-ignored`), the action-outcome branch
(`action-failure-ignored`) and the alert's context string (`context-jq-key-typo`),
the release-subject regex (`-drops-scope`,
`-drops-component`, `-too-loose`), how that subject is extracted
(`head-line-takes-whole-message`), and the alert link (`verdict-sha-ignored`).

`lint_reference.py` carries the same idea as negative controls, each asserting the
injected *reason* rather than merely a non-zero exit — including one that fails if
actionlint's ShellCheck layer is not actually running.

## Differential oracle

`--target` accepts a real workflow, so a live downstream `release-please.yml` can
be driven through the identical suite:

```bash
python3 tests/release-steps/run_cases.py --target /path/to/repo/.github/workflows/release-please.yml
```

A repo whose workflow disagrees with the canonical copy shows up as failing cases,
which is the drift this whole directory exists to make visible.

## Adding a case

Append to `CASES` in `run_cases.py`: a name, the env overrides that describe the
world (`STUB_PRLIST`, `STUB_MAIN`, `STUB_TAGS_FOUND`, `STUB_TAG_FLAKY`,
`HEAD_MSG`, `OUTPUTS_JSON`, `RELEASE_OUTCOME`), and the expected outputs. Then add
or extend a mutant that the new case — and ideally only the new case — catches,
and confirm it goes red.

One case is a **characterization test, not an endorsement**:
`push/frozen-prior-release+promotion-merge-KNOWN-GAP` asserts `alert=false` — the
*wrong* answer — because that is what the step does today. An earlier release froze
(release PR merged, never tagged, still `autorelease: pending`); a later promotion
merge pushes to main; `head_commit` exists, so the freeze proof is never queried;
the tip subject is a promotion merge, so nothing matches; no tags, so nothing
alerts. A provably frozen pipeline reports healthy — and this is the one freeze
state reachable under a `push`-only trigger.

That is gap 1 of the three "Known gaps, deliberately left" in
`release-verification.md`: the proof runs only when `HEAD_MSG` is empty. Closing it means gating on `-z "$tags"`
instead, in one change across every repo running these steps — not by editing that
expectation. `release-health.yml`'s daily sweep catches the case within ~24h. The
day someone fixes the gate, this case goes red and forces the fix to be
acknowledged here.

## Known gaps

- Only `release-verification.md` is covered. Every other reference file under
  `skills/*/references/` still carries runnable blocks that nothing executes.
- The `release-health.yml` sweep steps are linted and `bash -n`-checked but not
  driven through cases.
- Gaps 2 and 3 documented in `release-verification.md` — a proven freeze discarded
  when the same run cut any tag, and when the release-please step itself failed —
  have no case yet, characterization or otherwise.
- No case sets `OUTPUTS_JSON` to `null` — what `toJSON(steps.release.outputs)`
  yields if the `id: release` reference ever breaks. The step dies at the first
  `jq` in that state, before writing any output, so no alert would send. Closing
  it means changing the step, not just adding a case.
