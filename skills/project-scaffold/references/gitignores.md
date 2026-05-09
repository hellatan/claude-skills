# .gitignore Templates

Pick the right one based on stack. For fullstack repos, concatenate both blocks at root (each subdir can have a tighter own `.gitignore` too if needed).

---

## Universal (always include)

```
# OS
.DS_Store
Thumbs.db

# Editor
.vscode/
.idea/
*.swp
*.swo
*~

# Env
.env
.env.local
.env.*.local

# Logs
*.log
logs/

# Claude Code local state
.claude/local/
```

---

## Node / TypeScript / Next.js

```
# Dependencies
node_modules/

# Build output
dist/
build/
.next/
out/

# Coverage
coverage/
*.lcov

# TypeScript
*.tsbuildinfo

# Vite / parcel / etc.
.vite/
.parcel-cache/

# Testing
.nyc_output/
playwright-report/
test-results/
```

---

## Python

```
# Bytecode
__pycache__/
*.py[cod]
*$py.class

# Packaging
*.egg-info/
*.egg
build/
dist/
wheels/
pip-wheel-metadata/

# Virtual envs
.venv/
venv/
env/
ENV/

# Testing
.pytest_cache/
.coverage
.coverage.*
htmlcov/
.tox/
.mypy_cache/
.ruff_cache/

# Notebooks
.ipynb_checkpoints/
```

---

## Research / data-heavy (on top of Python)

```
# Data
data/raw/
data/processed/
data/*.csv
data/*.parquet
data/*.feather

# Outputs
outputs/
charts/
reports/

# Models
models/*.pkl
models/*.joblib
*.h5
```

---

## Fullstack

Combine **Universal + Node/TS + Python**, plus:

```
# Build artifacts from either side
backend/dist/
frontend/dist/
frontend/.next/
frontend/out/
```
