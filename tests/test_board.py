from omakeyfig.keyboard_widget import cluster_rows, find_slots, short_label
from omakeyfig.layouts import load_layout


def s70():
    return load_layout(0x0220)


def test_rows_and_key_count():
    keys = s70()
    rows = cluster_rows(keys)
    assert len(rows) == 5
    assert sum(len(r) for r in rows) == 74
    # rows run top to bottom, keys left to right
    assert rows[0][0].rect[1] < rows[-1][0].rect[1]
    assert all(r[i].rect[0] <= r[i + 1].rect[0] for r in rows for i in range(len(r) - 1))


def test_short_labels():
    by_slot = {k.slot: k for k in s70()}
    assert short_label(by_slot[14]) == "Q"
    assert short_label(by_slot[1]) == "M1"
    assert short_label(by_slot[35]) == "Space"


def test_find_slots_printable():
    keys = s70()
    assert find_slots(keys, "q", "q") == [14]
    assert find_slots(keys, "Q", "Q") == [14]  # shift handled via lower
    assert find_slots(keys, "!", "!") == find_slots(keys, "1", "1")  # shifted symbol
    assert find_slots(keys, "z", "z") == [16]


def test_find_slots_special():
    keys = s70()
    assert find_slots(keys, "space", None) == [35, 53]  # split spacebar, both light
    assert find_slots(keys, "enter", None) == [93]
    assert find_slots(keys, "escape", None) == [7]
    assert find_slots(keys, "shift", None) == sorted(find_slots(keys, "shift", None))
    assert set(find_slots(keys, "shift", None)) == {10, 88}
    assert find_slots(keys, "left", None) == [89]


def test_fn_layer_legends():
    from omakeyfig.keyboard_widget import fn_legend
    assert fn_legend(13) == "F1"    # Fn+1
    assert fn_legend(85) == "F12"   # Fn+=
    assert fn_legend(99) == "Pause"  # user-verified
    assert fn_legend(100) == "End"   # user-verified
    assert fn_legend(94) == "Brt+"
    assert fn_legend(14) is None     # Q: unknown until tester-confirmed
    assert fn_legend(71) is None     # Fn itself has no Fn legend


def test_fshift_tables():
    from omakeyfig.keyboard_widget import FSHIFT_FN_MEDIA, FSHIFT_KEYS
    assert len(FSHIFT_KEYS) == 12 and len(FSHIFT_FN_MEDIA) == 12
    assert FSHIFT_KEYS[13] == "F1" and FSHIFT_KEYS[85] == "F12"
    assert FSHIFT_FN_MEDIA[61] == "Play" and FSHIFT_FN_MEDIA[85] == "Vol+"
    assert set(FSHIFT_KEYS) == set(FSHIFT_FN_MEDIA)  # same physical keys
