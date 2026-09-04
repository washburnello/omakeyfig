"""Headless CLI: `omakeyfig` doubles as the backend for hooks and the bar widget."""

from __future__ import annotations

import argparse
import json
import sys

from omakeyfig import PID_S70, VID_ROYAL_KLUDGE
from omakeyfig import codec, hid_layer, lighting, omarchy, profiles
from omakeyfig.keycodes import vk_to_firmware_code
from omakeyfig.layouts import load_layout


def cmd_status(args) -> int:
    try:
        devs = hid_layer.list_rk_devices()
    except RuntimeError as e:
        print(f"omakeyfig: {e}", file=sys.stderr)
        return 2
    if not devs:
        print("No Royal Kludge devices found (connect via USB cable).")
        return 1
    for d in devs:
        print(f"vid={d['vendor_id']:#06x} pid={d['product_id']:#06x} "
              f"product={d['product']!r} serial={d['serial']!r}")
    return 0


def _default_mappings(pid: int) -> tuple[dict[int, int], int]:
    """Defaults keyed by firmware SLOT (the 8th KB.ini field), NOT position.

    Slots are sparse (S70 uses 1..101); unused slots encode as 0, exactly
    like KludgeKnight's full-buffer fill. Applies the user's verified
    customs from Profile1.rkf on top of factory (see rkf.py + field-guide):
    Esc->`, PgUp->Home, PgDn->End, M1->Esc.
    """
    keys = load_layout(pid)
    n_keys = max(k.slot for k in keys) + 1
    out: dict[int, int] = {}
    for k in keys:
        try:
            out[k.slot] = vk_to_firmware_code(k.vk)
        except KeyError:
            out[k.slot] = 0
    if pid in (0x0220, 0x0229, 0x01D9, 0x00D7):
        customs = {7: 0xC0, 99: 0x24, 100: 0x23, 1: 0x1B}  # rkf-verified
        for slot, vk in customs.items():
            try:
                out[slot] = vk_to_firmware_code(vk)
            except KeyError:
                pass
    return out, n_keys


def cmd_write_map(args) -> int:
    pid = int(args.pid, 0)
    mappings, n_keys = _default_mappings(pid)
    if args.profile:
        prof = profiles.load_profile(args.profile)
        n_keys = max(n_keys, *(int(k) + 1 for k in prof.get("mappings", {})))
        for k, v in prof.get("mappings", {}).items():
            mappings[int(k)] = int(v)
    buffers = codec.encode_keymap(mappings, n_keys)
    if args.dry_run:
        print(f"dry-run: {len(buffers)} buffers x {len(buffers[0])} bytes, "
              f"{len(mappings)} keys; first bytes: {buffers[0][:8].hex()}")
        return 0
    if not args.yes and not args.profile:
        print("Refusing to write defaults without --yes or --profile (firmware is write-only).")
        return 2
    dev = hid_layer.RKDevice(VID_ROYAL_KLUDGE, pid)
    try:
        dev.write_feature_buffers(buffers)
    finally:
        dev.close()
    print(f"Wrote {len(mappings)}-key map to pid={pid:#06x}.")
    return 0


def cmd_apply_theme(args) -> int:
    color = omarchy.keyboard_accent()
    state = lighting.LightingState(color=color)
    desc = lighting.describe(state)
    buf = lighting.build_lighting_report(state)
    if args.dry_run:
        print(f"dry-run: would apply theme lighting: {desc}")
        print(f"  bytes: {buf[:14].hex()}...(65B)")
        return 0
    dev = hid_layer.RKDevice(VID_ROYAL_KLUDGE, PID_S70)
    try:
        dev.write_feature_buffers([buf])
    finally:
        dev.close()
    print(f"Theme lighting applied: {desc}")
    return 0


def cmd_light(args) -> int:
    state = lighting.LightingState(effect=args.effect, brightness=args.brightness,
                                   speed=args.speed, color=args.color,
                                   random=args.random, sleep=args.sleep)
    buf = lighting.build_lighting_report(state)
    if args.dry_run:
        print(f"dry-run: {lighting.describe(state)}")
        print(f"  bytes: {buf[:14].hex()}...(65B)")
        return 0
    dev = hid_layer.RKDevice(VID_ROYAL_KLUDGE, PID_S70)
    try:
        dev.write_feature_buffers([buf])
    finally:
        dev.close()
    print(f"Lighting applied: {lighting.describe(state)}")
    return 0


def cmd_list_profiles(args) -> int:
    for name in profiles.list_profiles():
        print(name)
    return 0


def cmd_save_profile(args) -> int:
    pid = int(args.pid, 0)
    mappings, _ = _default_mappings(pid)
    payload = {"pid": pid, "mappings": {str(k): v for k, v in mappings.items()},
               "lighting": lighting.LightingState().__dict__}
    p = profiles.save_profile(args.name, payload)
    print(f"Saved {p}")
    return 0


def cmd_tui(args) -> int:
    from omakeyfig.app import run
    return run()


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="omakeyfig",
                                 description="Unofficial RK keyboard customizer (S70-first).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("status", help="List connected RK devices")
    s.set_defaults(fn=cmd_status)
    w = sub.add_parser("write-map", help="Write a keymap to the keyboard")
    w.add_argument("--pid", default=hex(PID_S70))
    w.add_argument("--profile", default=None)
    w.add_argument("--dry-run", action="store_true")
    w.add_argument("--yes", action="store_true")
    w.set_defaults(fn=cmd_write_map)
    t = sub.add_parser("apply-theme", help="Apply Omarchy theme accent as lighting")
    t.add_argument("--dry-run", action="store_true")
    t.add_argument("--from-omarchy", action="store_true")
    t.set_defaults(fn=cmd_apply_theme)
    li = sub.add_parser("light", help="Set keyboard-wide lighting")
    li.add_argument("--effect", default="Steady", choices=lighting.EFFECTS)
    li.add_argument("--brightness", type=int, default=5)
    li.add_argument("--speed", type=int, default=5)
    li.add_argument("--color", default="#faa968")
    li.add_argument("--random", action="store_true")
    li.add_argument("--sleep", type=int, default=5)
    li.add_argument("--dry-run", action="store_true")
    li.set_defaults(fn=cmd_light)
    sv = sub.add_parser("save-profile", help="Snapshot default layout to a profile")
    sv.add_argument("name")
    sv.add_argument("--pid", default=hex(PID_S70))
    sv.set_defaults(fn=cmd_save_profile)
    lp = sub.add_parser("list-profiles", help="List saved profiles")
    lp.set_defaults(fn=cmd_list_profiles)
    lp = sub.add_parser("tui", help="Open the Textual TUI")
    lp.set_defaults(fn=cmd_tui)
    return ap


def main(argv=None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
