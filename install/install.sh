#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
# shellcheck source=lib.sh
source "$SCRIPT_DIR/lib.sh"

log "Omarchy/OpenCode dotfiles installer"
log "Repo: $REPO_ROOT"

detect_environment
ensure_dotfiles_link "$REPO_ROOT"
ensure_base_dirs

run_step "OpenCode base config/skills" "$SCRIPT_DIR/opencode.sh" "$REPO_ROOT"
run_step "Ponytail" "$SCRIPT_DIR/ponytail.sh" "$REPO_ROOT"
run_step "OmniRoute" "$SCRIPT_DIR/omniroute.sh" "$REPO_ROOT"
run_step "Graphify" "$SCRIPT_DIR/graphify.sh" "$REPO_ROOT"
run_step "Addy Osmani agent skills" "$SCRIPT_DIR/agent-skills.sh" "$REPO_ROOT"

run_step "Verification" "$SCRIPT_DIR/verify.sh" "$REPO_ROOT" || true

print_summary
