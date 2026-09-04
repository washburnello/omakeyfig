"""Textual TUI. Themed from Omarchy colors.toml at startup."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Input, Label, ListItem, ListView, RichLog, Select, Static

from omakeyfig import codec, hid_layer, lighting, omarchy, remap
from omakeyfig.keyboard_widget import KeyboardTester, KeyCapture, find_slots
from omakeyfig.layouts import load_layout

# Full RGB effect names get a live board preview approximated as one of the
# four preview modes the tester widget can paint.
PREVIEW_FOR_EFFECT = {"Steady": "Static", "Breathing": "Breathing", "Rainbow": "Rainbow"}


class HelpOverlay(ModalScreen):
    """`?` keybinding overlay, charm-style."""

    BINDINGS = [
        ("h j k l / arrows", "move board cursor"),
        ("enter", "jump to action filter"),
        ("type", "filter actions"),
        ("enter on action", "assign to selected key"),
        ("u", "undo last assignment"),
        ("ctrl+s", "review + push to keyboard"),
        ("?", "this overlay"),
        ("esc", "close overlay / back"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="help-box"):
            yield Label("Keybindings", classes="panel-title")
            for keys, what in self.BINDINGS:
                yield Label(f"{keys}  —  {what}")
            yield Button("Close", id="btn-help-close")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-help-close":
            self.dismiss()


class ConfirmPush(ModalScreen[bool]):
    """Explicit confirm gate: no hardware write without saying yes here."""

    def __init__(self, lines: list[str]) -> None:
        super().__init__()
        self.lines = lines

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-box"):
            yield Label("Push to keyboard?", classes="panel-title")
            yield Label(f"{len(self.lines)} changed key(s). Firmware is write-only: "
                        "this overwrites the board map.")
            for line in self.lines[:20]:
                yield Label(line)
            if len(self.lines) > 20:
                yield Label(f"… and {len(self.lines) - 20} more")
            with Horizontal():
                yield Button("Write to keyboard", id="btn-confirm-yes", variant="error")
                yield Button("Cancel", id="btn-confirm-no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "btn-confirm-yes")


class RemapScreen(VerticalScroll):
    """Visual remap editor: cursor the board, filter actions, assign, push."""

    def compose(self) -> ComposeResult:
        yield Label("Remap — cursor a key, pick an action (? for help)", classes="panel-title")
        board = KeyboardTester(load_layout(0x0220), omarchy.keyboard_accent())
        board.click_mode = "select"
        yield board
        with Horizontal():
            yield Button("Fn", id="btn-fn")
            yield Button("F-Shift", id="btn-fshift")
        with Horizontal():
            yield Label("Selected ")
            yield Static("none", id="remap-sel")
        with Horizontal():
            yield Label("Filter ")
            yield Input(placeholder="/ type to filter actions", id="remap-filter")
        yield ListView(*[ListItem(Label(f"{a.label}  [{a.category}]"))
                         for a in remap.ACTIONS], id="remap-actions")
        yield Label("Pending changes", classes="panel-title")
        yield RichLog(id="remap-diff", highlight=True, max_lines=200)
        with Horizontal():
            yield Button("Undo (u)", id="btn-undo")
            yield Button("Push (ctrl+s)", id="btn-push-remap")
            yield Button("Back", id="btn-back")
        yield Static("", id="remap-status")


class TesterScreen(VerticalScroll):
    """Live keypress tester: press keys on the S70, see what the OS delivers."""

    def compose(self) -> ComposeResult:
        yield Label("Key tester — press keys on the keyboard", classes="panel-title")
        yield KeyCapture("… (press any key)", id="capture")
        yield KeyboardTester(load_layout(0x0220), omarchy.keyboard_accent())
        with Horizontal():
            yield Button("Fn", id="btn-fn")
            yield Button("F-Shift", id="btn-fshift")
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
            yield Button("Fn", id="btn-fn")
            yield Button("F-Shift", id="btn-fshift")
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
        "Macros M1-M5": "Factory: M1=Ctrl+A M2=Ctrl+C M3=Ctrl+V M4=Ctrl+X M5=Ctrl+S.",
        "Profiles": "For now: `omakeyfig save-profile <name>` / `write-map --profile`.",
    }

    # -- remap ---------------------------------------------------------------
    def _init_remap_base(self) -> None:
        from omakeyfig.cli import _default_mappings
        base, n = _default_mappings(0x0220)
        self.remap_base = base
        self.remap_n_keys = n
        self.remap_pending = {}
        self.remap_history = []

    def remap_effective(self, slot: int) -> int:
        return self.remap_pending.get(slot, self.remap_base.get(slot, 0))

    def remap_diff_lines(self) -> list[str]:
        lines = []
        for slot in sorted(self.remap_pending):
            old, new = self.remap_base.get(slot, 0), self.remap_pending[slot]
            lines.append(f"slot {slot}: {remap.label_for_fw(old)} -> {remap.label_for_fw(new)}")
        return lines

    def refresh_remap_ui(self) -> None:
        try:
            board = self.query_one("#kb", KeyboardTester)
            sel = self.query_one("#remap-sel", Static)
            diff = self.query_one("#remap-diff", RichLog)
        except Exception:
            return
        if board.selected is None:
            sel.update("none")
        else:
            cur = self.remap_effective(board.selected)
            sel.update(f"slot {board.selected}: {remap.label_for_fw(cur)}")
        diff.clear()
        for line in self.remap_diff_lines():
            diff.write(line)

    def remap_filter_actions(self, query: str) -> None:
        try:
            lv = self.query_one("#remap-actions", ListView)
        except Exception:
            return
        lv.clear()
        self._action_aids = [a.aid for a in remap.search(query)]
        for a in remap.search(query):
            lv.append(ListItem(Label(f"{a.label}  [{a.category}]")))

    def remap_assign(self, aid: int) -> None:
        try:
            board = self.query_one("#kb", KeyboardTester)
            status = self.query_one("#remap-status", Static)
        except Exception:
            return
        if board.selected is None:
            status.update("Cursor a board key first (click, arrows, or hjkl).")
            return
        slot = board.selected
        self.remap_history.append((slot, self.remap_pending.get(slot)))
        self.remap_pending[slot] = remap.fw_for(aid)
        if self.remap_pending[slot] == self.remap_base.get(slot, 0):
            del self.remap_pending[slot]
        self.refresh_remap_ui()
        status.update(f"slot {slot} -> {remap.BY_ID[aid].label} "
                      f"({len(self.remap_pending)} pending)")

    def remap_undo(self) -> None:
        if not self.remap_history:
            return
        slot, prev = self.remap_history.pop()
        if prev is None:
            self.remap_pending.pop(slot, None)
        else:
            self.remap_pending[slot] = prev
        if self.remap_pending.get(slot) == self.remap_base.get(slot, 0):
            self.remap_pending.pop(slot, None)
        self.refresh_remap_ui()

    def remap_push(self) -> None:
        if self._screen != "remap":
            return
        lines = self.remap_diff_lines()
        if not lines:
            try:
                self.query_one("#remap-status", Static).update("Nothing to push.")
            except Exception:
                pass
            return

        def _after(ok: bool | None) -> None:
            if not ok:
                return
            full = dict(self.remap_base)
            full.update(self.remap_pending)
            try:
                buffers = codec.encode_keymap(full, self.remap_n_keys)
                dev = hid_layer.RKDevice()
                try:
                    dev.write_feature_buffers(buffers)
                finally:
                    dev.close()
            except Exception as e:
                try:
                    self.query_one("#remap-status", Static).update(f"Push failed: {e}")
                except Exception:
                    pass
                return
            self.remap_base = full
            self.remap_pending = {}
            self.remap_history = []
            self.refresh_remap_ui()
            try:
                self.query_one("#remap-status", Static).update(
                    f"Pushed {len(lines)} change(s) to the keyboard.")
            except Exception:
                pass

        self.push_screen(ConfirmPush(lines), _after)

    def __init__(self) -> None:
        super().__init__()
        self._status = "Connect the S70 via USB, then pick a section."
        self._screen: str | None = None  # None | "tester" | "lighting" | "remap"
        self.light_b = 5
        self.light_s = 5
        self.light_z = 5
        self.remap_base: dict[int, int] = {}
        self.remap_n_keys = 102
        self.remap_pending: dict[int, int] = {}
        self.remap_history: list[tuple[int, int | None]] = []  # (slot, previous or None)
        self._action_aids: list[int] = [a.aid for a in remap.ACTIONS]

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

    BINDINGS = [("ctrl+s", "push remap", "remap_push_binding")]

    def action_remap_push_binding(self) -> None:
        self.remap_push()

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
        self._action_aids = [a.aid for a in remap.ACTIONS]
        main = self.query_one("#main", Vertical)
        main.remove_children()
        if name == "lighting":
            main.mount(LightingScreen())
        elif name == "remap":
            self._init_remap_base()
            main.mount(RemapScreen())
        else:
            main.mount(TesterScreen())
            self.set_timer(0.05, lambda: self.query_one("#capture", KeyCapture).focus())

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if self._screen == "remap" and event.control.id == "remap-actions":
            idx = event.control.index
            aids = getattr(self, "_action_aids", [a.aid for a in remap.ACTIONS])
            if idx is not None and 0 <= idx < len(aids):
                self.remap_assign(aids[idx])
            return
        idx = event.control.index
        label = self.SECTIONS[idx] if idx is not None and 0 <= idx < len(self.SECTIONS) else ""
        if label == "Key tester":
            self.show_screen("tester")
        elif label == "Lighting":
            self.show_screen("lighting")
        elif label == "Remap":
            self.show_screen("remap")
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
            return
        if self._screen == "remap":
            await self.remap_key(event)

    async def remap_key(self, event) -> None:
        focused = self.focused
        in_filter = getattr(focused, "id", None) == "remap-filter"
        key = event.key
        if key in ("?", "question_mark") or getattr(event, "character", None) == "?":
            self.push_screen(HelpOverlay())
            return
        if in_filter:
            if key == "escape":
                self.query_one("#kb", KeyboardTester).focus() if False else None
            return
        try:
            board = self.query_one("#kb", KeyboardTester)
        except Exception:
            return
        moves = {"left": (-1, 0), "h": (-1, 0), "right": (1, 0), "l": (1, 0),
                 "up": (0, -1), "k": (0, -1), "down": (0, 1), "j": (0, 1)}
        if key in moves:
            dx, dy = moves[key]
            board.move_cursor(dx, dy)
            self.refresh_remap_ui()
            event.prevent_default()
        elif key == "enter":
            try:
                self.query_one("#remap-filter", Input).focus()
            except Exception:
                pass
            event.prevent_default()
        elif key == "u":
            self.remap_undo()

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
        if self._screen == "remap" and event.input.id == "remap-filter":
            self.remap_filter_actions(event.value)
            return
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
        if bid == "btn-undo":
            self.remap_undo()
            return
        if bid == "btn-push-remap":
            self.remap_push()
            return
        if bid == "btn-push":
            self.push_lighting()
            return
        if bid == "btn-fn":
            try:
                board = self.query_one("#kb", KeyboardTester)
            except Exception:
                return
            board.set_fn_view(not board.fn_view)
            event.button.variant = "success" if board.fn_view else "default"
            return
        if bid == "btn-fshift":
            try:
                board = self.query_one("#kb", KeyboardTester)
            except Exception:
                return
            board.set_fshift_view(not board.fshift_view)
            event.button.variant = "success" if board.fshift_view else "default"
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
