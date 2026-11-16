# dotfiles

Minimal personal dotfiles for Omarchy. Omarchy provides and manages its own default application/desktop/terminal/theme configuration; this repository keeps only personal Bash configuration and does not override general `.config` settings.

## Fresh install

### Clone

```bash
git clone https://github.com/vlaktaks/dotfiles.git ~/.dotfiles
```

### Activate Bash configuration

Back up an existing `~/.bashrc` if present, then create the symlink:

```bash
mv ~/.bashrc ~/.bashrc.bak  # if needed
ln -s ~/.dotfiles/.bashrc ~/.bashrc
```

The repository-managed `.bashrc` is the single source of truth for personal Bash configuration. It initializes the Omarchy environment when available, loads Omarchy's default Bash configuration when available, and preserves personal exports, aliases, and functions (it also remains usable outside Omarchy).

## Neovim

Neovim is used as the default editor with Omarchy's default configuration and behavior. The visible Neovim text size in a terminal is controlled by the terminal emulator (not by Neovim's own TUI configuration). The current appearance is **JetBrainsMono Nerd Font, size 9**, which matches Omarchy's default terminal font settings, so no personal Neovim/terminal override is required in this repository. If a minimal personal override is ever needed for this specific setting, it should be the only exception; otherwise all other Neovim behavior comes from Omarchy defaults.



