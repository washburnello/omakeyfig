from omakeyfig.keycodes import MACRO_VKS, vk_to_firmware_code
from omakeyfig.layouts import parse_kb_ini


def test_fn_and_macro_markers():
    assert vk_to_firmware_code(0xFA) == 0xB000
    for vk in MACRO_VKS:
        assert vk_to_firmware_code(vk) & 0xF000 == 0xF000


def test_regular_key_encoding():
    assert vk_to_firmware_code(0x51) == 0x14 << 8  # Q
    assert vk_to_firmware_code(0x20) == 0x2C << 8  # Space


def test_kb_ini_sample_parses():
    sample = ";Q\nK21=146,82,178,116, 0x02,0x51,0x00,14\n"
    keys = parse_kb_ini(sample)
    assert len(keys) == 1 and keys[0].vk == 0x51 and keys[0].slot == 14
