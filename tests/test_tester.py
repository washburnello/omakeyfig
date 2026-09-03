import asyncio

from textual.widgets import Button, ListView, Select

from omakeyfig.app import OmakeyfigApp
from omakeyfig.keyboard_widget import KeyboardTester


def _run(coro):
    return asyncio.run(coro)


async def _open_tester(app):
    lv = app.query_one("#sections", ListView)
    lv.focus()
    return lv


def test_key_tester_records_presses():
    async def scenario():
        app = OmakeyfigApp()
        async with app.run_test() as pilot:
            lv = await _open_tester(app)
            for _ in range(5):
                await pilot.press("down")
            await pilot.press("enter")
            await pilot.pause()
            assert app._screen == "tester"
            await pilot.press("q", "z")
            await pilot.pause()
            board = app.query_one("#kb", KeyboardTester)
            assert board.pressed == {14, 16}
            log = app.query_one("#keylog")
            dump = "\n".join(str(getattr(line, "text", line)) for line in log.lines)
            assert "key=q" in dump
            assert "key=z" in dump
    _run(scenario())


def test_clear_resets_indicators():
    async def scenario():
        app = OmakeyfigApp()
        async with app.run_test() as pilot:
            lv = await _open_tester(app)
            for _ in range(5):
                await pilot.press("down")
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("q")
            await pilot.pause()
            board = app.query_one("#kb", KeyboardTester)
            assert board.pressed == {14}
            from textual.widgets import Button
            btn = app.query_one("#btn-clear", Button)
            btn.scroll_visible()
            await pilot.pause()
            await pilot.pause()
            await pilot.click("#btn-clear")
            await pilot.pause()
            assert board.pressed == set()
            assert list(app.query_one("#keylog").lines) == []
    _run(scenario())


def test_board_rows_are_flush():
    """Bordered rows must sit directly adjacent — no blank lines between."""
    async def scenario():
        app = OmakeyfigApp()
        async with app.run_test() as pilot:
            lv = await _open_tester(app)
            for _ in range(5):
                await pilot.press("down")
            await pilot.press("enter")
            await pilot.pause()
            rows = list(app.query(".kb-row"))
            assert len(rows) == 5
            for row in rows:
                assert row.region.height == 3, row.region
            ys = [row.region.y for row in rows]
            for a, b in zip(ys, ys[1:]):
                assert b - a == 3, ys
    _run(scenario())


def test_lighting_screen_preview_no_hardware():
    """Lighting screen previews without touching hardware."""
    async def scenario():
        app = OmakeyfigApp()
        async with app.run_test() as pilot:
            lv = app.query_one("#sections", ListView)
            lv.focus()
            await pilot.pause()
            await pilot.press("down", "down")
            await pilot.press("enter")
            await pilot.pause()
            assert app._screen == "lighting"
            board = app.query_one("#kb", KeyboardTester)
            # Default effect Steady previews as Static on open.
            assert board.led_mode == "Static"
            sel = app.query_one("#led-effect", Select)
            sel.value = "Rainbow"
            await pilot.pause()
            assert board.led_mode == "Rainbow"
            # Steppers clamp 0..10.
            assert app.light_b == 5
            plus = app.query_one("#btn-b-plus", Button)
            plus.scroll_visible()
            await pilot.pause()
            await pilot.pause()
            await pilot.click("#btn-b-plus")
            await pilot.pause()
            assert app.light_b == 6
    _run(scenario())


def test_led_mode_switch():
    async def scenario():
        app = OmakeyfigApp()
        async with app.run_test() as pilot:
            lv = await _open_tester(app)
            for _ in range(5):
                await pilot.press("down")
            await pilot.press("enter")
            await pilot.pause()
            board = app.query_one("#kb", KeyboardTester)
            assert board.led_mode == "Off"
            board.set_led_mode("Static")
            assert board.led_mode == "Static"
            w = board.by_slot[14]
            assert str(w.styles.background) != board.base_bg
    _run(scenario())


def test_fn_toggle_swaps_labels():
    """Fn button swaps board labels to Fn legends and back."""
    async def scenario():
        app = OmakeyfigApp()
        async with app.run_test() as pilot:
            lv = await _open_tester(app)
            for _ in range(5):
                await pilot.press("down")
            await pilot.press("enter")
            await pilot.pause()
            board = app.query_one("#kb", KeyboardTester)
            assert board.fn_view is False
            assert board.by_slot[13].shown_label == "1"
            from textual.widgets import Button
            fn = app.query_one("#btn-fn", Button)
            fn.focus()
            await pilot.pause(0.4)
            await pilot.press("enter")
            await pilot.pause(0.4)
            assert board.fn_view is True
            assert board.by_slot[13].shown_label == "F1"
            assert board.by_slot[14].shown_label == "?"
            await pilot.press("enter")
            await pilot.pause(0.4)
            assert board.fn_view is False
            assert board.by_slot[13].shown_label == "1"
    _run(scenario())
