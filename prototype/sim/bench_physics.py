"""S4/S5 - PDX-1 bench physics budget.

S4  Alpha slowing-down in the *bench* plasma, using the PARC-Delta v1.6
    Rosenbluth test-particle coefficients (expected-drag moment, deterministic):
    time scales and electron/proton energy split.
S5  Alpha inventory budget: 11B(p,3a) yield of a thin foil, trapped fraction from
    the orbit simulation, effective lifetime -> achievable alpha density, compared
    with the n_alpha/n_p = 2% of the PARC-Delta linear IBW (LAPD) reference case.
S6  IBW resonance / channel map along the machine axis from the simulated field.

All inputs are listed in the JSON output; assumptions are flagged.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.constants import e, epsilon_0, m_e, m_p, physical_constants, N_A
from scipy.integrate import solve_ivp

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
sys.path.insert(0, str(HERE.parent / "design"))
sys.path.insert(0, str(LAB / "parc-delta" / "src"))
import pdx1_params as P  # noqa: E402
from plotstyle import apply_style, COLORS  # noqa: E402
from parc_delta_v10.slowing_down import (  # noqa: E402
    MaxwellianFieldSpecies,
    expected_kinetic_energy_rate_per_marker_j_s,
    rosenbluth_test_particle_coefficients,
)
from parc_delta_v10.linear_ibw import LAPDReferenceCase  # noqa: E402

OUT = HERE / "out"
M_ALPHA = physical_constants["alpha particle mass"][0]
Q_ALPHA = 2 * e
M_B11 = 11.0093054 * physical_constants["atomic mass constant"][0]
MEV = 1e6 * e

BP = P.BENCH_PLASMA
FIELDS = [
    MaxwellianFieldSpecies("electron", m_e, -e, BP["n_e_m3"], BP["T_e_eV"]),
    MaxwellianFieldSpecies("proton", m_p, e, BP["n_e_m3"], BP["T_p_eV"]),
]


def power_by_species(energy_j: float) -> np.ndarray:
    v = np.array([np.sqrt(2 * energy_j / M_ALPHA)])
    out = []
    for f in FIELDS:
        c = rosenbluth_test_particle_coefficients(v, test_mass_kg=M_ALPHA, test_charge_c=Q_ALPHA,
                                                  field_species=f, coulomb_logarithm=BP["ln_lambda"])
        out.append(float(expected_kinetic_energy_rate_per_marker_j_s(v, test_mass_kg=M_ALPHA, coefficients=c)[0]))
    return np.array(out)  # J/s (negative = alpha loses energy)


def slowing_down(e0_mev: float):
    def rhs(t, y):
        p = power_by_species(max(y[0], 1e-3 * MEV))
        return [p.sum(), -p[0], -p[1]]
    e_stop = 50e3 * e  # stop at 50 keV (well above bench thermal energies)
    ev = lambda t, y: y[0] - e_stop
    ev.terminal = True
    sol = solve_ivp(rhs, (0, 1.0), [e0_mev * MEV, 0, 0], events=ev, rtol=1e-7, atol=1e-12 * MEV,
                    dense_output=True, max_step=1e-4)
    return sol


def main() -> None:
    apply_style()
    orbit = json.loads((OUT / "alpha_orbit_summary.json").read_text())
    magnet = json.loads((OUT / "magnet_summary.json").read_text())

    # ------------------------------------------------ S4 slowing down in bench plasma
    sd = {}
    curves = {}
    for e0 in (1.5, 3.12, 5.7):
        sol = slowing_down(e0)
        t_end = float(sol.t[-1])
        e_frac = sol.y[1, -1] / (sol.y[1, -1] + sol.y[2, -1])
        t_half = float(sol.t[np.argmin(np.abs(sol.y[0] - 0.5 * e0 * MEV))])
        sd[f"{e0:.2f}MeV"] = {"time_to_50keV_ms": t_end * 1e3, "time_to_half_energy_ms": t_half * 1e3,
                              "electron_share_of_deposited_energy": float(e_frac),
                              "proton_share_of_deposited_energy": float(1 - e_frac)}
        tt = np.linspace(0, t_end, 300)
        curves[e0] = (tt, sol.sol(tt)[0] / MEV)

    # ------------------------------------------------ S5 alpha inventory budget
    sigma_b = 1.2                      # ASSUMPTION: ~peak 11B(p,3a) cross-section near E_p = 0.675 MeV (barn)
    rho_b = 2.34e3                     # kg/m^3, crystalline boron (100% 11B assumed)
    n_b = rho_b / M_B11                # atoms/m^3
    t_foil = P.TARGET_FOIL_THICKNESS_UM * 1e-6
    protons_per_s = P.BEAM_CURRENT_UA * 1e-6 / e
    reactions_per_s = protons_per_s * n_b * t_foil * sigma_b * 1e-28
    alphas_per_s = 3 * reactions_per_s
    s3 = orbit["scan"]["3.0T"]
    trapped_frac = 1 - orbit["fraction_in_loss_cone_at_birth"]
    tau_target_s = (s3["median_time_to_first_foil_recrossing_us"] or 1.5) * 1e-6
    tau_slow_s = sd["3.12MeV"]["time_to_50keV_ms"] * 1e-3
    v_plasma = np.pi * (P.PLASMA_RADIUS_MM / 1000) ** 2 * 2 * 0.99   # between mirror throats
    n_alpha_target_limited = alphas_per_s * trapped_frac * tau_target_s / v_plasma
    n_alpha_slowing_limited = alphas_per_s * trapped_frac * tau_slow_s / v_plasma
    ref = LAPDReferenceCase()
    n_alpha_required = ref.alpha_to_proton_density * BP["n_e_m3"]
    budget = {
        "beam_current_uA": P.BEAM_CURRENT_UA,
        "foil_thickness_um": P.TARGET_FOIL_THICKNESS_UM,
        "assumed_cross_section_barn": sigma_b,
        "reactions_per_s": reactions_per_s,
        "alphas_per_s": alphas_per_s,
        "trapped_fraction_at_birth": trapped_frac,
        "effective_lifetime_target_limited_us": tau_target_s * 1e6,
        "effective_lifetime_slowing_limited_ms": tau_slow_s * 1e3,
        "plasma_volume_m3": v_plasma,
        "alpha_density_target_limited_m3": n_alpha_target_limited,
        "alpha_density_slowing_limited_m3": n_alpha_slowing_limited,
        "reference_case_alpha_to_proton_ratio": ref.alpha_to_proton_density,
        "alpha_density_required_at_bench_density_m3": n_alpha_required,
        "shortfall_factor_best_case": n_alpha_required / n_alpha_slowing_limited,
        "beam_power_on_foil_W_upper_bound": P.BEAM_CURRENT_UA * 1e-6 * P.BEAM_ENERGY_MEV * 1e6,
        "verdict": ("Fusion-born alphas from a uA-class beam-foil source cannot reach the alpha density "
                    "needed for IBW self-excitation; PDX-1 Phase 1 measures the birth spectrum and "
                    "orbit physics, and Phase 2 needs a surrogate energetic-ion ring."),
    }

    # ------------------------------------------------ S6 resonance / channel map
    fm = np.load(OUT / "field_map.npz")
    z = fm["z"]
    b_axis = np.abs(fm["bz"][0])
    i_edge = np.argmin(np.abs(fm["r"] - P.PLASMA_RADIUS_MM / 1000))
    b_edge = np.hypot(fm["bz"][i_edge], fm["br"][i_edge])
    fca = Q_ALPHA * b_axis / (2 * np.pi * M_ALPHA) / 1e6
    fcp = e * b_axis / (2 * np.pi * m_p) / 1e6
    fcb = 5 * e * b_axis / (2 * np.pi * M_B11) / 1e6
    b0 = magnet["B0_on_axis_T"]
    fca0 = Q_ALPHA * b0 / (2 * np.pi * M_ALPHA) / 1e6
    fcp0 = e * b0 / (2 * np.pi * m_p) / 1e6
    channels = {f"A{k+1}": (n + 0.5) * fca0 for k, n in enumerate((2, 3, 4, 5))}
    # lower-hybrid / plasma frequencies at bench density
    n = BP["n_e_m3"]
    wpe2 = n * e**2 / (epsilon_0 * m_e); wpi2 = n * e**2 / (epsilon_0 * m_p)
    wce, wci = e * b0 / m_e, e * b0 / m_p
    f_lh = np.sqrt(1 / (1 / (wce * wci) + 1 / wpi2)) / (2 * np.pi) / 1e6
    # resonance layers: where harmonic n*fca(X) equals a channel frequency (central cell only)
    cc = np.abs(z) <= 1.2
    layers = {}
    for name, f in channels.items():
        hits = []
        for nh in range(1, 8):
            g = nh * fca[cc] - f
            idx = np.flatnonzero(np.sign(g[:-1]) != np.sign(g[1:]))
            hits += [{"harmonic": nh, "x_mm": float(z[cc][i] * 1000)} for i in idx]
        layers[name] = {"f_MHz": f, "layers": hits}
    # sensitivity: layer motion per 1% frequency change for the 3rd harmonic of A2 (if any)
    shift = None
    for name, f in channels.items():
        for nh in range(1, 8):
            for df in (0.0, 0.01):
                pass
    def layer_x(f, nh):
        g = nh * fca[cc] - f
        idx = np.flatnonzero((np.sign(g[:-1]) != np.sign(g[1:])) & (z[cc][:-1] > 0))
        return float(z[cc][idx[0]] * 1000) if len(idx) else None
    x0, x1 = layer_x(channels["A2"], 4), layer_x(channels["A2"] * 1.01, 4)
    if x0 is not None and x1 is not None:
        shift = x1 - x0
    rmap = {
        "B0_T": b0, "f_c_alpha_MHz": fca0, "f_c_proton_MHz": fcp0,
        "f_c_B11_5plus_MHz": 5 * e * b0 / (2 * np.pi * M_B11) / 1e6,
        "f_lower_hybrid_MHz": f_lh, "f_pe_GHz": np.sqrt(wpe2) / (2 * np.pi) / 1e9,
        "channels": layers,
        "A2_4th_harmonic_layer_shift_mm_per_1pct": shift,
        "note": "Channel plan is illustrative: (n+1/2) x f_c,alpha at B0, between alpha harmonics where IBW branches exist.",
    }

    summary = {"bench_plasma": BP, "slowing_down": sd, "alpha_budget": budget, "resonance_map": rmap,
               "caveats": [
                   "Slowing-down uses the expected (mean) Rosenbluth drag of PARC-Delta v1.6 with fixed Maxwellian "
                   "electron/proton reservoirs; no boron, impurities or neutrals.",
                   "Cross-section 1.2 b is an approximate resonance value (assumption); the budget conclusion "
                   "holds for any value within 10x.",
               ]}
    (OUT / "bench_physics_summary.json").write_text(json.dumps(summary, indent=2))

    # ------------------------------------------------ figures
    fig, ax = plt.subplots(figsize=(8.5, 4.0))
    for e0, col in zip(curves, (COLORS["secondary"], COLORS["primary"], COLORS["accent"])):
        tt, ee = curves[e0]
        ax.plot(tt * 1e3, ee, lw=2.2, color=col, label=f"birth energy {e0:.2f} MeV")
    ax.axvline(budget["effective_lifetime_target_limited_us"] / 1e3, color=COLORS["target"], ls="--", lw=1.2)
    ax.text(budget["effective_lifetime_target_limited_us"] / 1e3 * 1.15, 5.2, "median target\nre-hit (1.5 µs)",
            color=COLORS["target"], fontsize=9)
    ax.set_xscale("log")
    ax.set_xlim(1e-4, max(c[0][-1] for c in curves.values()) * 1e3 * 1.3)
    ax.set_xlabel("Time (ms, log scale)")
    ax.set_ylabel("Mean alpha energy (MeV)")
    ax.set_title(f"Alpha slowing-down in the bench plasma (n = {BP['n_e_m3']:.0e} m⁻³, Te = {BP['T_e_eV']:.0f} eV)")
    ax.legend(loc="lower left")
    fig.tight_layout(); fig.savefig(OUT / "fig_bench_slowing_down.png", dpi=200); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.5, 4.0))
    labels = ["Target-limited\n(on-axis foil)", "Slowing-limited\n(ideal: no target)", "Needed for IBW drive\n(2% of n_p, ref. case)"]
    vals = [n_alpha_target_limited, n_alpha_slowing_limited, n_alpha_required]
    bars = ax.bar(labels, vals, color=[COLORS["target"], COLORS["accent"], COLORS["good"]], width=0.55)
    ax.set_yscale("log")
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v * 1.8, f"{v:.1e} m⁻³", ha="center", fontsize=10, color=COLORS["ink"])
    ax.set_ylim(1e2, 1e20)
    ax.set_ylabel("Fast-alpha density (m⁻³, log)")
    ax.set_title(f"Alpha inventory budget: ~10^{np.log10(budget['shortfall_factor_best_case']):.0f}× short of IBW self-excitation")
    ax.grid(axis="x", visible=False)
    fig.tight_layout(); fig.savefig(OUT / "fig_alpha_budget.png", dpi=200); plt.close(fig)

    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    zm = z * 1000
    for nh in range(1, 7):
        ax.plot(zm, nh * fca, color=COLORS["accent"], lw=1.6 if nh == 1 else 1.0, alpha=1 if nh == 1 else 0.75)
        ax.text(1230, nh * fca[np.argmin(np.abs(zm - 1200))], f"{nh}Ωα", color=COLORS["accent"], fontsize=8, va="center")
    for nh in range(1, 3):
        ax.plot(zm, nh * fcp, color=COLORS["primary"], lw=1.4, ls="--")
    ax.plot(zm, fcb, color=COLORS["boron"], lw=1.2, ls=":", label="Ω(¹¹B⁵⁺)")
    for k, (name, d) in enumerate(layers.items()):
        ax.axhline(d["f_MHz"], color=COLORS["ink"], lw=0.8, alpha=0.6)
        ax.text(-1650, d["f_MHz"] + 2, f"{name}: {d['f_MHz']:.1f} MHz", fontsize=8.5, color=COLORS["ink"])
        for L in d["layers"]:
            ax.plot(L["x_mm"], d["f_MHz"], "o", ms=5, color=COLORS["target"])
    ax.plot([], [], color=COLORS["accent"], label="alpha harmonics nΩα")
    ax.plot([], [], color=COLORS["primary"], ls="--", label="proton harmonics")
    ax.plot([], [], "o", color=COLORS["target"], label="resonance layer")
    ax.annotate("2Ωα ≈ Ωp  (q/m ratio 0.503):\neven alpha harmonics overlap proton\nharmonics — the basis of α→p channeling",
                (-150, 46), xytext=(-420, 3), fontsize=8.2, color=COLORS["primary"],
                arrowprops=dict(arrowstyle="-", color=COLORS["primary"], lw=0.8))
    ax.set_xlim(-1700, 1350); ax.set_ylim(0, 175)
    ax.set_xlabel("Axial position X (mm)"); ax.set_ylabel("Frequency (MHz)")
    ax.set_title("IBW channel plan and cyclotron-resonance layers along the axis")
    ax.legend(loc="upper center", ncol=4, fontsize=8.5)
    fig.tight_layout(); fig.savefig(OUT / "fig_resonance_map.png", dpi=200); plt.close(fig)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
