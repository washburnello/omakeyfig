"""Omarchy theme integration: read colors.toml + keyboard.rgb of the active theme."""

from __future__ import annotations

from pathlib import Path

CURRENT_THEME_DIR = Path.home() / ".local" / "state" / "omarchy" / "current" / "theme"


def _parse_simple_toml(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("[") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def theme_colors() -> dict[str, str]:
    p = CURRENT_THEME_DIR / "colors.toml"
    if not p.exists():
        return {}
    return _parse_simple_toml(p)


def keyboard_accent(default: str = "#faa968") -> str:
    """Accent color Omarchy wants on keyboards (single hex line in keyboard.rgb)."""
    p = CURRENT_THEME_DIR / "keyboard.rgb"
    if p.exists():
        v = p.read_text().strip().splitlines()
        if v and v[0].strip().startswith("#"):
            return v[0].strip()
    c = theme_colors().get("accent", default)
    return c if c.startswith("#") else default


def theme_follow_enabled() -> bool:
    cfg = Path.home() / ".config" / "omakeyfig" / "config.toml"
    if not cfg.exists():
        return False
    for line in cfg.read_text().splitlines():
        s = line.strip().replace(" ", "")
        if s.startswith("theme_follow="):
            return s.split("=", 1)[1].lower() in ("true", "1", "yes", "on")
    return False
