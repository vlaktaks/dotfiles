# Changelog

## Unreleased

### Added
- Integrated **ble.sh** (Bash Line Editor, 0.4 devel) for interactive Bash syntax highlighting in `.bashrc` (TTY-only, graceful fallback when not installed; `--attach=none`/`ble-attach` ordering preserved alongside existing Omarchy/Starship/prompt-hook initialization).
- Added dotfiles-managed ble.sh configuration at `.config/blesh/init.sh` with restrained, theme-matched `ble-face` highlighting mapped to the active Rundfunk/Kitty palette (truecolor).
- Documented ble.sh installation options (AUR `blesh-git` or user-level `~/.local/share/blesh`), config linking, and integration notes in `README.md`.

### Changed
- Standardized directory-listing aliases in `.bashrc` to a single `eza` style (`--icons=always --group-directories-first`) for `ls`, `ll`, `la`, `l`, `lsa`, `lt`, `lta`, and the `code` shortcut, overriding mixed/inconsistent definitions and avoiding GNU `ls`/`eza` flag mixing.
