import asyncio

from omakeyfig.app import OmakeyfigApp


def _run(coro):
    return asyncio.run(coro)


def test_key_tester_records_presses():
    async def scenario():
        app = OmakeyfigApp()
        async with app.run_test() as pilot:
            # Focus the section list and move to "Key tester" (last item).
            from textual.widgets import ListView
            lv = app.query_one("#sections", ListView)
            lv.focus()
            await pilot.pause()
            for _ in range(5):
                await pilot.press("down")
            await pilot.press("enter")
            await pilot.pause()
            assert app._tester is True
            await pilot.press("q", "z")
            await pilot.pause()
            log = app.query_one("#keylog")
            dump = "\n".join(str(getattr(line, "text", line)) for line in log.lines)
            assert "key=q" in dump
            assert "key=z" in dump
    _run(scenario())
