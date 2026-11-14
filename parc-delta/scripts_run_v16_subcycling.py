"""Reproduce v1.6 multispecies TA/Nanbu subcycling sensitivity scan."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from scipy.constants import e, m_e, m_p, physical_constants

from parc_delta_v10.pb11_alpha_source import sample_pb11_alpha_birth
from parc_delta_v10.slowing_down import MaxwellianFieldSpecies, RosenbluthSlowingDownSolver
from parc_delta_v10.collisional_scattering import run_test_particle_multispecies_scattering

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results"
OUT.mkdir(exist_ok=True)
M_ALPHA = physical_constants["alpha particle mass"][0]
Q_ALPHA = 2.0 * e
FIELDS = [
    MaxwellianFieldSpecies("electron", m_e, -e, 1.04e20, 1.0e4),
    MaxwellianFieldSpecies("proton", m_p, e, 1.0e20, 1.0e4),
    MaxwellianFieldSpecies("thermal_alpha", M_ALPHA, 2.0 * e, 2.0e18, 1.0e4),
]
DT = 5.0e-5
STEPS = 200
METHODS = (("takizuka_abe", 2502), ("nanbu", 2503))
SUBCYCLES = (1, 4, 8)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--include-32", action="store_true", help="also run 32 substeps per species per half-pass")
    args = parser.parse_args()
    source = sample_pb11_alpha_birth(
        128, channel="alpha0", e_cm_mev=0.6183888798350381,
        seed=1452, frame="beam_lab",
    )
    reference_solver = RosenbluthSlowingDownSolver(
        test_mass_kg=M_ALPHA, test_charge_c=Q_ALPHA,
        field_species=FIELDS, coulomb_logarithm=15.0,
        max_dt_k=0.02,
    )
    reference = reference_solver.run(
        source.velocity_m_s, dt_s=DT, steps=STEPS,
        alpha_density_m3=2.0e18, seed=2501, record_every=STEPS,
    )
    reference_final = reference.snapshots[-1].mean_energy_ev
    initial_energy = reference.snapshots[0].mean_energy_ev
    fp_loss = initial_energy - reference_final

    path = OUT / "v16_multispecies_subcycling_sensitivity.csv"
    if args.include_32:
        if not path.exists():
            raise RuntimeError("run the default subcycling scan before --include-32")
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        rows = [row for row in rows if int(row["substeps_per_species_per_half_pass"]) != 32]
        for method, seed in METHODS:
            history32 = run_test_particle_multispecies_scattering(
                source.velocity_m_s,
                test_mass_kg=M_ALPHA, test_charge_c=Q_ALPHA,
                field_species=FIELDS, dt_s=DT, steps=STEPS,
                coulomb_logarithm=15.0, method=method, seed=seed,
                record_every=STEPS, substeps_per_species=32,
            )
            energy32 = history32[-1]["mean_energy_ev"]
            rows.append({
                "method": method,
                "substeps_per_species_per_half_pass": 32,
                "dt_s": DT,
                "duration_s": DT * STEPS,
                "marker_count": int(source.velocity_m_s.shape[0]),
                "initial_mean_energy_ev": initial_energy,
                "rosenbluth_final_mean_energy_ev": reference_final,
                "final_mean_energy_ev": energy32,
                "relative_final_mean_energy_difference_vs_fp": (energy32 - reference_final) / reference_final,
                "fraction_of_fp_energy_loss_captured": (initial_energy - energy32) / fp_loss,
            })
            print(f"{method} K=32 complete", flush=True)
    else:
        # K=16 is the production comparison already reproduced by the main
        # runner. Reuse its exact fixed-seed value, avoiding a second costly run.
        summary_path = OUT / "v16_slowing_down_and_collision_validation.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        production = summary["full_mixture_collision_method_comparison"]
        if not np.isclose(production["initial_mean_energy_ev"], initial_energy, rtol=1e-12):
            raise RuntimeError("main runner result does not match subcycling source/reference")
        rows = []
        for method, seed in METHODS:
            for k in SUBCYCLES:
                history = run_test_particle_multispecies_scattering(
                    source.velocity_m_s,
                    test_mass_kg=M_ALPHA, test_charge_c=Q_ALPHA,
                    field_species=FIELDS, dt_s=DT, steps=STEPS,
                    coulomb_logarithm=15.0, method=method, seed=seed,
                    record_every=STEPS, substeps_per_species=k,
                )
                final_energy = history[-1]["mean_energy_ev"]
                rows.append({
                    "method": method,
                    "substeps_per_species_per_half_pass": k,
                    "dt_s": DT,
                    "duration_s": DT * STEPS,
                    "marker_count": int(source.velocity_m_s.shape[0]),
                    "initial_mean_energy_ev": initial_energy,
                    "rosenbluth_final_mean_energy_ev": reference_final,
                    "final_mean_energy_ev": final_energy,
                    "relative_final_mean_energy_difference_vs_fp": (final_energy - reference_final) / reference_final,
                    "fraction_of_fp_energy_loss_captured": (initial_energy - final_energy) / fp_loss,
                })
                print(f"{method} K={k} complete", flush=True)
            k16_energy = production["final_mean_energy_ev_by_method"][method]
            rows.append({
                "method": method,
                "substeps_per_species_per_half_pass": 16,
                "dt_s": DT,
                "duration_s": DT * STEPS,
                "marker_count": int(source.velocity_m_s.shape[0]),
                "initial_mean_energy_ev": initial_energy,
                "rosenbluth_final_mean_energy_ev": reference_final,
                "final_mean_energy_ev": k16_energy,
                "relative_final_mean_energy_difference_vs_fp": (k16_energy - reference_final) / reference_final,
                "fraction_of_fp_energy_loss_captured": (initial_energy - k16_energy) / fp_loss,
            })
            print(f"{method} K=16 reused from main runner", flush=True)
    path = OUT / "v16_multispecies_subcycling_sensitivity.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {path.name}: {len(rows)} rows; FP final mean={reference_final:.3f} eV")


if __name__ == "__main__":
    main()
