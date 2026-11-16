# dotfiles

Personal dotfiles for Omarchy Bash configuration.

## Clone

```bash
git clone https://github.com/vlaktaks/dotfiles.git ~/.dotfiles
```

## Activate Bash configuration

If an existing `~/.bashrc` is present, back it up before replacing it with the symlink, then create the symlink:

```bash
mv ~/.bashrc ~/.bashrc.bak
ln -s ~/.dotfiles/.bashrc ~/.bashrc
```

The repository-managed `.bashrc` loads Omarchy defaults when available and then applies my personal Bash configuration.




