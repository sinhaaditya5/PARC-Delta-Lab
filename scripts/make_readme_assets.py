#!/usr/bin/env python3
"""Build the README imagery in docs/assets/ from pipeline outputs.

Reads the full-resolution outputs written by the prototype pipeline
(prototype/*/out) and writes web-sized copies:

  docs/assets/banner.jpg                 hero render with title overlay
  docs/assets/renders/*.jpg              hero, cutaway and detail stills
  docs/assets/pdx1_turntable.gif         turntable loop (needs ffmpeg)
  docs/assets/charts/*.png               simulation charts
  docs/assets/diagrams/*.png             system diagrams
  docs/assets/drawing/PDX1-GA-001.png    general-arrangement drawing

Usage:
  python scripts/make_readme_assets.py [--proto PATH] [--out PATH]
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
MAX_W = 1600

RENDERS = ["pdx1_hero", "pdx1_cutaway_annotated", "pdx1_detail_annotated"]
CHARTS = [
    "fig_magnet_axis", "fig_magnet_map", "fig_alpha_orbits", "fig_alpha_phase_space",
    "fig_alpha_fate_vs_B", "fig_alpha_fate_history", "fig_alpha_target_offset",
    "fig_bench_slowing_down", "fig_alpha_budget", "fig_resonance_map",
]
DIAGRAMS = ["d1_architecture", "d2_control_loop", "d3_energy_flow", "d4_validation", "d5_roadmap"]

FONT_CANDIDATES = {
    "bold": ["/System/Library/Fonts/Supplemental/Arial Bold.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    "regular": ["/System/Library/Fonts/Supplemental/Arial.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
}


def font(kind: str, size: int) -> ImageFont.ImageFont:
    for path in FONT_CANDIDATES[kind]:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size)


def fit_width(im: Image.Image, width: int = MAX_W) -> Image.Image:
    if im.width <= width:
        return im
    return im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)


def save_jpg(src: Path, dst: Path, quality: int = 86) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    fit_width(Image.open(src).convert("RGB")).save(dst, quality=quality, optimize=True, progressive=True)


def save_png(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    fit_width(Image.open(src).convert("RGB")).save(dst, optimize=True)


def banner(hero: Path, dst: Path) -> None:
    """1600x520 banner: title on a dark field (left), hero render faded in (right)."""
    W, H, BG = 1600, 520, (12, 16, 26)
    render_w, offset_x = 1120, 500
    shot = Image.open(hero).convert("RGB")
    shot = shot.resize((render_w, round(shot.height * render_w / shot.width)), Image.LANCZOS)
    top = max(0, (shot.height - H) // 2 + 10)
    shot = shot.crop((0, top, render_w, top + H))

    # Horizontal alpha ramp so the render dissolves into the background.
    ramp = Image.new("L", (render_w, H))
    px = ramp.load()
    fade = 300
    for x in range(render_w):
        a = 255 if x >= fade else int(255 * (x / fade) ** 1.6)
        for y in range(H):
            px[x, y] = a
    im = Image.new("RGB", (W, H), BG)
    im.paste(shot, (offset_x, 0), ramp.filter(ImageFilter.GaussianBlur(4)))

    d = ImageDraw.Draw(im)
    x0 = 64
    d.text((x0, 150), "PARC-Delta Lab", font=font("bold", 74), fill=(245, 247, 250))
    d.text((x0, 248), "p–¹¹B alpha-channeling research model", font=font("regular", 32), fill=(196, 206, 224))
    d.text((x0, 292), "+ PDX-1 linear test-stand concept study", font=font("regular", 32), fill=(196, 206, 224))
    d.rectangle((x0, 360, x0 + 120, 365), fill=(232, 131, 58))
    d.text((x0, 384), "simulation · CAD · drawings · renders · reproducible pipeline",
           font=font("regular", 22), fill=(150, 162, 184))
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst, quality=88, optimize=True, progressive=True)


def turntable_gif(frames_dir: Path, dst: Path, width: int = 600, fps: int = 10) -> bool:
    ffmpeg = shutil.which("ffmpeg")
    frames = sorted(frames_dir.glob("f_*.png"))
    if not ffmpeg or not frames:
        print(f"skip turntable GIF (ffmpeg={bool(ffmpeg)}, frames={len(frames)})")
        return False
    with tempfile.TemporaryDirectory() as tmp:
        palette = Path(tmp) / "palette.png"
        src = ["-framerate", "24", "-i", str(frames_dir / "f_%04d.png")]
        vf = f"fps={fps},scale={width}:-1:flags=lanczos"
        subprocess.run([ffmpeg, "-y", "-loglevel", "error", *src,
                        "-vf", f"{vf},palettegen=stats_mode=diff", str(palette)], check=True)
        subprocess.run([ffmpeg, "-y", "-loglevel", "error", *src, "-i", str(palette),
                        "-lavfi", f"{vf}[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=4",
                        "-loop", "0", str(dst)], check=True)
    return True


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--proto", type=Path, default=ROOT / "prototype", help="prototype folder with */out outputs")
    ap.add_argument("--out", type=Path, default=ROOT / "docs" / "assets")
    args = ap.parse_args()
    P, O = args.proto, args.out

    renders = P / "renders" / "out"
    banner(renders / "pdx1_hero.png", O / "banner.jpg")
    for name in RENDERS:
        save_jpg(renders / f"{name}.png", O / "renders" / f"{name}.jpg")
    turntable_gif(renders / "turntable", O / "pdx1_turntable.gif")
    for name in CHARTS:
        save_png(P / "sim" / "out" / f"{name}.png", O / "charts" / f"{name}.png")
    for name in DIAGRAMS:
        save_png(P / "diagrams" / "out" / f"{name}.png", O / "diagrams" / f"{name}.png")
    save_png(P / "drawings" / "out" / "PDX1-GA-001_paper_hi.png", O / "drawing" / "PDX1-GA-001.png")

    total = sum(f.stat().st_size for f in O.rglob("*") if f.is_file())
    print(f"wrote {sum(1 for f in O.rglob('*') if f.is_file())} files, {total / 1e6:.1f} MB -> {O}")


if __name__ == "__main__":
    main()
