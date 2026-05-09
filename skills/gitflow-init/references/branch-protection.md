# Branch protection — `gh api` script + 403 fallback

Skip this step entirely if Step 6's check showed **free-tier + private repo** (GitHub returns 403 in that case — branch protection on private repos requires Pro). Otherwise, apply protection to `main`, `develop`, and (if staging enabled) `stage`. The required status check `contexts` must match the `name:` of each CI job in `.github/workflows/ci.yml` exactly.

## Bash

```bash
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)

protect_branch() {
  local branch=$1
  gh api -X PUT "repos/$REPO/branches/$branch/protection" --input - <<'EOF'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["lint + typecheck", "unit tests", "integration tests", "e2e tests", "production build"]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "required_approving_review_count": 0,
    "dismiss_stale_reviews": false,
    "require_code_owner_reviews": false
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
EOF
}

protect_branch main
protect_branch develop
# protect_branch stage   # only if staging was opted in
```

## If protection fails with 403

Surface this exact message:

> Branch protection couldn't be applied — GitHub returned a **403 (forbidden — your account/plan isn't allowed to do this)**. Branch protection requires GitHub Pro for private repos. You have three options:
>
> 1. Make the repo public (everything works, free): `gh repo edit --visibility public`
> 2. Upgrade to GitHub Pro (~$4/mo) — branch protection works on private repos
> 3. Skip it for now (your local pre-commit hooks + global git rules still protect you, and CI still runs on PRs — you just *can* merge a failing PR if you ignore the red X)
