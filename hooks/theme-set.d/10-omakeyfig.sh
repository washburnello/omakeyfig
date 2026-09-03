#!/bin/bash
# omakeyfig theme-set hook: optionally push Omarchy's keyboard accent to the RK board.
# Installed via: omarchy hook install theme-set hooks/theme-set.d/10-omakeyfig.sh
# Respects theme_follow=true in ~/.config/omakeyfig/config.toml (default: off).
THEME_NAME=$1
CFG="$HOME/.config/omakeyfig/config.toml"
if grep -qi "^theme_follow *= *true" "$CFG" 2>/dev/null; then
  omakeyfig apply-theme --from-omarchy 2>/dev/null || true
fi
