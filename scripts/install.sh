#!/usr/bin/env bash
# Symlinks each skill into ~/.claude/skills/<skill-name>
# Run from repo root: ./scripts/install.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_DIR="$REPO_ROOT/skills"
TARGET_DIR="$HOME/.claude/skills"

if [[ ! -d "$SKILLS_DIR" ]]; then
  echo "❌ No skills/ directory found at $SKILLS_DIR"
  exit 1
fi

mkdir -p "$TARGET_DIR"

echo "Installing skills from $SKILLS_DIR → $TARGET_DIR"
echo

for skill_path in "$SKILLS_DIR"/*/; do
  skill_name="$(basename "$skill_path")"
  target="$TARGET_DIR/$skill_name"

  # If target exists and isn't a symlink to our repo, warn
  if [[ -e "$target" && ! -L "$target" ]]; then
    echo "⚠️  $skill_name: $target exists and is not a symlink. Skipping."
    echo "    To replace with this repo's version: rm -rf '$target' && rerun this script."
    continue
  fi

  # If symlink exists pointing elsewhere, replace it
  if [[ -L "$target" ]]; then
    current_target="$(readlink "$target")"
    if [[ "$current_target" == "$skill_path"* ]] || [[ "$current_target" == "${skill_path%/}" ]]; then
      echo "✅ $skill_name: already symlinked correctly"
      continue
    fi
    echo "🔄 $skill_name: replacing existing symlink"
    rm "$target"
  fi

  ln -s "${skill_path%/}" "$target"
  echo "✅ $skill_name: installed"
done

echo
echo "Done. Run 'ls -la $TARGET_DIR' to verify."
