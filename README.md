# dotfiles

Personal Omarchy/Arch Linux dotfiles managed for reproducible setup (contents of `~/.dotfiles`), including shell/editor configuration and a native OpenCode integration for:

- **Ponytail** (lazy/scope-disciplined coding plugin + bundled skills/commands)
- **OmniRoute** (AI gateway/provider integration for OpenCode)
- **Ollama** (local model server: NVIDIA CUDA, localhost-only API, systemd startup, model-specific context tags)
- **Graphify** (knowledge-graph skill/integration)
- **Linux-Security-Check** (read-only Linux security, malware, Omarchy plugin, supply-chain, update, and privacy audits)
- **Addy Osmani agent skills** (complete upstream `skills/` collection, installed globally for OpenCode)
- **Email MCP** (on-demand Outlook via Microsoft Graph device-code OAuth, hard confirmation gates, disabled by default)

**Defaults:** [Flea](https://github.com/thisisgm/flea) is configured as the default file manager (Hyprland keybindings, MIME handler for directories, and Omarchy shell dock pin). Nautilus is left installed.

Repository: https://github.com/vlaktaks/dotfiles

## Fresh installation

On a fresh Omarchy (Arch-based) system:

```bash
git clone https://github.com/vlaktaks/dotfiles.git ~/.dotfiles
cd ~/.dotfiles
./install/install.sh
```

Or clone elsewhere and copy/symlink so the repository lives at `~/.dotfiles`, then run the installer from that repository path.

The installer is **idempotent** and safe to re-run. It:

1. Detects the environment (Arch/Omarchy expected) and checks core dependencies.
2. Ensures `~/.dotfiles` points to this repository when possible (without breaking an existing different setup).
3. Creates required directories (`~/.config/opencode`, skills/commands dirs, etc.).
4. Merges managed OpenCode configuration **non-destructively** (preserves existing providers/models/plugins/permissions/settings where present).
5. Links managed OpenCode instructions and skills from this repo into `~/.config/opencode`.
6. Validates the Linux-Security-Check skill structure and installs/configures Ponytail, OmniRoute, and Graphify integrations, and verifies the Ollama setup (best effort, with clear warnings when manual action is needed).
7. Installs the **Email MCP** server (`~/.local/bin/email-mcp`), creates the private secrets dir (`~/.config/opencode/secrets`, 0700), and merges the disabled-by-default `email-mcp` MCP server and its read-allow/write-ask permission rules into `opencode.json`.
8. Verifies key files/links and prints a summary.

> **Note:** Some steps may require network access (npm/PyPI/git upstreams) and may take time on first run. The installer avoids unnecessary `sudo` and does not install packages that are already present.

## Activate Bash configuration

If an existing `~/.bashrc` is present, back it up before replacing it with the symlink:

```bash
mv ~/.bashrc ~/.bashrc.bak
ln -s ~/.dotfiles/.bashrc ~/.bashrc
```

The repository-managed `.bashrc` loads Omarchy defaults when available and then applies my personal Bash configuration.

## Link configuration files

To match the current setup, link the following paths into `~/.config` (back up any existing targets first if needed):

```bash
mkdir -p ~/.config/kitty ~/.config/lazygit ~/.config/hypr ~/.config/omarchy

ln -sfn ~/.dotfiles/.config/nvim ~/.config/nvim
ln -sfn ~/.dotfiles/.config/kitty ~/.config/kitty
ln -sfn ~/.dotfiles/.config/blesh ~/.config/blesh
ln -sfn ~/.dotfiles/.config/lazygit/config.yml ~/.config/lazygit/config.yml

# Hyprland / Omarchy (Flea as default file manager)
ln -sf ~/.dotfiles/.config/hypr/bindings.lua ~/.config/hypr/bindings.lua
ln -sf ~/.dotfiles/.config/omarchy/shell.json ~/.config/omarchy/shell.json
ln -sf ~/.dotfiles/.config/mimeapps.list ~/.config/mimeapps.list

# Individual Kitty files (alternative to linking the whole directory)
# ln -sf ~/.dotfiles/.config/kitty/kitty.conf ~/.config/kitty/kitty.conf
# ln -sf ~/.dotfiles/.config/kitty/user.conf ~/.config/kitty/user.conf
# ln -sf ~/.dotfiles/.config/kitty/paste_handler.py ~/.config/kitty/paste_handler.py
```

Additional files in `.config/` are included in this repository; link any others you use in the same way. Adjust paths if your clone location differs; the OpenCode installer uses the repository path you run it from.

## Rundfunk-inspired motion effects

This repository includes a coordinated, restrained motion-effects setup for Kitty, Bash, and Neovim inspired by the Rundfunk palette (`#D6B45A` gold, cyan accents, red for errors where applicable).

> **Path note:** examples above use `~/.dotfiles`. Ensure `~/.dotfiles` (and your `~/.config/*` symlinks) point to the actual clone of this repository you intend to use; the active Kitty config must load `kitty.conf` and have the `shaders/` directory available from that config location.

### Kitty

- **Config:** `.config/kitty/kitty.conf`
- **Native cursor trail (text cursor):** enabled with restrained, visible settings and gold `cursor_trail_color` (`#D6B45A`). The trail follows the terminal text cursor (not the mouse pointer), so test it in apps that move the text cursor (e.g. Neovim or cursor movement in the shell).
- **Bell/visual feedback:** audio bell and visual bell flashes are disabled (`enable_audio_bell no`, `visual_bell_duration 0.0`, `visual_bell_color none`, `window_alert_on_bell no`) to avoid distracting full-window flashes (including on ordinary commands). BEL-based completion feedback is intentionally not emitted.
- **Custom shader pipelines (kept for compatible environments):** `.config/kitty/shaders/`
  - `bell-pulse.pipeline` / `bell-pulse.slang`: subtle gold feedback on `bell-in-window`
  - `focus-glow.pipeline` / `focus-glow.slang`: brief cyan accent on `os-window-focus-in` and `tab-change`
  - `cursor-trail-motion-blur` (shipped Kitty shader name) can be used for smoother cursor trails
- **Loading/activation:** custom `.slang` shaders require `shader-slang` (`slangc`) to compile. Because `slangc` may not be installed (and this repo does not install system packages), `custom_shaders` is commented out by default in `kitty.conf`. Uncomment the `custom_shaders` line when `slangc` is available to enable shader-based effects. Shader pipelines resolve from the Kitty config `shaders/` directory, so `~/.config/kitty` must expose both `kitty.conf` and `shaders/`.
- **Reload:** after config/symlink changes, reload Kitty config (`Ctrl+Shift+F5` by default, or `kitty @ load-config` if remote control is available) or restart Kitty windows to apply changes.

### Bash

- **Config:** `.bashrc`
- **Behavior:** a lightweight `PROMPT_COMMAND` hook remains integrated without replacing existing prompt hooks (captures `$?` first, skips the initial prompt, preserves exit status) but intentionally does **not** emit BEL, so ordinary command completion does not trigger visual-bell flashes.
- **Directory listings (eza, compact):** `ls`, `ll`, `l`, `la`, `lsa`, `lt`, `lta`, and the `code` shortcut use a single compact `eza` style with **Nerd Font icons only** and filenames (`--icons=always --group-directories-first`), with **no permissions/sizes/dates/owners/headers**. `ll` and `l` match `ls` (compact, not long format); `la`/`lsa` include hidden files; `lt`/`lta` are compact tree listings. Omarchy-provided eza aliases are overridden in `~/.bashrc` to keep one authoritative style (no mixed GNU `ls`/`eza` flags). Colors follow terminal/`eza` defaults for the active theme. No custom `cd` function is defined (Bash's builtin `cd` behavior is preserved; changing directories does not auto-list contents).
- **Dependency:** `eza` (installed via the system package manager, e.g. on Arch/Omarchy). If `eza` is unavailable, `.bashrc` falls back to GNU `ls`-based aliases.
- **Runtime note:** existing interactive shells must be restarted or run `source ~/.bashrc` to load changes.

### ble.sh (Bash syntax highlighting)

- **Program (outside repo):** [ble.sh](https://github.com/akinomyoga/ble.sh) (Bash Line Editor) provides interactive command-line syntax highlighting and line-editing enhancements.
- **Version/selection:** use a maintained ble.sh 0.4 devel/nightly build (not the outdated stable 0.3.4 release). In this environment, `blesh-git` 0.4.0-devel4+15294275 was installed to `~/.local/share/blesh` (user-level). Upstream currently distributes 0.4 as devel/nightly builds.
- **Install (reproducible):**
  - **Arch/AUR (preferred on Omarchy):** install `blesh-git` via an AUR helper, e.g. `yay -S blesh-git` (or `paru -S blesh-git`). This installs ble.sh to `/usr/share/blesh/ble.sh` (package-managed, outside this repo). Review the AUR package/build before installing.
  - **User-level (no root required):** install to `~/.local/share/blesh/ble.sh` (outside this repo), e.g. from the upstream nightly tarball as documented by ble.sh:
    - `curl -L https://github.com/akinomyoga/ble.sh/releases/download/nightly/ble-nightly.tar.xz | tar xJf -`
    - `bash ble-nightly/ble.sh --install ~/.local/share`
- **Repository config (authoritative):** `.config/blesh/init.sh` (theme-matched `ble-face` settings). Link `~/.config/blesh` to this dotfiles config as shown above; `.bashrc` passes it to ble.sh via `--rcfile` when available.
- **Bash integration:** `.bashrc` sources ble.sh for interactive Bash sessions only (checks TTY and readable install paths: `/usr/share/blesh/ble.sh`, `${XDG_DATA_HOME:-~/.local/share}/blesh/ble.sh`) with `--attach=none` early in interactive startup and `ble-attach` at the very end. Missing installations are skipped gracefully without breaking Bash startup. Existing Omarchy/Starship initialization, `PROMPT_COMMAND` hooks/order, exit-status handling, aliases/functions/PATH/completions, and non-BEL terminal behavior are preserved. Inline auto-suggestions are disabled (`complete_auto_complete=`) to keep input clean; syntax highlighting is the primary feature.
- **Palette (mapped to active Kitty/Rundfunk theme):** faces in `.config/blesh/init.sh` use the active theme colors as source of truth (e.g. fg `#d7dde8`, bg `#101216`, muted `#3a4352`/`#8b98aa`, cyan/blue accents `#59d9e6`/`#56e6d8`, green strings/valid files `#7ee787`, yellow vars `#ffd479`, magenta keywords/escapes `#ff6ac1`, red errors/invalid `#ff5c7a`, gold functions `#d6b45a`) with restrained, readable styling (no bright full-background error flashes). Actual on-screen colors/rendering require interactive Kitty verification.

### Neovim

- **Plugin manager/config:** LazyVim + `lazy.nvim` (`.config/nvim/init.lua`, `.config/nvim/lua/config/lazy.lua`, plugin specs in `.config/nvim/lua/plugins/`)
- **Animations:** `nvim-mini/mini.animate` (`lua/plugins/mini-animate.lua`, `opts` as a function to avoid premature `require`) for cursor movement, scrolling, window resize, and window open/close with short timings. Snacks animated scrolling remains disabled (`snacks-animated-scrolling-off.lua`) to avoid overlap.
- **Transient highlights:** `rachartier/tiny-glimmer.nvim` (`lua/plugins/tiny-glimmer.lua`) for yank, paste, undo, and redo with short Rundfunk-inspired gold/cyan fades.
- **Requirements:** Neovim 0.10+ recommended for `tiny-glimmer.nvim`; `mini.animate` requires a recent Neovim/LazyVim setup. Plugins install/load via the existing lazy.nvim configuration (e.g. install missing plugins on startup or via Lazy).

### Notes

- Effects are event-driven/animated only while active (no background daemons, polling, or persistent CPU/GPU work when idle).
- No Kitty remote-control socket/network access or insecure permissions are enabled for these effects.
- Existing terminal/editor colors and configurations are preserved apart from the added motion-effect settings and plugin specs.

## OpenCode integration (native/global)

Managed via `./install/install.sh` (idempotent, non-destructive merge of existing OpenCode configuration).

### What gets installed

#### OpenCode (managed config/skills)
- **Config:** managed merge into `~/.config/opencode/opencode.json` (keeps `update` behavior and existing settings; adds required plugin/provider entries without deleting others).
- **Global instructions:** `~/.config/opencode/AGENTS.md` symlinked to `.config/opencode/AGENTS.md` in this repo.
- **Global skills:** each managed skill directory in `.config/opencode/skills/` is symlinked into `~/.config/opencode/skills/<skill-name>/` so OpenCode can discover them in all projects.
- **Secrets/local state:** files like `~/.config/opencode/service.json` remain local and untracked.

#### Ponytail
- **Upstream:** https://github.com/DietrichGebert/ponytail (pinned in `sources/manifests/upstream.json`; curated source snapshot in `sources/ponytail/` for skills/plugin-reference reproducibility)
- **Plugin:** `@dietrichgebert/ponytail` declared in OpenCode `plugins` (OpenCode v2 config key) and installed globally via npm when possible.
- **Bundled skills exposed:** `ponytail`, `ponytail-review`, `ponytail-audit`, `ponytail-debt`, `ponytail-gain`, `ponytail-help` (symlinked from dotfiles-managed skills).
- **Commands/modes:** provided by the Ponytail OpenCode plugin (`/ponytail`, `/ponytail-review`, `/ponytail-audit`, `/ponytail-debt`, `/ponytail-gain`, `/ponytail-help`, modes including lite/full/ultra/off per upstream). Verify inside OpenCode after installation/restart.

#### OmniRoute
- **Upstream:** https://github.com/cheaper-inference/OmniRoute (pinned in manifest; npm package `omniroute`)
- **Installation:** global npm package `omniroute` (when npm is available).
- **OpenCode provider integration:** adds a non-destructive `provider.omniroute` entry in `~/.config/opencode/opencode.json` (OpenAI-compatible provider via `@ai-sdk/openai-compatible`, default local base URL `http://localhost:20128/v1`, placeholder API key `sk_omniroute` for local setups). Existing providers and model choices are preserved.
- **Service:** creates `~/.config/systemd/user/omniroute.service` if missing (portable `ExecStart`, not auto-enabled/started by default). Manage with:
  - `systemctl --user daemon-reload`
  - `systemctl --user start omniroute`
  - `systemctl --user enable omniroute` (to start automatically, when appropriate)
  - `systemctl --user status omniroute`
  - logs via `journalctl --user -u omniroute -f`

#### Ollama

- **Upstream:** https://github.com/ollama/ollama (pinned in `sources/manifests/upstream.json`; latest stable at pin time: v0.40.18)
- **Installation:** the installer verifies a **single** existing installation (official `install.sh`, manual tarball into `/usr/bin`, or the Arch `ollama` package) and never adds a second method or overwrites an existing unit. On a fresh system, install Ollama first with exactly one method (requires sudo), then re-run the dotfiles installer:
  - official installer (recommended, creates the `ollama` user, unit, and `/usr/share/ollama` model store): `curl -fsSL https://ollama.com/install.sh | sh`
  - manual tarball: `curl -L https://ollama.com/download/ollama-linux-amd64.tgz | sudo tar -C / -xz`
  - or `sudo pacman -S ollama` when the packaged version is acceptable
- **Service:** system unit (`/etc/systemd/system/ollama.service` or the package-shipped unit) plus a drop-in that sets `OLLAMA_CONTEXT_LENGTH=32768` as the global default context. The API stays bound to `127.0.0.1:11434`. The installer enables the service when possible (`systemctl enable ollama`).
- **CUDA:** NVIDIA acceleration is used automatically when an NVIDIA GPU is present; nothing is forced to CPU or disabled.
- **Model-specific context (Modelfile tags):** OpenCode sends no `num_ctx`, so Ollama resolves the context from the model's `PARAMETER num_ctx` (Modelfile) or the global default. `inkling-2-mini:16k` pins Inkling 2 Mini to 16384 tokens — a 26B model with a vision projector needs that headroom on a 12 GB GPU (its default/32K does not fit) — while `qwen3.8:27b` keeps the 32768 global default with no tag.
- **Model downloads are optional and manual** (~18 GB each); the installer never downloads model weights silently:
  - `ollama pull inkling-2-mini`, then re-run `./install/install.sh` (it creates the `inkling-2-mini:16k` tag automatically) — or manually: `ollama create inkling-2-mini:16k -f -` with a Modelfile containing `FROM inkling-2-mini:latest` and `PARAMETER num_ctx 16384`
  - `ollama pull qwen3.8:27b`
- **OpenCode discovery:** OpenCode probes `http://127.0.0.1:11434`, discovers completion-capable models, and lists them as `ollama/*` in `/models`; no provider entry or key is required.

#### Graphify
- **Upstream:** https://github.com/Graphify-Labs/graphify (pinned in manifest; curated source snapshot in `sources/graphify/` containing OpenCode skill sources + metadata)
- **OpenCode skill:** `graphify` skill (OpenCode variant, including `references/`) installed globally under `~/.config/opencode/skills/graphify/` via symlink from this repo.
- **CLI/dependencies:** installer attempts to install `graphifyy` (CLI name `graphify`) using `uv tool`, `pipx`, or `python3 -m pip --user` when available. Graphify requires Python 3.10+; use in projects as documented by upstream (`/graphify ...` workflows / `graphify` CLI) after dependencies are satisfied.

#### Linux-Security-Check (security auditing skill)
- **Standalone distribution:** https://github.com/vlaktaks/omarchy-security-skill (same functional skill; the dotfiles copy remains the authoritative source and installer-managed installation).
- **Location:** `.config/opencode/skills/linux-security-check/` (linked globally as `~/.config/opencode/skills/linux-security-check/`).
- **Purpose:** read-only, evidence-based audits of Linux systems, suspicious files/scripts, Omarchy plugins, software installers/supply chains, Arch/Omarchy update risk, and microphone/camera privacy.
- **Modes:** full system audit; malware/suspicious file analysis; Omarchy plugin audit; general software installation review (GitHub/GitLab, Arch, AUR, AppImage, Python, npm, archives); update safety assessment; privacy/microphone/camera investigation.
- **Default behavior:** **read-only**. It never deletes, kills, disables, installs, updates, quarantines, or executes untrusted samples. Remediation is recommended and requires explicit approval. It does not create daemons, timers, or background scans.
- **Reports:** uses 🟢 PASS, 🟡 WARNING, 🔴 CRITICAL/HIGH, and ⚪ UNKNOWN with textual labels; color is optional, respects `NO_COLOR`, and is never emitted in Markdown. Findings include evidence, location, impact, confidence, and recommended action.
- **Supporting scripts:** `scripts/scan-patterns.py` (bounded static pattern triage), `scripts/check-omarchy-manifest.py` (manifest/layout validation without activation), and `scripts/report.py` (consistent report rendering). All are stdlib-only and read-only.
- **Optional tools:** ClamAV/YARA, `arch-audit`, `checkupdates`, `namcap`, `shellcheck`, `qmllint`, `readelf`, `getcap`, `ss`, `lsof`, `pw-dump`, `wpctl`, `pactl`. Absence is a coverage limitation, not a failure; no scanner is mandatory.
- **Limitations:** no scanner proves safety; marketplace verification is exact-commit static baseline checking, not a security audit; TLS/encrypted payloads, packed binaries, privileged/other-user processes, and runtime behavior may be unobservable; version/CVE matches require applicability checks.
- **Tests:** `tests/run-all.sh` (scanner/report/manifest fixtures plus isolated-HOME installer regression). Never executes harmful fixtures.

Example prompts:

```text
Run a security audit on my Linux machine.
Check this file and directory for malware: ~/Downloads/example
Is this Omarchy plugin safe to install? https://github.com/owner/plugin
Can I safely install this AUR package? <package>
Is it safe to update Hyprland/Quickshell/NVIDIA right now?
Check whether my microphone is being used or sending information somewhere.
```

#### Addy Osmani agent skills (complete collection)
- **Upstream:** https://github.com/addyosmani/agent-skills (pinned in manifest; curated snapshot in `sources/addyosmani-agent-skills/skills/*` + markers)
- **Scope:** **all** directories from upstream `skills/` are copied into `.config/opencode/skills/<skill-name>/` in this repo and linked globally for OpenCode.
- **Structure:** original per-skill directory structure is preserved, including each `SKILL.md` and any supplementary `references/` or other bundled resources.
- **Not installed globally:** upstream repo-contributor root `AGENTS.md`/`CLAUDE.md` are **not** copied into global OpenCode config; this repo provides its own managed global `AGENTS.md`.

## Repository structure

```text
.
├── .bashrc
├── .config/
│   ├── blesh/ kitty/ lazygit/ nvim/ hypr/ omarchy/ mimeapps.list  # dotfiles configs
│   └── opencode/
│       ├── opencode.json        # managed base config (merged non-destructively)
│       ├── AGENTS.md            # managed global OpenCode instructions
│       ├── skills/              # managed global skills (Addy Osmani + Ponytail + Graphify + Linux-Security-Check)
│       └── commands/            # managed OpenCode commands (if any)
├── install/
│   ├── install.sh               # one-command entry point
│   ├── lib.sh                   # shared helpers
│   ├── merge_opencode_config.mjs# safe JSON merge for opencode.json
│   ├── opencode.sh              # link/merge OpenCode config & skills
│   ├── linux-security-check.sh  # validate security skill structure
│   ├── ponytail.sh              # Ponytail integration
│   ├── omniroute.sh             # OmniRoute install/config/service template
│   ├── graphify.sh              # Graphify skill/CLI setup
│   ├── agent-skills.sh          # completeness checks for Addy Osmani skills
│   ├── ollama.sh                # Ollama install verification + context tag setup
│   ├── verify.sh                # post-install verification
│   └── omniroute.env.example    # example private env file (no secrets)
├── sources/
│   ├── manifests/upstream.json  # upstream repos/commits/versions
│   ├── ponytail/                # vendored upstream snapshot (pinned)
│   ├── graphify/                # vendored upstream snapshot (pinned)
│   └── addyosmani-agent-skills/ # vendored upstream skills snapshot (pinned)
├── .gitignore
├── CHANGELOG.md
└── README.md
```

(Existing config areas not listed above are preserved; this repo extends the existing layout without replacing unrelated files.)

## How OpenCode discovers skills and config

- **Global config:** `~/.config/opencode/opencode.json` (merged by installer; never blindly replaced).
- **Global instructions:** `~/.config/opencode/AGENTS.md` (symlinked from this repo).
- **Global skills:** `~/.config/opencode/skills/<skill-name>/SKILL.md` (each managed skill directory symlinked from `.config/opencode/skills/` in this repo). OpenCode also supports compatible paths (`~/.claude/skills`, `~/.agents/skills`), but this setup uses the native OpenCode global path.
- **Plugins:** declared in `opencode.json` under `plugins` (OpenCode v2). Ponytail is added non-destructively.

Skills are available in **all projects** once linked globally.

## OmniRoute credentials (do this after install)

**Never commit credentials or API keys to Git.** Do not put secrets in tracked dotfiles, and do not paste them into logs.

1. Create a private env file (example template provided):
   ```bash
   mkdir -p ~/.config/omniroute
   cp ~/.dotfiles/install/omniroute.env.example ~/.config/omniroute/omniroute.env
   chmod 600 ~/.config/omniroute/omniroute.env
   $EDITOR ~/.config/omniroute/omniroute.env
   ```
2. Configure provider credentials/keys as required by your OmniRoute setup (only for providers you use; review provider terms).
3. If using the systemd user service, uncomment/add `EnvironmentFile=%h/.config/omniroute/omniroute.env` in `~/.config/systemd/user/omniroute.service`, then:
   ```bash
   systemctl --user daemon-reload
   systemctl --user restart omniroute
   ```
4. For OpenCode provider auth, the installer seeds `provider.omniroute.options.apiKey` with a local placeholder (`sk_omniroute`) **only if the provider entry is newly added**. If your OmniRoute deployment requires a real OmniRoute API key, update it locally (do not commit) or configure via environment as appropriate for your workflow.

The installer and repo are designed so secrets remain outside Git (`.gitignore` excludes common secret patterns and OpenCode service/config secret files).

## Email integration (Outlook, manual-only)

On-demand Outlook access for OpenCode through one small, stdlib-only MCP server (`~/.local/bin/email-mcp`, source in `sources/email-mcp/`). It is **disabled by default**: OpenCode startup never touches email. Connect it via `/mcps` when you want to work with mail.

- **Microsoft Graph**, delegated permissions, device-code login. You never enter your Microsoft password outside Microsoft's own sign-in page.
- Scopes are incremental: `email-mcp login outlook` requests read access (`Mail.Read`); `email-mcp login outlook --write` adds `Mail.ReadWrite Mail.Send` for drafting/sending/moving/deleting.

Hard safety gates are enforced in the server (`send_draft` needs `confirm: true` after you see the full draft; `move_to_folder` needs `confirm: true` with exact ids/counts; `delete_permanently` needs the literal string `PERMANENTLY DELETE`), and OpenCode `ask` permissions make every write tool prompt you with its exact arguments.

Full setup, examples, and troubleshooting: `sources/email-mcp/README.md`. One-time steps after install:

```bash
email-mcp login outlook                     # device-code login (create a free Azure app registration first, see doc)
email-mcp login outlook --write             # once, when you want draft/send/move/delete access
```

Secrets live in `~/.config/opencode/secrets/` (0700/0600), outside Git. Disconnect any time with `email-mcp revoke outlook` plus the Microsoft consent page.

## Updating upstream tools and skills

Upstream sources and installed versions are recorded in `sources/manifests/upstream.json`. `sources/` contains **curated, pinned snapshots** of only the upstream material needed to reproduce/update managed artifacts (not full upstream repos/worked examples/tests/assets).

Recommended update flow (manual, intentional):
1. Review upstream changes/releases for Ponytail, OmniRoute, Graphify, and addyosmani/agent-skills.
2. Refresh vendored snapshots at a chosen commit/tag:
   - Refresh the relevant curated snapshot under `sources/ponytail/`, `sources/graphify/`, and/or `sources/addyosmani-agent-skills/` and update `sources/manifests/upstream.json` (commit/version). Keep snapshots intentional (avoid vendoring unnecessary upstream build artifacts, large worked examples, or unrelated platform assets).
   - For Addy Osmani skills, re-copy **all** `skills/*` directories into `.config/opencode/skills/` preserving full directory contents; keep local naming/structure consistent.
   - For Graphify, refresh `.config/opencode/skills/graphify/` from the upstream OpenCode skill variant and its `references/`.
   - For Ponytail bundled skills, refresh the `ponytail*` skill directories if upstream changed them.
3. Update package/tool versions as appropriate (e.g. `npm install -g @dietrichgebert/ponytail omniroute`, `uv tool install --upgrade graphifyy`) and record versions in docs/manifest.
4. Re-run `./install/install.sh` (idempotent) and verify.
5. Commit the updated vendored content, manifests, and docs. Do not commit secrets or machine-local state.

Avoid deleting or overwriting unrelated local customizations; resolve overlaps deliberately and document intended use when skills overlap.

## Verification

After installation (and after restarting OpenCode if it was running):

The installer/verification perform **configuration and static/runtime-precondition checks** (JSON merge safety, idempotence in temp fixtures, symlinks, skill integrity, plugin/package presence, CLI availability, service unit presence). Some behaviors require interactive or authenticated runtime checks (see "Requires manual action" / troubleshooting):

```bash
./install/verify.sh "$(pwd)"   # from repo root
opencode --version
node -e "JSON.parse(require('fs').readFileSync(process.env.HOME+'/.config/opencode/opencode.json','utf8')); console.log('ok')"
ls ~/.config/opencode/skills | wc -l
test -f ~/.config/opencode/skills/linux-security-check/SKILL.md && echo "linux-security-check discoverable"
python3 -c "compile(open('$HOME/.config/opencode/skills/linux-security-check/scripts/scan-patterns.py').read(),'scan','exec'); print('scan script parses')"
bash .config/opencode/skills/linux-security-check/tests/run-all.sh   # from repo root
omniroute --help 2>/dev/null || echo "omniroute not on PATH"
graphify --help 2>/dev/null || echo "graphify not on PATH"
systemctl --user status omniroute --no-pager || true
~/.local/bin/email-mcp selfcheck                 # gates/builders/parsing (offline)
~/.local/bin/email-mcp status                    # account state, no secrets
ls -la ~/.config/opencode/secrets                # 0700 dir, 0600 files (created after first login)
```

In OpenCode, confirm:
- Ponytail plugin loads and `/ponytail`, `/ponytail-review`, `/ponytail-audit`, `/ponytail-debt`, `/ponytail-gain`, `/ponytail-help` are available.
- Skills (including `ponytail`, `graphify`, `linux-security-check`, and Addy Osmani skills like `spec-driven-development`) are discoverable.
- Existing providers remain configured; OmniRoute provider appears if added.
- No configuration parse errors.

If OmniRoute is running locally: check `http://127.0.0.1:20128/` or `http://127.0.0.1:20128/v1/models` (depending on deployment/auth) and ensure models are visible in OpenCode as configured.

For email: connect `email-mcp` in `/mcps`, then try "Show my 10 newest emails." (read-only). All write operations will prompt for approval; nothing is ever sent or moved without it.

## Audit notes (current environment)

- **Verified in this environment:** OpenCode config merge is non-destructive and refuses to overwrite invalid JSON; installer idempotence tested in isolated temp `HOME` fixtures; all 33 managed skills present with `SKILL.md` and linked globally; Ponytail npm plugin installed and listed by `opencode plugin list`; OmniRoute and Graphify CLIs installed and respond to `--help`; `~/.config/systemd/user/omniroute.service` present (currently enabled/active in this environment; verification warns about the opt-in state).
- **Runtime-tested:**
  - **OmniRoute (systemd, temporary):** `systemctl --user start/stop omniroute` succeeded using the actual user unit; executable resolved in systemd environment (mise shim on systemd PATH), service became `active (running)` on port 20128, `GET /` returned `307 -> /dashboard`, `GET /v1/models` returned `401 Authentication required` with placeholder key/default state; service stopped cleanly and remained `disabled`/`inactive`.
  - **Ponytail (OpenCode CLI session, disposable project):** `opencode run --standalone` successfully loaded/executed `ponytail-help`, `ponytail`, `/ponytail lite`, `/ponytail-debt` (scanned/produced ledger), `/ponytail-gain`, `/ponytail ultra`, and `/ponytail off` with expected behavior/responses. `/ponytail-review` and `/ponytail-audit` were not explicitly exercised in this pass.
  - **Graphify (disposable corpus):** `graphify update` on a code-only temp corpus (no LLM key required) produced `graphify-out/graph.json`, `graph.html`, and `GRAPH_REPORT.md` (8 nodes, 10 edges); `graphify query` and `graphify explain` returned results referencing test-corpus entities. Temp artifacts were removed.
  - **Linux-Security-Check (OpenCode CLI, read-only):** `opencode run --standalone` loaded the skill by exact ID `linux-security-check` and completed a user-systemd/basic-posture audit with evidence and explicit limitations; no system changes were made. It reported a WARNING for the local OmniRoute listener bound to `0.0.0.0:20128` (firewall/auth unverified), which remains unremediated.
  - **Ollama (local, NVIDIA RTX 5070 12 GB):** single installation at `/usr/bin/ollama` v0.40.18 (client and server match; latest stable at audit time), systemd unit enabled/active, API on `127.0.0.1:11434`, `OLLAMA_CONTEXT_LENGTH=32768` drop-in; CUDA v13 backend loads; `inkling-2-mini:16k` (num_ctx 16384) and `qwen3.8:27b` (32768) inference verified with correct outputs and GPU offload (~9.4 GB / ~7.9 GB VRAM); OpenCode runs `ollama/inkling-2-mini:16k` end-to-end including the WebFetch tool; a captured request confirmed OpenCode sends no `num_ctx`, so the Modelfile `PARAMETER num_ctx` takes effect.
  - **Email MCP (Outlook):** `email-mcp selfcheck` passes (hard gates for send/move/bulk-cap/permanent-delete, Outlook-only tool schemas, date/address/HTML builders, a mocked Microsoft Graph backend covering list/search/read/thread/draft/reply/send/move/permanent-delete, and OAuth token refresh/expiry logic — all offline); a raw MCP stdio handshake verified `initialize`, `tools/list` (11 tools) and gate rejections (`send_draft` without `confirm:true`, `delete_permanently` with a wrong confirmation); config merge for `mcp.servers`/`permissions` is non-destructive and idempotent (tested on temp fixtures). Live mailbox tests were **not** performed (see below). Proton Mail support was **removed** after evaluation (Bridge requires a paid Proton plan); see the CHANGELOG.
- **Configured but not fully runtime-verified:** Ponytail behavior in an interactive OpenCode TUI session and explicit `/ponytail-review`/`/ponytail-audit` runs; OmniRoute authenticated model discovery (`/v1/models` with valid key), `auto`/catalog correctness for configured providers, chat completions, and OpenCode provider connectivity against a fully configured gateway.
- **Email MCP manual/authenticated steps (not yet done):** live read/write mailbox tests against the signed-in Outlook account (read login completed: `Mail.Read` + identity scopes; write scopes `Mail.ReadWrite Mail.Send` require one opt-in `email-mcp login outlook --write` consent). Until live tests run, the integration is mock/configuration-validated only.
- **Not tested:** complete fresh Omarchy reinstall end-to-end in a clean VM/image.

## Troubleshooting

- **Installer says `~/.dotfiles` points elsewhere:** this is intentional to avoid breaking an existing setup. Run the installer from the desired repo path; symlinks created by the installer target that repo.
- **OpenCode config parse errors:** restore from a backup created by the installer (if any) or inspect `~/.config/opencode/opencode.json` for JSON syntax issues; re-run merge after fixing.
- **Plugin/commands not visible:** restart OpenCode, ensure `plugins` includes `@dietrichgebert/ponytail` in `~/.config/opencode/opencode.json`, and verify the package is installed/resolvable.
- **`graphify` command missing:** install via `uv tool install graphifyy` (recommended on externally managed Python) or pipx/pip, ensure it is on `PATH`, then restart shell/OpenCode.
- **OmniRoute not reachable:** start the service (`systemctl --user start omniroute`), check `journalctl --user -u omniroute`, confirm port/base URL, and configure credentials if required.
- **Ollama CUDA out-of-memory (`llama-server startup failed after projector CPU offload retry: CUDA error: out of memory`):** a vision model with too large a context does not fit in GPU memory. Use the `inkling-2-mini:16k` tag in OpenCode (or pass `num_ctx` explicitly in direct API requests) and do not load two large models at once; the global `OLLAMA_CONTEXT_LENGTH` must stay at 32768 for `qwen3.8:27b`.
- **Ollama tag missing / model not pulled:** run `ollama pull <model>` first (large download, optional), then re-run `./install/install.sh`; the installer creates the `inkling-2-mini:16k` tag from the pulled base model. Verify with `ollama list` and `curl -fsS http://localhost:11434/api/show -d '{"model":"inkling-2-mini:16k"}'`.
- **Skill not discovered:** ensure `~/.config/opencode/skills/<name>/SKILL.md` exists and is readable (symlink target present).
- **Email tools not visible in OpenCode:** connect the `email-mcp` server in `/mcps` (it is intentionally disabled by default). `email-mcp status` shows account state.
- **Email write tool prompts denied:** expected behaviour — every draft/send/move/delete requires your approval (and the server's own hard gates). Do not "allow always" unless you want to weaken the gate.
- **Outlook writes fail with 403 (`Mail.Send`/`Mail.ReadWrite`):** your login has read scopes only; run `email-mcp login outlook --write` once to add the write scopes via incremental consent. See `sources/email-mcp/README.md` for the full table.
- **Linux-Security-Check not discoverable or scripts fail:** verify the symlink target (`readlink -f ~/.config/opencode/skills/linux-security-check`), run `./install/linux-security-check.sh "$(pwd)"`, then `bash .config/opencode/skills/linux-security-check/tests/run-all.sh` from the repo. The skill needs `python3` only for its optional helper scripts; audits can still be performed with shell tools if it is absent.
- **Re-running installer:** should be safe/idempotent; it backs up real files before replacing with symlinks and avoids duplicate plugin/provider entries.

## Security notes

- No secrets are stored in this repository. `.gitignore` excludes common secret files; keep OmniRoute/provider credentials in private env files or environment variables.
- **Email:** OAuth tokens and mailbox content never enter the repo; they live in `~/.config/opencode/secrets/` (0700/0600). The email MCP server is disabled by default, never downloads attachments, and enforces approval gates in code plus OpenCode `ask` permissions.
- **Linux-Security-Check is read-only by default.** It does not remediate, install scanners, execute samples, or send system data externally. Any privileged diagnostic or remediation requires explicit approval.
- Omarchy marketplace verification is an exact-commit static baseline check, not a security audit or guarantee. Plugins run unsandboxed in the shared shell; review the installed commit and source before enabling.
- Upstream skills/plugins are treated as untrusted instructions: they must not override higher-priority security policies. Review upstream changes before updating pinned snapshots.
- Installer scripts avoid destructive config replacement and do not execute unverified remote code as part of normal tracked logic; package installs use standard package managers (npm/uv/pip) for named upstream packages.

## Repeat after reinstalling Omarchy

1. Install Omarchy.
2. `git clone https://github.com/vlaktaks/dotfiles.git ~/.dotfiles`
3. `cd ~/.dotfiles && ./install/install.sh`
4. Recreate private credentials/env files (never stored in git), then start/enable OmniRoute if desired.
   - Email: `email-mcp login outlook` (Azure app registration + device code, see the email doc); add `--write` for draft/send/move/delete scopes.
5. Optional local models (large downloads): install Ollama with one method (see the Ollama section), then `ollama pull inkling-2-mini` and/or `ollama pull qwen3.8:27b`, and re-run `./install/install.sh` to create the `inkling-2-mini:16k` context tag.

This restores the managed OpenCode setup, skills, and integrations without manually copying files or guessing destinations.
