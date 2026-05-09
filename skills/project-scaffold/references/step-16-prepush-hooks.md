# Step 16 — Detect global pre-push hooks before pushing

The bootstrap push in Step 17 pushes directly to `main` and `develop` (the only time this skill ever does that — see Step 17 notes). If the user has a global pre-push hook that blocks pushes to protected branches, the bootstrap will fail unless we either:

- Pass an override env var the hook recognizes, or
- Surface the situation and let the user decide.

This step detects the hook and asks before attempting the push.

## Detect

```bash
git config --global core.hooksPath
ls -la $(git config --global core.hooksPath)/pre-push 2>/dev/null
```

If `core.hooksPath` is unset OR the `pre-push` file doesn't exist, no hook is installed — proceed to Step 17 without warning.

## Warn (only if a hook was found)

> 👀 Detected a global git hook at `<path>` that may block pushing to `main`/`develop`. The bootstrap push needs to seed those branches once before normal protection rules kick in. After this initial push, all future changes go through the normal Pull Request flow.
>
> If your hook supports an override env var (commonly `ALLOW_PUSH_TO_PROTECTED=1`), I'll use it for the bootstrap push only. Confirm the env var name your hook expects, or let me know if it's something else.

Wait for the user's confirmation before proceeding to Step 17. Don't guess at the env var name — different hooks use different conventions, and a wrong guess silently fails.

## Why this is its own step

Discovering the hook *during* the bootstrap push (Step 17) means a partial push: maybe `main` got there, `develop` got blocked, the repo state is now inconsistent, and the user has to clean up. Detecting up front and getting permission for the override keeps Step 17 atomic.
