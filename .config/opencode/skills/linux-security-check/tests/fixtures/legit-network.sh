#!/usr/bin/env bash
# Harmless fixture: legitimate, documented update check with checksum and signature verification.
# It downloads data files only; it never executes downloaded content.
set -euo pipefail

base="https://mirror.example.org/example-app"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

curl -fsS -o "$tmp/index.txt" "$base/index.txt"
curl -fsS -o "$tmp/index.txt.sig" "$base/index.txt.sig"
curl -fsS -o "$tmp/index.txt.sha256" "$base/index.txt.sha256"

(cd "$tmp" && sha256sum -c index.txt.sha256)
gpg --verify "$tmp/index.txt.sig" "$tmp/index.txt"
printf 'Verified update metadata at %s\n' "$tmp/index.txt"
