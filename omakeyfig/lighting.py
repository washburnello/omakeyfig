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

# Built-in effect names exposed by the official RK software for the S70.
EFFECTS = [
    "Static", "Breathing", "Wave", "Ripple", "Reactive",
    "Rainbow", "Raindrop", "Marquee", "Aurora", "Off",
]


@dataclass
class LightingState:
    effect: str = "Static"
    brightness: int = 100  # 0..100
    speed: int = 50        # 0..100
    color: str = "#faa968"  # hex RGB, defaults to Omarchy accent at runtime
    sleep_minutes: int = 0  # 0 = never


def clamp(v: int, lo: int = 0, hi: int = 100) -> int:
    return max(lo, min(hi, v))


def build_lighting_report(state: LightingState) -> bytes:
    """Placeholder encoder; replaced with captured bytes after validation.

    Returns a human-readable description encoded as bytes so dry-run paths
    and tests exercise the full pipeline without hardware.
    """
    desc = (f"lighting:{state.effect}:b{clamp(state.brightness)}"
            f":s{clamp(state.speed)}:{state.color}:sleep{state.sleep_minutes}")
    return desc.encode()


def describe(state: LightingState) -> str:
    return (f"{state.effect} brightness={state.brightness}% "
            f"speed={state.speed}% color={state.color} sleep={state.sleep_minutes}min")
