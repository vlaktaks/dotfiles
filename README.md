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
mkdir -p ~/.config/kitty ~/.config/lazygit ~/.config/hypr ~/.config/omarchy

ln -sfn ~/.dotfiles/.config/nvim ~/.config/nvim
ln -sfn ~/.dotfiles/.config/lazygit/config.yml ~/.config/lazygit/config.yml

ln -sf ~/.dotfiles/.config/kitty/kitty.conf ~/.config/kitty/kitty.conf
ln -sf ~/.dotfiles/.config/kitty/user.conf ~/.config/kitty/user.conf
ln -sf ~/.dotfiles/.config/kitty/paste_handler.py ~/.config/kitty/paste_handler.py

# Hyprland / Omarchy (Flea as default file manager)
ln -sf ~/.dotfiles/.config/hypr/bindings.lua ~/.config/hypr/bindings.lua
ln -sf ~/.dotfiles/.config/omarchy/shell.json ~/.config/omarchy/shell.json
ln -sf ~/.dotfiles/.config/mimeapps.list ~/.config/mimeapps.list
```

Additional files in `.config/` are included in this repository; link any others you use in the same way.




