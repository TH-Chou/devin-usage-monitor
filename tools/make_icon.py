#!/usr/bin/env python3
"""Generate the Devin Token Monitor app icon (.icns).

Solid opaque black 1024x1024 PNG background with a white activity-pulse
mark — no transparency, no margins. Exports a full iconset + .icns.

Usage: .venv/bin/python tools/make_icon.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

OUT = Path(__file__).resolve().parent.parent / "assets"
SIZE = 1024
INNER = int(SIZE * 0.804)

TOP = (0, 0, 0)
BOT = (0, 0, 0)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def squircle_mask(size: int, radius_ratio: float = 0.225) -> Image.Image:
    m = Image.new("L", (size * 4, size * 4), 0)
    d = ImageDraw.Draw(m)
    r = int(size * 4 * radius_ratio)
    d.rounded_rectangle([0, 0, size * 4 - 1, size * 4 - 1], r, fill=255)
    return m.resize((size, size), Image.LANCZOS)


def pulse_points(size):
    return [(0.06 * size, 0.55 * size), (0.28 * size, 0.55 * size),
            (0.38 * size, 0.30 * size), (0.50 * size, 0.78 * size),
            (0.60 * size, 0.45 * size), (0.68 * size, 0.55 * size),
            (0.94 * size, 0.55 * size)]


def make_master() -> Image.Image:
    # fully opaque black canvas — no transparent margins
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 255))

    w = int(0.05 * SIZE)
    pts = pulse_points(SIZE)
    d = ImageDraw.Draw(img)
    d.line(pts, fill=(255, 255, 255, 255), width=w, joint="curve")
    for p in (pts[0], pts[-1]):  # round caps
        d.ellipse([p[0] - w / 2, p[1] - w / 2, p[0] + w / 2, p[1] + w / 2],
                  fill=(255, 255, 255, 255))
    px, py = pts[3]  # peak dot
    d.ellipse([px - w * 0.8, py - w * 0.8, px + w * 0.8, py + w * 0.8],
              fill=(255, 255, 255, 255))
    return img


def main() -> int:
    OUT.mkdir(exist_ok=True)
    master = make_master()
    master.save(OUT / "icon_1024.png")

    iconset = OUT / "AppIcon.iconset"
    iconset.mkdir(exist_ok=True)
    for size in (16, 32, 128, 256, 512):
        for scale in (1, 2):
            px = size * scale
            name = f"icon_{size}x{size}" + ("@2x" if scale == 2 else "") + ".png"
            master.resize((px, px), Image.LANCZOS).save(iconset / name)
    subprocess.run(
        ["iconutil", "-c", "icns", str(iconset), "-o", str(OUT / "dtm.icns")],
        check=True,
    )
    print(f"wrote {OUT/'dtm.icns'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
