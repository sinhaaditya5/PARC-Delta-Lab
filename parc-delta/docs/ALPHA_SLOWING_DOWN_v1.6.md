# PARC-Delta v1.6 — time-dependent alpha slowing-down model

## 1. Scope

v1.6 advances the branch-resolved v1.4 p–11B alpha birth samples through a
non-relativistic, test-particle Landau/Fokker–Planck operator. The field
species are fixed isotropic Maxwellian reservoirs: electrons, protons and a
thermal-alpha background. The test alpha markers do not modify those
reservoirs. Deposited species powers are therefore test-particle expectation
moments, not self-consistent plasma heating.

The implementation follows the Maxwellian Rosenbluth-coefficient/Langevin
form used in ASCOT5-style test-particle collision models. For test particle
momentum \(\mathbf p=m_a\mathbf v\),

\[
 d\mathbf p=-K(v)\mathbf p\,dt
 +\sqrt{2D_\parallel(v)}\,\hat{\mathbf p}\,dW_\parallel
 +\sqrt{2D_\perp(v)}\,(I-\hat{\mathbf p}\hat{\mathbf p})\cdot d\mathbf W_\perp.
\]

For a Maxwellian field species \(b\), define

\[
 v_b=\sqrt{2T_b/m_b},\qquad x=v/v_b,
\]

where temperatures in code input are eV and are converted to joules. The
Chandrasekhar function is

\[
 G(x)=\frac{\operatorname{erf}(x)-2xe^{-x^2}/\sqrt\pi}{2x^2}.
\]

With \(\Gamma_b=n_b q_a^2q_b^2\ln\Lambda/(4\pi\epsilon_0^2)\),

\[
 K_b(v)=\left(1+\frac{m_a}{m_b}\right)
 \frac{2\Gamma_b}{m_a^2v_b^2}\frac{G(x)}{v},
\]

\[
 D_{\parallel,b}(v)=\frac{\Gamma_b}{v}G(x),\qquad
 D_{\perp,b}(v)=\frac{\Gamma_b}{2v}
 [\operatorname{erf}(x)-G(x)].
\]

The implementation uses a small-\(x\) series to avoid cancellation at zero
speed and sums the independent field-species drag/diffusion coefficients.
The Euler–Maruyama momentum update uses independent Gaussian increments in
the local parallel and perpendicular subspaces. A timestep guard enforces
\(K_{\rm total,max}\Delta t\le 0.02\), and the non-relativistic model rejects
marker speeds at or above 0.1c.

The per-marker Itô energy moment for one field species is

\[
 \left\langle\frac{dE_a}{dt}\right\rangle_b
 =-K_bm_av^2+\frac{D_{\parallel,b}+2D_{\perp,b}}{m_a}.
\]

The reported positive background deposition is the negative of this moment,
multiplied by an illustrative test-marker density. Because the background is
fixed, this moment is not fed back into background temperatures or densities.

## 2. Collision algorithms used as independent comparators

The package also includes test-particle versions of the Takizuka–Abe (TA)
and Nanbu pair-scattering samplers. Each marker is paired with a freshly
sampled Maxwellian field velocity. The relative velocity is rotated at fixed
magnitude and the test-particle recoil is reconstructed in the pair
centre-of-mass frame. The field marker is then discarded; no field-particle
back-reaction is applied.

For the TA small-angle update, \(\delta=\tan(\Theta/2)\) is Gaussian with
variance

\[
 \langle\delta^2\rangle=
 \frac{q_a^2q_b^2n_b\ln\Lambda}{
 8\pi\epsilon_0^2\mu_{ab}^2g^3}\Delta t,
 \qquad \mu_{ab}=\frac{m_am_b}{m_a+m_b}.
\]

The bath density is used in this test-particle adaptation. The Nanbu
cumulative-angle parameter is calibrated to the TA small-angle second moment
and solves

\[
 \coth A-A^{-1}=e^{-s},\qquad s=2\langle\delta^2\rangle.
\]

For the three fixed Maxwellian baths, the code uses symmetric forward/reverse
half-step splitting to reduce deterministic species-order bias. This is an
engineering implementation of established collision algorithms, not a new
collision theory. It does not implement equal-weight two-species macroparticle
pairing or dynamic field-particle updates.

## 3. Inputs and normalization

The base source case is a 0.675 MeV proton beam on stationary boron-11,
converted to entrance centre-of-mass energy (0.6183888798 MeV). The `alpha0`
and `alpha1` sequential kinematic branches remain separate and unweighted.
Each full-history case uses 512 events and 1,536 alpha records.

The illustrative fixed background is:

| Field species | Density (m^-3) | Temperature |
|---|---:|---:|
| Electrons | 1.04e20 | 10 keV |
| Protons | 1.00e20 | 10 keV |
| Thermal alpha background | 2.00e18 | 10 keV |

The listed background is charge neutral within this reduced p/alpha/e
mixture. The test-born alpha population is a tracer population whose density
`2e18 m^-3` is used only to scale per-marker energy to a power/energy density;
it does not back-react on the fixed field reservoirs. This is not a complete
p–11B fuel mixture: boron-ion collisions, reactant depletion and full
quasineutrality including the test population are omitted.

The v1.4 alpha birth velocities are generated relativistically, while the
slowing-down operator is non-relativistic. The source audit reports maximum
speed 0.0605c and a maximum non-relativistic-versus-relativistic kinetic
energy difference of 0.274% (mean difference about 0.125%). This is a stated
approximation, not an exact relativistic collision treatment.

## 4. Full-history reference results

Run settings: \(\ln\Lambda=15\), \(\Delta t=10^{-4}\) s, 10,000 steps,
1.0 s total, 1,536 alpha markers per branch, and fixed RNG seeds.

| Quantity | alpha0 | alpha1 |
|---|---:|---:|
| Initial alpha mean energy (non-relativistic) | 3.11317 MeV | 3.11418 MeV |
| Final alpha mean energy | 15.303 keV | 14.734 keV |
| Final alpha median energy | 11.993 keV | 11.634 keV |
| Expected energy deposited to electrons | 728.535 kJ/m^3 | 725.087 kJ/m^3 |
| Expected energy deposited to protons | 261.553 kJ/m^3 | 266.670 kJ/m^3 |
| Expected energy deposited to thermal alpha bath | 6.031 kJ/m^3 | 6.179 kJ/m^3 |
| Relative stochastic energy-budget residual | 0.347% | 0.477% |

The final mean energy approaches the 3-D Maxwellian mean energy \(3T/2=15\)
keV for the 10 keV reservoirs. Integrated expected deposition is about
73% to electrons, 26–27% to protons and 0.6% to the thermal-alpha bath for
these conditions. These fractions are conditional on the simplified source,
background and fixed Coulomb logarithm. They are the classical collisional
baseline; no IBW energy transfer is included.

## 5. Independent collision-method comparisons

### Single proton bath

For a 1 eV fixed Maxwellian proton bath, 384 test markers, 0.05 s duration
and \(\Delta t=5\times10^{-5}\) s, final mean-energy differences relative
to the Rosenbluth/Langevin solver are:

| Method | Relative final mean-energy difference |
|---|---:|
| Takizuka–Abe | +0.00276% |
| Nanbu | +0.000428% |

This is a favorable single-bath benchmark only; it does not validate all
species or all velocity regimes.

### Electron–proton–thermal-alpha mixture

For the full 10 keV three-species bath, 384 test markers and 0.01 s duration,
the Rosenbluth/Langevin reference final mean is 2.957205 MeV. Subcycling
reduces the final-mean difference, but energy-transfer capture remains below
the reference:

| Method | Substeps/species/half-pass | Final mean alpha energy | Difference vs. FP | FP energy loss captured |
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

The subcycling trend is monotonic for this fixed source, seed and duration,
but it is not a formal asymptotic convergence proof. At K=32, TA still
captures 7.11% less energy loss than the Rosenbluth reference and Nanbu
captures 6.12% less. The full-mixture collision comparison remains an open
validation gate. Electron energy exchange is particularly sensitive to the
near-comoving part of the test/field velocity distribution; the adequacy of
field-particle sampling and importance sampling must be assessed with
independent seeds and one-step species-resolved moments.

The subcycling table is reproducible with `scripts_run_v16_subcycling.py`
and `scripts_run_v16_subcycling.py --include-32`; the latter appends the K=32
runs after the default sweep has generated the CSV.

## 6. Additional numerical sensitivities

- Rosenbluth/Langevin fixed-duration timestep scan: 25, 50 and 100 microsecond
  steps over 0.05 s; final mean-energy spread and stochastic energy residual
  are retained in `v16_rosenbluth_timestep_convergence.csv`.
- Single-proton TA/Nanbu timestep scan: 10, 20, 50 and 100 microsecond steps
  over 0.01 s.
- TA/Nanbu marker-count scan: 384 and 1,536 markers, three RNG
  realizations per method/count. This small sensitivity sample is not
  sufficient to fit a robust asymptotic \(N^{-1/2}\) law.
- Coulomb-log sensitivity: \(\ln\Lambda=10,15,20\).
- Entrance proton beam energy sensitivity: 0.34, 0.675 and 1.85 MeV, with
  `alpha0` and `alpha1` kept separate.

## 7. Limitations and next work

Not yet validated:

1. Full multispecies field-particle back-reaction, momentum/energy conservation
   of the complete evolving plasma, or a discrete H theorem.
2. Accurate TA/Nanbu convergence for light-electron-dominated energy transfer
   in the full mixture; at K=32, 6.1–7.1% of the Rosenbluth energy loss is
   still not captured.
3. Relativistic collision corrections, magnetized/finite-Larmor-radius
   corrections, spatial transport or boron-ion collisions.
4. Experimental R-matrix-weighted p–11B birth spectra and branch probabilities.
5. Collisional finite-\(k_\parallel\) IBW susceptibility, nonlinear saturation,
   irreversible proton heating or electrical recovery.
6. Reactor gain, net electricity, plant economics or a commercially useful
   energy-generation mechanism.

Next research gate: determine why the three-species TA/Nanbu test-particle
samplers remain below the Rosenbluth energy-transfer moment after subcycling.
Increase field-particle samples per marker/time step, quantify seed uncertainty,
and match species-resolved one-step energy moments. Do not couple this operator
into IBW or reactor energy-balance claims until this gate is closed.
