#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="${1:?repo root required}"
# shellcheck source=lib.sh
source "$(dirname "$0")/lib.sh"

# Ollama (localhost AI model server): verify/pin a single maintainable install,
# ensure the systemd unit + OLLAMA_CONTEXT_LENGTH=32768 drop-in, and recreate the
# model-specific context tags (Modelfile PARAMETER num_ctx). Never auto-downloads models.

OLLAMA_PIN="0.40.18" # pinned known-good stable; bump together with sources/manifests/upstream.json

# 1) Installation: exactly one method (official installer / manual tar / pacman), no duplicates
if have_cmd ollama; then
  local_ver="$(ollama --version 2>/dev/null | awk '{print $NF}')"
  [[ -n "$local_ver" ]] && ok "ollama client present (v$local_ver)" || warn "ollama found but version could not be determined"
  bins="$(type -a ollama 2>/dev/null | wc -l)"
  if (( bins > 1 )); then
    warn "multiple 'ollama' executables on PATH (expected exactly one): $(type -a ollama 2>/dev/null | tr '\n' ' ')"
  fi
  if [[ -n "$local_ver" ]] && [[ "$(printf '%s\n%s\n' "$local_ver" "$OLLAMA_PIN" | sort -V | head -n1)" != "$OLLAMA_PIN" ]]; then
    warn "ollama v$local_ver is older than the pinned v$OLLAMA_PIN; consider updating (see README)"
  fi
else
  warn "ollama not installed. Install it with one method only (requires sudo), then re-run this installer:"
  warn "  official installer:  curl -fsSL https://ollama.com/install.sh | sh"
  warn "  manual tarball:      curl -L https://ollama.com/download/ollama-linux-amd64.tgz | sudo tar -C / -xz"
  warn "  pacman (if acceptable version): sudo pacman -S ollama"
  return 0
fi

if have_cmd nvidia-smi && nvidia-smi >/dev/null 2>&1; then
  ok "NVIDIA GPU detected (CUDA acceleration available to ollama runners)"
else
  warn "nvidia-smi not available; ollama will fall back to CPU (expected on non-NVIDIA machines)"
fi

# 2) systemd unit: verify only; never overwrite an existing unit
if [[ -f /etc/systemd/system/ollama.service ]]; then
  ok "systemd unit present: /etc/systemd/system/ollama.service"
elif [[ -f /usr/lib/systemd/system/ollama.service ]]; then
  ok "systemd unit present: /usr/lib/systemd/system/ollama.service (package-shipped)"
else
  warn "no ollama systemd unit found; create /etc/systemd/system/ollama.service with (sudo required):"
  cat <<'UNIT'
[Unit]
Description=Ollama Service
After=network-online.target

[Service]
ExecStart=/usr/bin/ollama serve
User=ollama
Group=ollama
Restart=always
RestartSec=3
Environment="PATH=/usr/sbin:/usr/bin:/sbin:/bin"

[Install]
WantedBy=default.target
UNIT
  warn "Then: sudo useradd -r -s /bin/false -U -m -d /usr/share/ollama ollama && sudo systemctl daemon-reload && sudo systemctl enable --now ollama"
fi

if have_cmd systemctl; then
  if systemctl is-enabled ollama >/dev/null 2>&1; then
    ok "ollama.service enabled (starts automatically after reboot)"
  else
    systemctl enable ollama >/dev/null 2>&1 && ok "Enabled ollama.service" || warn "ollama.service not enabled; run: systemctl enable ollama (sudo may be required)"
  fi
else
  warn "systemctl not found; cannot verify ollama.service startup"
fi

# 3) Drop-in override: global OLLAMA_CONTEXT_LENGTH=32768 (model-specific num_ctx takes precedence)
OVERRIDE_DIR="/etc/systemd/system/ollama.service.d"
OVERRIDE_FILE="$OVERRIDE_DIR/override.conf"
if [[ -f "$OVERRIDE_FILE" ]]; then
  if grep -q 'OLLAMA_CONTEXT_LENGTH=32768' "$OVERRIDE_FILE" 2>/dev/null; then
    ok "drop-in sets OLLAMA_CONTEXT_LENGTH=32768 (global default)"
  else
    warn "drop-in $OVERRIDE_FILE exists without OLLAMA_CONTEXT_LENGTH=32768; leaving as-is"
  fi
elif [[ -w /etc/systemd/system ]]; then
  mkdir -p "$OVERRIDE_DIR"
  printf '[Service]\nEnvironment="OLLAMA_CONTEXT_LENGTH=32768"\n' > "$OVERRIDE_FILE"
  ok "Created drop-in $OVERRIDE_FILE (OLLAMA_CONTEXT_LENGTH=32768)"
else
  warn "drop-in missing; create it with (sudo required):"
  warn "  sudo mkdir -p $OVERRIDE_DIR && printf '%s\\n' '[Service]' 'Environment=\"OLLAMA_CONTEXT_LENGTH=32768\"' | sudo tee $OVERRIDE_FILE"
fi

# 4) Model tags (manifest-only; no model downloads performed here)
if have_cmd curl && curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  tags="$(curl -fsS http://127.0.0.1:11434/api/tags)"
  if printf '%s' "$tags" | grep -q '"inkling-2-mini:16k"'; then
    ok "tag inkling-2-mini:16k present"
  elif printf '%s' "$tags" | grep -q '"inkling-2-mini:latest"'; then
    tmp="$(mktemp)"
    printf 'FROM inkling-2-mini:latest\nPARAMETER num_ctx 16384\n' > "$tmp"
    if ollama create inkling-2-mini:16k -f "$tmp" >/dev/null 2>&1; then
      ok "Created tag inkling-2-mini:16k (num_ctx 16384, GPU enabled) from local inkling-2-mini"
    else
      warn "Failed to create tag inkling-2-mini:16k; create manually (see README)"
    fi
    rm -f "$tmp"
  else
    warn "base model inkling-2-mini not pulled; download first (optional, ~18 GB), then re-run:"
    warn "  ollama pull inkling-2-mini"
  fi
  printf '%s' "$tags" | grep -q '"qwen3.8:27b"' \
    && ok "model qwen3.8:27b present (uses global 32768 context; no tag needed)" \
    || warn "model qwen3.8:27b not pulled (optional, ~17 GB): ollama pull qwen3.8:27b"
else
  warn "ollama server not reachable on localhost:11434; skipped model tag checks (start it and re-run)"
fi

ok "Ollama step completed (models are optional downloads; see README for manual steps)"
