# Changelog

## Unreleased

### Added
- Integrated **ble.sh** (Bash Line Editor, 0.4 devel) for interactive Bash syntax highlighting in `.bashrc` (TTY-only, graceful fallback when not installed; `--attach=none`/`ble-attach` ordering preserved alongside existing Omarchy/Starship/prompt-hook initialization).
- Added dotfiles-managed ble.sh configuration at `.config/blesh/init.sh` with restrained, theme-matched `ble-face` highlighting mapped to the active Rundfunk/Kitty palette (truecolor).
- Documented ble.sh installation options (AUR `blesh-git` or user-level `~/.local/share/blesh`), config linking, and integration notes in `README.md`.

### Changed
- Standardized directory-listing aliases in `.bashrc` to a single `eza` style (`--icons=always --group-directories-first`) for `ls`, `ll`, `la`, `l`, `lsa`, `lt`, `lta`, and the `code` shortcut, overriding mixed/inconsistent definitions and avoiding GNU `ls`/`eza` flag mixing.
- Finalized directory listings to a compact icon-and-name-only `eza` style (no metadata/headers) for all listing aliases, removed long-format/tree metadata flags, and removed the custom `cd` function so `cd` uses Bash's builtin behavior without auto-listing.

### Fixed
- Restored the standard LazyVim dashboard/logo in Neovim by removing the Ryoku dashboard override, and fixed startup failures caused by a broken `plugins.theme` symlink/import path by removing the dangling theme module and disabling the unused Omarchy theme hot-reload hook.
