#!/usr/bin/env python3
"""Pull a named step's `run:` body out of a workflow file or a markdown reference.

The `Evaluate release outcome` step is shell embedded in YAML embedded in
Markdown, so nothing that lints YAML or shell sees it on its own. This module is
the seam: it parses the Markdown's fenced ```yaml blocks (or a real workflow
`.yml`) and hands back the raw `run:` string, so the exact bytes the skill tells
people to paste are the bytes under test.

Accepting a `.yml` too is deliberate — it lets a live downstream workflow be run
through the same case suite as a differential oracle, which is how drift between
the canonical copy and the workflows it is canonical FOR gets caught.

Usage:  extract_step.py <path> "<step name>"      # prints the run: body
"""

from __future__ import annotations

import re
import sys

import yaml

FENCE_RE = re.compile(r"^```ya?ml\n(.*?)^```", re.M | re.S)


def yaml_documents(path: str):
    """Every YAML document in `path` — the file itself, or its fenced blocks."""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    if path.endswith((".yml", ".yaml")):
        yield text
        return
    yield from FENCE_RE.findall(text)


def steps_of(doc):
    """Steps in a parsed document, whether it is a bare step list or a workflow."""
    if isinstance(doc, list):
        yield from (s for s in doc if isinstance(s, dict))
    elif isinstance(doc, dict):
        for job in (doc.get("jobs") or {}).values():
            if isinstance(job, dict):
                yield from (s for s in (job.get("steps") or []) if isinstance(s, dict))
        runs = doc.get("runs")
        if isinstance(runs, dict):  # composite action
            yield from (s for s in (runs.get("steps") or []) if isinstance(s, dict))


def extract_step_dict(path: str, name: str) -> dict:
    """The whole step mapping — `run`, `env`, `shell`, `if`, everything.

    Callers want the whole thing, not just `run`: roughly half of a step's
    correctness lives in its `env:` block (which runner context it wires in), and
    `shell:` decides whether the body runs under `bash -e` or `bash -eo pipefail`.
    A harness that tests only the `run:` string supplies its own correct env to
    whatever it extracts, and is blind to a step that stopped declaring one.
    """
    for raw in yaml_documents(path):
        try:
            doc = yaml.safe_load(raw)
        except yaml.YAMLError:
            continue  # a fenced block that is not valid YAML on its own
        for step in steps_of(doc):
            if step.get("name") == name and "run" in step:
                return step
    raise SystemExit(f"step {name!r} with a run: block not found in {path}")


def extract_step(path: str, name: str) -> str:
    return extract_step_dict(path, name)["run"]


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    sys.stdout.write(extract_step(sys.argv[1], sys.argv[2]))
