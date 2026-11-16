# dotfiles

Personal dotfiles for my Omarchy setup.

## Fresh-install guide (Omarchy)

### 1. Clone dotfiles

```bash
git clone https://github.com/vlaktaks/dotfiles.git ~/.dotfiles
```

### 2. Activate the personal Bash configuration

If an existing `~/.bashrc` is present, back it up before replacing it with the symlink, for example:

```bash
mv ~/.bashrc ~/.bashrc.bak
```

Then link the repository-managed configuration:

```bash
ln -s ~/.dotfiles/.bashrc ~/.bashrc
```

The repository-managed `.bashrc`:

- Initializes the Omarchy environment when available (sources `/usr/share/omarchy/default/bash/env-bootstrap`, including for non-interactive shells).
- Loads Omarchy's own default Bash configuration when available (`$OMARCHY_PATH/default/bash/rc`) and removes Omarchy's `cd` alias so the personal `cd()` function takes precedence.
- Preserves my personal aliases, exports, and functions.
- Also remains usable outside Omarchy (Omarchy-specific initialization/defaults are applied only when their files/paths are available).

### 3. Install packages

`list.txt` (at the repository root) lists additional package dependencies required by the configuration and tooling represented in this repository, one package name per line. It is intended to be installed in a single operation.

**Repositories/package manager:** Package names are Arch Linux packages from the configured official repositories (as available on Omarchy). The one-shot command below uses `yay`, which is the package helper available on Omarchy and can install packages from official repositories (and from the AUR when AUR package names are included). The current `list.txt` contains official-repository packages only.

**Prerequisites:** A working Omarchy/Arch package environment with `yay` installed and network access to the configured repositories. No `curl`-based installation or remote installer scripts are used.

**One-shot installation command (Omarchy 4.5):**

```bash
yay -S --needed -- $(grep -vE '^\s*(#|$)' ~/.dotfiles/list.txt)
```

Run this from `bash` (so command substitution works). It installs all packages listed in `list.txt` in one operation, skipping packages that are already installed (`--needed`).

> Note: Omarchy provides `omarchy pkg add <packages...>` for installing named Arch packages and `omarchy pkg aur add <packages...>` for AUR packages, but neither accepts a package-list file. The command above is the straightforward one-shot way to install the contents of `list.txt`.

**Optional / alias-specific tools (not listed in `list.txt`):** Some entries in `.bashrc` are personal conveniences that rely on tools not included as required packages here, for example: `git`/`make` (used by the `gh-update` alias; commonly present via Omarchy/base development tools), `xdg-open` (used by the `sab` alias), `pacman` (system package manager), and locally installed/personal binaries such as `/opt/nanominer/nanominer` or a local `sabnzbd` downloads path. The `extract()` function's `.rar` case invokes `unrar2dir` as written; that specific helper is not provided by a standard package and is not included in `list.txt` (the general `unrar` package provides `unrar`, not `unrar2dir`). Common archive tools already provided by a typical Omarchy/base system (e.g. `tar`, `bzip2`, `gzip`, `unzip`) are not duplicated in `list.txt`.

