from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np
from scipy.constants import e, m_p, m_e, physical_constants

from parc_delta_v10.collision_benchmarks import (
    landau_pairwise_energy_exchange,
    landau_spitzer_power_density_w_m3,
    landau_spitzer_temperature_rate_ev_s,
    temperature_ev_from_velocities,
)
from parc_delta_v10.coulomb_mc import maxwellian_velocity_samples
from parc_delta_v10.pb11_alpha_source import (
    e_cm_from_proton_lab_energy,
    sample_pb11_alpha_birth,
)

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)
M_ALPHA = physical_constants["alpha particle mass"][0]
DENSITY = 1.0e20
T_P_EV = 100.0
T_ALPHA_EV = 10.0
LOG_LAMBDA = 11.5


def centered_maxwellian(count: int, mass: float, temperature_ev: float, seed: int) -> np.ndarray:
    v = maxwellian_velocity_samples(
        count, mass_kg=mass, temperature_ev=temperature_ev, seed=seed
    )
    return v - np.mean(v, axis=0)


rows = []
for count in (128, 256, 512, 768, 1024, 1536, 2048):
    vp = centered_maxwellian(count, m_p, T_P_EV, 10)
    va = centered_maxwellian(count, M_ALPHA, T_ALPHA_EV, 11)
    measured = landau_pairwise_energy_exchange(
        species_a="proton", species_b="alpha",
        mass_a_kg=m_p, mass_b_kg=M_ALPHA,
        charge_a_c=e, charge_b_c=2 * e,
        density_a_m3=DENSITY, density_b_m3=DENSITY,
        velocities_a_m_s=vp, velocities_b_m_s=va,
        coulomb_logarithm=LOG_LAMBDA,
        chunk_rows=128,
    )
    temp_p = temperature_ev_from_velocities(vp, m_p)
    temp_a = temperature_ev_from_velocities(va, M_ALPHA)
    ls_rate = landau_spitzer_temperature_rate_ev_s(
        mass_a_kg=m_p, mass_b_kg=M_ALPHA,
        charge_a_c=e, charge_b_c=2 * e,
        density_b_m3=DENSITY,
        temperature_a_ev=temp_p, temperature_b_ev=temp_a,
        coulomb_logarithm=LOG_LAMBDA,
    )
    ls_power = landau_spitzer_power_density_w_m3(
        density_a_m3=DENSITY, temperature_rate_a_ev_s=ls_rate
    )
    rows.append({
        "particles_per_species": count,
        "proton_temperature_ev": temp_p,
        "alpha_temperature_ev": temp_a,
        "pairwise_landau_power_w_m3": measured.q_a_w_m3,
        "landau_spitzer_power_w_m3": ls_power,
        "relative_error": (measured.q_a_w_m3 - ls_power) / ls_power,
        "energy_closure_relative": abs(measured.conservation_residual_w_m3) / abs(measured.q_a_w_m3),
        "pair_count": measured.pair_count,
        "coulomb_logarithm": LOG_LAMBDA,
    })

csv_path = RESULTS / "v15_landau_spitzer_convergence.csv"
with csv_path.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)

summary = {
    "release": "1.5.0-research",
    "benchmark": "proton-alpha Maxwellian Landau-Spitzer initial temperature equilibration",
    "model_scope": "instantaneous pairwise Landau energy-exchange moment; not a time-integrated collision trajectory",
    "parameters": {
        "proton_density_m3": DENSITY,
        "alpha_density_m3": DENSITY,
        "proton_initial_temperature_ev": T_P_EV,
        "alpha_initial_temperature_ev": T_ALPHA_EV,
        "coulomb_logarithm_fixed": LOG_LAMBDA,
        "proton_mass_kg": m_p,
        "alpha_mass_kg": M_ALPHA,
    },
    "rows": rows,
    "best_relative_error": min(rows, key=lambda r: abs(r["relative_error"])),
    "largest_particle_count_relative_error": rows[-1]["relative_error"],
    "largest_particle_count_energy_closure_relative": rows[-1]["energy_closure_relative"],
    "interpretation": "Convergence of the discrete Landau energy-exchange moment toward the analytic Maxwellian Landau-Spitzer rate. Does not establish long-time stochastic orbit accuracy, an H theorem, or a complete collision operator.",
}
json_path = RESULTS / "v15_landau_spitzer_convergence.json"
json_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
print(json.dumps({
    "csv": str(csv_path), "json": str(json_path),
    "largest_particle_count_relative_error": summary["largest_particle_count_relative_error"],
    "largest_particle_count_energy_closure_relative": summary["largest_particle_count_energy_closure_relative"],
}, indent=2))


# Conditional coupling of the two unweighted kinematic alpha branches to
# illustrative Maxwellian background species. No alpha0/alpha1 branch weights
# are applied; each channel is reported independently.
beam_energy_lab_mev = 0.675
e_cm_birth_mev = e_cm_from_proton_lab_energy(beam_energy_lab_mev)
source_event_count = 2000
n_proton = 1.0e20
alpha_density_fraction = 0.02
n_alpha = alpha_density_fraction * n_proton
n_electron = n_proton + 2.0 * n_alpha
background_temperature_ev = 1.0e4
background_count = 2048
v_proton = maxwellian_velocity_samples(
    background_count, mass_kg=m_p,
    temperature_ev=background_temperature_ev, seed=501,
)
v_proton -= np.mean(v_proton, axis=0)
v_electron = maxwellian_velocity_samples(
    background_count, mass_kg=m_e,
    temperature_ev=background_temperature_ev, seed=502,
)
v_electron -= np.mean(v_electron, axis=0)
source_rows = []
for channel, source_seed in (("alpha0", 1001), ("alpha1", 1002)):
    source = sample_pb11_alpha_birth(
        source_event_count, channel=channel,
        e_cm_mev=e_cm_birth_mev, seed=source_seed, frame="cm",
    )
    # The kinematic sample is generated in the reacting-pair CM frame. Remove
    # residual finite-sample bulk velocity before computing thermal-frame
    # collision moments; this does not apply a branch probability.
    alpha_velocity = source.velocity_m_s - np.mean(source.velocity_m_s, axis=0)
    for log_lambda in (10.0, 15.0, 20.0):
        for background_name, background_mass, background_charge, background_density, background_velocity in (
            ("proton", m_p, e, n_proton, v_proton),
            ("electron", m_e, -e, n_electron, v_electron),
        ):
            transfer = landau_pairwise_energy_exchange(
                species_a=f"alpha_{channel}", species_b=background_name,
                mass_a_kg=M_ALPHA, mass_b_kg=background_mass,
                charge_a_c=2.0 * e, charge_b_c=background_charge,
                density_a_m3=n_alpha, density_b_m3=background_density,
                velocities_a_m_s=alpha_velocity,
                velocities_b_m_s=background_velocity,
                coulomb_logarithm=log_lambda, chunk_rows=64,
            )
            source_rows.append({
                "channel": channel,
                "background_species": background_name,
                "beam_energy_lab_mev": beam_energy_lab_mev,
                "entrance_e_cm_mev": e_cm_birth_mev,
                "alpha_density_fraction_of_protons": alpha_density_fraction,
                "background_temperature_ev": background_temperature_ev,
                "coulomb_logarithm": log_lambda,
                "alpha_count": int(alpha_velocity.shape[0]),
                "background_count": int(background_velocity.shape[0]),
                "alpha_mean_energy_mev": float(np.mean(source.kinetic_energy_mev)),
                "alpha_q50_energy_mev": float(np.median(source.kinetic_energy_mev)),
                "alpha_q95_energy_mev": float(np.quantile(source.kinetic_energy_mev, 0.95)),
                "alpha_power_w_m3": transfer.q_a_w_m3,
                "background_power_w_m3": transfer.q_b_w_m3,
                "thermal_moment_closure_relative": abs(transfer.conservation_residual_w_m3)
                    / max(abs(transfer.q_a_w_m3), abs(transfer.q_b_w_m3), 1e-300),
            })

source_csv = RESULTS / "v15_reaction_source_collision_moments.csv"
with source_csv.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(source_rows[0]))
    writer.writeheader()
    writer.writerows(source_rows)
source_json = RESULTS / "v15_reaction_source_collision_moments.json"
source_summary = {
    "release": "1.5.0-research",
    "description": "Conditional initial Landau collision moments for p-B11 alpha birth branches, reported separately.",
    "branching_weights_applied": False,
    "reaction_source_model": "sequential kinematic alpha0 and alpha1 channels; alpha1 uses the v1.4 truncated Breit-Wigner proxy",
    "collision_model": "nonrelativistic Landau pairwise energy-exchange moment with fixed Coulomb logarithm; no time evolution",
    "parameters": {
        "proton_lab_energy_mev": beam_energy_lab_mev,
        "entrance_cm_energy_mev": e_cm_birth_mev,
        "proton_density_m3": n_proton,
        "alpha_density_m3": n_alpha,
        "electron_density_m3": n_electron,
        "alpha_density_fraction_of_protons": alpha_density_fraction,
        "proton_temperature_ev": background_temperature_ev,
        "electron_temperature_ev": background_temperature_ev,
        "events_per_branch": source_event_count,
        "coulomb_logarithms": [10.0, 15.0, 20.0],
    },
    "rows": source_rows,
    "limitations": [
        "alpha0 and alpha1 are not combined because validated channel branching weights and differential cross sections are absent",
        "no R-matrix line shape, angular correlation or target energy-loss correction",
        "nonrelativistic Landau collision operator; relativistic corrections are not included",
        "initial energy-exchange moments only; no alpha slowing-down trajectory, thermalization time or entropy production",
        "background temperatures and alpha density fraction are illustrative inputs, not a self-consistent p-B11 plasma state",
    ],
}
source_json.write_text(json.dumps(source_summary, indent=2) + "\n", encoding="utf-8")
print(json.dumps({
    "source_collision_csv": str(source_csv),
    "source_collision_json": str(source_json),
    "source_collision_rows": len(source_rows),
    "branch_weights_applied": False,
}, indent=2))
