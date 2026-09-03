"""USB HID transport for Royal Kludge boards (Linux/hidapi).

- Targets the config interface (second HID interface on the S70).
- Uses HID feature reports (report ID 0x0a) for all writes.
- Serializes writes through a lock; no concurrent access to the device.
- udev rule (udev/60-rk.rules) grants user access so sudo is not needed.
"""

from __future__ import annotations

import threading

from omakeyfig import VID_ROYAL_KLUDGE
from omakeyfig.codec import REPORT_ID

USAGE_PAGE = 0x0001
USAGE = 0x0080


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


class RKDevice:
    """Opened RK keyboard with serialized feature-report writes."""

    def __init__(self, vendor_id: int = VID_ROYAL_KLUDGE, product_id: int | None = None):
        hid = _import_hid()
        self._lock = threading.Lock()
        cands = [d for d in hid.enumerate(vendor_id, product_id or 0)]
        # Prefer the config interface when several HID paths exist.
        cands.sort(key=lambda d: 0 if (d.get("usage_page"), d.get("usage")) == (USAGE_PAGE, USAGE) else 1)
        if not cands:
            raise KeyboardNotFoundError(
                f"No HID device vid={vendor_id:#06x} pid={product_id:#06x} found. "
                "Connect the keyboard via USB cable (wireless modes cannot be configured)."
            )
        chosen = cands[0]
        self.info = chosen
        self._dev = hid.device()
        self._dev.open_path(chosen["path"])

    def write_feature_buffers(self, buffers: list[bytes], dry_run: bool = False) -> list[bytes]:
        """Send all buffers as feature reports (report ID = first byte).

        With dry_run=True, validates shape and returns buffers untouched.
        """
        for i, b in enumerate(buffers):
            if len(b) != 65 or b[0] != REPORT_ID:
                raise ValueError(f"buffer {i}: must be 65 bytes starting with 0x0a")
        if dry_run:
            return buffers
        with self._lock:
            for b in buffers:
                # hidapi: send_feature_report takes data including report ID.
                self._dev.send_feature_report(bytes(b))
        return buffers

    def close(self) -> None:
        try:
            self._dev.close()
        except Exception:
            pass
