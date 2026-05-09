# claude-skills

Personal monorepo of Claude Code skills.

## Skills

| Skill | Description |
|---|---|
| [project-scaffold](skills/project-scaffold) | Bootstrap a new project with prescriptive defaults — Next.js / FastAPI, lean CLAUDE.md, git workflow, pre-commit, GitHub Actions CI, release-please, deploy stub. |

## Install

```bash
git clone git@github.com:hellatan/claude-skills.git ~/projects/claude-skills
cd ~/projects/claude-skills
./scripts/install.sh
```

This symlinks each skill into `~/.claude/skills/`. Edits in the repo are picked up immediately by Claude Code.

## Adding a new skill

1. Branch off `develop`: `git checkout -b feat/<skill-name>`
2. Create `skills/<skill-name>/SKILL.md` (see Anthropic conventions in `CLAUDE.md`)
3. Run `./scripts/validate.sh` to confirm the SKILL.md is well-formed
4. Run `./scripts/install.sh` to symlink it locally
5. Test with Claude Code
6. Commit with `feat: add <skill-name> skill`, open PR to develop

## Updating an existing skill

Edit in place under `skills/<skill-name>/`. Symlink is already live, so changes show up immediately in Claude Code. Commit with `fix:` (bugfix) or `feat:` (new behavior).
