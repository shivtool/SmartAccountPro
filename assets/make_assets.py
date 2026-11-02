# -*- coding: utf-8 -*-
"""Installer ke liye branding assets banata hai (app.ico, logo.png, wizard images).
Agar is folder ke bahar (project folder mein) logo.png ya logo.ico rakhi hai to wahi use hoti hai,
warna ek default violet 'SAP' logo banta hai.   Chalaane ke liye:  py -3 assets\\make_assets.py
Zaroorat: pip install pillow"""
import os
import sys
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ACC, DARK, GOLD = (95, 61, 196), (43, 26, 99), (255, 183, 3)
FONTS_B = [r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
FONTS_R = [r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]


def font(cands, size):
    for p in cands:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                pass
    return ImageFont.load_default()


def user_logo():
    for name in ("logo.png", "logo.ico"):
        for d in (ROOT, os.path.dirname(ROOT)):
            p = os.path.join(d, name)
            if os.path.exists(p):
                try:
                    im = Image.open(p)
                    if getattr(im, "n_frames", 1) > 1 or p.endswith(".ico"):
                        try:
                            im.size = max(im.info.get("sizes", {(256, 256)}))
                        except Exception:
                            pass
                    return im.convert("RGBA")
                except Exception:
                    pass
    return None


def gradient(w, h, c1, c2):
    im = Image.new("RGB", (w, h))
    px = im.load()
    for y in range(h):
        t = y / max(1, h - 1)
        col = tuple(round(a + (b - a) * t) for a, b in zip(c1, c2))
        for x in range(w):
            px[x, y] = col
    return im


def default_icon(size=512):
    s = size
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    tile = gradient(s, s, (122, 90, 224), DARK).convert("RGBA")
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, s - 1, s - 1), radius=s // 5, fill=255)
    im.paste(tile, (0, 0), mask)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((s * 0.12, s * 0.80, s * 0.88, s * 0.86), radius=s // 40, fill=GOLD)
    f = font(FONTS_B, int(s * 0.36))
    bb = d.textbbox((0, 0), "SAP", font=f)
    d.text(((s - (bb[2] - bb[0])) / 2 - bb[0], s * 0.34 - bb[1] / 2), "SAP", font=f, fill="white")
    f2 = font(FONTS_B, int(s * 0.17))
    bb = d.textbbox((0, 0), "₹", font=f2)
    d.text(((s - (bb[2] - bb[0])) / 2 - bb[0], s * 0.10 - bb[1] / 2 + s * 0.02), "₹", font=f2, fill=GOLD)
    return im


def square(im, size):
    im = im.copy()
    im.thumbnail((size, size), Image.LANCZOS)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(im, ((size - im.width) // 2, (size - im.height) // 2), im)
    return out


def wizard_large(icon, w, h):
    k = w / 164
    im = gradient(w, h, ACC, DARK)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w, int(6 * k)), fill=GOLD)
    tile = int(88 * k)
    pad = int(8 * k)
    bx, by = (w - tile - 2 * pad) // 2, int(30 * k)
    d.rounded_rectangle((bx, by, bx + tile + 2 * pad, by + tile + 2 * pad), radius=int(14 * k), fill=(255, 255, 255))
    ic = square(icon, tile)
    im.paste(ic, (bx + pad, by + pad), ic)
    f = font(FONTS_B, int(19 * k))
    y = by + tile + 2 * pad + int(20 * k)
    for line in ("Smart", "Account Pro"):
        bb = d.textbbox((0, 0), line, font=f)
        d.text(((w - (bb[2] - bb[0])) / 2 - bb[0], y), line, font=f, fill="white")
        y += int(26 * k)
    d.rectangle((int(w * 0.30), y + int(10 * k), int(w * 0.70), y + int(12 * k)), fill=GOLD)
    fs = font(FONTS_R, int(11 * k))
    for i, line in enumerate(("Accounts  •  Reports", "Backup  •  Security")):
        bb = d.textbbox((0, 0), line, font=fs)
        d.text(((w - (bb[2] - bb[0])) / 2 - bb[0], y + int(22 * k) + i * int(16 * k)), line, font=fs, fill=(226, 216, 250))
    fb = font(FONTS_B, int(12 * k))
    bb = d.textbbox((0, 0), "SHIV COMPUTER", font=fb)
    d.text(((w - (bb[2] - bb[0])) / 2 - bb[0], h - int(30 * k)), "SHIV COMPUTER", font=fb, fill=GOLD)
    return im


def wizard_small(icon, s):
    im = Image.new("RGB", (s, s), (255, 255, 255))
    ic = square(icon, int(s * 0.92))
    im.paste(ic, ((s - ic.width) // 2, (s - ic.height) // 2), ic)
    return im


def main():
    ul = user_logo()
    if ul is not None:
        base = Image.new("RGBA", (512, 512), (255, 255, 255, 0))
        t = square(ul, 480)
        base.paste(t, (16, 16), t)
        print("logo: user logo use hua")
    else:
        base = default_icon(512)
        print("logo: default SAP logo bana")
    base.save(os.path.join(HERE, "logo.png"))
    base.save(os.path.join(HERE, "app.ico"), sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    wizard_large(base, 164, 314).save(os.path.join(HERE, "wiz_large.bmp"))
    wizard_large(base, 328, 628).save(os.path.join(HERE, "wiz_large_2x.bmp"))
    wizard_small(base, 55).save(os.path.join(HERE, "wiz_small.bmp"))
    wizard_small(base, 110).save(os.path.join(HERE, "wiz_small_2x.bmp"))
    print("assets taiyar:", HERE)


if __name__ == "__main__":
    sys.exit(main())
