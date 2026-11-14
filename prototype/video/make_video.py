"""PDX-1 explainer video: narrated scenes (macOS `say`) over renders, charts and diagrams.

Output: video/out/PDX1_explainer.mp4 (1920x1080, 30 fps, H.264/AAC) + captions (.srt).
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

HERE = Path(__file__).resolve().parent
PROTO = HERE.parent
OUT = HERE / "out"
WORK = OUT / "work"
WORK.mkdir(parents=True, exist_ok=True)
FFMPEG = shutil.which("ffmpeg")
FFPROBE = shutil.which("ffprobe")
VOICE, RATE = "Daniel", 168
W, H, FPS = 1920, 1080, 30
NAVY, INK, MUTED, ACCENT = (13, 22, 40), (29, 36, 51), (96, 104, 122), (232, 131, 58)
FB = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FR = "/System/Library/Fonts/Supplemental/Arial.ttf"
R = PROTO / "renders" / "out"
S = PROTO / "sim" / "out"
D = PROTO / "diagrams" / "out"
G = PROTO / "drawings" / "out"


def f(path, size):
    return ImageFont.truetype(path, size)


def wrap(draw, text, font, width):
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if draw.textlength(t, font=font) <= width:
            cur = t
        else:
            lines.append(cur); cur = w_
    lines.append(cur)
    return lines


def caption_band(img, caption, dark=False):
    d = ImageDraw.Draw(img, "RGBA")
    band = 128
    d.rectangle([0, H - band, W, H], fill=(10, 16, 30, 225) if dark else (243, 245, 248, 255))
    fc = f(FR, 33)
    lines = wrap(d, caption, fc, W - 160)[:2]
    y = H - band + (band - 44 * len(lines)) / 2
    for ln in lines:
        d.text((80, y), ln, font=fc, fill=(235, 240, 248) if dark else INK)
        y += 44
    d.ellipse([40, H - band / 2 - 7, 54, H - band / 2 + 7], fill=ACCENT)


def chart_slide(path, title, caption, scene):
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 118], fill=NAVY)
    d.text((70, 30), title, font=f(FB, 50), fill="white")
    d.text((W - 70, 46), "PARC-Delta · PDX-1", font=f(FR, 28), fill=(170, 182, 205), anchor="ra")
    ch = Image.open(path).convert("RGB")
    box_w, box_h = W - 140, H - 118 - 128 - 50
    sc = min(box_w / ch.width, box_h / ch.height)
    ch = ch.resize((int(ch.width * sc), int(ch.height * sc)), Image.LANCZOS)
    img.paste(ch, ((W - ch.width) // 2, 118 + 25 + (box_h - ch.height) // 2))
    caption_band(img, caption)
    out = WORK / f"{scene}.png"
    img.save(out)
    return out


def render_slide(path, caption, scene, darken=1.0):
    img = Image.open(path).convert("RGB").resize((W, H), Image.LANCZOS)
    if darken != 1.0:
        img = ImageEnhance.Brightness(img).enhance(darken)
    caption_band(img, caption, dark=True)
    out = WORK / f"{scene}.png"
    img.save(out)
    return out


def title_slide(scene):
    img = Image.open(R / "pdx1_hero.png").convert("RGB").resize((W, H), Image.LANCZOS)
    img = ImageEnhance.Brightness(img).enhance(0.42)
    d = ImageDraw.Draw(img)
    d.text((110, 330), "PDX-1", font=f(FB, 150), fill="white")
    d.text((116, 520), "A concept test stand for p–¹¹B alpha-channeling research", font=f(FR, 50), fill=(225, 232, 245))
    d.text((116, 600), "CAD · simulation · prototype renders · validation", font=f(FR, 38), fill=(255, 175, 110))
    d.text((116, 900), "PARC-Delta research programme  ·  concept study, not a reactor or power plant", font=f(FR, 30), fill=(170, 182, 205))
    out = WORK / f"{scene}.png"
    img.save(out)
    return out


def end_slide(scene):
    img = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(img)
    d.text((110, 300), "Every number in this video is simulated", font=f(FB, 64), fill="white")
    d.text((110, 390), "and every open question is stated.", font=f(FB, 64), fill="white")
    lines = ["76/76 tests pass  ·  v1.6 reproduced to 7.5e-10",
             "3.0 T HTS mirror  ·  0.1% alpha wall loss  ·  39.7% loss cone = theory",
             "Open: TA/Nanbu 6–7% gap · alpha accumulation · nonlinear + irreversible heating"]
    for k, ln in enumerate(lines):
        d.text((116, 560 + k * 70), ln, font=f(FR, 38), fill=(255, 175, 110) if k == 2 else (215, 225, 240))
    d.text((116, 930), "PARC-Delta · PDX-1 concept study · 2026-11-01", font=f(FR, 30), fill=(150, 162, 185))
    out = WORK / f"{scene}.png"
    img.save(out)
    return out


SCENES = [
    ("s01", "title", None, "",
     "This is P D X one: a concept test stand for the PARC Delta research programme on proton boron eleven fusion and "
     "alpha channeling. Everything you will see was designed, simulated and rendered from one shared set of parameters."),
    ("s02", "turntable", None, "6.9 m linear mirror · 0.675 MeV protons → 1 µm ¹¹B foil at the centre of a 3 T HTS magnet",
     "P D X one is a six point nine metre linear mirror. A seven hundred kilovolt accelerator fires six hundred and seventy five "
     "kilo electron volt protons through a helicon plasma source, onto a one micron boron eleven foil at the centre of a three tesla superconducting magnet."),
    ("s03", "render", R / "pdx1_hero_annotated.png", "2 mirror + 6 main REBCO coils at 20 K · 4 IBW antennas · α, wave and heating diagnostics",
     "The central cell has two mirror coils and six main coils, all high temperature superconductor at twenty kelvin, four "
     "Faraday shielded ion Bernstein wave antennas, and diagnostics for alpha particles, waves and proton heating."),
    ("s04", "render", R / "pdx1_cutaway_annotated.png", "The orange orbits are simulated trajectories from the PARC-Delta α0/α1 birth source — not artwork",
     "Inside, each fusion reaction makes three alpha particles. The orange orbits are not artwork. They are simulated "
     "trajectories from the PARC Delta birth source model, pushed through the simulated magnetic field."),
    ("s05", "chart", S / "fig_magnet_axis.png", "B0 = 3.00 T, mirror ratio 1.63 · ~10 T on the mirror windings → design moved from NbTi to REBCO HTS",
     "The magnet simulation gives three point zero tesla at the centre and a mirror ratio of one point six three. It also "
     "flagged about ten tesla on the mirror windings, beyond practical niobium titanium margins, so the design moved to REBCO."),
    ("s06", "chart", S / "fig_alpha_phase_space.png", "Solver check: simulated end loss 39.67% vs analytic loss cone 39.69%",
     "The orbit solver was checked against theory. Alphas inside the magnetic loss cone escape, and the simulated end loss "
     "of thirty nine point seven percent matches the analytic prediction."),
    ("s07", "chart", S / "fig_alpha_fate_vs_B.png", "Wall loss falls from 76% at 1 T to 0.1% at 3 T — why the design point is 3 T",
     "Scanning the field shows why three tesla was chosen. Wall losses fall from seventy six percent at one tesla to about zero point one percent."),
    ("s08", "chart", S / "fig_alpha_budget.png", "Honest finding: µA beam-foil alphas are ~10⁹× too sparse to self-excite IBWs → Phase 2 needs a surrogate fast-ion source",
     "The simulations also told us something important. An on axis foil re intersects many trapped alphas within microseconds, "
     "and a microamp beam makes roughly a billion times too few alphas to drive the waves on their own. So phase one measures "
     "the birth spectrum, and phase two needs a surrogate energetic ion source."),
    ("s09", "chart", S / "fig_resonance_map.png", "Channels A1–A4 (57.6–126.6 MHz) sit between alpha harmonics; retuning moves each resonance layer along the axis",
     "The four antenna channels, from fifty seven to one hundred and twenty seven megahertz, sit between alpha cyclotron harmonics. "
     "Because the field varies along the axis, retuning a channel moves its resonance layer. That is the actuator for the scheduler."),
    ("s10", "chart", D / "d2_control_loop.png", "Hypothesis under test — not a demonstrated result",
     "The hypothesis under test is that a distribution aware scheduler, which senses, estimates, decides and acts every cycle, "
     "can steer more alpha energy into protons than a fixed wave baseline, with the same R F budget."),
    ("s11", "chart", D / "d3_energy_flow.png", "The baseline to beat: ~73% of alpha energy to electrons (reactor-like), 99.9% at bench temperature",
     "This is the baseline to beat. In a reactor like plasma, about seventy three percent of alpha energy goes to electrons. At bench temperature, nearly all of it."),
    ("s12", "chart", D / "d4_validation.png", "76/76 tests · v1.6 reproduced to 7.5e-10 · nonlinear and irreversible-heating gates still open",
     "On the software side, all seventy six tests pass, and the full version one point six campaign reproduced to better than one part in a billion. "
     "The nonlinear and irreversible heating gates remain open, and we say so."),
    ("s13", "chart", G / "PDX1-GA-001_paper_hi.png", "General arrangement PDX1-GA-001 (A0, 1:10) generated headlessly in CADCraft from the same parameter file",
     "The general arrangement drawing was generated in CAD Craft from the same parameters, alongside a STEP model ready for engineering review."),
    ("s14", "chart", D / "d5_roadmap.png", "Each phase has a falsifiable exit test",
     "Next: close the collision gap, build the magnet and beam target stage, then test the scheduler against fair baselines. Each phase has a falsifiable exit test."),
    ("s15", "end", None, "", "Every number here is simulated, and every open question is stated. Thank you."),
]


def duration(path):
    out = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True)
    return float(out.stdout.strip())


def srt_time(t):
    h, m = int(t // 3600), int(t % 3600 // 60)
    s = t % 60
    return f"{h:02d}:{m:02d}:{int(s):02d},{int((s % 1) * 1000):03d}"


def main():
    clips, srt, t0 = [], [], 0.0
    turntable = sorted((R / "turntable").glob("f_*.png"))
    for scene, kind, src, caption, narration in SCENES:
        audio = WORK / f"{scene}.aiff"
        subprocess.run(["say", "-v", VOICE, "-r", str(RATE), "-o", str(audio), narration], check=True)
        dur = duration(audio) + 0.9
        clip = WORK / f"{scene}.mp4"
        fade = f"fade=t=in:st=0:d=0.35,fade=t=out:st={dur - 0.35:.2f}:d=0.35"
        if kind == "turntable":
            frames_dir = WORK / "tt"
            frames_dir.mkdir(exist_ok=True)
            for k, fr in enumerate(turntable):
                img = Image.open(fr).convert("RGB").resize((W, H), Image.LANCZOS)
                caption_band(img, caption, dark=True)
                img.save(frames_dir / f"t_{k:04d}.png")
            vin = ["-stream_loop", "-1", "-framerate", "15", "-i", str(frames_dir / "t_%04d.png")]
            vf = f"fps={FPS},{fade},format=yuv420p"
        else:
            png = {"title": lambda: title_slide(scene), "end": lambda: end_slide(scene),
                   "render": lambda: render_slide(src, caption, scene),
                   "chart": lambda: chart_slide(src, caption.split(" · ")[0] if False else TITLES.get(scene, ""), caption, scene)}[kind]()
            vin = ["-loop", "1", "-framerate", str(FPS), "-i", str(png)]
            if kind in ("render", "title"):
                nfr = int(dur * FPS)
                vf = (f"scale=2400:-2,zoompan=z='1+0.05*on/{nfr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={FPS},"
                      f"{fade},format=yuv420p")
            else:
                vf = f"{fade},format=yuv420p"
        cmd = [FFMPEG, "-y", "-loglevel", "error", *vin, "-i", str(audio), "-t", f"{dur:.2f}",
               "-vf", vf, "-af", f"apad,afade=t=out:st={dur - 0.3:.2f}:d=0.3", "-c:v", "libx264", "-preset", "medium",
               "-crf", "20", "-r", str(FPS), "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2", str(clip)]
        subprocess.run(cmd, check=True)
        clips.append(clip)
        srt.append((t0, t0 + dur - 0.5, narration))
        t0 += dur
        print(f"{scene}: {dur:.1f}s")
    lst = WORK / "concat.txt"
    lst.write_text("".join(f"file '{c}'\n" for c in clips))
    final = OUT / "PDX1_explainer.mp4"
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy",
                    "-movflags", "+faststart", str(final)], check=True)
    (OUT / "PDX1_explainer.srt").write_text("".join(f"{i+1}\n{srt_time(a)} --> {srt_time(b)}\n{t}\n\n" for i, (a, b, t) in enumerate(srt)))
    print("total", round(t0, 1), "s ->", final)


TITLES = {
    "s05": "Magnet: field on axis", "s06": "Orbit solver vs theory", "s07": "Choosing the field",
    "s08": "Alpha inventory budget", "s09": "IBW channel plan", "s10": "The hypothesis",
    "s11": "Baseline to beat", "s12": "Validation status", "s13": "Engineering drawing", "s14": "Roadmap",
}

if __name__ == "__main__":
    main()
