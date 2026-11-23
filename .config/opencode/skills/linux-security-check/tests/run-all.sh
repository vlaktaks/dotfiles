#!/usr/bin/env bash
# Run all Linux-Security-Check tests. Read-only; uses isolated temp HOME for install tests.
set -euo pipefail

SKILL_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SKILL_DIR"

echo "== Python unit tests =="
python3 -m unittest discover -s tests -p 'test_*.py' -v

echo
echo "== Installer regression (isolated HOME) =="
bash tests/test-install.sh

echo
echo "All Linux-Security-Check tests passed."
