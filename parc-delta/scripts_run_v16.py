from __future__ import annotations

import csv
import json
import math
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np
from scipy.constants import c, e, m_e, m_p, physical_constants

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from parc_delta_v10.pb11_alpha_source import (  # noqa: E402
    e_cm_from_proton_lab_energy,
    sample_pb11_alpha_birth,
)
from parc_delta_v10.slowing_down import (  # noqa: E402
    MaxwellianFieldSpecies,
    RosenbluthSlowingDownSolver,
    expected_kinetic_energy_rate_per_marker_j_s,
    rosenbluth_test_particle_coefficients,
)
from parc_delta_v10.collisional_scattering import (  # noqa: E402
    run_test_particle_scattering,
    run_test_particle_multispecies_scattering,
)

OUT = ROOT / "results"
OUT.mkdir(exist_ok=True)
DOCS = ROOT / "docs"
M_ALPHA = physical_constants["alpha particle mass"][0]
Q_ALPHA = 2.0 * e
BASE_BEAM_MEV = 0.675
BASE_ECM_MEV = e_cm_from_proton_lab_energy(BASE_BEAM_MEV)
ALPHA_DENSITY = 2.0e18  # illustrative population normalization, not reaction-rate-derived
LN_LAMBDA = 15.0
DT = 1.0e-4
STEPS = 10000

PHYSICAL_FIELDS = [
    MaxwellianFieldSpecies("electron", m_e, -e, 1.04e20, 1.0e4),
    MaxwellianFieldSpecies("proton", m_p, e, 1.0e20, 1.0e4),
    MaxwellianFieldSpecies("thermal_alpha", M_ALPHA, Q_ALPHA, 2.0e18, 1.0e4),
]


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def to_plain(value):
    if isinstance(value, dict):
        return {str(k): to_plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_plain(v) for v in value]
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    return value


def build_source(channel: str, events: int, beam_mev: float, seed: int):
    ecm = e_cm_from_proton_lab_energy(beam_mev)
    return sample_pb11_alpha_birth(
        events,
        channel=channel,
        e_cm_mev=ecm,
        seed=seed,
        frame="beam_lab",
    )


def relativistic_nonrelativistic_source_audit(sample) -> dict[str, float]:
    v2 = np.sum(sample.velocity_m_s**2, axis=1)
    beta2 = v2 / c**2
    gamma = 1.0 / np.sqrt(1.0 - beta2)
    rel_mev = (gamma - 1.0) * M_ALPHA * c**2 / (1.0e6 * e)
    nr_mev = 0.5 * M_ALPHA * v2 / (1.0e6 * e)
    rel_err = np.abs(nr_mev - rel_mev) / np.maximum(rel_mev, 1.0e-30)
    return {
        "max_speed_over_c": float(np.sqrt(np.max(beta2))),
        "max_relative_kinetic_energy_difference": float(np.max(rel_err)),
        "mean_relative_kinetic_energy_difference": float(np.mean(rel_err)),
        "source_mean_relativistic_energy_mev": float(np.mean(sample.kinetic_energy_mev)),
        "source_mean_nonrelativistic_energy_mev": float(np.mean(nr_mev)),
    }


def main() -> None:
    summary: dict[str, object] = {
        "version": "1.6.0-research",
        "model": "non-relativistic test-particle Rosenbluth/Langevin solver with fixed Maxwellian reservoirs",
        "beam_energy_lab_mev": BASE_BEAM_MEV,
        "entrance_cm_energy_mev": BASE_ECM_MEV,
        "alpha_population_density_m3": ALPHA_DENSITY,
        "coulomb_logarithm": LN_LAMBDA,
        "backgrounds": [
            {"name": x.name, "density_m3": x.density_m3, "temperature_ev": x.temperature_ev,
             "mass_kg": x.mass_kg, "charge_c": x.charge_c}
            for x in PHYSICAL_FIELDS
        ],
        "branch_note": "alpha0 and alpha1 are separate unweighted branch cases; no branching fractions are assumed.",
        "scope_note": "Test particles do not back-react on fixed Maxwellian backgrounds. Deposited powers are expected Landau moments, not self-consistent background heating.",
    }

    # Main full-mixture slowing-down histories, one unweighted channel at a time.
    all_history: list[dict[str, object]] = []
    all_deposition: list[dict[str, object]] = []
    channel_summaries: dict[str, object] = {}
    channel_sources = {}
    for channel, seed in (("alpha0", 440), ("alpha1", 441)):
        source = build_source(channel, events=512, beam_mev=BASE_BEAM_MEV, seed=seed)
        channel_sources[channel] = source
        audit = relativistic_nonrelativistic_source_audit(source)
        solver = RosenbluthSlowingDownSolver(
            test_mass_kg=M_ALPHA,
            test_charge_c=Q_ALPHA,
            field_species=PHYSICAL_FIELDS,
            coulomb_logarithm=LN_LAMBDA,
            max_dt_k=0.02,
            max_speed_fraction_c=0.1,
        )
        initial_speed = np.linalg.norm(source.velocity_m_s, axis=1)
        initial_coefficients = solver._coefficients(source.velocity_m_s)
        initial_power_by_species = {}
        for field, coefficient in zip(PHYSICAL_FIELDS, initial_coefficients):
            initial_rate = expected_kinetic_energy_rate_per_marker_j_s(
                initial_speed, test_mass_kg=M_ALPHA, coefficients=coefficient
            )
            initial_power_by_species[field.name] = float(-ALPHA_DENSITY * np.mean(initial_rate))
        result = solver.run(
            source.velocity_m_s,
            dt_s=DT,
            steps=STEPS,
            alpha_density_m3=ALPHA_DENSITY,
            seed=1200 + seed,
            record_every=1000,
        )
        channel_summaries[channel] = {
            "source": source.summary(),
            "source_nonrelativistic_audit": audit,
            "solver": {
                "dt_s": result.dt_s,
                "steps": result.steps,
                "marker_count": result.marker_count,
                "initial_energy_density_j_m3": result.initial_energy_density_j_m3,
                "initial_power_density_w_m3_by_field_species": initial_power_by_species,
                "final_energy_density_j_m3": result.final_energy_density_j_m3,
                "deposited_energy_j_m3_by_field_species": result.deposited_energy_j_m3,
                "final_power_density_w_m3_by_field_species": result.final_power_density_w_m3,
                "actual_alpha_energy_change_j_m3": result.actual_alpha_energy_change_j_m3,
                "expected_alpha_energy_change_j_m3": result.expected_alpha_energy_change_j_m3,
                "energy_budget_residual_j_m3": result.energy_budget_residual_j_m3,
                "relative_energy_budget_residual": result.relative_energy_budget_residual,
                "max_dt_k_guard": 0.02,
            },
            "snapshots": [asdict(x) for x in result.snapshots],
        }
        for snap in result.snapshots:
            all_history.append({"channel": channel, **asdict(snap)})
        for name, val in result.deposited_energy_j_m3.items():
            all_deposition.append({
                "channel": channel,
                "field_species": name,
                "deposited_energy_j_m3": val,
                "deposited_energy_mev_per_alpha": val / (ALPHA_DENSITY * 1.0e6 * e),
            })
    summary["full_mixture_slows_down"] = channel_summaries
    write_csv(OUT / "v16_full_mixture_slowing_history.csv", all_history)
    write_csv(OUT / "v16_full_mixture_energy_deposition.csv", all_deposition)

    print("v1.6 runner: full-history Rosenbluth cases complete", flush=True)

    # Independent TA and Nanbu benchmark against the Rosenbluth FP reference.
    # The colder proton bath isolates alpha-proton scattering, keeping both
    # small-angle algorithms in their controlled weak-deflection regime.
    comparison_source = build_source("alpha0", events=128, beam_mev=BASE_BEAM_MEV, seed=1452)
    proton_bath = MaxwellianFieldSpecies("proton", m_p, e, 1.0e20, 1.0)
    comp_dt = 5.0e-5
    comp_steps = 1000
    comp_solver = RosenbluthSlowingDownSolver(
        test_mass_kg=M_ALPHA,
        test_charge_c=Q_ALPHA,
        field_species=[proton_bath],
        coulomb_logarithm=LN_LAMBDA,
        max_dt_k=0.02,
    )
    fp_result = comp_solver.run(
        comparison_source.velocity_m_s,
        dt_s=comp_dt,
        steps=comp_steps,
        alpha_density_m3=ALPHA_DENSITY,
        seed=2201,
        record_every=100,
    )
    comparison_rows: list[dict[str, object]] = []
    method_histories: dict[str, list[dict[str, float]]] = {
        "rosenbluth_langevin": [asdict(x) for x in fp_result.snapshots]
    }
    for method, seed in (("takizuka_abe", 2202), ("nanbu", 2203)):
        hist = run_test_particle_scattering(
            comparison_source.velocity_m_s,
            test_mass_kg=M_ALPHA,
            test_charge_c=Q_ALPHA,
            field_species=proton_bath,
            dt_s=comp_dt,
            steps=comp_steps,
            coulomb_logarithm=LN_LAMBDA,
            method=method,
            seed=seed,
            record_every=100,
        )
        method_histories[method] = hist
    final_energy = {name: rows[-1]["mean_energy_ev"] for name, rows in method_histories.items()}
    reference_energy = final_energy["rosenbluth_langevin"]
    for name, rows in method_histories.items():
        for row in rows:
            comparison_rows.append({"method": name, **row})
    comparison_summary = {
        "field_species": "proton",
        "field_density_m3": proton_bath.density_m3,
        "field_temperature_ev": proton_bath.temperature_ev,
        "dt_s": comp_dt,
        "steps": comp_steps,
        "duration_s": comp_dt * comp_steps,
        "marker_count": int(comparison_source.velocity_m_s.shape[0]),
        "initial_mean_energy_ev": method_histories["rosenbluth_langevin"][0]["mean_energy_ev"],
        "final_mean_energy_ev_by_method": final_energy,
        "relative_final_mean_energy_difference_vs_rosenbluth": {
            name: (val - reference_energy) / reference_energy
            for name, val in final_energy.items()
        },
        "note": "Test-particle comparison against a fixed cold Maxwellian proton bath; TA and Nanbu are independently sampled pair-scattering updates.",
    }
    summary["independent_collision_method_comparison"] = comparison_summary
    write_csv(OUT / "v16_ta_nanbu_rosenbluth_comparison.csv", comparison_rows)

    print("v1.6 runner: single-species TA/Nanbu comparison complete", flush=True)

    # Full fixed-background e/p/thermal-alpha comparison. A symmetric
    # forward/reverse half-step split reduces deterministic species-order bias.
    mix_dt = 5.0e-5
    mix_steps = 200
    mix_fp_solver = RosenbluthSlowingDownSolver(
        test_mass_kg=M_ALPHA, test_charge_c=Q_ALPHA,
        field_species=PHYSICAL_FIELDS, coulomb_logarithm=LN_LAMBDA,
        max_dt_k=0.02,
    )
    mix_fp = mix_fp_solver.run(
        comparison_source.velocity_m_s, dt_s=mix_dt, steps=mix_steps,
        alpha_density_m3=ALPHA_DENSITY, seed=2501, record_every=mix_steps,
    )
    mix_method_final = {"rosenbluth_langevin": mix_fp.snapshots[-1].mean_energy_ev}
    mix_method_histories = {"rosenbluth_langevin": [asdict(x) for x in mix_fp.snapshots]}
    for method, seed in (("takizuka_abe", 2502), ("nanbu", 2503)):
        history = run_test_particle_multispecies_scattering(
            comparison_source.velocity_m_s,
            test_mass_kg=M_ALPHA, test_charge_c=Q_ALPHA,
            field_species=PHYSICAL_FIELDS, dt_s=mix_dt, steps=mix_steps,
            coulomb_logarithm=LN_LAMBDA, method=method, seed=seed,
            record_every=mix_steps, substeps_per_species=16,
        )
        mix_method_histories[method] = history
        mix_method_final[method] = history[-1]["mean_energy_ev"]
    mix_reference = mix_method_final["rosenbluth_langevin"]
    mix_comparison = {
        "field_species": [x.name for x in PHYSICAL_FIELDS],
        "field_densities_m3": {x.name: x.density_m3 for x in PHYSICAL_FIELDS},
        "field_temperatures_ev": {x.name: x.temperature_ev for x in PHYSICAL_FIELDS},
        "dt_s": mix_dt,
        "steps": mix_steps,
        "duration_s": mix_dt * mix_steps,
        "marker_count": int(comparison_source.velocity_m_s.shape[0]),
        "initial_mean_energy_ev": mix_method_histories["rosenbluth_langevin"][0]["mean_energy_ev"],
        "final_mean_energy_ev_by_method": mix_method_final,
        "relative_final_mean_energy_difference_vs_rosenbluth": {
            name: (value - mix_reference) / mix_reference
            for name, value in mix_method_final.items()
        },
        "operator_split": "symmetric forward/reverse half-step composition; each bath receives total dt",
        "substeps_per_species_per_half_pass": 16,
        "note": "Three fixed Maxwellian test-particle baths (electrons, protons, thermal alphas); backgrounds do not back-react.",
    }
    summary["full_mixture_collision_method_comparison"] = mix_comparison
    mix_rows = []
    for name, history in mix_method_histories.items():
        for row in history:
            mix_rows.append({"method": name, **row})
    write_csv(OUT / "v16_full_mixture_ta_nanbu_rosenbluth_comparison.csv", mix_rows)

    print("v1.6 runner: full-mixture K=16 comparison complete", flush=True)

    print("v1.6 runner: full-mixture comparison complete; optional subcycling scan is separate", flush=True)

    # Multispecies TA/Nanbu timestep sensitivity at fixed physical duration.
    mix_dt_rows = []
    mix_duration = 0.002
    for method, seed0 in (("takizuka_abe", 3600), ("nanbu", 3700)):
        for dt_mix in (1.0e-5, 2.0e-5, 5.0e-5, 1.0e-4):
            nstep_mix = int(round(mix_duration / dt_mix))
            hist_mix = run_test_particle_multispecies_scattering(
                comparison_source.velocity_m_s,
                test_mass_kg=M_ALPHA, test_charge_c=Q_ALPHA,
                field_species=PHYSICAL_FIELDS, dt_s=dt_mix, steps=nstep_mix,
                coulomb_logarithm=LN_LAMBDA, method=method,
                seed=seed0 + nstep_mix, record_every=nstep_mix,
            )
            mix_dt_rows.append({
                "method": method, "substeps_per_species_per_half_pass": 1,
                "dt_s": dt_mix, "steps": nstep_mix,
                "duration_s": nstep_mix * dt_mix,
                "final_mean_energy_ev": hist_mix[-1]["mean_energy_ev"],
                "initial_mean_energy_ev": hist_mix[0]["mean_energy_ev"],
                "fractional_energy_change": hist_mix[-1]["mean_energy_ev"] / hist_mix[0]["mean_energy_ev"] - 1.0,
            })
    write_csv(OUT / "v16_multispecies_timestep_convergence.csv", mix_dt_rows)

    # Timestep convergence at fixed physical duration for both independent samplers.
    convergence_rows = []
    duration = 0.01
    for method, seed0 in (("takizuka_abe", 3300), ("nanbu", 3400)):
        for dt in (1.0e-5, 2.0e-5, 5.0e-5, 1.0e-4):
            steps = int(round(duration / dt))
            hist = run_test_particle_scattering(
                comparison_source.velocity_m_s,
                test_mass_kg=M_ALPHA,
                test_charge_c=Q_ALPHA,
                field_species=proton_bath,
                dt_s=dt,
                steps=steps,
                coulomb_logarithm=LN_LAMBDA,
                method=method,
                seed=seed0 + steps,
                record_every=steps,
            )
            convergence_rows.append({
                "method": method,
                "dt_s": dt,
                "steps": steps,
                "duration_s": steps * dt,
                "final_mean_energy_ev": hist[-1]["mean_energy_ev"],
                "initial_mean_energy_ev": hist[0]["mean_energy_ev"],
                "fractional_energy_change": hist[-1]["mean_energy_ev"] / hist[0]["mean_energy_ev"] - 1.0,
            })
    write_csv(OUT / "v16_timestep_convergence.csv", convergence_rows)
    print("v1.6 runner: single-species timestep scan complete", flush=True)

    # Full-mixture Rosenbluth SDE timestep sensitivity (same alpha1 source,
    # same physical duration, and fixed seed for reproducibility).
    fp_dt_rows = []
    dt_source = build_source("alpha1", events=256, beam_mev=BASE_BEAM_MEV, seed=6111)
    for dt_fp in (2.5e-5, 5.0e-5, 1.0e-4):
        nsteps = int(round(0.05 / dt_fp))
        fp_solver = RosenbluthSlowingDownSolver(
            test_mass_kg=M_ALPHA, test_charge_c=Q_ALPHA,
            field_species=PHYSICAL_FIELDS, coulomb_logarithm=LN_LAMBDA,
            max_dt_k=0.02,
        )
        fp_run = fp_solver.run(
            dt_source.velocity_m_s, dt_s=dt_fp, steps=nsteps,
            alpha_density_m3=ALPHA_DENSITY, seed=6120,
            record_every=nsteps,
        )
        fp_dt_rows.append({
            "dt_s": dt_fp,
            "steps": nsteps,
            "duration_s": nsteps * dt_fp,
            "final_mean_energy_ev": fp_run.snapshots[-1].mean_energy_ev,
            "final_median_energy_ev": fp_run.snapshots[-1].median_energy_ev,
            "electron_deposition_energy_j_m3": fp_run.deposited_energy_j_m3["electron"],
            "proton_deposition_energy_j_m3": fp_run.deposited_energy_j_m3["proton"],
            "thermal_alpha_deposition_energy_j_m3": fp_run.deposited_energy_j_m3["thermal_alpha"],
            "relative_energy_budget_residual": fp_run.relative_energy_budget_residual,
        })
    write_csv(OUT / "v16_rosenbluth_timestep_convergence.csv", fp_dt_rows)
    print("v1.6 runner: Rosenbluth timestep scan complete", flush=True)

    # Marker-count convergence of the two independent test-particle samplers.
    # Three RNG replicates quantify finite-sample stochastic spread.
    particle_rows = []
    count_source = build_source("alpha0", events=512, beam_mev=BASE_BEAM_MEV, seed=7222)
    for event_count in (128, 512):
        initial_subset = count_source.velocity_m_s[:3 * event_count]
        for method in ("takizuka_abe", "nanbu"):
            for replicate in range(3):
                hist = run_test_particle_scattering(
                    initial_subset, test_mass_kg=M_ALPHA, test_charge_c=Q_ALPHA,
                    field_species=proton_bath, dt_s=5.0e-5, steps=50,
                    coulomb_logarithm=LN_LAMBDA, method=method,
                    seed=7300 + event_count + 100 * replicate + (0 if method == "takizuka_abe" else 10_000),
                    record_every=200,
                )
                particle_rows.append({
                    "method": method,
                    "source_events": event_count,
                    "marker_count": int(initial_subset.shape[0]),
                    "replicate": replicate,
                    "duration_s": 0.0025,
                    "final_mean_energy_ev": hist[-1]["mean_energy_ev"],
                    "fractional_energy_change": hist[-1]["mean_energy_ev"] / hist[0]["mean_energy_ev"] - 1.0,
                })
    write_csv(OUT / "v16_mc_particle_number_convergence.csv", particle_rows)

    print("v1.6 runner: timestep convergence scans complete", flush=True)

    # Coulomb-log and entrance-energy sensitivity: initial moments and short
    # time evolutions. Every branch remains separately normalized.
    sensitivity_rows = []
    for channel in ("alpha0", "alpha1"):
        for beam in (0.34, 0.675, 1.85):
            source = build_source(channel, events=256, beam_mev=beam, seed=4550 + int(beam * 100) + (0 if channel == "alpha0" else 1))
            for ln_lam in (10.0, 15.0, 20.0):
                solver = RosenbluthSlowingDownSolver(
                    test_mass_kg=M_ALPHA, test_charge_c=Q_ALPHA,
                    field_species=PHYSICAL_FIELDS,
                    coulomb_logarithm=ln_lam,
                    max_dt_k=0.02,
                )
                speed = np.linalg.norm(source.velocity_m_s, axis=1)
                coeffs = solver._coefficients(source.velocity_m_s)
                initial_rates = {}
                for field, coef in zip(PHYSICAL_FIELDS, coeffs):
                    rate = expected_kinetic_energy_rate_per_marker_j_s(
                        speed, test_mass_kg=M_ALPHA, coefficients=coef
                    )
                    initial_rates[field.name] = float(-ALPHA_DENSITY * np.mean(rate))
                run = solver.run(
                    source.velocity_m_s, dt_s=5.0e-5, steps=200,
                    alpha_density_m3=ALPHA_DENSITY,
                    seed=5000 + int(ln_lam) + int(beam * 100) + (0 if channel == "alpha0" else 10),
                    record_every=100,
                )
                sensitivity_rows.append({
                    "channel": channel,
                    "proton_beam_lab_mev": beam,
                    "entrance_cm_energy_mev": e_cm_from_proton_lab_energy(beam),
                    "coulomb_logarithm": ln_lam,
                    "initial_mean_alpha_energy_mev": float(np.mean(source.kinetic_energy_mev)),
                    "initial_electron_deposition_mw_m3": initial_rates["electron"] / 1e6,
                    "initial_proton_deposition_mw_m3": initial_rates["proton"] / 1e6,
                    "initial_thermal_alpha_deposition_mw_m3": initial_rates["thermal_alpha"] / 1e6,
                    "mean_alpha_energy_after_0p01s_mev": run.snapshots[-1].mean_energy_ev / 1e6,
                    "relative_energy_budget_residual": run.relative_energy_budget_residual,
                })
    write_csv(OUT / "v16_source_and_coulomb_log_sensitivity.csv", sensitivity_rows)

    print("v1.6 runner: source/Coulomb-log sensitivity complete", flush=True)

    summary["numerical_controls"] = {
        "full_mixture_dt_s": DT,
        "full_mixture_steps": STEPS,
        "full_mixture_duration_s": DT * STEPS,
        "alpha_marker_count_per_channel": 1536,
        "illustrative_alpha_population_density_m3": ALPHA_DENSITY,
        "full_mixture_ln_lambda": LN_LAMBDA,
        "source_model": "v1.4 branch-resolved sequential kinematics, alpha0 and alpha1 kept separate; no branch weights",
        "nonrelativistic_boundary": "alpha marker speeds checked against 0.1c; source-energy relativistic discrepancy reported",
        "full_mixture_timestep_convergence_cases": len(fp_dt_rows),
        "multispecies_collision_timestep_cases": len(mix_dt_rows),
        "TA_Nanbu_marker_count_replicates": len(particle_rows),
    }

    with (OUT / "v16_slowing_down_and_collision_validation.json").open("w", encoding="utf-8") as handle:
        json.dump(to_plain(summary), handle, indent=2, sort_keys=True)

    print(json.dumps({
        "version": summary["version"],
        "channel_final_mean_energy_mev": {
            ch: data["snapshots"][-1]["mean_energy_ev"] / 1e6
            for ch, data in channel_summaries.items()
        },
        "test_particle_collision_comparison": comparison_summary,
        "full_mixture_collision_comparison": mix_comparison,
        "multispecies_subcycling_sensitivity_script": "scripts_run_v16_subcycling.py",
        "sensitivity_rows": len(sensitivity_rows),
        "outputs": sorted(p.name for p in OUT.glob("v16_*")),
    }, indent=2))


if __name__ == "__main__":
    main()
