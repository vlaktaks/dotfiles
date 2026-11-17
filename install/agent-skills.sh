#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="${1:?repo root required}"
source "$(dirname "$0")/lib.sh"

# All Addy Osmani skills are vendored in repo at .config/opencode/skills/* (copied from pinned upstream)
# and linked into ~/.config/opencode/skills by opencode.sh. This script validates completeness.

UPSTREAM_DIR="$REPO_ROOT/sources/addyosmani-agent-skills/skills"
MANAGED_DIR="$REPO_ROOT/.config/opencode/skills"
if [[ ! -d "$UPSTREAM_DIR" ]]; then
  warn "Upstream Addy Osmani skills source missing at $UPSTREAM_DIR; cannot validate completeness"
  exit 0
fi

missing=0
total=0
shopt -s nullglob
for src in "$UPSTREAM_DIR"/*; do
  [[ -d "$src" ]] || continue
  total=$((total+1))
  name="$(basename "$src")"
  if [[ -d "$MANAGED_DIR/$name" && -f "$MANAGED_DIR/$name/SKILL.md" ]]; then
    :
  else
    warn "Missing Addy Osmani skill in managed config: $name"
    missing=$((missing+1))
  fi
done
shopt -u nullglob

if (( missing == 0 )); then
  ok "All Addy Osmani skills present in dotfiles ($total skills)"
else
  err "$missing of $total Addy Osmani skills missing from managed config"
  exit 1
fi

# Ensure upstream contributor AGENTS.md not installed as global config
if [[ -f "$HOME/.config/opencode/AGENTS.md" ]] && grep -q "addyosmani/agent-skills" "$HOME/.config/opencode/AGENTS.md" 2>/dev/null; then
  warn "Global AGENTS.md appears to reference addyosmani repo-contributor instructions; ensure dotfiles-managed AGENTS.md is the intended one"
fi
ok "Addy Osmani agent skills are globally discoverable via OpenCode skills directory (linked from dotfiles)"
