#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="${1:?repo root required}"
source "$(dirname "$0")/lib.sh"

fail=0
pass() { ok "VERIFY: $*"; }
failmsg() { err "VERIFY: $*"; fail=1; }
warnmsg() { warn "VERIFY: $*"; }

LIVE_OC="$HOME/.config/opencode"
MANAGED_OC="$REPO_ROOT/.config/opencode"

# OpenCode config parses
if have_cmd node && [[ -f "$LIVE_OC/opencode.json" ]]; then
  if node -e "JSON.parse(require('fs').readFileSync(process.argv[1],'utf8'))" "$LIVE_OC/opencode.json" >/dev/null 2>&1; then
    pass "~/.config/opencode/opencode.json parses as JSON"
  else
    failmsg "~/.config/opencode/opencode.json is not valid JSON"
  fi
else
  warnmsg "cannot validate opencode.json (node or file missing)"
fi

# AGENTS.md
if [[ -L "$LIVE_OC/AGENTS.md" ]]; then
  tgt="$(readlink -f "$LIVE_OC/AGENTS.md" || true)"
  if [[ "$tgt" == "$(readlink -f "$MANAGED_OC/AGENTS.md")" ]]; then
    pass "OpenCode AGENTS.md symlinked to managed file"
  else
    warnmsg "OpenCode AGENTS.md symlink target unexpected: $tgt"
  fi
elif [[ -f "$LIVE_OC/AGENTS.md" ]]; then
  warnmsg "OpenCode AGENTS.md exists but is not a symlink to managed file"
else
  failmsg "OpenCode AGENTS.md missing"
fi

# Skills: all managed skills linked and contain SKILL.md
managed_count=0
linked_ok=0
missing_skill=0
shopt -s nullglob
for src in "$MANAGED_OC/skills"/*; do
  [[ -d "$src" ]] || continue
  name="$(basename "$src")"
  managed_count=$((managed_count+1))
  dst="$LIVE_OC/skills/$name"
  if [[ -L "$dst" ]] && [[ "$(readlink -f "$dst" || true)" == "$(readlink -f "$src")" ]]; then
    linked_ok=$((linked_ok+1))
  else
    warnmsg "skill not correctly symlinked: $name"
  fi
  if [[ ! -f "$dst/SKILL.md" && ! -f "$src/SKILL.md" ]]; then
    failmsg "skill missing SKILL.md: $name"
    missing_skill=$((missing_skill+1))
  fi
done
shopt -u nullglob
if (( managed_count == linked_ok && managed_count > 0 && missing_skill == 0 )); then
  pass "all managed skills linked with SKILL.md present ($managed_count)"
else
  warnmsg "managed=$managed_count linked_ok=$linked_ok missing_skillmd=$missing_skill"
fi

# Linux-Security-Check: structure, frontmatter, references, scripts, symlink
LSC_SRC="$MANAGED_OC/skills/linux-security-check"
LSC_DST="$LIVE_OC/skills/linux-security-check"
lsc_required=(
  SKILL.md
  references/linux-audit.md
  references/malware-analysis.md
  references/omarchy-plugin-audit.md
  references/software-supply-chain.md
  references/update-risk.md
  references/privacy-audit.md
  references/report-format.md
  scripts/scan-patterns.py
  scripts/check-omarchy-manifest.py
  scripts/report.py
  tests/run-all.sh
)
if [[ -f "$LSC_SRC/SKILL.md" ]]; then
  pass "Linux-Security-Check skill present in repository"
  grep -q '^name: Linux-Security-Check$' "$LSC_SRC/SKILL.md" \
    && pass "Linux-Security-Check frontmatter name is valid" \
    || failmsg "Linux-Security-Check frontmatter name is invalid"
  grep -q '^description: .*' "$LSC_SRC/SKILL.md" \
    && pass "Linux-Security-Check frontmatter description present" \
    || failmsg "Linux-Security-Check frontmatter description missing"
  for rel in "${lsc_required[@]}"; do
    [[ -f "$LSC_SRC/$rel" ]] || failmsg "Linux-Security-Check missing: $rel"
  done
  if [[ -L "$LSC_DST" ]] && [[ "$(readlink -f "$LSC_DST" || true)" == "$(readlink -f "$LSC_SRC")" ]]; then
    pass "Linux-Security-Check discoverable via ~/.config/opencode/skills symlink"
  else
    failmsg "Linux-Security-Check not correctly symlinked into ~/.config/opencode/skills"
  fi
  if have_cmd python3; then
    if python3 - "$LSC_SRC" <<'PY' >/dev/null 2>&1
import pathlib
import sys
for path in sorted(pathlib.Path(sys.argv[1]).glob("scripts/*.py")):
    compile(path.read_text(encoding="utf-8"), str(path), "exec")
PY
    then
      pass "Linux-Security-Check scripts compile"
    else
      failmsg "Linux-Security-Check scripts have a syntax error"
    fi
  else
    warnmsg "python3 not available; skipped Linux-Security-Check script syntax check"
  fi
else
  failmsg "Linux-Security-Check skill missing from repository"
fi

# Key skills present
for s in ponytail ponytail-review ponytail-audit ponytail-debt ponytail-gain ponytail-help graphify spec-driven-development linux-security-check; do
  [[ -f "$LIVE_OC/skills/$s/SKILL.md" ]] && pass "skill discoverable: $s" || failmsg "skill missing: $s"
done

# Plugin configured (no duplicates for ponytail entry as string/object in simple cases)
if have_cmd node && [[ -f "$LIVE_OC/opencode.json" ]]; then
  node - "$LIVE_OC/opencode.json" <<'NODE' >/tmp/dotfiles-verify-plugin.txt 2>/dev/null || true
import fs from 'node:fs';
const p=process.argv[2];
const j=JSON.parse(fs.readFileSync(p,'utf8'));
const plugins=[...(Array.isArray(j.plugins)?j.plugins:[]), ...(Array.isArray(j.plugin)?j.plugin:[])];
const hits=plugins.filter(x=> (typeof x==='string' && x.includes('@dietrichgebert/ponytail')) || (x && typeof x==='object' && JSON.stringify(x).includes('@dietrichgebert/ponytail')));
console.log(hits.length);
NODE
  hits="$(cat /tmp/dotfiles-verify-plugin.txt 2>/dev/null || echo 0)"
  if [[ "$hits" == "1" ]]; then
    pass "Ponytail plugin configured exactly once in opencode.json"
  elif [[ "$hits" =~ ^[0-9]+$ ]] && (( hits > 1 )); then
    warnmsg "Ponytail plugin appears $hits times in opencode.json"
  else
    failmsg "Ponytail plugin not found in opencode.json"
  fi
fi

# Binaries
have_cmd opencode && pass "opencode CLI available ($(opencode --version 2>/dev/null | head -n1))" || warnmsg "opencode CLI not on PATH"
have_cmd omniroute && pass "omniroute CLI available ($(command -v omniroute))" || warnmsg "omniroute CLI not installed/on PATH"
have_cmd graphify && pass "graphify CLI available ($(graphify --help 2>/dev/null | head -n1 || echo installed))" || warnmsg "graphify CLI not installed/on PATH"

# systemd unit (created by installer; should exist but not be enabled/started)
if [[ -f "$HOME/.config/systemd/user/omniroute.service" ]]; then
  pass "omniroute systemd user unit present"
  if have_cmd systemctl; then
    en="$(systemctl --user is-enabled omniroute 2>/dev/null || true)"
    ac="$(systemctl --user is-active omniroute 2>/dev/null || true)"
    [[ "$en" == "enabled" ]] && warnmsg "omniroute.service is enabled (manual opt-in expected)" || pass "omniroute.service not enabled ($en)"
    [[ "$ac" == "active" ]] && warnmsg "omniroute.service is active" || pass "omniroute.service not active ($ac)"
  fi
else
  warnmsg "omniroute systemd user unit not found"
fi

# OmniRoute health (non-fatal/runtime-dependent)
if have_cmd curl; then
  if curl -fsS "http://127.0.0.1:${OMNIROUTE_PORT:-20128}/" >/dev/null 2>&1 || curl -fsS "http://127.0.0.1:${OMNIROUTE_PORT:-20128}/v1/models" >/dev/null 2>&1; then
    pass "OmniRoute endpoint reachable locally"
  else
    warnmsg "OmniRoute not reachable on localhost:${OMNIROUTE_PORT:-20128} (service may not be running)"
  fi
fi

# Ollama
have_cmd ollama && pass "ollama CLI available ($(ollama --version 2>/dev/null | awk '{print $NF}'))" || warnmsg "ollama CLI not installed/on PATH"
if have_cmd ollama && have_cmd curl; then
  cli_v="$(ollama --version 2>/dev/null | awk '{print $NF}')"
  srv="$(curl -fsS http://127.0.0.1:11434/api/version 2>/dev/null || true)"
  if [[ -n "$srv" ]]; then
    srv_v="$(printf '%s' "$srv" | sed -n 's/.*"version":"\([^"]*\)".*/\1/p')"
    [[ -n "$srv_v" && "$srv_v" == "$cli_v" ]] \
      && pass "ollama client/server versions match ($cli_v)" \
      || warnmsg "ollama client/server version mismatch: client=$cli_v server=${srv_v:-unknown}"
  else
    warnmsg "ollama server not reachable on localhost:11434 (service may not be running)"
  fi
fi
if have_cmd ss && ss -tln 2>/dev/null | grep -q '127.0.0.1:11434'; then
  pass "ollama API bound to 127.0.0.1:11434 (localhost only)"
else
  warnmsg "ollama listener on 127.0.0.1:11434 not found"
fi
if [[ -f /etc/systemd/system/ollama.service ]] || [[ -f /usr/lib/systemd/system/ollama.service ]]; then
  pass "ollama systemd unit present"
  if have_cmd systemctl && systemctl is-enabled ollama >/dev/null 2>&1; then
    pass "ollama.service enabled"
  else
    warnmsg "ollama.service not enabled"
  fi
else
  warnmsg "no ollama systemd unit found"
fi
if [[ -f /etc/systemd/system/ollama.service.d/override.conf ]] && grep -q 'OLLAMA_CONTEXT_LENGTH=32768' /etc/systemd/system/ollama.service.d/override.conf 2>/dev/null; then
  pass "drop-in sets OLLAMA_CONTEXT_LENGTH=32768"
else
  warnmsg "drop-in OLLAMA_CONTEXT_LENGTH=32768 not found"
fi
if have_cmd curl && curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  tags="$(curl -fsS http://127.0.0.1:11434/api/tags 2>/dev/null)"
  printf '%s' "$tags" | grep -q '"inkling-2-mini:16k"' && pass "tag inkling-2-mini:16k present" || warnmsg "tag inkling-2-mini:16k missing"
  show16="$(curl -fsS http://127.0.0.1:11434/api/show -d '{"model":"inkling-2-mini:16k"}' 2>/dev/null || true)"
  if printf '%s' "$show16" | grep -q 'num_ctx[[:space:]]*16384'; then
    pass "inkling-2-mini:16k num_ctx=16384"
  else
    warnmsg "inkling-2-mini:16k num_ctx not 16384 (show: ${show16:0:120})"
  fi
  printf '%s' "$tags" | grep -q '"qwen3.8:27b"' && pass "model qwen3.8:27b present" || warnmsg "model qwen3.8:27b not pulled (optional)"
else
  warnmsg "ollama model tags not verifiable (server unreachable)"
fi

# Email MCP (Outlook)
EMCP="$HOME/.local/bin/email-mcp"
if [[ -x "$EMCP" ]]; then
  pass "email-mcp binary present at $EMCP"
  if have_cmd python3 && "$EMCP" selfcheck >/dev/null 2>&1; then
    pass "email-mcp selfcheck passed (gates, builders, parsing)"
  else
    failmsg "email-mcp selfcheck failed"
  fi
else
  failmsg "email-mcp binary missing at $EMCP"
fi
if [[ -d "$HOME/.config/opencode/secrets" ]]; then
  perms="$(stat -c '%a' "$HOME/.config/opencode/secrets" 2>/dev/null || echo '?')"
  [[ "$perms" == "700" ]] && pass "secrets dir is 0700" || failmsg "secrets dir perms are $perms (expected 700)"
  for f in outlook-tokens.json outlook-config.json; do
    if [[ -f "$HOME/.config/opencode/secrets/$f" ]]; then
      fperms="$(stat -c '%a' "$HOME/.config/opencode/secrets/$f" 2>/dev/null || echo '?')"
      [[ "$fperms" == "600" ]] && pass "$f is 0600" || failmsg "$f perms are $fperms (expected 600)"
    fi
  done
else
  warnmsg "secrets dir not created yet (~/.config/opencode/secrets; email-mcp login creates it)"
fi
if have_cmd node && [[ -f "$LIVE_OC/opencode.json" ]]; then
  node - "$LIVE_OC/opencode.json" <<'NODE' >/tmp/dotfiles-verify-email.txt 2>/dev/null || true
import fs from 'node:fs';
const j = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const srv = (j.mcp && j.mcp.servers && j.mcp.servers['email-mcp']) || null;
const perms = Array.isArray(j.permissions) ? j.permissions : [];
const ask = perms.filter(r => r.action && r.action.startsWith('email_mcp_') && r.effect === 'ask').map(r => r.action);
const allow = perms.filter(r => r.action && r.action.startsWith('email_mcp_') && r.effect === 'allow').map(r => r.action);
console.log(JSON.stringify({ present: !!srv, disabled: !!(srv && srv.disabled), ask, allow }));
NODE
  out="$(cat /tmp/dotfiles-verify-email.txt 2>/dev/null || echo '{}')"
  if node -e "const d=JSON.parse(process.argv[1]); if(!d.present)process.exit(1); if(!d.disabled)process.exit(2); if(d.ask.length!==5)process.exit(3); if(d.allow.length<6)process.exit(4); if(d.ask.includes('email_mcp_email_shutdown')||d.allow.includes('email_mcp_email_shutdown'))process.exit(5);" "$out"; then
    pass "email-mcp configured in opencode.json: present, disabled by default, 5 ask-gated write tools, read tools allowed, no stale shutdown rule"
  else
    failmsg "email-mcp opencode.json entry incomplete: $out"
  fi
else
  warnmsg "cannot verify email-mcp opencode.json entry (node or config missing)"
fi

# Secret hygiene (paths only, no content)
[[ -f "$LIVE_OC/service.json" ]] && pass "local OpenCode service.json present (untracked/local secret-bearing file expected)" || true
[[ -f "$HOME/.config/omniroute/omniroute.env" ]] && warnmsg "private OmniRoute env file exists (ensure chmod 600, never commit)" || pass "no ~/.config/omniroute/omniroute.env found (credentials not configured yet, expected)"

# Repo hygiene: no secret-bearing files may be tracked in the dotfiles repository
if have_cmd git && [[ -d "$REPO_ROOT/.git" ]]; then
  if tracked_secrets="$(git -C "$REPO_ROOT" ls-files | grep -Ei '(^|/)(secrets?/|\.env|\.env\.|outlook-tokens|outlook-config|.*\.key$|.*\.pem$)' || true)"; then
    if [[ -n "$tracked_secrets" ]]; then
      failmsg "repo tracks secret-bearing paths: $tracked_secrets"
    else
      pass "no secret-bearing files tracked in dotfiles repo"
    fi
  fi
fi

if (( fail )); then
  warn "Verification completed with issues"
  exit 1
fi
ok "Verification checks passed (review warnings for manual/runtime items)"
