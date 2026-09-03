from omakeyfig import codec


def test_encode_shape():
    bufs = codec.encode_keymap({0: 0x0400, 1: 0x0500}, 74)
    assert len(bufs) == codec.N_BUFFERS
    assert all(len(b) == codec.BUFFER_LEN for b in bufs)
    assert all(b[0] == codec.REPORT_ID for b in bufs)
    assert (bufs[0][3], bufs[0][4]) == (0x01, 0xF8)


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
