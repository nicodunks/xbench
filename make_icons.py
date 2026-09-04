#!/usr/bin/env python3
"""Make the favicon set and the custom cursor from one source image.

Usage: python3 make_icons.py assets/roon-source.png
Writes assets/favicon.ico, assets/favicon-32.png, assets/apple-touch-icon.png,
and assets/cursor.png (32x32 round crop with a thin light ring).
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps

src = Path(sys.argv[1] if len(sys.argv) > 1 else "assets/roon-source.png")
out = Path("assets")
img = Image.open(src).convert("RGBA")
w, h = img.size
side = min(w, h)
img = img.crop(((w - side) // 2, (h - side) // 2, (w - side) // 2 + side, (h - side) // 2 + side))


def round_icon(size, ring=0):
    base = img.resize((size * 4, size * 4), Image.LANCZOS)
    mask = Image.new("L", base.size, 0)
    ImageDraw.Draw(mask).ellipse((0, 0, base.size[0] - 1, base.size[1] - 1), fill=255)
    base.putalpha(mask)
    if ring:
        d = ImageDraw.Draw(base)
        d.ellipse((0, 0, base.size[0] - 1, base.size[1] - 1), outline=(242, 242, 237, 255), width=ring * 4)
    return base.resize((size, size), Image.LANCZOS)


round_icon(32).save(out / "favicon-32.png")
round_icon(180).save(out / "apple-touch-icon.png")
round_icon(64).save(out / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
round_icon(32, ring=1).save(out / "cursor.png")
print("wrote favicon-32.png, apple-touch-icon.png, favicon.ico, cursor.png")
