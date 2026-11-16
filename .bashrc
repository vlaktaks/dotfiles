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
# Extra aliases
# ================================================

alias ll='ls -lah --color=auto'
alias la='ls -A'
alias update='sudo pacman -Syu'
alias fix='source ~/.bashrc'
alias code='cd ~/Code/ && ls -a'
alias nanoxmr='/opt/nanominer/nanominer /home/jp/config.ini'
alias gh-update='cd ~/cli && git pull && make && cp bin/gh ~/.local/bin/gh'
alias ysap='cd ~/Code/Bash && ls -a'
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
# Subtle command completion feedback (Kitty bell)
# ================================================
# Emits a single BEL after command execution to trigger Kitty's bell-pulse shader.
# Integrated without replacing existing PROMPT_COMMAND hooks (e.g. starship/Omarchy).
# Captures $? first so the command's exit status is preserved.
if [[ $- == *i* && -z ${__DOTFILES_BELL_PROMPT_LOADED+x} ]]; then
  __DOTFILES_BELL_PROMPT_LOADED=1
  __dotfiles_bell_last_hist=${HISTCMD:-0}

  __dotfiles_bell_prompt() {
    local status=$?
    local current_hist=${HISTCMD:-0}

    # Skip the initial prompt; only notify after an actual command line executed.
    if [[ $current_hist -ne $__dotfiles_bell_last_hist ]]; then
      __dotfiles_bell_last_hist=$current_hist
      # BEL is the notification mechanism; Kitty can react via bell-in-window shader events.
      # A single event cannot reliably distinguish success from failure, so one subtle
      # completion effect is used for all commands.
      printf '\a'
    fi

    return "$status"
  }

  PROMPT_COMMAND="__dotfiles_bell_prompt${PROMPT_COMMAND:+;$PROMPT_COMMAND}"
fi

