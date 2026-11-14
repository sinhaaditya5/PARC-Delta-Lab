# PARC-Delta v1.1 — Published linear IBW model reproduction

**Status:** collisionless linear benchmark implemented and tested. This is not a nonlinear kinetic model, a p–B11 reactor model, or proof of net power.

## Primary reference

Hong Qin and Nathaniel J. Fisch, “Thresholdless IBW Emission and Alpha-to-Thermal-Ion Energy Channeling via Pole Resonance of Fusion-Product Ions,” arXiv:2609.07732v2 (15 September 2026). <https://arxiv.org/abs/2609.07732>

The implementation follows the paper's Eqs. (4)–(12), (14)–(18), (22)–(29), and (32)–(38), for the strictly perpendicular, electrostatic, collisionless proton–alpha LAPD reference case.

## Model boundary and assumptions

- Uniform magnetic field, homogeneous plasma, `k_parallel = 0`.
- Electrostatic wave with perturbation convention `exp(i k_perp x - i omega t)` and `omega = omega_r + i gamma`; positive `gamma` means growing amplitude.
- Thermal protons and electrons are isotropic Maxwellians.
- Fusion-product alpha particles are a monoenergetic, strictly perpendicular cold ring.
- Electron and proton finite-Larmor-radius susceptibilities are represented by the Maxwellian harmonic sums.
- Alpha-ring susceptibility is represented by the cold-ring cyclotron-pole sum.
- The reference uses `m_alpha = 4 m_p`, matching the paper's `Omega_alpha/Omega_p = 1/2` harmonic placement. This mass approximation is explicit in the code.
- No collisions, finite `k_parallel`, inhomogeneity, geometry, finite ring width, nonlinear saturation, wave leakage, ash transport, or irreversible thermalization are solved here.

## Reference inputs

| Parameter | Value |
|---|---:|
| Magnetic field | 0.05 T |
| Thermal proton density | 1.0 × 10^17 m^-3 |
| Alpha density / proton density | 0.02 |
| Electron density from quasineutrality | 1.04 × 10^17 m^-3 |
| Proton temperature | 5 eV |
| Electron temperature | 10 eV |
| Perpendicular alpha-ring energy | 24 keV |
| Selected alpha harmonic | n = 3 |
| Perpendicular wave number | 251.74 m^-1 |

At the reference wavenumber, the code obtains `b_p = 1.32319`, `lambda_alpha = 112.70587`, and `3 Omega_alpha / Omega_p = 1.5`.

## Implemented equations

The dimensionless dispersion uses `z = omega^2 / Omega_p^2`:

`D(z,k) = 1 + chi_e_th + chi_p_th + sum_n R_n/(z - z_hn) = 0`.

For thermal species, the susceptibility is evaluated as a sum of positive cyclotron-harmonic residues:

`chi_s_th = -sum_l C_sl / (z - z_sl)`

with the modified-Bessel finite-Larmor-radius coefficients from the reference paper. The alpha-ring residues use

`R_n = -(2 omega_ph^2/lambda_h) n^2 d[J_n(lambda_h)^2]/d lambda_h`.

For a selected energetic-ion pole, the regular thermal-plus-nonselected-pole root is `z_r`, the selected pole is `z_hn`, and the local roots follow

`z_± = (z_r + z_hn)/2 ± 1/2 sqrt((z_r-z_hn)^2 - 4 R_n / D'_reg(z_r))`.

A positive residue is required for the destabilizing root-pole branch in this sign convention. A root crossing alone does not imply instability.

The full rational dispersion is also solved near the local complex root, rather than reporting only the local quadratic approximation.

The near-resonance thermal energy-partition weights are calculated from the reference's species sums `H_s`; the output explicitly calls the proton fraction a **coherent proton response**, not irreversible heat.

## v1.1 reproduction results

### Fixed-wavenumber mode

| Quantity | v1.1 result | Paper value |
|---|---:|---:|
| Real frequency / proton cyclotron frequency | 1.498375 | approximately 1.50 |
| Growth rate / proton cyclotron frequency | 1.3345 × 10^-3 | 1.33 × 10^-3 |
| Growth rate | 6.392 × 10^3 s^-1 | not separately tabulated in the cited result |
| Full dispersion residual | 1.25 × 10^-14 | — |
| Critical alpha density / reference alpha density (local detuned approximation) | 0.598 | 0.62 reported at fixed wavenumber |

The fixed-wavenumber root, sign of the residue, and order of the detuned threshold reproduce the paper's reported LAPD case closely. The 0.598 versus 0.62 threshold difference is small but is retained, not fitted away.

### Linear power partition

| Destination of alpha-particle power loss | v1.1 fraction |
|---|---:|
| Coherent thermal-proton response | 99.9555% |
| Thermal-electron response | 0.03606% |
| Wave electric-field energy | 0.008434% |
| Sum | 100.0000% |

The paper reports approximately 99.96% in the coherent proton component. This is not 99.96% irreversible proton heating. Collision/phase-mixing and nonlinear thermalization remain unmodelled.

### Wavenumber scan

A 141-point scan over 248–255 m^-1 evaluates the local discriminant and residue at the reference alpha density. In this discrete scan, the unstable band is approximately 250.9–252.5 m^-1; the peak local growth is approximately 1.332 × 10^-3 Omega_p. This is a linear root-pole diagnostic, not a controlled-wave operating window or a reactor performance result.

## Important independent numerical check

The code separately solves for the wavenumber at which the *thermal-only* proton IBW root exactly coincides with the third alpha cyclotron pole. It obtains:

- `k_perp = 250.1480 m^-1`;
- `b_p = 1.30651`;
- `lambda_alpha = 111.99312`;
- selected third-harmonic residue `R_3 = -0.07214` in the code's normalized units.

The residue is negative, whereas the root-pole instability requires a positive residue. Therefore, this exact crossing is not destabilizing in this independent reproduction. At the separate reference point `k_perp = 251.74 m^-1`, the detuned root has positive residue and is unstable.

This is not silently reconciled with the paper. The paper identifies an exact thermal crossing near `b_p ≈ 1.31` and explicitly notes that the residue and detuning at that crossing require further numerical revalidation. PARC-Delta records this as an open reproducibility discrepancy. The exact crossing should be rechecked against the authors' parameter and Bessel-argument conventions before drawing a physical conclusion.

## What v1.1 proves—and does not prove

It proves that the implementation reproduces the paper's chosen fixed-wavenumber, collisionless linear LAPD mode and its coherent species power partition within the tolerances above. It also identifies a sign-sensitive exact-crossing check that must be reconciled.

It does **not** prove:

- irreversible proton heating;
- saturation-free, sustained transfer;
- a nonlinear multi-wave cascade;
- a PARC resonance scheduler advantage;
- p–B11 reactor-relevant alpha birth distributions;
- increased p–B11 fusion reactivity;
- fusion gain, positive net electrical output, low LCOE, or commercial readiness.

## Next validation work

1. Ask the authors or independently reconstruct the exact `b_p ≈ 1.31` crossing and `R_3` sign, using the same mass, ring-energy and Bessel conventions.
2. Add finite alpha-ring width and a measured/broadened alpha birth distribution; quantify whether the sharp root-pole effect survives.
3. Add finite `k_parallel`, collisional susceptibility, and finite-system wave leakage, with convergence checks.
4. Couple the linear seed to a nonlinear Vlasov/PIC or quasilinear solver and track plateau formation, phase mixing, trapped particles, proton/electron heating and wave energy.
5. Only then compare no-channeling, single-mode and controlled multi-mode cases under identical inputs.



## v1.2 mass-convention follow-up

The v1.1 crossing result above is specifically tied to `m_alpha=4m_p`. The v1.2 extension makes that convention configurable and reruns the crossing using the CODATA 2022 alpha-to-proton mass ratio. The residue sign becomes positive at a different crossing (`k_perp*=245.1432 m^-1`, `b_p*=1.25475`), but the result still does not match the paper's approximate `b_p≈1.31` statement. At the paper's fixed `k_perp=251.74 m^-1`, the CODATA-mass model is detuned and stable at the reference alpha density. This is a sensitivity diagnosis, not a full source-model reconciliation. See `MASS_CONVENTION_AND_FINITE_WIDTH_v1.2.md`.
