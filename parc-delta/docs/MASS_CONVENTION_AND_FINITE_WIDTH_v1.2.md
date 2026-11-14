# PARC-Delta v1.2 — mass convention, finite-width and resonance-broadening validation

**Status:** implemented and unit-tested as a reduced linear sensitivity model. This is not a complete collisional kinetic model, a nonlinear channeling demonstration, or a p–B11 reactor prediction.

## 1. Why the mass convention matters

The v1.1 reference case set `m_alpha = 4 m_p`, which places the third alpha cyclotron harmonic at exactly `1.5 Omega_p`. This is the mass convention implied by the benchmark's stated harmonic ratio. The physical CODATA 2022 alpha-to-proton mass ratio is `3.972599690252`, not exactly 4.

The v1.2 model makes `alpha_mass_ratio_proton` an explicit input. The default remains `4.0` so the v1.1 published fixed-wavenumber benchmark is preserved as a regression control. The physical-mass sensitivity uses `3.972599690252`.

| Quantity at the exact thermal-root/alpha-pole crossing | `m_alpha = 4 m_p` | CODATA alpha mass |
|---|---:|---:|
| `3 Omega_alpha / Omega_p` | 1.500000 | 1.510346 |
| `k_perp*` (m⁻¹) | 250.148001 | 245.143191 |
| `b_p*` | 1.306506 | 1.254750 |
| `lambda_alpha*` | 111.993121 | 109.375878 |
| `R_3` (normalized code units) | −0.072144 | +0.069990 |
| Destabilizing sign | No | Yes |

The residue sign therefore depends on the alpha mass convention. This is a plausible explanation for the v1.1 sign discrepancy, but it is **not a complete reconciliation**: the physical-mass calculation's `b_p* = 1.25475` does not match the paper's approximate `b_p ≈ 1.31` statement. The parameter convention and exact crossing should be confirmed against the authors' numerical setup before the preprint's exact-resonance claim is treated as independently reproduced.

At the paper's fixed `k_perp = 251.74 m^-1`, the CODATA-mass case is strongly detuned: `Delta z = -0.040881`, `R_3 = +0.013983`, and the local critical alpha-density fraction is approximately `78.97` times the reference alpha density. It is not unstable at the reference density. Thus, the v1.1 fixed-wavenumber reproduction is specifically the `4 m_p` benchmark case; it must not be silently relabelled as an exact-mass reproduction.

## 2. Finite-width alpha-ring model

The cold alpha ring in v1.1 is generalized to a positive lognormal distribution of perpendicular kinetic energy:

- arithmetic mean energy remains 24 keV;
- the input width is the coefficient of variation, `CV = standard_deviation(E_perp) / mean(E_perp)`;
- the quadrature integrates the alpha-ring residue over energy;
- Gauss–Hermite quadrature uses `roots_hermite` and the order is recorded in every result.

The averaged residue is

\[
\bar{R}_n(k_\perp)=\int_0^\infty p(E_\perp)\,R_n\!\left(\lambda(E_\perp)\right)\,dE_\perp,
\qquad
\lambda(E_\perp)=\frac{k_\perp}{\Omega_\alpha}
\sqrt{\frac{2E_\perp}{m_\alpha}}.
\]

An important property of the strictly perpendicular, homogeneous-field model is that the cyclotron pole location is independent of perpendicular speed:

\[
\chi_\alpha(z,k_\perp)=\int p(E_\perp)\sum_n\frac{R_n(E_\perp)}{z-z_{hn}}dE_\perp
=\sum_n\frac{\bar R_n}{z-z_{hn}}.
\]

Consequently, perpendicular energy spread **averages the residues but does not broaden the pole frequencies** in this reduced model. Finite `k_parallel`, a parallel-velocity distribution, magnetic-field inhomogeneity, and finite-system effects are required to introduce additional resonance broadening mechanisms.

The sensitivity scan is performed at the exact thermal-root/third-alpha-pole crossing for the CODATA alpha mass (`k_perp* = 245.14319093 m^-1`).

| Alpha-energy CV | Quadrature order | Averaged `R_3` | `gamma / Omega_p` | Growth vs cold ring |
|---:|---:|---:|---:|---:|
| 0% | 64 | 0.0699902 | 1.69715 × 10⁻³ | 100.0% |
| 1% | 64 | 0.0376089 | 1.24408 × 10⁻³ | 73.3% |
| 2% | 64 | 0.0057441 | 4.86198 × 10⁻⁴ | 28.6% |
| 5% | 128 | 0.0006701 | 1.66063 × 10⁻⁴ | 9.78% |
| 10% | 128 | 0.0006796 | 1.67238 × 10⁻⁴ | 9.85% |
| 20% | 512 | 0.0007180 | 1.71898 × 10⁻⁴ | 10.13% |

The non-monotonic behavior at larger CV is expected from averaging an oscillatory Bessel-function coupling. A wider distribution is not guaranteed to reduce the averaged residue monotonically. The quadrature requirement is raised above 10% CV; CV values above 20% are outside the validated range of this release.

These widths are controlled sensitivity inputs, not measured LAPD alpha spectra. The 24 keV ring is the paper's LAPD benchmark and is not a p–B11 fusion-product alpha birth distribution.

## 3. Phenomenological alpha-pole broadening

A second sensitivity calculation replaces each alpha-harmonic denominator by

\[
\frac{R_n}{(\omega+i\nu_\alpha)^2-n^2\Omega_\alpha^2},
\]

where `nu_alpha` is normalized to `Omega_p`. This corresponds to shifting the alpha poles to `omega = ± n Omega_alpha − i nu_alpha`. It is a damped-pole/decorrelation proxy, not a Coulomb Fokker–Planck or Landau collision operator. The thermal proton and electron susceptibilities remain collisionless.

At the physical-mass exact crossing, `nu_alpha / Omega_p = 10^-3` changes the growth as follows:

| Alpha-energy CV | Unbroadened `gamma / Omega_p` | Broadened `gamma / Omega_p` | Remaining growth |
|---:|---:|---:|---:|
| 0% | 1.69715 × 10⁻³ | 1.26925 × 10⁻³ | 74.8% |
| 2% | 4.86198 × 10⁻⁴ | 1.97415 × 10⁻⁴ | 40.6% |
| 5% | 1.66063 × 10⁻⁴ | 2.68566 × 10⁻⁵ | 16.2% |

Alpha-pole broadening reduces the growth rate in this scan but does not eliminate it at the tested rates. This model cannot establish a collisional stabilization threshold because it does not include a validated Coulomb collision operator or thermal-species damping. No conversion of coherent proton-wave response into irreversible proton heat is calculated.

## 4. Numerical verification and artifacts

- Full repository tests: **34 passed**.
- Full complex roots are checked by normalized dispersion residuals below `1e-8` in the reported runs.
- The 5% energy-CV residue was checked at quadrature orders 32, 64 and 128.
- The 20% energy-CV residue was checked at quadrature orders 512 and 768.
- `scripts_run_v12.py` regenerates the JSON and CSV sensitivity outputs.

Generated outputs:

- `results/v12_mass_convention_sensitivity.json`
- `results/v12_mass_convention_sensitivity.csv`
- `results/v12_finite_width_sensitivity.csv`
- `results/v12_alpha_pole_broadening_sensitivity.csv`
- `results/v12_finite_width_and_broadening.json`

## 5. What v1.2 establishes—and does not establish

It establishes that (i) the exact-crossing residue sign is sensitive to the alpha mass convention; (ii) finite perpendicular energy width can strongly reduce the coherent root–pole growth in this LAPD reference case; and (iii) a phenomenological alpha-pole width further reduces the mode growth.

It does **not** establish a realistic Coulomb collision rate, a finite-`k_parallel` kinetic response, p–B11 alpha-source spectrum, nonlinear saturation, proton thermalization, multi-wave scheduling advantage, fusion gain, net electricity, LCOE, or commercial readiness. The results do not support an abundant-cheap-electricity claim.

## References

- H. Qin and N. J. Fisch, “Thresholdless IBW Emission and Alpha-to-Thermal-Ion Energy Channeling via Pole Resonance of Fusion-Product Ions,” arXiv:2609.07732v2 (2026), <https://arxiv.org/abs/2609.07732>.
- NIST/CODATA 2022, alpha-particle mass and alpha-particle-to-proton mass ratio, <https://physics.nist.gov/cuu/pdf/all.pdf>.
