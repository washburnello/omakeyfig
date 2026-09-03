"""Textual TUI skeleton. Themed from Omarchy colors.toml at startup."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Label, ListItem, ListView, Static

from omakeyfig import omarchy


class OmakeyfigApp(App):
    TITLE = "omakeyfig — RK keyboard customizer (unofficial)"
    CSS = """
    Screen { background: $surface; }
    #side { width: 28; border-right: solid $primary; }
    #main { padding: 1 2; }
    .panel-title { text-style: bold; color: $accent; margin-bottom: 1; }
    """

    def __init__(self) -> None:
        super().__init__()
        self._status = "Connect the S70 via USB, then pick a section."

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="side"):
                yield Label("Sections", classes="panel-title")
                yield ListView(
                    ListItem(Label("Devices")),
                    ListItem(Label("Remap")),
                    ListItem(Label("Lighting")),
                    ListItem(Label("Macros M1-M5")),
                    ListItem(Label("Profiles")),
                )
            with Vertical(id="main"):
                yield Label("omakeyfig", classes="panel-title")
                yield Static(f"Theme accent: {omarchy.keyboard_accent()}", id="accent")
                yield Static(self._status, id="status")
                with Horizontal():
                    yield Button("Device status", id="btn-status")
                    yield Button("Dry-run write", id="btn-dry")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        from omakeyfig import cli as _cli
        status = self.query_one("#status", Static)
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
