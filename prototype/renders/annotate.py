"""Add labelled callouts to the Blender renders using the projected 3D anchors."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
FONT_B = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_R = "/System/Library/Fonts/Supplemental/Arial.ttf"


def font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def annotate(view: str, title: str, subtitle: str, header: bool = True) -> Path:
    img = Image.open(OUT / f"pdx1_{view}.png").convert("RGBA")
    W, H = img.size
    anchors = json.loads((OUT / f"anchors_{view}.json").read_text())
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    fl = font(FONT_B, int(H * 0.0205))
    ft, fs = font(FONT_B, int(H * 0.040)), font(FONT_R, int(H * 0.022))
    # header gradient band
    for y in range(int(H * 0.15) if header else 0):
        a = int(200 * (1 - y / (H * 0.15)))
        d.line([(0, y), (W, y)], fill=(8, 12, 22, a))
    if header:
        d.text((int(W * 0.03), int(H * 0.03)), title, font=ft, fill=(255, 255, 255, 255))
        d.text((int(W * 0.03), int(H * 0.085)), subtitle, font=fs, fill=(190, 200, 220, 255))
    pts = [(n, x, y) for n, (x, y, z) in anchors.items() if 0 < x < W and 0 < y < H and z > 0]
    left = sorted([p for p in pts if p[1] < W * 0.5], key=lambda p: p[2])
    right = sorted([p for p in pts if p[1] >= W * 0.5], key=lambda p: p[2])
    pad, box_h = int(H * 0.011), int(H * 0.042)
    for side, group in (("L", left), ("R", right)):
        if not group:
            continue
        y_lo, y_hi = (H * 0.19 if header else H * 0.05), H * 0.95
        slots = []
        for _, _, ay in group:
            slots.append(min(max(ay, y_lo), y_hi))
        # enforce minimum spacing
        gap = box_h + pad
        for i in range(1, len(slots)):
            slots[i] = max(slots[i], slots[i - 1] + gap)
        overflow = slots[-1] - y_hi
        if overflow > 0:
            slots = [s - overflow for s in slots]
            for i in range(len(slots) - 2, -1, -1):
                slots[i] = min(slots[i], slots[i + 1] - gap)
        for (name, ax, ay), sy in zip(group, slots):
            tw = d.textlength(name, font=fl)
            bw = tw + 2 * pad
            bx = int(W * 0.025) if side == "L" else int(W * 0.975 - bw)
            by = int(sy - box_h / 2)
            lx = bx + bw if side == "L" else bx
            d.line([(lx, sy), (ax, ay)], fill=(255, 196, 120, 235), width=max(2, H // 540))
            r = max(5, H // 200)
            d.ellipse([ax - r, ay - r, ax + r, ay + r], fill=(255, 150, 60, 255), outline=(255, 255, 255, 255), width=2)
            d.rounded_rectangle([bx, by, bx + bw, by + box_h], radius=int(box_h * 0.25),
                                fill=(12, 18, 32, 215), outline=(255, 170, 90, 255), width=2)
            d.text((bx + pad, by + (box_h - fl.size) / 2 - 2), name, font=fl, fill=(255, 255, 255, 255))
    d.text((int(W * 0.03), int(H * 0.965)), "Concept design · rendered from the build123d CAD model in Blender 5.0 (Cycles) · "
           "orbits and plasma shape from the PDX-1 simulations", font=font(FONT_R, int(H * 0.016)), fill=(170, 178, 195, 255))
    out = OUT / (f"pdx1_{view}_annotated.png" if header else f"pdx1_{view}_callouts.png")
    Image.alpha_composite(img, overlay).convert("RGB").save(out, quality=95)
    return out


if __name__ == "__main__":
    views = sys.argv[1:] or ["hero", "cutaway"]
    meta = {
        "hero": ("PDX-1 linear test stand — concept prototype", "6.9 m beam-target mirror device for p–¹¹B alpha-channeling research"),
        "cutaway": ("Inside the central cell", "Fusion alphas born on the ¹¹B foil gyrate between the HTS mirror coils"),
        "detail": ("Target and IBW antenna detail", "Faraday-shielded straps A1–A4 drive ion-Bernstein waves at 57–127 MHz"),
    }
    for v in views:
        print(annotate(v, *meta[v]))
        print(annotate(v, *meta[v], header=False))
