# Step L — Final report template

Show the user a verbatim summary plus a "next steps" block. Use this template:

## Status block (fill in per-project)

- ✅ Local path
- ✅ GitHub URL (`gh repo view --web` to open in browser)
- ✅ Current branch (should be `develop`)
- ✅ Files + workflows created
- ✅ Branch protection status (applied / skipped with reason)
- ✅ Smoke test results

## "Next steps" block (copy verbatim)

```
Next steps:
1. Push a feature branch and open a PR to develop to confirm CI runs green
2. Fill in the deploy target in `.github/workflows/deploy.yml`
3. Replace the smoke test stubs with real tests as you build features
4. When ready to release, merge develop → main; release-please will open a release PR

Useful commands (run from repo root):
- `npm run check:all` — run everything CI would run
- `npm run dev` — start dev servers
- `pre-commit run --all-files` — manually run all pre-commit hooks
```

(For Python-only projects: replace `npm run` with `python scripts/dev.py`.)
