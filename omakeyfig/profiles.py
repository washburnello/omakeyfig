"""Local profiles. The firmware is write-only, so profiles are the source of truth."""

from __future__ import annotations

import json
from pathlib import Path


def config_dir() -> Path:
    return Path.home() / ".config" / "omakeyfig"


def profiles_dir() -> Path:
    d = config_dir() / "profiles"
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_profile(name: str, payload: dict) -> Path:
    p = profiles_dir() / f"{name}.json"
    p.write_text(json.dumps(payload, indent=2, sort_keys=True))
    return p


def load_profile(name: str) -> dict:
    p = profiles_dir() / f"{name}.json"
    return json.loads(p.read_text())


def list_profiles() -> list[str]:
    d = profiles_dir()
    return sorted(p.stem for p in d.glob("*.json"))
