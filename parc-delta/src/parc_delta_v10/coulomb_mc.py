"""Conserving pairwise small-angle Coulomb collision Monte Carlo.

The operator is a stochastic weak-deflection (Landau-limit) particle
realization. Each macro-particle in every species must carry the same physical
number weight. Each pair update rotates relative velocity at fixed magnitude,
so pair momentum and kinetic energy are conserved to floating-point accuracy.

This is not a deterministic finite-grid Landau discretization, not a
finite-Larmor-radius gyrokinetic operator, and not yet coupled into the
finite-k_parallel eigenvalue solver. Strongly coupled encounters (ln Lambda <=
0) are rejected rather than silently clipped into a weak-coupling model.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

import numpy as np
from scipy.constants import e, epsilon_0, hbar


@dataclass(frozen=True)
class CollisionSpecies:
    name: str
    mass_kg: float
    charge_c: float
    density_m3: float
    temperature_ev: float
    velocity_m_s: np.ndarray

    def __post_init__(self) -> None:
        v = np.asarray(self.velocity_m_s, dtype=float)
        if not self.name:
            raise ValueError("species name cannot be blank")
        if not (math.isfinite(self.mass_kg) and self.mass_kg > 0):
            raise ValueError("mass_kg must be finite and positive")
        if not (math.isfinite(self.charge_c) and self.charge_c != 0):
            raise ValueError("charge_c must be finite and nonzero")
        if not (math.isfinite(self.density_m3) and self.density_m3 > 0):
            raise ValueError("density_m3 must be finite and positive")
        if not (math.isfinite(self.temperature_ev) and self.temperature_ev > 0):
            raise ValueError("temperature_ev must be finite and positive")
        if v.ndim != 2 or v.shape[1] != 3 or v.shape[0] < 2 or np.any(~np.isfinite(v)):
            raise ValueError("velocity_m_s must be a finite (N>=2, 3) array")


@dataclass(frozen=True)
class CollisionDiagnostics:
    pair_count: int
    skipped_strong_coupling_pairs: int
    max_pair_deflection_rad: float
    debye_length_m: float
    coulomb_log_min: float
    coulomb_log_max: float
    momentum_density_before: tuple[float, float, float]
    momentum_density_after: tuple[float, float, float]
    energy_density_before_j_m3: float
    energy_density_after_j_m3: float
    relative_momentum_error: float
    relative_energy_error: float
    particle_counts_before: dict[str, int]
    particle_counts_after: dict[str, int]


class MultiSpeciesCoulombMonteCarlo:
    """All-pairs stochastic small-angle Coulomb operator for local plasma cells."""

    def __init__(
        self,
        species: Sequence[CollisionSpecies],
        *,
        max_deflection_rad: float = 0.15,
        debye_length_m: float | None = None,
        coulomb_logarithm: float | None = None,
    ) -> None:
        if len(species) < 1:
            raise ValueError("at least one species is required")
        if not (math.isfinite(max_deflection_rad) and 0 < max_deflection_rad <= 0.25):
            raise ValueError("max_deflection_rad must lie in (0, 0.25]")
        names = [s.name for s in species]
        if len(set(names)) != len(names):
            raise ValueError("species names must be unique")
        self.species = [
            CollisionSpecies(
                name=s.name, mass_kg=s.mass_kg, charge_c=s.charge_c,
                density_m3=s.density_m3, temperature_ev=s.temperature_ev,
                velocity_m_s=np.asarray(s.velocity_m_s, dtype=float).copy(),
            ) for s in species
        ]
        self.max_deflection_rad = max_deflection_rad
        if coulomb_logarithm is not None and not (
            math.isfinite(coulomb_logarithm) and coulomb_logarithm > 0
        ):
            raise ValueError("coulomb_logarithm must be finite and positive")
        self.fixed_coulomb_logarithm = (
            None if coulomb_logarithm is None else float(coulomb_logarithm)
        )
        weights = np.array([s.density_m3 / s.velocity_m_s.shape[0] for s in self.species])
        if np.max(np.abs(weights - weights[0])) > 1.0e-10 * weights[0]:
            raise ValueError(
                "all species must use equal macro-particle number weights: density/N must match"
            )
        self.macro_weight_density_m3 = float(weights[0])
        if debye_length_m is not None:
            if not (math.isfinite(debye_length_m) and debye_length_m > 0):
                raise ValueError("debye_length_m must be finite and positive")
            self.debye_length_m = float(debye_length_m)
            self.debye_length_source = "user-supplied screening length"
        else:
            inv_lambda_sq = 0.0
            for s in self.species:
                inv_lambda_sq += s.density_m3 * s.charge_c**2 / (epsilon_0 * s.temperature_ev * e)
            self.debye_length_m = math.sqrt(1.0 / inv_lambda_sq)
            self.debye_length_source = "Maxwellian mixture Debye estimate from species temperatures"

    @staticmethod
    def _moments(species: Sequence[CollisionSpecies]) -> tuple[np.ndarray, float]:
        momentum = np.zeros(3, dtype=float)
        energy = 0.0
        for s in species:
            v = s.velocity_m_s
            momentum += s.mass_kg * s.density_m3 * np.mean(v, axis=0)
            energy += 0.5 * s.mass_kg * s.density_m3 * float(np.mean(np.sum(v * v, axis=1)))
        return momentum, energy

    @staticmethod
    def _rotate_relative(
        va: np.ndarray,
        vb: np.ndarray,
        ma: float,
        mb: float,
        theta_x: float,
        theta_y: float,
    ) -> tuple[np.ndarray, np.ndarray, float]:
        relative = va - vb
        speed = float(np.linalg.norm(relative))
        if speed == 0.0:
            return va, vb, 0.0
        axis = relative / speed
        # Stable orthonormal basis perpendicular to the relative-velocity axis.
        ref = np.array([0.0, 0.0, 1.0]) if abs(axis[2]) < 0.9 else np.array([0.0, 1.0, 0.0])
        e1 = np.cross(axis, ref)
        e1 /= np.linalg.norm(e1)
        e2 = np.cross(axis, e1)
        tangent = theta_x * e1 + theta_y * e2
        theta = math.hypot(theta_x, theta_y)
        if theta == 0.0:
            new_axis = axis
        else:
            new_axis = math.cos(theta) * axis + (math.sin(theta) / theta) * tangent
            new_axis /= np.linalg.norm(new_axis)
        new_relative = speed * new_axis
        center = (ma * va + mb * vb) / (ma + mb)
        va_new = center + (mb / (ma + mb)) * new_relative
        vb_new = center - (ma / (ma + mb)) * new_relative
        return va_new, vb_new, theta

    def _pair_variance(self, a: CollisionSpecies, b: CollisionSpecies, va: np.ndarray, vb: np.ndarray, dt_s: float) -> tuple[float, float]:
        relative_speed = float(np.linalg.norm(va - vb))
        if relative_speed <= 0.0:
            return 0.0, math.nan
        reduced_mass = a.mass_kg * b.mass_kg / (a.mass_kg + b.mass_kg)
        b90 = abs(a.charge_c * b.charge_c) / (
            4.0 * math.pi * epsilon_0 * reduced_mass * relative_speed**2
        )
        de_broglie = hbar / (2.0 * reduced_mass * relative_speed)
        b_min = max(b90, de_broglie)
        if self.fixed_coulomb_logarithm is not None:
            log_lambda = self.fixed_coulomb_logarithm
        else:
            log_lambda = (
                math.log(self.debye_length_m / b_min)
                if b_min < self.debye_length_m else -math.inf
            )
        if not math.isfinite(log_lambda) or log_lambda <= 0.0:
            return 0.0, log_lambda
        q_product_sq = (a.charge_c * b.charge_c) ** 2
        # d<theta^2>/dt from integrating (2*b_90/b)^2 over
        # n*g*2*pi*b db between b_min and the Debye screening length.
        # A fixed Coulomb logarithm is available for controlled analytic
        # Landau-Spitzer comparisons; the default remains velocity-dependent.
        variance = (
            self.macro_weight_density_m3 * q_product_sq * log_lambda * dt_s
            / (2.0 * math.pi * epsilon_0**2 * reduced_mass**2 * relative_speed**3)
        )
        return max(0.0, float(variance)), log_lambda

    def step(self, dt_s: float, *, seed: int = 0) -> CollisionDiagnostics:
        """Advance one local collision step. Rejects time steps with large kicks."""
        if not (math.isfinite(dt_s) and dt_s > 0):
            raise ValueError("dt_s must be finite and positive")
        rng = np.random.default_rng(seed)
        # Work on private copies: a rejected large-angle step must not leave a
        # partially advanced plasma state.
        working = [
            CollisionSpecies(
                name=s.name, mass_kg=s.mass_kg, charge_c=s.charge_c,
                density_m3=s.density_m3, temperature_ev=s.temperature_ev,
                velocity_m_s=s.velocity_m_s.copy(),
            ) for s in self.species
        ]
        before_momentum, before_energy = self._moments(working)
        counts_before = {s.name: int(s.velocity_m_s.shape[0]) for s in working}
        pair_count = 0
        skipped = 0
        max_kick = 0.0
        logs: list[float] = []
        for ia, a in enumerate(working):
            for ib in range(ia, len(working)):
                b = working[ib]
                va_arr, vb_arr = a.velocity_m_s, b.velocity_m_s
                if ia == ib:
                    index_pairs = ((i, j) for i in range(len(va_arr)) for j in range(i + 1, len(vb_arr)))
                else:
                    index_pairs = ((i, j) for i in range(len(va_arr)) for j in range(len(vb_arr)))
                for i, j in index_pairs:
                    va, vb = va_arr[i].copy(), vb_arr[j].copy()
                    variance, log_lambda = self._pair_variance(a, b, va, vb, dt_s)
                    if not math.isfinite(log_lambda) or log_lambda <= 0.0:
                        skipped += 1
                        continue
                    logs.append(log_lambda)
                    # Two independent transverse angular components; their
                    # summed variance is the integrated mean-square deflection.
                    sigma = math.sqrt(0.5 * variance)
                    dx, dy = rng.normal(0.0, sigma, size=2)
                    va_new, vb_new, kick = self._rotate_relative(
                        va, vb, a.mass_kg, b.mass_kg, float(dx), float(dy)
                    )
                    if kick > self.max_deflection_rad:
                        raise ValueError(
                            f"pair kick {kick:.3g} rad exceeds limit {self.max_deflection_rad:.3g}; reduce dt_s"
                        )
                    va_arr[i] = va_new
                    vb_arr[j] = vb_new
                    max_kick = max(max_kick, kick)
                    pair_count += 1
        after_momentum, after_energy = self._moments(working)
        momentum_reference = sum(
            s.mass_kg * s.density_m3
            * math.sqrt(float(np.mean(np.sum(s.velocity_m_s * s.velocity_m_s, axis=1))))
            for s in working
        )
        momentum_scale = max(float(np.linalg.norm(before_momentum)), momentum_reference, 1.0e-300)
        energy_scale = max(abs(before_energy), 1.0e-300)
        counts_after = {s.name: int(s.velocity_m_s.shape[0]) for s in working}
        if counts_before != counts_after:
            raise ArithmeticError("particle counts changed during collision step")
        self.species = working
        return CollisionDiagnostics(
            pair_count=pair_count,
            skipped_strong_coupling_pairs=skipped,
            max_pair_deflection_rad=max_kick,
            debye_length_m=self.debye_length_m,
            coulomb_log_min=float(min(logs)) if logs else math.nan,
            coulomb_log_max=float(max(logs)) if logs else math.nan,
            momentum_density_before=tuple(float(x) for x in before_momentum),
            momentum_density_after=tuple(float(x) for x in after_momentum),
            energy_density_before_j_m3=float(before_energy),
            energy_density_after_j_m3=float(after_energy),
            relative_momentum_error=float(np.linalg.norm(after_momentum - before_momentum) / momentum_scale),
            relative_energy_error=float(abs(after_energy - before_energy) / energy_scale),
            particle_counts_before=counts_before,
            particle_counts_after=counts_after,
        )


def maxwellian_velocity_samples(
    count: int,
    *,
    mass_kg: float,
    temperature_ev: float,
    drift_m_s: tuple[float, float, float] = (0.0, 0.0, 0.0),
    seed: int = 0,
) -> np.ndarray:
    """Draw non-relativistic 3-D Maxwellian velocities for operator benchmarks."""
    if count < 2 or mass_kg <= 0 or temperature_ev <= 0:
        raise ValueError("count >= 2, mass_kg > 0, and temperature_ev > 0 are required")
    rng = np.random.default_rng(seed)
    sigma = math.sqrt(temperature_ev * e / mass_kg)
    return rng.normal(0.0, sigma, size=(count, 3)) + np.asarray(drift_m_s, dtype=float)
