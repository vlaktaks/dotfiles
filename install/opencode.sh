#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="${1:?repo root required}"
# shellcheck source=lib.sh
source "$(dirname "$0")/lib.sh"

MANAGED_OC="$REPO_ROOT/.config/opencode"
LIVE_OC="$HOME/.config/opencode"
mkdir -p "$LIVE_OC/skills" "$LIVE_OC/commands"

# Merge managed opencode.json into live config without clobbering existing settings/providers/plugins
if [[ -f "$MANAGED_OC/opencode.json" ]]; then
  if have_cmd node; then
    node "$REPO_ROOT/install/merge_opencode_config.mjs" "$LIVE_OC/opencode.json" "$MANAGED_OC/opencode.json"
    ok "Merged managed OpenCode config into $LIVE_OC/opencode.json"
  else
    warn "node not available; cannot safely merge opencode.json. Copy/merge manually from $MANAGED_OC/opencode.json"
  fi
else
  warn "Managed opencode.json not found at $MANAGED_OC/opencode.json"
fi

# Link global AGENTS.md (managed)
if [[ -f "$MANAGED_OC/AGENTS.md" ]]; then
  dst="$LIVE_OC/AGENTS.md"
  if [[ -e "$dst" && ! -L "$dst" ]]; then
    # if identical, replace with symlink; else back up
    if cmp -s "$dst" "$MANAGED_OC/AGENTS.md"; then
      rm -f "$dst"
    else
      backup_if_real_file "$dst"
      rm -f "$dst"
    fi
  fi
  link_path "$MANAGED_OC/AGENTS.md" "$dst"
fi

# Link managed skills (each directory containing SKILL.md or skill dir)
if [[ -d "$MANAGED_OC/skills" ]]; then
  shopt -s nullglob
  for src in "$MANAGED_OC/skills"/*; do
    [[ -d "$src" ]] || continue
    name="$(basename "$src")"
    dst="$LIVE_OC/skills/$name"
    if [[ -L "$dst" ]]; then
      link_path "$src" "$dst"
      continue
    fi
    if [[ -e "$dst" ]]; then
      backup_if_real_file "$dst"
      rm -rf "$dst"
    fi
    ln -sfn "$src" "$dst"
    ok "Linked skill: $name"
  done
  shopt -u nullglob
fi

# Link managed commands if any
if [[ -d "$MANAGED_OC/commands" ]]; then
  shopt -s nullglob
  for src in "$MANAGED_OC/commands"/*; do
    [[ -f "$src" ]] || continue
    name="$(basename "$src")"
    link_path "$src" "$LIVE_OC/commands/$name"
  done
  shopt -u nullglob
fi

# Link managed agents (subagent definitions; each *.md under agents/)
if [[ -d "$MANAGED_OC/agents" ]]; then
  mkdir -p "$LIVE_OC/agents"
  shopt -s nullglob
  for src in "$MANAGED_OC/agents"/*.md; do
    [[ -f "$src" ]] || continue
    name="$(basename "$src")"
    link_path "$src" "$LIVE_OC/agents/$name"
  done
  shopt -u nullglob
fi

ok "OpenCode configuration/skills/agents linked from dotfiles (secrets like service.json left local)"
