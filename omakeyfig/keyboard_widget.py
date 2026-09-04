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

PX_PER_CELL = 7  # roomy cells for modern monitors; narrow terminals scroll
KEY_HEIGHT = 3

# The split seam: firmware slots AFTER which the two halves separate.
# The INI rects draw uniform ~15px gaps everywhere, so the seam is not
# geometric — it comes from the physical board (user's ASCII layout):
# row0 6|7, row1 T|Y, row2 G|H, row3 B|N, bottom SPACE|SPACE.
SEAM_AFTER_SLOTS = frozenset({43, 38, 39, 40, 35})
SEAM_CELLS = 6

# Fn-layer legends by firmware slot. Sources: user-verified (PgUp->Pause,
# PgDn->End), S70 manual (Fn+A Windows mode, Fn+S Mac mode), S70 review
# (Fn+| color presets, Fn+arrows brightness/speed), RK-standard number row
# (Fn+1..= -> F1-F12). Everything else is None ("?" in the UI) until
# confirmed with the key tester: open the tester, hold physical Fn, press
# a key, and read what the OS receives.
FN_LAYER: dict[int, str] = {
    # number row -> F1..F12
    13: "F1", 19: "F2", 25: "F3", 31: "F4", 37: "F5", 43: "F6",
    55: "F7", 61: "F8", 67: "F9", 73: "F10", 79: "F11", 85: "F12",
    15: "Win", 21: "Mac",       # Fn+A Windows mode, Fn+S Mac mode
    80: "Home", 86: "ScrLk",    # user-confirmed (was "?" before)
    92: "Style",                # user-confirmed: lighting style/mode
    52: "Hue",                  # user-confirmed: Fn+N cycles hue
    98: "Ins",                  # Fn+Delete -> Insert (manual lists Insert)
    99: "Pause", 100: "End",    # user-verified
    94: "Brt+", 95: "Brt-",     # Fn+Up/Down brightness
    89: "Spd◀", 101: "Spd▶",    # Fn+Left/Right animation speed/direction
}
# FN-LCK (user's name) = the Fn+LeftCtrl chord that toggles F-shift mode,
# not a separate combo. The F-Shift board toggle mirrors that mode.


def fn_legend(slot: int) -> str | None:
    return FN_LAYER.get(slot)


# F-shift mode (toggled on the board with Fn+LeftCtrl): the number row
# defaults to F1..F12, and Fn+those keys emit media functions. Mapping is
# the RK-standard F-key media table (RK61 docs; S70 manual lists the same
# 12 functions). Slots are the S70 number-row slots 13..85.
FSHIFT_KEYS: dict[int, str] = {
    13: "F1", 19: "F2", 25: "F3", 31: "F4", 37: "F5", 43: "F6",
    55: "F7", 61: "F8", 67: "F9", 73: "F10", 79: "F11", 85: "F12",
}
FSHIFT_FN_MEDIA: dict[int, str] = {
    13: "MyPC", 19: "Browser", 25: "Mail", 31: "Calc", 37: "Player",
    43: "Stop", 55: "Prev", 61: "Play", 67: "Next", 73: "Mute",
    79: "Vol-", 85: "Vol+",
}

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


def row_layout(row: list[KeyDef]) -> list[tuple]:
    """Linear layout ops for one physical row: ("gap"|"key"|"seam", width[, keydef]).

    Includes the split seam: SEAM_CELLS extra cells after the seam slot.
    Both the key row and its Fn legend row consume this, so they align.
    """
    min_x = min(k.rect[0] for k in row)
    ops: list[tuple] = []
    cursor = 0
    for k in row:
        x1, _, x2, _ = k.rect
        off = round((x1 - min_x) / PX_PER_CELL)
        if off > cursor:
            ops.append(("gap", off - cursor))
            cursor = off
        w = cells_for(x2 - x1)
        ops.append(("key", w, k))
        cursor += w
        if k.slot in SEAM_AFTER_SLOTS:
            ops.append(("seam", SEAM_CELLS))
            cursor += SEAM_CELLS
    return ops


def find_slots(keys: list[KeyDef], key_name: str, character: str | None) -> list[int]:
    """Map an OS key event to firmware slots (label matching only)."""
    return [s for s, _, _ in match_candidates(keys, None, key_name, character)]


def match_candidates(keys: list[KeyDef], fw_of: dict[int, int] | None,
                     key_name: str, character: str | None) -> list[tuple[int, str, str]]:
    """Map an OS key event to [(slot, bind_label, via)].

    `fw_of` maps slot -> current firmware code (the pushed base map).
    Matches bind labels FIRST (what the slot actually sends), then physical
    labels (what the cap says). Both halves of the split spacebar match a
    space event when they share a bind — the OS genuinely cannot tell them
    apart, and the caller should say so.
    """
    from omakeyfig.remap import label_for_fw

    def bind(slot: int) -> str:
        if fw_of is None or slot not in fw_of:
            return ""
        try:
            return label_for_fw(fw_of[slot])
        except Exception:
            return ""

    found: list[tuple[int, str, str]] = []
    seen: set[int] = set()

    def add(slot: int, via: str) -> None:
        if slot not in seen:
            seen.add(slot)
            found.append((slot, bind(slot), via))

    if character and len(character) == 1:
        ch = SHIFTED.get(character.lower(), character.lower())
        for k in keys:
            if k.slot in seen:
                continue
            b = bind(k.slot)
            if b and len(b) == 1 and b.lower() == ch:
                add(k.slot, "bind")
        for k in keys:
            if k.slot in seen:
                continue
            if len(short_label(k)) == 1 and short_label(k).lower() == ch:
                add(k.slot, "label")
        if found:
            return found
    want = key_name.lower()
    for k in keys:
        if k.slot in seen:
            continue
        b = bind(k.slot)
        if b and b.lower() == want:
            add(k.slot, "bind")
    for k in keys:
        if k.slot in seen:
            continue
        if want in match_names(k):
            add(k.slot, "label")
    return found


def _hex(rgb: tuple[float, float, float]) -> str:
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(c * 255))) for c in rgb)


def _parse_hex(s: str) -> tuple[float, float, float]:
    s = s.strip().lstrip("#")
    return int(s[0:2], 16) / 255, int(s[2:4], 16) / 255, int(s[4:6], 16) / 255


class KeyCapture(Static, can_focus=True):
    """Focusable display that consumes no keys itself, so every keypress
    bubbles up to the app handler (except app-level bindings)."""

    DEFAULT_CSS = "KeyCapture { height: 3; content-align: center middle; border: solid $primary; }"


class LegendWidget(Static):
    """Slim, non-outlined Fn legend cell shown under its key row."""

    DEFAULT_CSS = "LegendWidget { height: 1; margin: 0; padding: 0; text-align: center; opacity: 0.65; }"

    def __init__(self, kd: KeyDef, cells: int) -> None:
        super().__init__("")
        self.slot = kd.slot
        self.legend = ""
        self.styles.width = cells
        self.set_legends(False)

    def set_legends(self, fshift_view: bool) -> None:
        if fshift_view:
            self.legend = FSHIFT_FN_MEDIA.get(self.slot) or fn_legend(self.slot) or ""
        else:
            self.legend = fn_legend(self.slot) or ""
        self.update(self.legend)


class KeyWidget(Static):
    DEFAULT_CSS = """
    KeyWidget {
        height: 3;
        margin: 0;
        padding: 0;
        text-align: center;
        content-align: center middle;
        border: solid $primary;
    }
    """

    def __init__(self, kd: KeyDef, cells: int, keycaps: dict[int, str] | None = None) -> None:
        from omakeyfig.keycaps import display_label
        super().__init__("")
        self.slot = kd.slot
        self.base_label = short_label(kd)
        self.keycap_label = display_label(kd.slot, self.base_label, keycaps)
        self.shown_label = self.keycap_label
        self.fshift_view = False
        # Label view: "caps" (keycap text) | "slots" (firmware slot #) | "binds" (firmware action).
        self.label_view = "caps"
        self.bind_label: str | None = None
        self.styles.width = cells
        self.update(self.keycap_label)

    def set_label_view(self, mode: str, bind_label: str | None = None) -> None:
        if mode in ("caps", "slots", "binds"):
            self.label_view = mode
        if bind_label is not None:
            self.bind_label = bind_label
        self.refresh_label()

    def refresh_label(self) -> None:
        if self.fshift_view and self.slot in FSHIFT_KEYS:
            self.shown_label = FSHIFT_KEYS[self.slot]
            self.update(f"[bold]{self.shown_label}[/bold]")
            return
        if self.label_view == "slots":
            self.shown_label = str(self.slot)
        elif self.label_view == "binds":
            self.shown_label = self.bind_label or "?"
        else:
            self.shown_label = self.keycap_label
        self.update(self.shown_label)

    def set_fshift_view(self, on: bool) -> None:
        self.fshift_view = on
        self.refresh_label()

    def on_click(self) -> None:
        parent = self.parent
        while parent is not None and not isinstance(parent, KeyboardTester):
            parent = parent.parent
        if parent is not None:
            if parent.click_mode == "select":
                parent.select_slot(self.slot)
            else:
                parent.flash_slot(self.slot)


class KeyboardTester(Vertical):
    """Visual board. Owns pressed state + LED preview painting."""

    DEFAULT_CSS = """
    KeyboardTester { height: auto; overflow-x: auto; }
    KeyboardTester .kb-row { height: 3; margin: 0; padding: 0; }
    KeyboardTester .kb-legend { height: 1; margin: 0; padding: 0; display: none; }
    KeyboardTester.show-fn .kb-legend { display: block; }
    """

    LED_MODES = ["Off", "Static", "Breathing", "Rainbow"]

    def __init__(self, keys: list[KeyDef], accent: str = "#faa968") -> None:
        super().__init__(id="kb")
        self.keys = keys
        self.accent = accent
        self.pressed: set[int] = set()
        self.led_mode = "Off"
        self.fn_view = False
        self.fshift_view = False
        self.label_view = "caps"
        self.bind_labels: dict[int, str] = {}
        self.by_slot: dict[int, KeyWidget] = {}
        self.click_mode = "flash"  # or "select" for the remap screen
        self.selected: int | None = None
        self.rows: list[list[KeyDef]] = []
        self._t0 = time.monotonic()
        self._timer = None
        colors = omarchy.theme_colors()
        self.base_bg = colors.get("lighter_background", "#0a2540")
        self.base_fg = colors.get("foreground", "#f6dcac")
        self.sel_bg = colors.get("selection", "#134e5a")

    def compose(self):
        from textual.widgets import Static as S
        self.rows = cluster_rows(self.keys)
        for row in self.rows:
            with Horizontal(classes="kb-row"):
                for op in row_layout(row):
                    if op[0] in ("gap", "seam"):
                        gap = S("")
                        gap.styles.width = op[1]
                        yield gap
                    else:
                        _, w, k = op
                        key = KeyWidget(k, w)
                        self.by_slot[k.slot] = key
                        yield key
            with Horizontal(classes="kb-legend"):
                for op in row_layout(row):
                    if op[0] in ("gap", "seam"):
                        gap = S("")
                        gap.styles.width = op[1]
                        yield gap
                    else:
                        _, w, k = op
                        yield LegendWidget(k, w)

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

    # -- Fn-layer / F-shift views -----------------------------------------------
    def set_fn_view(self, on: bool) -> None:
        self.fn_view = on
        self.set_class(on, "show-fn")

    def set_fshift_view(self, on: bool) -> None:
        self.fshift_view = on
        for w in self.by_slot.values():
            w.set_fshift_view(on)
        try:
            for leg in self.query(LegendWidget):
                leg.set_legends(on)
        except Exception:
            pass

    # -- label views: caps | slots | binds --------------------------------------
    LABEL_VIEWS = ("caps", "slots", "binds")

    def set_label_view(self, mode: str, bind_labels: dict[int, str] | None = None) -> None:
        if mode in self.LABEL_VIEWS:
            self.label_view = mode
        if bind_labels is not None:
            self.bind_labels = bind_labels
        for slot, w in self.by_slot.items():
            w.set_label_view(self.label_view, self.bind_labels.get(slot))

    def cycle_label_view(self, bind_labels: dict[int, str] | None = None) -> str:
        if bind_labels is not None:
            self.bind_labels = bind_labels
        nxt = self.LABEL_VIEWS[(self.LABEL_VIEWS.index(self.label_view) + 1) % 3]
        self.set_label_view(nxt)
        return nxt

    # -- cursor selection (remap screen) ---------------------------------------
    def _center(self, kd: KeyDef) -> float:
        return (kd.rect[0] + kd.rect[2]) / 2

    def select_slot(self, slot: int | None) -> None:
        self.selected = slot
        self._paint()

    def move_cursor(self, dx: int, dy: int) -> int | None:
        """Move the cursor across physical rows; returns the new slot."""
        if not self.rows:
            return None
        if self.selected is None:
            row_i, col_i = (0 if dy >= 0 else len(self.rows) - 1), 0
            self.select_slot(self.rows[row_i][col_i].slot)
            return self.selected
        cur = next(((ri, ci) for ri, row in enumerate(self.rows)
                    for ci, k in enumerate(row) if k.slot == self.selected), None)
        if cur is None:
            return None
        ri, ci = cur
        if dy == 0:
            ci = max(0, min(len(self.rows[ri]) - 1, ci + dx))
        else:
            ri = max(0, min(len(self.rows) - 1, ri + dy))
            x = self._center(self.rows[cur[0]][cur[1]])
            ci = min(range(len(self.rows[ri])), key=lambda c: abs(self._center(self.rows[ri][c]) - x))
        self.select_slot(self.rows[ri][ci].slot)
        return self.selected

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
            elif k.slot == self.selected:
                w.styles.background = self.sel_bg
                w.styles.color = "#ffffff"
            elif self.led_mode == "Off":
                w.styles.background = self.base_bg
                w.styles.color = self.base_fg
            else:
                w.styles.background = self.led_color(k, t)
                w.styles.color = "#000000"
