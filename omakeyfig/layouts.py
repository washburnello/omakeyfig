"""Parser for official RK KB.ini layout files.

Format per key:  K<n>=x1,y1,x2,y2, 0x02,<VK>,0x00,<slot>
Fields: display rect (x1,y1,x2,y2), unknown, Windows VK code, unknown, key slot.
Lines starting with ';' before a K-line give the display label.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

KEY_RE = re.compile(
    r"^K(\d+)\s*=\s*(\d+),(\d+),(\d+),(\d+),\s*0x02,0x([0-9A-Fa-f]+),0x00,(\d+)"
)


@dataclass
class KeyDef:
    index: int          # K-number from the INI (1-based)
    label: str          # display label from preceding comment
    rect: tuple[int, int, int, int]
    vk: int             # Windows VK code
    slot: int           # firmware key slot


def parse_kb_ini(text: str) -> list[KeyDef]:
    keys: list[KeyDef] = []
    pending_label = ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith(";"):
            pending_label = line[1:].strip()
            continue
        m = KEY_RE.match(line)
        if m:
            n, x1, y1, x2, y2, vk, slot = (
                int(m.group(1)), int(m.group(2)), int(m.group(3)),
                int(m.group(4)), int(m.group(5)),
                int(m.group(6), 16), int(m.group(7)),
            )
            keys.append(KeyDef(index=n, label=pending_label or f"K{n}",
                               rect=(x1, y1, x2, y2), vk=vk, slot=slot))
            pending_label = ""
    # Order by slot so list position == firmware key index for codec use.
    keys.sort(key=lambda k: k.slot)
    return keys


def load_layout(pid: int, data_dir: Path | None = None) -> list[KeyDef]:
    """Load a vendored layout by PID (e.g. 0x0220). Falls back to S70."""
    d = data_dir or (Path(__file__).parent / "layouts" / "data")
    cand = d / f"{pid:04X}_KB.ini"
    if not cand.exists():
        cand = d / "0220_KB.ini"  # S70 default; other RK boards: ymmv
    return parse_kb_ini(cand.read_text(encoding="utf-8", errors="replace"))
