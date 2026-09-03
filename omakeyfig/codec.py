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

# Per-buffer framing (Rangoli + KludgeKnight, verified on S70):
#   byte 0: report ID (0x0a)
#   byte 1: total buffer count (9)
#   byte 2: 1-based sequence number
#   bytes 3-4 (buffer 0 only): 0x01, 0xf8
# Key space is a flat 9*65 = 585-byte area striped across the payloads:
# buffer 0 takes bytes [0:60], buffers 1..8 take 62 bytes each starting at
# payload byte 3. Key slot i lives at space offset i*4.
SEQ_COUNT_BYTE = 1
SEQ_NUM_BYTE = 2
HEADER_AT = (3, 4)
HEADER_VALS = (0x01, 0xF8)
FIRST_BUF_DATA_START = 5
OTHER_BUF_DATA_START = 3

SPACE_LEN = N_BUFFERS * BUFFER_LEN  # 585
MAX_KEYS = SPACE_LEN // KEY_BYTES  # 146


def encode_keycode(code: int) -> bytes:
    """Encode one firmware code into its 4-byte slot (big-endian placement).

    Direct port of Rangoli/KludgeKnight setBufferKey: the most significant
    byte goes first; unused leading bytes are zero.
    """
    if not 0 <= code <= 0xFFFFFFFF:
        raise ValueError(f"firmware code {code:#x} out of 32-bit range")
    if code >= 0x01000000:
        return bytes(((code >> 24) & 0xFF, (code >> 16) & 0xFF,
                      (code >> 8) & 0xFF, code & 0xFF))
    if code >= 0x010000:
        return bytes((0x00, (code >> 16) & 0xFF, (code >> 8) & 0xFF, code & 0xFF))
    if code >= 0x0100:
        return bytes((0x00, 0x00, (code >> 8) & 0xFF, code & 0xFF))
    return bytes((0x00, 0x00, 0x00, code & 0xFF))


def encode_keymap(mappings: dict[int, int], n_keys: int) -> list[bytes]:
    """Encode {slot: firmware_code} into 9 x 65-byte feature reports.

    Faithful port of KludgeKnight BufferCodec.encode (itself ported from
    Rangoli): flat 585-byte space, per-buffer framing, big-endian key slots.
    Missing slots encode as firmware code 0.
    """
    if n_keys > MAX_KEYS:
        raise ValueError(f"n_keys={n_keys} exceeds capacity {MAX_KEYS}")
    space = bytearray(SPACE_LEN)
    for slot, code in mappings.items():
        if not 0 <= slot < n_keys:
            raise ValueError(f"key slot {slot} out of range for n_keys={n_keys}")
        off = slot * KEY_BYTES
        space[off : off + KEY_BYTES] = encode_keycode(code)

    buffers: list[bytes] = []
    cursor = 0
    for i in range(N_BUFFERS):
        buf = bytearray(BUFFER_LEN)
        buf[0] = REPORT_ID
        buf[SEQ_COUNT_BYTE] = N_BUFFERS
        buf[SEQ_NUM_BYTE] = i + 1
        if i == 0:
            buf[HEADER_AT[0]] = HEADER_VALS[0]
            buf[HEADER_AT[1]] = HEADER_VALS[1]
            start = FIRST_BUF_DATA_START
        else:
            start = OTHER_BUF_DATA_START
        end = BUFFER_LEN
        buf[start:end] = space[cursor : cursor + (end - start)]
        cursor += end - start
        buffers.append(bytes(buf))
    return buffers


def decode_keymap(buffers: list[bytes], n_keys: int) -> dict[int, int]:
    """Inverse of encode_keymap. Used for tests and dry-run inspection."""
    if len(buffers) != N_BUFFERS:
        raise ValueError(f"expected {N_BUFFERS} buffers, got {len(buffers)}")
    space = bytearray()
    for i, buf in enumerate(buffers):
        if len(buf) != BUFFER_LEN:
            raise ValueError(f"buffer {i}: expected {BUFFER_LEN} bytes, got {len(buf)}")
        if buf[0] != REPORT_ID:
            raise ValueError(f"buffer {i}: bad report ID {buf[0]:#x}")
        if buf[SEQ_COUNT_BYTE] != N_BUFFERS or buf[SEQ_NUM_BYTE] != i + 1:
            raise ValueError(f"buffer {i}: bad framing bytes")
        if i == 0:
            if (buf[HEADER_AT[0]], buf[HEADER_AT[1]]) != HEADER_VALS:
                raise ValueError("buffer 0: missing header bytes 0x01 0xf8")
            space += buf[FIRST_BUF_DATA_START:]
        else:
            space += buf[OTHER_BUF_DATA_START:]
    out: dict[int, int] = {}
    for slot in range(n_keys):
        off = slot * KEY_BYTES
        out[slot] = int.from_bytes(space[off : off + KEY_BYTES], "big")
    return out
