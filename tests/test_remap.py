import asyncio

from textual.widgets import Input, ListView

from omakeyfig import remap
from omakeyfig.app import OmakeyfigApp
from omakeyfig.keyboard_widget import KeyboardTester


def _run(coro):
    return asyncio.run(coro)


async def _open_remap(app, pilot):
    lv = app.query_one("#sections", ListView)
    lv.focus()
    await pilot.pause()
    await pilot.press("down")  # Devices(0) -> Remap(1)
    await pilot.press("enter")
    await pilot.pause()
    assert app._screen == "remap"


def test_catalog_search():
    assert len(remap.search("")) == len(remap.ACTIONS) == 103
    vols = remap.search("vol")
    assert {a.label for a in vols} == {"Volume Up", "Volume Down"}
    assert remap.fw_for(0x51) == 0x1400  # Q
    assert remap.label_for_fw(0x010000E9) == "Volume Up"


def test_cursor_moves_physically():
    async def scenario():
        app = OmakeyfigApp()
        async with app.run_test() as pilot:
            await _open_remap(app, pilot)
            board = app.query_one("#kb", KeyboardTester)
            assert board.move_cursor(0, 0) == 1  # first key: M1
            assert board.move_cursor(0, 1) == 2  # down into row 2
            right = board.move_cursor(1, 0)
            assert right is not None and right != 2
            assert board.move_cursor(-100, 0) == board.rows[1][0].slot  # clamp
    _run(scenario())


def test_assign_undo_flow():
    async def scenario():
        app = OmakeyfigApp()
        async with app.run_test() as pilot:
            await _open_remap(app, pilot)
            board = app.query_one("#kb", KeyboardTester)
            board.select_slot(14)  # Q
            app.refresh_remap_ui()
            await pilot.pause()
            app.remap_assign(0xAF)  # Volume Up
            assert app.remap_pending == {14: 0x010000E9}
            assert app.remap_diff_lines() == ["slot 14: Q -> Volume Up"]
            app.remap_undo()
            assert app.remap_pending == {}
    _run(scenario())


def test_filter_and_assign_via_ui():
    async def scenario():
        app = OmakeyfigApp()
        async with app.run_test() as pilot:
            await _open_remap(app, pilot)
            board = app.query_one("#kb", KeyboardTester)
            board.select_slot(14)
            app.refresh_remap_ui()
            filt = app.query_one("#remap-filter", Input)
            filt.focus()
            await pilot.pause()
            await pilot.press(*list("vol"))
            await pilot.pause()
            lv = app.query_one("#remap-actions", ListView)
            texts = []
            for item in lv.children:
                try:
                    lab = item.query_one("Label")
                    texts.append(str(getattr(lab, "content", None) or lab.render_line(0).text))
                except Exception:
                    texts.append("")
            assert any("Volume Up" in t for t in texts), texts
            assert all("Volume" in t or "Brightness" in t for t in texts), texts
    _run(scenario())


def test_push_confirm_writes_and_clears():
    """Confirm modal gates the write; mocked device receives encoded map."""
    import omakeyfig.app as appmod
    from omakeyfig import codec
    from textual.widgets import Button

    captured: dict = {}

    class FakeDev:
        def write_feature_buffers(self, bufs, dry_run=False):
            captured["bufs"] = bufs
            return bufs

        def close(self):
            pass

    async def scenario():
        app = OmakeyfigApp()
        async with app.run_test() as pilot:
            await _open_remap(app, pilot)
            board = app.query_one("#kb", KeyboardTester)
            board.select_slot(14)
            app.remap_assign(0xAF)  # Q -> Volume Up
            assert app.remap_pending == {14: 0x010000E9}
            orig = appmod.hid_layer.RKDevice
            appmod.hid_layer.RKDevice = lambda *a, **k: FakeDev()
            try:
                app.remap_push()
                await pilot.pause()
                assert app.screen_stack[-1].__class__.__name__ == "ConfirmPush"
                yes = app.screen_stack[-1].query_one("#btn-confirm-yes", Button)
                yes.scroll_visible()
                await pilot.pause(0.4)
                await pilot.click("#btn-confirm-yes")
                await pilot.pause(0.4)
            finally:
                appmod.hid_layer.RKDevice = orig
            assert "bufs" in captured, "device write never happened"
            assert codec.decode_keymap(captured["bufs"], app.remap_n_keys)[14] == 0x010000E9
            assert app.remap_pending == {}  # cleared after push
    _run(scenario())


def test_help_overlay():
    async def scenario():
        app = OmakeyfigApp()
        async with app.run_test() as pilot:
            await _open_remap(app, pilot)
            await pilot.press("question_mark")
            await pilot.pause()
            assert app.screen_stack[-1].__class__.__name__ == "HelpOverlay"
            await pilot.press("escape")
            await pilot.pause()
    _run(scenario())


def test_macro_combo_encoding():
    async def scenario():
        app = OmakeyfigApp()
        async with app.run_test() as pilot:
            lv = app.query_one("#sections", ListView)
            lv.focus()
            await pilot.pause()
            await pilot.press("down", "down", "down", "enter")
            await pilot.pause()
            assert app._screen == "macros"
            app.macro_slot = 2
            app.macro_mods = {"m-lctrl", "m-lshift"}
            app.macro_base = 0x54  # T
            assert app.macro_combo_fw() == 0x010000 | 0x020000 | 0x1700
            app.macro_mods = set()
            app.macro_base = 0xB3  # Play/Pause, no mods
            assert app.macro_combo_fw() == 0x010000CD
    _run(scenario())


def test_macro_assign_push_mocked():
    import omakeyfig.app as appmod
    from omakeyfig import codec
    from textual.widgets import Button
    captured: dict = {}

    class FakeDev:
        def write_feature_buffers(self, bufs, dry_run=False):
            captured["bufs"] = bufs
            return bufs

        def close(self):
            pass

    async def scenario():
        app = OmakeyfigApp()
        async with app.run_test() as pilot:
            lv = app.query_one("#sections", ListView)
            lv.focus()
            await pilot.pause()
            await pilot.press("down", "down", "down", "enter")
            await pilot.pause()
            app.macro_slot = 2
            app.macro_mods = {"m-lctrl"}
            app.macro_base = 0x43  # C -> Ctrl+C
            orig = appmod.hid_layer.RKDevice
            appmod.hid_layer.RKDevice = lambda *a, **k: FakeDev()
            try:
                app.macro_assign()
                await pilot.pause()
                assert app.screen_stack[-1].__class__.__name__ == "ConfirmPush"
                yes = app.screen_stack[-1].query_one("#btn-confirm-yes", Button)
                yes.scroll_visible()
                await pilot.pause(0.4)
                await pilot.click("#btn-confirm-yes")
                await pilot.pause(0.4)
            finally:
                appmod.hid_layer.RKDevice = orig
            assert codec.decode_keymap(captured["bufs"], 102)[2] == 0x010600
    _run(scenario())


def test_profiles_save_apply_delete_mocked():
    import omakeyfig.app as appmod
    from omakeyfig import codec, profiles
    from textual.widgets import Button, Input
    captured: dict = {}

    class FakeDev:
        def write_feature_buffers(self, bufs, dry_run=False):
            captured["bufs"] = bufs
            return bufs

        def close(self):
            pass

    async def scenario():
        app = OmakeyfigApp()
        async with app.run_test() as pilot:
            lv = app.query_one("#sections", ListView)
            lv.focus()
            await pilot.pause()
            await pilot.press("down", "down", "down", "down", "enter")
            await pilot.pause()
            assert app._screen == "profiles"
            assert "washburnello-restore" in app._profile_names
            # save a new profile from the effective map
            name_in = app.query_one("#profile-name", Input)
            name_in.value = "tui-test-tmp"
            app.profile_save()
            await pilot.pause()
            assert "tui-test-tmp" in app._profile_names
            # select it and apply with mocked device
            app.profile_selected = "tui-test-tmp"
            orig = appmod.hid_layer.RKDevice
            appmod.hid_layer.RKDevice = lambda *a, **k: FakeDev()
            try:
                app.profile_apply()
                await pilot.pause()
                assert app.screen_stack[-1].__class__.__name__ == "ConfirmPush"
                yes = app.screen_stack[-1].query_one("#btn-confirm-yes", Button)
                yes.scroll_visible()
                await pilot.pause(0.4)
                await pilot.click("#btn-confirm-yes")
                await pilot.pause(0.4)
            finally:
                appmod.hid_layer.RKDevice = orig
            assert "bufs" in captured
            assert codec.decode_keymap(captured["bufs"], 102)[14] == 0x1400  # Q intact
            # delete it
            app.profile_selected = "tui-test-tmp"
            app.profile_delete()
            assert "tui-test-tmp" not in app._profile_names
            profiles.profiles_dir().joinpath("tui-test-tmp.json").unlink(missing_ok=True)
    _run(scenario())


def test_export_json_contract():
    import json
    from omakeyfig import cli as _cli
    import io
    from contextlib import redirect_stdout
    buf = io.StringIO()
    with redirect_stdout(buf):
        assert _cli.main(["export", "--pid", "0x220"]) == 0
    d = json.loads(buf.getvalue())
    assert set(d) == {"pid", "n_keys", "devices", "rows", "defaults",
                      "actions", "effects", "accent", "seam_after", "seam_cells"}
    assert sorted(d["seam_after"]) == [35, 38, 39, 40, 43] and d["seam_cells"] == 6
    assert sum(len(r) for r in d["rows"]) == 74
    assert len(d["actions"]) == 103 and len(d["effects"]) == 21
    q = next(c for r in d["rows"] for c in r if c["slot"] == 14)
    assert q["label"] == "Q" and q["char"] == "q" and "q" in q["names"]
    assert d["defaults"]["14"] == 0x1400
