# Changelog

## Unreleased

### Added
- Integrated **ble.sh** (Bash Line Editor, 0.4 devel) for interactive Bash syntax highlighting in `.bashrc` (TTY-only, graceful fallback when not installed; `--attach=none`/`ble-attach` ordering preserved alongside existing Omarchy/Starship/prompt-hook initialization).
- Added dotfiles-managed ble.sh configuration at `.config/blesh/init.sh` with restrained, theme-matched `ble-face` highlighting mapped to the active Rundfunk/Kitty palette (truecolor).
- Documented ble.sh installation options (AUR `blesh-git` or user-level `~/.local/share/blesh`), config linking, and integration notes in `README.md`.
- Reproducible OpenCode integration managed through dotfiles, with idempotent installation scripts.
- Ponytail OpenCode integration (plugin, bundled skills exposure, and command support) with preserved existing OpenCode settings.
- OmniRoute installation/configuration scaffolding for OpenCode provider integration, with non-destructive config merge and secret-safe credential handling (env/private files, never committed).
- Graphify OpenCode skill integration (vendored from upstream) and dependency/setup guidance.
- Full Addy Osmani agent-skills collection installed as globally discoverable OpenCode skills (all upstream `skills/*` directories, including supplementary references).
- Global OpenCode `AGENTS.md` guidance for skill selection and usage.
- Upstream source manifests/pins and update workflow documentation for reproducible maintenance.
- Fresh Omarchy installation documentation and verification/troubleshooting guidance.

### Changed
- Standardized directory-listing aliases in `.bashrc` to a single `eza` style (`--icons=always --group-directories-first`) for `ls`, `ll`, `la`, `l`, `lsa`, `lt`, `lta`, and the `code` shortcut, overriding mixed/inconsistent definitions and avoiding GNU `ls`/`eza` flag mixing.
- Finalized directory listings to a compact icon-and-name-only `eza` style (no metadata/headers) for all listing aliases, removed long-format/tree metadata flags, and removed the custom `cd` function so `cd` uses Bash's builtin behavior without auto-listing.
- Expanded repository structure to include managed OpenCode config/skills, install scripts, and upstream source tracking.

### Fixed
- Restored the standard LazyVim dashboard/logo in Neovim by removing the Ryoku dashboard override, and fixed startup failures caused by a broken `plugins.theme` symlink/import path by removing the dangling theme module and disabling the unused Omarchy theme hot-reload hook.

### Audited / Hardened
- Performed post-install audit of OpenCode/Ponytail/OmniRoute/Graphify/Addy Osmani integration files and installer behavior.
- Hardened `install/merge_opencode_config.mjs` to refuse overwriting existing invalid `opencode.json` (non-destructive safety).
- Improved verification coverage (`install/verify.sh`) for managed skill symlinks/integrity, single Ponytail plugin declaration, service state, and local secret-path hygiene checks.
- Made OmniRoute systemd unit generation/use portable (`/usr/bin/env omniroute serve --port ...`) and kept service non-enabled/non-started by default.
- Trimmed vendored `sources/` snapshots to curated subsets required for reproducibility/update of managed artifacts (removed unnecessary large upstream assets/worked examples/tests/docs where not needed), while preserving pinned commit manifests and required skill/plugin reference material.
- Documented runtime acceptance results: OmniRoute systemd start/stop and endpoint behavior (unauthenticated), Ponytail command/mode checks via `opencode run --standalone` (help/main/lite/debt/gain/ultra/off), and Graphify real code-only graph build/query in a disposable corpus; recorded remaining manual/authenticated and untested items (review/audit commands, full TUI, authenticated OmniRoute model/chat, clean-VM fresh install).
