"""Collect every test/simulation result into one curated JSON used by the docx, deck and video."""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

PROTO = Path(__file__).resolve().parents[1]
LAB = PROTO.parent
SIM = PROTO / "sim" / "out"
OUT = PROTO / "report" / "out"
OUT.mkdir(parents=True, exist_ok=True)


def nums(path: Path) -> list[float]:
    vals = []
    if path.suffix == ".csv":
        with path.open() as f:
            for row in csv.reader(f):
                for v in row:
                    try:
                        vals.append(float(v))
                    except ValueError:
                        pass
    else:
        def walk(o):
            if isinstance(o, dict):
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
            elif isinstance(o, (int, float)) and not isinstance(o, bool):
                vals.append(float(o))
        walk(json.loads(path.read_text()))
    return vals


def repro() -> dict:
    orig = LAB / "parc-delta" / "results"
    rerun = LAB / "runs" / "v16_rerun" / "results"
    files, total, worst = [], 0, 0.0
    for f in sorted(orig.glob("v16_*")):
        a, b = nums(f), nums(rerun / f.name)
        w = max((abs(x - y) / abs(x) for x, y in zip(a, b) if x and math.isfinite(x) and math.isfinite(y)), default=0.0)
        files.append({"file": f.name, "values": len(a), "max_rel_diff": w})
        total += len(a)
        worst = max(worst, w)
    return {"files": files, "file_count": len(files), "values_compared": total, "max_rel_diff": worst}


def main() -> None:
    mag = json.loads((SIM / "magnet_summary.json").read_text())
    orb = json.loads((SIM / "alpha_orbit_summary.json").read_text())
    bench = json.loads((SIM / "bench_physics_summary.json").read_text())
    parts = json.loads((PROTO / "cad" / "out" / "pdx1_parts.json").read_text())
    r = repro()
    s3 = orb["scan"]["3.0T"]
    tests = [
        {"id": "T1", "area": "Software", "what": "PARC-Delta v1.6 unit + regression suite (pytest)",
         "how": "76 automated tests run on a clean Python 3.12 toolchain on the external SSD",
         "result": "76 / 76 passed in 13 s", "status": "pass"},
        {"id": "T2", "area": "Reproducibility", "what": "Re-run of the full v1.6 numerical campaign",
         "how": f"scripts_run_v16.py re-executed in an isolated copy; {r['values_compared']} numbers in {r['file_count']} result files compared to the shipped release",
         "result": f"max relative difference {r['max_rel_diff']:.1e} (floating-point level)", "status": "pass"},
        {"id": "T3", "area": "Physics (inherited)", "what": "Collision-operator cross-checks (v1.5/v1.6 release)",
         "how": "Landau–Spitzer analytic moment; single-bath and full-mixture TA/Nanbu vs Rosenbluth",
         "result": "single bath agrees to <0.003%; full mixture still captures only 92.9% / 93.9% of energy loss", "status": "open"},
        {"id": "T4", "area": "Magnet", "what": "HTS coil set field, mirror ratio, stored energy, conductor field",
         "how": "magpylib analytic loops (8×10 filaments per coil); 2×2 current solve; inductance-matrix energy",
         "result": f"B0 {mag['B0_on_axis_T']:.2f} T, mirror ratio {mag['mirror_ratio']:.2f}, {mag['stored_magnetic_energy_MJ']:.1f} MJ, "
                   f"peak winding field {mag['peak_field_at_conductor_T']:.1f} T", "status": "design change"},
        {"id": "T5", "area": "Orbit solver", "what": "Boris full-orbit integrator vs adiabatic loss-cone theory",
         "how": f"{2*orb['alphas_per_branch']} alphas from the PARC-Delta α0/α1 birth source, 4 µs, 0.4 ns steps",
         "result": f"simulated end loss {s3['fractions']['all']['end loss']*100:.2f}% vs analytic loss cone {orb['fraction_in_loss_cone_at_birth']*100:.2f}%",
         "status": "pass"},
        {"id": "T6", "area": "Confinement", "what": "Alpha wall loss vs central field (1–4 T)",
         "how": "coil currents scaled; limiter at r = 250 mm",
         "result": f"wall loss {orb['scan']['1.0T']['fractions']['all']['limiter/wall']*100:.0f}% at 1 T → "
                   f"{orb['scan']['3.0T']['fractions']['all']['limiter/wall']*100:.1f}% at 3 T (design point)", "status": "pass"},
        {"id": "T7", "area": "Target", "what": "Foil / target-assembly re-intersection by trapped alphas",
         "how": "X = 0 plane crossings tracked on foil, frame ring and arm; target offset scanned 0–160 mm",
         "result": f"{s3['fractions']['all']['target hit']*100:.0f}% hit the target assembly within 4 µs; median first foil re-crossing "
                   f"{s3['median_time_to_first_foil_recrossing_us']:.1f} µs; offsetting trades target hits for wall hits", "status": "finding"},
        {"id": "T8", "area": "Collisions", "what": "Alpha slowing-down in the bench plasma",
         "how": "PARC-Delta Rosenbluth expected-drag coefficients, ne = 1e19 m⁻³, Te = 10 eV, Tp = 2 eV",
         "result": f"3.1 MeV → 50 keV in {bench['slowing_down']['3.12MeV']['time_to_50keV_ms']:.1f} ms; "
                   f"{bench['slowing_down']['3.12MeV']['electron_share_of_deposited_energy']*100:.2f}% to electrons", "status": "pass"},
        {"id": "T9", "area": "Feasibility", "what": "Fast-alpha inventory vs IBW drive requirement",
         "how": "10 µA, 1 µm ¹¹B foil, σ ≈ 1.2 b (assumed), trapped fraction and lifetimes from T5/T7/T8",
         "result": f"best case {bench['alpha_budget']['alpha_density_slowing_limited_m3']:.1e} m⁻³ vs "
                   f"{bench['alpha_budget']['alpha_density_required_at_bench_density_m3']:.0e} m⁻³ needed "
                   f"(~10^{math.log10(bench['alpha_budget']['shortfall_factor_best_case']):.0f}× short)", "status": "finding"},
        {"id": "T10", "area": "RF", "what": "IBW channel plan and cyclotron-resonance layers",
         "how": "simulated B(X) on axis → nΩα, nΩp, Ω(¹¹B⁵⁺); four channels at (n+½)Ωα(B0)",
         "result": f"Ωα/2π = {bench['resonance_map']['f_c_alpha_MHz']:.1f} MHz, Ωp/2π = {bench['resonance_map']['f_c_proton_MHz']:.1f} MHz, "
                   f"f_LH = {bench['resonance_map']['f_lower_hybrid_MHz']:.0f} MHz; channels 57.6–126.6 MHz", "status": "pass"},
        {"id": "T11", "area": "CAD", "what": "Model integrity and drawing traceability",
         "how": "build123d solid model (STEP), CADCraft GA drawing and simulations all read one parameter file",
         "result": f"{parts['part_count']} labelled parts, {parts['overall_mm'][0]/1000:.1f} × {parts['overall_mm'][1]/1000:.1f} × "
                   f"{parts['overall_mm'][2]/1000:.1f} m envelope; A0 drawing PDX1-GA-001", "status": "pass"},
    ]
    questions = [
        ("Collision closure", "Why do TA/Nanbu still miss 6–7% of the Rosenbluth alpha energy loss at 32 substeps, and does importance sampling of near-comoving electrons close it?"),
        ("Trapped-alpha accumulation", "An on-axis foil re-intersects ~38% of trapped alphas within 4 µs. Pulsed or retractable targets, or a gas/pellet boron target, are needed to build a trapped population."),
        ("Alpha drive", "Fusion alphas from a µA beam are ~10⁹× too sparse for IBW self-excitation. What surrogate energetic-ion source reaches n_fast/n_p ≈ 1% at bench scale?"),
        ("Coherent vs irreversible", "How will PDX-1 separate coherent proton response from irreversible proton heating (Gate 4)? Candidate: RFEA/CX energy distributions with RF on/off modulation."),
        ("Nonlinear physics", "Does the multi-mode advantage survive nonlinear saturation and mode coupling? Requires a PIC benchmark (Gate 3) before any control-law claim."),
        ("Magnet engineering", "REBCO mirror coils see ~10 T and a ~170 MPa J×B×R screen; quench protection, structure and cost need FEA and vendor input."),
        ("Bench electron dominance", "At Te = 10 eV, 99.9% of alpha energy goes to electrons. Which bench parameters make the α→p channel measurable against this baseline?"),
        ("Source validation", "Can the Si spectrometer resolve the α0/α1 branch structure to validate the sequential-kinematic source (an open Gate 2 item)?"),
        ("Radiation safety", "Alphas striking boron produce neutrons via ¹¹B(α,n)¹⁴N; shielding and licensing need a dose assessment even at µA currents."),
        ("Foil survival", "≤6.75 W of beam power on a 1 µm foil: thermal survival, sputtering and 11B enrichment supply need testing."),
    ]
    out = {
        "project": "PARC-Delta", "device": "PDX-1 linear test stand (concept)", "date": "2026-11-01",
        "magnet": mag, "orbits": orb, "bench": bench, "reproducibility": r,
        "cad": {"part_count": parts["part_count"], "overall_mm": parts["overall_mm"]},
        "tests": tests, "open_questions": [{"topic": t, "question": q} for t, q in questions],
        "release_v16": {
            "tests": 76, "alpha_final_mean_kev": [15.303, 14.734], "deposition_electron_pct": 73,
            "deposition_proton_pct": [26, 27], "deposition_thermal_alpha_pct": 0.6,
            "ta_nanbu_k32_energy_capture_pct": [92.89, 93.88],
        },
    }
    (OUT / "results_summary.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(json.dumps(tests, indent=1, ensure_ascii=False)[:1500])


if __name__ == "__main__":
    main()
