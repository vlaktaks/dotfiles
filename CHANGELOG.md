# Changelog

## Unreleased

### Added
- Added **Email MCP** (`sources/email-mcp/`, `install/email.sh`): an on-demand, manual-only OpenCode integration for Outlook and Proton Mail.
  - One stdlib-only Python MCP server (`~/.local/bin/email-mcp`) covering both accounts: list/newest/unread, keyword/sender/subject/date search, full message and thread reading, spam-folder listing, draft/reply drafting (thread metadata preserved), send, move to Spam/Trash/Archive, and permanent delete — each result labeled with its account.
  - Outlook via Microsoft Graph with delegated OAuth permissions and device-code login (personal Outlook.com or Microsoft 365; no client secret; incremental scopes: read-only by default, `--write` adds `Mail.ReadWrite`).
  - Proton Mail via the official Arch `extra` `protonmail-bridge` (signature-verified) over loopback IMAP/SMTP with Bridge-generated credentials and TLS pinned to the Bridge certificate.
  - Hard safety gates enforced in the server (`send_draft` needs `confirm:true`; `move_to_folder` needs `confirm:true` with exact ids/counts and a 100-message bulk cap; `delete_permanently` needs the literal string `PERMANENTLY DELETE`), plus OpenCode `ask` permissions on every write tool and `disabled: true` MCP config so OpenCode startup never touches email.
  - Secrets outside Git in `~/.config/opencode/secrets/` (0700 dir, 0600 files); `email-mcp login|status|revoke|selfcheck` CLI for setup, verification, and disconnection.
  - Extended `install/merge_opencode_config.mjs` with non-destructive union-merging of `mcp.servers` and append-merging of `permissions`; added email coverage to `install/verify.sh` (selfcheck, permissions hygiene, config entry, Bridge package/unit state, repo secret scan) and full documentation in `sources/email-mcp/README.md` plus README/CHANGELOG sections.
- Added **Ollama** integration: a non-destructive installer step (`install/ollama.sh`) that verifies a single maintainable Ollama installation (official installer, manual tarball, or pacman — never a second method), ensures the systemd unit and the `OLLAMA_CONTEXT_LENGTH=32768` drop-in, enables the service when possible, and idempotently creates the `inkling-2-mini:16k` Modelfile tag (16384-token context, GPU enabled) from a locally pulled base model without ever downloading model weights.
- Added Ollama verification coverage in `install/verify.sh` (client/server version match, localhost-only listener, systemd unit and enable state, context drop-in, model tag presence and `num_ctx`), and pinned Ollama v0.40.18 in `sources/manifests/upstream.json`.
- Added **Linux-Security-Check**, a read-only OpenCode skill for full Linux audits, malware/suspicious-file analysis, Omarchy plugin review, software supply-chain and installer checks, Arch/Omarchy update-risk assessment, and microphone/camera privacy investigations. Includes modular references, bounded stdlib-only helper scripts, a consistent severity report format, and harmless static fixtures/tests.
- Added installer validation for the security skill (`install/linux-security-check.sh`), verification coverage in `install/verify.sh`, and isolated-HOME installer regression tests.
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
