"""Generate PARC-Delta v1.2 mass, finite-width and damped-pole sensitivities."""
from __future__ import annotations

import csv
import json
from dataclasses import asdict, replace
from pathlib import Path

from parc_delta_v10.linear_ibw import (
    CODATA_ALPHA_TO_PROTON_MASS_RATIO,
    CollisionlessIBWModel,
    LAPDReferenceCase,
)

OUT = Path(__file__).parent / "results"
OUT.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    nominal = LAPDReferenceCase()  # m_alpha = 4 m_p approximation retained as control
    physical = replace(nominal, alpha_mass_ratio_proton=CODATA_ALPHA_TO_PROTON_MASS_RATIO)

    nominal_model = CollisionlessIBWModel(nominal)
    physical_model = CollisionlessIBWModel(physical)
    nominal_cross = nominal_model.exact_thermal_crossing()
    physical_cross = physical_model.exact_thermal_crossing()
    physical_fixed_k = physical_model.pole_analysis()

    physical_cross_case = replace(
        physical,
        k_perp_m_inv=physical_cross["k_perp_exact_thermal_crossing_m_inv"],
    )

    mass_report = {
        "title": "PARC-Delta v1.2 alpha mass-convention sensitivity",
        "constants": {
            "codata_alpha_to_proton_mass_ratio": CODATA_ALPHA_TO_PROTON_MASS_RATIO,
            "reference_approximation_alpha_to_proton_mass_ratio": 4.0,
            "codata_source": "NIST/CODATA 2022 recommended values",
        },
        "approximate_mass_crossing": {
            "case": asdict(nominal),
            "derived_alpha_harmonic_frequency_over_omega_p": nominal_model.plasma.alpha_pole_frequency_over_omega_p,
            "mean_ring_bessel_argument": nominal_model.plasma.alpha_ring_lambda,
            **nominal_cross,
        },
        "physical_mass_crossing": {
            "case": asdict(physical),
            "derived_alpha_harmonic_frequency_over_omega_p": physical_model.plasma.alpha_pole_frequency_over_omega_p,
            "mean_ring_bessel_argument": physical_model.plasma.alpha_ring_lambda,
            **physical_cross,
        },
        "physical_mass_at_published_fixed_k": {
            "k_perp_m_inv": physical.k_perp_m_inv,
            "derived_alpha_harmonic_frequency_over_omega_p": physical_model.plasma.alpha_pole_frequency_over_omega_p,
            **physical_fixed_k,
        },
        "interpretation": (
            "The residue sign at the exact thermal crossing changes with the alpha mass convention. "
            "The CODATA-mass crossing is destabilizing, but its crossing wavenumber and b_p do not "
            "match the paper's approximate b_p~1.31 statement. At the paper's fixed k=251.74 m^-1, "
            "the CODATA-mass case is strongly detuned and stable at the reference alpha density. "
            "This is a parameter-convention sensitivity, not a completed reconciliation."
        ),
    }
    (OUT / "v12_mass_convention_sensitivity.json").write_text(
        json.dumps(mass_report, indent=2, sort_keys=True), encoding="utf-8"
    )

    mass_rows = []
    for label, case, model, crossing in [
        ("4_mp_approximation", nominal, nominal_model, nominal_cross),
        ("CODATA_alpha_mass", physical, physical_model, physical_cross),
    ]:
        mass_rows.append({
            "mass_convention": label,
            "alpha_mass_ratio_proton": case.alpha_mass_ratio_proton,
            "third_alpha_harmonic_over_omega_p": model.plasma.alpha_pole_frequency_over_omega_p,
            "k_cross_m_inv": crossing["k_perp_exact_thermal_crossing_m_inv"],
            "b_proton_cross": crossing["b_proton_at_crossing"],
            "lambda_alpha_cross": (
                model.plasma.alpha_ring_lambda
                * crossing["k_perp_exact_thermal_crossing_m_inv"] / case.k_perp_m_inv
            ),
            "R3_cross": crossing["thermal_crossing_residue"],
            "positive_residue": crossing["destabilizing_residue_at_crossing"],
        })
    write_csv(OUT / "v12_mass_convention_sensitivity.csv", mass_rows)

    cvs_and_orders = [(0.0, 64), (0.01, 64), (0.02, 64), (0.05, 128), (0.10, 128), (0.20, 512)]
    finite_rows: list[dict] = []
    finite_modes: dict[str, dict] = {}
    cold_gamma = None
    for cv, order in cvs_and_orders:
        case = physical_cross_case
        model = CollisionlessIBWModel(
            case,
            alpha_energy_coefficient_of_variation=cv,
            alpha_quadrature_order=order,
        )
        # The thermal crossing location is independent of perpendicular alpha
        # energy spread at k_parallel=0; reuse the CODATA-mass crossing. The
        # mode solve supplies the width-averaged residue for this row.
        crossing = physical_cross
        mode = model.solve_full_mode()
        if cold_gamma is None:
            cold_gamma = mode.gamma_over_omega_p
        row = {
            "alpha_energy_cv": cv,
            "quadrature_order": order,
            "k_cross_m_inv": crossing["k_perp_exact_thermal_crossing_m_inv"],
            "b_proton_cross": crossing["b_proton_at_crossing"],
            "mean_lambda_alpha": model.plasma.alpha_ring_lambda,
            "averaged_R3": mode.selected_residue_normalized,
            "omega_real_over_omega_p": mode.omega_real_over_omega_p,
            "gamma_over_omega_p": mode.gamma_over_omega_p,
            "growth_rate_s_inv": mode.growth_rate_s_inv,
            "growth_fraction_of_cold": mode.gamma_over_omega_p / cold_gamma,
            "growth_suppression_percent": 100.0 * (1.0 - mode.gamma_over_omega_p / cold_gamma),
            "dispersion_residual": mode.normalized_dispersion_residual,
        }
        finite_rows.append(row)
        finite_modes[f"cv_{cv:.3f}"] = row
    write_csv(OUT / "v12_finite_width_sensitivity.csv", finite_rows)

    broadening_rows: list[dict] = []
    broadening_curves: dict[str, list[dict]] = {}
    nu_values = [0.0, 1e-4, 5e-4, 1e-3, 2e-3, 5e-3, 1e-2]
    for cv, order in [(0.0, 64), (0.02, 64), (0.05, 128)]:
        model = CollisionlessIBWModel(
            physical_cross_case,
            alpha_energy_coefficient_of_variation=cv,
            alpha_quadrature_order=order,
        )
        curve = []
        cold_mode = model.solve_full_mode()
        cold_omega = complex(cold_mode.omega_real_over_omega_p, cold_mode.gamma_over_omega_p)
        gamma_zero = None
        for nu in nu_values:
            mode = model.solve_broadened_mode(
                alpha_broadening_over_omega_p=nu, initial_omega=cold_omega
            )
            if gamma_zero is None:
                gamma_zero = mode.gamma_over_omega_p
            row = {
                "alpha_energy_cv": cv,
                "alpha_broadening_over_omega_p": nu,
                "omega_real_over_omega_p": mode.omega_real_over_omega_p,
                "gamma_over_omega_p": mode.gamma_over_omega_p,
                "growth_fraction_of_unbroadened": mode.gamma_over_omega_p / gamma_zero,
                "dispersion_residual": mode.normalized_dispersion_residual,
                "is_growing": mode.is_growing,
            }
            broadening_rows.append(row)
            curve.append(row)
        broadening_curves[f"cv_{cv:.3f}"] = curve
    write_csv(OUT / "v12_alpha_pole_broadening_sensitivity.csv", broadening_rows)

    report = {
        "title": "PARC-Delta v1.2 finite-width and alpha-pole broadening sensitivity",
        "reference_case": asdict(physical_cross_case),
        "energy_distribution": {
            "family": "lognormal perpendicular alpha kinetic energy",
            "mean_energy_kev": physical_cross_case.alpha_ring_energy_kev,
            "cv_definition": "standard_deviation(E_perp) / mean(E_perp)",
            "normalization": "arithmetic mean held fixed at 24 keV",
            "pole_behavior": (
                "For k_parallel=0 and homogeneous B, cyclotron pole locations are independent of v_perp. "
                "Finite energy width averages the Bessel residues; it does not create a frequency spread."
            ),
        },
        "finite_width_results": finite_modes,
        "alpha_pole_broadening": {
            "denominator": "(omega + i*nu_alpha)^2 - (n*Omega_alpha/Omega_p)^2",
            "interpretation": (
                "Phenomenological damped-pole/decorrelation proxy applied to alpha harmonics only. "
                "It is not a Coulomb Fokker-Planck operator; background species remain collisionless."
            ),
            "curves": broadening_curves,
        },
        "limitations": [
            "The 24 keV alpha ring is the LAPD reference benchmark, not a p-B11 fusion-born alpha distribution.",
            "The lognormal energy-width family is a sensitivity prior, not a measured distribution.",
            "Finite k_parallel, velocity-space parallel spread, full Coulomb collisions, spatial gradients, and wave leakage are omitted.",
            "Coherent proton response is not irreversible proton heat.",
            "No reactor gain, net electricity, cost, or commercial feasibility result is implied.",
        ],
    }
    (OUT / "v12_finite_width_and_broadening.json").write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
    )

    print(json.dumps({
        "mass_convention_sensitivity": mass_report,
        "finite_width_rows": finite_rows,
        "broadening_rows": broadening_rows,
    }, indent=2, sort_keys=True))
    print("Wrote v1.2 sensitivity results under results/")


if __name__ == "__main__":
    main()
