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
    assert short_label(by_slot[1]) == "M5"  # macro col prints M5..M1 top-down
    assert short_label(by_slot[5]) == "M1"
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


def test_fn_user_confirmed_legends():
    from omakeyfig.keyboard_widget import fn_legend
    assert fn_legend(80) == "Home"     # Fn+[
    assert fn_legend(86) == "ScrLk"    # Fn+]
    assert fn_legend(92) == "Style"    # Fn+\ lighting style
    assert fn_legend(52) == "Hue"      # Fn+N hue cycle


def test_keycap_overrides(tmp_path, monkeypatch):
    from omakeyfig import keycaps as _k
    monkeypatch.setattr(_k, "keycaps_file", lambda: tmp_path / "keycaps.toml")
    assert _k.display_label(14, "Q") == "Q"
    _k.set_keycap(14, "ESC")
    assert _k.display_label(14, "Q") == "ESC"
    _k.set_keycap(14, None)
    assert _k.display_label(14, "Q") == "Q"


def test_keywidget_uses_keycap(tmp_path, monkeypatch):
    from omakeyfig import keycaps as _k
    from omakeyfig.keyboard_widget import KeyWidget
    from omakeyfig.layouts import load_layout
    monkeypatch.setattr(_k, "keycaps_file", lambda: tmp_path / "keycaps.toml")
    monkeypatch.setattr("omakeyfig.keycaps.keycaps_file", lambda: tmp_path / "keycaps.toml")
    _k.set_keycap(14, "ESC")
    kd = next(k for k in load_layout(0x0220) if k.slot == 14)
    w = KeyWidget(kd, 5)
    assert w.keycap_label == "ESC" and w.base_label == "Q"


def test_label_views_cycle():
    from omakeyfig.keyboard_widget import KeyWidget
    from omakeyfig.layouts import load_layout
    kd = next(k for k in load_layout(0x0220) if k.slot == 14)
    w = KeyWidget(kd, 5)
    assert w.shown_label == "Q"  # caps default
    w.set_label_view("slots")
    assert w.shown_label == "14"
    w.set_label_view("binds", "Volume Up")
    assert w.shown_label == "Volume Up"
    w.set_label_view("binds")  # keeps previous bind label
    assert w.shown_label == "Volume Up"
    w.set_label_view("caps")
    assert w.shown_label == "Q"


def test_legend_widget_resolution():
    from omakeyfig.keyboard_widget import LegendWidget
    from omakeyfig.layouts import load_layout
    keys = {k.slot: k for k in load_layout(0x0220)}
    assert LegendWidget(keys[13], 5).legend == "F1"
    assert LegendWidget(keys[14], 5).legend == ""
    assert LegendWidget(keys[99], 5).legend == "Pause"
    w = LegendWidget(keys[13], 5)
    w.set_legends(True)  # fshift: Fn+number row = media
    assert w.legend == "MyPC"
    w.set_legends(False)
    assert w.legend == "F1"


def test_match_candidates_binds_first():
    from omakeyfig.keyboard_widget import match_candidates
    from omakeyfig.layouts import load_layout
    keys = load_layout(0x0220)
    base = {35: 0x2C00, 53: 0x2C00}  # both halves send Space
    # space event: both halves, same bind
    cands = match_candidates(keys, base, "space", " ")
    slots = sorted(s for s, _, _ in cands)
    assert slots == [35, 53]
    assert {b for _, b, _ in cands} == {"Space"}
    # right half remapped to Enter: 'enter' matches bind (53) + label (93)
    base[53] = 0x2800
    cands = match_candidates(keys, base, "enter", None)
    got = {s: v for s, _, v in cands}
    assert got[53] == "bind" and got[93] == "label"
    # plain Q press still resolves by label when binds match factory
    fw_q = 0x1400
    cands = match_candidates(keys, {14: fw_q}, "q", "q")
    assert cands[0][0] == 14


def test_row_layout_has_seam():
    from omakeyfig.keyboard_widget import cluster_rows, row_layout
    from omakeyfig.layouts import load_layout
    rows = cluster_rows(load_layout(0x0220))
    # row 0: seam after slot 43 ("6"); row 4: after slot 35 (left space)
    ops0 = row_layout(rows[0])
    kinds = [o[0] for o in ops0]
    assert "seam" in kinds
    seam_i = kinds.index("seam")
    assert ops0[seam_i - 1][2].slot == 43
    assert ops0[seam_i][1] == 6
    ops4 = row_layout(rows[4])
    kinds4 = [o[0] for o in ops4]
    assert "seam" in kinds4
    assert ops4[kinds4.index("seam") - 1][2].slot == 35
    # no seam slot appears twice, every row with one gets exactly one
    for r in rows:
        n = sum(1 for o in row_layout(r) if o[0] == "seam")
        assert n <= 1
