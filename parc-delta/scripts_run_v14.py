"""Generate PARC-Delta v1.4 p-B11 source and Coulomb-MC benchmark outputs."""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np
from scipy.constants import e, m_e, m_p, physical_constants

from parc_delta_v10.coulomb_mc import (
    CollisionSpecies,
    MultiSpeciesCoulombMonteCarlo,
    maxwellian_velocity_samples,
)
from parc_delta_v10.pb11_alpha_source import (
    BE8_EXCITED_WIDTH_MEV,
    Q_TOTAL_MEV,
    e_cm_from_proton_lab_energy,
    gyrotropic_velocity_histogram,
    sample_pb11_alpha_birth,
)
from scipy.constants import epsilon_0

ROOT = Path(__file__).parent
OUT = ROOT / "results"
OUT.mkdir(parents=True, exist_ok=True)
M_ALPHA = physical_constants["alpha particle mass"][0]


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"No rows to write: {path}")
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    source_rows: list[dict] = []
    gyrotropic_rows: list[dict] = []
    summaries: list[dict] = []
    beam_energies = [0.34, 0.675, 1.85, 2.57, 4.73]
    event_count = 4000
    seed_base = 1400
    run_index = 0
    for e_lab in beam_energies:
        ecm = e_cm_from_proton_lab_energy(e_lab)
        for channel in ("alpha0", "alpha1"):
            sample = sample_pb11_alpha_birth(
                event_count,
                channel=channel,
                e_cm_mev=ecm,
                seed=seed_base + run_index,
                frame="beam_lab",
            )
            sample_cm = sample_pb11_alpha_birth(
                event_count,
                channel=channel,
                e_cm_mev=ecm,
                seed=seed_base + run_index,
                frame="cm",
            )
            run_index += 1
            speed_max = float(np.max(np.linalg.norm(sample_cm.velocity_m_s, axis=1)))
            projection = gyrotropic_velocity_histogram(
                sample_cm,
                v_parallel_edges_m_s=np.linspace(-1.05 * speed_max, 1.05 * speed_max, 65),
                v_perp_edges_m_s=np.linspace(0.0, 1.05 * speed_max, 65),
            )
            for ipar, vpar_center in enumerate(projection["v_parallel_centers_m_s"]):
                for iperp, vperp_center in enumerate(projection["v_perp_centers_m_s"]):
                    gyrotropic_rows.append({
                        "incident_proton_lab_energy_mev": e_lab,
                        "entrance_cm_energy_mev": ecm,
                        "channel": channel,
                        "v_parallel_m_s": float(vpar_center),
                        "v_perp_m_s": float(vperp_center),
                        "normalized_f_v_s3_per_m3": float(projection["f_v_s3_per_m3"][ipar, iperp]),
                        "velocity_cell_volume_m3_per_s3": float(projection["cell_volume_m3_per_s3"][ipar, iperp]),
                    })
            energies_by_role = {}
            energies_by_role_cm = {}
            for role in ("primary", "be8_daughter_1", "be8_daughter_2"):
                mask_lab = sample.role == role
                energies = sample.kinetic_energy_mev[mask_lab]
                mask_cm = sample_cm.role == role
                energies_cm = sample_cm.kinetic_energy_mev[mask_cm]
                def energy_summary(values):
                    mode_counts, mode_edges = np.histogram(values, bins=240, range=(0.0, 12.0))
                    mode_idx = int(np.argmax(mode_counts))
                    return {
                        "mean_mev": float(np.mean(values)),
                        "std_mev": float(np.std(values)),
                        "q05_mev": float(np.quantile(values, 0.05)),
                        "median_mev": float(np.quantile(values, 0.50)),
                        "q95_mev": float(np.quantile(values, 0.95)),
                        "histogram_mode_mev": float(0.5 * (mode_edges[mode_idx] + mode_edges[mode_idx + 1])),
                        "histogram_bin_width_mev": float(mode_edges[1] - mode_edges[0]),
                    }
                energies_by_role[role] = energy_summary(energies)
                energies_by_role_cm[role] = energy_summary(energies_cm)
            summaries.append({
                "incident_proton_lab_energy_mev": e_lab,
                "entrance_cm_energy_mev": ecm,
                "channel": channel,
                "events": event_count,
                "alphas": int(sample.kinetic_energy_mev.size),
                "event_total_alpha_kinetic_energy_lab_mev_mean": float(
                    np.mean(np.bincount(sample.event_id, weights=sample.kinetic_energy_mev))
                ),
                "expected_q_plus_incident_lab_energy_mev": Q_TOTAL_MEV + e_lab,
                "event_total_alpha_kinetic_energy_cm_mev_mean": float(
                    np.mean(np.bincount(sample_cm.event_id, weights=sample_cm.kinetic_energy_mev))
                ),
                "expected_q_plus_ecm_mev": Q_TOTAL_MEV + ecm,
                "mean_pitch_cosine_lab": float(np.mean(sample.pitch_cosine)),
                "mean_pitch_cosine_cm": float(np.mean(sample_cm.pitch_cosine)),
                "per_role_energy_lab_mev": energies_by_role,
                "per_role_energy_cm_mev": energies_by_role_cm,
                "be8_relative_energy_mev": {
                    "mean": float(np.mean(sample.be8_relative_energy_mev)),
                    "std": float(np.std(sample.be8_relative_energy_mev)),
                    "q05": float(np.quantile(sample.be8_relative_energy_mev, 0.05)),
                    "median": float(np.quantile(sample.be8_relative_energy_mev, 0.50)),
                    "q95": float(np.quantile(sample.be8_relative_energy_mev, 0.95)),
                },
                "branching_fraction": None,
                "cross_section_weighting": "not applied",
                "detector_response": "not applied",
                "angular_distribution": "isotropic sequential-decay approximation",
            })
            for idx in range(sample.kinetic_energy_mev.size):
                source_rows.append({
                    "incident_proton_lab_energy_mev": e_lab,
                    "entrance_cm_energy_mev": ecm,
                    "channel": channel,
                    "event_id": int(sample.event_id[idx]),
                    "alpha_role": str(sample.role[idx]),
                    "kinetic_energy_mev": float(sample.kinetic_energy_mev[idx]),
                    "vx_m_s": float(sample.velocity_m_s[idx, 0]),
                    "vy_m_s": float(sample.velocity_m_s[idx, 1]),
                    "vz_m_s": float(sample.velocity_m_s[idx, 2]),
                    "pitch_cosine": float(sample.pitch_cosine[idx]),
                })
    write_csv(OUT / "v14_pb11_alpha_birth_spectra.csv", source_rows)
    write_csv(OUT / "v14_pb11_alpha_gyrotropic_source_grid.csv", gyrotropic_rows)
    summary_rows = []
    for item in summaries:
        primary = item["per_role_energy_cm_mev"]["primary"]
        summary_rows.append({
            "incident_proton_lab_energy_mev": item["incident_proton_lab_energy_mev"],
            "entrance_cm_energy_mev": item["entrance_cm_energy_mev"],
            "channel": item["channel"],
            "primary_alpha_cm_mean_mev": primary["mean_mev"],
            "primary_alpha_cm_median_mev": primary["median_mev"],
            "primary_alpha_cm_histogram_mode_mev": primary["histogram_mode_mev"],
            "primary_alpha_cm_q05_mev": primary["q05_mev"],
            "primary_alpha_cm_q95_mev": primary["q95_mev"],
            "be8_daughter_1_cm_median_mev": item["per_role_energy_cm_mev"]["be8_daughter_1"]["median_mev"],
            "be8_daughter_2_cm_median_mev": item["per_role_energy_cm_mev"]["be8_daughter_2"]["median_mev"],
            "branching_fraction": "not assigned",
        })
    write_csv(OUT / "v14_pb11_alpha_source_summary.csv", summary_rows)

    # A separate equilibrium-mixture collision verification. This isolates
    # conservation mechanics from the as-yet-uncoupled reaction-born alpha F.
    n_p = 1.0e17
    n_alpha = 0.5e17
    n_e = n_p + 2.0 * n_alpha
    counts = {"electron": 48, "proton": 24, "alpha": 12}
    t_ev = 1.0e4
    macro_density = n_p / counts["proton"]
    assert abs(n_alpha / counts["alpha"] - macro_density) / macro_density < 1e-12
    assert abs(n_e / counts["electron"] - macro_density) / macro_density < 1e-12
    species = [
        CollisionSpecies("electron", m_e, -e, n_e, t_ev,
            maxwellian_velocity_samples(counts["electron"], mass_kg=m_e, temperature_ev=t_ev, seed=14)),
        CollisionSpecies("proton", m_p, e, n_p, t_ev,
            maxwellian_velocity_samples(counts["proton"], mass_kg=m_p, temperature_ev=t_ev, seed=15)),
        CollisionSpecies("alpha", M_ALPHA, 2 * e, n_alpha, t_ev,
            maxwellian_velocity_samples(counts["alpha"], mass_kg=M_ALPHA, temperature_ev=t_ev, seed=16)),
    ]
    operator = MultiSpeciesCoulombMonteCarlo(species)
    collision_diag = operator.step(1.0e-8, seed=17)
    collision_report = {
        "operator": "all-pairs stochastic weak-deflection Coulomb Monte Carlo (Landau limit)",
        "screening_model": operator.debye_length_source,
        "initial_conditions": {
            "n_proton_m3": n_p,
            "n_alpha_m3": n_alpha,
            "n_electron_m3": n_e,
            "temperature_ev_all_species": t_ev,
            "macroparticle_counts": counts,
            "equal_macroparticle_number_weight_m3": macro_density,
        },
        "time_step_s": 1.0e-8,
        "random_seed": 17,
        "diagnostics": {
            "pair_count": collision_diag.pair_count,
            "skipped_strong_coupling_pairs": collision_diag.skipped_strong_coupling_pairs,
            "max_pair_deflection_rad": collision_diag.max_pair_deflection_rad,
            "debye_length_m": collision_diag.debye_length_m,
            "coulomb_log_min": collision_diag.coulomb_log_min,
            "coulomb_log_max": collision_diag.coulomb_log_max,
            "relative_momentum_error": collision_diag.relative_momentum_error,
            "relative_energy_error": collision_diag.relative_energy_error,
            "momentum_density_before_kg_m2_s": collision_diag.momentum_density_before,
            "momentum_density_after_kg_m2_s": collision_diag.momentum_density_after,
            "energy_density_before_j_m3": collision_diag.energy_density_before_j_m3,
            "energy_density_after_j_m3": collision_diag.energy_density_after_j_m3,
            "particle_counts_before": collision_diag.particle_counts_before,
            "particle_counts_after": collision_diag.particle_counts_after,
        },
        "status": "conservation-mechanics benchmark only; not a slowing-down prediction",
    }
    (OUT / "v14_coulomb_mc_conservation_benchmark.json").write_text(
        json.dumps(collision_report, indent=2), encoding="utf-8"
    )

    # Source-to-collision plumbing check: 6 alpha samples from two alpha1
    # events collide with thermal electron/proton macro-particles. The screening
    # length is supplied from the Maxwellian e/p background only; no scalar-T
    # Debye contribution is assigned to the nonthermal birth alphas.
    birth = sample_pb11_alpha_birth(2, channel="alpha1", e_cm_mev=0.620, seed=180, frame="cm")
    source_np, source_na = 1.0e17, 0.5e17
    source_ne = source_np + 2.0 * source_na
    source_counts = {"electron": 24, "proton": 12, "alpha_birth": 6}
    source_weight = source_np / source_counts["proton"]
    assert abs(source_na / source_counts["alpha_birth"] - source_weight) / source_weight < 1e-12
    assert abs(source_ne / source_counts["electron"] - source_weight) / source_weight < 1e-12
    te_j = t_ev * e
    tp_j = t_ev * e
    lambda_background = math.sqrt(
        epsilon_0 / (source_ne * e**2 / te_j + source_np * e**2 / tp_j)
    )
    source_species = [
        CollisionSpecies("electron", m_e, -e, source_ne, t_ev,
            maxwellian_velocity_samples(source_counts["electron"], mass_kg=m_e, temperature_ev=t_ev, seed=181)),
        CollisionSpecies("proton", m_p, e, source_np, t_ev,
            maxwellian_velocity_samples(source_counts["proton"], mass_kg=m_p, temperature_ev=t_ev, seed=182)),
        CollisionSpecies("alpha_birth", M_ALPHA, 2 * e, source_na, 1.0e6, birth.velocity_m_s),
    ]
    source_operator = MultiSpeciesCoulombMonteCarlo(
        source_species, debye_length_m=lambda_background
    )
    source_diag = source_operator.step(1.0e-8, seed=183)
    source_collision_report = {
        "initial_alpha_source": "alpha1 sequential decay; 2 reaction events / 6 alpha particles; E_cm=0.620 MeV",
        "background": "Maxwellian electrons and protons at 10 keV",
        "screening_length_m": lambda_background,
        "screening_scope": "Maxwellian electron/proton background only; nonthermal alpha contribution to screening omitted",
        "equal_macroparticle_number_weight_m3": source_weight,
        "time_step_s": 1.0e-8,
        "diagnostics": {
            "pair_count": source_diag.pair_count,
            "skipped_strong_coupling_pairs": source_diag.skipped_strong_coupling_pairs,
            "max_pair_deflection_rad": source_diag.max_pair_deflection_rad,
            "coulomb_log_min": source_diag.coulomb_log_min,
            "coulomb_log_max": source_diag.coulomb_log_max,
            "relative_momentum_error": source_diag.relative_momentum_error,
            "relative_energy_error": source_diag.relative_energy_error,
            "particle_counts_before": source_diag.particle_counts_before,
            "particle_counts_after": source_diag.particle_counts_after,
        },
        "status": "source-to-collision plumbing and invariant check only; two events are not a slowing-down simulation",
    }
    (OUT / "v14_source_coupled_collision_smoke_test.json").write_text(
        json.dumps(source_collision_report, indent=2), encoding="utf-8"
    )

    report = {
        "title": "PARC-Delta v1.4 reaction-source and conserving Coulomb-collision prototype",
        "version": "1.4.0-research",
        "reaction_source": {
            "reaction": "p + 11B -> alpha + 8Be -> 3 alpha",
            "q_total_mev_from_nuclear_mass_balance": Q_TOTAL_MEV,
            "nuclear_mass_convention": "CODATA proton and alpha nuclear masses; 11B atomic mass minus five electron masses; electron binding energy neglected",
            "channels": ["alpha0: 8Be ground-state branch", "alpha1: first-excited-state branch"],
            "alpha0_be8_relative_energy_mev": 0.09184,
            "alpha1_be8_resonance_energy_mev": 3.028,
            "alpha1_be8_resonance_width_mev": BE8_EXCITED_WIDTH_MEV,
            "method": "relativistic sequential two-body kinematics; isotropic primary and secondary decay directions",
            "gyrotropic_projection": "normalized probability density f(v_parallel,v_perp) in the reacting-pair CM frame; 2*pi*v_perp velocity-space Jacobian included",
            "sampling": summaries,
            "weights": "No branch fractions or differential cross-section weights assumed; channels kept separate.",
            "not_included": ["R-matrix line shape", "reaction differential cross section", "branching fractions", "reactant distribution convolution", "solid/plasma stopping", "detector acceptance and response"],
            "external_spectrum_comparison": {
                "reference": "Mazzucconi et al. (2025), spectra reported in the CM frame; primary alpha1-associated feature described as roughly 4.5-7 MeV across incident proton energies 0.34-4.73 MeV",
                "model_check": "The present alpha1 CM primary histogram mode is below 4.5 MeV for the 0.34 and 0.675 MeV beam cases. The paper describes peak locations while this implementation estimates modes from finite Monte Carlo samples with a 0.05 MeV histogram bin; this is a preliminary mismatch diagnostic, not a like-for-like detector-level validation.",
                "likely_model_gaps": ["simple truncated Cauchy resonance line shape", "omitted energy-dependent penetrability and R-matrix interference", "isotropic angular approximation", "no detector/target response convolution"],
            },
        },
        "collision_operator": {
            "implemented": True,
            "type": "stochastic pairwise weak-deflection Coulomb Monte Carlo in the Landau limit",
            "pair_update": "rotate relative velocity at fixed magnitude; update both partners in their pair centre-of-mass frame",
            "cutoffs": "Debye screening upper impact parameter; max(classical 90-degree impact parameter, de Broglie wavelength) lower impact parameter",
            "requirement": "equal physical number weight per macroparticle across all species",
            "benchmark": collision_report,
            "source_coupled_smoke_test": source_collision_report,
            "scope_limits": [
                "not a deterministic finite-grid Landau operator",
                "not a finite-Larmor-radius gyrokinetic operator",
                "no discrete H-theorem proof; entropy monotonicity is not claimed",
                "strong-coupling pairs with non-positive Coulomb logarithm are skipped and counted",
                "not yet coupled to the linear IBW eigenmode or alpha susceptibility",
            ],
        },
        "release_gates": {
            "reaction_birth_kinematics": "implemented for separate alpha0/alpha1 sequential channels; independent validation against differential spectra still required",
            "coulomb_pair_invariants": "implemented and tested at macro-particle level",
            "full_landau_h_theorem": "open",
            "reaction_source_to_gyrotropic_susceptibility": "open",
            "collisionally modified_ibw_root": "open",
            "irreversible_proton_heating": "not calculated",
            "reactor_gain_and_net_electricity": "not calculated",
        },
    }
    (OUT / "v14_pb11_alpha_source_and_collision_results.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )

    print(json.dumps({
        "spectrum_rows": len(source_rows),
        "gyrotropic_grid_rows": len(gyrotropic_rows),
        "source_cases": len(summaries),
        "source_collision_pairs": source_diag.pair_count,
        "source_collision_relative_momentum_error": source_diag.relative_momentum_error,
        "source_collision_relative_energy_error": source_diag.relative_energy_error,
        "collision_pairs": collision_diag.pair_count,
        "relative_momentum_error": collision_diag.relative_momentum_error,
        "relative_energy_error": collision_diag.relative_energy_error,
        "debye_length_m": collision_diag.debye_length_m,
        "coulomb_log_range": [collision_diag.coulomb_log_min, collision_diag.coulomb_log_max],
    }, indent=2))


if __name__ == "__main__":
    main()
