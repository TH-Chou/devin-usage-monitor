#!/usr/bin/env python3
"""Render 3 icon candidates on the shared glass tile for user selection.

A: deep-blue gradient tile + white pulse/activity line (monitoring)
B: deep-blue gradient tile + white lightning bolt (token energy)
C: light glass tile + slate gauge ring (quota usage)

Usage: .venv/bin/python tools/icon_candidates.py
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from make_icon import lerp, squircle_mask

OUT = Path(__file__).resolve().parent.parent / "assets" / "candidates"
S = 1024
INNER = int(S * 0.804)


def tile(top, bot):
    t = Image.new("RGBA", (INNER, INNER), (0, 0, 0, 0))
    g = Image.new("RGB", (1, INNER))
    for y in range(INNER):
        tt = (y / INNER) ** 1.12
        g.putpixel((0, y), lerp(top, bot, tt))
    t.paste(g.resize((INNER, INNER)), (0, 0))
    m = squircle_mask(INNER)
    out = Image.new("RGBA", (INNER, INNER), (0, 0, 0, 0))
    out.paste(t, (0, 0), m)
    # glass sheen
    sheen = Image.new("RGBA", (INNER, INNER), (0, 0, 0, 0))
    ImageDraw.Draw(sheen).ellipse(
        [-int(0.25 * INNER), -int(0.42 * INNER),
         int(1.25 * INNER), int(0.62 * INNER)],
        fill=(255, 255, 255, 80 if top[0] < 120 else 110),
    )
    sheen = sheen.filter(ImageFilter.GaussianBlur(60))
    out.paste(sheen, (0, 0), m)
    return out


def pulse_mark(size, width_ratio=0.085):
    """Heartbeat/activity polyline."""
    w = width_ratio * size
    pts = [(0.06, 0.55), (0.28, 0.55), (0.38, 0.30), (0.50, 0.78),
           (0.60, 0.45), (0.68, 0.55), (0.94, 0.55)]
    return [(x * size, y * size) for x, y in pts], w


def bolt_mark(size):
    w, h = int(0.5 * size), int(0.62 * size)
    ox, oy = (size - w) // 2, int(0.19 * size)
    return [(0.56 * w + ox, 0.0 + oy), (0.20 * w + ox, 0.58 * h + oy),
            (0.46 * w + ox, 0.58 * h + oy), (0.36 * w + ox, 1.0 * h + oy),
            (0.80 * w + ox, 0.38 * h + oy), (0.52 * w + ox, 0.38 * h + oy)]


def gauge_mark(size, track, fill_color, frac=0.72):
    cx, cy, r = size / 2, size / 2, 0.30 * size
    w = int(0.075 * size)
    box = [cx - r, cy - r, cx + r, cy + r]
    return box, w, frac


def compose(mark_fn, top, bot):
    img = tile(top, bot)
    mark_fn(img)
    canvas = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    off = (S - INNER) // 2
    canvas.paste(img, (off, off))
    return canvas


def variant_a():  # pulse on deep blue
    def m(img):
        pts, w = pulse_mark(INNER)
        # shadow
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).line(pts, fill=(10, 20, 40, 150),
                                width=int(w), joint="curve")
        img.paste(sh.filter(ImageFilter.GaussianBlur(16)), (0, int(w * 0.5)))
        d = ImageDraw.Draw(img)
        d.line(pts, fill=(255, 255, 255, 255), width=int(w), joint="curve")
        # rounded caps
        for p in (pts[0], pts[-1]):
            d.ellipse([p[0] - w / 2, p[1] - w / 2, p[0] + w / 2, p[1] + w / 2],
                      fill=(255, 255, 255, 255))
        # dot at pulse peak
        px, py = pts[3]
        d.ellipse([px - w * 0.95, py - w * 0.95, px + w * 0.95, py + w * 0.95],
                  fill=(255, 255, 255, 255))
    return compose(m, (96, 128, 190), (52, 82, 150))


def variant_b():  # white bolt on deep blue
    def m(img):
        poly = bolt_mark(INNER)
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).polygon(
            [(x, y + INNER * 0.025) for x, y in poly],
            fill=(10, 20, 40, 150))
        img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(20)))
        ImageDraw.Draw(img).polygon(poly, fill=(255, 255, 255, 255))
    return compose(m, (96, 128, 190), (52, 82, 150))


def variant_c():  # gauge ring on glass
    def m(img):
        box, w, frac = gauge_mark(INNER, None, None)
        d = ImageDraw.Draw(img)
        d.arc(box, 0, 360, fill=(140, 158, 182, 120), width=w)
        # filled arc from -90deg
        d.arc(box, -90, -90 + 360 * frac, fill=(88, 112, 152, 255), width=w)
        # end cap
        ang = math.radians(-90 + 360 * frac)
        cx, cy = INNER / 2, INNER / 2
        r = 0.30 * INNER
        x, y = cx + r * math.cos(ang), cy + r * math.sin(ang)
        d.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2],
                  fill=(88, 112, 152, 255))
        # center bolt mini
        bp = [(x * 0.92 + cx * 0.08, y * 0.92 + cy * 0.08) for x, y in bolt_mark(int(INNER * 0.55))]
        ImageDraw.Draw(img).polygon(
            [(px + (cx - INNER * 0.275), py + (cy - INNER * 0.30))
             for px, py in bolt_mark(int(INNER * 0.55))],
            fill=(88, 112, 152, 255))
    return compose(m, (236, 241, 249), (197, 210, 231))


OUT.mkdir(parents=True, exist_ok=True)
for name, fn in (("A_pulse", variant_a), ("B_bolt", variant_b),
                 ("C_gauge", variant_c)):
    fn().save(OUT / f"{name}.png")
    print("wrote", OUT / f"{name}.png")
