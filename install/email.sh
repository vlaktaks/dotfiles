#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="${1:?repo root required}"
# shellcheck source=lib.sh
source "$(dirname "$0")/lib.sh"

# Email MCP integration (Outlook via Microsoft Graph + Proton Mail via Bridge IMAP/SMTP).
# Idempotent. No secrets are created or read here; credentials are handled by
# `email-mcp login outlook|proton` into ~/.config/opencode/secrets/ (0700/0600).

SRC="$REPO_ROOT/sources/email-mcp/email_mcp.py"
BIN="$HOME/.local/bin/email-mcp"
SECRETS="$HOME/.config/opencode/secrets"

if [[ -f "$SRC" ]]; then
  mkdir -p "$HOME/.local/bin"
  if ! cmp -s "$SRC" "$BIN" 2>/dev/null; then
    cp "$SRC" "$BIN"
    chmod 755 "$BIN"
    ok "Installed email-mcp to $BIN"
  else
    ok "email-mcp already up to date at $BIN"
  fi
  if ! have_cmd python3; then
    err "python3 not found; email-mcp cannot run"
  fi
  "$BIN" selfcheck >/dev/null || err "email-mcp selfcheck failed"
else
  err "email-mcp source missing: $SRC"
fi

# Private secrets dir (never inside the repo)
mkdir -p "$SECRETS"
chmod 700 "$SECRETS"
ok "Ensured private secrets directory $SECRETS (0700)"

# Merge MCP server + safety permissions into live OpenCode config (non-destructive)
LIVE_OC="$HOME/.config/opencode/opencode.json"
TMP_MANAGED="$(mktemp)"
BIN_PATH="$BIN"
cat > "$TMP_MANAGED" <<'JSON'
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "servers": {
      "email-mcp": {
        "type": "local",
        "command": ["__BIN__"],
        "disabled": true,
        "environment": { "PYTHONUNBUFFERED": "1" }
      }
    }
  },
  "permissions": [
    { "action": "email_mcp_email_accounts", "resource": "*", "effect": "allow" },
    { "action": "email_mcp_list_messages", "resource": "*", "effect": "allow" },
    { "action": "email_mcp_search_messages", "resource": "*", "effect": "allow" },
    { "action": "email_mcp_read_message", "resource": "*", "effect": "allow" },
    { "action": "email_mcp_read_thread", "resource": "*", "effect": "allow" },
    { "action": "email_mcp_list_spam", "resource": "*", "effect": "allow" },
    { "action": "email_mcp_email_shutdown", "resource": "*", "effect": "allow" },
    { "action": "email_mcp_draft_new", "resource": "*", "effect": "ask" },
    { "action": "email_mcp_draft_reply", "resource": "*", "effect": "ask" },
    { "action": "email_mcp_send_draft", "resource": "*", "effect": "ask" },
    { "action": "email_mcp_move_to_folder", "resource": "*", "effect": "ask" },
    { "action": "email_mcp_delete_permanently", "resource": "*", "effect": "ask" }
  ]
}
JSON
if have_cmd node; then
  node - "$TMP_MANAGED" "$BIN_PATH" <<'NODE'
import fs from 'node:fs';
const [,, p, bin] = process.argv;
const d = JSON.parse(fs.readFileSync(p, 'utf8'));
d.mcp.servers['email-mcp'].command = [bin];
fs.writeFileSync(p, JSON.stringify(d, null, 2) + '\n');
NODE
  node "$REPO_ROOT/install/merge_opencode_config.mjs" "$LIVE_OC" "$TMP_MANAGED" >/dev/null
  ok "Ensured 'email-mcp' MCP server (disabled by default) and read/ask permission rules in $LIVE_OC (non-destructive)"
else
  warn "node not available; skipped MCP config merge into $LIVE_OC"
fi
rm -f "$TMP_MANAGED"

# Proton Mail Bridge: official Arch extra package, never started/enabled here
if have_cmd pacman; then
  if pacman -Q protonmail-bridge >/dev/null 2>&1; then
    ok "protonmail-bridge installed ($(pacman -Q protonmail-bridge | awk '{print $2}'))"
  else
    warn "protonmail-bridge not installed; install from the official Arch repo: sudo pacman -S protonmail-bridge"
  fi
fi

# Bridge systemd user unit ships with the package but must never be enabled here
UNIT_DIR="$HOME/.config/systemd/user"
if [[ -f /usr/lib/systemd/user/protonmail-bridge.service ]] && have_cmd systemctl; then
  if systemctl --user is-enabled protonmail-bridge >/dev/null 2>&1; then
    warn "protonmail-bridge user service is enabled (was not enabled by this installer; consider: systemctl --user disable protonmail-bridge)"
  else
    ok "protonmail-bridge user service not enabled (on-demand only)"
  fi
fi

ok "Email MCP configured. Connect it in OpenCode via /mcps when needed; auth: email-mcp login outlook / login proton"
