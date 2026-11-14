# PARC-Delta v1.5 — Landau–Spitzer collision-rate validation

## Purpose

v1.4 verified exact pairwise momentum and kinetic-energy invariants for its
small-angle relative-velocity rotation. Those invariants are necessary but do
not establish the physical collision rate. v1.5 adds an independent
particle-pair evaluation of the Landau collision operator's thermal-energy
exchange moment and compares it with the analytic Landau–Spitzer result for
Maxwellian species.

## Discrete Landau energy-exchange moment

For two distinct species `a` and `b`, the implementation evaluates the
particle-sum form of Turrell, Sherlock & Rose (2016), Eq. (4.1):

\[
Q_a = 4\pi\ln\Lambda\,
\frac{n_a n_b}{N_aN_b}
\left(\frac{q_aq_b}{4\pi\epsilon_0}\right)^2
\sum_{i=1}^{N_a}\sum_{j=1}^{N_b}
\frac{1}{u_{ij}^3}
\left[
\frac{u_{ij}^2}{m_a}
-\frac{m_a+m_b}{m_am_b}
(\mathbf v_i-\mathbf V_a)\cdot\mathbf u_{ij}
\right],
\]

where \(\mathbf u_{ij}=\mathbf v_i-\mathbf v_j\) and \(\mathbf V_a\) is
the sample drift velocity of species `a`. The reverse moment is evaluated
independently. For zero-drift Maxwellian test distributions,
\(Q_a+Q_b=0\) to floating-point accuracy.

The particle-pair sum is chunked in the `a` index to cap memory use. This is an
instantaneous moment evaluation; it is not a time integrator.

## Analytic Landau–Spitzer comparator

For Maxwellian species, the analytic initial temperature rate is implemented
in eV/s with a sign convention that hot species cool and cold species heat:

\[
\frac{dT_a}{dt} = n_b\frac{8\sqrt{\pi}}{3}
\frac{\sqrt{2m_a}}{m_b}
\left(\frac{q_aq_b}{4\pi\epsilon_0}\right)^2
\ln\Lambda\,
\left(T_a+\frac{m_a}{m_b}T_b\right)^{-3/2}
(T_b-T_a),
\]

where the temperatures inside the power law are in joules. The associated
thermal power density is \(Q_{a,LS}=\frac32 n_a e(dT_a/dt)_{eV/s}\).

**Sign-convention note.** Turrell et al. (2016) Eq. (4.1) defines the
particle-sum moment, and Eq. (3.7) places that moment on the gain side of the
species energy balance. For a hotter species, the discrete Eq. (4.1) moment is
negative, as required for cooling. The printed temperature-difference factor
in Eq. (6.3) of that paper is \(T_a-T_b\), which has the opposite sign from
that physical interpretation and from Eq. (4.1)/(6.2). This package therefore
uses \(T_b-T_a\) in the analytic temperature-rate comparator, so the hotter
species cools and the colder species heats. The comparison is made on this
explicitly corrected sign convention; it is not a literal reproduction of
the sign printed in Eq. (6.3).

## Benchmark setup

- Species: protons and alpha particles.
- Proton temperature: nominal 100 eV.
- Alpha temperature: nominal 10 eV.
- Density of each species for this controlled unit benchmark: \(10^{20}\,m^{-3}\).
- Coulomb logarithm: fixed at 11.5 so the particle sum and analytic comparator
  use exactly the same convention.
- Each distribution is sampled independently from an isotropic Maxwellian
  and recentered to remove finite-sample bulk drift.
- Particle counts are increased from 128 to 2048 per species.

Equal species densities are deliberately used here as a controlled benchmark,
not as a p–B11 reactor composition. The analytic rate includes the actual
sample temperatures, so finite particle sampling does not silently change
the comparator.

## Results

See `results/v15_landau_spitzer_convergence.csv` and
`results/v15_landau_spitzer_convergence.json` for the generated data. The
largest-particle-count row is the principal convergence result. The measured
pairwise moment approaches the analytic Landau–Spitzer energy-exchange rate
as particle count increases, with equal-and-opposite species energy moments.

## Conditional reaction-source coupling

The runner also evaluates the same instantaneous Landau pair moment for the
v1.4 `alpha0` and `alpha1` sequential-kinematic samples against Maxwellian
proton and electron backgrounds. The two channels are never mixed: the
published p–11B literature reports separate channels and differential
cross-section measurements, and the present package does not yet have
validated energy-dependent branch weights or a complete angular model.

For a reproducible sensitivity case, the run uses a 0.675 MeV proton beam on
stationary boron (the relativistically converted entrance CM energy),
\(n_p=10^{20}\,m^{-3}\), \(n_{\alpha}/n_p=0.02\), quasineutral electron density,
and 10 keV proton/electron backgrounds. It uses 2,000 events per branch,
6,000 alpha records per branch, and fixed \(\ln\Lambda=10,15,20\). The alpha
samples are recentered to the reacting-pair CM rest frame before taking the
nonrelativistic thermal moment.

At \(\ln\Lambda=15\), the initial alpha-to-background power moments are:

| Channel | Background | Alpha loss (W m⁻³) | Background gain (W m⁻³) |
|---|---|---:|---:|
| alpha0 | protons | 4.650 × 10⁵ | 4.650 × 10⁵ |
| alpha0 | electrons | 4.344 × 10⁶ | 4.344 × 10⁶ |
| alpha1 | protons | 4.702 × 10⁵ | 4.702 × 10⁵ |
| alpha1 | electrons | 4.946 × 10⁶ | 4.946 × 10⁶ |

The complete 12-row parameter scan is in
`results/v15_reaction_source_collision_moments.csv`. It is conditional on the
chosen alpha density fraction, temperatures and Coulomb logarithm. It does
not combine channels, infer a branching ratio, account for a self-consistent
reactivity, or integrate a slowing-down trajectory. In particular, the
larger electron energy-transfer moment is a result for this specified
10 keV-background case, not a universal p–11B partition.

## Relationship to the stochastic collision step

The v1.4 pairwise stochastic update uses a Gaussian transverse angular
increment whose variance is obtained by integrating small-angle Rutherford
scattering over impact parameter. In the small-step limit, its expected
thermal-energy transfer is the same Landau pair moment. v1.5 makes the
Coulomb logarithm optionally fixed for controlled comparisons; the default
remains velocity-dependent through the Debye screening estimate and
short-distance cutoff.

This release validates the analytic moment and its discrete particle-sum
representation. It does **not** yet establish convergence of long-time
stochastic trajectories to Landau–Spitzer relaxation. That requires an
ensemble-averaged time-history study across particle count and timestep, plus
an independent benchmark (e.g. a Takizuka–Abe/Nanbu or particle-moment
reference implementation).

## Not yet validated

- Long-time temperature equilibration by the v1.4 stochastic step.
- Test-particle slowing-down trajectory and cumulative energy partition for a suprathermal alpha distribution.
- Discrete H theorem / non-negative entropy production.
- Arbitrarily unequal macroparticle weights in the stochastic step.
- Gyrokinetic/finite-Larmor-radius corrections to collision dynamics.
- Coupling of collisions to the finite-\(k_\parallel\) IBW eigenmode.
- Irreversible proton heating or reactor energy gain.

## Literature

1. A. E. Turrell, M. Sherlock & S. J. Rose, “Efficient evaluation of
   collisional energy transfer terms for plasma particle simulations,”
   *Journal of Plasma Physics* 82 (2016), DOI:
   [10.1017/S0022377816000131](https://doi.org/10.1017/S0022377816000131).
2. K. Nanbu, “Theory of cumulative small-angle collisions in plasmas,”
   *Physical Review E* 55 (1997), 4642–4652, DOI:
   [10.1103/PhysRevE.55.4642](https://doi.org/10.1103/PhysRevE.55.4642).
3. C. Wang et al., “Particle simulation of Coulomb collisions: Comparing the
   methods of Takizuka & Abe and Nanbu,” *Journal of Computational Physics*
   227 (2008), DOI: [10.1016/j.jcp.2007.12.027](https://doi.org/10.1016/j.jcp.2007.12.027).

4. S. Taskaev et al., “Measurement of the 11B(p, α0)8Be and the
   11B(p, α1)8Be* reactions cross-sections at the proton energies up to
   2.2 MeV,” *Nuclear Instruments and Methods in Physics Research B* 555
   (2024), 165490, DOI:
   [10.1016/j.nimb.2024.165490](https://doi.org/10.1016/j.nimb.2024.165490).
5. “Study of the energy spectrum of alpha particles in an experiment on
   irradiation of a boron target with a proton beam at the Prometheus
   accelerator,” *Nuclear Instruments and Methods in Physics Research B* 563
   (2025), 165651, DOI:
   [10.1016/j.nimb.2025.165651](https://doi.org/10.1016/j.nimb.2025.165651).
