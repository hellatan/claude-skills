#!/usr/bin/env bash
# Executes the `Evaluate release outcome` step embedded in
# skills/gh-actions-init/references/release-verification.md, and lints the fenced
# yaml blocks around it.
#
# That step is shell embedded in YAML embedded in Markdown: scripts/validate.sh
# only checks skill structure, and actionlint never sees it because the file is
# Markdown. This is what runs it. No other reference file is covered yet.
#
#   npm run test:release-steps        # or: ./scripts/test-release-steps.sh
#
# Exits non-zero if any case fails, any mutant goes undetected, or the lint pass
# (or its own negative control) fails. Fail-fast: a case failure aborts before the
# lint stage runs, so a red run reports the first failing stage only.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TESTS_DIR="$REPO_ROOT/tests/release-steps"

# Pinned so a linter upgrade cannot silently change what this repo considers
# clean. Bump deliberately, in its own commit, and refresh the checksums with:
#   curl -fsSL https://github.com/rhysd/actionlint/releases/download/v<ver>/actionlint_<ver>_checksums.txt
ACTIONLINT_VERSION="1.7.12"
CACHE_DIR="$REPO_ROOT/.cache/actionlint/$ACTIONLINT_VERSION"

die() {
  echo "❌ $*" >&2
  exit 1
}

need() {
  command -v "$1" >/dev/null 2>&1 || die "$1 is required but not on PATH. $2"
}

need python3 "Install Python 3.9 or newer."
need jq "The step under test pipes its outputs through jq (brew install jq / apt-get install jq)."
need git "lint_reference.py runs 'git init' — actionlint refuses to run outside a git project."
need curl "Needed to fetch the pinned actionlint release."
need tar "Needed to unpack the pinned actionlint release."
python3 -c 'import yaml' 2>/dev/null ||
  die "PyYAML is required. Install it however you manage Python — e.g. 'python3 -m pip install pyyaml',
   'pipx runpip', or a venv. On a Homebrew/system Python, plain pip may refuse with
   'externally-managed-environment'; use a venv or your package manager's python3-yaml."

# ShellCheck is what gives actionlint its shell analysis. Without it actionlint
# silently drops that whole layer and still reports clean, so this is required
# rather than optional — lint_reference.py has a negative control that fails when
# the layer is missing, and a "recommended" dependency whose absence fails the run
# is a required one.
need shellcheck "actionlint needs it for shell analysis (brew install shellcheck / apt-get install shellcheck)."

# Resolve actionlint at the pinned version, downloading it if the local one is
# absent or a different version. Every failure path returns non-zero: `set -e` is
# NOT in effect inside the command substitution this is called from, so a silent
# failure here would hand back a path to a binary that does not exist — or worse,
# a truncated one left executable in the cache by an interrupted download.
resolve_actionlint() {
  local os arch expected url tmp got
  if command -v actionlint >/dev/null 2>&1 &&
    actionlint --version 2>/dev/null | head -n1 | grep -qx "$ACTIONLINT_VERSION"; then
    command -v actionlint
    return 0
  fi
  if [ -x "$CACHE_DIR/actionlint" ] &&
    "$CACHE_DIR/actionlint" --version 2>/dev/null | head -n1 | grep -qx "$ACTIONLINT_VERSION"; then
    echo "$CACHE_DIR/actionlint"
    return 0
  fi
  case "$(uname -s)" in
    Linux) os=linux ;;
    Darwin) os=darwin ;;
    *) echo "unsupported OS $(uname -s) — install actionlint $ACTIONLINT_VERSION manually" >&2; return 1 ;;
  esac
  case "$(uname -m)" in
    x86_64 | amd64) arch=amd64 ;;
    arm64 | aarch64) arch=arm64 ;;
    *) echo "unsupported arch $(uname -m) — install actionlint $ACTIONLINT_VERSION manually" >&2; return 1 ;;
  esac
  case "${os}_${arch}" in
    darwin_amd64) expected=5b44c3bc2255115c9b69e30efc0fecdf498fdb63c5d58e17084fd5f16324c644 ;;
    darwin_arm64) expected=aba9ced2dee8d27fecca3dc7feb1a7f9a52caefa1eb46f3271ea66b6e0e6953f ;;
    linux_amd64) expected=8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8 ;;
    linux_arm64) expected=325e971b6ba9bfa504672e29be93c24981eeb1c07576d730e9f7c8805afff0c6 ;;
    *) echo "no pinned checksum for ${os}/${arch}" >&2; return 1 ;;
  esac

  url="https://github.com/rhysd/actionlint/releases/download/v${ACTIONLINT_VERSION}/actionlint_${ACTIONLINT_VERSION}_${os}_${arch}.tar.gz"
  echo "→ downloading actionlint ${ACTIONLINT_VERSION} (${os}/${arch})" >&2
  mkdir -p "$CACHE_DIR"
  tmp="$(mktemp -d "${TMPDIR:-/tmp}/actionlint.XXXXXX")" || return 1
  # Download to a file, verify, THEN install. Piping curl into tar leaves a
  # truncated, executable binary in the cache when the transfer is cut short,
  # and every later run reuses it.
  curl -fsSL --retry 3 --retry-all-errors --connect-timeout 10 --max-time 180 \
    -o "$tmp/actionlint.tar.gz" "$url" || { rm -rf "$tmp"; echo "download failed: $url" >&2; return 1; }
  if command -v sha256sum >/dev/null 2>&1; then
    got="$(sha256sum "$tmp/actionlint.tar.gz" | cut -d' ' -f1)"
  else
    got="$(shasum -a 256 "$tmp/actionlint.tar.gz" | cut -d' ' -f1)"
  fi
  if [ "$got" != "$expected" ]; then
    rm -rf "$tmp"
    echo "checksum mismatch for actionlint ${ACTIONLINT_VERSION} ${os}/${arch}: got ${got}, expected ${expected}" >&2
    return 1
  fi
  tar -xzf "$tmp/actionlint.tar.gz" -C "$tmp" actionlint || { rm -rf "$tmp"; echo "unpack failed" >&2; return 1; }
  chmod +x "$tmp/actionlint" || { rm -rf "$tmp"; return 1; }
  mv "$tmp/actionlint" "$CACHE_DIR/actionlint" || { rm -rf "$tmp"; return 1; }
  rm -rf "$tmp"
  echo "$CACHE_DIR/actionlint"
}

ACTIONLINT_BIN="$(resolve_actionlint)" || die "could not resolve actionlint ${ACTIONLINT_VERSION} (see above)."
[ -x "$ACTIONLINT_BIN" ] || die "resolved actionlint is not executable: $ACTIONLINT_BIN"
"$ACTIONLINT_BIN" --version 2>/dev/null | head -n1 | grep -qx "$ACTIONLINT_VERSION" ||
  die "resolved actionlint is not version ${ACTIONLINT_VERSION}: $ACTIONLINT_BIN"
export ACTIONLINT_BIN

echo "── release-verification: step behaviour ──────────────────────────"
python3 "$TESTS_DIR/run_cases.py" --mutants

echo
echo "── release-verification: workflow + shell lint ───────────────────"
python3 "$TESTS_DIR/lint_reference.py" --actionlint "$ACTIONLINT_BIN"
