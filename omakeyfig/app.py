"""Textual TUI. Themed from Omarchy colors.toml at startup."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Footer, Header, Input, Label, ListItem, ListView, RichLog, Select, Static

from omakeyfig import hid_layer, lighting, omarchy
from omakeyfig.keyboard_widget import KeyboardTester, KeyCapture, find_slots
from omakeyfig.layouts import load_layout

# Full RGB effect names get a live board preview approximated as one of the
# four preview modes the tester widget can paint.
PREVIEW_FOR_EFFECT = {"Steady": "Static", "Breathing": "Breathing", "Rainbow": "Rainbow"}


class TesterScreen(VerticalScroll):
    """Live keypress tester: press keys on the S70, see what the OS delivers."""

    def compose(self) -> ComposeResult:
        yield Label("Key tester — press keys on the keyboard", classes="panel-title")
        yield KeyCapture("… (press any key)", id="capture")
        yield KeyboardTester(load_layout(0x0220), omarchy.keyboard_accent())
        with Horizontal():
            yield Button("Clear", id="btn-clear")
            yield Button("Back", id="btn-back")
        yield RichLog(id="keylog", highlight=True, max_lines=200)


class LightingScreen(VerticalScroll):
    """Lighting controls with a live board preview. Push sends it to hardware."""

    def compose(self) -> ComposeResult:
        accent = omarchy.keyboard_accent()
        yield Label("Lighting — preview on the board, then push", classes="panel-title")
        with Horizontal():
            yield Label("Effect ")
            yield Select([(e, e) for e in lighting.EFFECTS], value="Steady", id="led-effect")
        with Horizontal():
            yield Label("Color ")
            yield Input(value=accent, id="led-color", max_length=7)
        with Horizontal(classes="stepper"):
            yield Label("Brightness")
            yield Button("−", id="btn-b-minus")
            yield Static("5", id="val-b")
            yield Button("+", id="btn-b-plus")
        with Horizontal(classes="stepper"):
            yield Label("Speed")
            yield Button("−", id="btn-s-minus")
            yield Static("5", id="val-s")
            yield Button("+", id="btn-s-plus")
        with Horizontal(classes="stepper"):
            yield Label("Sleep")
            yield Button("−", id="btn-z-minus")
            yield Static("5", id="val-z")
            yield Button("+", id="btn-z-plus")
        yield KeyboardTester(load_layout(0x0220), accent)
        with Horizontal():
            yield Button("Push to keyboard", id="btn-push")
            yield Button("Back", id="btn-back")
        yield Static("", id="light-status")

    def lighting_state(self) -> lighting.LightingState:
        app = self.app
        color = app.query_one("#led-color", Input).value.strip() or "#000000"
        return lighting.LightingState(
            effect=str(app.query_one("#led-effect", Select).value),
            brightness=app.light_b, speed=app.light_s, sleep=app.light_z,
            color=color,
        )


class OmakeyfigApp(App):
    TITLE = "omakeyfig — RK keyboard customizer (unofficial)"
    CSS = """
    Screen { background: $surface; }
    #side { width: 28; border-right: solid $primary; }
    #main { padding: 1 2; }
    .panel-title { text-style: bold; color: $accent; margin-bottom: 1; }
    .stepper Label { width: 12; }
    .stepper Static { width: 14; }
    .stepper Button { width: 6; }
    #led-effect { width: 1fr; }
    #led-color { width: 12; }
    """
    SECTIONS = ["Devices", "Remap", "Lighting", "Macros M1-M5", "Profiles", "Key tester"]
    SECTION_HELP = {
        "Devices": "USB status of the S70. Use the Device status button.",
        "Remap": "Visual remap editor lands here next.",
        "Macros M1-M5": "Factory: M1=Ctrl+A M2=Ctrl+C M3=Ctrl+V M4=Ctrl+X M5=Ctrl+S.",
        "Profiles": "For now: `omakeyfig save-profile <name>` / `write-map --profile`.",
    }

    def __init__(self) -> None:
        super().__init__()
        self._status = "Connect the S70 via USB, then pick a section."
        self._screen: str | None = None  # None | "tester" | "lighting"
        self.light_b = 5
        self.light_s = 5
        self.light_z = 5

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
        self._screen = None
        main = self.query_one("#main", Vertical)
        main.remove_children()
        main.mount(Label("omakeyfig", classes="panel-title"))
        main.mount(Static(f"Theme accent: {omarchy.keyboard_accent()}", id="accent"))
        main.mount(Static(self._status, id="status"))
        row = Horizontal()
        main.mount(row)
        row.mount(Button("Device status", id="btn-status"))
        row.mount(Button("Dry-run write", id="btn-dry"))

    def show_screen(self, name: str) -> None:
        self._screen = name
        main = self.query_one("#main", Vertical)
        main.remove_children()
        main.mount(LightingScreen() if name == "lighting" else TesterScreen())
        if name == "tester":
            self.set_timer(0.05, lambda: self.query_one("#capture", KeyCapture).focus())

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        idx = event.control.index
        label = self.SECTIONS[idx] if idx is not None and 0 <= idx < len(self.SECTIONS) else ""
        if label == "Key tester":
            self.show_screen("tester")
        elif label == "Lighting":
            self.show_screen("lighting")
        else:
            if self._screen is not None:
                self.show_home()
            try:
                self.query_one("#status", Static).update(
                    self.SECTION_HELP.get(label, self._status))
            except Exception:
                pass

    # -- key tester ---------------------------------------------------------
    def record_key(self, key: str, character: str | None) -> None:
        if self._screen != "tester":
            return
        try:
            cap = self.query_one("#capture", KeyCapture)
            log = self.query_one("#keylog", RichLog)
            board = self.query_one("#kb", KeyboardTester)
        except Exception:
            return
        shown = repr(character) if character else "—"
        cap.update(f"[bold]{key}[/bold]  char={shown}")
        slots = find_slots(board.keys, key, character)
        if slots:
            board.mark_pressed(slots)
            log.write(f"key={key} char={shown} -> slot(s) {slots}")
        else:
            log.write(f"key={key} char={shown} (no board match)")

    async def on_key(self, event) -> None:
        if self._screen == "tester" and event.key not in ("tab", "shift+tab"):
            self.record_key(event.key, event.character)

    # -- lighting ------------------------------------------------------------
    def refresh_light_labels(self) -> None:
        try:
            self.query_one("#val-b", Static).update(str(self.light_b))
            self.query_one("#val-s", Static).update(str(self.light_s))
            self.query_one("#val-z", Static).update(str(self.light_z))
        except Exception:
            pass

    def preview_lighting(self) -> None:
        if self._screen != "lighting":
            return
        try:
            effect = str(self.query_one("#led-effect", Select).value)
            board = self.query_one("#kb", KeyboardTester)
        except Exception:
            return
        board.set_led_mode(PREVIEW_FOR_EFFECT.get(effect, "Static"))

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "led-effect":
            self.preview_lighting()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "led-color" and self._screen == "lighting":
            v = event.value.strip()
            if len(v) == 7 and v.startswith("#"):
                try:
                    int(v[1:], 16)
                except ValueError:
                    return
                try:
                    board = self.query_one("#kb", KeyboardTester)
                except Exception:
                    return
                board.accent = v
                board._paint()

    def push_lighting(self) -> None:
        try:
            screen = self.query_one("LightingScreen")
            status = screen.query_one("#light-status", Static)
            color = screen.query_one("#led-color", Input).value.strip()
            effect = str(screen.query_one("#led-effect", Select).value)
        except Exception:
            return
        try:
            state = lighting.LightingState(effect=effect, brightness=self.light_b,
                                           speed=self.light_s, sleep=self.light_z,
                                           color=color)
            buf = lighting.build_lighting_report(state)  # validates effect + color
        except ValueError as e:
            status.update(f"Invalid: {e}")
            return
        try:
            dev = hid_layer.RKDevice()
            try:
                dev.write_feature_buffers([buf])
            finally:
                dev.close()
            status.update(f"Pushed: {lighting.describe(state)}")
        except Exception as e:
            status.update(f"Push failed: {e}")

    # -- buttons --------------------------------------------------------------
    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "btn-back":
            self.show_home()
            self.query_one("#sections", ListView).focus()
            return
        if bid == "btn-clear":
            try:
                self.query_one("#keylog", RichLog).clear()
                self.query_one("#capture", KeyCapture).update("… (press any key)")
                self.query_one("#kb", KeyboardTester).clear_pressed()
            except Exception:
                pass
            return
        if bid == "btn-push":
            self.push_lighting()
            return
        steps = {"btn-b-minus": ("light_b", -1), "btn-b-plus": ("light_b", 1),
                 "btn-s-minus": ("light_s", -1), "btn-s-plus": ("light_s", 1),
                 "btn-z-minus": ("light_z", -1), "btn-z-plus": ("light_z", 1)}
        if bid in steps:
            attr, delta = steps[bid]
            setattr(self, attr, max(0, min(10, getattr(self, attr) + delta)))
            self.refresh_light_labels()
            return
        from omakeyfig import cli as _cli
        try:
            status = self.query_one("#status", Static)
        except Exception:
            return
        if bid == "btn-status":
            try:
                devs = hid_layer.list_rk_devices()
                status.update(str(devs) if devs else "No RK devices found (USB cable required).")
            except RuntimeError as e:
                status.update(str(e))
        elif bid == "btn-dry":
            rc = _cli.main(["write-map", "--dry-run"])
            status.update(f"dry-run exited {rc} (see terminal output).")


def run() -> int:
    OmakeyfigApp().run()
    return 0
