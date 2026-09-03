"""Visual S70 keyboard for the tester screen and LED previews.

- Lays keys out in their physical arrangement, derived from the KB.ini
  display rects (rows clustered by y-center, widths/gaps scaled to cells).
- Pressing a physical key lights its on-screen key; it stays lit until
  cleared.
- LED preview modes (Off/Static/Breathing/Rainbow) paint the unpressed keys
  to approximate the matching hardware lighting effect.
"""

from __future__ import annotations

import colorsys
import math
import time

from textual.containers import Horizontal, Vertical
from textual.widgets import Static

from omakeyfig import omarchy
from omakeyfig.keycodes import MACRO_VKS
from omakeyfig.layouts import KeyDef

PX_PER_CELL = 9
KEY_HEIGHT = 3

# US-shifted symbols map back to their base key for highlight purposes.
SHIFTED = {
    "!": "1", "@": "2", "#": "3", "$": "4", "%": "5", "^": "6",
    "&": "7", "*": "8", "(": "9", ")": "0", "_": "-", "+": "=",
    "{": "[", "}": "]", "|": "\\", ":": ";", '"': "'", "<": ",",
    ">": ".", "?": "/", "~": "`",
}

LABEL_ALIASES = {
    "esc": {"esc", "escape"},
    "pgup": {"pgup", "pageup"},
    "pgdn": {"pgdn", "pagedown"},
    "del": {"del", "delete"},
    "caps": {"caps", "capslock", "caps_lock"},
    "capslock": {"caps", "capslock", "caps_lock"},
    "bksp": {"bksp", "backspace"},
    "backspace": {"bksp", "backspace"},
    "win": {"win", "windows", "super", "meta"},
    "lwin": {"win", "windows", "super", "meta"},
    "shift": {"shift"},
    "lshift": {"shift", "lshift"},
    "rshift": {"shift", "rshift"},
    "ctrl": {"ctrl", "control"},
    "lctrl": {"ctrl", "control", "lctrl"},
    "rctrl": {"ctrl", "control", "rctrl"},
    "alt": {"alt"},
    "lalt": {"alt", "lalt"},
    "ralt": {"alt", "ralt"},
}

SHORT_LABELS = {
    "Backspace": "Bksp", "CapsLock": "Caps", "Delete": "Del",
    "LShift": "Shift", "RShift": "Shift", "LCtrl": "Ctrl", "RCtrl": "Ctrl",
    "LAlt": "Alt", "RAlt": "Alt", "LWin": "Win",
    "Left": "←", "Right": "→", "Up": "↑", "Down": "↓",
    "PgUp": "PgUp", "PgDn": "PgDn", "Enter": "Enter",
}


def short_label(kd: KeyDef) -> str:
    if kd.vk in MACRO_VKS:
        return MACRO_VKS[kd.vk]
    if kd.label in SHORT_LABELS:
        return SHORT_LABELS[kd.label]
    return kd.label


def match_names(kd: KeyDef) -> set[str]:
    """All textual key names / characters that should light this key."""
    names: set[str] = set()
    label = short_label(kd)
    low = label.lower()
    names.add(low)
    names.update(LABEL_ALIASES.get(low, set()))
    # Keep the raw INI label matchable too (arrows shorten to glyphs).
    raw = kd.label.lower()
    names.add(raw)
    names.update(LABEL_ALIASES.get(raw, set()))
    if kd.label == "Space":
        names.add("space")
    if len(label) == 1:
        names.add(label.lower())
    return names


def cluster_rows(keys: list[KeyDef]) -> list[list[KeyDef]]:
    """Group keys into physical rows by rect y-center, left-to-right."""
    with_y = [((k.rect[1] + k.rect[3]) / 2, k) for k in keys]
    with_y.sort(key=lambda t: t[0])
    rows: list[list[KeyDef]] = []
    for y, k in with_y:
        if rows and abs(y - sum((kk.rect[1] + kk.rect[3]) / 2 for kk in rows[-1]) / len(rows[-1])) < 20:
            rows[-1].append(k)
        else:
            rows.append([k])
    for row in rows:
        row.sort(key=lambda k: k.rect[0])
    return rows


def cells_for(px_width: int) -> int:
    return max(3, round(px_width / PX_PER_CELL))


def find_slots(keys: list[KeyDef], key_name: str, character: str | None) -> list[int]:
    """Map an OS key event to firmware slots."""
    if character and len(character) == 1:
        ch = character.lower()
        ch = SHIFTED.get(ch, ch)
        hits = [k.slot for k in keys
                if len(short_label(k)) == 1 and short_label(k).lower() == ch]
        if hits:
            return hits
    want = key_name.lower()
    return [k.slot for k in keys if want in match_names(k)]


def _hex(rgb: tuple[float, float, float]) -> str:
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(c * 255))) for c in rgb)


def _parse_hex(s: str) -> tuple[float, float, float]:
    s = s.strip().lstrip("#")
    return int(s[0:2], 16) / 255, int(s[2:4], 16) / 255, int(s[4:6], 16) / 255


class KeyCapture(Static, can_focus=True):
    """Focusable display that consumes no keys itself, so every keypress
    bubbles up to the app handler (except app-level bindings)."""

    DEFAULT_CSS = "KeyCapture { height: 3; content-align: center middle; border: solid $primary; }"


class KeyWidget(Static):
    DEFAULT_CSS = "KeyWidget { height: 1; margin: 0; padding: 0; text-align: center; }"

    def __init__(self, kd: KeyDef, cells: int) -> None:
        super().__init__(short_label(kd))
        self.slot = kd.slot
        self.styles.width = cells

    def on_click(self) -> None:
        parent = self.parent
        while parent is not None and not isinstance(parent, KeyboardTester):
            parent = parent.parent
        if parent is not None:
            parent.flash_slot(self.slot)


class KeyboardTester(Vertical):
    """Visual board. Owns pressed state + LED preview painting."""

    DEFAULT_CSS = """
    KeyboardTester { height: auto; overflow-x: auto; }
    KeyboardTester .kb-row { height: 1; margin: 0; padding: 0; }
    """

    LED_MODES = ["Off", "Static", "Breathing", "Rainbow"]

    def __init__(self, keys: list[KeyDef], accent: str = "#faa968") -> None:
        super().__init__(id="kb")
        self.keys = keys
        self.accent = accent
        self.pressed: set[int] = set()
        self.led_mode = "Off"
        self.by_slot: dict[int, KeyWidget] = {}
        self._t0 = time.monotonic()
        self._timer = None
        colors = omarchy.theme_colors()
        self.base_bg = colors.get("lighter_background", "#0a2540")
        self.base_fg = colors.get("foreground", "#f6dcac")

    def compose(self):
        from textual.widgets import Static as S
        for row in cluster_rows(self.keys):
            min_x = min(k.rect[0] for k in row)
            with Horizontal(classes="kb-row"):
                cursor = 0
                for k in row:
                    x1, _, x2, _ = k.rect
                    off = round((x1 - min_x) / PX_PER_CELL)
                    if off > cursor:
                        gap = S("")
                        gap.styles.width = off - cursor
                        yield gap
                        cursor = off
                    w = cells_for(x2 - x1)
                    key = KeyWidget(k, w)
                    self.by_slot[k.slot] = key
                    yield key
                    cursor += w

    def on_mount(self) -> None:
        self._timer = self.set_interval(0.1, self._tick)
        self._paint()

    def on_unmount(self) -> None:
        if self._timer is not None:
            self._timer.stop()

    # -- pressed state ------------------------------------------------------
    def mark_pressed(self, slots: list[int]) -> None:
        self.pressed.update(slots)
        self._paint()

    def flash_slot(self, slot: int) -> None:
        self.mark_pressed([slot])

    def clear_pressed(self) -> None:
        self.pressed.clear()
        self._paint()

    # -- LED preview ---------------------------------------------------------
    def set_led_mode(self, mode: str) -> None:
        if mode in self.LED_MODES:
            self.led_mode = mode
            self._paint()

    def led_color(self, kd: KeyDef, t: float) -> str:
        if self.led_mode == "Static":
            return self.accent
        if self.led_mode == "Breathing":
            f = 0.30 + 0.70 * (0.5 + 0.5 * math.sin(2 * math.pi * t / 2.4))
            r, g, b = _parse_hex(self.accent)
            return _hex((r * f, g * f, b * f))
        if self.led_mode == "Rainbow":
            x_frac = (kd.rect[0] + kd.rect[2]) / 2 / 850
            return _hex(colorsys.hsv_to_rgb((t * 0.15 + x_frac) % 1.0, 0.9, 1.0))
        return self.base_bg

    def _tick(self) -> None:
        if self.led_mode != "Off":
            self._paint()

    def _paint(self) -> None:
        t = time.monotonic() - self._t0
        for k in self.keys:
            w = self.by_slot.get(k.slot)
            if w is None:
                continue
            if k.slot in self.pressed:
                w.styles.background = "#ffffff"
                w.styles.color = "#000000"
            elif self.led_mode == "Off":
                w.styles.background = self.base_bg
                w.styles.color = self.base_fg
            else:
                w.styles.background = self.led_color(k, t)
                w.styles.color = "#000000"
