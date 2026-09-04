"""Remap action catalog + search.

Actions mirror KludgeKnight's KEY_MAP (VK -> firmware code, labels,
categories) plus the macro-slot codes for M1-M5. `fw_for(action_id)`
returns the firmware code to write for a slot.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Action:
    aid: int      # VK code or pseudo-VK for media/macros
    label: str
    category: str
    fw: int


def _h(hid: int) -> int:
    return hid << 8


_LETTERS = [(vk, chr(vk), "Letters", _h(h))
            for vk, h in zip(range(0x41, 0x5B),
                             [0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C,
                              0x0D, 0x0E, 0x0F, 0x10, 0x11, 0x12, 0x13, 0x14, 0x15,
                              0x16, 0x17, 0x18, 0x19, 0x1A, 0x1B, 0x1C, 0x1D])]
_NUMBERS = [((0x30 + (i % 10)), str(i % 10), "Numbers", _h(h))
            for i, h in [(1, 0x1E), (2, 0x1F), (3, 0x20), (4, 0x21), (5, 0x22),
                         (6, 0x23), (7, 0x24), (8, 0x25), (9, 0x26), (0, 0x27)]]
_FKEYS = [(0x70 + i, f"F{i + 1}", "Function Keys", _h(0x3A + i)) for i in range(12)]
_SYMBOLS = [
    (0xC0, "` ~", "Symbols", _h(0x35)), (0xBD, "- _", "Symbols", _h(0x2D)),
    (0xBB, "= +", "Symbols", _h(0x2E)), (0xDB, "[ {", "Symbols", _h(0x2F)),
    (0xDD, "] }", "Symbols", _h(0x30)), (0xDC, "\\ |", "Symbols", _h(0x31)),
    (0xBA, "; :", "Symbols", _h(0x33)), (0xDE, "' \"", "Symbols", _h(0x34)),
    (0xBC, ", <", "Symbols", _h(0x36)), (0xBE, ". >", "Symbols", _h(0x37)),
    (0xBF, "/ ?", "Symbols", _h(0x38)),
]
_NAV = [
    (0x25, "Left", "Navigation", _h(0x50)), (0x28, "Down", "Navigation", _h(0x51)),
    (0x27, "Right", "Navigation", _h(0x4F)), (0x26, "Up", "Navigation", _h(0x52)),
    (0x24, "Home", "Navigation", _h(0x4A)), (0x23, "End", "Navigation", _h(0x4D)),
    (0x21, "Page Up", "Navigation", _h(0x4B)), (0x22, "Page Down", "Navigation", _h(0x4E)),
    (0x2D, "Insert", "Navigation", _h(0x49)), (0x2E, "Delete", "Navigation", _h(0x4C)),
    (0x2C, "Print Screen", "Navigation", _h(0x46)),
]
_MODS = [
    (0xA0, "Left Shift", "Modifiers", 0x020000), (0xA1, "Right Shift", "Modifiers", 0x200000),
    (0xA2, "Left Ctrl", "Modifiers", 0x010000), (0xA3, "Right Ctrl", "Modifiers", 0x100000),
    (0xA4, "Left Alt", "Modifiers", 0x040000), (0xA5, "Right Alt", "Modifiers", 0x400000),
    (0x5B, "Left Win", "Modifiers", 0x080000), (0x5C, "Right Win", "Modifiers", 0x800000),
    (0xFA, "Fn", "Modifiers", 0xB000),
]
_SPECIAL = [
    (0x1B, "Esc", "Special", _h(0x29)), (0x09, "Tab", "Special", _h(0x2B)),
    (0x14, "Caps Lock", "Special", _h(0x39)), (0x20, "Space", "Special", _h(0x2C)),
    (0x0D, "Enter", "Special", _h(0x28)), (0x08, "Backspace", "Special", _h(0x2A)),
    (0x5D, "App", "Special", _h(0x65)), (0x13, "Pause", "Special", _h(0x48)),
    (0x91, "Scroll Lock", "Special", _h(0x47)),
]
_MEDIA = [
    (0xAD, "Mute", "Media", 0x010000E2), (0xAE, "Volume Down", "Media", 0x010000EA),
    (0xAF, "Volume Up", "Media", 0x010000E9), (0xB0, "Next Track", "Media", 0x010000B5),
    (0xB1, "Previous Track", "Media", 0x010000B6), (0xB2, "Stop", "Media", 0x010000B7),
    (0xB3, "Play/Pause", "Media", 0x010000CD), (0x99, "Calculator", "Media", 0x01000192),
    (0x1001, "Brightness Up", "Media", 0x0100006F),
    (0x1002, "Brightness Down", "Media", 0x01000070),
]
_MACROS = [
    (0xD9, "M1 (Ctrl+A)", "Macros", 0x010400), (0xB9, "M2 (Ctrl+C)", "Macros", 0x010600),
    (0xC6, "M3 (Ctrl+V)", "Macros", 0x011900), (0xB8, "M4 (Ctrl+X)", "Macros", 0x011B00),
    (0xC7, "M5 (Ctrl+S)", "Macros", 0x011600),
]

ACTIONS: list[Action] = [Action(*t) for group in
                         (_LETTERS, _NUMBERS, _FKEYS, _SYMBOLS, _NAV, _MODS,
                          _SPECIAL, _MEDIA, _MACROS) for t in group]
BY_ID = {a.aid: a for a in ACTIONS}


def fw_for(aid: int) -> int:
    return BY_ID[aid].fw


def label_for_fw(fw: int) -> str:
    for a in ACTIONS:
        if a.fw == fw:
            return a.label
    return f"{fw:#08x}"


def search(query: str) -> list[Action]:
    """Case-insensitive substring search over labels; empty query = all."""
    q = query.strip().lower()
    if not q:
        return list(ACTIONS)
    return [a for a in ACTIONS if q in a.label.lower() or q in a.category.lower()]
