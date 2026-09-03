"""USB HID transport for Royal Kludge boards (Linux/hidapi).

- Targets the config interface (second HID interface on the S70).
- Uses HID feature reports (report ID 0x0a) for all writes.
- Serializes writes through a lock; no concurrent access to the device.
- udev rule (udev/60-rk.rules) grants user access so sudo is not needed.
"""

from __future__ import annotations

import fcntl
import os
import re
import threading
from pathlib import Path

from omakeyfig import VID_ROYAL_KLUDGE
from omakeyfig.codec import REPORT_ID

USAGE_PAGE = 0x0001
USAGE = 0x0080

SYS_HIDRAW = Path("/sys/class/hidraw")


def _ioc(dir_: int, type_: int, nr: int, size: int) -> int:
    return (dir_ << 30) | (size << 16) | (type_ << 8) | nr


def _hid_iocsfeature(length: int) -> int:
    return _ioc(3, ord("H"), 0x06, length)  # HIDIOCSFEATURE(len)


_IFACE_RE = re.compile(r":1\.(\d+)$")


def find_config_node(vendor_id: int = VID_ROYAL_KLUDGE,
                     product_id: int | None = None) -> tuple[str, int]:
    """Find the /dev/hidraw node for the RK *config* interface.

    Returns (devnode, interface_number). Prefers USB interface :1.1
    (the non-boot HID interface on the S70); falls back to any match.
    """
    want_pid = f"{product_id:04X}" if product_id is not None else None
    fallback: tuple[str, int] | None = None
    for node in sorted(SYS_HIDRAW.glob("hidraw*")):
        try:
            uevent = (node / "device" / "uevent").read_text()
        except OSError:
            continue
        m = re.search(r"HID_ID=(\S+)", uevent)
        if not m:
            continue
        parts = m.group(1).split(":")
        if len(parts) < 3:
            continue
        vid, pid = parts[-2][-4:].upper(), parts[-1][-4:].upper()
        if vid != f"{vendor_id:04X}":
            continue
        if want_pid is not None and pid != want_pid:
            continue
        try:
            resolved = os.path.realpath(node / "device")
            parent = os.path.basename(os.path.dirname(resolved))
        except OSError:
            parent = ""
        im = re.search(r":1\.(\d+)$", parent)
        iface = int(im.group(1)) if im else -1
        devnode = f"/dev/{node.name}"
        if iface == 1:
            return devnode, iface
        if fallback is None:
            fallback = (devnode, iface)
    if fallback is None:
        raise KeyboardNotFoundError(
            f"No hidraw node vid={vendor_id:#06x} pid={product_id} found. "
            "Connect the keyboard via USB cable (wireless modes cannot be configured)."
        )
    return fallback


class KeyboardNotFoundError(RuntimeError):
    pass


def _import_hid():
    try:
        import hid  # type: ignore[import-not-found]
    except ImportError as e:
        raise RuntimeError(
            "Python 'hid' package (hidapi) is not installed. "
            "Create a venv and `pip install -e '.[dev]'` (or at least `pip install hidapi`)."
        ) from e
    return hid


def list_rk_devices() -> list[dict]:
    """Enumerate connected Royal Kludge devices."""
    hid = _import_hid()
    found = []
    for d in hid.enumerate(VID_ROYAL_KLUDGE, 0):
        found.append({
            "vendor_id": d["vendor_id"],
            "product_id": d["product_id"],
            "serial": d.get("serial_number") or "",
            "product": d.get("product_string") or "",
            "manufacturer": d.get("manufacturer_string") or "",
            "path": d["path"],
            "usage_page": d.get("usage_page"),
            "usage": d.get("usage"),
        })
    return found


class RawHidrawDevice:
    """Opened RK keyboard via raw hidraw + HIDIOCSFEATURE ioctl.

    Used instead of hidapi's open (which fails on this board despite
    correct permissions); the on-wire mechanism is identical to hidapi's
    send_feature_report.
    """

    def __init__(self, vendor_id: int = VID_ROYAL_KLUDGE, product_id: int | None = None):
        self.devnode, self.iface = find_config_node(vendor_id, product_id)
        self.info = {"path": self.devnode.encode(), "interface": self.iface,
                     "vendor_id": vendor_id, "product_id": product_id}
        self._lock = threading.Lock()
        self._fd = os.open(self.devnode, os.O_RDWR)

    def write_feature_buffers(self, buffers: list[bytes], dry_run: bool = False) -> list[bytes]:
        for i, b in enumerate(buffers):
            if len(b) != 65 or b[0] != REPORT_ID:
                raise ValueError(f"buffer {i}: must be 65 bytes starting with 0x0a")
        if dry_run:
            return buffers
        with self._lock:
            for b in buffers:
                req = _hid_iocsfeature(len(b))
                fcntl.ioctl(self._fd, req, bytearray(b))
        return buffers

    def close(self) -> None:
        try:
            os.close(self._fd)
        except Exception:
            pass


# RKDevice is the raw-hidraw backend (hidapi open is broken for this board).
RKDevice = RawHidrawDevice
