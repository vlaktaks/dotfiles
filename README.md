# dotfiles

Personal dotfiles repository (contents of `~/.dotfiles`).

**Defaults:** [Flea](https://github.com/thisisgm/flea) is configured as the default file manager (Hyprland keybindings, MIME handler for directories, and Omarchy shell dock pin). Nautilus is left installed.

## Clone or copy

Clone directly to `~/.dotfiles`:

```bash
git clone https://github.com/vlaktaks/dotfiles.git ~/.dotfiles
```

Or clone elsewhere and copy/symlink so the repository lives at `~/.dotfiles`.

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
mkdir -p ~/.config/lazygit ~/.config/hypr ~/.config/omarchy

ln -sfn ~/.dotfiles/.config/nvim ~/.config/nvim
ln -sfn ~/.dotfiles/.config/kitty ~/.config/kitty
ln -sfn ~/.dotfiles/.config/blesh ~/.config/blesh
ln -sfn ~/.dotfiles/.config/lazygit/config.yml ~/.config/lazygit/config.yml

# Hyprland / Omarchy (Flea as default file manager)
ln -sf ~/.dotfiles/.config/hypr/bindings.lua ~/.config/hypr/bindings.lua
ln -sf ~/.dotfiles/.config/omarchy/shell.json ~/.config/omarchy/shell.json
ln -sf ~/.dotfiles/.config/mimeapps.list ~/.config/mimeapps.list
```

Additional files in `.config/` are included in this repository; link any others you use in the same way.

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
- **Runtime note:** existing interactive shells must be restarted or run `source ~/.bashrc` to load hook changes.

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




