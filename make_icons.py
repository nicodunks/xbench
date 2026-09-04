#!/usr/bin/env python3
"""Make the cursor from the source image and the favicon set from an X glyph.

Usage: python3 make_icons.py assets/roon-source.jpg
Writes assets/cursor.png (32x32 round crop with a thin light ring) and
assets/favicon.ico, favicon-32.png, apple-touch-icon.png (an X on ink).
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

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


round_icon(32, ring=1).save(out / "cursor.png")


def font(sz):
    for p in ["/System/Library/Fonts/Supplemental/PTMono-Regular.ttf", "/System/Library/Fonts/Supplemental/Andale Mono.ttf",
              "/System/Library/Fonts/Menlo.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"]:
        try:
            return ImageFont.truetype(p, sz)
        except Exception:
            pass
    return ImageFont.load_default()


def x_icon(size):
    s = size * 4
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, s - 1, s - 1), radius=int(s * .22), fill=(17, 19, 17, 255), outline=(242, 242, 237, 255), width=max(2, s // 32))
    f = font(int(s * .78)); b = d.textbbox((0, 0), "X", font=f)
    d.text(((s - (b[2] - b[0])) / 2 - b[0], (s - (b[3] - b[1])) / 2 - b[1] - s * .02), "X", fill=(242, 242, 237, 255), font=f)
    return im.resize((size, size), Image.LANCZOS)


x_icon(32).save(out / "favicon-32.png")
x_icon(180).save(out / "apple-touch-icon.png")
x_icon(64).save(out / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
print("wrote cursor.png, favicon-32.png, apple-touch-icon.png, favicon.ico")
