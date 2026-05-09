# claude-skills

Personal monorepo of Claude skills. Each skill lives under `skills/<skill-name>/` and follows the Anthropic skills convention (SKILL.md + optional `references/`, `scripts/`, `assets/`).

## Lifecycle

- Feature branches off `develop`, never `main`.
- PRs target `develop`. CI must pass before merge.
- Release: PR `develop` → `main`. release-please opens a release PR with version bump + changelog. Merging it tags the commit.
- Skills are installed locally via `scripts/install.sh` (see README).

## Project map

- `skills/<skill-name>/` — one folder per skill
- `scripts/install.sh` — symlinks each skill into `~/.claude/skills/`
- `scripts/validate.sh` — sanity-checks every SKILL.md (frontmatter present, name matches folder, etc.)
- `.github/workflows/` — CI for validation + release-please

## Conventions

- Skill folder names are lowercase, hyphenated. `name` in frontmatter must match folder name.
- Each skill is self-contained. No shared code or references between skills — duplicate is fine.
- `description` field in frontmatter must be "pushy" (explicit trigger contexts) so Claude invokes correctly.
- Conventional commits required (release-please drives off them).
- See `skills/<skill>/SKILL.md` for individual skill details.

## Install (development)

```bash
./scripts/install.sh
```

This symlinks each `skills/<skill-name>/` into `~/.claude/skills/<skill-name>`. Edits in the repo are immediately live.
