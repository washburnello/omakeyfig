from omakeyfig import rkf


def rec(*bs: int) -> bytes:
    assert len(bs) == 16
    return bytes(bs)


def test_vk_record():
    k = rkf._parse_record(rec(0x0D, 0x0D, 0x0D, 0, 0, 0x31, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0x02))
    assert (k.slot, k.kind, k.vk) == (13, "vk", 0x31)


def test_vk_record_odd_flags():
    # M1's Esc record ends in 0x05; K59's '/' record ends in 0x08.
    # The flag byte is not a type marker: byte 3/4 == 0 means VK record.
    k = rkf._parse_record(rec(0x01, 0, 0, 0, 0, 0x1B, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0x05))
    assert (k.slot, k.kind, k.vk) == (1, "vk", 0x1B)
    k = rkf._parse_record(rec(0x4C, 0x4C, 0x4C, 0, 0, 0xBF, 0, 0, 0, 0, 0, 0, 0xA2, 0, 0, 0x08))
    assert (k.slot, k.kind, k.vk) == (0x4C, "vk", 0xBF)


def test_modifier_record_big_endian_fw():
    k = rkf._parse_record(rec(0x0A, 0x0A, 0x0A, 0x00, 0x02, 0x00, 0x00, 0x10, 0, 0, 0, 0, 0, 0, 0, 0x02))
    assert (k.slot, k.kind, k.fw, k.vk) == (10, "modifier", 0x020000, 0x10)


def test_combo_macro_preserved_raw():
    raw = rec(0x03, 0, 0, 0xFF, 0xEC, 0x27, 0xE1, 0, 0, 0, 0, 0, 0, 0, 0, 0x02)
    k = rkf._parse_record(raw)
    assert k.kind == "macro" and k.raw == raw


def test_m4_style_macro_blob():
    raw = rec(0x04, 0x4E, 0x8F, 0x05, 0x04, 0xDC, 0xDD, 0x00, 0xB8, 0x3A, 0xA5, 0, 0, 0, 0, 0x05)
    k = rkf._parse_record(raw)
    assert k.kind == "macro" and k.slot == 4


def test_to_profile_maps_vk_and_modifiers():
    prof = rkf.RkfProfile(pid=0x220, name="t", keys=[
        rkf.RkfKey(slot=13, kind="vk", vk=0x31),
        rkf.RkfKey(slot=10, kind="modifier", fw=0x020000),
        rkf.RkfKey(slot=3, kind="macro", raw=b"\xff"),
    ])
    out = rkf.to_omakeyfig_profile(prof, lambda vk: vk << 8)
    assert out["mappings"] == {"13": 0x3100, "10": 0x020000}
    assert out["unresolved_macros"] == {3: "ff"}
