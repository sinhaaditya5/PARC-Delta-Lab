"""S2 - PDX-1 superconducting coil set: currents, field map, mirror ratio, stored energy.

Uses magpylib (analytic current-loop fields). Each winding pack is discretised into
filament loops. Coil currents are solved (linear superposition) to hit the design
targets B(0) = B0_TARGET_T and B(mirror throat) = MIRROR_RATIO_TARGET * B0.

Outputs (prototype/sim/out/):
  field_map.npz          Br, Bz on an (r, z) grid for the orbit solver
  magnet_summary.json    currents, current densities, B0, mirror ratio, stored energy
  fig_magnet_axis.png    B on axis + coil layout
  fig_magnet_map.png     |B| map with field lines and vessel / limiter outline
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import magpylib as magpy
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "design"))
import pdx1_params as P  # noqa: E402
from plotstyle import COLORS, apply_style  # noqa: E402

OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
MU0 = 4e-7 * np.pi
NR_FIL, NZ_FIL = 8, 10


def coil_collection(coil: P.Coil, amp_turns: float) -> magpy.Collection:
    """Winding pack -> NR_FIL x NZ_FIL filament loops; axis along z (== CAD X)."""
    rs, zs = filament_rz(coil)
    i_fil = amp_turns / (NR_FIL * NZ_FIL)
    loops = [magpy.current.Circle(current=i_fil, diameter=2 * r, position=(0, 0, z))
             for r in rs for z in zs]
    return magpy.Collection(*loops)


def filament_rz(coil: P.Coil) -> tuple[np.ndarray, np.ndarray]:
    """Cell-centred filament positions (m) of a uniformly discretised winding pack."""
    dr, dz = (coil.r_out - coil.r_in) / NR_FIL, coil.width / NZ_FIL
    rs = (coil.r_in + dr * (np.arange(NR_FIL) + 0.5)) / 1000.0
    zs = (coil.x - coil.width / 2 + dz * (np.arange(NZ_FIL) + 0.5)) / 1000.0
    return rs, zs


def stored_energy_j(amp_turns: dict[str, float]) -> float:
    """E = 1/2 I^T M I over all filaments (Maxwell coaxial-loop mutual inductance,
    rectangular-cell self inductance via geometric-mean distance). Avoids the
    line-current singularity of a field-energy integral."""
    from scipy.special import ellipe, ellipk
    R, Zc, I, G = [], [], [], []
    for c in P.COILS:
        rs, zs = filament_rz(c)
        dr, dz = (c.r_out - c.r_in) / NR_FIL / 1000, c.width / NZ_FIL / 1000
        for r in rs:
            for z in zs:
                R.append(r); Zc.append(z); I.append(amp_turns[c.group] / (NR_FIL * NZ_FIL))
                G.append(0.2235 * (dr + dz))
    R, Zc, I, G = map(np.asarray, (R, Zc, I, G))
    R1, R2 = R[:, None], R[None, :]
    d = Zc[:, None] - Zc[None, :]
    m = 4 * R1 * R2 / ((R1 + R2) ** 2 + d**2)
    np.fill_diagonal(m, 0.5)  # placeholder, overwritten below
    k = np.sqrt(m)
    M = MU0 * np.sqrt(R1 * R2) * ((2 / k - k) * ellipk(m) - (2 / k) * ellipe(m))
    np.fill_diagonal(M, MU0 * R * (np.log(8 * R / G) - 2.0))
    return float(0.5 * I @ M @ I)


def field_rz(sources, r: np.ndarray, z: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    pts = np.column_stack([r.ravel(), np.zeros(r.size), z.ravel()])
    if isinstance(sources, (list, tuple)):
        sources = magpy.Collection(*sources, override_parent=True)
    b = np.asarray(magpy.getB(sources, pts)).reshape(-1, 3)
    return b[:, 0].reshape(r.shape), b[:, 2].reshape(r.shape)


def solve_currents() -> dict[str, float]:
    """Unit amp-turn responses -> 2x2 linear solve for main / mirror group currents."""
    z_probe = np.array([0.0, max(c.x for c in P.MIRROR_COILS) / 1000.0])
    resp = {}
    for group in ("main", "mirror"):
        src = [coil_collection(c, 1.0) for c in P.COILS if c.group == group]
        _, bz = field_rz(src, np.zeros(2), z_probe)
        resp[group] = bz
    a = np.column_stack([resp["main"], resp["mirror"]])
    target = np.array([P.B0_TARGET_T, P.B0_TARGET_T * P.MIRROR_RATIO_TARGET])
    nI_main, nI_mirror = np.linalg.solve(a, target)
    return {"main": float(nI_main), "mirror": float(nI_mirror)}


def build_sources(amp_turns: dict[str, float], scale: float = 1.0):
    return [coil_collection(c, scale * amp_turns[c.group]) for c in P.COILS]


def main() -> None:
    apply_style()
    nI = solve_currents()
    sources = build_sources(nI)

    # ---- on-axis profile
    z_axis = np.linspace(-1.9, 1.9, 761)
    _, bz_axis = field_rz(sources, np.zeros_like(z_axis), z_axis)
    b0 = float(np.interp(0.0, z_axis, bz_axis))
    b_max = float(bz_axis.max())
    z_max = float(abs(z_axis[np.argmax(bz_axis)]))

    # ---- (r, z) map for orbit solver (fine) and plotting
    r_grid = np.linspace(0.0, 0.36, 73)
    z_grid = np.linspace(-1.70, 1.70, 681)
    R, Z = np.meshgrid(r_grid, z_grid, indexing="ij")
    br, bz = field_rz(sources, R, Z)
    np.savez_compressed(OUT / "field_map.npz", r=r_grid, z=z_grid, br=br, bz=bz,
                        amp_turns_main=nI["main"], amp_turns_mirror=nI["mirror"])

    # ---- stored energy from the filament inductance matrix
    stored_j = stored_energy_j(nI)

    # ---- conductor field on winding-pack surfaces (filament ripple ~exp(-pi) there)
    peak_cond = 0.0
    surf_b = {}
    for c in P.COILS:
        n = 25
        zr = np.linspace(c.x - c.width / 2, c.x + c.width / 2, n) / 1000
        rr = np.linspace(c.r_in, c.r_out, n) / 1000
        rs_ = np.concatenate([np.full(n, c.r_in / 1000), np.full(n, c.r_out / 1000), rr, rr])
        zs_ = np.concatenate([zr, zr, np.full(n, (c.x - c.width / 2) / 1000), np.full(n, (c.x + c.width / 2) / 1000)])
        b1, b2 = field_rz(sources, rs_, zs_)
        bm = np.sqrt(b1**2 + b2**2)
        peak_cond = max(peak_cond, float(bm.max()))
        _, bzi = field_rz(sources, np.array([c.r_in / 1000]), np.array([c.x / 1000]))
        _, bzo = field_rz(sources, np.array([c.r_out / 1000]), np.array([c.x / 1000]))
        surf_b[c.name] = (float(bzi[0]), float(bzo[0]), float(bm.max()))

    # ---- hoop-stress screen: sigma ~ J * <Bz>_winding * R_mid (no structural credit)
    hoop = {}
    for c in (P.MAIN_COILS[2], P.MIRROR_COILS[1]):
        j = nI[c.group] / (c.area_mm2 * 1e-6)
        r_mid = 0.5 * (c.r_in + c.r_out) / 1000
        b_avg = 0.5 * (surf_b[c.name][0] + surf_b[c.name][1])
        hoop[c.name] = float(abs(j * b_avg * r_mid) / 1e6)

    summary = {
        "design": "PDX-1 concept coil set (2 mirror + 6 main REBCO HTS coils, conduction-cooled at 20 K)",
        "amp_turns_per_main_coil": nI["main"],
        "amp_turns_per_mirror_coil": nI["mirror"],
        "engineering_current_density_main_A_mm2": nI["main"] / P.MAIN_COILS[0].area_mm2,
        "engineering_current_density_mirror_A_mm2": nI["mirror"] / P.MIRROR_COILS[0].area_mm2,
        "B0_on_axis_T": b0,
        "B_max_on_axis_T": b_max,
        "mirror_throat_position_m": z_max,
        "mirror_ratio": b_max / b0,
        "peak_field_at_conductor_T": peak_cond,
        "stored_magnetic_energy_MJ": stored_j / 1e6,
        "hoop_stress_estimate_MPa": hoop,
        "winding_surface_field_T": {k: {"Bz_inner": v[0], "Bz_outer": v[1], "Bmax_surface": v[2]} for k, v in surf_b.items()},
        "method": "magpylib analytic loops, %dx%d filaments per winding pack" % (NR_FIL, NZ_FIL),
        "caveats": [
            "Hoop stress is a J*B*R screening estimate without structural credit; needs FEA.",
            "Field map ignores iron, leads, joints and coil-case eddy currents.",
            "Design iteration: the first pass assumed NbTi at 4.2 K; the ~10 T mirror-coil winding field "
            "exceeds practical NbTi margins, so the baseline was changed to REBCO HTS at 20 K.",
        ],
    }
    (OUT / "magnet_summary.json").write_text(json.dumps(summary, indent=2))

    # ---- figure 1: axis profile with coil footprint
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.plot(z_axis * 1000, bz_axis, color=COLORS["primary"], lw=2.2, label="|B| on axis")
    ax.axhline(b0, color=COLORS["muted"], lw=1, ls="--")
    ax.annotate(f"B0 = {b0:.2f} T (central cell)", (0, b0), xytext=(60, b0 - 0.5), color=COLORS["ink"], fontsize=9.5)
    ax.annotate(f"mirror throat {b_max:.2f} T\nmirror ratio R = {b_max / b0:.2f}", (z_max * 1000, b_max),
                xytext=(z_max * 1000 + 160, b_max + 0.05), color=COLORS["ink"], fontsize=9.5,
                arrowprops=dict(arrowstyle="-", color=COLORS["muted"]))
    for c in P.COILS:
        ax.axvspan(c.x - c.width / 2, c.x + c.width / 2, ymin=0, ymax=0.06,
                   color=COLORS["accent"] if c.group == "mirror" else COLORS["secondary"], alpha=0.9)
    ax.axvline(0, color=COLORS["target"], lw=1, ls=":")
    ax.text(25, 0.55, "11B foil", color=COLORS["target"], fontsize=9)
    ax.text(-1880, 0.48, "orange = mirror coils, slate = main coils", color=COLORS["muted"], fontsize=8.5)
    ax.set_xlabel("Axial position X (mm)")
    ax.set_ylabel("Magnetic field (T)")
    ax.set_title("PDX-1 on-axis magnetic field (simulated)")
    ax.set_ylim(0, b_max * 1.18)
    ax.set_xlim(-1900, 1900)
    fig.tight_layout()
    fig.savefig(OUT / "fig_magnet_axis.png", dpi=200)
    plt.close(fig)

    # ---- figure 2: |B| map + flux surfaces (psi = r A_theta, from integrating r*Bz)
    bmag = np.sqrt(br**2 + bz**2)
    psi = np.zeros_like(bz)
    for j in range(len(z_grid)):
        psi[:, j] = np.concatenate([[0], np.cumsum(0.5 * (R[1:, j] * bz[1:, j] + R[:-1, j] * bz[:-1, j]) * np.diff(r_grid))])
    fig, ax = plt.subplots(figsize=(10, 3.6))
    ax.grid(False)
    zz_mm, rr_mm = Z * 1000, R * 1000
    for sgn in (1, -1):
        cf = ax.contourf(zz_mm, sgn * rr_mm, bmag, levels=np.linspace(0, bmag.max(), 25), cmap="viridis")
        ax.contour(zz_mm, sgn * rr_mm, psi, levels=12, colors="white", linewidths=0.6, alpha=0.8)
    cb = fig.colorbar(cf, ax=ax, pad=0.01)
    cb.set_label("|B| (T)")
    for sgn in (1, -1):
        ax.plot([P.VESSEL_X0, P.VESSEL_X1], [sgn * P.VESSEL_R_IN] * 2, color="white", lw=1.6)
        ax.plot([P.VESSEL_X0, P.VESSEL_X1], [sgn * P.LIMITER_R] * 2, color=COLORS["accent"], lw=1, ls="--")
    ax.text(-880, 262, "limiter r = 250 mm", color=COLORS["accent"], fontsize=8)
    ax.text(-880, 312, "vessel wall r = 300 mm", color="white", fontsize=8)
    ax.set_xlabel("Axial position X (mm)")
    ax.set_ylabel("r (mm)")
    ax.set_title("|B| and flux surfaces in the central cell (simulated)")
    fig.tight_layout()
    fig.savefig(OUT / "fig_magnet_map.png", dpi=200)
    plt.close(fig)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
