"""Lighting control for RK boards.

Keyboard-wide lighting (mode / brightness / speed / color / sleep) is
implemented per the Rangoli reverse engineering. Per-key RGB stays behind
`SUPPORTS_PER_KEY_RGB = False` until validated against real S70 captures.

The exact command bytes are filled in during hardware validation (Phase 4);
until then every method works in dry-run form and `describe()` documents
intent. This keeps the TUI/CLI contract stable while the byte layer is
being captured.
"""

from __future__ import annotations

from dataclasses import dataclass

SUPPORTS_PER_KEY_RGB = False

# Effect name -> mode bit for RGB boards (Rangoli ModeModel::RGBModes).
RGB_EFFECT_BITS = {
    "Neon Stream": 1, "Ripples": 2, "Windmill": 3, "Wave": 4,
    "Rainbow": 5, "Stars": 6, "Layered": 7, "Rich": 8,
    "Marquee": 9, "Storm": 10, "Race": 11, "Snake": 12,
    "Diagonal": 13, "Custom": 14, "Ambilight": 15, "Streamer": 16,
    "Steady": 17, "Breathing": 18, "Neon": 19,
    "Shadow": 20, "Flash": 21,
}
EFFECTS = sorted(RGB_EFFECT_BITS)

# Rangoli slider scale for brightness/animation/sleep.
LEVEL_MIN, LEVEL_MAX = 0, 10


@dataclass
class LightingState:
    effect: str = "Steady"
    brightness: int = 5   # 0..10 (Rangoli slider scale)
    speed: int = 5        # 0..10, sent as the animation byte
    color: str = "#faa968"  # hex RGB; ignored when random=True
    random: bool = False
    sleep: int = 5        # sleep timer value, same scale


def clamp(v: int, lo: int = LEVEL_MIN, hi: int = LEVEL_MAX) -> int:
    return max(lo, min(hi, v))


def parse_hex_color(s: str) -> tuple[int, int, int]:
    s = s.strip().lstrip("#")
    if len(s) != 6:
        raise ValueError(f"bad hex color {s!r}")
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)


def build_lighting_report(state: LightingState) -> bytes:
    """Encode the standard lighting buffer (direct port of Rangoli's
    setStandardLightBufferBetter, BufferSize=65).

    [0]=0x0a [1]=0x01 [2]=0x01 [3]=0x02 [4]=0x29 [5]=modebit [6]=0x00
    [7]=animation [8]=brightness [9..11]=RGB [12]=randomflag [13]=sleep.
    """
    bit = RGB_EFFECT_BITS.get(state.effect)
    if bit is None:
        raise ValueError(f"unknown effect {state.effect!r}")
    buf = bytearray(65)
    buf[0] = 0x0A
    buf[1] = 0x01
    buf[2] = 0x01
    buf[3] = 0x02
    buf[4] = 0x29
    buf[5] = bit
    buf[7] = clamp(state.speed)
    buf[8] = clamp(state.brightness)
    if not state.random:
        r, g, b = parse_hex_color(state.color)
        buf[9], buf[10], buf[11] = r, g, b
    buf[12] = 0x01 if state.random else 0x00
    buf[13] = clamp(state.sleep)
    return bytes(buf)


def describe(state: LightingState) -> str:
    return (f"{state.effect} brightness={state.brightness}/10 "
            f"speed={state.speed}/10 color={state.color} sleep={state.sleep}")
