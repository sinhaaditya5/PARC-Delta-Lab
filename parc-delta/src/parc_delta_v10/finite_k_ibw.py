"""Finite-parallel-wavenumber kinetic IBW susceptibility for PARC-Delta.

This module extends the published strictly-perpendicular collisionless model
with k_parallel != 0. Thermal electrons/protons use the Maxwellian Harris
susceptibility and the energetic alpha component uses a gyrotropic ring with
lognormal perpendicular-energy spread and Maxwellian parallel spread.

Important scope boundary: collisions are not included in this module. The
velocity-space response uses the collisionless Landau contour via the plasma
dispersion function. A conserving multi-species Landau collision operator is a
separate implementation and validation gate; it must not be replaced by a
constant-frequency damping term and labelled Coulomb collisions.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import math
from typing import Callable

import numpy as np
from scipy.constants import e, epsilon_0, m_e, m_p
from scipy.optimize import least_squares, root
from scipy.special import ive, jv, jvp, roots_hermite, wofz

from .linear_ibw import (
    CODATA_ALPHA_TO_PROTON_MASS_RATIO,
    LAPDReferenceCase,
    CollisionlessIBWModel,
    derive_plasma,
)


def plasma_dispersion_zeta(zeta: complex) -> complex:
    """Fried-Conte Z function with Landau analytic continuation: Z=i√π w(z)."""
    return complex(1j * math.sqrt(math.pi) * wofz(complex(zeta)))


def plasma_dispersion_zeta_derivative(zeta: complex) -> complex:
    """Derivative Z'(z), evaluated asymptotically for large |z| to avoid cancellation."""
    z = complex(zeta)
    if abs(z) > 8.0:
        # Differentiate the large-|z| expansion of Z. In the upper-half-plane
        # this is the standard Landau-contour asymptotic; for the large real
        # detunings used here the exponentially small continuation term is
        # below double precision.
        inv = 1.0 / (z * z)
        return complex(
            inv
            + 1.5 * inv**2
            + 3.75 * inv**3
            + 13.125 * inv**4
            + 59.0625 * inv**5
            + 324.84375 * inv**6
        )
    return complex(-2.0 * (1.0 + z * plasma_dispersion_zeta(z)))


@dataclass(frozen=True)
class FiniteParallelCase:
    """Finite-k_parallel kinetic parameters around the v1.2 LAPD benchmark."""
    plasma: LAPDReferenceCase = LAPDReferenceCase(
        alpha_mass_ratio_proton=CODATA_ALPHA_TO_PROTON_MASS_RATIO,
        k_perp_m_inv=245.143,
    )
    k_parallel_m_inv: float = 0.0
    alpha_parallel_temperature_ev: float = 0.0
    alpha_perp_energy_cv: float = 0.0
    alpha_energy_quadrature_order: int = 64
    alpha_harmonics: int = 40
    proton_harmonics: int = 40
    electron_harmonics: int = 4

    def __post_init__(self) -> None:
        if not math.isfinite(self.k_parallel_m_inv) or self.k_parallel_m_inv < 0:
            raise ValueError("k_parallel_m_inv must be finite and non-negative")
        if not math.isfinite(self.alpha_parallel_temperature_ev) or self.alpha_parallel_temperature_ev < 0:
            raise ValueError("alpha_parallel_temperature_ev must be finite and non-negative")
        if not math.isfinite(self.alpha_perp_energy_cv) or not 0 <= self.alpha_perp_energy_cv <= 0.20:
            raise ValueError("alpha_perp_energy_cv must lie in [0, 0.20]")
        if not 8 <= self.alpha_energy_quadrature_order <= 1024:
            raise ValueError("alpha_energy_quadrature_order must lie in [8, 1024]")
        if self.alpha_perp_energy_cv > 0.10 and self.alpha_energy_quadrature_order < 512:
            raise ValueError("alpha_perp_energy_cv > 0.10 requires quadrature order >= 512")
        for name in ("alpha_harmonics", "proton_harmonics", "electron_harmonics"):
            if getattr(self, name) < 1:
                raise ValueError(f"{name} must be >= 1")

    @property
    def k_total_m_inv(self) -> float:
        return math.hypot(self.plasma.k_perp_m_inv, self.k_parallel_m_inv)

    @property
    def k_parallel_over_perp(self) -> float:
        return self.k_parallel_m_inv / self.plasma.k_perp_m_inv


@dataclass(frozen=True)
class KineticMode:
    omega_real_over_omega_p: float
    gamma_over_omega_p: float
    normalized_residual: float
    solver_success: bool
    solver_message: str


class FiniteKParallelIBWModel:
    """Collisionless electrostatic kinetic dispersion with finite k_parallel."""

    def __init__(self, case: FiniteParallelCase):
        self.case = case
        self.plasma_case = case.plasma
        self.plasma = derive_plasma(case.plasma)
        self.omega_p = self.plasma.proton_cyclotron_s_inv
        self.omega_alpha = self.plasma.alpha_cyclotron_s_inv
        self.k_perp = case.plasma.k_perp_m_inv
        self.k_parallel = case.k_parallel_m_inv
        self.k_total = case.k_total_m_inv
        self.alpha_mass = case.plasma.alpha_mass_ratio_proton * m_p
        self.alpha_charge = 2.0 * e
        self.alpha_density = self.plasma.alpha_density_m3
        self.alpha_omega_ps_sq = (
            self.alpha_density * self.alpha_charge**2 / (epsilon_0 * self.alpha_mass)
        )
        self._energy_nodes, self._energy_weights = self._make_energy_quadrature()
        self._vperp_nodes = np.sqrt(2.0 * self._energy_nodes * 1.0e3 * e / self.alpha_mass)
        self._j_cache: dict[int, tuple[float, float]] = {}
        for harmonic in range(-case.alpha_harmonics, case.alpha_harmonics + 1):
            j2_avg = 0.0
            jjprime_over_v_avg = 0.0
            for weight, vperp in zip(self._energy_weights, self._vperp_nodes):
                lam = self.k_perp * vperp / self.omega_alpha
                jn = float(jv(harmonic, lam))
                derivative = float(jvp(harmonic, lam, 1))
                j2_avg += float(weight) * jn * jn
                jjprime_over_v_avg += float(weight) * jn * derivative / vperp
            self._j_cache[harmonic] = (j2_avg, jjprime_over_v_avg)

    def _make_energy_quadrature(self) -> tuple[np.ndarray, np.ndarray]:
        cv = self.case.alpha_perp_energy_cv
        mean = self.plasma_case.alpha_ring_energy_kev
        if cv == 0.0:
            return np.array([mean]), np.array([1.0])
        variance_log = math.log1p(cv * cv)
        sigma_log = math.sqrt(variance_log)
        mu_log = math.log(mean) - 0.5 * variance_log
        nodes, weights = roots_hermite(self.case.alpha_energy_quadrature_order)
        energy = np.exp(mu_log + math.sqrt(2.0) * sigma_log * nodes)
        return energy, weights / math.sqrt(math.pi)

    @staticmethod
    def _species_thermal_susceptibility(
        omega: complex,
        *,
        density_m3: float,
        charge_c: float,
        mass_kg: float,
        temperature_ev: float,
        cyclotron_frequency: float,
        k_perp: float,
        k_parallel: float,
        k_total: float,
        harmonics: int,
    ) -> complex:
        """Maxwellian Harris susceptibility; exact perpendicular limit when k||=0."""
        if temperature_ev <= 0 or density_m3 <= 0 or harmonics < 1:
            raise ValueError("thermal species parameters must be positive")
        omega_ps_sq = density_m3 * charge_c**2 / (epsilon_0 * mass_kg)
        temperature_j = temperature_ev * e
        thermal_speed = math.sqrt(2.0 * temperature_j / mass_kg)
        debye_sq = epsilon_0 * temperature_j / (density_m3 * charge_c**2)
        b = (k_perp * thermal_speed / (math.sqrt(2.0) * cyclotron_frequency)) ** 2

        if k_parallel == 0.0:
            total = 0.0 + 0.0j
            for n in range(1, harmonics + 1):
                gamma_n = float(ive(n, b))
                pole = (n * cyclotron_frequency) ** 2
                total -= (2.0 * omega_ps_sq / (b * (omega * omega - pole))) * (n * n * gamma_n)
            return complex(total)

        prefactor = 1.0 / (k_total * k_total * debye_sq)
        harmonic_sum = 0.0 + 0.0j
        for n in range(-harmonics, harmonics + 1):
            gamma_n = float(ive(abs(n), b))
            zeta = (omega - n * cyclotron_frequency) / (k_parallel * thermal_speed)
            # Equivalent Harris form, written term-by-term to reduce cancellation
            # in the k_parallel -> 0 asymptotic limit.
            harmonic_sum += gamma_n * (
                1.0 + omega * plasma_dispersion_zeta(zeta) / (k_parallel * thermal_speed)
            )
        return complex(prefactor * harmonic_sum)

    def proton_susceptibility(self, omega: complex) -> complex:
        return self._species_thermal_susceptibility(
            omega,
            density_m3=self.plasma_case.proton_density_m3,
            charge_c=e,
            mass_kg=m_p,
            temperature_ev=self.plasma_case.proton_temperature_ev,
            cyclotron_frequency=self.omega_p,
            k_perp=self.k_perp,
            k_parallel=self.k_parallel,
            k_total=self.k_total,
            harmonics=self.case.proton_harmonics,
        )

    def electron_susceptibility(self, omega: complex) -> complex:
        return self._species_thermal_susceptibility(
            omega,
            density_m3=self.plasma.electron_density_m3,
            charge_c=-e,
            mass_kg=m_e,
            temperature_ev=self.plasma_case.electron_temperature_ev,
            cyclotron_frequency=e * self.plasma_case.magnetic_field_t / m_e,
            k_perp=self.k_perp,
            k_parallel=self.k_parallel,
            k_total=self.k_total,
            harmonics=self.case.electron_harmonics,
        )

    def alpha_susceptibility(self, omega: complex) -> complex:
        """Gyrotropic alpha ring with perpendicular-energy and parallel spreads.

        The radial velocity distribution is represented by a positive-energy
        lognormal quadrature. The parallel distribution is Maxwellian. The
        velocity integral is analytic in v_parallel through Z and Z', retaining
        Landau-contour continuation for damped as well as growing roots.
        """
        omega = complex(omega)
        total = 0.0 + 0.0j
        vth_parallel = math.sqrt(
            2.0 * self.case.alpha_parallel_temperature_ev * e / self.alpha_mass
        ) if self.case.alpha_parallel_temperature_ev > 0 else 0.0

        for n in range(-self.case.alpha_harmonics, self.case.alpha_harmonics + 1):
            j2_average, jjprime_over_v_average = self._j_cache[n]
            detuning = omega - n * self.omega_alpha
            if self.k_parallel == 0.0 or vth_parallel == 0.0:
                # Parallel cold-beam limit. For k||=0 the first term vanishes.
                response = (
                    -(self.k_parallel**2) * j2_average / (detuning * detuning)
                    - (2.0 * n * self.k_perp * jjprime_over_v_average) / detuning
                )
            else:
                zeta = detuning / (self.k_parallel * vth_parallel)
                z_value = plasma_dispersion_zeta(zeta)
                z_derivative = plasma_dispersion_zeta_derivative(zeta)
                parallel_term = -j2_average * z_derivative / (vth_parallel**2)
                perpendicular_term = (
                    2.0 * n * self.k_perp * jjprime_over_v_average
                    * z_value / (self.k_parallel * vth_parallel)
                )
                response = parallel_term + perpendicular_term
            total += response
        return complex((self.alpha_omega_ps_sq / (self.k_total**2)) * total)

    def dispersion(self, omega_over_omega_p: complex) -> complex:
        omega = complex(omega_over_omega_p) * self.omega_p
        return complex(
            1.0
            + self.proton_susceptibility(omega)
            + self.electron_susceptibility(omega)
            + self.alpha_susceptibility(omega)
        )

    def solve_mode(
        self,
        initial_omega_over_omega_p: complex,
        *,
        residual_tolerance: float = 1.0e-7,
    ) -> KineticMode:
        """Solve D(omega,k)=0 with the Landau analytic continuation."""
        initial = complex(initial_omega_over_omega_p)
        if not (math.isfinite(initial.real) and math.isfinite(initial.imag)):
            raise ValueError("initial_omega_over_omega_p must be finite")

        def residual(vector: np.ndarray) -> list[float]:
            omega = complex(float(vector[0]), float(vector[1]))
            value = self.dispersion(omega)
            return [float(value.real), float(value.imag)]

        solution = root(
            residual,
            [initial.real, initial.imag],
            method="hybr",
            options={"xtol": 1.0e-10},
        )
        omega = complex(float(solution.x[0]), float(solution.x[1]))
        residual_norm = abs(self.dispersion(omega))
        if residual_norm > residual_tolerance:
            refined = least_squares(
                residual,
                solution.x,
                method="lm",
                xtol=1.0e-14,
                ftol=1.0e-14,
                gtol=1.0e-14,
                max_nfev=1000,
            )
            omega = complex(float(refined.x[0]), float(refined.x[1]))
            residual_norm = abs(self.dispersion(omega))
        if not (math.isfinite(omega.real) and math.isfinite(omega.imag) and omega.real > 0):
            raise ArithmeticError(f"finite-k mode solver returned invalid root {omega!r}")
        if residual_norm > residual_tolerance:
            raise ArithmeticError(
                f"finite-k mode residual {residual_norm:.3e} exceeds {residual_tolerance:.3e}; "
                f"solver={solution.message}"
            )
        return KineticMode(
            omega_real_over_omega_p=omega.real,
            gamma_over_omega_p=omega.imag,
            normalized_residual=float(residual_norm),
            solver_success=bool(solution.success),
            solver_message=str(solution.message),
        )

    def response_breakdown(self, omega_over_omega_p: complex) -> dict[str, complex]:
        omega = complex(omega_over_omega_p) * self.omega_p
        return {
            "proton": self.proton_susceptibility(omega),
            "electron": self.electron_susceptibility(omega),
            "alpha": self.alpha_susceptibility(omega),
        }


def make_reference_case(
    *,
    k_parallel_over_perp: float = 0.0,
    alpha_parallel_temperature_ev: float = 0.0,
    alpha_perp_energy_cv: float = 0.0,
    energy_quadrature_order: int = 64,
    alpha_mass_ratio_proton: float = CODATA_ALPHA_TO_PROTON_MASS_RATIO,
) -> FiniteParallelCase:
    """Construct the CODATA-mass crossing case from the v1.2 reference setup."""
    if not math.isfinite(k_parallel_over_perp) or k_parallel_over_perp < 0:
        raise ValueError("k_parallel_over_perp must be finite and non-negative")
    # Recompute the physical-mass exact crossing from the v1.2 thermal model;
    # do not freeze a rounded wavenumber into the finite-k calculation.
    base_seed = LAPDReferenceCase(
        alpha_mass_ratio_proton=alpha_mass_ratio_proton,
        k_perp_m_inv=251.74,
    )
    crossing = CollisionlessIBWModel(base_seed).exact_thermal_crossing()
    base = replace(
        base_seed,
        k_perp_m_inv=float(crossing["k_perp_exact_thermal_crossing_m_inv"]),
    )
    return FiniteParallelCase(
        plasma=base,
        k_parallel_m_inv=k_parallel_over_perp * base.k_perp_m_inv,
        alpha_parallel_temperature_ev=alpha_parallel_temperature_ev,
        alpha_perp_energy_cv=alpha_perp_energy_cv,
        alpha_energy_quadrature_order=energy_quadrature_order,
    )
