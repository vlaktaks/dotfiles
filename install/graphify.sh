#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="${1:?repo root required}"
source "$(dirname "$0")/lib.sh"

# Graphify: install CLI/deps (best-effort) and ensure OpenCode skill is exposed (managed in dotfiles).
# Official upstream installs via pip/pipx: `pip install graphifyy && graphify install` (Claude-focused).
# For OpenCode we expose the vendored opencode skill in ~/.config/opencode/skills/graphify.

SKILL_SRC="$REPO_ROOT/.config/opencode/skills/graphify"
if [[ -f "$SKILL_SRC/SKILL.md" ]]; then
  ok "Graphify OpenCode skill present in dotfiles: $SKILL_SRC"
else
  warn "Graphify skill missing at $SKILL_SRC"
fi

installed_cli=false
if have_cmd graphify; then
  ok "graphify CLI already available ($(command -v graphify))"
  installed_cli=true
else
  log "Attempting to install graphifyy (CLI: graphify) using available Python tooling"
  if have_cmd uv; then
    if uv tool install --upgrade graphifyy >/tmp/dotfiles-graphify-install.log 2>&1; then
      ok "Installed graphifyy via 'uv tool install'"
      installed_cli=true
    else
      warn "uv tool install graphifyy failed (see /tmp/dotfiles-graphify-install.log)"
    fi
  elif have_cmd pipx; then
    if pipx install graphifyy >/tmp/dotfiles-graphify-install.log 2>&1 || pipx upgrade graphifyy >/tmp/dotfiles-graphify-install.log 2>&1; then
      ok "Installed/updated graphifyy via pipx"
      installed_cli=true
    else
      warn "pipx install graphifyy failed (see /tmp/dotfiles-graphify-install.log)"
    fi
  elif have_cmd python3; then
    if python3 -m pip install --user --upgrade graphifyy >/tmp/dotfiles-graphify-install.log 2>&1; then
      ok "Installed graphifyy via 'python3 -m pip --user'"
      installed_cli=true
    else
      warn "python3 -m pip install --user graphifyy failed (see /tmp/dotfiles-graphify-install.log). On externally-managed Python, prefer 'uv tool install graphifyy' or pipx."
    fi
  else
    warn "No Python/uv/pipx tooling found; cannot install graphifyy automatically"
  fi
fi

if $installed_cli && have_cmd graphify; then
  ok "Graphify CLI ready: $(graphify --help 2>/dev/null | head -n1 || echo installed)"
else
  warn "Graphify CLI not confirmed on PATH. OpenCode can still discover the graphify skill if Python deps are satisfied when used; install graphifyy manually if needed."
fi

warn "Graphify's own 'graphify install' targets Claude (~/.claude). This setup uses the OpenCode skill in ~/.config/opencode/skills/graphify (managed by dotfiles)."
