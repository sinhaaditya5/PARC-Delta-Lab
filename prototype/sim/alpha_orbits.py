"""S3 - Full-orbit alpha confinement in the PDX-1 magnetic field.

Alpha birth states come straight from the PARC-Delta v1.4 sequential-kinematic
source (``sample_pb11_alpha_birth``, beam_lab frame, 0.675 MeV protons on 11B),
separately for the alpha0 and alpha1 branches (no branching ratio assumed).
Birth positions: Gaussian beam spot on the foil at X = 0.

Each alpha is pushed with a Boris integrator through the magpylib field map
(``field_map.npz``) for 4 us and classified as:
  confined       still inside the central cell at the end
  end loss       crossed |X| > 1.2 m (left through a mirror throat)
  limiter/wall   reached r >= 250 mm
  target hit     re-crossed the X = 0 plane on the foil frame ring or the insertion arm
Re-crossings of the 25 mm foil itself are counted (energy loss in the foil is
*not* modelled here; see caveats).

Scope: collisionless, no plasma electric fields, no foil energy loss, no
collisions. A geometric/orbit screen, not a transport calculation.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.constants import e, physical_constants

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
sys.path.insert(0, str(HERE.parent / "design"))
sys.path.insert(0, str(LAB / "parc-delta" / "src"))
import pdx1_params as P  # noqa: E402
from parc_delta_v10.pb11_alpha_source import (  # noqa: E402
    e_cm_from_proton_lab_energy,
    sample_pb11_alpha_birth,
)
from plotstyle import COLORS, apply_style  # noqa: E402

OUT = HERE / "out"
M_ALPHA = physical_constants["alpha particle mass"][0]
Q_ALPHA = 2 * e
QM = Q_ALPHA / M_ALPHA

FIELD = np.load(OUT / "field_map.npz")
RG, ZG, BR0, BZ0 = FIELD["r"], FIELD["z"], FIELD["br"], FIELD["bz"]
DR, DZ = RG[1] - RG[0], ZG[1] - ZG[0]

R_LIM = P.LIMITER_R / 1000
Z_END = P.VESSEL_X1 / 1000
FOIL_R = P.TARGET_FOIL_R / 1000
FRAME_R = P.TARGET_FRAME_R[1] / 1000
ARM_HALF = 0.008
FATES = ["confined", "end loss", "limiter/wall", "target hit"]


def bfield(x, y, z, scale):
    """Bilinear (r, z) interpolation of the axisymmetric map -> Cartesian B."""
    r = np.sqrt(x * x + y * y)
    fr = np.clip(r / DR, 0, len(RG) - 1.001)
    fz = np.clip((z - ZG[0]) / DZ, 0, len(ZG) - 1.001)
    i, j = fr.astype(int), fz.astype(int)
    tr, tz = fr - i, fz - j
    def interp(a):
        return ((1 - tr) * (1 - tz) * a[i, j] + tr * (1 - tz) * a[i + 1, j]
                + (1 - tr) * tz * a[i, j + 1] + tr * tz * a[i + 1, j + 1])
    br, bz = interp(BR0) * scale, interp(BZ0) * scale
    rs = np.where(r > 1e-12, r, 1.0)
    return br * x / rs, br * y / rs, bz


def birth_population(channel: str, events: int, seed: int):
    src = sample_pb11_alpha_birth(events, channel=channel,
                                  e_cm_mev=e_cm_from_proton_lab_energy(P.BEAM_ENERGY_MEV),
                                  seed=seed, frame="beam_lab")
    v = src.velocity_m_s.copy()
    v[:, 2] *= -1.0                       # PDX-1 beam travels toward -X (sim -z)
    n = v.shape[0]
    rng = np.random.default_rng(seed + 1000)
    pos = np.zeros((n, 3))
    sig = P.BEAM_SIGMA_MM / 1000
    k = 0
    while k < n:                           # truncated Gaussian spot inside the foil
        cand = rng.normal(0, sig, size=(2 * n, 2))
        cand = cand[np.hypot(cand[:, 0], cand[:, 1]) < FOIL_R * 0.98]
        take = min(n - k, len(cand))
        pos[k:k + take, :2] = cand[:take]
        k += take
    return pos, v, src.kinetic_energy_mev.copy()


def push(pos, vel, scale, t_end=4.0e-6, dt=4.0e-10, keep_traj=None, traj_every=4, cx=0.0):
    n = pos.shape[0]
    x, y, z = pos[:, 0].copy(), pos[:, 1].copy(), pos[:, 2].copy()
    vx, vy, vz = vel[:, 0].copy(), vel[:, 1].copy(), vel[:, 2].copy()
    fate = np.zeros(n, dtype=int)                  # 0 alive
    t_fate = np.full(n, np.nan)
    foil_cross = np.zeros(n, dtype=int)
    t_first_foil = np.full(n, np.nan)
    steps = int(round(t_end / dt))
    alive_hist = np.zeros((steps // 50 + 1, 5))
    traj = [] if keep_traj is not None else None
    h = 0.5 * QM * dt
    for s in range(steps):
        a = fate == 0
        if not a.any():
            break
        bx, by, bz = bfield(x[a], y[a], z[a], scale)
        tx, ty, tz = h * bx, h * by, h * bz
        t2 = tx * tx + ty * ty + tz * tz
        sx, sy, sz = 2 * tx / (1 + t2), 2 * ty / (1 + t2), 2 * tz / (1 + t2)
        ux, uy, uz = vx[a], vy[a], vz[a]
        px = ux + (uy * tz - uz * ty); py = uy + (uz * tx - ux * tz); pz = uz + (ux * ty - uy * tx)
        ux = ux + (py * sz - pz * sy); uy = uy + (pz * sx - px * sz); uz = uz + (px * sy - py * sx)
        vx[a], vy[a], vz[a] = ux, uy, uz
        z_old = z[a].copy()
        x[a] += ux * dt; y[a] += uy * dt; z[a] += uz * dt
        t = (s + 1) * dt
        idx = np.flatnonzero(a)
        # X = 0 plane re-crossing (skip the first few steps after birth)
        if s > 5:
            crossed = np.sign(z_old) != np.sign(z[idx])
            if crossed.any():
                ci = idx[crossed]
                rc = np.hypot(x[ci] - cx, y[ci])
                on_foil = rc < FOIL_R
                foil_cross[ci[on_foil]] += 1
                first = ci[on_foil & np.isnan(t_first_foil[ci])]
                t_first_foil[first] = t
                hit = ((rc >= FOIL_R) & (rc < FRAME_R)) | ((np.abs(x[ci] - cx) < ARM_HALF) & (y[ci] > FRAME_R))
                fate[ci[hit]] = 3; t_fate[ci[hit]] = t
        r = np.hypot(x[idx], y[idx])
        wall = (r >= R_LIM) & (fate[idx] == 0)
        fate[idx[wall]] = 2; t_fate[idx[wall]] = t
        end = (np.abs(z[idx]) > Z_END) & (fate[idx] == 0)
        fate[idx[end]] = 1; t_fate[idx[end]] = t
        if s % 50 == 0:
            alive_hist[s // 50] = [t, *(np.mean(fate == k) for k in range(4))]
        if traj is not None and s % traj_every == 0:
            traj.append(np.column_stack([x[keep_traj], y[keep_traj], z[keep_traj], fate[keep_traj]]))
    return dict(fate=fate, t_fate=t_fate, foil_cross=foil_cross, t_first_foil=t_first_foil,
                alive_hist=alive_hist[: s // 50 + 1], traj=None if traj is None else np.array(traj))


def main() -> None:
    apply_style()
    t0 = time.time()
    pops = {ch: birth_population(ch, 700, seed) for ch, seed in (("alpha0", 7101), ("alpha1", 7102))}
    pos = np.vstack([pops["alpha0"][0], pops["alpha1"][0]])
    vel = np.vstack([pops["alpha0"][1], pops["alpha1"][1]])
    ekin = np.concatenate([pops["alpha0"][2], pops["alpha1"][2]])
    branch = np.array(["alpha0"] * len(pops["alpha0"][2]) + ["alpha1"] * len(pops["alpha1"][2]))
    speed = np.linalg.norm(vel, axis=1)
    pitch = vel[:, 2] / speed

    b0_scan = [1.0, 2.0, 3.0, 4.0]
    scan = {}
    base = None
    rng = np.random.default_rng(3)
    for b0 in b0_scan:
        scale = b0 / P.B0_TARGET_T
        keep = None
        if b0 == P.B0_TARGET_T:
            keep = rng.choice(len(ekin), 40, replace=False)
        res = push(pos, vel, scale, keep_traj=keep)
        res["keep"] = keep
        frac = {}
        for br in ("alpha0", "alpha1", "all"):
            m = np.ones(len(ekin), bool) if br == "all" else branch == br
            frac[br] = {FATES[k]: float(np.mean(res["fate"][m] == k)) for k in range(4)}
        recross = res["foil_cross"] > 0
        scan[b0] = {
            "fractions": frac,
            "fraction_with_foil_recrossing": float(np.mean(recross)),
            "median_time_to_first_foil_recrossing_us": float(np.nanmedian(res["t_first_foil"]) * 1e6) if recross.any() else None,
            "mean_foil_recrossings_per_alpha": float(np.mean(res["foil_cross"])),
        }
        if b0 == P.B0_TARGET_T:
            base = res
        print(f"B0={b0:.1f} T  {frac['all']}  recross={scan[b0]['fraction_with_foil_recrossing']:.3f}  ({time.time()-t0:.0f}s)")

    # target radial-offset scan at the design field (beam steered onto an off-axis flux tube)
    offset_scan = {}
    for off_mm in (0.0, 40.0, 80.0, 120.0, 160.0):
        p_off = pos.copy(); p_off[:, 0] += off_mm / 1000
        r_ = push(p_off, vel, 1.0, cx=off_mm / 1000)
        offset_scan[off_mm] = {FATES[k]: float(np.mean(r_["fate"] == k)) for k in range(4)}
        print("offset", off_mm, offset_scan[off_mm])

    # analytic loss-cone check at the birth point
    fm = np.load(OUT / "field_map.npz")
    bz_axis = fm["bz"][0]
    rm = float(bz_axis.max() / np.interp(0, fm["z"], bz_axis))
    cos_lc = float(np.sqrt(1 - 1 / rm))
    summary = {
        "source": "PARC-Delta v1.4 sample_pb11_alpha_birth, beam_lab frame, E_p = 0.675 MeV, alpha0 + alpha1 unweighted",
        "alphas_per_branch": int(np.sum(branch == "alpha0")),
        "integrator": "Boris, dt = 0.4 ns, 4 us, bilinear (r,z) field interpolation",
        "mirror_ratio_on_axis": rm,
        "loss_cone_abs_pitch_cosine": cos_lc,
        "fraction_in_loss_cone_at_birth": float(np.mean(np.abs(pitch) > cos_lc)),
        "birth_energy_mev": {"mean": float(ekin.mean()), "min": float(ekin.min()), "max": float(ekin.max())},
        "scan": {f"{k:.1f}T": v for k, v in scan.items()},
        "target_offset_scan_at_design_B0": {f"{k:.0f}mm": v for k, v in offset_scan.items()},
        "caveats": [
            "Collisionless orbits; no plasma potential, no collisions, no foil energy loss or scattering.",
            "Foil re-crossings are counted but particles are kept; every re-crossing costs energy in reality.",
            "Insertion arm modelled as a 16 mm wide vertical strip in the X = 0 plane.",
        ],
        "runtime_s": time.time() - t0,
    }
    (OUT / "alpha_orbit_summary.json").write_text(json.dumps(summary, indent=2))
    np.savez_compressed(OUT / "alpha_orbit_tracks.npz", traj=base["traj"], keep=base["keep"],
                        ekin=ekin[base["keep"]], dt_frame=4 * 4.0e-10)

    # ---- fig: fate vs B0
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    cols = [COLORS["good"], COLORS["secondary"], COLORS["accent"], COLORS["target"]]
    bottom = np.zeros(len(b0_scan))
    for k, name in enumerate(FATES):
        vals = np.array([scan[b]["fractions"]["all"][name] for b in b0_scan]) * 100
        ax.bar([f"{b:.0f} T" for b in b0_scan], vals, bottom=bottom, color=cols[k], label=name, width=0.6)
        for i, v in enumerate(vals):
            if v > 4:
                ax.text(i, bottom[i] + v / 2, f"{v:.0f}%", ha="center", va="center", color="white", fontsize=9, fontweight="bold")
        bottom += vals
    ax.set_ylabel("Share of fusion-born alphas (%)")
    ax.set_xlabel("Central-cell field B0 (coil currents scaled)")
    ax.set_title("Where do the alphas go after 4 µs? (full-orbit simulation)")
    ax.set_ylim(0, 100)
    ax.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.18))
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(OUT / "fig_alpha_fate_vs_B.png", dpi=200)
    plt.close(fig)

    # ---- fig: target offset trade-off
    fig, ax = plt.subplots(figsize=(8.5, 4.0))
    offs = list(offset_scan)
    for k, name in enumerate(FATES):
        ax.plot(offs, [offset_scan[o][name] * 100 for o in offs], marker="o", lw=2, color=cols[k], label=name)
    ax.set_xlabel("Target (beam spot) radial offset from axis (mm)")
    ax.set_ylabel("Share of alphas at 4 µs (%)")
    ax.set_title(f"Design trade: target position vs alpha fate (B0 = {P.B0_TARGET_T:.0f} T)")
    ax.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.2))
    fig.tight_layout()
    fig.savefig(OUT / "fig_alpha_target_offset.png", dpi=200)
    plt.close(fig)

    # ---- fig: birth pitch vs energy colored by fate (3 T)
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    for k, name in enumerate(FATES):
        m = base["fate"] == k
        ax.scatter(pitch[m], ekin[m], s=6, alpha=0.7, color=cols[k], label=f"{name} ({np.mean(m)*100:.0f}%)")
    for sgn in (-1, 1):
        ax.axvline(sgn * cos_lc, color=COLORS["ink"], ls="--", lw=1)
    ax.text(cos_lc + 0.02, ekin.max() * 0.97, "loss cone", fontsize=9, color=COLORS["ink"])
    ax.text(-cos_lc - 0.02, ekin.max() * 0.97, "loss cone", fontsize=9, color=COLORS["ink"], ha="right")
    ax.set_xlabel("Birth pitch cosine  v∥/v  (negative = along the beam, toward −X)")
    ax.set_ylabel("Birth energy (MeV)")
    ax.set_title(f"Alpha birth phase space and fate at B0 = {P.B0_TARGET_T:.0f} T")
    ax.legend(markerscale=3, fontsize=9, loc="upper center", ncol=4, bbox_to_anchor=(0.5, -0.17))
    fig.tight_layout()
    fig.savefig(OUT / "fig_alpha_phase_space.png", dpi=200)
    plt.close(fig)

    # ---- fig: orbit projections
    tr = base["traj"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.4), gridspec_kw={"width_ratios": [2.3, 1]})
    th = np.linspace(0, 2 * np.pi, 200)
    for j in range(min(14, tr.shape[1])):
        live = tr[:, j, 3] == 0
        last = np.argmax(~live) if (~live).any() else len(live)
        seg = tr[: max(last, 2), j]
        col = plt.cm.plasma(0.15 + 0.7 * j / 14)
        a1.plot(seg[:, 2] * 1000, np.hypot(seg[:, 0], seg[:, 1]) * 1000, lw=0.6, color=col)
        a2.plot(seg[:, 0] * 1000, seg[:, 1] * 1000, lw=0.6, color=col)
    a1.axhline(P.LIMITER_R, color=COLORS["accent"], ls="--", lw=1)
    a1.axhline(P.VESSEL_R_IN, color=COLORS["ink"], lw=1.4)
    a1.axvspan(-P.VESSEL_X1, -1200, color=COLORS["grid"])
    a1.set_xlim(-1250, 1250); a1.set_ylim(0, 320)
    a1.set_xlabel("X (mm)"); a1.set_ylabel("r (mm)")
    a1.set_title("Side view: gyro-orbits bounce between mirrors")
    a2.plot(P.LIMITER_R * np.cos(th), P.LIMITER_R * np.sin(th), color=COLORS["accent"], ls="--", lw=1)
    a2.plot(P.VESSEL_R_IN * np.cos(th), P.VESSEL_R_IN * np.sin(th), color=COLORS["ink"], lw=1.4)
    a2.add_patch(plt.Circle((0, 0), P.TARGET_FOIL_R, color=COLORS["target"], alpha=0.5))
    a2.set_aspect("equal"); a2.set_xlim(-320, 320); a2.set_ylim(-320, 320)
    a2.set_title("End view: every orbit\nre-visits the foil axis")
    a2.set_xlabel("Y (mm)"); a2.set_ylabel("Z (mm)")
    fig.tight_layout()
    fig.savefig(OUT / "fig_alpha_orbits.png", dpi=200)
    plt.close(fig)

    # ---- fig: survival / fate history at 3 T
    hist = base["alive_hist"]
    fig, ax = plt.subplots(figsize=(8.5, 3.8))
    ax.stackplot(hist[:, 0] * 1e6, *(hist[:, k + 1] * 100 for k in range(4)), colors=cols, labels=FATES, alpha=0.95)
    ax.set_xlabel("Time after birth (µs)"); ax.set_ylabel("Share of alphas (%)")
    ax.set_title(f"Alpha fate history at B0 = {P.B0_TARGET_T:.0f} T")
    ax.set_ylim(0, 100); ax.set_xlim(0, hist[-1, 0] * 1e6)
    ax.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.2))
    fig.tight_layout()
    fig.savefig(OUT / "fig_alpha_fate_history.png", dpi=200)
    plt.close(fig)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
