# PARC-Delta v1.3 — finite-parallel-wavenumber kinetic extension

**Status:** implemented collisionless finite-`k_parallel` electrostatic response, parameterized gyrotropic alpha velocity distribution, and numerical recovery of the v1.2 perpendicular control. A conserving Coulomb collision operator is **not implemented**.

## 1. Research question

The v1.2 calculation assumes `k_parallel = 0`. In that limit, a perpendicular alpha-energy spread changes the Bessel residues but does not spread cyclotron-pole frequencies. This is a useful benchmark limit, but it excludes parallel Doppler broadening and parallel Landau/cyclotron resonance. The v1.3 question is whether the root-pole branch remains growing when a finite parallel wavenumber and parallel velocity distribution are admitted.

The alpha distribution is a parameterized gyrotropic ring family:

- perpendicular kinetic energy: positive lognormal quadrature, with its arithmetic mean fixed at 24 keV;
- parallel velocity: Maxwellian with user-controlled `T_parallel`;
- alpha/proton mass ratio: the CODATA value used in the v1.2 physical-mass crossing study.

This is not a measured LAPD distribution and not a p–B11 fusion-product birth spectrum. It is a controlled sensitivity family.

## 2. Thermal-species susceptibility

For a Maxwellian species `s`, the finite-`k_parallel` electrostatic Harris susceptibility is evaluated as

\[
\chi_s = \frac{1}{k^2\lambda_{Ds}^2}
\sum_{n=-N_s}^{N_s}\Gamma_n(b_s)
\left[1 + \frac{\omega}{k_\parallel v_{ts}}Z(\zeta_{ns})\right],
\]

where

\[
k^2=k_\perp^2+k_\parallel^2,\quad
v_{ts}=\sqrt{2T_s/m_s},\quad
\lambda_{Ds}^2=\frac{\epsilon_0 T_s}{n_s q_s^2},
\]

\[
b_s=\frac{k_\perp^2T_s}{m_s\Omega_s^2},\quad
\Gamma_n(b)=e^{-b}I_{|n|}(b),\quad
\zeta_{ns}=\frac{\omega-n\Omega_s}{k_\parallel v_{ts}}.
\]

`Z(zeta) = i sqrt(pi) w(zeta)` is evaluated with the Faddeeva function, providing the Landau analytic continuation. The harmonic sum is symmetric in positive and negative cyclotron harmonics. The `k_parallel = 0` branch is evaluated directly using the perpendicular Bernstein expression to avoid an ill-conditioned limiting calculation.

## 3. Alpha-ring susceptibility

The energetic-ion response uses the gyrotropic Vlasov susceptibility specialized to a perpendicular ring distribution with a Maxwellian parallel factor. Defining

\[
\zeta_{n\alpha}=\frac{\omega-n\Omega_\alpha}
{k_\parallel v_{t\parallel,\alpha}},\qquad
v_{t\parallel,\alpha}=\sqrt{2T_{\parallel,\alpha}/m_\alpha},
\]

and averaging Bessel factors over the perpendicular-energy quadrature gives

\[
\chi_\alpha=\frac{\omega_{p\alpha}^2}{k^2}
\sum_{n=-N_\alpha}^{N_\alpha}\left[
-\left\langle J_n^2\right\rangle
\frac{Z'(\zeta_{n\alpha})}{v_{t\parallel,\alpha}^2}
+2n k_\perp\left\langle\frac{J_nJ_n'}{v_\perp}\right\rangle
\frac{Z(\zeta_{n\alpha})}{k_\parallel v_{t\parallel,\alpha}}
\right].
\]

For `T_parallel = 0`, the code uses the cold-parallel limit

\[
\chi_\alpha=\frac{\omega_{p\alpha}^2}{k^2}
\sum_n\left[
-\frac{k_\parallel^2\langle J_n^2\rangle}
{(\omega-n\Omega_\alpha)^2}
-\frac{2n k_\perp\langle J_nJ_n'/v_\perp\rangle}
{\omega-n\Omega_\alpha}
\right].
\]

At `k_parallel = 0`, this reduces to the v1.2 ring susceptibility, including the finite perpendicular-energy average. This limit is covered by regression tests.

## 4. Numerical validation

The finite-`k_parallel` implementation recovers the v1.2 CODATA-mass perpendicular control:

| Quantity | v1.2 control | v1.3 at `k_parallel = 0` |
|---|---:|---:|
| `omega_r / Omega_p` | 1.5103447207879066 | 1.5103447207879066 |
| `gamma / Omega_p` | 0.0016971465721730727 | 0.0016971465721730727 |
| `|D(omega)|` evaluated at v1.2 root | — | `2.46e-12` |

All generated finite-`k_parallel` roots in the v1.3 scan satisfy `|D| < 7.1e-8`.

### 4.1 Cold parallel alpha beam, zero perpendicular spread

Tracked branch values:

| `k_parallel/k_perp` | `gamma/Omega_p` | Linear branch |
|---:|---:|---|
| 0 | +1.69715e-3 | Growing |
| 1e-3 | +1.64597e-3 | Growing |
| 2e-3 | +1.63102e-4 | Growing |
| 3e-3 | approximately 0 | Marginal |
| 5e-3 | −7.95685e-5 | Damped |
| 1e-2 | −5.74771e-2 | Damped |

The tracked branch becomes marginal near `k_parallel/k_perp = 3e-3` for this cold-parallel alpha case. This is a property of this parameter set and the retained branch, not a universal stability boundary.

### 4.2 Parallel alpha temperature sensitivity

For zero perpendicular-energy spread, the approximate marginal point shifts with `T_parallel`:

| Alpha `T_parallel` | Approximate marginal `k_parallel/k_perp` |
|---:|---:|
| 0 eV | 0.0030 |
| 1 eV | 0.0030 |
| 10 eV | 0.00329 |
| 100 eV | 0.00479 |

These values are linearly interpolated between scan points. They are not experimentally measured thresholds. The non-monotonic dependence occurs because parallel spread changes both the resonant response and the selected root's frequency.

### 4.3 Perpendicular energy-width interaction

At finite `k_parallel`, perpendicular energy width and parallel temperature interact. The code finds cases where increasing energy CV reduces growth strongly, cases where a broad ring remains weakly growing over the scanned interval, and cases where the branch is damped. This non-monotonicity is why a single “finite-width suppression factor” cannot be extrapolated to reactor conditions.

## 5. Collision status — an explicit open gate

The v1.3 model includes collisionless Landau phase mixing through `Z(zeta)`. It does **not** include Coulomb collisions. In particular:

- no constant collision frequency is added to cyclotron poles;
- the v1.2 phenomenological alpha-pole broadening is not imported as a physical collision model;
- no collisional thermalization or irreversible proton heating is inferred.

A conserving collision implementation must include test-particle and field-particle terms and pass discrete conservation and entropy tests. At minimum the numerical operator must demonstrate:

1. particle-number conservation for each species;
2. momentum conservation across the coupled species;
3. total kinetic-energy conservation across the coupled species;
4. non-negative entropy production / a discrete H-theorem;
5. velocity-grid and cyclotron-harmonic convergence;
6. recovery of the collisionless result as collision strength tends to zero.

A published gyrokinetic linearized Landau operator demonstrates the importance of both test-particle and field-particle contributions and finite-Larmor-radius corrections, but it cannot be copied blindly into this ion-Bernstein calculation: the full cyclotron-harmonic kinetic formulation and its finite-Larmor-radius terms must be respected. See Pan & Ernst (2019), DOI `10.1103/PhysRevE.99.023201`, and Li & Ernst (2011), DOI `10.1103/PhysRevLett.106.195002`.

## 6. Limitations

- The 24 keV alpha ring is the LAPD reference case, not the roughly MeV-scale alpha birth distribution from p–B11 fusion.
- The alpha velocity distribution is a parameterized family, not a measured distribution or a reaction-derived slowing-down solution.
- The model is local, homogeneous, electrostatic and linear. It omits electromagnetic coupling, spatial gradients, finite geometry, wave leakage, nonlinear trapping, quasilinear relaxation, ash transport and feedback on fusion reactivity.
- Collisionless Landau damping is not collisional thermalization.
- A growing linear eigenmode does not establish nonlinear saturation, net alpha-energy extraction, irreversible heating, reactor gain or net electricity.

## 7. Reproduction

```bash
PYTHONPATH=src python scripts_run_v13.py
PYTHONPATH=src pytest -q
```

Outputs:

- `results/v13_finite_kparallel_kinetic_results.json`
- `results/v13_finite_kparallel_temperature_scan.csv`
- `results/v13_finite_kparallel_energy_width_scan.csv`

## 8. References

1. H. Qin and N. J. Fisch, “Thresholdless IBW Emission and Alpha-to-Thermal-Ion Energy Channeling via Pole Resonance of Fusion-Product Ions,” arXiv:2609.07732 (2026), https://arxiv.org/abs/2609.07732.
2. “An introduction to perpendicularly propagating Bernstein waves,” *Physics of Plasmas* (2026), DOI: 10.1063/5.0316617. The article discusses the Harris oblique electrostatic dispersion relation and the plasma dispersion function.
3. Q. Pan and D. R. Ernst, “Gyrokinetic Landau collision operator in conservative form,” *Physical Review E* 99, 023201 (2019), DOI: 10.1103/PhysRevE.99.023201.
4. B. Li and D. R. Ernst, “Gyrokinetic Fokker-Planck collision operator,” *Physical Review Letters* 106, 195002 (2011), DOI: 10.1103/PhysRevLett.106.195002.
