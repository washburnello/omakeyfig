"""Textual TUI. Themed from Omarchy colors.toml at startup."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, Footer, Header, Label, ListItem, ListView, RichLog, Static

from omakeyfig import omarchy


class KeyCapture(Static, can_focus=True):
    """Focusable display that consumes no keys itself, so every keypress
    bubbles up to the app handler (except app-level bindings)."""

    DEFAULT_CSS = "KeyCapture { height: 5; content-align: center middle; border: solid $primary; }"


class TesterScreen(Vertical):
    """Live keypress tester: press keys on the S70, see what the OS delivers."""

    def compose(self) -> ComposeResult:
        yield Label("Key tester — press keys on the keyboard", classes="panel-title")
        yield KeyCapture("… (press any key)", id="capture")
        yield RichLog(id="keylog", highlight=True, max_lines=200)
        with Horizontal():
            yield Button("Clear", id="btn-clear")
            yield Button("Back", id="btn-back")


class SectionBack(Message):
    pass


class OmakeyfigApp(App):
    TITLE = "omakeyfig — RK keyboard customizer (unofficial)"
    CSS = """
    Screen { background: $surface; }
    #side { width: 28; border-right: solid $primary; }
    #main { padding: 1 2; }
    .panel-title { text-style: bold; color: $accent; margin-bottom: 1; }
    """
    SECTIONS = ["Devices", "Remap", "Lighting", "Macros M1-M5", "Profiles", "Key tester"]
    SECTION_HELP = {
        "Devices": "USB status of the S70. Use the Device status button.",
        "Remap": "Visual remap editor lands here next.",
        "Lighting": "For now: `omakeyfig light --help`. TUI sliders land next.",
        "Macros M1-M5": "Factory: M1=Ctrl+A M2=Ctrl+C M3=Ctrl+V M4=Ctrl+X M5=Ctrl+S.",
        "Profiles": "For now: `omakeyfig save-profile <name>` / `write-map --profile`.",
    }

    def __init__(self) -> None:
        super().__init__()
        self._status = "Connect the S70 via USB, then pick a section."
        self._tester = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="side"):
                yield Label("Sections", classes="panel-title")
                yield ListView(*[ListItem(Label(s)) for s in self.SECTIONS], id="sections")
            with Vertical(id="main"):
                yield Label("omakeyfig", classes="panel-title")
                yield Static(f"Theme accent: {omarchy.keyboard_accent()}", id="accent")
                yield Static(self._status, id="status")
                with Horizontal():
                    yield Button("Device status", id="btn-status")
                    yield Button("Dry-run write", id="btn-dry")
        yield Footer()

    def show_home(self) -> None:
        self._tester = False
        main = self.query_one("#main", Vertical)
        main.remove_children()
        main.mount(Label("omakeyfig", classes="panel-title"))
        main.mount(Static(f"Theme accent: {omarchy.keyboard_accent()}", id="accent"))
        main.mount(Static(self._status, id="status"))
        row = Horizontal()
        main.mount(row)
        row.mount(Button("Device status", id="btn-status"))
        row.mount(Button("Dry-run write", id="btn-dry"))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        idx = event.control.index
        label = self.SECTIONS[idx] if idx is not None and 0 <= idx < len(self.SECTIONS) else ""
        if label == "Key tester":
            self._tester = True
            main = self.query_one("#main", Vertical)
            main.remove_children()
            main.mount(TesterScreen())
            self.set_timer(0.05, lambda: self.query_one("#capture", KeyCapture).focus())
        else:
            if self._tester:
                self.show_home()
            try:
                self.query_one("#status", Static).update(
                    self.SECTION_HELP.get(label, self._status))
            except Exception:
                pass

    def record_key(self, key: str, character: str | None) -> None:
        if not self._tester:
            return
        try:
            cap = self.query_one("#capture", KeyCapture)
            log = self.query_one("#keylog", RichLog)
        except Exception:
            return
        shown = repr(character) if character else "—"
        cap.update(f"[bold]{key}[/bold]  char={shown}")
        log.write(f"key={key} char={shown}")

    async def on_key(self, event) -> None:
        if self._tester and event.key not in ("tab", "shift+tab"):
            self.record_key(event.key, event.character)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.show_home()
            self.query_one("#sections", ListView).focus()
            return
        if event.button.id == "btn-clear":
            try:
                self.query_one("#keylog", RichLog).clear()
                self.query_one("#capture", KeyCapture).update("… (press any key)")
            except Exception:
                pass
            return
        from omakeyfig import cli as _cli
        try:
            status = self.query_one("#status", Static)
        except Exception:
            return
        if event.button.id == "btn-status":
            try:
                from omakeyfig import hid_layer
                devs = hid_layer.list_rk_devices()
                status.update(str(devs) if devs else "No RK devices found (USB cable required).")
            except RuntimeError as e:
                status.update(str(e))
        elif event.button.id == "btn-dry":
            rc = _cli.main(["write-map", "--dry-run"])
            status.update(f"dry-run exited {rc} (see terminal output).")


def run() -> int:
    OmakeyfigApp().run()
    return 0
