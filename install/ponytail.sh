#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="${1:?repo root required}"
source "$(dirname "$0")/lib.sh"

# Ponytail OpenCode integration: plugin is declared in managed opencode.json (merged by opencode.sh).
# Bundled skills are vendored/linked into ~/.config/opencode/skills/ponytail* by opencode.sh/agent-skills.sh.

if have_cmd npm; then
  if npm ls -g --depth=0 @dietrichgebert/ponytail >/dev/null 2>&1; then
    ok "Ponytail npm package already installed globally (@dietrichgebert/ponytail)"
  else
    log "Installing Ponytail OpenCode plugin package globally: @dietrichgebert/ponytail"
    if npm install -g @dietrichgebert/ponytail >/tmp/dotfiles-ponytail-install.log 2>&1; then
      ok "Installed @dietrichgebert/ponytail globally"
    else
      warn "Could not globally install @dietrichgebert/ponytail (see /tmp/dotfiles-ponytail-install.log). OpenCode may still resolve the plugin from config/cache; verify with 'opencode' and /ponytail commands."
    fi
  fi
else
  warn "npm not found; skipping Ponytail package install (plugin is configured in opencode.json)"
fi

# Verify bundled skills are present in managed dotfiles
for d in ponytail ponytail-review ponytail-audit ponytail-debt ponytail-gain ponytail-help; do
  if [[ -f "$REPO_ROOT/.config/opencode/skills/$d/SKILL.md" ]]; then
    ok "Ponytail skill present: $d"
  else
    warn "Ponytail skill missing from dotfiles: $d"
  fi
done

ok "Ponytail integration prepared (plugin configured, skills exposed). Modes/commands are provided by Ponytail; verify in OpenCode."
