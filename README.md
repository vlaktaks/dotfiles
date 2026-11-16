# dotfiles

Personal dotfiles managed in this repository.

## Bash (Omarchy-aware)

This repository's `.bashrc` is intended to be the single source of truth for my personal Bash configuration while preserving Omarchy's own environment initialization and default Bash configuration.

### Fresh-install workflow

```bash
git clone https://github.com/vlaktaks/dotfiles.git ~/.dotfiles
ln -s ~/.dotfiles/.bashrc ~/.bashrc
```

If `~/.bashrc` already exists, back it up before replacing it with the symlink, for example:

```bash
mv ~/.bashrc ~/.bashrc.bak
```

The `.bashrc` will:

1. Source Omarchy's environment bootstrap when available (`/usr/share/omarchy/default/bash/env-bootstrap`), even for non-interactive shells.
2. Return early for non-interactive shells.
3. Load Omarchy's default Bash configuration when available (`$OMARCHY_PATH/default/bash/rc`) and remove Omarchy's `cd` alias.
4. Apply personal aliases, functions, and environment settings from this repository.
