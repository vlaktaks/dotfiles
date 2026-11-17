#!/usr/bin/env bash
set -euo pipefail

# Shared helpers for dotfiles install scripts.
# Intended to be sourced.

COLOR_RESET='\033[0m'
COLOR_GREEN='\033[0;32m'
COLOR_YELLOW='\033[0;33m'
COLOR_RED='\033[0;31m'
COLOR_BLUE='\033[0;34m'

declare -a SUMMARY_OK=()
declare -a SUMMARY_WARN=()
declare -a SUMMARY_FAIL=()

log() { printf '%b[INFO]%b %s\n' "$COLOR_BLUE" "$COLOR_RESET" "$*"; }
ok() { printf '%b[ OK ]%b %s\n' "$COLOR_GREEN" "$COLOR_RESET" "$*"; SUMMARY_OK+=("$*"); }
warn() { printf '%b[WARN]%b %s\n' "$COLOR_YELLOW" "$COLOR_RESET" "$*"; SUMMARY_WARN+=("$*"); }
err() { printf '%b[FAIL]%b %s\n' "$COLOR_RED" "$COLOR_RESET" "$*"; SUMMARY_FAIL+=("$*"); }

have_cmd() { command -v "$1" >/dev/null 2>&1; }

detect_environment() {
  if [[ -f /etc/os-release ]]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    log "OS: ${PRETTY_NAME:-unknown} (ID=${ID:-?})"
    if [[ "${ID:-}" != "arch" && "${ID_LIKE:-}" != *arch* && "${ID:-}" != "omarchy" ]]; then
      warn "Not detected as Arch/Omarchy (ID=${ID:-?}). Scripts will continue but package installation may differ."
    else
      ok "Arch/Omarchy-like environment detected"
    fi
  else
    warn "/etc/os-release not found; cannot confirm Omarchy/Arch"
  fi

  local missing=()
  for c in bash git node npm python3; do
    have_cmd "$c" || missing+=("$c")
  done
  if ((${#missing[@]})); then
    warn "Missing commands at start: ${missing[*]} (install scripts may install/configure some)"
  else
    ok "Core dependencies present: bash git node npm python3"
  fi
  have_cmd uv && ok "uv available" || warn "uv not found (optional for some workflows; required for some Graphify setups)"
  have_cmd opencode && ok "opencode available ($(opencode --version 2>/dev/null | head -n1 || echo unknown))" || warn "opencode CLI not found in PATH"
}

ensure_dotfiles_link() {
  local repo_root="$1"
  local target="$HOME/.dotfiles"
  if [[ -L "$target" ]]; then
    local cur
    cur="$(readlink -f "$target" || true)"
    if [[ "$cur" == "$(readlink -f "$repo_root")" ]]; then
      ok "~/.dotfiles already points to repo"
    else
      warn "~/.dotfiles points to '$cur' (expected '$repo_root'); leaving as-is"
    fi
  elif [[ -e "$target" ]]; then
    warn "~/.dotfiles exists and is not a symlink; leaving as-is"
  else
    ln -s "$repo_root" "$target"
    ok "Created symlink ~/.dotfiles -> $repo_root"
  fi
}

ensure_base_dirs() {
  mkdir -p "$HOME/.config/opencode" "$HOME/.config/opencode/skills" "$HOME/.config/opencode/commands" "$HOME/.local/bin" "$HOME/.config/systemd/user"
  ok "Ensured base config directories"
}

backup_if_real_file() {
  local path="$1"
  if [[ -e "$path" && ! -L "$path" ]]; then
    local bak="${path}.bak.$(date +%Y%m%d%H%M%S)"
    cp -a "$path" "$bak"
    ok "Backed up $path -> $bak"
  fi
}

link_path() {
  local src="$1" dst="$2"
  mkdir -p "$(dirname "$dst")"
  if [[ -L "$dst" ]]; then
    local cur
    cur="$(readlink -f "$dst" || true)"
    if [[ "$cur" == "$(readlink -f "$src")" ]]; then
      ok "Symlink ok: $dst"
      return 0
    fi
  elif [[ -e "$dst" ]]; then
    warn "Destination exists and is not the expected symlink: $dst (skipping replace)"
    return 0
  fi
  ln -sfn "$src" "$dst"
  ok "Linked $dst -> $src"
}

run_step() {
  local name="$1" script="$2" repo_root="$3"
  log "Step: $name"
  if [[ ! -x "$script" && ! -f "$script" ]]; then
    err "Missing script: $script"
    return 1
  fi
  if bash "$script" "$repo_root"; then
    ok "Step completed: $name"
  else
    local rc=$?
    err "Step failed ($rc): $name"
    return $rc
  fi
}

print_summary() {
  printf '\n%b=== Install summary ===%b\n' "$COLOR_BLUE" "$COLOR_RESET"
  printf '%bOK (%d)%b\n' "$COLOR_GREEN" "${#SUMMARY_OK[@]}" "$COLOR_RESET"
  for x in "${SUMMARY_OK[@]:-}"; do [[ -n "$x" ]] && printf '  - %s\n' "$x"; done
  printf '%bWARN (%d)%b\n' "$COLOR_YELLOW" "${#SUMMARY_WARN[@]}" "$COLOR_RESET"
  for x in "${SUMMARY_WARN[@]:-}"; do [[ -n "$x" ]] && printf '  - %s\n' "$x"; done
  printf '%bFAIL (%d)%b\n' "$COLOR_RED" "${#SUMMARY_FAIL[@]}" "$COLOR_RESET"
  for x in "${SUMMARY_FAIL[@]:-}"; do [[ -n "$x" ]] && printf '  - %s\n' "$x"; done
  if ((${#SUMMARY_FAIL[@]})); then
    printf '\nSome steps failed. Review warnings/errors above and rerun after fixing issues.\n'
    return 1
  fi
  printf '\nInstall completed. Review any warnings above for manual follow-up (e.g. OmniRoute credentials).\n'
}
