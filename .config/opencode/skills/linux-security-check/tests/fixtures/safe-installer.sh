#!/usr/bin/env bash
# Harmless fixture: installs a user-local config file with no network or privilege use.
set -euo pipefail

src_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
dest="${XDG_CONFIG_HOME:-$HOME/.config}/example-app"

mkdir -p "$dest"
install -m 0644 "$src_dir/example.conf" "$dest/example.conf"
printf 'Installed example config to %s\n' "$dest"
