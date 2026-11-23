#!/usr/bin/env bash
# Isolated installer regression test: never touches the real ~/.config/opencode.
# Works both in the dotfiles layout and in the standalone skill repository.
set -euo pipefail

SKILL_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"

fail() { printf '[FAIL] %s\n' "$*" >&2; exit 1; }
pass() { printf '[ OK ] %s\n' "$*"; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export HOME="$TMP/home"
mkdir -p "$HOME/.config/opencode/skills/my-local-skill"
printf '# local skill\n' > "$HOME/.config/opencode/skills/my-local-skill/SKILL.md"

if [[ -f "$SKILL_DIR/../../../../install/opencode.sh" ]]; then
  MODE="dotfiles"
  REPO_ROOT="$(cd -- "$SKILL_DIR/../../../.." && pwd -P)"
elif [[ -f "$SKILL_DIR/SKILL.md" ]]; then
  MODE="standalone"
  REPO_ROOT="$SKILL_DIR"
else
  fail "cannot locate the dotfiles root or a standalone SKILL.md from $SKILL_DIR"
fi

LINK="$HOME/.config/opencode/skills/linux-security-check"

if [[ "$MODE" == "dotfiles" ]]; then
  cat > "$HOME/.config/opencode/opencode.json" <<'JSON'
{
  "$schema": "https://opencode.ai/config.json",
  "update": "disable",
  "plugins": ["@dietrichgebert/ponytail"],
  "provider": {"custom": {"name": "Custom"}},
  "customKey": true
}
JSON

  bash "$REPO_ROOT/install/opencode.sh" "$REPO_ROOT" >/dev/null
  bash "$REPO_ROOT/install/opencode.sh" "$REPO_ROOT" >/dev/null

  [[ -L "$LINK" ]] || fail "linux-security-check is not symlinked"
  [[ "$(readlink -f "$LINK")" == "$(readlink -f "$REPO_ROOT/.config/opencode/skills/linux-security-check")" ]] \
    || fail "linux-security-check symlink points to the wrong place"
  [[ -f "$LINK/SKILL.md" ]] || fail "installed skill has no SKILL.md"
  [[ -f "$LINK/references/linux-audit.md" ]] || fail "installed skill lacks references"
  [[ -f "$LINK/scripts/scan-patterns.py" ]] || fail "installed skill lacks scripts"
  pass "skill linked and complete"

  [[ -d "$HOME/.config/opencode/skills/my-local-skill" ]] \
    || fail "existing local skill was removed"
  [[ ! -L "$HOME/.config/opencode/skills/my-local-skill" ]] \
    || fail "existing local skill was replaced by a symlink"
  pass "existing local skill preserved"

  node - "$HOME/.config/opencode/opencode.json" <<'NODE'
import fs from 'node:fs';
const j = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
if (j.provider?.custom?.name !== 'Custom') { console.error('provider lost'); process.exit(1); }
if (j.customKey !== true) { console.error('custom key lost'); process.exit(1); }
const plugin = (j.plugins || []).filter(p => String(p).includes('@dietrichgebert/ponytail'));
if (plugin.length !== 1) { console.error('ponytail count=' + plugin.length); process.exit(1); }
NODE
  pass "existing OpenCode config preserved without duplicates"

  managed_count="$(find "$REPO_ROOT/.config/opencode/skills" -mindepth 1 -maxdepth 1 -type d | wc -l)"
  linked_count="$(find "$HOME/.config/opencode/skills" -mindepth 1 -maxdepth 1 -type l | wc -l)"
  (( linked_count >= managed_count )) || fail "expected >= $managed_count skill links, found $linked_count"
  [[ -z "$(find "$HOME/.config/opencode" -name '*.bak.*' -print -quit)" ]] \
    || fail "reinstall created unexpected backups"
  pass "reinstall is idempotent ($linked_count links, no backups)"

  if bash "$REPO_ROOT/install/verify.sh" "$REPO_ROOT" >"$TMP/verify.log" 2>&1; then
    pass "verify.sh passed in isolated HOME"
  else
    cat "$TMP/verify.log" >&2
    fail "verify.sh failed in isolated HOME"
  fi
else
  # Standalone layout: simulate the documented clone/copy installation without
  # touching the active configuration, then simulate a safe in-place update.
  cp -a "$SKILL_DIR" "$LINK"
  rm -rf "$LINK/.git" "$LINK/scripts/__pycache__" "$LINK/tests/__pycache__"

  [[ -f "$LINK/SKILL.md" ]] || fail "installed skill has no SKILL.md"
  [[ -f "$LINK/references/linux-audit.md" ]] || fail "installed skill lacks references"
  [[ -f "$LINK/scripts/scan-patterns.py" ]] || fail "installed skill lacks scripts"
  [[ -f "$LINK/tests/run-all.sh" ]] || fail "installed skill lacks tests"
  grep -q '^name: Linux-Security-Check$' "$LINK/SKILL.md" \
    || fail "installed SKILL.md has an unexpected name"
  pass "standalone skill copied and complete"

  [[ -d "$HOME/.config/opencode/skills/my-local-skill" ]] \
    || fail "existing local skill was removed"
  pass "existing local skill preserved"

  cp -a "$SKILL_DIR/." "$LINK/"
  rm -rf "$LINK/.git"
  [[ -f "$LINK/SKILL.md" && -f "$LINK/scripts/report.py" ]] \
    || fail "safe update lost files"
  pass "standalone update is non-destructive"
fi

printf '\nInstaller regression test passed (%s layout).\n' "$MODE"
