#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="${1:?repo root required}"
source "$(dirname "$0")/lib.sh"

OMNI_PORT="${OMNIROUTE_PORT:-20128}"
OMNI_BASE_URL="${OMNIROUTE_BASE_URL:-http://localhost:${OMNI_PORT}}"
OMNI_API_KEY="${OMNIROUTE_API_KEY:-sk_omniroute}" # placeholder for local installs; never commit real keys

if have_cmd npm; then
  if npm ls -g --depth=0 omniroute >/dev/null 2>&1; then
    ok "OmniRoute npm package already installed globally"
  else
    log "Installing OmniRoute globally: omniroute"
    if npm install -g omniroute >/tmp/dotfiles-omniroute-install.log 2>&1; then
      ok "Installed omniroute globally"
    else
      err "Failed to install omniroute globally (see /tmp/dotfiles-omniroute-install.log)"
    fi
  fi
else
  warn "npm not found; cannot install OmniRoute automatically"
fi

# Non-destructive OpenCode provider integration (add provider.omniroute only if missing)
LIVE_OC="$HOME/.config/opencode/opencode.json"
TMP_MANAGED="$(mktemp)"
OMNI_BASE_URL_V1="${OMNI_BASE_URL%/}/v1"
cat > "$TMP_MANAGED" <<'JSON'
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "omniroute": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "OmniRoute",
      "options": {
        "baseURL": "__OMNI_BASE_URL_V1__",
        "apiKey": "__OMNI_API_KEY__"
      },
      "models": {
        "auto": { "name": "OmniRoute Auto" },
        "claude-sonnet-4-5-thinking": { "name": "claude-sonnet-4-5-thinking" },
        "claude-opus-4-5-thinking": { "name": "claude-opus-4-5-thinking" },
        "gemini-3.1-pro-high": { "name": "gemini-3.1-pro-high" },
        "gemini-3-flash": { "name": "gemini-3-flash" }
      }
    }
  }
}
JSON
if have_cmd node; then
  node - "$TMP_MANAGED" "$OMNI_BASE_URL_V1" "$OMNI_API_KEY" <<'NODE'
import fs from 'node:fs';
const [,, p, baseURL, apiKey] = process.argv;
const d = JSON.parse(fs.readFileSync(p, 'utf8'));
d.provider.omniroute.options.baseURL = baseURL;
d.provider.omniroute.options.apiKey = apiKey;
fs.writeFileSync(p, JSON.stringify(d, null, 2) + '\n');
NODE
  node "$REPO_ROOT/install/merge_opencode_config.mjs" "$LIVE_OC" "$TMP_MANAGED" >/dev/null
  ok "Ensured OpenCode provider 'omniroute' exists (non-destructive; existing provider config preserved if already present)"
else
  warn "node not available; skipped OmniRoute provider merge into $LIVE_OC"
fi
rm -f "$TMP_MANAGED"

# systemd user service (manageable/observable). Do not enable/start automatically unless explicitly requested.
UNIT_DIR="$HOME/.config/systemd/user"
UNIT_PATH="$UNIT_DIR/omniroute.service"
mkdir -p "$UNIT_DIR"
if [[ ! -f "$UNIT_PATH" ]]; then
  cat > "$UNIT_PATH" <<UNIT
[Unit]
Description=OmniRoute AI gateway
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/bin/env omniroute serve --port ${OMNI_PORT}
Restart=on-failure
RestartSec=3
Environment=PORT=${OMNI_PORT}
# Set provider credentials via a private env file outside git (e.g. %h/.config/omniroute/omniroute.env, chmod 600)
# EnvironmentFile=%h/.config/omniroute/omniroute.env

[Install]
WantedBy=default.target
UNIT
  ok "Created systemd user unit: $UNIT_PATH (not enabled by default)"
else
  ok "Systemd user unit already exists: $UNIT_PATH"
fi

if have_cmd systemctl; then
  systemctl --user daemon-reload >/dev/null 2>&1 || warn "Failed to daemon-reload user systemd"
  ok "OmniRoute can be managed with: systemctl --user start|stop|status|enable omniroute.service"
else
  warn "systemctl not found; cannot manage omniroute user service automatically"
fi

warn "OmniRoute credentials/API keys must NOT be committed. Configure via environment variables or a private env file (e.g. ~/.config/omniroute/omniroute.env, chmod 600) and reference it from the service or your shell. Review provider terms before enabling auto-routing."
