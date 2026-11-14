"""Analytic and particle-sum benchmarks for Coulomb energy exchange.

The particle-pair moment follows the Landau-operator result used by Turrell,
Sherlock & Rose (J. Plasma Phys. 82, 2016, DOI 10.1017/S0022377816000131),
Eq. (4.1). It is a diagnostic of the instantaneous collision moment; it does
not integrate a distribution in time and does not by itself validate a Monte
Carlo trajectory or an H theorem.

The analytic comparator is the Landau-Spitzer initial temperature exchange
rate for two isotropic Maxwellian species (Spitzer 1967). Note: the printed
(T_a - T_b) sign in Turrell et al. (2016), Eq. (6.3), conflicts with the
physical gain/loss sign implied by their particle moment Eq. (4.1) and energy
balance Eq. (3.7); this implementation uses (T_b - T_a), so the hotter
species cools. Temperatures passed to this module are in eV.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

import numpy as np
from scipy.constants import e, epsilon_0


@dataclass(frozen=True)
class PairwiseEnergyExchange:
    species_a: str
    species_b: str
    q_a_w_m3: float
    q_b_w_m3: float
    conservation_residual_w_m3: float
    pair_count: int
    coulomb_logarithm: float
    mean_drift_a_m_s: tuple[float, float, float]
    mean_drift_b_m_s: tuple[float, float, float]


def _validate_velocity_array(name: str, value: np.ndarray) -> np.ndarray:
    v = np.asarray(value, dtype=float)
    if v.ndim != 2 or v.shape[1] != 3 or v.shape[0] < 2 or np.any(~np.isfinite(v)):
        raise ValueError(f"{name} must be a finite array with shape (N>=2, 3)")
    return v


def _validate_species(
    name: str, mass_kg: float, charge_c: float, density_m3: float,
    velocities: np.ndarray,
) -> tuple[str, float, float, float, np.ndarray]:
    if not isinstance(name, str) or not name.strip():
        raise ValueError("species name must be a non-empty string")
    if not (math.isfinite(mass_kg) and mass_kg > 0):
        raise ValueError("mass_kg must be finite and positive")
    if not (math.isfinite(charge_c) and charge_c != 0):
        raise ValueError("charge_c must be finite and nonzero")
    if not (math.isfinite(density_m3) and density_m3 > 0):
        raise ValueError("density_m3 must be finite and positive")
    return name, float(mass_kg), float(charge_c), float(density_m3), _validate_velocity_array("velocities", velocities)


def _pair_power_one_direction(
    va: np.ndarray,
    vb: np.ndarray,
    *,
    mass_a_kg: float,
    mass_b_kg: float,
    charge_a_c: float,
    charge_b_c: float,
    density_a_m3: float,
    density_b_m3: float,
    coulomb_logarithm: float,
    chunk_rows: int = 128,
) -> float:
    """Evaluate Eq. (4.1) in chunks to bound memory use."""
    na, nb = va.shape[0], vb.shape[0]
    drift_a = np.mean(va, axis=0)
    mass_sum = mass_a_kg + mass_b_kg
    prefactor = (
        4.0 * math.pi * coulomb_logarithm
        * (density_a_m3 * density_b_m3 / (na * nb))
        * (charge_a_c * charge_b_c / (4.0 * math.pi * epsilon_0)) ** 2
    )
    total = 0.0
    for start in range(0, na, chunk_rows):
        va_block = va[start:start + chunk_rows]
        relative = va_block[:, None, :] - vb[None, :, :]
        speed_sq = np.einsum("ijk,ijk->ij", relative, relative)
        speed = np.sqrt(speed_sq)
        # Pairs with exactly identical floating-point velocities have a
        # measure-zero contribution for continuous distributions. Exclude
        # exact zeros rather than dividing by zero.
        valid = speed > 0.0
        if not np.any(valid):
            continue
        dot = np.einsum("ijk,ik->ij", relative, va_block - drift_a)
        bracket = np.zeros_like(speed)
        bracket[valid] = (
            speed_sq[valid] / mass_a_kg
            - (mass_sum / (mass_a_kg * mass_b_kg)) * dot[valid]
        ) / (speed[valid] ** 3)
        total += float(np.sum(bracket))
    return float(prefactor * total)


def landau_pairwise_energy_exchange(
    *,
    species_a: str,
    species_b: str,
    mass_a_kg: float,
    mass_b_kg: float,
    charge_a_c: float,
    charge_b_c: float,
    density_a_m3: float,
    density_b_m3: float,
    velocities_a_m_s: np.ndarray,
    velocities_b_m_s: np.ndarray,
    coulomb_logarithm: float,
    chunk_rows: int = 128,
) -> PairwiseEnergyExchange:
    """Return pairwise Landau energy-exchange moments Q_a and Q_b.

    The result is in W m^-3 and includes the density-per-macroparticle
    normalization n_a*n_b/(N_a*N_b). For a zero-drift Maxwellian pair,
    Q_a + Q_b should be numerically zero. For drifting distributions, this
    function returns thermal-frame exchange moments; bulk-flow work is a
    separate moment and the residual need not vanish by itself.
    """
    if species_a == species_b:
        raise ValueError("this diagnostic is for two distinct species")
    if not (math.isfinite(coulomb_logarithm) and coulomb_logarithm > 0):
        raise ValueError("coulomb_logarithm must be finite and positive")
    if not isinstance(chunk_rows, int) or chunk_rows < 1:
        raise ValueError("chunk_rows must be a positive integer")
    a = _validate_species(species_a, mass_a_kg, charge_a_c, density_a_m3, velocities_a_m_s)
    b = _validate_species(species_b, mass_b_kg, charge_b_c, density_b_m3, velocities_b_m_s)
    va, vb = a[4], b[4]
    common = dict(
        mass_a_kg=a[1], mass_b_kg=b[1], charge_a_c=a[2], charge_b_c=b[2],
        density_a_m3=a[3], density_b_m3=b[3],
        coulomb_logarithm=coulomb_logarithm, chunk_rows=chunk_rows,
    )
    q_a = _pair_power_one_direction(va, vb, **common)
    reverse = dict(
        mass_a_kg=b[1], mass_b_kg=a[1], charge_a_c=b[2], charge_b_c=a[2],
        density_a_m3=b[3], density_b_m3=a[3],
        coulomb_logarithm=coulomb_logarithm, chunk_rows=chunk_rows,
    )
    q_b = _pair_power_one_direction(vb, va, **reverse)
    return PairwiseEnergyExchange(
        species_a=a[0], species_b=b[0], q_a_w_m3=q_a, q_b_w_m3=q_b,
        conservation_residual_w_m3=q_a + q_b,
        pair_count=int(va.shape[0] * vb.shape[0]),
        coulomb_logarithm=float(coulomb_logarithm),
        mean_drift_a_m_s=tuple(float(x) for x in np.mean(va, axis=0)),
        mean_drift_b_m_s=tuple(float(x) for x in np.mean(vb, axis=0)),
    )


def landau_spitzer_temperature_rate_ev_s(
    *,
    mass_a_kg: float,
    mass_b_kg: float,
    charge_a_c: float,
    charge_b_c: float,
    density_b_m3: float,
    temperature_a_ev: float,
    temperature_b_ev: float,
    coulomb_logarithm: float,
) -> float:
    """Analytic initial dT_a/dt in eV/s for two Maxwellian species.

    The sign is chosen so that a hotter species (T_a > T_b) cools. This is
    the Landau-Spitzer Maxwellian energy-exchange moment, not a momentum
    deflection frequency.
    """
    for name, value in (("mass_a_kg", mass_a_kg), ("mass_b_kg", mass_b_kg),
                        ("density_b_m3", density_b_m3),
                        ("temperature_a_ev", temperature_a_ev),
                        ("temperature_b_ev", temperature_b_ev),
                        ("coulomb_logarithm", coulomb_logarithm)):
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be finite and positive")
    if not math.isfinite(charge_a_c) or charge_a_c == 0 or not math.isfinite(charge_b_c) or charge_b_c == 0:
        raise ValueError("charges must be finite and nonzero")
    ta = temperature_a_ev * e
    tb = temperature_b_ev * e
    prefactor = (
        density_b_m3 * (8.0 * math.sqrt(math.pi) / 3.0)
        * math.sqrt(2.0 * mass_a_kg) / mass_b_kg
        * (charge_a_c * charge_b_c / (4.0 * math.pi * epsilon_0)) ** 2
        * coulomb_logarithm
    )
    dta_dt_j_s = prefactor * (ta + (mass_a_kg / mass_b_kg) * tb) ** (-1.5) * (tb - ta)
    return float(dta_dt_j_s / e)


def temperature_ev_from_velocities(velocities_m_s: np.ndarray, mass_kg: float) -> float:
    """Return the scalar 3-D temperature after subtracting species drift."""
    v = _validate_velocity_array("velocities_m_s", velocities_m_s)
    if not (math.isfinite(mass_kg) and mass_kg > 0):
        raise ValueError("mass_kg must be finite and positive")
    centered = v - np.mean(v, axis=0)
    return float(mass_kg * np.mean(np.sum(centered * centered, axis=1)) / (3.0 * e))


def landau_spitzer_power_density_w_m3(
    *,
    density_a_m3: float,
    temperature_rate_a_ev_s: float,
) -> float:
    """Convert dT_a/dt to collisional thermal power density Q_a."""
    if not (math.isfinite(density_a_m3) and density_a_m3 > 0 and math.isfinite(temperature_rate_a_ev_s)):
        raise ValueError("density must be positive and temperature rate finite")
    return float(1.5 * density_a_m3 * e * temperature_rate_a_ev_s)
