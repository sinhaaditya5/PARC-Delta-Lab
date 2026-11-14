"""Sequential p-11B -> 3 alpha birth kinematics for PARC-Delta.

This is a kinematic source generator, not a reaction-rate or branching model.
The alpha_0 and alpha_1 channels are generated separately. Their branching
fractions, differential cross sections, and energy-dependent yields must be
provided from a validated nuclear-data evaluation before combining them.

The alpha_1 channel uses a truncated Cauchy/Breit-Wigner proxy for the
unbound 8Be first-excited-state invariant-mass distribution. It is a
transparent approximation, not a full R-matrix/sequential-decay calculation.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Literal

import numpy as np
from scipy.constants import atomic_mass, c, e, m_e, m_p, physical_constants

# Nuclear masses in MeV/c^2. The 11B nuclear mass is reconstructed from the
# neutral-atom mass by subtracting five electron rest masses; atomic electron
# binding-energy corrections (sub-keV) are neglected. p and alpha masses use
# CODATA nuclear masses directly. This is the fully ionized plasma convention.
M_B11_ATOMIC_U = 11.00930536
U_C2_MEV = atomic_mass * c**2 / (1.0e6 * e)
M_PROTON_MEV = m_p * c**2 / (1.0e6 * e)
M_BORON11_MEV = (M_B11_ATOMIC_U - 5.0 * m_e / atomic_mass) * U_C2_MEV
M_ALPHA_MEV = physical_constants["alpha particle mass"][0] * c**2 / (1.0e6 * e)
Q_TOTAL_MEV = M_PROTON_MEV + M_BORON11_MEV - 3.0 * M_ALPHA_MEV

# Nuclear-structure inputs summarized in the cited literature.
BE8_GROUND_RELATIVE_ENERGY_MEV = 0.09184
BE8_EXCITED_RELATIVE_ENERGY_MEV = 3.028
BE8_EXCITED_WIDTH_MEV = 1.5

Channel = Literal["alpha0", "alpha1"]


@dataclass(frozen=True)
class AlphaBirthSample:
    """Three alpha particles per reaction, in the requested output frame."""
    kinetic_energy_mev: np.ndarray  # (3*N_events,)
    velocity_m_s: np.ndarray        # (3*N_events, 3)
    event_id: np.ndarray            # (3*N_events,)
    role: np.ndarray                # primary, be8_daughter_1, be8_daughter_2
    pitch_cosine: np.ndarray        # relative to the supplied magnetic-field axis
    channel: str
    e_cm_mev: np.ndarray            # (N_events,), event-level entrance CM energies
    be8_relative_energy_mev: np.ndarray  # (N_events,)
    metadata: dict[str, float | str | int]

    def summary(self) -> dict[str, float | int | str]:
        energy = self.kinetic_energy_mev
        return {
            "channel": self.channel,
            "events": int(self.e_cm_mev.size),
            "alpha_count": int(energy.size),
            "energy_mean_mev": float(np.mean(energy)),
            "energy_std_mev": float(np.std(energy)),
            "energy_min_mev": float(np.min(energy)),
            "energy_max_mev": float(np.max(energy)),
            "energy_q05_mev": float(np.quantile(energy, 0.05)),
            "energy_q50_mev": float(np.quantile(energy, 0.50)),
            "energy_q95_mev": float(np.quantile(energy, 0.95)),
            "mean_pitch_cosine": float(np.mean(self.pitch_cosine)),
            "mean_total_alpha_energy_per_event_mev": float(
                np.mean(np.bincount(self.event_id, weights=energy))
            ),
        }


def e_cm_from_proton_lab_energy(e_p_lab_mev: float) -> float:
    """Relativistic p + stationary 11B CM kinetic energy in MeV."""
    if not math.isfinite(e_p_lab_mev) or e_p_lab_mev < 0:
        raise ValueError("e_p_lab_mev must be finite and non-negative")
    s = (
        M_PROTON_MEV**2 + M_BORON11_MEV**2
        + 2.0 * M_BORON11_MEV * (M_PROTON_MEV + e_p_lab_mev)
    )
    return math.sqrt(s) - M_PROTON_MEV - M_BORON11_MEV


def proton_lab_energy_from_e_cm(e_cm_mev: float) -> float:
    """Inverse relativistic conversion for a stationary 11B target."""
    if not math.isfinite(e_cm_mev) or e_cm_mev < 0:
        raise ValueError("e_cm_mev must be finite and non-negative")
    w = M_PROTON_MEV + M_BORON11_MEV + e_cm_mev
    return (w * w - (M_PROTON_MEV**2 + M_BORON11_MEV**2)) / (
        2.0 * M_BORON11_MEV
    ) - M_PROTON_MEV


def _unit_vectors(rng: np.random.Generator, count: int) -> np.ndarray:
    z = rng.uniform(-1.0, 1.0, count)
    phi = rng.uniform(0.0, 2.0 * math.pi, count)
    radial = np.sqrt(np.maximum(0.0, 1.0 - z * z))
    return np.column_stack((radial * np.cos(phi), radial * np.sin(phi), z))


def _boost_four_vector(
    energy_mev: np.ndarray, momentum_mev_c: np.ndarray, beta: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Boost four-vectors by beta (dimensionless), using c=1 units."""
    beta2 = np.sum(beta * beta, axis=1)
    if np.any(beta2 >= 1.0):
        raise ValueError("Lorentz boost requires |beta| < 1")
    gamma = 1.0 / np.sqrt(1.0 - beta2)
    bp = np.sum(beta * momentum_mev_c, axis=1)
    factor = np.zeros_like(energy_mev)
    nz = beta2 > 0.0
    factor[nz] = ((gamma[nz] - 1.0) * bp[nz] / beta2[nz]) + gamma[nz] * energy_mev[nz]
    p_out = momentum_mev_c + factor[:, None] * beta
    e_out = gamma * (energy_mev + bp)
    return e_out, p_out


def _sample_be8_relative_energy(
    rng: np.random.Generator,
    channel: Channel,
    e_available_mev: np.ndarray,
) -> np.ndarray:
    if channel == "alpha0":
        return np.full_like(e_available_mev, BE8_GROUND_RELATIVE_ENERGY_MEV)
    if channel != "alpha1":
        raise ValueError("channel must be 'alpha0' or 'alpha1'")
    lo = 0.0
    hi = np.maximum(1.0e-9, e_available_mev - 1.0e-9)
    half_width = 0.5 * BE8_EXCITED_WIDTH_MEV
    cdf_lo = 0.5 + np.arctan((lo - BE8_EXCITED_RELATIVE_ENERGY_MEV) / half_width) / math.pi
    cdf_hi = 0.5 + np.arctan((hi - BE8_EXCITED_RELATIVE_ENERGY_MEV) / half_width) / math.pi
    u = cdf_lo + rng.random(e_available_mev.size) * (cdf_hi - cdf_lo)
    return BE8_EXCITED_RELATIVE_ENERGY_MEV + half_width * np.tan(math.pi * (u - 0.5))



def gyrotropic_velocity_histogram(
    sample: AlphaBirthSample,
    *,
    v_parallel_edges_m_s: np.ndarray,
    v_perp_edges_m_s: np.ndarray,
) -> dict[str, np.ndarray | float]:
    """Project a 3-D alpha source onto (v_parallel, v_perp) and normalize f.

    The returned ``f_v`` is a probability density in 3-D velocity space under
    gyrotropic symmetry, so sum(f_v * 2*pi*v_perp*dv_perp*dv_parallel) = 1.
    This is a source representation only; it is not yet a susceptibility.
    """
    vpar_edges = np.asarray(v_parallel_edges_m_s, dtype=float)
    vperp_edges = np.asarray(v_perp_edges_m_s, dtype=float)
    for name, edges in (("v_parallel_edges_m_s", vpar_edges), ("v_perp_edges_m_s", vperp_edges)):
        if edges.ndim != 1 or edges.size < 3 or np.any(~np.isfinite(edges)) or np.any(np.diff(edges) <= 0):
            raise ValueError(f"{name} must be a finite, strictly increasing 1-D array")
    if vperp_edges[0] < 0:
        raise ValueError("v_perp_edges_m_s cannot begin below zero")
    speed = np.linalg.norm(sample.velocity_m_s, axis=1)
    vpar = speed * sample.pitch_cosine
    vperp = np.sqrt(np.maximum(0.0, speed**2 - vpar**2))
    counts, _, _ = np.histogram2d(vpar, vperp, bins=(vpar_edges, vperp_edges))
    dvpar = np.diff(vpar_edges)
    dvperp = np.diff(vperp_edges)
    vperp_mid = 0.5 * (vperp_edges[:-1] + vperp_edges[1:])
    cell_volume = (dvpar[:, None] * (2.0 * math.pi * vperp_mid[None, :] * dvperp[None, :]))
    f_v = counts / (sample.velocity_m_s.shape[0] * cell_volume)
    normalization = float(np.sum(f_v * cell_volume))
    return {
        "v_parallel_centers_m_s": 0.5 * (vpar_edges[:-1] + vpar_edges[1:]),
        "v_perp_centers_m_s": vperp_mid,
        "f_v_s3_per_m3": f_v,
        "cell_volume_m3_per_s3": cell_volume,
        "normalization": normalization,
        "captured_particle_fraction": float(np.sum(counts) / sample.velocity_m_s.shape[0]),
    }

def sample_pb11_alpha_birth(
    event_count: int,
    *,
    channel: Channel,
    e_cm_mev: float | np.ndarray,
    seed: int = 0,
    frame: Literal["cm", "beam_lab"] = "cm",
    magnetic_field_axis: tuple[float, float, float] = (0.0, 0.0, 1.0),
) -> AlphaBirthSample:
    """Sample sequential p-11B -> alpha + 8Be -> 3 alpha kinematics.

    Args:
        event_count: Number of independent fusion events.
        channel: ``alpha0`` (8Be ground-state branch) or ``alpha1`` (first
            excited-state branch). No branching ratio is assumed.
        e_cm_mev: Scalar or one value per event. This is the entrance-channel
            relative kinetic energy in the p-11B center-of-mass frame.
        seed: Random seed for reproducibility.
        frame: ``cm`` gives the reacting-pair CM frame; ``beam_lab`` applies
            the exact boost for a proton beam incident on stationary 11B.
        magnetic_field_axis: Axis used only to calculate pitch cosine.

    Returns:
        Three alpha 4-vector samples per event with event IDs and roles.
    """
    if event_count < 1:
        raise ValueError("event_count must be >= 1")
    if frame not in ("cm", "beam_lab"):
        raise ValueError("frame must be 'cm' or 'beam_lab'")
    ecm = np.asarray(e_cm_mev, dtype=float)
    if ecm.ndim == 0:
        ecm = np.full(event_count, float(ecm))
    if ecm.shape != (event_count,) or np.any(~np.isfinite(ecm)) or np.any(ecm < 0):
        raise ValueError("e_cm_mev must be a non-negative scalar or length event_count array")

    b_axis = np.asarray(magnetic_field_axis, dtype=float)
    if b_axis.shape != (3,) or not np.all(np.isfinite(b_axis)):
        raise ValueError("magnetic_field_axis must be a finite 3-vector")
    b_norm = float(np.linalg.norm(b_axis))
    if b_norm == 0:
        raise ValueError("magnetic_field_axis cannot be zero")
    b_axis /= b_norm

    rng = np.random.default_rng(seed)
    parent_energy = M_PROTON_MEV + M_BORON11_MEV + ecm
    available = Q_TOTAL_MEV + ecm
    be8_rel = _sample_be8_relative_energy(rng, channel, available)
    be8_mass = 2.0 * M_ALPHA_MEV + be8_rel

    # Exact relativistic two-body p + 11B -> alpha + 8Be kinematics.
    lam = (
        (parent_energy**2 - (M_ALPHA_MEV + be8_mass)**2)
        * (parent_energy**2 - (M_ALPHA_MEV - be8_mass)**2)
    )
    if np.any(lam <= 0.0):
        raise ValueError("sampled 8Be invariant mass is outside two-body phase space")
    p_primary = np.sqrt(lam) / (2.0 * parent_energy)  # MeV/c
    e_primary = np.sqrt(M_ALPHA_MEV**2 + p_primary**2)
    e_be8 = np.sqrt(be8_mass**2 + p_primary**2)

    primary_dir = _unit_vectors(rng, event_count)
    p_primary_vec = p_primary[:, None] * primary_dir
    p_be8_vec = -p_primary_vec
    beta_be8 = p_be8_vec / e_be8[:, None]

    # Isotropic 8Be -> alpha + alpha decay in the 8Be rest frame.
    daughter_p = np.sqrt(np.maximum(0.0, 0.25 * be8_mass**2 - M_ALPHA_MEV**2))
    daughter_dir = _unit_vectors(rng, event_count)
    daughter_p_vec = daughter_p[:, None] * daughter_dir
    daughter_e = 0.5 * be8_mass

    daughter_1_e, daughter_1_p = _boost_four_vector(
        daughter_e, daughter_p_vec, beta_be8
    )
    daughter_2_e, daughter_2_p = _boost_four_vector(
        daughter_e, -daughter_p_vec, beta_be8
    )

    # CM-frame primary alpha and the two boosted 8Be daughters.
    energy_all = np.column_stack((e_primary, daughter_1_e, daughter_2_e))
    momentum_all = np.stack((p_primary_vec, daughter_1_p, daughter_2_p), axis=1)

    if frame == "beam_lab":
        # For a proton beam on a stationary boron target, total CM momentum is
        # the incoming proton momentum along +z.
        e_p_lab = np.array([proton_lab_energy_from_e_cm(x) for x in ecm])
        p_beam = np.sqrt(e_p_lab * (e_p_lab + 2.0 * M_PROTON_MEV))
        beta_cm = np.zeros((event_count, 3), dtype=float)
        beta_cm[:, 2] = p_beam / (M_PROTON_MEV + M_BORON11_MEV + e_p_lab)
        for role_idx in range(3):
            energy_all[:, role_idx], momentum_all[:, role_idx, :] = _boost_four_vector(
                energy_all[:, role_idx], momentum_all[:, role_idx, :], beta_cm
            )

    kinetic_mev = energy_all - M_ALPHA_MEV
    speed = np.linalg.norm(momentum_all, axis=2) / energy_all * c
    velocity = momentum_all / np.maximum(np.linalg.norm(momentum_all, axis=2)[:, :, None], 1e-300) * speed[:, :, None]

    # Flatten event-major: primary, daughter 1, daughter 2 for each event.
    velocity_flat = velocity.reshape(-1, 3)
    energy_flat = kinetic_mev.reshape(-1)
    event_ids = np.repeat(np.arange(event_count, dtype=int), 3)
    roles = np.tile(np.array(["primary", "be8_daughter_1", "be8_daughter_2"]), event_count)
    pitch = velocity_flat @ b_axis / np.maximum(np.linalg.norm(velocity_flat, axis=1), 1e-300)

    return AlphaBirthSample(
        kinetic_energy_mev=energy_flat,
        velocity_m_s=velocity_flat,
        event_id=event_ids,
        role=roles,
        pitch_cosine=np.clip(pitch, -1.0, 1.0),
        channel=channel,
        e_cm_mev=ecm.copy(),
        be8_relative_energy_mev=be8_rel,
        metadata={
            "frame": frame,
            "q_total_mev": Q_TOTAL_MEV,
            "be8_excited_width_mev": BE8_EXCITED_WIDTH_MEV if channel == "alpha1" else 0.0,
            "be8_ground_relative_energy_mev": BE8_GROUND_RELATIVE_ENERGY_MEV,
            "branching_fraction_assumed": 0.0,
            "cross_section_weighting": "not applied",
        },
    )
