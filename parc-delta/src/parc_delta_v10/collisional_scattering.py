"""Independent test-particle Takizuka–Abe and Nanbu Coulomb samplers.

Each alpha marker is scattered from a freshly sampled Maxwellian field
particle. The field is held fixed: this is a test-particle reservoir model,
not a self-consistent field-particle update. For equal macroparticle weights,
the corresponding TA pairing formula uses the smaller density; for this
fixed-bath test-particle realization the physical bath density n_b is used.

The Nanbu isotropy parameter is calibrated to the TA small-angle limit:
E[1-cos(chi)] ~ s = 2 E[tan^2(Theta_TA/2)].
"""
from __future__ import annotations

import math
from typing import Literal

import numpy as np
from scipy.constants import e, epsilon_0

from .slowing_down import MaxwellianFieldSpecies


def _orthonormal_perpendicular(axis: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    ref = np.zeros_like(axis)
    choose_z = np.abs(axis[:, 2]) < 0.9
    ref[choose_z, 2] = 1.0
    ref[~choose_z, 1] = 1.0
    e1 = np.cross(axis, ref)
    norm = np.linalg.norm(e1, axis=1)
    e1 /= norm[:, None]
    e2 = np.cross(axis, e1)
    return e1, e2


def _langevin_function(a: np.ndarray) -> np.ndarray:
    out = np.empty_like(a)
    small = a < 1.0e-3
    x = a[small]
    out[small] = x / 3.0 - x**3 / 45.0 + 2.0 * x**5 / 945.0
    mid = (~small) & (a < 20.0)
    out[mid] = 1.0 / np.tanh(a[mid]) - 1.0 / a[mid]
    large = a >= 20.0
    out[large] = 1.0 - 1.0 / a[large]
    return out


def nanbu_a_from_s(s: np.ndarray | float) -> np.ndarray:
    """Solve coth(A)-1/A=exp(-s), vectorized with safeguarded Newton steps."""
    sv = np.asarray(s, dtype=float)
    if np.any(~np.isfinite(sv)) or np.any(sv < 0.0):
        raise ValueError("s must be finite and non-negative")
    target = np.exp(-sv)
    out = np.zeros_like(sv)
    # Zero cumulative collision exposure means no deflection: A -> infinity.
    out[sv == 0.0] = np.inf
    active = (sv > 0.0) & (target > 1.0e-14)
    if not np.any(active):
        return out
    t = target[active]
    # Cohen inverse-Langevin initial approximation; Newton corrects it.
    denom = np.maximum(1.0e-15, 1.0 - t * t)
    a = np.maximum(1.0e-14, (3.0 * t - t**3) / denom)
    for _ in range(10):
        f = _langevin_function(a) - t
        deriv = np.empty_like(a)
        small = a < 1.0e-3
        deriv[small] = 1.0 / 3.0 - a[small]**2 / 15.0 + 2.0 * a[small]**4 / 189.0
        mid = (~small) & (a < 20.0)
        deriv[mid] = 1.0 / a[mid]**2 - 1.0 / np.sinh(a[mid])**2
        large = a >= 20.0
        deriv[large] = 1.0 / a[large]**2
        update = f / np.maximum(deriv, 1.0e-30)
        a = np.maximum(1.0e-14, a - update)
    out[active] = a
    return out


def _sample_nanbu_cosine(a: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    u = rng.random(a.size)
    cosine = np.empty_like(a)
    isotropic = a < 1.0e-7
    cosine[isotropic] = 2.0 * u[isotropic] - 1.0
    concentrated = ~isotropic
    # cos(chi)=1+log(u+(1-u)exp(-2A))/A.
    ac = a[concentrated]
    uc = u[concentrated]
    logterm = np.logaddexp(np.log(np.maximum(uc, 1.0e-300)),
                           np.log(np.maximum(1.0 - uc, 1.0e-300)) - 2.0 * ac)
    cosine[concentrated] = 1.0 + logterm / ac
    return np.clip(cosine, -1.0, 1.0)


def _update_test_particle(
    test_velocity: np.ndarray,
    field_velocity: np.ndarray,
    *,
    test_mass_kg: float,
    field_mass_kg: float,
    cosine: np.ndarray,
    azimuth: np.ndarray,
) -> np.ndarray:
    relative = test_velocity - field_velocity
    speed = np.linalg.norm(relative, axis=1)
    moving = speed > 0.0
    axis = np.zeros_like(relative)
    axis[moving] = relative[moving] / speed[moving, None]
    axis[~moving, 0] = 1.0
    e1, e2 = _orthonormal_perpendicular(axis)
    sine = np.sqrt(np.maximum(0.0, 1.0 - cosine * cosine))
    new_axis = (
        cosine[:, None] * axis
        + sine[:, None] * (np.cos(azimuth)[:, None] * e1 + np.sin(azimuth)[:, None] * e2)
    )
    relative_new = speed[:, None] * new_axis
    fraction = field_mass_kg / (test_mass_kg + field_mass_kg)
    return test_velocity + fraction * (relative_new - relative)


def advance_test_particle_collision_step(
    velocities_m_s: np.ndarray,
    *,
    test_mass_kg: float,
    test_charge_c: float,
    field_species: MaxwellianFieldSpecies,
    dt_s: float,
    coulomb_logarithm: float,
    method: Literal["takizuka_abe", "nanbu"],
    rng: np.random.Generator,
) -> np.ndarray:
    """Advance test particles against a fixed Maxwellian field reservoir."""
    v = np.asarray(velocities_m_s, dtype=float)
    if v.ndim != 2 or v.shape[1] != 3 or v.shape[0] < 1 or np.any(~np.isfinite(v)):
        raise ValueError("velocities_m_s must have shape (N,3) and be finite")
    if not (math.isfinite(test_mass_kg) and test_mass_kg > 0.0):
        raise ValueError("test_mass_kg must be positive")
    if not math.isfinite(test_charge_c) or test_charge_c == 0.0:
        raise ValueError("test_charge_c must be nonzero")
    if not (math.isfinite(dt_s) and dt_s > 0.0):
        raise ValueError("dt_s must be positive")
    if not (math.isfinite(coulomb_logarithm) and coulomb_logarithm > 0.0):
        raise ValueError("coulomb_logarithm must be positive")
    if method not in ("takizuka_abe", "nanbu"):
        raise ValueError("method must be 'takizuka_abe' or 'nanbu'")

    field_sigma = math.sqrt(field_species.temperature_ev * e / field_species.mass_kg)
    vb = rng.normal(0.0, field_sigma, size=v.shape)
    relative = v - vb
    g = np.linalg.norm(relative, axis=1)
    mu = test_mass_kg * field_species.mass_kg / (test_mass_kg + field_species.mass_kg)
    # TA Gaussian variance for delta=tan(Theta/2). The test-particle bath
    # density n_b is used rather than the equal-weight paired min-density.
    prefactor = (test_charge_c * field_species.charge_c) ** 2 * field_species.density_m3 * coulomb_logarithm
    variance_delta = np.zeros_like(g)
    valid = g > 0.0
    variance_delta[valid] = (
        prefactor * dt_s
        / (8.0 * math.pi * epsilon_0**2 * mu**2 * g[valid]**3)
    )
    if method == "takizuka_abe":
        delta = rng.normal(0.0, np.sqrt(variance_delta))
        theta = 2.0 * np.arctan(delta)
        cosine = np.cos(theta)
    else:
        # Match TA's small-angle second moment: <1-cos(chi)> = s + O(s^2).
        isotropy = 2.0 * variance_delta
        a = nanbu_a_from_s(isotropy)
        cosine = _sample_nanbu_cosine(a, rng)
    azimuth = rng.uniform(0.0, 2.0 * math.pi, size=v.shape[0])
    return _update_test_particle(
        v, vb, test_mass_kg=test_mass_kg, field_mass_kg=field_species.mass_kg,
        cosine=cosine, azimuth=azimuth,
    )


def run_test_particle_scattering(
    initial_velocities_m_s: np.ndarray,
    *,
    test_mass_kg: float,
    test_charge_c: float,
    field_species: MaxwellianFieldSpecies,
    dt_s: float,
    steps: int,
    coulomb_logarithm: float,
    method: Literal["takizuka_abe", "nanbu"],
    seed: int = 0,
    record_every: int = 100,
) -> list[dict[str, float]]:
    """Run TA or Nanbu test-particle scattering and return energy snapshots."""
    v = np.asarray(initial_velocities_m_s, dtype=float).copy()
    if not isinstance(steps, int) or steps < 1 or not isinstance(record_every, int) or record_every < 1:
        raise ValueError("steps and record_every must be positive integers")
    rng = np.random.default_rng(seed)
    out: list[dict[str, float]] = []

    def add_snapshot(step: int) -> None:
        energy_ev = 0.5 * test_mass_kg * np.sum(v * v, axis=1) / e
        out.append({
            "time_s": step * dt_s,
            "mean_energy_ev": float(np.mean(energy_ev)),
            "median_energy_ev": float(np.median(energy_ev)),
            "q05_energy_ev": float(np.quantile(energy_ev, 0.05)),
            "q95_energy_ev": float(np.quantile(energy_ev, 0.95)),
        })

    add_snapshot(0)
    for step in range(1, steps + 1):
        v = advance_test_particle_collision_step(
            v, test_mass_kg=test_mass_kg, test_charge_c=test_charge_c,
            field_species=field_species, dt_s=dt_s,
            coulomb_logarithm=coulomb_logarithm, method=method, rng=rng,
        )
        if step % record_every == 0 or step == steps:
            add_snapshot(step)
    return out


def advance_test_particle_multispecies_collision_step(
    velocities_m_s: np.ndarray,
    *,
    test_mass_kg: float,
    test_charge_c: float,
    field_species: tuple[MaxwellianFieldSpecies, ...] | list[MaxwellianFieldSpecies],
    dt_s: float,
    coulomb_logarithm: float,
    method: Literal["takizuka_abe", "nanbu"],
    rng: np.random.Generator,
    substeps_per_species: int = 1,
) -> np.ndarray:
    """Advance test markers against several fixed Maxwellian baths.

    A symmetric forward/reverse composition is used to reduce deterministic
    species-order bias. Each field species receives a total exposure of
    ``dt_s`` split across ``substeps_per_species`` independent small-angle
    updates in each half pass. The backgrounds remain fixed and are not
    updated.
    """
    fields = tuple(field_species)
    if not fields:
        raise ValueError("at least one field species is required")
    if len({item.name for item in fields}) != len(fields):
        raise ValueError("field species names must be unique")
    if not (math.isfinite(dt_s) and dt_s > 0.0):
        raise ValueError("dt_s must be finite and positive")
    if not isinstance(substeps_per_species, int) or substeps_per_species < 1:
        raise ValueError("substeps_per_species must be a positive integer")
    v = np.asarray(velocities_m_s, dtype=float)
    sub_dt = 0.5 * dt_s / substeps_per_species
    for field in fields:
        for _ in range(substeps_per_species):
            v = advance_test_particle_collision_step(
                v,
                test_mass_kg=test_mass_kg,
                test_charge_c=test_charge_c,
                field_species=field,
                dt_s=sub_dt,
                coulomb_logarithm=coulomb_logarithm,
                method=method,
                rng=rng,
            )
    for field in reversed(fields):
        for _ in range(substeps_per_species):
            v = advance_test_particle_collision_step(
                v,
                test_mass_kg=test_mass_kg,
                test_charge_c=test_charge_c,
                field_species=field,
                dt_s=sub_dt,
                coulomb_logarithm=coulomb_logarithm,
                method=method,
                rng=rng,
            )
    return v


def run_test_particle_multispecies_scattering(
    initial_velocities_m_s: np.ndarray,
    *,
    test_mass_kg: float,
    test_charge_c: float,
    field_species: tuple[MaxwellianFieldSpecies, ...] | list[MaxwellianFieldSpecies],
    dt_s: float,
    steps: int,
    coulomb_logarithm: float,
    method: Literal["takizuka_abe", "nanbu"],
    seed: int = 0,
    record_every: int = 100,
    substeps_per_species: int = 1,
) -> list[dict[str, float]]:
    """Run symmetric-split multispecies test-particle scattering."""
    v = np.asarray(initial_velocities_m_s, dtype=float).copy()
    if not isinstance(steps, int) or steps < 1:
        raise ValueError("steps must be a positive integer")
    if not isinstance(record_every, int) or record_every < 1:
        raise ValueError("record_every must be a positive integer")
    if not (math.isfinite(dt_s) and dt_s > 0.0):
        raise ValueError("dt_s must be finite and positive")
    rng = np.random.default_rng(seed)
    out: list[dict[str, float]] = []

    def add_snapshot(step: int) -> None:
        energy_ev = 0.5 * test_mass_kg * np.sum(v * v, axis=1) / e
        out.append({
            "time_s": step * dt_s,
            "mean_energy_ev": float(np.mean(energy_ev)),
            "median_energy_ev": float(np.median(energy_ev)),
            "q05_energy_ev": float(np.quantile(energy_ev, 0.05)),
            "q95_energy_ev": float(np.quantile(energy_ev, 0.95)),
        })

    add_snapshot(0)
    for step in range(1, steps + 1):
        v = advance_test_particle_multispecies_collision_step(
            v,
            test_mass_kg=test_mass_kg,
            test_charge_c=test_charge_c,
            field_species=field_species,
            dt_s=dt_s,
            coulomb_logarithm=coulomb_logarithm,
            method=method,
            rng=rng,
            substeps_per_species=substeps_per_species,
        )
        if step % record_every == 0 or step == steps:
            add_snapshot(step)
    return out
