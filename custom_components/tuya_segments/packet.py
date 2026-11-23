"""Encoder for the Tuya RGBIC `draw_tool` datapoint. No Home Assistant imports, so it is unit-testable."""

from __future__ import annotations

import base64

MAX_PER_PACKET = 0x7F  # count shares a byte with the 0x80 flag


def encode(segments: list[int], hue: float, sat: float, val: int) -> list[str]:
    """Return base64 packets painting `segments` (0-based) one HSV colour.

    hue 0-360, sat 0-100, val 0-100 (0 = segment off, untested on hardware).
    """
    h = max(0, min(360, int(round(hue))))
    s = max(0, min(100, int(round(sat))))
    v = max(0, min(100, int(val)))
    segs = sorted(set(segments))
    packets = []
    for i in range(0, len(segs), MAX_PER_PACKET):
        chunk = segs[i : i + MAX_PER_PACKET]
        raw = (
            bytes([0x01, 0x02, 0x01])
            + h.to_bytes(2, "big")
            + bytes([s, v, 0x00, 0x00, 0x80 | len(chunk)])
            + b"".join(idx.to_bytes(2, "big") for idx in chunk)
        )
        packets.append(base64.b64encode(raw).decode())
    return packets
