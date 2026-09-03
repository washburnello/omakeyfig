"""HID feature-report codec for Royal Kludge boards.

Documented behavior (from KludgeKnight docs + Rangoli's
keyboardconfiguratorcontroller):
- Every keymap write sends 9 feature-report buffers, 65 bytes each.
- Byte 0 of each buffer is the report ID (0x0a).
- Buffer 0 carries header bytes 0x01, 0xf8 at buffer positions 3-4.
- Key space is striped across the remaining payload bytes: each key
  occupies 4 bytes, little-endian. Key index i lives at space offset i*4.
- The firmware is write-only: mappings cannot be read back. Every change
  writes the FULL keymap, even for a single key.

Layout of the 572-byte key space:
- buffer 0: payload bytes [5:65]  -> space [0:60]   (60 bytes, 15 keys)
- buffers 1..8: payload bytes [1:65] -> space [60+b*64 ..] (64 bytes each)

This is an independent Python implementation of that documented behavior,
written for omakeyfig (GPL-3.0-or-later) with attribution to Rangoli and
KludgeKnight. It is not a copy of their source.
"""

REPORT_ID = 0x0A
N_BUFFERS = 9
BUFFER_LEN = 65  # includes the report-ID byte
KEY_BYTES = 4

HEADER_AT = (3, 4)
HEADER_VALS = (0x01, 0xF8)
FIRST_BUF_DATA_START = 5  # key space starts at buffer byte 5 in buffer 0

# Usable key-space bytes: 60 in buffer 0 + 8 * 64.
SPACE_LEN = (BUFFER_LEN - FIRST_BUF_DATA_START) + (N_BUFFERS - 1) * (BUFFER_LEN - 1)
MAX_KEYS = SPACE_LEN // KEY_BYTES  # 143


def encode_keymap(mappings: dict[int, int], n_keys: int) -> list[bytes]:
    """Encode {key_index: firmware_code} into 9 x 65-byte feature reports.

    Missing indices encode as firmware code 0. Raises ValueError if n_keys
    exceeds capacity.
    """
    if n_keys > MAX_KEYS:
        raise ValueError(f"n_keys={n_keys} exceeds capacity {MAX_KEYS}")
    space = bytearray(SPACE_LEN)
    for idx, code in mappings.items():
        if not 0 <= idx < n_keys:
            raise ValueError(f"key index {idx} out of range for n_keys={n_keys}")
        if not 0 <= code <= 0xFFFFFFFF:
            raise ValueError(f"firmware code {code:#x} out of 32-bit range")
        off = idx * KEY_BYTES
        space[off : off + KEY_BYTES] = code.to_bytes(4, "little")

    buffers: list[bytes] = []
    cursor = 0
    for b in range(N_BUFFERS):
        buf = bytearray(BUFFER_LEN)
        buf[0] = REPORT_ID
        if b == 0:
            buf[HEADER_AT[0]] = HEADER_VALS[0]
            buf[HEADER_AT[1]] = HEADER_VALS[1]
            chunk_len = BUFFER_LEN - FIRST_BUF_DATA_START
            buf[FIRST_BUF_DATA_START:] = space[cursor : cursor + chunk_len]
            cursor += chunk_len
        else:
            chunk_len = BUFFER_LEN - 1
            buf[1:] = space[cursor : cursor + chunk_len]
            cursor += chunk_len
        buffers.append(bytes(buf))
    return buffers


def decode_keymap(buffers: list[bytes], n_keys: int) -> dict[int, int]:
    """Inverse of encode_keymap. Used for tests and dry-run inspection."""
    if len(buffers) != N_BUFFERS:
        raise ValueError(f"expected {N_BUFFERS} buffers, got {len(buffers)}")
    space = bytearray()
    for b, buf in enumerate(buffers):
        if len(buf) != BUFFER_LEN:
            raise ValueError(f"buffer {b}: expected {BUFFER_LEN} bytes, got {len(buf)}")
        if buf[0] != REPORT_ID:
            raise ValueError(f"buffer {b}: bad report ID {buf[0]:#x}")
        if b == 0:
            if (buf[HEADER_AT[0]], buf[HEADER_AT[1]]) != HEADER_VALS:
                raise ValueError("buffer 0: missing header bytes 0x01 0xf8")
            space += buf[FIRST_BUF_DATA_START:]
        else:
            space += buf[1:]
    out: dict[int, int] = {}
    for idx in range(n_keys):
        off = idx * KEY_BYTES
        out[idx] = int.from_bytes(space[off : off + KEY_BYTES], "little")
    return out
