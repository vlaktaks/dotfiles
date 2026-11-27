#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="${1:?repo root required}"
# shellcheck source=lib.sh
source "$(dirname "$0")/lib.sh"

# Magnitude: user-level CLI install (no sudo), loopback-only by default.
# The vendored installer verifies the release publisher signature and SHA-256.
# Never pipe a remote script: we run the pinned, reviewed copy from this repo.

MAG_VERSION_PIN="0.3.7"
MAG_BIN_DIR="$HOME/.magnitude/bin"
MAG_CMD="${MAGNITUDE_CMD:-$MAG_BIN_DIR/magnitude}"
MAG_PORT="${MAGNITUDE_PORT:-10100}"

# Optional explicit opt-ins (off by default):
#   MAGNITUDE_ENABLE_SERVICE=1   enable+start the systemd user unit now
#   MAGNITUDE_PULL_MODEL=<id>    pull one model after install (costs disk)
#   MAGNITUDE_NETWORK_KEY=<hex>  enable LAN network access bound to MAGNITUDE_BIND (default 192.168.1.35)
MAG_BIND="${MAGNITUDE_BIND:-192.168.1.35}"

have_cmd "$MAG_CMD" || { MAG_CMD="magnitude"; have_cmd magnitude || MAG_CMD=""; }

if [[ -n "$MAG_CMD" ]] && "$MAG_CMD" --version >/dev/null 2>&1; then
  ok "Magnitude CLI available ($("$MAG_CMD" --version 2>/dev/null | head -n1))"
else
  log "Installing Magnitude CLI ${MAG_VERSION_PIN} (user-level, no sudo)"
  if sh "$REPO_ROOT/sources/magnitude/install.sh" >/tmp/dotfiles-magnitude-install.log 2>&1; then
    ok "Installed Magnitude CLI (see /tmp/dotfiles-magnitude-install.log)"
  else
    err "Magnitude installer failed (see /tmp/dotfiles-magnitude-install.log)"
    return 1
  fi
fi

# Config: create only if missing; never overwrite user settings.
MAG_CONF="$HOME/.magnitude/config.json"
if [[ ! -f "$MAG_CONF" ]]; then
  mkdir -p "$HOME/.magnitude"
  printf '{\n  "autoDownloadUpdates": true\n}\n' > "$MAG_CONF"
  ok "Created default Magnitude config: $MAG_CONF"
else
  ok "Magnitude config exists: $MAG_CONF (left as-is)"
fi

# Optional: LAN network access with a caller-provided key (never committed).
if [[ -n "${MAGNITUDE_NETWORK_KEY:-}" ]]; then
  if have_cmd node; then
    node - "$MAG_CONF" "$MAG_BIND" <<'NODE'
import fs from 'node:fs';
const [,, conf, bind] = process.argv;
const key = process.env.MAGNITUDE_NETWORK_KEY;
const d = JSON.parse(fs.readFileSync(conf, 'utf8'));
d.network = { enabled: true, bind, apiKey: key, requireApiKey: true };
fs.writeFileSync(conf, JSON.stringify(d, null, 2) + '\n');
NODE
    ok "Enabled Magnitude network access bound to $MAG_BIND (API key required)"
  else
    warn "node not available; set network access manually in $MAG_CONF"
  fi
else
  ok "Magnitude network access not enabled (loopback only; set MAGNITUDE_NETWORK_KEY to enable LAN)"
fi

# systemd user unit (created, not enabled by default)
UNIT_DIR="$HOME/.config/systemd/user"
UNIT_PATH="$UNIT_DIR/magnitude.service"
mkdir -p "$UNIT_DIR"
if [[ ! -f "$UNIT_PATH" ]]; then
  cat > "$UNIT_PATH" <<UNIT
[Unit]
Description=Magnitude local inference engine
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=%h/.magnitude/bin/magnitude serve
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
UNIT
  ok "Created systemd user unit: $UNIT_PATH (not enabled by default)"
else
  ok "Systemd user unit already exists: $UNIT_PATH"
fi

if have_cmd systemctl; then
  systemctl --user daemon-reload >/dev/null 2>&1 || warn "Failed to daemon-reload user systemd"
  if [[ "${MAGNITUDE_ENABLE_SERVICE:-0}" == "1" ]]; then
    systemctl --user enable --now magnitude.service >/dev/null 2>&1 \
      && ok "magnitude.service enabled and started" \
      || warn "Failed to enable magnitude.service"
    loginctl show-user "$USER" -p Linger 2>/dev/null | grep -q 'Linger=yes' \
      || warn "loginctl linger is off; run: sudo loginctl enable-linger $USER (keeps service running after logout)"
  else
    ok "magnitude.service not enabled (opt-in with MAGNITUDE_ENABLE_SERVICE=1)"
  fi
fi

# Optional model pull (explicit opt-in only; never download models by default)
if [[ -n "${MAGNITUDE_PULL_MODEL:-}" ]]; then
  log "Pulling model: $MAGNITUDE_PULL_MODEL"
  if "$MAG_CMD" models pull "$MAGNITUDE_PULL_MODEL" 2>&1 | tail -n 3; then
    ok "Model pull requested: $MAGNITUDE_PULL_MODEL (download continues in Magnitude)"
  else
    warn "Model pull failed for $MAGNITUDE_PULL_MODEL"
  fi
else
  ok "No model pulled (opt-in with MAGNITUDE_PULL_MODEL=<model-id>)"
fi

# Non-destructive OpenCode provider integration (add provider.magnitude only if missing)
LIVE_OC="$HOME/.config/opencode/opencode.json"
TMP_MANAGED="$(mktemp)"
MAG_BASE_URL="${MAGNITUDE_BASE_URL:-http://127.0.0.1:${MAG_PORT}}"
cat > "$TMP_MANAGED" <<'JSON'
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "magnitude": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Magnitude",
      "options": {
        "baseURL": "__MAG_BASE_URL__/inference/v1",
        "apiKey": "magnitude-local"
      },
      "models": {
        "qwen3.5-4b:gguf:q4": {
          "name": "Magnitude Qwen3.5 4B (local)",
          "limit": { "context": 32768, "output": 8192 }
        },
        "qwen3.6-35b-a3b:gguf:q4": {
          "name": "Magnitude Qwen3.6 35B-A3B (local)",
          "limit": { "context": 32768, "output": 8192 }
        }
      }
    }
  }
}
JSON
if have_cmd node; then
  node - "$TMP_MANAGED" "$MAG_BASE_URL" <<'NODE'
import fs from 'node:fs';
const [,, p, baseURL] = process.argv;
const d = JSON.parse(fs.readFileSync(p, 'utf8'));
d.provider.magnitude.options.baseURL = baseURL.replace(/\/$/, '') + '/inference/v1';
fs.writeFileSync(p, JSON.stringify(d, null, 2) + '\n');
NODE
  node "$REPO_ROOT/install/merge_opencode_config.mjs" "$LIVE_OC" "$TMP_MANAGED" >/dev/null
  ok "Ensured OpenCode provider 'magnitude' exists (non-destructive; loopback, key is a local placeholder)"
else
  warn "node not available; skipped Magnitude provider merge into $LIVE_OC"
fi
rm -f "$TMP_MANAGED"
