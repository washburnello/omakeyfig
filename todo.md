# omakeyfig todo — parked items needing a human or deeper RE

## Needs washburnello's input (nothing blocked on these)

1. **K2 (` key, slot 97) intent.** Left at factory `` ` ``. Candidate: Esc
   (would mirror the M1/Esc swap philosophy). The .rkf shows you HAD a
   custom macro there (`02 00 00 ff 84 95 dd`), but the encoding is
   undecoded — see #4. One-word answer ("esc" / "leave it") resolves this.
2. **M2–M5 future roles.** Currently factory Ctrl+C/V/X/S (your old dev
   macros went unused). Use the Macros screen to assign new combos whenever
   ready — no further work needed.
3. **Fn-layer `?` legends.** Open the tester, hold physical Fn, press each
   unknown key, and report what arrives; each is a one-line addition to
   `FN_LAYER` in `keyboard_widget.py`.

## Needs deeper reverse engineering (all optional, app is complete without)

4. **Macro blob decode.** M2/M3/M5 combo records (`ff ec 27 e1`-style) and
   the M4/K2 16-byte blobs in Profile1.rkf are preserved raw in
   `rkf.unresolved()` but not decoded. Requires the official Windows app +
   USB capture while programming a macro. Payoff: import anyone's .rkf
   macros exactly instead of rebuilding them in the Macros UI.
5. **Per-key RGB custom mode.** Rangoli documents 7 extra buffers
   (`0x0a [7] [seq] [0x03 0x7e 0x01]...`, 3 bytes/key RGB by bufferIndex).
   Needs a USB capture to confirm on the S70 before implementing — the
   standard lighting path is fully working, so this is pure enhancement.
6. **F-shift toggle command.** No HID command is known for flipping the
   Fn+LeftCtrl mode from software. Would need USB capture of the official
   app (if it even exposes the toggle). The board chord works fine.

## Packaging / distribution (not started)

7. **PyPI publish** (`pip install omakeyfig`): name looks free; needs
   `python -m build` + `twine upload` + a PyPI account decision.
8. **AUR package** (`yay -S omakeyfig`): write PKGBUILD installing the
   package + udev rule + desktop file. Straightforward on Arch.
9. **screenshots/demo** for the README (tester, remap, lighting screens).

## Done (record)

- Keymap write/read-back protocol, lighting, Fn + F-shift visualization,
  remap UI, macros UI, profiles UI, .rkf importer, theme hook, bar widget.
- Stale profiles `pre-hw-backup` / `test-default` (positional-slot bug)
  renamed to `*.STALE-buggy.json` so they can never be applied.
