# omakeyfig

Unofficial TUI customizer for the **Royal Kludge RK-S70** (split 75%) on
Omarchy/Linux — and, on a best-effort basis, other Royal Kludge boards.

> **Unofficial software, not affiliated with Royal Kludge or Omarchy.**
> Protocol knowledge is derived from reverse engineering by the
> [Rangoli](https://github.com/rnayabed/rangoli) project and the
> [KludgeKnight](https://www.kludgeknight.com/) web app
> ([source](https://github.com/vinc3m1/kludgeknight)). License: GPL-3.0-or-later.

## Features (v1)

- Key remapping with visual S70 layout (74 keys incl. M1–M5 macros)
- Lighting control (mode / brightness / speed / color / sleep)
- Profiles in `~/.config/omakeyfig/profiles/` (firmware is **write-only**, so profiles are the source of truth)
- Omarchy integration: theme-aware TUI, `keyboard.rgb` accent default, opt-in `theme-set` hook, bar widget

## Requirements

- USB cable connection (wireless modes cannot be configured — RK firmware limitation)
- Linux + Python 3.11+, venv recommended

## Install

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
# user-space HID access (no sudo needed afterwards):
sudo cp udev/60-rk.rules /etc/udev/rules.d/ && sudo udevadm control --reload-rules && sudo udevadm trigger
```

## Use

```bash
omakeyfig status                  # list connected RK boards (expect 258a:0220 for the S70)
omakeyfig tui                     # Textual TUI (includes the Key tester screen)
omakeyfig write-map --dry-run     # validate codec without touching hardware
omakeyfig save-profile default    # snapshot defaults
omakeyfig write-map --profile default --yes   # real write (backs up first in later versions)
omakeyfig apply-theme --dry-run   # preview Omarchy accent lighting
omakeyfig tui                     # Textual TUI
```

## Opening the app

- **Omarchy menu** (`Super + Alt + Space`): search for **omakeyfig**.
- **Terminal**: `omakeyfig tui` (the installer below puts it on PATH).
- **Key tester**: open the TUI → select **Key tester** → press keys on the
  S70. A visual board (physical arrangement from the S70 layout data) lights
  each pressed key white and logs the OS key event + firmware slot(s); both
  halves of the split spacebar light together, as do L/R modifier pairs.
  **Clear** resets all indicators. Leave via **Back**.
- **Lighting**: effect picker (all 21 RGB effects), hex color (defaults to
  your Omarchy accent), brightness / speed / sleep steppers, a live board
  preview, and **Push to keyboard** to send it to the real board.

Desktop install (menu entry + PATH shim):

```bash
VENV="$PWD/.venv/bin/python"
printf '#!/bin/sh\nexec "%s" -m omakeyfig.cli "$@"\n' "$VENV" > ~/.local/bin/omakeyfig
chmod +x ~/.local/bin/omakeyfig
sed "s|^Exec=.*|Exec=$HOME/.local/bin/omakeyfig tui|" desktop/omakeyfig.desktop \
  > ~/.local/share/applications/omakeyfig.desktop
# ensure ~/.local/bin is on PATH, then `omakeyfig tui` works anywhere
```

## Omarchy extras

- Auto-sync lighting on theme change (opt-in): set `theme_follow = true` in `~/.config/omakeyfig/config.toml`,
  then `omarchy hook install theme-set hooks/theme-set.d/10-omakeyfig.sh`.
- Bar widget: `omarchy plugin add https://github.com/washburnello/omakeyfig.git --path omarchy-plugin`
  (left-click opens TUI, right-click applies theme color).

## Safety

All RK configurators are write-only and unofficial. `omakeyfig` defaults to `--dry-run`,
asks for confirmation before real writes, and stores every profile locally first.
