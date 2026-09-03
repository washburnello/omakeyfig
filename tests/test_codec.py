from omakeyfig import codec


def test_encode_shape_and_framing():
    bufs = codec.encode_keymap({0: 0x0400, 1: 0x0500}, 74)
    assert len(bufs) == codec.N_BUFFERS
    assert all(len(b) == codec.BUFFER_LEN for b in bufs)
    for i, b in enumerate(bufs):
        assert b[0] == codec.REPORT_ID
        assert b[1] == codec.N_BUFFERS
        assert b[2] == i + 1
    assert (bufs[0][3], bufs[0][4]) == (0x01, 0xF8)


def test_big_endian_key_slots():
    # A key (HID 0x04 -> fw 0x0400) must land big-endian: 00 00 04 00.
    bufs = codec.encode_keymap({0: 0x0400}, 74)
    assert bytes(bufs[0][5:9]) == bytes((0x00, 0x00, 0x04, 0x00))
    # Modifier bitflag 0x010000 -> 00 01 00 00.
    bufs = codec.encode_keymap({0: 0x010000}, 74)
    assert bytes(bufs[0][5:9]) == bytes((0x00, 0x01, 0x00, 0x00))


def test_round_trip():
    mapping = {i: (0x0400 + i) & 0xFFFFFFFF for i in range(74)}
    bufs = codec.encode_keymap(mapping, 74)
    assert codec.decode_keymap(bufs, 74) == mapping


def test_single_key_change_still_writes_all():
    full = {i: 0x0400 for i in range(74)}
    one = dict(full)
    one[10] = 0x0500
    a, b = codec.encode_keymap(full, 74), codec.encode_keymap(one, 74)
    assert len(a) == len(b) == 9
    assert a != b  # exactly one key's bytes differ
