"""Generate PWA icons (stdlib only): dark tile with three rising green bars."""
import struct
import zlib
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "docs" / "icons"
BG, FG = (15, 23, 32), (62, 207, 142)


def png(size):
    rows = []
    bars = [(0.22, 0.38, 0.46), (0.42, 0.58, 0.62), (0.62, 0.78, 0.78)]  # x0, x1, top (fractions)
    for y in range(size):
        row = bytearray([0])
        for x in range(size):
            fx, fy = x / size, y / size
            on = any(x0 <= fx < x1 and top <= fy < 0.80 for x0, x1, top in bars)
            row += bytes(FG if on else BG)
        rows.append(bytes(row))
    raw = zlib.compress(b"".join(rows), 9)

    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", raw) + chunk(b"IEND", b""))


OUT.mkdir(parents=True, exist_ok=True)
for s in (180, 192, 512):
    (OUT / f"icon-{s}.png").write_bytes(png(s))
print("icons written")
