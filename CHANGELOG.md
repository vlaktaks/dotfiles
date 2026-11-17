# Changelog

## Unreleased

### Audited / Hardened
- Performed post-install audit of OpenCode/Ponytail/OmniRoute/Graphify/Addy Osmani integration files and installer behavior.
- Hardened `install/merge_opencode_config.mjs` to refuse overwriting existing invalid `opencode.json` (non-destructive safety).
- Improved verification coverage (`install/verify.sh`) for managed skill symlinks/integrity, single Ponytail plugin declaration, service state, and local secret-path hygiene checks.
- Made OmniRoute systemd unit generation/use portable (`/usr/bin/env omniroute serve --port ...`) and kept service non-enabled/non-started by default.
- Trimmed vendored `sources/` snapshots to curated subsets required for reproducibility/update of managed artifacts (removed unnecessary large upstream assets/worked examples/tests/docs where not needed), while preserving pinned commit manifests and required skill/plugin reference material.
- Documented runtime acceptance results: OmniRoute systemd start/stop and endpoint behavior (unauthenticated), Ponytail command/mode checks via `opencode run --standalone` (help/main/lite/debt/gain/ultra/off), and Graphify real code-only graph build/query in a disposable corpus; recorded remaining manual/authenticated and untested items (review/audit commands, full TUI, authenticated OmniRoute model/chat, clean-VM fresh install).


### Added
- Reproducible OpenCode integration managed through dotfiles, with idempotent installation scripts.
- Ponytail OpenCode integration (plugin, bundled skills exposure, and command support) with preserved existing OpenCode settings.
- OmniRoute installation/configuration scaffolding for OpenCode provider integration, with non-destructive config merge and secret-safe credential handling (env/private files, never committed).
- Graphify OpenCode skill integration (vendored from upstream) and dependency/setup guidance.
- Full Addy Osmani agent-skills collection installed as globally discoverable OpenCode skills (all upstream `skills/*` directories, including supplementary references).
- Global OpenCode `AGENTS.md` guidance for skill selection and usage.
- Upstream source manifests/pins and update workflow documentation for reproducible maintenance.
- Fresh Omarchy installation documentation and verification/troubleshooting guidance.

### Changed
- Expanded repository structure to include managed OpenCode config/skills, install scripts, and upstream source tracking.
