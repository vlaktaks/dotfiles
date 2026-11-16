#!/usr/bin/env bash

# ================================================
# This bashRC can kill you! ~ J.P. Ramackers
# ================================================

# Omarchy environment (OMARCHY_PATH + PATH).
# Required even for non-interactive shells.
if [[ -r /usr/share/omarchy/default/bash/env-bootstrap ]]; then
  source /usr/share/omarchy/default/bash/env-bootstrap
fi

# Skip personal configuration in non-interactive shells.
[[ $- != *i* ]] && return

# ble.sh (Bash Line Editor): syntax highlighting and line editing enhancements.
# Load early in interactive startup and attach at end of .bashrc (upstream-recommended).
# Gracefully skip if not installed (package-managed or user-level install).
if [[ -z ${BLE_VERSION-} ]]; then
  _dotfiles_blesh_candidates=(
    "/usr/share/blesh/ble.sh"
    "${XDG_DATA_HOME:-$HOME/.local/share}/blesh/ble.sh"
  )
  for _dotfiles_blesh_path in "${_dotfiles_blesh_candidates[@]}"; do
    if [[ -r $_dotfiles_blesh_path && -t 0 && -t 1 && -t 2 ]]; then
      # Use dotfiles-managed config when available (authoritative source of truth).
      _dotfiles_blesh_rc="${XDG_CONFIG_HOME:-$HOME/.config}/blesh/init.sh"
      if [[ -r $_dotfiles_blesh_rc ]]; then
        source -- "$_dotfiles_blesh_path" --attach=none --rcfile "$_dotfiles_blesh_rc"
      else
        source -- "$_dotfiles_blesh_path" --attach=none
      fi
      break
    fi
  done
  unset _dotfiles_blesh_path _dotfiles_blesh_candidates _dotfiles_blesh_rc
fi

# Load Omarchy defaults when available.
if [[ -n ${OMARCHY_PATH:-} && -r "$OMARCHY_PATH/default/bash/rc" ]]; then
  source "$OMARCHY_PATH/default/bash/rc"
  # Let the personal cd() function take precedence.
  unalias cd 2>/dev/null
fi

# Personal configuration follows below.

export GOBIN="$HOME/.local/bin"
export PATH="$GOBIN:$PATH"

export PATH="$(go env GOPATH)/bin:$PATH"

export VIRTUAL_ENV_DISABLE_PROMPT=1

# ================================================
# Directory listings (eza, unified Nerd Font icon style)
# ================================================
# One authoritative eza style for all listing aliases (icons always, dirs first).
# Requires: eza (Arch/Omarchy package). Falls back to GNU ls if unavailable.
if command -v eza &>/dev/null; then
  _dotfiles_eza=(eza --icons=always --group-directories-first)
  _dotfiles_eza_long=(--long --header --binary --time-style=long-iso)

  alias ls='eza --icons=always --group-directories-first'
  alias l='eza --icons=always --group-directories-first --long --header --binary --time-style=long-iso'
  alias ll='eza --icons=always --group-directories-first --long --header --binary --time-style=long-iso'
  alias la='eza --icons=always --group-directories-first --all'
  alias lsa='eza --icons=always --group-directories-first --all'
  alias lt='eza --icons=always --group-directories-first --long --header --binary --time-style=long-iso --tree --level=2 --git'
  alias lta='eza --icons=always --group-directories-first --long --header --binary --time-style=long-iso --tree --level=2 --git --all'

  # Custom shortcut: jump to ~/Code and show a consistent listing (no VS Code editor installed).
  alias code='cd ~/Code/ && eza --icons=always --group-directories-first --all'

  unset _dotfiles_eza _dotfiles_eza_long
else
  alias ll='ls -lh --color=auto'
  alias la='ls -A --color=auto'
  alias l='ls -lh --color=auto'
  alias code='cd ~/Code/ && ls -A --color=auto'
fi

# ================================================
# Extra aliases
# ================================================

alias update='sudo pacman -Syu'
alias fix='source ~/.bashrc'
alias nanoxmr='/opt/nanominer/nanominer /home/jp/config.ini'
alias gh-update='cd ~/cli && git pull && make && cp bin/gh ~/.local/bin/gh'
alias ysap='cd ~/Code/Bash && eza --icons=always --group-directories-first --all'
alias sab='xdg-open /var/lib/sabnzbd/Downloads/complete'

# ================================================
# Extra functions for extract and cd
# ================================================

function extract() {
  if [ -f "$1" ]; then
    case "$1" in
    *.tar.bz2) tar xjvf "$1" ;;
    *.tar.gz) tar xzvf "$1" ;;
    *.tar.xz) tar xvf "$1" ;;
    *.bz2) bzip2 -d "$1" ;;
    *.rar) unrar2dir "$1" ;;
    *.gz) gunzip "$1" ;;
    *.tar) tar xf "$1" ;;
    *.tbz2) tar xjf "$1" ;;
    *.tgz) tar xzf "$1" ;;
    *.zip) unzip "$1" ;;
    *.Z) uncompress "$1" ;;
    *.7z) 7z x "$1" ;;
    *.ace) unace x "$1" ;;
    *) echo "'$1' cannot be extracted via extract()" ;;
    esac
  else
    echo "'$1' is not a valid file"
  fi
}

function cd() {
  local new_directory="${*:-$HOME}"
  builtin cd "$new_directory" &&
    /bin/ls -lhF --time-style=long-iso --color=auto --ignore=lost+found
}

# ================================================
# Command completion hook (reserved for future subtle feedback)
# ================================================
# A BEL-based visual completion flash was intentionally disabled because Kitty's
# native visual bell causes a distracting full-window flash for ordinary commands.
# The hook remains integrated without replacing existing PROMPT_COMMAND hooks and
# preserves the command's exit status.
if [[ $- == *i* && -z ${__DOTFILES_BELL_PROMPT_LOADED+x} ]]; then
  __DOTFILES_BELL_PROMPT_LOADED=1
  __dotfiles_bell_last_hist=${HISTCMD:-0}

  __dotfiles_bell_prompt() {
    local status=$?
    local current_hist=${HISTCMD:-0}

    # Track executed command lines (initial prompt skipped) without emitting BEL.
    if [[ $current_hist -ne $__dotfiles_bell_last_hist ]]; then
      __dotfiles_bell_last_hist=$current_hist
    fi

    return "$status"
  }

  PROMPT_COMMAND="__dotfiles_bell_prompt${PROMPT_COMMAND:+;$PROMPT_COMMAND}"
fi

# Attach ble.sh after all interactive initialization and prompt hooks are configured.
[[ ${BLE_VERSION-} ]] && ble-attach

