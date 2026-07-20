# project-scaffold on existing repos — design

**Date:** 2026-07-16
**Status:** Draft — one open decision (A vs B) blocks an implementation plan
**Home skill:** `project-scaffold` (greenfield-only today). The five sister skills — `gitflow-init`,
`gh-actions-init`, `precommit-init`, `testing-init`, `claude-md-init` — already retrofit their own
slices onto existing repos; only the orchestration is missing.

> **Provenance:** field notes captured live on 2026-06-14 while scaffolding an existing private
> Python + Next.js monorepo (it already had a committed engine) with the greenfield skill. They
> lived in that app repo for a month — where none of the work is actionable, since the skill isn't
> there — and nothing happened. Ported here so they sit with the skill. Items 1–9 are the original
> notes; item 10 was found on 2026-07-16 and is the reason this got picked back up.

> **Numbering:** items are cited as "item N". A bare `#N` is a PR link, never a list index.

## Problem

`/project-scaffold` assumes an empty directory. Applied to a repo that already has code, ~9 of its
21 steps are wrong in ways that range from "blocked immediately" to "silently ships a bug." It has
been used this way anyway, because no `project-retrofit` exists and the sister skills each cover
only their own slice.

The failure isn't that the skill errors out — it's that **the greenfield flow half-applies and still
reports success**. The live run ended with a green `check:all` and a commit message saying so, while
the JS toolchain was missing its formatter and `CLAUDE.md` asserted otherwise for a month.

## Evidence — what this cost on the live run

Scaffolded 2026-06-14. The generated `CLAUDE.md` claimed `JS: ESLint + Prettier, CSS Modules` and
the pre-commit config claimed formatting was *"enforced by the web app's ESLint/Prettier in CI"*.
Prettier was never installed — no dep, no config, no script, no CI job — for the month until it was
noticed and wired up.

The docs weren't wrong on purpose. That Conventions line comes from the `claude-md-init` template,
which states **the skill's guarantees** as fact ("Pre-commit runs ESLint + Prettier on staged
files"). Greenfield makes them true by construction (Step 11). Retrofitted onto a half-applied
Step 11, the template keeps asserting a promise nothing delivered — so a generated doc becomes a
**trap that reads with the authority of something verified**.

It went off as designed: an agent read that line and ran `npx prettier --write` as a formatting
check. With no local prettier, npx downloaded one and reformatted the file to *its* defaults
(single→double quotes, 80-col rewrap) — a 194-line diff on a +7-line change. That one was caught and
reverted; the next might not have been.

## Goals

- One entry point that takes an existing repo to the same end state as a greenfield scaffold:
  feature → develop → main → tag → deploy, with CI, hooks, and release-please wired.
- Preserve what's already there: history (`git mv`), existing root files (merge, don't overwrite),
  the current version, the existing remote.
- **Fail loudly at scaffold time** when a step half-applies, instead of shipping a doc that lies.
- Keep the greenfield path as readable as it is today.

## Non-goals

- Not a general monorepo-restructuring tool. Item 4 detects and proposes a layout mapping; it does
  not try to know every layout.
- Not re-deciding framework defaults — Next.js / FastAPI / CSS Modules / ESLint+Prettier all stand.
- Not touching the sister skills' internals; they already retrofit correctly.

## The ten adaptations

Items 1–9 are the original field notes, verbatim in substance. Grouped by implementation cost — each
is prose in a skill an agent reads, not code, which is why none are hard.

### Mechanical (7) — a conditional or an assertion each

1. **Worktree guard blocks scaffold edits.** Greenfield runs `git init` at Step 15 — *after* files
   are written — so no guard is active during creation. An existing repo has `.git` already, so a
   PreToolUse worktree guard blocks `Edit`/`Write` to the primary checkout immediately.
   **Mitigation:** create `.claude/.allow-primary-edits` for the duration, remove it at the end.
2. **Step 2 inverts.** Greenfield verifies the target dir does NOT exist. Retrofit verifies it DOES
   and *is a git repo*; capture current branch + HEAD + existing version.
5. **Step 15 must skip `git init`.** `.git` exists. Create `develop` from the current default
   branch; expect existing history, so the scaffold lands as an additional commit, not a clean
   first one.
6. **Version invariant reconciliation.** Greenfield pins `0.1.0` everywhere. An existing repo has a
   version that must be reconciled with the release-please manifest invariant (or release-please
   seeded at the current version). The live run happened to already be `0.1.0`.
7. **Stale artifacts from the old layout.** Pre-restructure `.venv`, `.pytest_cache`, `.ruff_cache`
   must be cleaned/recreated under the new structure.
9. **Step 17 must check for an existing remote** before `gh repo create`. Greenfield assumes none.
10. **The tripwire** — see below. Its mitigation is an assertion; its *value* is that it makes the
    other nine self-checking.

### Real but bounded (2)

3. **Framework scaffold must target a SUBDIR.** `create-next-app` runs into e.g. `apps/web` with
   `--skip-git` and must not clobber root files. Greenfield assumes an empty root.
8. **Merge, don't overwrite, existing root files.** `.gitignore`, `README.md`, `pyproject.toml`,
   `CLAUDE.md` must be merged. `create-next-app` also emits stub `CLAUDE.md`/`README.md` in the
   subdir that collide and must be deduped (keep root, delete stub). Looks judgment-heavy, but
   "merge root, keep root CLAUDE.md, delete the stub" *is* the implementation when an agent is the
   audience.

### Genuinely hard (1)

4. **New step: "fold existing code in."** Greenfield has nothing to relocate. Retrofit needs a
   `git mv` pass into the monorepo layout (live run: `src/` → `apps/api/src/`, `tests/` →
   `apps/api/tests/`, `pyproject.toml` → `apps/api/`). This step doesn't exist in the skill at all.
   It doesn't need to be general — detect the layout, propose a mapping, confirm before moving.

## Item 10 — the tripwire, and why it's the keystone

**The gap:** retargeting `create-next-app` into a subdir (item 3) delivers ESLint, `jsconfig.json`,
and `next.config.mjs` for free, so the JS toolchain *looks* done. Prettier is the half that never
arrives for free — Step 11 installs it and writes `.prettierrc` as a separate action, and that
action is easy to skip when its neighbours appear satisfied.

**Why greenfield can't hit it:** canonical `check:all` is
`lint && format:check && typecheck && test`. A missing Prettier fails Step 20's smoke test
instantly. The live run's hand-written `check:all` was `lint && test && build` — no `format:check`.

> **The check that would have caught the gap was missing for the same reason the gap existed.**

So the smoke test went green and green meant done. This is why item 10 is not just a tenth entry:
items 1–9 are things a careful operator might remember, while item 10 is what catches the ones they
forget. Any retrofit step that half-applies is invisible unless the verification is canonical.

**Mitigation (two parts):**
1. Don't hand-write `check:all` during a retrofit. Diff it against `root-package-scripts.md` and
   treat every absent check as an unverified claim.
2. Assert directly, at the end: for each stack present, its formatter is a real dev dep **and**
   `format:check` is reachable from `check:all` **and** from CI.

**Generalized — the rule that outlives Prettier:** every template-inherited doc line asserts a
guarantee some step was supposed to deliver. If a retrofit skips that step, the doc still says it.
A scaffold isn't done until **every tool a generated doc names is greppable in a manifest**. Cheap
to check; fails loudly at scaffold time instead of silently a month later.

## Open decision — A vs B

The one thing blocking an implementation plan.

**A — add an "existing repo" mode to `project-scaffold`.** Detect `.git` at Step 2 and branch the
flow. One skill, one entry point. Cost: conditionals in most of 21 steps; prose skills degrade when
they fill with "if existing, do X instead," and the greenfield path (the common case) pays that
readability tax forever.

**B — a sibling `project-retrofit` skill.** Composes the already-retrofit-capable sister skills plus
the restructure/fold-in step, delegates the rest. Keeps `project-scaffold` greenfield-pure.

**Recommendation: B.** The sister skills already do most of the work, so B is mostly glue — the
genuinely new logic is items 3, 4, and 10. It also matches the `2026-05-31-ci-retrigger` precedent,
where template work lived in the owning skill and `project-scaffold` inherited via delegation. The
cost of B is a second entry point users must know to pick; mitigate with an "existing repo? use
`/project-retrofit`" line in `project-scaffold`'s "When NOT to use this skill".

## Components (assuming B)

1. **`skills/project-retrofit/SKILL.md`** — detect-existing-repo (item 2), escape hatch (item 1),
   fold-in (item 4), subdir framework scaffold (item 3), merge-not-overwrite (item 8), version
   reconcile (item 6), stale-artifact clean (item 7), then delegate to the five sister skills,
   then the item-10 tripwire assert. Skip git-init (item 5); check remote before create (item 9).
2. **`skills/project-scaffold/SKILL.md`** — one line under "When NOT to use this skill" pointing at
   `/project-retrofit`. No other change; greenfield stays pure.
3. **Tripwire, standalone** — worth landing in `project-scaffold`'s Step 20 smoke test regardless of
   A/B. It's a few lines, helps greenfield too, and is independently useful.

## Testing

- Dogfood against a scratch repo with committed code in the old layout; assert the end state matches
  a greenfield scaffold of the same stack.
- Negative test for item 10: delete `prettier` from the manifest and confirm the retrofit **fails**
  rather than reporting success — the exact scenario seen live.
- `scripts/validate.sh` for skill-lint on any new SKILL.md.

## Composition across skills

`project-retrofit` owns only the orchestration + fold-in. `gitflow-init`, `gh-actions-init`,
`precommit-init`, `testing-init`, and `claude-md-init` keep owning their slices and need no changes —
they already detect and extend existing repos. `project-scaffold` stays greenfield and gains one
pointer line.
