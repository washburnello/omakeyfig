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


# Full alphabet cross-checked against KludgeKnight's KEY_MAP (HID usages).
KK_ALPHABET = {
    0x41: 0x0400, 0x42: 0x0500, 0x43: 0x0600, 0x44: 0x0700,
    0x45: 0x0800, 0x46: 0x0900, 0x47: 0x0A00, 0x48: 0x0B00,
    0x49: 0x0C00, 0x4A: 0x0D00, 0x4B: 0x0E00, 0x4C: 0x0F00,
    0x4D: 0x1000, 0x4E: 0x1100, 0x4F: 0x1200, 0x50: 0x1300,
    0x51: 0x1400, 0x52: 0x1500, 0x53: 0x1600, 0x54: 0x1700,
    0x55: 0x1800, 0x56: 0x1900, 0x57: 0x1A00, 0x58: 0x1B00,
    0x59: 0x1C00, 0x5A: 0x1D00,
}


def test_alphabet_matches_kludgeknight():
    for vk, fw in KK_ALPHABET.items():
        assert vk_to_firmware_code(vk) == fw, f"VK {vk:#x}"


def test_kb_ini_sample_parses():
    sample = ";Q\nK21=146,82,178,116, 0x02,0x51,0x00,14\n"
    keys = parse_kb_ini(sample)
    assert len(keys) == 1 and keys[0].vk == 0x51 and keys[0].slot == 14
