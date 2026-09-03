from omakeyfig.keycodes import MACRO_FW, MACRO_VKS, vk_to_firmware_code
from omakeyfig.layouts import parse_kb_ini


def test_fn_and_macro_codes():
    assert vk_to_firmware_code(0xFA) == 0xB000
    assert vk_to_firmware_code(0xD9) == 0x010400  # M1 = Ctrl+A
    assert vk_to_firmware_code(0xB9) == 0x010600  # M2 = Ctrl+C
    assert vk_to_firmware_code(0xC6) == 0x011900  # M3 = Ctrl+V
    assert vk_to_firmware_code(0xB8) == 0x011B00  # M4 = Ctrl+X
    assert vk_to_firmware_code(0xC7) == 0x011600  # M5 = Ctrl+S
    assert set(MACRO_FW) == set(MACRO_VKS)


def test_regular_key_encoding():
    assert vk_to_firmware_code(0x51) == 0x14 << 8  # Q
    assert vk_to_firmware_code(0x20) == 0x2C << 8  # Space


def test_kb_ini_sample_parses():
    sample = ";Q\nK21=146,82,178,116, 0x02,0x51,0x00,14\n"
    keys = parse_kb_ini(sample)
    assert len(keys) == 1 and keys[0].vk == 0x51 and keys[0].slot == 14
