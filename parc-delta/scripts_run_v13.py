"""Generate finite-k_parallel kinetic IBW validation and sensitivity results."""
from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path

from parc_delta_v10.finite_k_ibw import FiniteKParallelIBWModel, make_reference_case
from parc_delta_v10.linear_ibw import CollisionlessIBWModel

ROOT = Path(__file__).parent
OUT = ROOT / "results"
OUT.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"No rows to write to {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    base_case = make_reference_case()
    perpendicular_control = CollisionlessIBWModel(base_case.plasma)
    control_mode = perpendicular_control.solve_full_mode()
    seed0 = complex(control_mode.omega_real_over_omega_p, control_mode.gamma_over_omega_p)

    zero_k_model = FiniteKParallelIBWModel(base_case)
    zero_k_mode = zero_k_model.solve_mode(seed0)
    zero_k_dispersion_residual_at_v12_root = abs(zero_k_model.dispersion(seed0))

    ratios = [0.0, 1.0e-4, 3.0e-4, 1.0e-3, 1.5e-3, 2.0e-3, 3.0e-3, 5.0e-3, 1.0e-2]
    alpha_parallel_temperatures = [0.0, 1.0, 10.0, 100.0]
    grid_rows: list[dict] = []
    grid_by_temperature: dict[str, list[dict]] = {}

    # Continue each branch in k_parallel rather than independently seeding all
    # points from the perpendicular result.
    for t_parallel in alpha_parallel_temperatures:
        seed = seed0
        curve: list[dict] = []
        for ratio in ratios:
            case = make_reference_case(
                k_parallel_over_perp=ratio,
                alpha_parallel_temperature_ev=t_parallel,
            )
            model = FiniteKParallelIBWModel(case)
            mode = model.solve_mode(seed)
            seed = complex(mode.omega_real_over_omega_p, mode.gamma_over_omega_p)
            breakdown = model.response_breakdown(seed)
            row = {
                "k_parallel_over_k_perp": ratio,
                "k_parallel_m_inv": case.k_parallel_m_inv,
                "alpha_parallel_temperature_ev": t_parallel,
                "alpha_perp_energy_cv": 0.0,
                "omega_real_over_omega_p": mode.omega_real_over_omega_p,
                "gamma_over_omega_p": mode.gamma_over_omega_p,
                "growth_rate_s_inv": mode.gamma_over_omega_p * model.omega_p,
                "normalized_residual": mode.normalized_residual,
                "solver_success": mode.solver_success,
                "proton_susceptibility_real": breakdown["proton"].real,
                "proton_susceptibility_imag": breakdown["proton"].imag,
                "electron_susceptibility_real": breakdown["electron"].real,
                "electron_susceptibility_imag": breakdown["electron"].imag,
                "alpha_susceptibility_real": breakdown["alpha"].real,
                "alpha_susceptibility_imag": breakdown["alpha"].imag,
                "branch_status": "growing" if mode.gamma_over_omega_p > 1e-10 else (
                    "damped" if mode.gamma_over_omega_p < -1e-10 else "marginal"
                ),
            }
            curve.append(row)
            grid_rows.append(row)
        grid_by_temperature[f"Tpar_{t_parallel:g}_eV"] = curve
    write_csv(OUT / "v13_finite_kparallel_temperature_scan.csv", grid_rows)

    width_rows: list[dict] = []
    width_by_cv: dict[str, list[dict]] = {}
    width_ratios = [3.0e-4, 1.0e-3, 2.0e-3, 3.0e-3, 5.0e-3]
    width_cvs = [0.0, 0.02, 0.05]
    width_temps = [0.0, 10.0, 100.0]
    for cv in width_cvs:
        for t_parallel in width_temps:
            # Reset each parameter family to its own perpendicular control mode.
            cv0_case = make_reference_case(
                alpha_parallel_temperature_ev=t_parallel,
                alpha_perp_energy_cv=cv,
                energy_quadrature_order=128 if cv >= 0.05 else 64,
            )
            cv0_old = CollisionlessIBWModel(
                cv0_case.plasma,
                alpha_energy_coefficient_of_variation=cv,
                alpha_quadrature_order=128 if cv >= 0.05 else 64,
            )
            old = cv0_old.solve_full_mode()
            seed = complex(old.omega_real_over_omega_p, old.gamma_over_omega_p)
            curve = []
            for ratio in width_ratios:
                case = make_reference_case(
                    k_parallel_over_perp=ratio,
                    alpha_parallel_temperature_ev=t_parallel,
                    alpha_perp_energy_cv=cv,
                    energy_quadrature_order=128 if cv >= 0.05 else 64,
                )
                model = FiniteKParallelIBWModel(case)
                mode = model.solve_mode(seed)
                seed = complex(mode.omega_real_over_omega_p, mode.gamma_over_omega_p)
                row = {
                    "alpha_perp_energy_cv": cv,
                    "alpha_parallel_temperature_ev": t_parallel,
                    "k_parallel_over_k_perp": ratio,
                    "omega_real_over_omega_p": mode.omega_real_over_omega_p,
                    "gamma_over_omega_p": mode.gamma_over_omega_p,
                    "growth_rate_s_inv": mode.gamma_over_omega_p * model.omega_p,
                    "normalized_residual": mode.normalized_residual,
                    "branch_status": "growing" if mode.gamma_over_omega_p > 1e-10 else (
                        "damped" if mode.gamma_over_omega_p < -1e-10 else "marginal"
                    ),
                }
                curve.append(row)
                width_rows.append(row)
            width_by_cv[f"cv_{cv:.3f}_Tpar_{t_parallel:g}eV"] = curve
    write_csv(OUT / "v13_finite_kparallel_energy_width_scan.csv", width_rows)

    report = {
        "title": "PARC-Delta v1.3 finite-parallel-wavenumber kinetic IBW extension",
        "model_class": "collisionless electrostatic magnetized kinetic susceptibility",
        "reference_case": asdict(base_case),
        "v12_perpendicular_control": {
            "omega_real_over_omega_p": control_mode.omega_real_over_omega_p,
            "gamma_over_omega_p": control_mode.gamma_over_omega_p,
            "v13_zero_kparallel_mode": asdict(zero_k_mode),
            "v13_dispersion_residual_at_v12_root": zero_k_dispersion_residual_at_v12_root,
        },
        "thermal_species": {
            "model": "Maxwellian Harris susceptibility with all retained cyclotron harmonics",
            "parallel_resonances": "Landau-contour plasma dispersion function Z(zeta)",
        },
        "alpha_species": {
            "model": "gyrotropic ring; lognormal perpendicular energy; Maxwellian parallel velocity",
            "perpendicular_energy_mean_kev": base_case.plasma.alpha_ring_energy_kev,
            "perpendicular_energy_cv_scan": width_cvs,
            "parallel_temperature_ev_scan": alpha_parallel_temperatures,
            "quadrature": "Gauss-Hermite in log-energy; analytic Z and Z-prime integration over parallel Maxwellian",
            "distribution_status": "parametric sensitivity family; not a measured LAPD or p-B11 fusion-product distribution",
        },
        "finite_kparallel_temperature_scan": grid_by_temperature,
        "finite_kparallel_energy_width_scan": width_by_cv,
        "collision_operator_status": {
            "implemented": False,
            "reason": (
                "No collisional damping is inserted in this release. A frequency-shifted pole or a constant-nu "
                "substitution is not a conserving Coulomb collision operator. The required full magnetized "
                "linearized Landau test-particle plus field-particle operator has to be discretized and checked "
                "for particle, momentum, energy conservation and non-negative entropy production before use."
            ),
            "required_validation": [
                "discrete particle-number conservation",
                "discrete momentum conservation across coupled species",
                "discrete total kinetic-energy conservation across coupled species",
                "non-negative entropy production / H-theorem test",
                "velocity-grid and harmonic convergence",
                "recovery of collisionless v1.3 as collision frequency tends to zero",
            ],
        },
        "limitations": [
            "The 24 keV LAPD alpha ring is a laboratory reference, not the approximately MeV-scale alpha birth distribution of p-B11 fusion.",
            "The alpha distribution is a tunable gyrotropic ring family, not a reaction-derived slowing-down distribution.",
            "The model is electrostatic, homogeneous and local; no finite geometry, gradients, electromagnetic coupling or wave escape is included.",
            "Finite-kparallel Landau phase mixing is collisionless and is not collisional thermalization.",
            "No nonlinear saturation, proton irreversible heating, fusion gain, net electricity, cost or commercial claim is established.",
        ],
        "references": [
            "Qin & Fisch (2026), arXiv:2609.07732, Eqs. (4)-(9): https://arxiv.org/abs/2609.07732",
            "An introduction to perpendicularly propagating Bernstein waves, Phys. Plasmas (2026), Harris oblique electrostatic dispersion relation: https://doi.org/10.1063/5.0316617",
            "Pan & Ernst (2019), Phys. Rev. E 99, 023201, conservative gyrokinetic Landau operator: https://doi.org/10.1103/PhysRevE.99.023201",
        ],
    }
    (OUT / "v13_finite_kparallel_kinetic_results.json").write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
    )

    print(json.dumps({
        "v12_growth": control_mode.gamma_over_omega_p,
        "v13_zero_k_growth": zero_k_mode.gamma_over_omega_p,
        "zero_k_residual_at_v12_root": zero_k_dispersion_residual_at_v12_root,
        "main_scan_rows": len(grid_rows),
        "width_scan_rows": len(width_rows),
        "max_main_residual": max(row["normalized_residual"] for row in grid_rows),
        "max_width_residual": max(row["normalized_residual"] for row in width_rows),
    }, indent=2))


if __name__ == "__main__":
    main()
