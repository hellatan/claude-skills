#!/usr/bin/env python3
"""Drive the `Evaluate release outcome` step across the event/state cross product.

The step decides, on every release-please run, whether the release pipeline is
healthy — and it is shell embedded in YAML embedded in Markdown, so no linter in
this repo executes it. This runs it: the extracted step is written to a temp file,
stub `gh`/`sleep` go first on PATH, the env is built FROM THE STEP'S OWN `env:`
block, the script runs under the shell the step declares, and `$GITHUB_OUTPUT` is
parsed back the way the runner parses it.

Two modes:

  (default)    run every case and assert the emitted alert / released / title /
               detail / commit_sha.

  --mutants    the verification OF the verification. Each mutant is a set of
               anchored substitutions that break one behaviour; the run asserts
               the cases that name that behaviour actually go RED. A mutant whose
               anchor no longer matches is a hard error, not a skip — that is the
               signal the step drifted and the mutant went blind.

Usage:
  run_cases.py [--target PATH] [--step NAME] [--only SUBSTR] [--mutants]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_step import extract_step_dict  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
STUB = os.path.join(HERE, "stub")
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
DEFAULT_TARGET = os.path.join(
    REPO_ROOT, "skills", "gh-actions-init", "references", "release-verification.md"
)
DEFAULT_STEP = "Evaluate release outcome"

BASH = shutil.which("bash") or "/bin/bash"

TAGGED = json.dumps(
    {"tag_name": "v1.2.0", "releases_created": "true", "paths_released": '["."]'}
)
# release-please namespaces its outputs for any non-root package path. Reading
# `.tag_name` directly finds nothing here — the failure that fired on a real
# release and put the `endswith("tag_name")` jq in the step.
TAGGED_NAMESPACED = json.dumps(
    {
        "apps/web--tag_name": "v1.2.0",
        "apps/web--release_created": "true",
        "releases_created": "true",
        "paths_released": '["apps/web"]',
    }
)
NO_TAGS = json.dumps({"releases_created": "false", "paths_released": "[]"})
# Carries a scope, because the release title pattern is configurable and the
# subject is NOT always the bare "chore: release X.Y.Z".
RELEASE_SUBJECT = "chore(main): release 1.2.0"
# The other configurable shape: a component between "release" and the version.
COMPONENT_SUBJECT = "chore: release backend 1.2.0"
# Prose that starts the same way and must NOT be read as a release merge.
PROSE_SUBJECT = "chore: release notes cleanup"
# What main's tip actually reads as once any promotion lands after a freeze.
PROMOTION_SUBJECT = "Merge pull request #99 from example/develop"
MAIN_SHA = "1" * 40
RUN_SHA = "2" * 40

# How the harness satisfies each `${{ ... }}` expression the step's env: block
# declares. An expression that is not in here is a hard error rather than a
# silently-unset variable — see build_env().
ENV_EXPRESSIONS = {
    "steps.release.outcome": "RELEASE_OUTCOME",
    "toJSON(steps.release.outputs)": "OUTPUTS_JSON",
    "github.event.head_commit.message": "HEAD_MSG",
    "github.repository": "REPO",
    "github.token": "GH_TOKEN",
}

# (name, env overrides, expectations). `<field>_has` asserts a substring;
# `<field>_max_len` asserts an upper bound.
CASES = [
    # ---- workflow_dispatch: the event carries no head_commit, so HEAD_MSG is
    # empty and the verdict has to come from the freeze proof instead. ----
    (
        "dispatch/healthy",
        dict(HEAD_MSG="", OUTPUTS_JSON=NO_TAGS, STUB_PRLIST="ok:"),
        dict(alert="false", released="false", commit_sha=RUN_SHA),
    ),
    (
        "dispatch/frozen",
        dict(
            HEAD_MSG="",
            OUTPUTS_JSON=NO_TAGS,
            STUB_PRLIST="ok:42",
            STUB_MAIN=f"ok:{MAIN_SHA}\t{RELEASE_SUBJECT}",
        ),
        dict(
            alert="true",
            released="false",
            title_has="NO TAG created",
            detail_has="#42",
            commit_sha=MAIN_SHA,
        ),
    ),
    (
        # The deterministic false-negative: after a promotion merge lands, main's
        # tip matches no release pattern. A verdict re-derived from that subject
        # reports green on a pipeline that is provably frozen.
        "dispatch/frozen+promotion-merge-on-main",
        dict(
            HEAD_MSG="",
            OUTPUTS_JSON=NO_TAGS,
            STUB_PRLIST="ok:42",
            STUB_MAIN=f"ok:{MAIN_SHA}\t{PROMOTION_SUBJECT}",
        ),
        dict(
            alert="true",
            released="false",
            title_has="NO TAG created",
            detail_has="#42",
            commit_sha=MAIN_SHA,
        ),
    ),
    (
        # A cosmetic follow-up call failing must not overturn a proven verdict.
        "dispatch/frozen+unreadable-main-tip",
        dict(HEAD_MSG="", OUTPUTS_JSON=NO_TAGS, STUB_PRLIST="ok:42", STUB_MAIN="fail"),
        dict(alert="true", released="false", title_has="NO TAG created", detail_has="#42"),
    ),
    (
        # The main-tip read is ONE call for both fields and its stderr must stay
        # out of the value, or the alert quotes a corrupted sha.
        "dispatch/frozen+main-tip-writes-stderr",
        dict(
            HEAD_MSG="",
            OUTPUTS_JSON=NO_TAGS,
            STUB_PRLIST="ok:42",
            STUB_MAIN=f"stderr-ok:{MAIN_SHA}\t{RELEASE_SUBJECT}",
        ),
        dict(alert="true", released="false", commit_sha=MAIN_SHA),
    ),
    (
        "dispatch/frozen+main-tip-lag",
        dict(
            HEAD_MSG="",
            OUTPUTS_JSON=NO_TAGS,
            STUB_PRLIST="ok:42",
            STUB_MAIN=f"flaky2:{MAIN_SHA}\t{RELEASE_SUBJECT}",
        ),
        dict(alert="true", released="false", commit_sha=MAIN_SHA),
    ),
    (
        "dispatch/frozen+pr-lookup-lag",
        dict(
            HEAD_MSG="",
            OUTPUTS_JSON=NO_TAGS,
            STUB_PRLIST="flaky2:42",
            STUB_MAIN=f"ok:{MAIN_SHA}\t{RELEASE_SUBJECT}",
        ),
        dict(alert="true", released="false", title_has="NO TAG created", detail_has="#42"),
    ),
    (
        # "We could not tell" must not look like "nothing is wrong".
        "dispatch/pr-lookup-fails-3x",
        dict(HEAD_MSG="", OUTPUTS_JSON=NO_TAGS, STUB_PRLIST="fail"),
        dict(
            alert="true",
            released="false",
            title_has="could not determine",
            detail_has="502",
            commit_sha=RUN_SHA,
        ),
    ),
    (
        # gh's stderr reaches $GITHUB_OUTPUT. A line in it equal to the heredoc
        # delimiter truncates the value and spills unparsable lines — which the
        # output parser below reports as a case failure.
        "dispatch/pr-lookup-fails-with-EOF-in-stderr",
        dict(HEAD_MSG="", OUTPUTS_JSON=NO_TAGS, STUB_PRLIST="fail-eof"),
        dict(alert="true", released="false", title_has="could not determine", detail_has="502"),
    ),
    (
        # Discord rejects an embed description over 4096 chars, so a long gh
        # error must be truncated rather than passed through.
        "dispatch/pr-lookup-fails-with-huge-stderr",
        dict(HEAD_MSG="", OUTPUTS_JSON=NO_TAGS, STUB_PRLIST="fail-huge"),
        dict(alert="true", title_has="could not determine", detail_max_len=4096),
    ),
    (
        # A SUCCESSFUL lookup that also wrote to stderr. Merging stderr into the
        # value would make this healthy repo report frozen.
        "dispatch/pr-lookup-writes-stderr-but-succeeds",
        dict(HEAD_MSG="", OUTPUTS_JSON=NO_TAGS, STUB_PRLIST="stderr-ok:"),
        dict(alert="false", released="false"),
    ),
    (
        # A run that cut and verified a tag is not blind, whatever the freeze
        # lookup did — so a failed lookup must not alert over a good release.
        "dispatch/tagged+pr-lookup-fails",
        dict(HEAD_MSG="", OUTPUTS_JSON=TAGGED, STUB_PRLIST="fail", STUB_TAGS_FOUND="v1.2.0"),
        dict(alert="false", released="true"),
    ),
    # ---- push: head_commit is present, so the subject drives the verdict. ----
    (
        "push/freeze",
        dict(HEAD_MSG=RELEASE_SUBJECT, OUTPUTS_JSON=NO_TAGS),
        dict(
            alert="true",
            released="false",
            title_has="NO TAG created",
            # The action's own outputs are quoted in the alert; without them the
            # reader cannot tell a config mismatch from a genuine no-op run.
            detail_has="releases_created=false",
            commit_sha=RUN_SHA,
        ),
    ),
    (
        "push/freeze-with-component-in-title",
        dict(HEAD_MSG=COMPONENT_SUBJECT, OUTPUTS_JSON=NO_TAGS),
        dict(alert="true", released="false", title_has="NO TAG created"),
    ),
    (
        # Prose that opens with the same words is not a release merge.
        "push/chore-release-prose",
        dict(HEAD_MSG=PROSE_SUBJECT, OUTPUTS_JSON=NO_TAGS),
        dict(alert="false", released="false"),
    ),
    (
        # Only the SUBJECT decides. A release-shaped line in the body must not.
        "push/release-shaped-line-in-body",
        dict(
            HEAD_MSG=f"feat(api): add a widget\n\n{RELEASE_SUBJECT}",
            OUTPUTS_JSON=NO_TAGS,
        ),
        dict(alert="false", released="false"),
    ),
    (
        "push/tagged",
        dict(HEAD_MSG=RELEASE_SUBJECT, OUTPUTS_JSON=TAGGED, STUB_TAGS_FOUND="v1.2.0"),
        dict(alert="false", released="true", commit_sha=RUN_SHA),
    ),
    (
        # A non-root package namespaces every output key.
        "push/tagged-namespaced-outputs",
        dict(
            HEAD_MSG=RELEASE_SUBJECT, OUTPUTS_JSON=TAGGED_NAMESPACED, STUB_TAGS_FOUND="v1.2.0"
        ),
        dict(alert="false", released="true"),
    ),
    (
        # Ref propagation lag right after the tag is cut must not alert.
        "push/tagged+tag-ref-propagation-lag",
        dict(HEAD_MSG=RELEASE_SUBJECT, OUTPUTS_JSON=TAGGED, STUB_TAG_FLAKY="v1.2.0"),
        dict(alert="false", released="true"),
    ),
    (
        # Reported a tag, ref absent on the remote — released must stay false so
        # the tagged-only deploy never ships a phantom tag.
        "push/missing-tag",
        dict(HEAD_MSG=RELEASE_SUBJECT, OUTPUTS_JSON=TAGGED, STUB_TAGS_FOUND=""),
        dict(alert="true", released="false", title_has="tag missing"),
    ),
    (
        # CHARACTERIZATION, NOT AN ENDORSEMENT. This asserts what the step does
        # today, which is the WRONG answer, so that the day someone fixes it this
        # case goes red and forces the fix to be acknowledged here.
        #
        # The state: an earlier release froze (release PR #42 merged, never tagged,
        # still `autorelease: pending`). A later promotion merge pushes to main.
        # release-please aborts with "There are untagged, merged release PRs
        # outstanding" and exits 0 with no tags. head_commit EXISTS on a push, so
        # HEAD_MSG is non-empty, so the freeze proof is never queried; the tip
        # subject is a promotion merge, so is_release_merge stays false; no tags, so
        # nothing alerts. A provably frozen pipeline reports healthy.
        #
        # This is the "Known gap, deliberately left" in release-verification.md: the
        # proof only runs when HEAD_MSG is empty. Closing it means gating on `-z
        # "$tags"` instead, in one change across every repo running these steps —
        # not by editing this expectation. `release-health.yml`'s daily sweep is
        # what catches this case today, within ~24h.
        "push/frozen-prior-release+promotion-merge-KNOWN-GAP",
        dict(
            HEAD_MSG=PROMOTION_SUBJECT,
            OUTPUTS_JSON=NO_TAGS,
            STUB_PRLIST="ok:42",
            STUB_MAIN=f"ok:{MAIN_SHA}\t{PROMOTION_SUBJECT}",
        ),
        dict(alert="false", released="false"),
    ),
    (
        "push/ordinary",
        dict(HEAD_MSG="feat(api): add a widget", OUTPUTS_JSON=NO_TAGS),
        dict(alert="false", released="false"),
    ),
    (
        "push/release-please-action-failed",
        dict(HEAD_MSG=RELEASE_SUBJECT, OUTPUTS_JSON=NO_TAGS, RELEASE_OUTCOME="failure"),
        dict(alert="true", released="false", title_has="release-please step failed"),
    ),
]

# (name, why, [(anchor, replacement)], {cases that MUST go red})
#
# Anchors are the shortest unique substring of the behaviour they break — never a
# whole block — and every substitution asserts it matched exactly once. A mutant
# that reddens EVERY case is rejected too: breaking the script outright proves
# nothing about which behaviour a case observes.
MUTANTS = [
    (
        "freeze-lookup-never-runs",
        "the original defect: no head_commit means no freeze detection at all",
        [('if [ -z "$HEAD_MSG" ]; then', "if false; then")],
        {
            "dispatch/frozen",
            "dispatch/frozen+promotion-merge-on-main",
            "dispatch/frozen+unreadable-main-tip",
            "dispatch/pr-lookup-fails-3x",
        },
    ),
    (
        "frozen-not-ored-into-alert",
        "the freeze proof is queried, then discarded by the branch that alerts",
        [
            (
                '{ [ "$is_release_merge" = "true" ] || [ "$frozen" = "true" ]; }',
                '[ "$is_release_merge" = "true" ]',
            )
        ],
        # NOT dispatch/frozen: there main's tip happens to BE a release subject,
        # so is_release_merge goes true on its own and the alert still fires. That
        # coincidence is precisely what hides this defect in the field — which is
        # why the cases where main's tip is something else are the proof.
        {"dispatch/frozen+promotion-merge-on-main", "dispatch/frozen+unreadable-main-tip"},
    ),
    (
        "freeze-query-drops-state-merged",
        "an OPEN release PR — the normal resting state — starts counting as proof",
        [('gh pr list --repo "$REPO" --state merged \\', 'gh pr list --repo "$REPO" \\')],
        {"dispatch/healthy"},
    ),
    (
        "freeze-query-drops-pending-label",
        "any merged PR starts counting as a stuck release PR",
        [
            (
                '--label "autorelease: pending" --limit 1 --json number \\',
                "--limit 1 --json number \\",
            )
        ],
        {"dispatch/healthy"},
    ),
    (
        "pr-lookup-retry-collapsed",
        "one transient 502 becomes a permanent 'could not determine'",
        [("  lookup_ok=false\n  for attempt in 1 2 3; do", "  lookup_ok=false\n  for attempt in 1; do")],
        {"dispatch/frozen+pr-lookup-lag"},
    ),
    (
        "main-tip-retry-collapsed",
        "one transient 502 drops the sha the alert links",
        [('    main_tsv=""\n    for attempt in 1 2 3; do', '    main_tsv=""\n    for attempt in 1; do')],
        {"dispatch/frozen+main-tip-lag"},
    ),
    (
        "tag-ref-retry-collapsed",
        "ref propagation lag manufactures a false 'tag missing' on a good release",
        [("  found=false\n  for attempt in 1 2 3; do", "  found=false\n  for attempt in 1; do")],
        {"push/tagged+tag-ref-propagation-lag"},
    ),
    (
        "pr-lookup-stderr-merged-into-value",
        "an advisory byte on a successful call makes a healthy repo look frozen",
        [("--jq '.[0].number // \"\"' 2>\"$err_file\"", "--jq '.[0].number // \"\"' 2>&1")],
        {"dispatch/pr-lookup-writes-stderr-but-succeeds"},
    ),
    (
        "main-tip-stderr-merged-into-value",
        "an advisory byte corrupts the sha and subject the alert quotes",
        [
            (
                "--jq '[.sha, (.commit.message | split(\"\\n\")[0])] | @tsv' 2>\"$main_err\"",
                "--jq '[.sha, (.commit.message | split(\"\\n\")[0])] | @tsv' 2>&1",
            )
        ],
        {"dispatch/frozen+main-tip-writes-stderr"},
    ),
    (
        "blind-lookup-reports-healthy",
        "three failed lookups silently become 'nothing is frozen'",
        [("lookup_failed=true", "lookup_failed=false")],
        {"dispatch/pr-lookup-fails-3x"},
    ),
    (
        "gh-stderr-not-truncated",
        "a long gh error blows past Discord's 4096-char embed cap and kills the alert",
        [('lookup_err=$(head -n 5 "$err_file" | cut -c1-400)', 'lookup_err=$(cat "$err_file")')],
        {"dispatch/pr-lookup-fails-with-huge-stderr"},
    ),
    (
        "output-delimiter-fixed-EOF",
        "gh stderr containing an EOF line truncates the value and spills junk",
        [('delim="EOF_$(date +%s)_${RANDOM}"', 'delim="EOF"')],
        {"dispatch/pr-lookup-fails-with-EOF-in-stderr"},
    ),
    (
        "verdict-sha-ignored",
        "the alert links the dispatched ref's tip instead of the commit it judged",
        [('echo "commit_sha=${verdict_sha:-$GITHUB_SHA}"', 'echo "commit_sha=$GITHUB_SHA"')],
        {"dispatch/frozen", "dispatch/frozen+promotion-merge-on-main"},
    ),
    (
        "tag-ref-never-verified",
        "a reported tag is trusted without checking the ref exists on the remote",
        [('if gh api "repos/${REPO}/git/ref/tags/${tag}" >/dev/null 2>&1; then', "if true; then")],
        {"push/missing-tag"},
    ),
    (
        "namespaced-tag-outputs-ignored",
        "a non-root package's `<path>--tag_name` output stops being seen",
        [
            (
                "jq -r 'to_entries[] | select(.key | endswith(\"tag_name\")) | .value | select(. != null and . != \"\")'",
                "jq -r '.tag_name // empty'",
            )
        ],
        {"push/tagged-namespaced-outputs"},
    ),
    (
        "context-jq-key-typo",
        "the alert stops quoting the action's outputs and says <empty> instead",
        [("'.releases_created // \"<empty>\"'", "'.releases_createdX // \"<empty>\"'")],
        {"push/freeze"},
    ),
    (
        "action-failure-ignored",
        "release-please failing outright stops being an alert",
        [
            (
                'if [ "$RELEASE_OUTCOME" = "failure" ]; then',
                'if [ "$RELEASE_OUTCOME" = "__never__" ]; then',
            )
        ],
        {"push/release-please-action-failed"},
    ),
    (
        "release-title-regex-drops-scope",
        "a scoped release subject (chore(main): release …) stops matching",
        [(r"(\([^)]*\))?", "")],
        {"push/freeze"},
    ),
    (
        "release-title-regex-drops-component",
        "a component between 'release' and the version stops matching",
        [(r"([^ ]+ +)?", "")],
        {"push/freeze-with-component-in-title"},
    ),
    (
        "release-title-regex-too-loose",
        "ordinary prose that opens with 'chore: release' is read as a release merge",
        [
            (
                r"'^chore(\([^)]*\))?: release +([^ ]+ +)?v?[0-9]+\.[0-9]+\.[0-9]+'",
                r"'^chore.*release'",
            )
        ],
        {"push/chore-release-prose"},
    ),
    (
        "head-line-takes-whole-message",
        "a release-shaped line in the commit BODY is read as the subject",
        [
            (
                "head_line=$(printf '%s\\n' \"$HEAD_MSG\" | head -n1)",
                'head_line="$HEAD_MSG"',
            )
        ],
        {"push/release-shaped-line-in-body"},
    ),
]


def sub_once(text: str, anchor: str, replacement: str, label: str) -> str:
    """Substitute exactly once, or fail loudly. A no-op mutation is a blind one."""
    count = text.count(anchor)
    if count != 1:
        raise SystemExit(
            f"mutant {label!r}: anchor matched {count} times, expected exactly 1.\n"
            f"  anchor: {anchor!r}\n"
            "  The step drifted from what this mutant models — re-anchor it or "
            "drop it, but do not trust the suite until you do."
        )
    return text.replace(anchor, replacement)


def build_env(step: dict, case_env: dict, runner_env: dict) -> dict:
    """The step's env: block IS the contract — build the environment from it.

    Only variables the step actually declares are set, so deleting `GH_TOKEN:` or
    `OUTPUTS_JSON:` from the reference breaks cases instead of being papered over
    by a harness that supplies its own. An expression the harness cannot satisfy
    is a hard error: a silently-empty variable is exactly the failure mode this
    whole suite exists to catch.
    """
    env = dict(runner_env)
    for name, expr in (step.get("env") or {}).items():
        match = re.fullmatch(r"\$\{\{\s*(.+?)\s*\}\}", str(expr).strip())
        if not match:
            raise SystemExit(f"env {name}: not a single ${{{{ }}}} expression: {expr!r}")
        key = ENV_EXPRESSIONS.get(match.group(1))
        if key is None:
            raise SystemExit(
                f"env {name}: the harness does not model {match.group(1)!r}.\n"
                "  Add it to ENV_EXPRESSIONS with a case value — do not leave it unset."
            )
        env[name] = case_env[key]
    return env


def shell_argv(step: dict, script_path: str) -> list[str]:
    """Match the runner's shell FLAGS (the binary is whichever bash is on PATH).

    A `run:` with no `shell:` gets `bash -e {0}` —
    note the absence of `-o pipefail`, which is the runner's behaviour, not an
    oversight. Declaring `shell: bash` opts into `bash --noprofile --norc -eo pipefail`.
    """
    shell = step.get("shell")
    if shell is None:
        return [BASH, "-e", script_path]
    if shell == "bash":
        return [BASH, "--noprofile", "--norc", "-eo", "pipefail", script_path]
    raise SystemExit(f"the harness does not model shell: {shell!r}")


def parse_github_output(path: str) -> tuple[dict, list]:
    """Parse $GITHUB_OUTPUT the way the runner does, including `key<<DELIM` blocks.

    Strict on purpose: a line that is neither is reported, because a stray line
    is how a value containing the delimiter corrupts the whole file.
    """
    out: dict[str, str] = {}
    errs: list[str] = []
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        heredoc = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)<<(.+)$", line)
        if heredoc:
            key, delim = heredoc.group(1), heredoc.group(2)
            i += 1
            buf, closed = [], False
            while i < len(lines):
                if lines[i] == delim:
                    closed = True
                    break
                buf.append(lines[i])
                i += 1
            if not closed:
                errs.append(f"unterminated heredoc for {key!r}")
            out[key] = "\n".join(buf)
        elif "=" in line:
            key, value = line.split("=", 1)
            if not re.match(r"^[A-Za-z_][A-Za-z0-9_-]*$", key):
                errs.append(f"invalid output key {key!r} (stray line {line[:80]!r})")
            out[key] = value
        else:
            errs.append(f"unparsable output line {line[:80]!r}")
        i += 1
    return out, errs


def run_case(step: dict, env_over: dict):
    with tempfile.TemporaryDirectory() as td:
        gh_out = os.path.join(td, "github_output")
        open(gh_out, "w", encoding="utf-8").close()
        script_path = os.path.join(td, "step.sh")
        with open(script_path, "w", encoding="utf-8") as fh:
            fh.write(step["run"])

        case_env = dict(
            RELEASE_OUTCOME="success",
            OUTPUTS_JSON=NO_TAGS,
            HEAD_MSG="",
            REPO="example/repo",
            GH_TOKEN="stub-token",
        )
        runner_env = dict(os.environ)
        runner_env["PATH"] = STUB + os.pathsep + runner_env["PATH"]
        runner_env.update(
            GITHUB_OUTPUT=gh_out,
            GITHUB_SHA=RUN_SHA,
            GITHUB_SERVER_URL="https://github.com",
            RUNNER_TEMP=td,
            # Stub defaults: healthy repo, main unreadable, no tags on the remote.
            STUB_PRLIST="ok:",
            STUB_MAIN="fail",
            STUB_TAGS_FOUND="",
            STUB_TAG_FLAKY="",
        )
        for key, value in env_over.items():
            (case_env if key in case_env else runner_env)[key] = value

        env = build_env(step, case_env, runner_env)
        proc = subprocess.run(
            shell_argv(step, script_path), env=env, capture_output=True, text=True, timeout=120
        )
        got, errs = parse_github_output(gh_out)
        return proc, got, errs


def check_case(step: dict, env_over: dict, want: dict) -> list[str]:
    proc, got, parse_errs = run_case(step, env_over)
    problems = [f"$GITHUB_OUTPUT: {e}" for e in parse_errs]
    if proc.returncode != 0:
        problems.append(f"step exited {proc.returncode}: {proc.stderr.strip()[:300]}")
    # A gh call the stub does not model would otherwise look exactly like a call
    # that failed — i.e. the step could grow a lookup and stay green.
    if "stub gh: unhandled" in proc.stderr or "stub gh: bad" in proc.stderr:
        marker = next(
            (line for line in proc.stderr.splitlines() if "stub gh:" in line),
            proc.stderr.strip()[:160],
        )
        problems.append(f"the stub does not model a call the step made: {marker}")
    for key, expected in want.items():
        if key.endswith("_has"):
            field = key[:-4]
            if expected not in got.get(field, ""):
                problems.append(
                    f"{field} is missing {expected!r} (got {got.get(field, '')[:160]!r})"
                )
        elif key.endswith("_max_len"):
            field = key[: -len("_max_len")]
            actual = len(got.get(field, ""))
            if actual > expected:
                problems.append(f"len({field})={actual}, want <= {expected}")
        elif got.get(key) != expected:
            problems.append(f"{key}={got.get(key)!r}, want {expected!r}")
    return problems


def run_suite(step: dict, only: str | None, quiet: bool = False) -> tuple[set[str], int]:
    """Run the cases; return the names that failed and how many ran."""
    failed, ran = set(), 0
    for name, env_over, want in CASES:
        if only and only not in name:
            continue
        ran += 1
        problems = check_case(step, env_over, want)
        if problems:
            failed.add(name)
        if not quiet:
            print(f"  [{'FAIL' if problems else 'pass'}] {name}")
            for p in problems:
                print(f"          {p}")
    return failed, ran


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--target", default=DEFAULT_TARGET, help="markdown reference or workflow .yml")
    ap.add_argument("--step", default=DEFAULT_STEP)
    ap.add_argument("--only", help="substring filter on case names")
    ap.add_argument("--mutants", action="store_true", help="assert each mutant goes red")
    args = ap.parse_args()

    step = extract_step_dict(args.target, args.step)
    print(f"target: {os.path.relpath(args.target, REPO_ROOT)}")
    print(f"step:   {args.step} ({len(step['run'])} bytes, env: {len(step.get('env') or {})} vars)")
    print(f"shell:  {' '.join(shell_argv(step, '<script>'))}")
    print()

    print("cases (must be GREEN):")
    failed, ran = run_suite(step, args.only)
    if ran == 0:
        raise SystemExit(f"--only {args.only!r} matched no cases")
    ok = not failed
    print(f"\n{len(failed)} failing of {ran} cases")

    if args.mutants:
        if args.only:
            raise SystemExit("--mutants runs the whole suite; drop --only")
        all_names = {name for name, _, _ in CASES}
        print("\nmutants (each must turn its cases RED):")
        for name, why, subs, expected_red in MUTANTS:
            broken = step["run"]
            for anchor, replacement in subs:
                broken = sub_once(broken, anchor, replacement, name)
            red, _ = run_suite({**step, "run": broken}, None, quiet=True)
            missed = expected_red - red
            indiscriminate = red == all_names
            status = "FAIL" if (missed or indiscriminate) else "pass"
            extra = red - expected_red
            print(f"  [{status}] {name} — {why}")
            print(
                f"          red: {len(red)}/{len(all_names)}"
                + (f"; also {', '.join(sorted(extra))}" if extra else "")
            )
            for m in sorted(missed):
                print(f"          NOT RED (mutant undetected): {m}")
            if indiscriminate:
                print("          every case red — this mutant proves nothing specific")
            if missed or indiscriminate:
                ok = False

    print()
    print("OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
