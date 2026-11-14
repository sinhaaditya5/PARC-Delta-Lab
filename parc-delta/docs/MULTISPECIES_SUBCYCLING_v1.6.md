# PARC-Delta v1.6 — full-mixture TA/Nanbu subcycling sensitivity

## Purpose

The initial three-species test-particle comparison showed that the Takizuka–Abe
(TA) and Nanbu samplers under-predicted the Rosenbluth/Langevin alpha energy
loss. This experiment varies the number of small-angle collision substeps per
field species and per symmetric half-pass. It tests whether that discrepancy
is a finite-step artifact. It does not establish asymptotic convergence.

## Reproducible conditions

- Alpha source: v1.4 `alpha0` sequential-decay kinematic branch.
- Proton beam: 0.675 MeV lab, stationary B-11 target; entrance CM energy
  0.618388879835 MeV.
- Alpha markers: 384, generated from 128 reaction events.
- Field species: electrons, protons and thermal alphas.
- Field densities: 1.04e20, 1.00e20 and 2.00e18 m^-3, respectively.
- Field temperatures: 10 keV for all three Maxwellian baths.
- Coulomb logarithm: 15.
- Outer timestep: 50 microseconds; 200 steps; total duration 0.01 s.
- Fixed source and method RNG seeds as recorded in
  `scripts_run_v16_subcycling.py`.
- Test-particle treatment: field reservoirs are resampled and remain fixed;
  there is no field-particle back-reaction.

The Rosenbluth/Langevin reference uses the same source-marker realization and
has initial mean alpha energy 3,113,176.141 eV and final mean energy
2,957,205.233 eV. Its mean energy loss is therefore 155,970.908 eV per
marker over the 0.01 s interval.

## Results

| Method | Substeps per field species per half-pass | Final mean alpha energy (eV) | Difference in final mean vs. F-P | Fraction of F-P energy loss captured |
|---|---:|---:|---:|---:|
| Takizuka–Abe | 1 | 3,030,741.066 | +2.4867% | 52.8529% |
| Takizuka–Abe | 4 | 3,000,949.662 | +1.4792% | 71.9535% |
| Takizuka–Abe | 8 | 2,989,441.937 | +1.0901% | 79.3316% |
| Takizuka–Abe | 16 | 2,979,265.706 | +0.7460% | 85.8560% |
| Takizuka–Abe | 32 | 2,968,290.097 | +0.3748% | 92.8930% |
| Nanbu | 1 | 3,018,869.201 | +2.0852% | 60.4644% |
| Nanbu | 4 | 2,990,096.459 | +1.1122% | 78.9119% |
| Nanbu | 8 | 2,980,226.060 | +0.7785% | 85.2403% |
| Nanbu | 16 | 2,972,063.918 | +0.5025% | 90.4734% |
| Nanbu | 32 | 2,966,751.984 | +0.3228% | 93.8791% |

At K=32, the absolute final-mean differences look small because the remaining
alpha energy is still about 2.97 MeV. The energy-transfer metric is more
discriminating: TA captures 92.893% and Nanbu 93.879% of the F-P predicted
loss. The remaining transfer shortfalls are 7.107% and 6.121%, respectively.
The pair samplers therefore remain under-dissipative relative to the
Rosenbluth reference over this test interval.

## Interpretation and limitations

The monotonic approach toward the F-P reference with increased subcycling is
consistent with finite-step error in the pair update. It does not prove that
subcycling is the only source of discrepancy. The scan uses one source
realization, one fixed seed per sampler, 384 markers and a 10 ms interval.
There are no statistical confidence intervals and no demonstrated
asymptotic convergence rate.

The electron contribution is especially challenging because the velocity
space collision moment is sensitive to near-comoving test/field pairs. This
is a candidate explanation for the remaining difference, not a proven
attribution. Further work needs multiple independent seeds, more field
samples per test marker, species-resolved one-step moments, an importance
sampling study and a full-mixture moment comparison against the analytic
Rosenbluth coefficients.

The TA/Nanbu methods here are fixed-background test-particle adaptations.
They do not conserve the energy and momentum of a dynamically evolving
multispecies plasma and do not establish a discrete H theorem. They must not
be used as validated collisional inputs to the IBW or reactor energy balance
until these gates close.

## Reproduction

From the package root:

```bash
PYTHONPATH=src python scripts_run_v16_subcycling.py
PYTHONPATH=src python scripts_run_v16_subcycling.py --include-32
```

The first command regenerates K=1, 4, 8 and reuses the exact K=16 values from
the primary runner. The second adds the more expensive K=32 rows. Output:
`results/v16_multispecies_subcycling_sensitivity.csv`.
