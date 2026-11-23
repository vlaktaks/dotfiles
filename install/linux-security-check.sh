#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="${1:?repo root required}"
source "$(dirname "$0")/lib.sh"

# Linux-Security-Check is a dotfiles-managed skill. opencode.sh links every
# managed skill directory into ~/.config/opencode/skills; this step validates
# the skill structure so a broken install fails early.
SKILL_DIR="$REPO_ROOT/.config/opencode/skills/linux-security-check"

required=(
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

missing=0
for rel in "${required[@]}"; do
  if [[ ! -f "$SKILL_DIR/$rel" ]]; then
    err "Linux-Security-Check missing: $SKILL_DIR/$rel"
    missing=1
  fi
done
(( missing == 0 )) || exit 1

grep -q '^name: Linux-Security-Check$' "$SKILL_DIR/SKILL.md" \
  || { err "Linux-Security-Check SKILL.md has an unexpected name field"; exit 1; }
grep -q '^description: .*' "$SKILL_DIR/SKILL.md" \
  || { err "Linux-Security-Check SKILL.md is missing a description"; exit 1; }

if have_cmd python3; then
  python3 - "$SKILL_DIR" <<'PY'
import pathlib
import sys
for path in sorted(pathlib.Path(sys.argv[1]).glob("scripts/*.py")):
    compile(path.read_text(encoding="utf-8"), str(path), "exec")
PY
  ok "Linux-Security-Check scripts compile"
else
  warn "python3 not found; skipped Linux-Security-Check script syntax check"
fi

ok "Linux-Security-Check skill present and structurally valid (linked by opencode.sh)"
