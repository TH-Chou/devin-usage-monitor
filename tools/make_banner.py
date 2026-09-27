#!/usr/bin/env python3
"""Generate the README hero banner (assets/banner.png).

Dark Liquid-Glass-style card: soft radial glows, the white activity-pulse
mark inside a squircle on the left, project name + tagline on the right.

Usage: .venv/bin/python tools/make_banner.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path(__file__).resolve().parent.parent / "assets"
W, H = 1600, 420

FONTS = (
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/SFNSDisplay.ttf",
)


def font(size: int, index: int = 0) -> ImageFont.FreeTypeFont:
    for path in FONTS:
        try:
            return ImageFont.truetype(path, size, index=index)
        except Exception:
            continue
    return ImageFont.load_default()


def pulse_points(size):
    return [(0.06 * size, 0.55 * size), (0.28 * size, 0.55 * size),
            (0.38 * size, 0.30 * size), (0.50 * size, 0.78 * size),
            (0.60 * size, 0.45 * size), (0.68 * size, 0.55 * size),
            (0.94 * size, 0.55 * size)]


def glow(img: Image.Image, center, radius: int, color, alpha: int):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.ellipse(
        [center[0] - radius, center[1] - radius,
         center[0] + radius, center[1] + radius],
        fill=color + (alpha,),
    )
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(radius * 0.55)))


def main() -> int:
    OUT.mkdir(exist_ok=True)
    img = Image.new("RGBA", (W, H), (9, 10, 18, 255))

    # ambient glows — subtle indigo / cyan
    glow(img, (W * 0.16, H * 0.05), 260, (63, 94, 251), 70)
    glow(img, (W * 0.88, H * 0.95), 300, (34, 140, 200), 55)
    glow(img, (W * 0.55, H * 0.5), 380, (88, 64, 200), 34)

    d = ImageDraw.Draw(img)

    # icon: dark squircle + white pulse
    icon = 230
    ix, iy = 110, (H - icon) // 2
    tile = Image.new("RGBA", (icon * 2, icon * 2), (0, 0, 0, 0))
    td = ImageDraw.Draw(tile)
    td.rounded_rectangle([0, 0, icon * 2 - 1, icon * 2 - 1],
                         int(icon * 2 * 0.24), fill=(18, 20, 30, 255),
                         outline=(255, 255, 255, 46), width=3)
    pts = [(p[0] * 2, p[1] * 2) for p in pulse_points(icon)]
    td.line(pts, fill=(255, 255, 255, 255), width=int(icon * 2 * 0.055),
            joint="curve")
    w2 = icon * 0.055
    for p in (pts[0], pts[-1]):
        td.ellipse([p[0] - w2, p[1] - w2, p[0] + w2, p[1] + w2],
                   fill=(255, 255, 255, 255))
    px, py = pts[3]
    td.ellipse([px - w2 * 1.5, py - w2 * 1.5, px + w2 * 1.5, py + w2 * 1.5],
               fill=(255, 255, 255, 255))
    img.alpha_composite(tile.resize((icon, icon), Image.LANCZOS), (ix, iy))

    # text block — vertically centered against the shorter canvas
    tx = ix + icon + 60
    title_f = font(96)
    sub_f = font(40)
    small_f = font(33)
    d.text((tx, H * 0.20), "Devin Token Monitor",
           font=title_f, fill=(245, 247, 255, 255))
    d.text((tx, H * 0.20 + 118),
           "Local token-usage & cost monitoring for Devin CLI",
           font=sub_f, fill=(186, 198, 230, 255))
    d.text((tx, H * 0.20 + 185),
           "menu bar · dashboard · CSV export · 6 languages",
           font=small_f, fill=(126, 140, 184, 255))

    img.convert("RGB").save(OUT / "banner.png", optimize=True)
    print(f"wrote {OUT/'banner.png'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
