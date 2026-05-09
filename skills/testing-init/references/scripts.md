# Scripts to add

## Node — `package.json` `"scripts"`

Add only the scopes the user opted into. Don't add `test:e2e` if e2e was skipped, etc.

```json
{
  "scripts": {
    "test": "vitest run",
    "test:unit": "vitest run --dir src",
    "test:integration": "vitest run --dir tests/integration",
    "test:e2e": "playwright test"
  }
}
```

If a `test` script already exists with different content, **don't overwrite it**. Surface the conflict to the user and let them decide whether to replace, rename (e.g., `test:legacy`), or skip.

If the project has a `check:all` script (from `project-scaffold`), extend it to include the new test commands:

```json
"check:all": "npm run lint && npm run format:check && npm run typecheck && npm run test"
```

## Python — `scripts/dev.py` (if it exists)

If the project was scaffolded by `project-scaffold`, it has `scripts/dev.py`. Extend the dispatch with:

```python
elif cmd == "test":
    run("pytest")
elif cmd == "test:unit":
    run('pytest -m "not integration and not e2e"')
elif cmd == "test:integration":
    run('pytest -m integration')
elif cmd == "test:e2e":
    run('pytest -m e2e')
```

If `scripts/dev.py` doesn't exist, document the raw commands in the final report:

```
Run tests:
- All:         pytest
- Unit only:   pytest -m "not integration and not e2e"
- Integration: pytest -m integration
- E2E:         pytest -m e2e
- Coverage:    pytest --cov
```

## Don't add pre-commit test hooks

Tests belong in CI, not pre-commit. Pre-commit should be fast (<5s ideally) — running tests there slows commits and discourages frequent commits. Even running unit tests via pre-commit is usually wrong.

If the user explicitly asks to add tests to pre-commit, push back gently and recommend CI-only first. If they still want it, they can add it themselves.
