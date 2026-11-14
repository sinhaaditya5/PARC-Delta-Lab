"""Collisionless, strictly-perpendicular proton--alpha IBW benchmark.

This module implements the reduced linear kinetic model in Qin & Fisch,
"Thresholdless IBW Emission and Alpha-to-Thermal-Ion Energy Channeling via
Pole Resonance of Fusion-Product Ions" (arXiv:2609.07732v2, 2026).

Scope is intentionally narrow:
- homogeneous, uniform-B plasma;
- electrostatic perturbation with k_parallel = 0;
- Maxwellian thermal electrons/protons;
- perpendicular alpha ring, optionally with a finite lognormal energy width;
- collisionless linear dispersion plus a separately labelled damped-alpha-pole proxy.

It is a reproducibility benchmark, not a p-11B reactor model, not a nonlinear
kinetic solver, and not a prediction of irreversible proton heating.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import csv
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from scipy.constants import e, epsilon_0, m_e, m_p
from scipy.optimize import brentq, root
from scipy.special import ive, jv, jvp
from scipy.special import roots_hermite


CODATA_ALPHA_TO_PROTON_MASS_RATIO = 3.972599690252


@dataclass(frozen=True)
class LAPDReferenceCase:
    """Reference parameters used for the published LAPD proton--alpha case.

    The default mass ratio 4.0 preserves the commonly used approximation
    Omega_alpha/Omega_p = 1/2. Set alpha_mass_ratio_proton to the CODATA
    value (3.972599690252) to use the physical alpha-particle mass ratio.
    """

    magnetic_field_t: float = 0.05
    proton_density_m3: float = 1.0e17
    alpha_to_proton_density: float = 0.02
    alpha_mass_ratio_proton: float = 4.0
    proton_temperature_ev: float = 5.0
    electron_temperature_ev: float = 10.0
    alpha_ring_energy_kev: float = 24.0
    k_perp_m_inv: float = 251.74
    alpha_harmonic: int = 3
    proton_harmonics: int = 40
    electron_harmonics: int = 4
    alpha_harmonics: int = 40

    def __post_init__(self) -> None:
        positive = {
            "magnetic_field_t": self.magnetic_field_t,
            "proton_density_m3": self.proton_density_m3,
            "alpha_to_proton_density": self.alpha_to_proton_density,
            "alpha_mass_ratio_proton": self.alpha_mass_ratio_proton,
            "proton_temperature_ev": self.proton_temperature_ev,
            "electron_temperature_ev": self.electron_temperature_ev,
            "alpha_ring_energy_kev": self.alpha_ring_energy_kev,
            "k_perp_m_inv": self.k_perp_m_inv,
        }
        for key, val in positive.items():
            if not math.isfinite(val) or val <= 0:
                raise ValueError(f"{key} must be finite and positive")
        for key in ("alpha_harmonic", "proton_harmonics", "electron_harmonics", "alpha_harmonics"):
            if getattr(self, key) < 1:
                raise ValueError(f"{key} must be >= 1")


@dataclass(frozen=True)
class DerivedPlasma:
    alpha_density_m3: float
    alpha_mass_ratio_proton: float
    electron_density_m3: float
    proton_cyclotron_s_inv: float
    alpha_cyclotron_s_inv: float
    electron_cyclotron_s_inv: float
    omega_pp_sq_over_omega_p_sq: float
    omega_pa_sq_over_omega_p_sq: float
    omega_pe_sq_over_omega_p_sq: float
    b_proton: float
    b_electron: float
    alpha_ring_lambda: float
    alpha_pole_z: float
    alpha_pole_frequency_over_omega_p: float


@dataclass(frozen=True)
class LinearModeResult:
    z_real: float
    z_imag: float
    omega_real_over_omega_p: float
    gamma_over_omega_p: float
    omega_real_s_inv: float
    growth_rate_s_inv: float
    normalized_dispersion_residual: float
    local_z_real: float
    local_z_imag: float
    thermal_root_z: float
    regular_root_z: float
    alpha_pole_z: float
    detuning_z: float
    selected_residue_normalized: float
    regular_dispersion_derivative: float
    discriminant_real: float
    critical_alpha_density_fraction_of_reference: float | None


@dataclass(frozen=True)
class BroadenedModeResult:
    alpha_broadening_over_omega_p: float
    omega_real_over_omega_p: float
    gamma_over_omega_p: float
    normalized_dispersion_residual: float
    is_growing: bool


@dataclass(frozen=True)
class PowerPartition:
    proton_fraction_of_alpha_loss: float
    electron_fraction_of_alpha_loss: float
    field_fraction_of_alpha_loss: float
    proton_weight: float
    electron_weight: float
    alpha_loss_weight: float
    closure_sum: float


def derive_plasma(case: LAPDReferenceCase) -> DerivedPlasma:
    """Compute dimensionless parameters and cyclotron/plasma frequencies."""
    alpha_n = case.proton_density_m3 * case.alpha_to_proton_density
    electron_n = case.proton_density_m3 + 2.0 * alpha_n
    alpha_mass = case.alpha_mass_ratio_proton * m_p

    omega_p = e * case.magnetic_field_t / m_p
    omega_a = 2.0 * e * case.magnetic_field_t / alpha_mass
    omega_e = e * case.magnetic_field_t / m_e

    omega_pp_sq = case.proton_density_m3 * e**2 / (epsilon_0 * m_p)
    omega_pa_sq = alpha_n * (2.0 * e) ** 2 / (epsilon_0 * alpha_mass)
    omega_pe_sq = electron_n * e**2 / (epsilon_0 * m_e)

    v_tp = math.sqrt(case.proton_temperature_ev * e / m_p)
    v_te = math.sqrt(case.electron_temperature_ev * e / m_e)
    rho_p = v_tp / omega_p
    rho_e = v_te / omega_e
    b_p = case.k_perp_m_inv**2 * rho_p**2
    b_e = case.k_perp_m_inv**2 * rho_e**2

    alpha_mass_kg = alpha_mass
    alpha_ring_speed = math.sqrt(2.0 * case.alpha_ring_energy_kev * 1.0e3 * e / alpha_mass_kg)
    lam = case.k_perp_m_inv * alpha_ring_speed / omega_a
    pole_z = (case.alpha_harmonic * omega_a / omega_p) ** 2

    return DerivedPlasma(
        alpha_density_m3=alpha_n,
        alpha_mass_ratio_proton=case.alpha_mass_ratio_proton,
        electron_density_m3=electron_n,
        proton_cyclotron_s_inv=omega_p,
        alpha_cyclotron_s_inv=omega_a,
        electron_cyclotron_s_inv=omega_e,
        omega_pp_sq_over_omega_p_sq=omega_pp_sq / omega_p**2,
        omega_pa_sq_over_omega_p_sq=omega_pa_sq / omega_p**2,
        omega_pe_sq_over_omega_p_sq=omega_pe_sq / omega_p**2,
        b_proton=b_p,
        b_electron=b_e,
        alpha_ring_lambda=lam,
        alpha_pole_z=pole_z,
        alpha_pole_frequency_over_omega_p=math.sqrt(pole_z),
    )


def _thermal_coefficients(case: LAPDReferenceCase, plasma: DerivedPlasma) -> tuple[np.ndarray, np.ndarray]:
    """Return proton A_m and electron E_l residues in Omega_p^4 units."""
    bp = plasma.b_proton
    be = plasma.b_electron
    if bp <= 0 or be <= 0:
        raise ValueError("finite-Larmor-radius parameters must be positive")

    proton = np.empty(case.proton_harmonics, dtype=float)
    for m in range(1, case.proton_harmonics + 1):
        # ive(m, b) = exp(-b) I_m(b), avoiding overflow at large b.
        gamma_m = float(ive(m, bp))
        proton[m - 1] = (
            2.0 * plasma.omega_pp_sq_over_omega_p_sq / bp
            * m**2 * gamma_m
        )

    electron = np.empty(case.electron_harmonics, dtype=float)
    for ell in range(1, case.electron_harmonics + 1):
        gamma_l = float(ive(ell, be))
        electron[ell - 1] = (
            2.0 * plasma.omega_pe_sq_over_omega_p_sq / be
            * ell**2 * gamma_l
        )
    return proton, electron


def _ring_residues(
    case: LAPDReferenceCase,
    plasma: DerivedPlasma,
    alpha_density_scale: float = 1.0,
    *,
    energy_coefficient_of_variation: float = 0.0,
    quadrature_order: int = 64,
) -> np.ndarray:
    """Return alpha-ring residues averaged over a positive energy distribution.

    At strictly perpendicular propagation in a uniform magnetic field, the
    cyclotron pole locations do not depend on perpendicular speed. A spread in
    ring energy therefore averages the Bessel residues but does not broaden the
    cyclotron poles. The energy distribution is lognormal, parameterized by
    its arithmetic mean (the case's alpha_ring_energy_kev) and coefficient of
    variation.
    """
    if not math.isfinite(alpha_density_scale) or alpha_density_scale < 0:
        raise ValueError("alpha_density_scale must be finite and non-negative")
    if not math.isfinite(energy_coefficient_of_variation) or energy_coefficient_of_variation < 0:
        raise ValueError("energy_coefficient_of_variation must be finite and non-negative")
    if quadrature_order < 8 or quadrature_order > 1024:
        raise ValueError("quadrature_order must be between 8 and 1024")
    if energy_coefficient_of_variation > 0.20:
        raise ValueError("energy coefficient of variation above 20% is outside the validated quadrature range")
    if energy_coefficient_of_variation > 0.10 and quadrature_order < 512:
        raise ValueError("energy CV above 10% requires quadrature_order>=512")

    if energy_coefficient_of_variation == 0.0:
        energies_kev = np.array([case.alpha_ring_energy_kev], dtype=float)
        weights = np.array([1.0], dtype=float)
    else:
        sigma_log_sq = math.log1p(energy_coefficient_of_variation**2)
        sigma_log = math.sqrt(sigma_log_sq)
        mu_log = math.log(case.alpha_ring_energy_kev) - 0.5 * sigma_log_sq
        nodes, raw_weights = roots_hermite(quadrature_order)
        energies_kev = np.exp(mu_log + math.sqrt(2.0) * sigma_log * nodes)
        weights = raw_weights / math.sqrt(math.pi)

    alpha_mass = case.alpha_mass_ratio_proton * m_p
    omega_a = plasma.alpha_cyclotron_s_inv
    prefactor_base = -2.0 * plasma.omega_pa_sq_over_omega_p_sq * alpha_density_scale
    out = np.zeros(case.alpha_harmonics, dtype=float)
    harmonics = np.arange(1, case.alpha_harmonics + 1, dtype=float)
    for energy_kev, weight in zip(energies_kev, weights):
        speed = math.sqrt(2.0 * energy_kev * 1.0e3 * e / alpha_mass)
        lam = case.k_perp_m_inv * speed / omega_a
        bessel = jv(harmonics, lam)
        bessel_derivative = jvp(harmonics, lam, 1)
        derivative_jn_squared = 2.0 * bessel * bessel_derivative
        out += float(weight) * (prefactor_base / lam) * harmonics**2 * derivative_jn_squared
    return out


class CollisionlessIBWModel:
    """Reference linear dispersion model with explicit species susceptibilities."""

    def __init__(
        self,
        case: LAPDReferenceCase | None = None,
        *,
        alpha_energy_coefficient_of_variation: float = 0.0,
        alpha_quadrature_order: int = 64,
    ):
        self.case = case or LAPDReferenceCase()
        if not math.isfinite(alpha_energy_coefficient_of_variation) or alpha_energy_coefficient_of_variation < 0:
            raise ValueError("alpha_energy_coefficient_of_variation must be finite and non-negative")
        if alpha_quadrature_order < 8 or alpha_quadrature_order > 1024:
            raise ValueError("alpha_quadrature_order must be between 8 and 1024")
        if alpha_energy_coefficient_of_variation > 0.20:
            raise ValueError("alpha energy CV above 20% is outside the validated quadrature range")
        if alpha_energy_coefficient_of_variation > 0.10 and alpha_quadrature_order < 512:
            raise ValueError("alpha energy CV above 10% requires alpha_quadrature_order>=512")
        self.alpha_energy_coefficient_of_variation = float(alpha_energy_coefficient_of_variation)
        self.alpha_quadrature_order = int(alpha_quadrature_order)
        self.plasma = derive_plasma(self.case)
        self.proton_coeffs, self.electron_coeffs = _thermal_coefficients(self.case, self.plasma)
        self.alpha_residues = self._compute_alpha_residues()
        self.alpha_poles = np.array([
            (n * self.plasma.alpha_cyclotron_s_inv / self.plasma.proton_cyclotron_s_inv) ** 2
            for n in range(1, self.case.alpha_harmonics + 1)
        ])
        self.proton_poles = np.arange(1, self.case.proton_harmonics + 1, dtype=float) ** 2
        self.electron_poles = np.array([
            (ell * self.plasma.electron_cyclotron_s_inv / self.plasma.proton_cyclotron_s_inv) ** 2
            for ell in range(1, self.case.electron_harmonics + 1)
        ])

    def _compute_alpha_residues(self, alpha_density_scale: float = 1.0) -> np.ndarray:
        return _ring_residues(
            self.case,
            self.plasma,
            alpha_density_scale,
            energy_coefficient_of_variation=self.alpha_energy_coefficient_of_variation,
            quadrature_order=self.alpha_quadrature_order,
        )

    def thermal_dispersion(self, z: complex) -> complex:
        """D_th(z)=1-sum(E_l/(z-z_el))-sum(A_m/(z-z_pm))."""
        value = 1.0 + 0.0j
        for coefficient, pole in zip(self.electron_coeffs, self.electron_poles):
            value -= coefficient / (z - pole)
        for coefficient, pole in zip(self.proton_coeffs, self.proton_poles):
            value -= coefficient / (z - pole)
        return value

    def regular_dispersion(self, z: complex, *, alpha_density_scale: float = 1.0) -> complex:
        """Thermal dispersion plus every alpha pole except the selected one."""
        value = self.thermal_dispersion(z)
        selected = self.case.alpha_harmonic
        residues = self._compute_alpha_residues(alpha_density_scale)
        for index, (residue, pole) in enumerate(zip(residues, self.alpha_poles), start=1):
            if index == selected:
                continue
            value += residue / (z - pole)
        return value

    def full_dispersion(self, z: complex, *, alpha_density_scale: float = 1.0) -> complex:
        """Full D(z)=D_th+sum_n R_n/(z-z_hn)."""
        value = self.thermal_dispersion(z)
        residues = self._compute_alpha_residues(alpha_density_scale)
        for residue, pole in zip(residues, self.alpha_poles):
            value += residue / (z - pole)
        return value

    def _root_bracket(self, harmonic_lower: int = 1) -> tuple[float, float]:
        low = float(harmonic_lower**2)
        high = float((harmonic_lower + 1) ** 2)
        eps = 1e-7 * (high - low)
        return low + eps, high - eps

    def find_thermal_root(self, *, harmonic_lower: int = 1, k_perp_m_inv: float | None = None) -> float:
        """Find real thermal IBW root between adjacent proton poles.

        A temporary model is used when scanning k, ensuring all susceptibilities
        are recalculated from that k rather than changing only the ring term.
        """
        if k_perp_m_inv is None or math.isclose(k_perp_m_inv, self.case.k_perp_m_inv, rel_tol=0, abs_tol=0):
            model = self
        else:
            model = CollisionlessIBWModel(
                LAPDReferenceCase(**{**asdict(self.case), "k_perp_m_inv": float(k_perp_m_inv)}),
                alpha_energy_coefficient_of_variation=self.alpha_energy_coefficient_of_variation,
                alpha_quadrature_order=self.alpha_quadrature_order,
            )
        low, high = model._root_bracket(harmonic_lower)
        return float(brentq(lambda x: model.thermal_dispersion(x).real, low, high, xtol=1e-13, rtol=1e-13))

    def _regular_root(self, *, harmonic_lower: int = 1, alpha_density_scale: float = 1.0) -> float:
        low, high = self._root_bracket(harmonic_lower)
        return float(brentq(
            lambda x: self.regular_dispersion(x, alpha_density_scale=alpha_density_scale).real,
            low, high, xtol=1e-13, rtol=1e-13,
        ))

    def _regular_derivative(self, z: float, *, alpha_density_scale: float = 1.0) -> float:
        h = 1e-6 * max(1.0, abs(z))
        derivative = (
            self.regular_dispersion(z + h, alpha_density_scale=alpha_density_scale).real
            - self.regular_dispersion(z - h, alpha_density_scale=alpha_density_scale).real
        ) / (2.0 * h)
        return float(derivative)

    def pole_analysis(self) -> dict[str, float | bool | None]:
        """Compute root-pole detuning, residue, splitting and density threshold."""
        n = self.case.alpha_harmonic
        pole_z = float(self.alpha_poles[n - 1])
        thermal_root_z = self.find_thermal_root()
        regular_root_z = self._regular_root()
        detuning = regular_root_z - pole_z
        residue = float(self.alpha_residues[n - 1])
        derivative = self._regular_derivative(regular_root_z)

        if derivative <= 0:
            raise ArithmeticError("regular IBW root derivative must be positive")
        if residue > 0:
            critical_fraction = detuning**2 * derivative / (4.0 * residue)
            discriminant = detuning**2 - 4.0 * residue / derivative
        else:
            critical_fraction = None
            discriminant = detuning**2 - 4.0 * residue / derivative

        midpoint = 0.5 * (regular_root_z + pole_z)
        local_disc = complex(discriminant)
        split = np.lib.scimath.sqrt(local_disc)
        local_roots = np.array([midpoint - 0.5 * split, midpoint + 0.5 * split], dtype=complex)
        unstable = [z for z in local_roots if z.imag > 0]
        local = unstable[0] if unstable else local_roots[0]

        return {
            "thermal_root_z": thermal_root_z,
            "regular_root_z": regular_root_z,
            "alpha_pole_z": pole_z,
            "detuning_z": detuning,
            "selected_residue_normalized": residue,
            "regular_dispersion_derivative": derivative,
            "discriminant": discriminant,
            "locally_unstable": bool(residue > 0 and discriminant < 0),
            "critical_alpha_density_fraction_of_reference": critical_fraction,
            "local_z_real": float(local.real),
            "local_z_imag": float(local.imag),
        }

    def solve_full_mode(self, *, initial_z: complex | None = None) -> LinearModeResult:
        """Solve the full complex dispersion relation near selected root-pole pair."""
        analysis = self.pole_analysis()
        if initial_z is None:
            initial_z = complex(analysis["local_z_real"], analysis["local_z_imag"])
        if initial_z.imag <= 0:
            initial_z = complex(initial_z.real, max(1e-7, abs(initial_z.imag)))

        def residual(vector: np.ndarray) -> list[float]:
            z = complex(float(vector[0]), float(vector[1]))
            value = self.full_dispersion(z)
            return [float(value.real), float(value.imag)]

        solved = root(residual, [initial_z.real, initial_z.imag], method="hybr", options={"xtol": 1e-11})
        z = complex(float(solved.x[0]), float(solved.x[1]))
        if z.imag < 0:
            z = z.conjugate()
        residual_norm = abs(self.full_dispersion(z))
        if not (math.isfinite(z.real) and math.isfinite(z.imag) and z.real > 0 and z.imag > 0):
            raise ArithmeticError(f"No growing root found near the selected pole: z={z!r}")
        if residual_norm > 1e-5:
            raise ArithmeticError(f"Full dispersion solve failed residual check: {residual_norm:.3e}")

        omega = np.lib.scimath.sqrt(z)
        analysis = self.pole_analysis()
        return LinearModeResult(
            z_real=float(z.real),
            z_imag=float(z.imag),
            omega_real_over_omega_p=float(omega.real),
            gamma_over_omega_p=float(omega.imag),
            omega_real_s_inv=float(omega.real * self.plasma.proton_cyclotron_s_inv),
            growth_rate_s_inv=float(omega.imag * self.plasma.proton_cyclotron_s_inv),
            normalized_dispersion_residual=float(residual_norm),
            local_z_real=float(analysis["local_z_real"]),
            local_z_imag=float(analysis["local_z_imag"]),
            thermal_root_z=float(analysis["thermal_root_z"]),
            regular_root_z=float(analysis["regular_root_z"]),
            alpha_pole_z=float(analysis["alpha_pole_z"]),
            detuning_z=float(analysis["detuning_z"]),
            selected_residue_normalized=float(analysis["selected_residue_normalized"]),
            regular_dispersion_derivative=float(analysis["regular_dispersion_derivative"]),
            discriminant_real=float(analysis["discriminant"]),
            critical_alpha_density_fraction_of_reference=analysis["critical_alpha_density_fraction_of_reference"],
        )

    def broadened_dispersion_omega(
        self, omega_over_omega_p: complex, *, alpha_broadening_over_omega_p: float
    ) -> complex:
        """Dispersion with phenomenological Lorentzian alpha-pole broadening.

        Each alpha harmonic denominator is replaced by
        (omega + i*nu_alpha)^2 - (n*Omega_alpha/Omega_p)^2. This is a
        damped-pole/decorrelation proxy, not a Landau or Fokker--Planck
        collision operator. Thermal-species susceptibilities remain collisionless.
        """
        nu = alpha_broadening_over_omega_p
        if not math.isfinite(nu) or nu < 0:
            raise ValueError("alpha_broadening_over_omega_p must be finite and non-negative")
        omega = complex(omega_over_omega_p)
        z = omega * omega
        value = self.thermal_dispersion(z)
        damped_omega = omega + 1j * nu
        for residue, pole in zip(self.alpha_residues, self.alpha_poles):
            value += float(residue) / (damped_omega * damped_omega - float(pole))
        return value

    def solve_broadened_mode(
        self, *, alpha_broadening_over_omega_p: float, initial_omega: complex | None = None
    ) -> BroadenedModeResult:
        """Solve the complex mode with a damped alpha cyclotron pole.

        The continuation starts from the collisionless growing eigenmode unless
        an explicit seed is provided. Results are valid only while that root
        can be tracked continuously.
        """
        nu = alpha_broadening_over_omega_p
        if not math.isfinite(nu) or nu < 0:
            raise ValueError("alpha_broadening_over_omega_p must be finite and non-negative")
        if initial_omega is None:
            initial = self.solve_full_mode()
            omega0 = complex(initial.omega_real_over_omega_p, initial.gamma_over_omega_p)
        else:
            omega0 = complex(initial_omega)
            if not (math.isfinite(omega0.real) and math.isfinite(omega0.imag)):
                raise ValueError("initial_omega must have finite real and imaginary parts")

        def residual(vector: np.ndarray) -> list[float]:
            omega = complex(float(vector[0]), float(vector[1]))
            value = self.broadened_dispersion_omega(
                omega, alpha_broadening_over_omega_p=nu
            )
            return [float(value.real), float(value.imag)]

        solved = root(residual, [omega0.real, omega0.imag], method="hybr", options={"xtol": 1e-11})
        omega = complex(float(solved.x[0]), float(solved.x[1]))
        residual_norm = abs(self.broadened_dispersion_omega(
            omega, alpha_broadening_over_omega_p=nu
        ))
        if not (math.isfinite(omega.real) and math.isfinite(omega.imag) and omega.real > 0):
            raise ArithmeticError(f"Broadened mode solve returned invalid root: {omega!r}")
        if residual_norm > 1e-7:
            raise ArithmeticError(f"Broadened dispersion residual too large: {residual_norm:.3e}")
        return BroadenedModeResult(
            alpha_broadening_over_omega_p=float(nu),
            omega_real_over_omega_p=float(omega.real),
            gamma_over_omega_p=float(omega.imag),
            normalized_dispersion_residual=float(residual_norm),
            is_growing=bool(omega.imag > 0),
        )

    def power_partition(self) -> PowerPartition:
        """Evaluate near-resonance linear power partition (not irreversible heat)."""
        z0 = float(self.plasma.alpha_pole_z)
        electron_weight = 0.0
        proton_weight = 0.0
        for coeff, pole in zip(self.electron_coeffs, self.electron_poles):
            electron_weight += float(coeff) * (z0 + float(pole)) / (z0 - float(pole)) ** 2
        for coeff, pole in zip(self.proton_coeffs, self.proton_poles):
            proton_weight += float(coeff) * (z0 + float(pole)) / (z0 - float(pole)) ** 2
        alpha_loss_weight = 1.0
        denominator = alpha_loss_weight + electron_weight + proton_weight
        p_fraction = proton_weight / denominator
        e_fraction = electron_weight / denominator
        field_fraction = alpha_loss_weight / denominator
        return PowerPartition(
            proton_fraction_of_alpha_loss=p_fraction,
            electron_fraction_of_alpha_loss=e_fraction,
            field_fraction_of_alpha_loss=field_fraction,
            proton_weight=proton_weight,
            electron_weight=electron_weight,
            alpha_loss_weight=alpha_loss_weight,
            closure_sum=p_fraction + e_fraction + field_fraction,
        )

    def exact_thermal_crossing(self, *, k_min: float = 245.0, k_max: float = 255.0) -> dict[str, float | bool]:
        """Find k where the thermal root coincides with the selected alpha pole.

        This also checks the sign of the alpha-pole residue. Root coincidence
        alone is insufficient: a positive residue is required for the
        root-pole instability in this convention.
        """
        target_z = float(self.plasma.alpha_pole_z)

        def mismatch(k: float) -> float:
            model = CollisionlessIBWModel(
                LAPDReferenceCase(**{**asdict(self.case), "k_perp_m_inv": float(k)}),
                alpha_energy_coefficient_of_variation=self.alpha_energy_coefficient_of_variation,
                alpha_quadrature_order=self.alpha_quadrature_order,
            )
            return float(model.thermal_dispersion(target_z).real)

        k_cross = float(brentq(mismatch, k_min, k_max, xtol=1e-12, rtol=1e-12))
        cross_model = CollisionlessIBWModel(
            LAPDReferenceCase(**{**asdict(self.case), "k_perp_m_inv": k_cross}),
            alpha_energy_coefficient_of_variation=self.alpha_energy_coefficient_of_variation,
            alpha_quadrature_order=self.alpha_quadrature_order,
        )
        residue = float(cross_model.alpha_residues[self.case.alpha_harmonic - 1])
        bp = float(cross_model.plasma.b_proton)
        return {
            "k_perp_exact_thermal_crossing_m_inv": k_cross,
            "b_proton_at_crossing": bp,
            "thermal_crossing_residue": residue,
            "destabilizing_residue_at_crossing": residue > 0,
            "thermal_root_matches_alpha_pole": abs(mismatch(k_cross)) < 1e-8,
        }

    def scan_wavenumber_band(
        self, *, k_min: float = 248.0, k_max: float = 255.0, points: int = 141
    ) -> list[dict[str, float | bool | None]]:
        """Scan the local root-pole criterion at fixed reference alpha density.

        Positive growth is reported only when both the residue sign and the
        finite-density discriminant criterion are satisfied. Growth is from
        the local quadratic root approximation, not a nonlinear saturation
        model.
        """
        if not (math.isfinite(k_min) and math.isfinite(k_max) and 0 < k_min < k_max):
            raise ValueError("require finite 0 < k_min < k_max")
        if points < 3:
            raise ValueError("points must be >= 3")
        rows: list[dict[str, float | bool | None]] = []
        for k_value in np.linspace(k_min, k_max, points):
            case = LAPDReferenceCase(**{**asdict(self.case), "k_perp_m_inv": float(k_value)})
            model = CollisionlessIBWModel(
                case,
                alpha_energy_coefficient_of_variation=self.alpha_energy_coefficient_of_variation,
                alpha_quadrature_order=self.alpha_quadrature_order,
            )
            analysis = model.pole_analysis()
            discriminant = float(analysis["discriminant"])
            unstable = bool(analysis["locally_unstable"])
            gamma_norm = 0.0
            omega_real_norm = math.nan
            if unstable:
                z = complex(float(analysis["local_z_real"]), float(analysis["local_z_imag"]))
                omega = np.lib.scimath.sqrt(z)
                omega_real_norm = float(omega.real)
                gamma_norm = float(omega.imag)
            rows.append({
                "k_perp_m_inv": float(k_value),
                "b_proton": float(model.plasma.b_proton),
                "thermal_to_alpha_detuning_z": float(analysis["detuning_z"]),
                "selected_alpha_residue": float(analysis["selected_residue_normalized"]),
                "critical_alpha_density_fraction_of_reference": analysis["critical_alpha_density_fraction_of_reference"],
                "unstable_at_reference_alpha_density": unstable,
                "local_omega_real_over_omega_p": omega_real_norm,
                "local_gamma_over_omega_p": gamma_norm,
                "root_pole_discriminant": discriminant,
            })
        return rows

    def result_dict(self) -> dict[str, Any]:
        mode = self.solve_full_mode()
        analysis = self.pole_analysis()
        partition = self.power_partition()
        return {
            "model": "strictly_perpendicular_collisionless_electrostatic_IBW",
            "scope_warning": (
                "LAPD proton-alpha benchmark only; not a p-B11 reactor, nonlinear model, "
                "Coulomb-collision prediction, or irreversible proton-heating estimate."
            ),
            "reference_case": asdict(self.case),
            "alpha_energy_distribution": {
                "family": "lognormal in perpendicular kinetic energy",
                "mean_energy_kev": self.case.alpha_ring_energy_kev,
                "coefficient_of_variation": self.alpha_energy_coefficient_of_variation,
                "quadrature_order": self.alpha_quadrature_order,
                "pole_frequency_depends_on_energy": False,
            },
            "derived_plasma": asdict(self.plasma),
            "pole_analysis": analysis,
            "full_mode": asdict(mode),
            "linear_power_partition": asdict(partition),
            "exact_thermal_crossing_check": self.exact_thermal_crossing(),
            "wavenumber_scan_summary": _summarize_scan(self.scan_wavenumber_band()),
        }


def _summarize_scan(rows: list[dict[str, float | bool | None]]) -> dict[str, Any]:
    unstable = [row for row in rows if row["unstable_at_reference_alpha_density"]]
    if not unstable:
        return {"unstable_point_count": 0, "unstable_k_min_m_inv": None, "unstable_k_max_m_inv": None, "max_local_growth_over_omega_p": 0.0}
    return {
        "unstable_point_count": len(unstable),
        "unstable_k_min_m_inv": min(float(row["k_perp_m_inv"]) for row in unstable),
        "unstable_k_max_m_inv": max(float(row["k_perp_m_inv"]) for row in unstable),
        "max_local_growth_over_omega_p": max(float(row["local_gamma_over_omega_p"]) for row in unstable),
    }


def run_reference_case(output_path: str | Path | None = None) -> dict[str, Any]:
    model = CollisionlessIBWModel()
    result = model.result_dict()
    if output_path is not None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
        scan_path = path.with_name(path.stem + "_wavenumber_scan.csv")
        model = CollisionlessIBWModel()
        rows = model.scan_wavenumber_band()
        with scan_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    return result


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("results/v11_linear_ibw_reference.json"))
    args = parser.parse_args()
    result = run_reference_case(args.out)
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
