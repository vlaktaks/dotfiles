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
ln -sfn ~/.dotfiles/.config/lazygit/config.yml ~/.config/lazygit/config.yml

# Hyprland / Omarchy (Flea as default file manager)
ln -sf ~/.dotfiles/.config/hypr/bindings.lua ~/.config/hypr/bindings.lua
ln -sf ~/.dotfiles/.config/omarchy/shell.json ~/.config/omarchy/shell.json
ln -sf ~/.dotfiles/.config/mimeapps.list ~/.config/mimeapps.list
```

Additional files in `.config/` are included in this repository; link any others you use in the same way.

## Rundfunk-inspired motion effects

This repository includes a coordinated, restrained motion-effects setup for Kitty, Bash, and Neovim inspired by the Rundfunk palette (`#D6B45A` gold, cyan accents, red for errors where applicable).

### Kitty

- **Config:** `.config/kitty/kitty.conf`
- **Custom shader pipelines:** `.config/kitty/shaders/`
  - `bell-pulse.pipeline` / `bell-pulse.slang`: subtle gold feedback on terminal bell (`bell-in-window` event, short eased animation)
  - `focus-glow.pipeline` / `focus-glow.slang`: brief cyan accent on `os-window-focus-in` and `tab-change`
- **Shipped shader used:** `cursor-trail-motion-blur` (loaded via `custom_shaders` for smoother cursor trails)
- **Native cursor trail:** enabled with restrained `cursor_trail`, decay, start-threshold, and gold `cursor_trail_color`
- **Loading:** `custom_shaders` references pipeline/shader names resolved from Kitty's config `shaders/` directory (link the full `.config/kitty` directory as shown above so pipelines resolve correctly).
- **Requirements:** Kitty >= 0.49 for custom shaders/events used here (tested against Kitty 0.49.2).

### Bash

- **Config:** `.bashrc`
- **Behavior:** a lightweight `PROMPT_COMMAND` hook emits a single BEL after each executed command to trigger Kitty's bell feedback. The hook captures `$?` first, integrates without replacing existing prompt hooks, and skips the initial prompt to avoid startup bells.
- **Limitation:** a BEL event does not distinguish success from failure, so one subtle completion effect is used for all commands (chosen to avoid insecure or complex Kitty remote-control setup).

### Neovim

- **Plugin manager/config:** LazyVim + `lazy.nvim` (`.config/nvim/init.lua`, `.config/nvim/lua/config/lazy.lua`, plugin specs in `.config/nvim/lua/plugins/`)
- **Animations:** `nvim-mini/mini.animate` (`lua/plugins/mini-animate.lua`) for cursor movement, scrolling, window resize, and window open/close with short timings. Snacks animated scrolling remains disabled (`snacks-animated-scrolling-off.lua`) to avoid overlap.
- **Transient highlights:** `rachartier/tiny-glimmer.nvim` (`lua/plugins/tiny-glimmer.lua`) for yank, paste, undo, and redo with short Rundfunk-inspired gold/cyan fades.
- **Requirements:** Neovim 0.10+ recommended for `tiny-glimmer.nvim`; `mini.animate` requires a recent Neovim/LazyVim setup. Plugins install/load via the existing lazy.nvim configuration on next Neovim start.

### Notes

- Effects are event-driven/animated only while active (no background daemons, polling, or persistent CPU/GPU work when idle).
- No Kitty remote-control socket/network access or insecure permissions are enabled for these effects.
- Existing terminal/editor colors and configurations are preserved apart from the added motion-effect settings and plugin specs.




