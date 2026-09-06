#!/usr/bin/env python3
"""Lint the YAML/shell embedded in the release-verification reference file.

actionlint only sees `.github/workflows/*.yml` inside a git repo, and these
workflows live as fenced blocks in Markdown with `<PLACEHOLDER>` tokens in them —
so nothing lints them. This assembles a throwaway git repo out of those blocks
(placeholders substituted with the documented defaults), runs actionlint over it,
and runs `bash -n` over every `run:` body in every emitted file. Only the fenced
``yaml`` blocks are covered — the file's ```bash blocks are not.

It also checks the wiring BETWEEN the steps — which `steps.check.outputs.*` the
consumer steps read versus which the verify step actually writes — because the
case suite drives one `run:` body and cannot see a consumer that reads the wrong
output.

It then runs NEGATIVE CONTROLS: the same pipeline over deliberately broken
copies, asserting each check actually goes red *for the injected reason*. A lint
step that structurally cannot fail is not a lint step, and actionlint silently
drops its whole shell-analysis layer when shellcheck is absent while still
reporting clean.

Usage:  lint_reference.py [--target PATH] [--actionlint BIN]
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_cases import sub_once  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
DEFAULT_TARGET = os.path.join(
    REPO_ROOT, "skills", "gh-actions-init", "references", "release-verification.md"
)
BASH = shutil.which("bash") or "/bin/bash"

FENCE_RE = re.compile(r"^```ya?ml\n(.*?)^```", re.M | re.S)

# The scaffold-time placeholders, filled with the defaults the reference itself
# documents. Their VALUES are irrelevant to the lint — what matters is that the
# blocks parse and lint once a real scaffold has substituted them.
PLACEHOLDERS = {
    "<ALERT_WEBHOOK_SECRET>": "DISCORD_GH_ERRORS_WEBHOOK",
    "<PR_ALERT_WEBHOOK_SECRET>": "DISCORD_PR_ALERTS_WEBHOOK",
    "<ALERT_CHANNEL_LABEL>": "gh_errors",
    "<ALERT_CHANNEL>": "#gh-errors",
    "<PR_ALERT_CHANNEL_LABEL>": "pr_alerts",
    "<PR_ALERT_CHANNEL>": "#pr-alerts",
    "<CRON_MINUTE>": "37",
}

# Context the verify steps are pasted INTO. Scaffolding for the linter only — it
# is not a claim about any real workflow; the canonical release-please.yml lives
# in references/release-please.md.
RELEASE_PLEASE_HEAD = """name: release-please

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: write
  pull-requests: write
  checks: read
  statuses: read

concurrency:
  group: release-please
  cancel-in-progress: false

jobs:
  release-please:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - id: release
        uses: googleapis/release-please-action@v5
        with:
          token: ${{ secrets.RELEASE_PLEASE_TOKEN }}
          target-branch: main
          config-file: .github/release-please-config.json
          manifest-file: .github/.release-please-manifest.json
"""

# Environment that must not leak into the throwaway repo's `git init`: inside a
# git hook or `git rebase -x` these point at the REAL repo, and git would
# initialise that instead of the temp tree.
GIT_ENV_LEAKS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY")


def fill(block: str) -> str:
    for token, value in PLACEHOLDERS.items():
        block = block.replace(token, value)
    return block


def find_block(blocks: list[str], predicate) -> str:
    for block in blocks:
        filled = fill(block)
        try:
            doc = yaml.safe_load(filled)
        except yaml.YAMLError:
            continue
        if predicate(doc):
            return filled
    raise SystemExit("expected YAML block not found in the reference file")


def build_tree(steps_block: str, health_block: str, action_block: str) -> str:
    root = tempfile.mkdtemp(prefix="release-steps-lint-")
    os.makedirs(f"{root}/.github/workflows")
    os.makedirs(f"{root}/.github/actions/discord-alert")
    with open(f"{root}/.github/actions/discord-alert/action.yml", "w", encoding="utf-8") as fh:
        fh.write(action_block)
    with open(f"{root}/.github/workflows/release-health.yml", "w", encoding="utf-8") as fh:
        fh.write(health_block)
    with open(f"{root}/.github/workflows/release-please.yml", "w", encoding="utf-8") as fh:
        fh.write(RELEASE_PLEASE_HEAD + textwrap.indent(steps_block, "      "))
    env = {k: v for k, v in os.environ.items() if k not in GIT_ENV_LEAKS}
    # actionlint refuses to run outside a git project.
    subprocess.run(["git", "init", "-q"], cwd=root, check=True, env=env)
    return root


def run_actionlint(root: str, binary: str) -> tuple[int, str]:
    proc = subprocess.run(
        [binary, "-no-color", "-oneline"], cwd=root, capture_output=True, text=True
    )
    return proc.returncode, (proc.stdout + proc.stderr)


def run_bash_n(root: str) -> tuple[int, list[str]]:
    rc, lines = 0, []
    targets = [
        (f"{root}/.github/workflows/release-please.yml", "jobs"),
        (f"{root}/.github/workflows/release-health.yml", "jobs"),
        (f"{root}/.github/actions/discord-alert/action.yml", "runs"),
    ]
    for path, kind in targets:
        doc = yaml.safe_load(open(path, encoding="utf-8"))
        if kind == "jobs":
            groups = [(name, job.get("steps") or []) for name, job in doc["jobs"].items()]
        else:
            groups = [("runs", (doc.get("runs") or {}).get("steps") or [])]
        for group, steps in groups:
            for step in steps:
                if "run" not in step:
                    continue
                label = f"{os.path.basename(path)}:{group}:{step.get('name', step.get('id', '?'))}"
                proc = subprocess.run(
                    [BASH, "-n"], input=step["run"], capture_output=True, text=True
                )
                lines.append(
                    f"  {BASH} -n {label}: {'ok' if proc.returncode == 0 else 'FAIL ' + proc.stderr.strip()}"
                )
                rc |= proc.returncode
    return rc, lines


def lint(steps_block: str, health_block: str, action_block: str, binary: str):
    root = build_tree(steps_block, health_block, action_block)
    try:
        al_rc, al_out = run_actionlint(root, binary)
        bash_rc, bash_lines = run_bash_n(root)
    finally:
        shutil.rmtree(root)
    return al_rc, al_out, bash_rc, bash_lines


def check_output_wiring(steps_block: str) -> list[str]:
    """The seam the case suite cannot see: producer vs consumers.

    `run_cases.py` asserts what the verify step WRITES to `$GITHUB_OUTPUT`.
    Nothing there asserts that the alert step reads it — so reverting the alert
    to `github.sha` would undo the user-visible half of the fix with the whole
    suite green. This closes that.
    """
    problems: list[str] = []
    steps = yaml.safe_load(steps_block)
    verify = next(s for s in steps if s.get("name") == "Evaluate release outcome")
    consumers = [s for s in steps if s is not verify]

    produced = set(re.findall(r'echo "([A-Za-z_][A-Za-z0-9_]*)(?:=|<<)', verify["run"]))
    consumer_text = yaml.safe_dump(consumers)
    consumed = set(re.findall(r"steps\.check\.outputs\.([A-Za-z_][A-Za-z0-9_]*)", consumer_text))

    for key in sorted(consumed - produced):
        problems.append(f"a consumer step reads steps.check.outputs.{key}, which the step never writes")
    for key in ("alert", "title", "detail", "commit_sha"):
        if key not in produced:
            problems.append(f"the step no longer writes `{key}` to $GITHUB_OUTPUT")
        elif key != "alert" and key not in consumed:
            problems.append(f"`{key}` is written but no consumer step reads it")

    alert_step = next(
        (s for s in consumers if "discord-alert" in str(s.get("uses", ""))), None
    )
    if alert_step is None:
        problems.append("no discord-alert consumer step found")
    else:
        description = str((alert_step.get("with") or {}).get("description", ""))
        if "steps.check.outputs.commit_sha" not in description:
            problems.append(
                "the alert links a commit that is not steps.check.outputs.commit_sha — on a "
                "workflow_dispatch github.sha is the DISPATCHED ref's tip, not the commit judged"
            )
    for step in consumers:
        if "steps.check.outputs.alert == 'true'" not in str(step.get("if", "")):
            problems.append(f"consumer step {step.get('name')!r} is not gated on the alert output")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--target", default=DEFAULT_TARGET)
    ap.add_argument("--actionlint", default=os.environ.get("ACTIONLINT_BIN", "actionlint"))
    args = ap.parse_args()

    if not shutil.which(args.actionlint) and not os.path.exists(args.actionlint):
        raise SystemExit(f"actionlint not found: {args.actionlint}")

    blocks = FENCE_RE.findall(open(args.target, encoding="utf-8").read())
    steps_block = find_block(
        blocks,
        lambda d: isinstance(d, list)
        and any(isinstance(s, dict) and s.get("name") == "Evaluate release outcome" for s in d),
    )
    health_block = find_block(
        blocks, lambda d: isinstance(d, dict) and d.get("name") == "release-health"
    )
    action_block = find_block(
        blocks, lambda d: isinstance(d, dict) and d.get("name") == "discord-alert"
    )

    version = subprocess.run(
        [args.actionlint, "--version"], capture_output=True, text=True
    ).stdout.splitlines()[0]
    print(f"target: {os.path.relpath(args.target, REPO_ROOT)}")
    print(f"actionlint: {version}   bash: {BASH}\n")

    al_rc, al_out, bash_rc, bash_lines = lint(
        steps_block, health_block, action_block, args.actionlint
    )
    print(al_out or "actionlint: clean")
    print("\n".join(bash_lines))
    ok = al_rc == 0 and bash_rc == 0

    wiring = check_output_wiring(steps_block)
    print(f"  output wiring: {'ok' if not wiring else 'FAIL'}")
    for problem in wiring:
        print(f"        {problem}")
    if wiring:
        ok = False

    # Negative controls. Without these, "clean" is indistinguishable from "the
    # linter never looked", and each control asserts the injected REASON — any
    # nonzero exit would otherwise satisfy it (a broken temp repo, for instance).
    print("\nnegative controls (each must go RED for its own reason):")

    def control(label: str, block: str, expect: str, which: str) -> bool:
        al_rc, al_out, bash_rc, bash_lines = lint(
            block, health_block, action_block, args.actionlint
        )
        rc, out = (al_rc, al_out) if which == "actionlint" else (bash_rc, "\n".join(bash_lines))
        red = rc != 0
        matched = red and expect in out
        print(f"  {label:<46} {'red' if matched else 'GREEN — CHECK IS BLIND'}")
        if red and not matched:
            print(f"        went red, but not for {expect}: {out.strip()[:200]}")
        return matched

    ok &= control(
        "actionlint, malformed step",
        sub_once(
            steps_block,
            "- name: Evaluate release outcome",
            "- name: Evaluate release outcome\n  runs-on: ubuntu-latest",
            "actionlint control",
        ),
        '"runs-on"',
        "actionlint",
    )
    # `local` outside a function is invalid to shellcheck (SC2168) and perfectly
    # fine to `bash -n`, so this fails ONLY if actionlint's shell-analysis layer
    # is live. actionlint drops that layer silently when shellcheck is absent.
    ok &= control(
        "actionlint shell analysis (needs shellcheck)",
        sub_once(steps_block, "    alert=false", "    local unused_probe=1\n    alert=false",
                 "shellcheck control"),
        "SC2168",
        "actionlint",
    )
    ok &= control(
        "bash -n, shell syntax error",
        sub_once(steps_block, "    alert=false", '    if [ "$x" = ; then\n    alert=false',
                 "bash -n control"),
        "syntax error",
        "bash",
    )

    print()
    print("OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
