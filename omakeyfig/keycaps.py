"""Keycap overrides: what the physical keycaps READ, independent of firmware.

The user swaps keycaps around. The board therefore shows the keycap label
(display only) while matching and firmware logic keep using the slot.
Stored in ~/.config/omakeyfig/keycaps.toml as `slot = "label"` lines.
"""

from __future__ import annotations

from pathlib import Path


def keycaps_file() -> Path:
    return Path.home() / ".config" / "omakeyfig" / "keycaps.toml"


def load_keycaps() -> dict[int, str]:
    p = keycaps_file()
    out: dict[int, str] = {}
    if not p.exists():
        return out
    for line in p.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or "=" not in line:
            continue
        k, v = line.split("=", 1)
        try:
            out[int(k.strip())] = v.strip().strip('"').strip("'")
        except ValueError:
            continue
    return out


def save_keycaps(caps: dict[int, str]) -> Path:
    p = keycaps_file()
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{slot} = \"{label}\"" for slot, label in sorted(caps.items())]
    p.write_text("\n".join(lines) + ("\n" if lines else ""))
    return p


def set_keycap(slot: int, label: str | None) -> dict[int, str]:
    caps = load_keycaps()
    if label:
        caps[slot] = label
    else:
        caps.pop(slot, None)
    save_keycaps(caps)
    return caps


def display_label(slot: int, default: str, caps: dict[int, str] | None = None) -> str:
    caps = caps if caps is not None else load_keycaps()
    return caps.get(slot, default)
