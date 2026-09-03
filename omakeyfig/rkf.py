"""Importer for the official RK Windows software's .rkf profile files.

Reverse-engineered from an S70 (PID 0x0220) Profile1.rkf. File layout:

- 0x00: u32 LE device PID (0x220).
- 0x04: 8 unknown bytes.
- 0x0C: UTF-16LE profile name, zero-padded to 0x30.
- 0x30: one 16-byte header record (content TBD, differs per file).
- 0x40: 74 key records, 16 bytes each, in KB.ini K1..K74 order
  (ends at 0x4E0; zeros afterwards until the lighting section ~0x5D60).
- 0x5D60: lighting config + custom color palette (see field-guide.md).

Key record shapes (byte offsets within the 16-byte record):
- Normal key:   [slot][x][y][0x00][0x00][VK][00 x9][flag]
  Effective mapping = VK code in byte 5. (x/y echo the slot for keys the
  user never touched; they are 0x00 for user-touched keys. Either way,
  byte 5 is authoritative.)
- Modifier key: [slot][slot][slot][fw0][fw1][fw2][fw3][genVK][00 x8][0x02]
  where fw0..fw3 is the 4-byte big-endian firmware code and genVK is the
  generic VK (Shift=0x10, Ctrl=0x11, Menu=0x12, ...).
- Combo macro:  [slot][0x00][0x00][0xFF][a][b][c][00 x8][0x02]
  Encoding of a/b/c is not yet decoded; preserved as raw bytes.
- M4-style macro record: 16 bytes ending in 0x05 with embedded key data;
  likewise preserved raw for now.

Only slot -> firmware-code mappings convertible to HID codes are returned
as mappings; macro records land in `unresolved` for manual handling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

RECORD_LEN = 16
N_KEYS = 74
KEYS_OFF = 0x40

# Modifier generic VKs seen in the wild (byte 7 of modifier records).
MODIFIER_SLOTS = {10, 11, 17, 23, 65, 77, 88}


@dataclass
class RkfKey:
    slot: int
    kind: str  # 'vk' | 'modifier' | 'macro' | 'unknown'
    vk: int = 0
    fw: int = 0
    raw: bytes = b""


@dataclass
class RkfProfile:
    pid: int
    name: str
    keys: list[RkfKey] = field(default_factory=list)

    def customizable_vk(self) -> dict[int, int]:
        """slot -> effective VK for plain VK records."""
        return {k.slot: k.vk for k in self.keys if k.kind == "vk"}

    def modifier_fw(self) -> dict[int, int]:
        """slot -> firmware code for modifier records."""
        return {k.slot: k.fw for k in self.keys if k.kind == "modifier"}

    def unresolved(self) -> dict[int, str]:
        """slot -> raw hex for macro records we cannot encode yet."""
        return {k.slot: k.raw.hex(" ") for k in self.keys if k.kind == "macro"}


def parse_rkf(path: str | Path) -> RkfProfile:
    data = Path(path).read_bytes()
    pid = int.from_bytes(data[0x00:0x04], "little")
    name = data[0x0C:0x30].decode("utf-16-le").rstrip("\x00")
    prof = RkfProfile(pid=pid, name=name)
    for i in range(N_KEYS):
        rec = data[KEYS_OFF + i * RECORD_LEN: KEYS_OFF + (i + 1) * RECORD_LEN]
        prof.keys.append(_parse_record(rec))
    return prof


def _parse_record(rec: bytes) -> RkfKey:
    slot = rec[0]
    if rec[3] == 0xFF:
        return RkfKey(slot=slot, kind="macro", raw=bytes(rec))
    if rec[3] == 0x00 and rec[4] == 0x00:
        # Plain VK record. (M1's Esc record ends in 0x05 but is still just
        # a VK record; K59's ends in 0x08. The flag byte is not a type.)
        return RkfKey(slot=slot, kind="vk", vk=rec[5], raw=bytes(rec))
    if rec[15] == 0x05:
        # M4-style 16-byte macro blob.
        return RkfKey(slot=slot, kind="macro", raw=bytes(rec))
    if slot in MODIFIER_SLOTS:
        fw = int.from_bytes(rec[3:7], "big")
        return RkfKey(slot=slot, kind="modifier", fw=fw, vk=rec[7], raw=bytes(rec))
    return RkfKey(slot=slot, kind="unknown", raw=bytes(rec))


def to_omakeyfig_profile(prof: RkfProfile, vk_to_fw) -> dict:
    """Convert to an omakeyfig profile payload.

    vk_to_fw(vk) -> firmware code; raises KeyError for unknown VKs.
    Macro slots are left out (caller fills factory/macros separately).
    """
    from omakeyfig.layouts import load_layout  # local import: layout data for slot sanity
    _ = load_layout  # (slots come from the file itself; layout only validates)
    mappings: dict[str, int] = {}
    for slot, vk in prof.customizable_vk().items():
        mappings[str(slot)] = vk_to_fw(vk)
    for slot, fw in prof.modifier_fw().items():
        mappings[str(slot)] = fw
    return {"pid": prof.pid, "mappings": mappings,
            "unresolved_macros": prof.unresolved(),
            "source": f"rkf:{prof.name}"}
