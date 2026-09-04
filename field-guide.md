# omakeyfig field guide

Critical, hard-won knowledge for anyone (human or agent) working on this
project. Read this before touching the protocol code or writing to hardware.

## The one rule

**RK firmware is write-only.** It accepts keymap/lighting writes but cannot
be read back. Consequences:

- NEVER write a map you cannot reconstruct. Every write must come from a
  profile file with a known-good slot -> firmware-code mapping.
- `~/.config/omakeyfig/profiles/` is the source of truth, not the keyboard.
- `factory-defaults` = official KB.ini defaults through our translation.
  `washburnello-restore` = factory + the 4 simple customs from Profile1.rkf.
- Profiles `pre-hw-backup` / `test-default` contain the **positional-slot
  bug** (see below). Do not apply them; delete when convenient.
- Hardware writes are currently FROZEN pending the 5 macro slots
  (K2, M2-M5). See "Unresolved macros".

## USB transport (verified on S70, PID 0x0220)

- VID `0x258a` (SINO WEALTH). User board: `258a:0220`, regional variants
  `0229` (FR) / `01D9` (DE) share the layout.
- **USB wired only.** Wireless modes cannot be configured (firmware limit).
- Config interface = USB interface `:1.1` = `/dev/hidraw5` on the user's
  machine (interface `:1.0` is the boot keyboard). Resolve via sysfs:
  parent dir of `/sys/class/hidraw/hidrawN/device` ends in `:1.1`.
- Writes are HID **feature reports** via `HIDIOCSFEATURE` ioctl on the
  hidraw node (65 bytes, first byte = report ID `0x0a`).
- **hidapi's `open()` is broken for this board** (fails despite correct
  permissions; raw `os.open` works). `hid_layer.py` uses raw hidraw +
  `fcntl.ioctl` and only uses the `hid` package for enumeration.
  Same on-wire mechanism as hidapi's `send_feature_report`.
- udev rule `udev/60-rk.rules` (`TAG+=uaccess`) is installed at
  `/etc/udev/rules.d/`; without it hidraw nodes are root-only.

## Keymap protocol (from Rangoli, via KludgeKnight's S70-tested port)

- Every keymap write = **9 buffers x 65 bytes**, sent sequentially.
- Per-buffer framing: `[0]=0x0a report ID, [1]=9 count, [2]=1-based seq`.
  Buffer 0 additionally has `[3]=0x01, [4]=0xf8`.
- Key space = flat 585 bytes: buffer 0 carries bytes `[0:60]`, buffers 1-8
  carry 62 bytes each starting at payload byte 3.
- Key **slot** `i` lives at space offset `i*4`, encoded by Rangoli/
  KludgeKnight `setBufferKey`: **big-endian placement**, MSB first, leading
  zero bytes preserved (NOT little-endian despite a stale comment upstream).
- Firmware code encodings (KludgeKnight KEY_MAP, cross-checked):
  regular key = USB HID usage `<< 8` (A = `0x0400`); left mods
  Ctrl/Shift/Alt/Win = `0x010000/020000/040000/080000`; right mods =
  `0x100000/.../0x800000`; Fn = `0xb000`; media = `0x01000000 | consumer`
  (VolUp `0x010000e9`, calculator `0x01000192`); S70 macros are Ctrl combos
  (M1=Ctrl+A `0x010400`, M2=Ctrl+C `0x010600`, M3=Ctrl+V `0x011900`,
  M4=Ctrl+X `0x011b00`, M5=Ctrl+S `0x011600`).
- **Slots are sparse, 1..101.** Always key mappings by the KB.ini slot
  (8th field), never by list position. `n_keys = max(slot)+1` (102 for S70,
  fits the 146-slot capacity). Unused slots encode as 0, like KludgeKnight.
- **W and Z HID codes**: W = HID `0x1A`, Z = HID `0x1D`. We shipped them
  swapped once; `test_alphabet_matches_kludgeknight` pins all 26 letters.

## Lighting protocol (Rangoli, verified: board glows on command)

- Standard lighting buffer, 65 bytes:
  `[0]=0x0a [1]=0x01 [2]=0x01 [3]=0x02 [4]=0x29 [5]=modebit [6]=0x00
  [7]=animation [8]=brightness [9..11]=RGB [12]=randomflag [13]=sleep`.
- Brightness/animation/sleep scale 0..10. Mode bits = Rangoli
  `ModeModel::RGBModes` (Steady=17, Breathing=18, Rainbow=5, NeonStream=1,
  Custom=14, ... full table in `lighting.py`).
- Custom per-key mode = 7 extra buffers (not yet implemented; needs capture).

## Official .rkf profiles (decoded from the user's Profile1.rkf)

- Header: u32 LE PID at 0x00, 8 unknown bytes, UTF-16LE name at 0x0C-0x30,
  one 16-byte header record at 0x30.
- 74 key records, 16 bytes each, at 0x40..0x4E0 in K1..K74 order.
- Record shapes (see `rkf.py`):
  - normal: `[slot][x][y][0x00][0x00][VK][00x9][flag]` — byte 5 is the
    effective VK. `x/y` echo the slot for untouched keys, `0x00` for
    user-touched keys. The flag byte varies (`0x02`, `0x05`, `0x08`) and is
    NOT a type marker.
  - modifier: `[slot x3][fw BE 4B][genericVK][00x8][0x02]`.
  - combo macro: `[slot][00][00][0xFF][a][b][c][00x8][0x02]` — a/b/c
    UNDECODED. M4's macro is a 16-byte blob ending `0x05`, also undecodable.
- Lighting config + custom palette live at ~0x5D60 (RGB triplets).
- Importer: `omakeyfig/rkf.py` (`parse_rkf`, `to_omakeyfig_profile`).
- User customs recovered: Esc->`` ` ``, PgUp->Home, PgDn->End, M1->Esc.
  (Also touched-but-identical: Delete.)

## Unresolved macros (need the user OR deeper RE)

Slots K2 (slot 97), M2 (2), M3 (3), M4 (4), M5 (5). Raw bytes in
`washburnello-restore` profile's `unresolved_macros` equivalent — see
`rkf.py` output. Board currently has FACTORY codes in these slots.

## Fn layer (fixed firmware table — NOT writable)
- The Fn layer is a second, firmware-fixed table keyed by physical key/slot,
  independent of the base map. Proof: after remapping base PgUp->Home,
  Fn+PgUp still emits Pause. The official app cannot customize it either:
  Profile1.rkf stores exactly 74 base-layer records and no Fn section.
- Consequence: omakeyfig can VISUALIZE the Fn layer but not rewrite it.
  `keyboard_widget.FN_LAYER` holds slot -> legend; unknown slots render "?".
  Sources: user-verified (PgUp->Pause, PgDn->End), S70 manual (Fn+A Win
  mode, Fn+S Mac mode), S70 review (Fn+| color, Fn+arrows brightness/speed),
  RK-standard number row (Fn+1..= -> F1-F12).
- UI: "Fn" toggle button in tester + lighting screens swaps labels
  (sub-rows were rejected: they double the 15-line board to 30).
- Unknown legends are completed empirically: open the tester, hold physical
  Fn, press keys, read what the OS receives. User-confirmed so far (Sep 2026,
  from the user's own layout diagram): Fn+`=PtSc NOT confirmed (user will
  wire PrtSc via base remap if wanted); Fn+[=Home, Fn+]=ScrollLock,
  Fn+\=lighting Style, Fn+N=hue cycle. FN-LCK is the user's name for the
  Fn+LeftCtrl F-shift chord itself, not a separate combo.

## Keycap layer (display only — omakeyfig/keycaps.py)

- The user swaps physical keycaps. `~/.config/omakeyfig/keycaps.toml`
  maps slot -> label shown on the board. Firmware matching, remap logic,
  and profiles NEVER use keycap labels — only slots.
- KeyWidget shows `keycap_label`; `base_label` (firmware function) stays
  available for status lines. CLI: `omakeyfig keycap <slot> <label>` and
  `omakeyfig keycap <slot> --clear`. A full keycap-editor UI is parked
  until the user pastes their ORIGINAL (pre-swap) layout.
- Workaround for "Fn+PgUp should be PgUp": OS-level remap of the Pause key
  (e.g. keyd/Hyprland maps Pause -> PgUp). Mention, don't implement here.

### F-shift mode (another fixed firmware mode — also NOT writable)
- Chord **Fn+LeftCtrl** (bottom row, 2nd from left) swaps the number row to
  F1..F12 as the *default* layer; the manual's "1F indicator" stays
  constantly on while active. Press the chord again to swap back.
- While F-shifted, **Fn+F-key emits media functions** (RK-standard table:
  F1=MyPC F2=Browser F3=Mail F4=Calc F5=Player F6=Stop F7=Prev F8=Play
  F9=Next F10=Mute F11=Vol- F12=Vol+). S70 manual lists exactly these 12
  functions; per-key mapping assumed from the RK61 table — confirm any
  doubtful key with the tester before relying on it.
- No HID command for toggling it is known (Rangoli/KludgeKnight have no
  such command; the .rkf has no such field). User toggles it on the board.
- UI: "F-Shift" toggle in tester/lighting/remap screens
  (`FSHIFT_KEYS`/`FSHIFT_FN_MEDIA` in keyboard_widget.py). F-Shift alone
  shows F1..F12 on the number row; F-Shift+Fn shows the media legends.
  Remapping F-keys in the remap UI does NOT change what F-shift emits
  (same fixed-table reason as the Fn layer).

## Past bugs (do not reintroduce)

1. Positional slots: mapping list position 0..73 instead of KB.ini slots
   scrambled the board. Fixed: `cli._default_mappings` uses `k.slot`.
2. Swapped W/Z HID codes. Fixed + alphabet regression test.
3. Codec framing: must include `[1]=count [2]=seq` + big-endian slots.
   First version missed framing and used little-endian.
4. hidapi open fails on this board -> raw hidraw backend.
5. `hid.enumerate` paths (`5-3.2:1.1`) are NOT device nodes; map interfaces
   via sysfs parent dir, not string matching on enumerate paths.
6. Textual Pilot tests: Button swallows re-presses inside its active-effect
   window (~0.2s). Use `await pilot.pause(0.4)` around button activations.

## Remap UI (omakeyfig/remap.py + RemapScreen in app.py)
- Catalog: 103 actions mirroring KludgeKnight KEY_MAP + macro combos;
  covers 100% of firmware codes on the factory board (assert in tests).
- Board cursor: click or arrows/hjkl (`move_cursor` snaps to nearest
  x-center across rows); selection paints with the theme `selection` color.
- Filter: Input.Changed rebuilds the action ListView; items carry NO ids
  (duplicate-id registration errors) — selection resolves via index into
  `_action_aids`. Reset `_action_aids` on every `show_screen`.
- Push flow: diff lines -> ConfirmPush modal -> encode base+pending ->
  RKDevice write -> base=full, pending/history cleared. Every push needs the
  modal "Write to keyboard" click. Tests mock RKDevice (no hardware).
- Pilot quirks: `?` arrives as key `question_mark` (check character too);
  modal Button Enter is unreliable — click `#btn-confirm-yes` instead;
  button re-press needs `pause(0.4)` (see bug 6).

## Macros UI (MacroScreen in app.py)

- Covers M1-M5 (slots 1-5) + K2 (slot 97). Combo encoding =
  `modifier-bits | HID<<8`, which reproduces the official macro codes
  (Ctrl+A `0x010400` etc.). Media bases allowed only with no modifiers.
- Each Assign builds the FULL map (base + one slot) and pushes through
  ConfirmPush immediately. Base = `_default_mappings` (factory + customs).
- K2 judgement (Sep 2026): left at factory `` ` `` — user never said what
  it does; candidate Esc. See todo.md #1.

## Profiles (profiles.py + ProfileScreen)

- Payload: `{pid, mappings: {slot: fw}, note?/source?}`. Apply path uses
  `n = max(max(slot)+1, 102)`. After apply, remap base is REPLACED by the
  profile map so further remap edits compose on top.
- Remap base persists across screen visits within a session
  (`_init_remap_base` inits once); Profiles Save snapshots base+pending.
- `washburnello-restore` == `_default_mappings` output (verified zero-diff).

## Omarchy install record (user machine, Sep 2026)

- Hook installed: `~/.config/omarchy/hooks/theme-set.d/10-omakeyfig.sh`,
  `theme_follow` default false.
- Bar widget installed: `~/.config/omarchy/plugins/washburnello.omakeyfig/`,
  added first in the bar right section. Backup:
  `~/.config/omarchy/shell.json.bak.omakeyfig`. Shell lists it enabled,
  no QML errors.
- Menu entry: `~/.local/share/applications/omakeyfig.desktop`;
  PATH shim: `~/.local/bin/omakeyfig` (-> repo venv python).

## Omarchy integration

- Theme colors: `~/.local/state/omarchy/current/theme/colors.toml`;
  keyboard accent: `keyboard.rgb` (single hex line).
- `theme_follow` in `~/.config/omakeyfig/config.toml` gates the
  `theme-set.d` hook. Default off.
- Bar widget id `washburnello.omakeyfig` in `omarchy-plugin/`.
- TUI stack: Python + Textual (deliberate; see README/scope notes).
  Charm-stack (Bubble Tea/Lip Gloss) design language adopted for UX
  (`?` overlay, vim nav, `/` filter) without switching languages.
- License is GPL-3.0-or-later (derivative of Rangoli/KludgeKnight codec).

## Repo map

- `omakeyfig/codec.py` framing+slots; `hid_layer.py` raw hidraw transport;
  `keycodes.py` VK->fw; `layouts.py` KB.ini parsing;
  `lighting.py` Rangoli lighting port; `rkf.py` .rkf importer;
  `profiles.py` local JSON profiles; `omarchy.py` theme reading;
  `cli.py` headless commands; `app.py` + `keyboard_widget.py` TUI.
- `hooks/theme-set.d/`, `udev/`, `omarchy-plugin/`, `desktop/`, `tests/`.
