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

Package dependencies required by the configuration and tooling represented in this repository are maintained as simple, root-level inventories (one package name per line):

- **`list.txt`** — packages from the official Arch repositories (as configured on Omarchy).
- **`aur-list.txt`** — AUR-only packages (if any). Currently empty; no AUR-only dependencies were identified.

**Prerequisites:** A working Omarchy/Arch package environment with network access to the configured repositories. `yay` is used by Omarchy's AUR helper and is available on Omarchy. No `curl`-based installation, remote shell execution, or downloaded installer scripts are used.

**One-shot installation (Omarchy 4.5, copy/paste):**

Install all official-repository packages (preferred Omarchy native command):

```bash
omarchy pkg add $(grep -vE '^\s*(#|$)' ~/.dotfiles/list.txt)
```

Install all AUR packages, if `aur-list.txt` contains any (Omarchy AUR wrapper):

```bash
[ -s ~/.dotfiles/aur-list.txt ] && omarchy pkg aur add $(grep -vE '^\s*(#|$)' ~/.dotfiles/aur-list.txt)
```

Run these from `bash` (command substitution expands the full list into one invocation). `omarchy pkg add` installs missing official packages via `pacman` (`--needed`) with appropriate privilege handling; `omarchy pkg aur add` installs missing AUR packages via `yay` (`--needed`). Neither command accepts a package-list file, so the list contents are passed as arguments in one go.

**Alternative (package-manager commands):**

```bash
sudo pacman -S --needed -- $(grep -vE '^\s*(#|$)' ~/.dotfiles/list.txt)
[ -s ~/.dotfiles/aur-list.txt ] && yay -S --needed -- $(grep -vE '^\s*(#|$)' ~/.dotfiles/aur-list.txt)
```

**Optional / alias-specific tools (not in the package lists):** Some `.bashrc` entries are personal conveniences that rely on tools not included as required packages here, for example: `git`/`make` (used by the `gh-update` alias; commonly present via Omarchy/base development tools), `xdg-open` (used by the `sab` alias), `pacman` (system package manager), and locally installed/personal binaries or paths such as `/opt/nanominer/nanominer` or a local `sabnzbd` downloads directory. The `extract()` function's `.rar` case invokes `unrar2dir` as written; that specific helper is not provided by a standard package and is not included (the general `unrar` package provides `unrar`, not `unrar2dir`). Common archive/system tools already supplied by a typical Omarchy/base installation (e.g. `tar`, `bzip2`, `gzip`, `unzip`) are not duplicated in the lists.


