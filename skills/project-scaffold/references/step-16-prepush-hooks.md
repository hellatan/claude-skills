# Step 16 — Detect global pre-push hooks before pushing

The bootstrap push in Step 17 pushes directly to `main` and `develop` (the only time this skill ever does that — see Step 17 notes). If the user has a global pre-push hook that blocks pushes to protected branches, the bootstrap will fail unless we either:

- Pass an override env var the hook recognizes, or
- Surface the situation and let the user decide.

This step detects the hook and asks before attempting the push.

## Detect

Pre-push protection can come from any of four places. Check all of them — missing one and the bootstrap push fails mid-flow:

```bash
# 1. git's own global hook directory
git config --global core.hooksPath
# If set, also check it contains a pre-push hook:
HOOKS_PATH=$(git config --global core.hooksPath)
[[ -n "$HOOKS_PATH" ]] && ls -la "${HOOKS_PATH/#\~/$HOME}/pre-push" 2>/dev/null

# 2. Claude Code harness hooks — these run BEFORE git ever sees the push,
#    so git's own hook chain doesn't include them. Common location:
grep -lE 'push.*protected|pre[-_]?push|block.*push' \
  ~/.claude/hooks/*.py ~/.claude/hooks/*.sh 2>/dev/null

# 3. Shell aliases / functions shadowing git
type git 2>/dev/null | grep -qE 'alias|function' && {
  echo "git is wrapped — inspect the alias/function definition"
  type git
}

# 4. init.templateDir — applies to every repo this user creates,
#    including the one we just did `git init` on
git config --global init.templateDir
```

If **all four** are empty/absent, no protection is in place — proceed to Step 17 without warning.

## Warn (if ANY of the four found something)

Surface this message **verbatim** so the user (and any other agent reading the session) understands this is the documented exception, not a violation:

> 🛡 **Detected pre-push protection:** `<list each source: e.g., "Claude harness hook ~/.claude/hooks/block-push-to-protected.py">`
>
> **This is the skill's documented bootstrap exception.** Seeding `main` + `develop` on a brand-new remote requires one direct push — there is no other way, since PRs need an existing target branch. After this single push, every future change goes through the normal PR flow and the protection re-engages naturally.
>
> Your global git-workflow rules **stay in force** for everything that follows; we're only suppressing the protection for the two `git push` calls in Step 17b.
>
> If your hook supports an override env var (commonly `ALLOW_PUSH_TO_PROTECTED=1`), I'll use it for the bootstrap push only. Confirm the env var name your hook expects, reply `ok` to use the default, or say `skip remote` if you'd rather finish locally and push manually later.

Wait for the user's confirmation before proceeding to Step 17. Don't guess at the env var name — different hooks use different conventions, and a wrong guess silently fails.

**On any user other than the skill author:** the "your global rules stay in force" sentence is the part that matters. Users with their own git-workflow protections shouldn't feel like the skill is asking them to weaken their security posture — it's asking them to allow one specific, scoped, documented exception that the rest of the workflow depends on.

## Why this is its own step

Discovering the hook *during* the bootstrap push (Step 17) means a partial push: maybe `main` got there, `develop` got blocked, the repo state is now inconsistent, and the user has to clean up. Detecting up front and getting permission for the override keeps Step 17 atomic.
