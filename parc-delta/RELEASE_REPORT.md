# PARC-Delta v1.6 — release report

**Release:** 1.6.0-research  
**Date:** 2026-11-01  
**Status:** Research validation package; not a reactor design.

## Release summary

v1.6 adds a time-dependent non-relativistic test-particle alpha slowing-down
solver based on Maxwellian Rosenbluth/Landau coefficients. It also adds
independent test-particle Takizuka–Abe and Nanbu pair-scattering samplers and
connects both to the branch-resolved v1.4 p–11B alpha source.

The principal new result is a classical collisional baseline: under the stated
fixed 10 keV electron/proton/thermal-alpha background, the alpha mean energy
falls from approximately 3.11 MeV to approximately 15 keV over 1 second. The
integrated expected energy-deposition moments route about 73% to electrons,
26–27% to protons and 0.6% to the thermal-alpha bath. The alpha0 and alpha1
kinematic branches remain separate and unweighted.

## Verification

- **76 automated tests passed.**
- All package source and v1.6 runner modules compile.
- Package version reports `1.6.0-research`.
- The v1.6 numerical runner completed and regenerated all v1.6 result files.
- The v1.5 Maxwellian Landau–Spitzer moment benchmark remains in the test
  suite; its Rosenbluth test-particle energy moment agrees with the analytic
  comparator within the configured tolerance.
- The independent single-proton-bath TA/Nanbu comparison agrees with the
  Rosenbluth/Langevin mean energy to better than 0.003% for the reported run.
- In the full electron–proton–thermal-alpha bath, subcycling improves the
  TA/Nanbu agreement with the Rosenbluth/Langevin reference. At 32 substeps
  per species per half-pass, final mean-energy differences are +0.375% (TA)
  and +0.323% (Nanbu). However, the samplers capture only 92.9% and 93.9%
  of the Fokker–Planck-predicted alpha energy loss, respectively. The
  remaining 7.1%/6.1% energy-transfer discrepancy is **open**; final-mean
  agreement must not be mistaken for closure of the transferred-energy moment.

## Model and reference parameters

| Parameter | Value |
|---|---:|
| Proton beam energy | 0.675 MeV (lab) |
| Entrance CM energy | 0.6183888798 MeV |
| Coulomb logarithm | 15 |
| Electron density / temperature | 1.04e20 m^-3 / 10 keV |
| Proton density / temperature | 1.00e20 m^-3 / 10 keV |
| Thermal alpha density / temperature | 2.00e18 m^-3 / 10 keV |
| Test alpha marker normalization | 2.00e18 m^-3 |
| Full-history timestep | 1e-4 s |
| Full-history duration | 1.0 s |
| Test markers per branch | 1,536 |

The test-alpha density is a tracer normalization used to convert per-marker
moments to volumetric powers. It does not back-react on field species. The
background is a reduced p/alpha/e mixture and omits boron-11 ions, fuel
reactant distributions and self-consistent ash evolution.

## Full-history results

| Quantity | alpha0 | alpha1 |
|---|---:|---:|
| Initial non-relativistic mean energy | 3.11317 MeV | 3.11418 MeV |
| Final mean energy | 15.303 keV | 14.734 keV |
| Final median energy | 11.993 keV | 11.634 keV |
| Electron deposition | 728.535 kJ/m^3 | 725.087 kJ/m^3 |
| Proton deposition | 261.553 kJ/m^3 | 266.670 kJ/m^3 |
| Thermal-alpha deposition | 6.031 kJ/m^3 | 6.179 kJ/m^3 |
| Relative stochastic energy-budget residual | 0.347% | 0.477% |

The final mean approaches \(3T/2=15\) keV for a 10 keV three-dimensional
Maxwellian. The deposition fractions are approximately 73% to electrons,
26–27% to protons and 0.6% to thermal alphas. These are conditional results
for the simplified source and fixed background; they are not reactor heating
predictions.

## Independent collision comparators

The TA/Nanbu code uses fixed Maxwellian field-particle reservoirs. Each
alpha marker receives a fresh field-velocity sample, the relative velocity
is rotated, and only the test particle is retained. The full-mixture operator
uses symmetric forward/reverse half-step splitting across electron, proton
and thermal-alpha baths.

**Single proton bath:** 384 markers, 1 eV field temperature, 0.05 s duration.
TA and Nanbu differ from the Rosenbluth/Langevin result by +0.00276% and
+0.000428%, respectively.

**Full three-species bath:** 384 markers, 10 keV field temperatures, 0.01 s
duration. The Rosenbluth/Langevin reference final mean is 2.957205 MeV.
The TA/Nanbu subcycling sweep is:

| Method | Substeps per species per half-pass | Final mean energy | Difference vs. FP | Fraction of FP energy loss captured |
|---|---:|---:|---:|---:|
| TA | 1 | 3.030741 MeV | +2.487% | 52.85% |
| TA | 4 | 3.000950 MeV | +1.479% | 71.95% |
| TA | 8 | 2.989442 MeV | +1.090% | 79.33% |
| TA | 16 | 2.979266 MeV | +0.746% | 85.86% |
| TA | 32 | 2.968290 MeV | +0.375% | 92.89% |
| Nanbu | 1 | 3.018869 MeV | +2.085% | 60.46% |
| Nanbu | 4 | 2.990096 MeV | +1.112% | 78.91% |
| Nanbu | 8 | 2.980226 MeV | +0.778% | 85.24% |
| Nanbu | 16 | 2.972064 MeV | +0.502% | 90.47% |
| Nanbu | 32 | 2.966752 MeV | +0.323% | 93.88% |

The progressive approach toward the Fokker–Planck result is evidence of
substep sensitivity. It is **not** proof of asymptotic convergence. At K=32,
TA still underpredicts the reference alpha energy loss by 7.11%, and Nanbu by
6.12%. Electron collision energy exchange remains especially sensitive to
near-comoving field-particle sampling. More field-particle sampling,
importance sampling, independent realizations and species-resolved
instantaneous-moment checks remain necessary.

## Numerical sensitivity outputs

The release regenerates:
- Rosenbluth/Langevin 25/50/100 microsecond timestep scan over 0.05 s;
- single-proton TA/Nanbu 10/20/50/100 microsecond timestep scan;
- full-mixture TA/Nanbu timestep scan over 0.002 s;
- three-seed TA/Nanbu marker-count scan at 384 and 1,536 markers;
- source beam-energy and Coulomb-log sensitivity over three values each,
  with alpha0 and alpha1 separate.

The scans use limited fixed-seed samples and are not a formal asymptotic
convergence proof. The subcycling sweep uses a single fixed seed and 384
markers, so it is a diagnostic rather than a statistical convergence study.
The full-mixture TA/Nanbu timestep and subcycling results remain sensitive to
resolution and are not claimed to have reached asymptotic convergence.

## Explicit limits

v1.6 does **not** validate:

1. Self-consistent multispecies field-particle back-reaction or a discrete
   H theorem.
2. Full-mixture TA/Nanbu collision-rate convergence (at K=32, transferred
   alpha energy remains 6.1–7.1% below the Rosenbluth reference).
3. Boron-ion collisions, p–11B reactant depletion, relativistic or magnetized
   collision corrections, transport, radiation or ash dynamics.
4. Experimentally validated R-matrix-weighted p–11B birth spectra or branch
   probabilities.
5. Collisional finite-\(k_\parallel\) IBW dispersion, nonlinear saturation,
   irreversible proton heating or direct electrical recovery.
6. Reactor gain, net plant electricity, low-cost power or a novel energy
   generation mechanism.

## Next gate

Resolve the residual full-mixture TA/Nanbu energy-transfer discrepancy.
Increase field-particle sampling per marker and timestep, measure seed
uncertainty, match each species' one-step energy moment independently against
the Rosenbluth coefficients, and add a self-consistent field-particle
conservation test. Only then should the collision model be coupled to the
finite-\(k_\parallel\) IBW kinetic dispersion.

## Reproducibility

```bash
python -m pip install -e ".[test]"
pytest -q
python scripts_run_v16.py
python scripts_run_v16_subcycling.py
python scripts_run_v16_subcycling.py --include-32
```

The subcycling table is retained in
`results/v16_multispecies_subcycling_sensitivity.csv` and detailed in
`docs/MULTISPECIES_SUBCYCLING_v1.6.md`.

See `docs/ALPHA_SLOWING_DOWN_v1.6.md`,
`docs/MULTISPECIES_SUBCYCLING_v1.6.md` and `docs/ACCEPTANCE_GATES.md`.
