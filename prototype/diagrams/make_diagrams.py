"""PDX-1 / PARC-Delta explanatory diagrams (PNG, 200 dpi) for the docx, deck and video."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

HERE = Path(__file__).resolve().parent
PROTO = HERE.parent
sys.path.insert(0, str(PROTO / "design"))
from plotstyle import COLORS, apply_style  # noqa: E402

OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
SIM = json.loads((PROTO / "sim" / "out" / "bench_physics_summary.json").read_text())
ORB = json.loads((PROTO / "sim" / "out" / "alpha_orbit_summary.json").read_text())
MAG = json.loads((PROTO / "sim" / "out" / "magnet_summary.json").read_text())

INK, MUTED = COLORS["ink"], COLORS["muted"]
FILL = {"blue": "#e7eefb", "orange": "#fdeedf", "green": "#e3f3ea", "grey": "#eef0f4", "red": "#f8e3e6",
        "purple": "#efe7f8"}
EDGE = {"blue": COLORS["primary"], "orange": COLORS["accent"], "green": COLORS["good"], "grey": MUTED,
        "red": COLORS["target"], "purple": COLORS["boron"]}


def canvas(w=13.33, h=7.0):
    apply_style()
    fig = plt.figure(figsize=(w, h))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100); ax.set_ylim(0, 100 * h / w)
    ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, title, body="", tone="blue", tsize=12.5, bsize=9.8):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.25,rounding_size=1.2",
                                fc=FILL[tone], ec=EDGE[tone], lw=1.6))
    ax.text(x + w / 2, y + h - 1.9, title, ha="center", va="top", fontsize=tsize, fontweight="bold", color=INK)
    if body:
        ax.text(x + w / 2, y + h - 5.4, body, ha="center", va="top", fontsize=bsize, color=INK, linespacing=1.35)
    return (x, y, w, h)


def arrow(ax, p0, p1, label="", color=None, style="-|>", ls="-", lw=1.8, rad=0.0, lpos=0.5, loff=(0, 1.2), lsize=9.2):
    color = color or MUTED
    a = FancyArrowPatch(p0, p1, arrowstyle=style, mutation_scale=16, color=color, lw=lw, ls=ls,
                        connectionstyle=f"arc3,rad={rad}")
    ax.add_patch(a)
    if label:
        mx, my = p0[0] + (p1[0] - p0[0]) * lpos + loff[0], p0[1] + (p1[1] - p0[1]) * lpos + loff[1]
        ax.text(mx, my, label, ha="center", va="bottom", fontsize=lsize, color=color, fontweight="bold")


def title(ax, t, sub=""):
    ax.text(3, 49.6, t, fontsize=19, fontweight="bold", color=INK, va="top")
    if sub:
        ax.text(3, 46.2, sub, fontsize=11, color=MUTED, va="top")


# --------------------------------------------------------------------------- D1 architecture
def d1():
    fig, ax = canvas()
    title(ax, "PDX-1 system architecture", "Beam path (top row) and the control / support systems (bottom row) — concept design")
    box(ax, 3, 25, 17, 15, "Proton accelerator", "0.7 MV electrostatic\n0.675 MeV, 10 µA\nquadrupole triplet", "grey")
    box(ax, 24, 25, 15, 15, "Helicon source", "H plasma column\nn ≈ 1e19 m⁻³\nTe ≈ 10 eV", "purple")
    box(ax, 43, 22, 26, 20.5, "Mirror central cell", f"B0 = {MAG['B0_on_axis_T']:.1f} T,  mirror ratio {MAG['mirror_ratio']:.2f}\n"
        "1 µm ¹¹B foil at X = 0\np + ¹¹B → 3α  (≈3 MeV mean)\nIBW straps A1–A4\nlimiter r = 250 mm", "blue")
    box(ax, 73, 25, 13, 15, "End-loss tank", "Cu beam dump\nend-loss\nanalyzer", "grey")
    box(ax, 3, 2.5, 21, 15, "Diagnostics", "Si α-spectrometer\nFILD · Thomson\nB-dot · RFEA\ninterferometer", "green", bsize=9.4)
    box(ax, 27, 2.5, 21, 15, "FPGA scheduler", "estimate α gradients\npick channel f, φ, P\nenforce constraints", "orange", bsize=9.4)
    box(ax, 51, 2.5, 21, 15, "RF chain ×4", "57.6–126.6 MHz amps\nL-match boxes\n7/16 vacuum feeds", "orange", bsize=9.4)
    box(ax, 75, 2.5, 22, 15, "HTS magnet + cryo", "2 mirror + 6 main\nREBCO coils, 20 K\n~14 MJ stored", "blue", bsize=9.4)
    arrow(ax, (20.4, 32.5), (23.6, 32.5), "", COLORS["primary"])
    arrow(ax, (39.4, 32.5), (42.6, 32.5), "p⁺", COLORS["primary"], loff=(0, 0.6))
    arrow(ax, (69.4, 32.5), (72.6, 32.5), "", COLORS["primary"])
    arrow(ax, (47, 21.6), (16, 17.9), "α, wave, heat signals", COLORS["good"], rad=0.12, lpos=0.55, loff=(0, 0.8))
    arrow(ax, (24.4, 10), (26.6, 10), "", COLORS["good"])
    arrow(ax, (48.4, 10), (50.6, 10), "", COLORS["accent"])
    arrow(ax, (61.5, 17.9), (61.5, 21.6), "RF power", COLORS["accent"], loff=(4.6, -1.2))
    arrow(ax, (80, 17.9), (68.6, 22.4), "B-field", COLORS["primary"], loff=(3.5, -0.4))
    fig.savefig(OUT / "d1_architecture.png", dpi=200)
    plt.close(fig)


# --------------------------------------------------------------------------- D2 control loop
def d2():
    fig, ax = canvas()
    title(ax, "Closed-loop resonance scheduler (the hypothesis under test)",
          "Distribution-aware control of a coupled set of IBW modes — PARC-Delta research hypothesis, not a demonstrated result")
    s = box(ax, 4, 18.5, 20, 16.5, "1 · SENSE", "Si α-spectrometer, FILD\nB-dot wave spectra\nRFEA proton heating\nThomson ne, Te", "green")
    e = box(ax, 28, 18.5, 20, 16.5, "2 · ESTIMATE", "α phase-space gradients\nspecies-resolved γ\n(PARC-Delta kinetic\nmodel + ledger)", "blue")
    d = box(ax, 52, 18.5, 20, 16.5, "3 · DECIDE", "choose channels A1–A4:\nfrequency, phase, power\nvia resonance map\n(layer moves with f)", "orange")
    a = box(ax, 76, 18.5, 20, 16.5, "4 · ACT", "4× RF amplifiers\nmatching networks\nFaraday-shielded straps", "orange")
    p = box(ax, 34, 2, 32, 11.5, "PLASMA", "α → IBW → protons (irreversible heat?)\nα → electrons (collisional baseline)", "purple", bsize=9.6)
    for x0, x1 in ((24.5, 27.6), (48.5, 51.6), (72.5, 75.6)):
        arrow(ax, (x0, 27), (x1, 27), color=INK)
    arrow(ax, (86, 18.1), (66.5, 8), "RF fields", COLORS["accent"], rad=-0.25, loff=(3, -1))
    arrow(ax, (33.6, 8), (14, 18.1), "measurements", COLORS["good"], rad=-0.25, loff=(-4, -1))
    c = box(ax, 22, 36.8, 56, 6.0, "Constraints enforced every cycle", "", "red", tsize=11)
    ax.text(50, 37.8, "RF budget ≤ fixed · electron heating ≤ baseline · wall load ≤ limit · stop rules (Gate 5)",
            ha="center", fontsize=9.5, color=INK)
    fig.savefig(OUT / "d2_control_loop.png", dpi=200)
    plt.close(fig)


# --------------------------------------------------------------------------- D3 energy flow
def d3():
    fig, ax = canvas()
    title(ax, "Where does fusion-alpha energy go?", "Simulated classical (collisional) baselines from PARC-Delta v1.6 — the number channeling must beat")
    sd = SIM["slowing_down"]["3.12MeV"]

    def bar(y, label, parts, note):
        ax.text(3, y + 3.2, label, fontsize=12, fontweight="bold", color=INK)
        x = 3
        for name, frac, col in parts:
            w = 90 * frac
            ax.add_patch(FancyBboxPatch((x, y - 2.6), max(w, 0.35), 5.2, boxstyle="square,pad=0", fc=col, ec="white", lw=1.5))
            if w > 7:
                ax.text(x + w / 2, y, f"{name}\n{frac*100:.1f}%", ha="center", va="center", color="white", fontsize=10.5, fontweight="bold")
            x += w
        ax.text(3, y - 5.3, note, fontsize=9.6, color=MUTED)

    bar(33, "Reactor-like background (10 keV, 1e20 m⁻³) — v1.6 Rosenbluth result",
        [("electrons", 0.73, COLORS["electron"]), ("protons", 0.265, COLORS["proton"]), ("", 0.006, COLORS["alpha"])],
        "≈73% electrons · 26–27% protons · 0.6% thermal alphas (fixed Maxwellian reservoirs, test-particle)")
    bar(16, "PDX-1 bench plasma (Te = 10 eV, 1e19 m⁻³) — same solver",
        [("electrons", sd["electron_share_of_deposited_energy"], COLORS["electron"]),
         ("", sd["proton_share_of_deposited_energy"], COLORS["proton"])],
        f"{sd['electron_share_of_deposited_energy']*100:.2f}% to electrons; 3.1 MeV α slows to 50 keV in {sd['time_to_50keV_ms']:.1f} ms")
    ax.text(97, 6, "Goal of α-channeling: divert this energy into protons via IBWs —\nto be shown experimentally against these baselines.",
            ha="right", fontsize=10.5, color=COLORS["accent"], fontweight="bold")
    fig.savefig(OUT / "d3_energy_flow.png", dpi=200)
    plt.close(fig)


# --------------------------------------------------------------------------- D4 validation gates
def d4():
    fig, ax = canvas()
    title(ax, "Validation ladder: what is proven, partial, and open", "PARC-Delta acceptance gates (v1.6) plus the PDX-1 device studies done in this work")
    gates = [
        ("Gate 0", "Input + energy accounting ledger", "done", "green"),
        ("Gate 1", "Collisionless linear IBW benchmark (LAPD case)", "done*", "green"),
        ("Gate 2", "Finite-width, collisional kinetics, α source, slowing-down", "partial", "orange"),
        ("Gate 3", "Nonlinear kinetic (PIC) benchmark", "open", "red"),
        ("Gate 4", "Coherent vs irreversible proton heating", "open", "red"),
        ("Gate 5", "Fair baselines B0 / B1 / B2", "open", "red"),
        ("Gate 6", "Self-consistent p–¹¹B energy balance", "open", "red"),
    ]
    for k, (g, d, st, tone) in enumerate(gates):
        y = 40 - k * 5.4
        ax.add_patch(FancyBboxPatch((3 + k * 1.2, y), 52, 4.4, boxstyle="round,pad=0.1,rounding_size=0.8", fc=FILL[tone], ec=EDGE[tone], lw=1.4))
        ax.text(4.5 + k * 1.2, y + 2.2, g, fontsize=11, fontweight="bold", color=INK, va="center")
        ax.text(13 + k * 1.2, y + 2.2, d, fontsize=10, color=INK, va="center")
        ax.text(53.5 + k * 1.2, y + 2.2, st.upper(), fontsize=9.5, fontweight="bold", color=EDGE[tone], va="center", ha="right")
    ax.text(3, 2.2, "* Gate 1: published exact-crossing residue/mass-convention discrepancy remains open.", fontsize=9, color=MUTED)
    box(ax, 64, 4, 33, 39.5, "Tested in this work", "", "blue", tsize=12.5)
    items = [
        "✓ 76/76 unit + regression tests pass",
        "✓ v1.6 results reproduced on a clean\n   toolchain (max rel. diff 7.5e-10)",
        f"✓ Magnet: B0 {MAG['B0_on_axis_T']:.2f} T, R {MAG['mirror_ratio']:.2f},\n   ~{MAG['stored_magnetic_energy_MJ']:.0f} MJ → HTS decision",
        f"✓ Orbit solver vs loss-cone theory:\n   {ORB['scan']['3.0T']['fractions']['all']['end loss']*100:.1f}% vs {ORB['fraction_in_loss_cone_at_birth']*100:.1f}% end loss",
        "✓ Field scan 1–4 T; target-offset trade",
        "✓ Bench slowing-down + α budget",
        "✓ IBW channel / resonance map",
        "✓ CAD ↔ simulation single source of truth",
    ]
    yy = 38.5
    for it in items:
        ax.text(66, yy, it, fontsize=9.8, color=INK, va="top", linespacing=1.3)
        yy -= 4.3 if "\n" in it else 2.9
    fig.savefig(OUT / "d4_validation.png", dpi=200)
    plt.close(fig)


# --------------------------------------------------------------------------- D5 roadmap
def d5():
    fig, ax = canvas(13.33, 5.6)
    ax.set_ylim(0, 42)
    ax.text(3, 40, "Staged plan: each phase has a falsifiable exit test", fontsize=19, fontweight="bold", color=INK, va="top")
    phases = [
        ("Phase 0 · now", "Model + concept", "PARC-Delta v1.6 (76 tests)\nPDX-1 CAD + device sims\nexit: close TA/Nanbu gap", "green"),
        ("Phase 1", "Magnet + beam-target", "HTS mirror, 0.7 MV beam\nmeasure α birth spectrum\nexit: source model ±10%", "blue"),
        ("Phase 2", "Fast-ion ring + IBW", "surrogate energetic ions\nA1–A4 closed-loop scheduler\nexit: B2 beats B0/B1", "orange"),
        ("Phase 3", "Nonlinear + scale-up", "PIC benchmark (Gate 3)\nirreversible heating (Gate 4)\nexit: go / no-go on scale", "purple"),
    ]
    for k, (h, t, b, tone) in enumerate(phases):
        x = 3 + k * 24.2
        box(ax, x, 4, 22, 29, h, "", tone)
        ax.text(x + 11, 26.5, t, ha="center", fontsize=12, fontweight="bold", color=EDGE[tone])
        ax.text(x + 11, 22.5, b, ha="center", va="top", fontsize=10.2, color=INK, linespacing=1.5)
        if k < 3:
            arrow(ax, (x + 22.3, 18), (x + 24.1, 18), color=INK)
    fig.savefig(OUT / "d5_roadmap.png", dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    d1(); d2(); d3(); d4(); d5()
    print(sorted(p.name for p in OUT.glob("*.png")))
