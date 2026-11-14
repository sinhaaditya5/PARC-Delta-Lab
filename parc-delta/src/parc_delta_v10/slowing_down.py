"""Test-particle alpha slowing-down using Maxwellian Rosenbluth coefficients.

The field species are stationary, isotropic Maxwellian reservoirs. The test
alpha population does not back-react on them. This is the standard
non-relativistic test-particle Landau/Fokker-Planck approximation, not a
conserving field-particle multispecies operator.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Sequence

import numpy as np
from scipy.constants import c, e, epsilon_0
from scipy.special import erf


@dataclass(frozen=True)
class MaxwellianFieldSpecies:
    name: str
    mass_kg: float
    charge_c: float
    density_m3: float
    temperature_ev: float

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("field species name cannot be blank")
        for key, val in (("mass_kg", self.mass_kg), ("density_m3", self.density_m3), ("temperature_ev", self.temperature_ev)):
            if not math.isfinite(val) or val <= 0.0:
                raise ValueError(f"{key} must be finite and positive")
        if not math.isfinite(self.charge_c) or self.charge_c == 0.0:
            raise ValueError("charge_c must be finite and nonzero")


@dataclass(frozen=True)
class SpeciesCoefficients:
    name: str
    k_s_inv: np.ndarray
    d_parallel_kg2_m2_s: np.ndarray
    d_perp_kg2_m2_s: np.ndarray


@dataclass(frozen=True)
class SlowingDownSnapshot:
    time_s: float
    mean_energy_ev: float
    median_energy_ev: float
    q05_energy_ev: float
    q95_energy_ev: float
    mean_speed_m_s: float
    max_speed_over_c: float


@dataclass(frozen=True)
class SlowingDownResult:
    snapshots: tuple[SlowingDownSnapshot, ...]
    deposited_energy_j_m3: dict[str, float]
    final_power_density_w_m3: dict[str, float]
    initial_energy_density_j_m3: float
    final_energy_density_j_m3: float
    expected_alpha_energy_change_j_m3: float
    actual_alpha_energy_change_j_m3: float
    energy_budget_residual_j_m3: float
    relative_energy_budget_residual: float
    steps: int
    dt_s: float
    marker_count: int
    alpha_density_m3: float
    coulomb_logarithm: float


def chandrasekhar_g(x: np.ndarray | float) -> np.ndarray:
    """Chandrasekhar function G(x)=[erf(x)-2*x*exp(-x²)/sqrt(pi)]/(2*x²).

    A series is used near zero to avoid catastrophic cancellation.
    """
    xa = np.asarray(x, dtype=float)
    if np.any(~np.isfinite(xa)) or np.any(xa < 0.0):
        raise ValueError("x must be finite and non-negative")
    out = np.empty_like(xa)
    small = xa < 1.0e-3
    xs = xa[small]
    out[small] = (2.0 * xs / (3.0 * math.sqrt(math.pi))
                  - 2.0 * xs**3 / (5.0 * math.sqrt(math.pi))
                  + xs**5 / (7.0 * math.sqrt(math.pi)))
    xl = xa[~small]
    out[~small] = (erf(xl) - 2.0 * xl * np.exp(-xl * xl) / math.sqrt(math.pi)) / (2.0 * xl * xl)
    return out


def rosenbluth_test_particle_coefficients(
    speed_m_s: np.ndarray,
    *,
    test_mass_kg: float,
    test_charge_c: float,
    field_species: MaxwellianFieldSpecies,
    coulomb_logarithm: float,
) -> SpeciesCoefficients:
    """Return ASCOT/Rosenbluth test-particle Langevin coefficients.

    The SDE is written for momentum p=m*v:
      dp = -K p dt + sqrt(2 D_parallel) b_hat dW_parallel
           + sqrt(2 D_perp) (I-b_hat b_hat) dW_perp.

    K has units s^-1; D coefficients have units kg^2 m^2 s^-1.
    """
    v = np.asarray(speed_m_s, dtype=float)
    if v.ndim != 1 or np.any(~np.isfinite(v)) or np.any(v < 0.0):
        raise ValueError("speed_m_s must be a finite non-negative vector")
    if not (math.isfinite(test_mass_kg) and test_mass_kg > 0.0):
        raise ValueError("test_mass_kg must be positive")
    if not math.isfinite(test_charge_c) or test_charge_c == 0.0:
        raise ValueError("test_charge_c must be nonzero")
    if not (math.isfinite(coulomb_logarithm) and coulomb_logarithm > 0.0):
        raise ValueError("coulomb_logarithm must be positive")

    vb = math.sqrt(2.0 * field_species.temperature_ev * e / field_species.mass_kg)
    x = v / vb
    gx = chandrasekhar_g(x)
    gamma_b = (
        field_species.density_m3 * test_charge_c**2 * field_species.charge_c**2
        * coulomb_logarithm / (4.0 * math.pi * epsilon_0**2)
    )

    g_over_v = np.empty_like(v)
    nonzero = v > 0.0
    g_over_v[nonzero] = gx[nonzero] / v[nonzero]
    g_over_v[~nonzero] = 2.0 / (3.0 * math.sqrt(math.pi) * vb)

    k = (1.0 + test_mass_kg / field_species.mass_kg) * (
        2.0 * gamma_b / (test_mass_kg**2 * vb**2)
    ) * g_over_v

    d_parallel = np.empty_like(v)
    d_perp = np.empty_like(v)
    d_parallel[nonzero] = gamma_b * gx[nonzero] / v[nonzero]
    erf_minus_g = erf(x) - gx
    d_perp[nonzero] = 0.5 * gamma_b * erf_minus_g[nonzero] / v[nonzero]
    zero_limit = 2.0 * gamma_b / (3.0 * math.sqrt(math.pi) * vb)
    d_parallel[~nonzero] = zero_limit
    d_perp[~nonzero] = zero_limit

    return SpeciesCoefficients(field_species.name, k, d_parallel, d_perp)


def expected_kinetic_energy_rate_per_marker_j_s(
    speed_m_s: np.ndarray,
    *,
    test_mass_kg: float,
    coefficients: SpeciesCoefficients,
) -> np.ndarray:
    """Itô generator's expected dE/dt for one field species."""
    v = np.asarray(speed_m_s, dtype=float)
    return (
        -coefficients.k_s_inv * test_mass_kg * v**2
        + (coefficients.d_parallel_kg2_m2_s + 2.0 * coefficients.d_perp_kg2_m2_s) / test_mass_kg
    )


class RosenbluthSlowingDownSolver:
    """Euler-Maruyama solver for a test alpha ensemble in fixed Maxwellian baths."""

    def __init__(
        self,
        *,
        test_mass_kg: float,
        test_charge_c: float,
        field_species: Sequence[MaxwellianFieldSpecies],
        coulomb_logarithm: float,
        max_dt_k: float = 0.02,
        max_speed_fraction_c: float = 0.1,
    ) -> None:
        if not field_species:
            raise ValueError("at least one field species is required")
        if len({x.name for x in field_species}) != len(field_species):
            raise ValueError("field species names must be unique")
        if not (math.isfinite(max_dt_k) and 0.0 < max_dt_k <= 0.1):
            raise ValueError("max_dt_k must lie in (0, 0.1]")
        if not (math.isfinite(max_speed_fraction_c) and 0.0 < max_speed_fraction_c < 1.0):
            raise ValueError("max_speed_fraction_c must lie in (0, 1)")
        if not (math.isfinite(coulomb_logarithm) and coulomb_logarithm > 0.0):
            raise ValueError("coulomb_logarithm must be positive")
        self.test_mass_kg = float(test_mass_kg)
        self.test_charge_c = float(test_charge_c)
        self.field_species = tuple(field_species)
        self.coulomb_logarithm = float(coulomb_logarithm)
        self.max_dt_k = float(max_dt_k)
        self.max_speed_fraction_c = float(max_speed_fraction_c)

    def _coefficients(self, velocities_m_s: np.ndarray) -> list[SpeciesCoefficients]:
        speed = np.linalg.norm(velocities_m_s, axis=1)
        return [
            rosenbluth_test_particle_coefficients(
                speed,
                test_mass_kg=self.test_mass_kg,
                test_charge_c=self.test_charge_c,
                field_species=field,
                coulomb_logarithm=self.coulomb_logarithm,
            )
            for field in self.field_species
        ]

    def step(
        self,
        velocities_m_s: np.ndarray,
        dt_s: float,
        *,
        rng: np.random.Generator,
    ) -> tuple[np.ndarray, dict[str, float]]:
        """Advance markers one step; return velocities and per-species Q (W/m3)/n_alpha.

        The returned power is per unit alpha number density, i.e. W per alpha
        particle. A positive value is energy deposited into that field species.
        """
        v = np.asarray(velocities_m_s, dtype=float)
        if v.ndim != 2 or v.shape[1] != 3 or v.shape[0] < 1 or np.any(~np.isfinite(v)):
            raise ValueError("velocities_m_s must be finite with shape (N,3)")
        if not (math.isfinite(dt_s) and dt_s > 0.0):
            raise ValueError("dt_s must be finite and positive")
        speed = np.linalg.norm(v, axis=1)
        if np.max(speed, initial=0.0) / c >= self.max_speed_fraction_c:
            raise ValueError("non-relativistic solver speed limit exceeded")
        coeffs = self._coefficients(v)
        k_total = np.sum([x.k_s_inv for x in coeffs], axis=0)
        if float(np.max(k_total, initial=0.0)) * dt_s > self.max_dt_k:
            raise ValueError("dt_s violates max_dt_k; reduce the timestep")

        deposited_power_per_alpha: dict[str, float] = {}
        for field, coef in zip(self.field_species, coeffs):
            d_e_dt = expected_kinetic_energy_rate_per_marker_j_s(
                speed, test_mass_kg=self.test_mass_kg, coefficients=coef
            )
            deposited_power_per_alpha[field.name] = float(-np.mean(d_e_dt))

        p = self.test_mass_kg * v
        speed_p = np.linalg.norm(p, axis=1)
        direction = np.zeros_like(p)
        nz = speed_p > 0.0
        direction[nz] = p[nz] / speed_p[nz, None]
        direction[~nz, 0] = 1.0

        xi = rng.normal(size=v.shape)
        xi_parallel = np.sum(xi * direction, axis=1)
        xi_perp = xi - xi_parallel[:, None] * direction
        d_parallel_total = np.sum([x.d_parallel_kg2_m2_s for x in coeffs], axis=0)
        d_perp_total = np.sum([x.d_perp_kg2_m2_s for x in coeffs], axis=0)
        p_new = (
            p - (k_total * dt_s)[:, None] * p
            + np.sqrt(2.0 * d_parallel_total * dt_s)[:, None] * xi_parallel[:, None] * direction
            + np.sqrt(2.0 * d_perp_total * dt_s)[:, None] * xi_perp
        )
        return p_new / self.test_mass_kg, deposited_power_per_alpha

    def run(
        self,
        initial_velocities_m_s: np.ndarray,
        *,
        dt_s: float,
        steps: int,
        alpha_density_m3: float,
        seed: int = 0,
        record_every: int = 100,
    ) -> SlowingDownResult:
        """Integrate an alpha ensemble and estimate energy deposition to each bath."""
        v = np.asarray(initial_velocities_m_s, dtype=float).copy()
        if v.ndim != 2 or v.shape[1] != 3 or v.shape[0] < 1 or np.any(~np.isfinite(v)):
            raise ValueError("initial_velocities_m_s must be finite with shape (N,3)")
        if not isinstance(steps, int) or steps < 1:
            raise ValueError("steps must be a positive integer")
        if not isinstance(record_every, int) or record_every < 1:
            raise ValueError("record_every must be a positive integer")
        if not (math.isfinite(alpha_density_m3) and alpha_density_m3 > 0.0):
            raise ValueError("alpha_density_m3 must be positive")
        if not (math.isfinite(dt_s) and dt_s > 0.0):
            raise ValueError("dt_s must be positive")
        if np.max(np.linalg.norm(v, axis=1), initial=0.0) / c >= self.max_speed_fraction_c:
            raise ValueError("initial alpha speed exceeds non-relativistic solver limit")

        rng = np.random.default_rng(seed)
        initial_energy = 0.5 * self.test_mass_kg * np.sum(v * v, axis=1)
        initial_density = alpha_density_m3 * float(np.mean(initial_energy))
        cumulative_deposition = {field.name: 0.0 for field in self.field_species}
        snapshots: list[SlowingDownSnapshot] = []
        final_power = {field.name: 0.0 for field in self.field_species}

        def snapshot(t: float) -> SlowingDownSnapshot:
            energy_ev = 0.5 * self.test_mass_kg * np.sum(v * v, axis=1) / e
            speed = np.linalg.norm(v, axis=1)
            return SlowingDownSnapshot(
                time_s=float(t),
                mean_energy_ev=float(np.mean(energy_ev)),
                median_energy_ev=float(np.median(energy_ev)),
                q05_energy_ev=float(np.quantile(energy_ev, 0.05)),
                q95_energy_ev=float(np.quantile(energy_ev, 0.95)),
                mean_speed_m_s=float(np.mean(speed)),
                max_speed_over_c=float(np.max(speed) / c),
            )

        snapshots.append(snapshot(0.0))
        for istep in range(1, steps + 1):
            v, power_per_alpha = self.step(v, dt_s, rng=rng)
            for name, power in power_per_alpha.items():
                q_density = alpha_density_m3 * power
                cumulative_deposition[name] += q_density * dt_s
                final_power[name] = q_density
            if istep % record_every == 0 or istep == steps:
                snapshots.append(snapshot(istep * dt_s))

        final_energy = 0.5 * self.test_mass_kg * np.sum(v * v, axis=1)
        final_density = alpha_density_m3 * float(np.mean(final_energy))
        expected_change = -sum(cumulative_deposition.values())
        actual_change = final_density - initial_density
        residual = actual_change - expected_change
        scale = max(abs(actual_change), abs(expected_change), 1.0e-30)
        return SlowingDownResult(
            snapshots=tuple(snapshots),
            deposited_energy_j_m3=cumulative_deposition,
            final_power_density_w_m3=final_power,
            initial_energy_density_j_m3=initial_density,
            final_energy_density_j_m3=final_density,
            expected_alpha_energy_change_j_m3=expected_change,
            actual_alpha_energy_change_j_m3=actual_change,
            energy_budget_residual_j_m3=residual,
            relative_energy_budget_residual=abs(residual) / scale,
            steps=steps,
            dt_s=dt_s,
            marker_count=v.shape[0],
            alpha_density_m3=alpha_density_m3,
            coulomb_logarithm=self.coulomb_logarithm,
        )
