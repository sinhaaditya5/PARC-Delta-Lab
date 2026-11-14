# PARC-Delta v1.0 input contract

The CLI accepts one JSON snapshot. It validates and accounts for externally calculated powers; it does not generate plasma coefficients.

## Required shape

```json
{
  "metadata": {
    "run_id": "unique-run-id",
    "distribution_source": "file-or-solver-run-reference",
    "dispersion_solver": "name-and-version",
    "collision_solver": "name-and-version",
    "units": "SI"
  },
  "external_flows": [
    {
      "reservoir": "alpha_fast",
      "power_w": 1.0,
      "direction": "in",
      "label": "fusion_alpha_birth_power",
      "source_ref": "traceable-source-id",
      "sigma_w": 0.1
    },
    {
      "reservoir": "electrons",
      "power_w": 0.1,
      "direction": "out",
      "label": "bremsstrahlung",
      "source_ref": "traceable-model-or-measurement-id"
    }
  ],
  "modes": [
    {
      "name": "IBW-mode-01",
      "energy_j": 1.0e-3,
      "sigma_energy_j": 1.0e-5,
      "source_ref": "wave-solver-output-id",
      "escape_damping_s_inv": 0.01,
      "sigma_escape_s_inv": 0.001,
      "rf_drive_w": 0.0,
      "species_growth_rates": {
        "alpha_fast": {
          "gamma_s_inv": 0.1,
          "sigma_s_inv": 0.01,
          "source_ref": "species-alpha-susceptibility-result",
          "method": "kinetic dielectric decomposition"
        },
        "protons": {
          "gamma_s_inv": -0.08,
          "sigma_s_inv": 0.01,
          "source_ref": "species-proton-susceptibility-result",
          "method": "kinetic dielectric decomposition"
        },
        "boron_ions": {
          "gamma_s_inv": -0.005,
          "sigma_s_inv": 0.001,
          "source_ref": "species-boron-susceptibility-result",
          "method": "kinetic dielectric decomposition"
        },
        "electrons": {
          "gamma_s_inv": -0.005,
          "sigma_s_inv": 0.001,
          "source_ref": "species-electron-susceptibility-result",
          "method": "kinetic dielectric decomposition"
        }
      }
    }
  ],
  "collisional_transfers": [],
  "nonlinear_wave_transfers": [],
  "irreversible_proton_heating_w": null
}
```

**The numerical values above are schema placeholders only. They are not PARC estimates, literature-fit coefficients, or an operating-point example. Do not use them to estimate output.**

## Validation rules

- All energies are joules; powers are watts; growth/damping rates are inverse seconds.
- `gamma_s_inv > 0` means that species drives the mode and loses energy; `< 0` means it damps the mode and receives energy.
- `escape_damping_s_inv` is non-negative.
- `source_ref` and `method` are mandatory for every supplied species rate. Use a synthetic URI only in tests.
- Internal collision and nonlinear wave-to-wave transfers must be directed and non-negative. Reverse the direction rather than using negative power.
- `irreversible_proton_heating_w` must come from a kinetic collision/phase-mixing analysis. Leave it `null` when unavailable. It is not inferred from coherent wave absorption.
- Each scenario must carry source and uncertainty metadata. Correlated uncertainty needs to be propagated upstream; this package's first-order per-rate errors assume independent inputs.

## CLI

```bash
PYTHONPATH=src python -m parc_delta_v10.cli path/to/snapshot.json --output results/ledger.json
```
