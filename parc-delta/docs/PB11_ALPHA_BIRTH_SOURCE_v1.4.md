# PARC-Delta v1.4 — p–11B alpha birth-source kinematics

**Status:** relativistic sequential-decay kinematics implemented for two dominant sequential branches; channel weights and a full nuclear reaction model remain open.

## 1. Why a single alpha energy is invalid

The reaction is treated as

\[
 p + {}^{11}\mathrm B \rightarrow \alpha + {}^{8}\mathrm{Be}^{*}
 \rightarrow \alpha + \alpha + \alpha.
\]

The relevant sequential channels are conventionally labelled:

- `alpha0`: the primary alpha leaves \(^{8}\mathrm{Be}\) in its ground-state resonance, which then decays into two alphas;
- `alpha1`: the primary alpha leaves \(^{8}\mathrm{Be}\) in its first excited \(2^+\) resonance, which then decays into two alphas.

The literature gives a ground-state breakup energy around 91.8 keV, an excited-state energy around 3.028 MeV, and an excited-state width around 1.5 MeV. The corresponding primary-alpha exit energies at low entrance energy are approximately 5.7 MeV (`alpha0`) and 3.76 MeV (`alpha1`), but the excited-state branch is broad. Recent spectra resolve a primary contribution associated with `alpha1`, a higher-energy `alpha0` contribution and low-energy secondary alphas from the \(^{8}\mathrm{Be}\) decay. These spectral structures vary with incident proton energy. [1–3]

Therefore, v1.4 keeps `alpha0` and `alpha1` as separate source cases. It does not assign a branch probability or combine them with arbitrary weights.

## 2. Nuclear mass convention and entrance energy

The code uses nuclear masses for a fully ionized plasma:

- CODATA proton mass;
- CODATA alpha-particle nuclear mass;
- the \(^{11}\mathrm B\) nuclear mass reconstructed from its atomic mass by subtracting five electron rest masses.

The small atomic electron-binding correction is neglected. With this convention the mass-balance energy release is

\[
Q_{pB}=m_p c^2 + m_{B}c^2 - 3m_{\alpha}c^2
       = 8.68188794\ \mathrm{MeV}
\]

for the mass values embedded in the implementation.

For a proton of lab kinetic energy \(T_{p,\mathrm{lab}}\) incident on stationary boron, the invariant entrance energy is calculated relativistically:

\[
s=m_p^2c^4+m_B^2c^4+2m_Bc^2(m_pc^2+T_{p,\mathrm{lab}}),
\qquad E_{\mathrm{cm}}=\sqrt{s}-(m_p+m_B)c^2.
\]

The sampler accepts fixed or event-wise `E_cm`. It does not convolve a thermal proton–boron reactant distribution or apply a p–B11 cross section.

## 3. Sequential two-body kinematics

For each event, sample the \(^{8}\mathrm{Be}\) invariant mass

\[
M_8c^2 = 2m_\alpha c^2 + E_{\alpha\alpha}.
\]

For `alpha0`, \(E_{\alpha\alpha}=0.09184\) MeV is held fixed as a narrow-resonance approximation. For `alpha1`, the current prototype samples a truncated Cauchy/Breit–Wigner proxy centred at 3.028 MeV with width 1.5 MeV, bounded by the event's available phase space.

Let \(W\) be the total entrance CM energy. The primary alpha and \(^{8}\mathrm{Be}\) momenta have equal magnitude:

\[
p^* = \frac{\sqrt{[W^2-(m_\alpha+M_8)^2][W^2-(m_\alpha-M_8)^2]}}{2W},
\]

where masses and energies are expressed in consistent \(c=1\) units. The two secondary alphas are generated back-to-back in the \(^{8}\mathrm{Be}\) rest frame and Lorentz-boosted into the entrance CM frame. An optional exact Lorentz boost maps the event to the proton-beam lab frame.

The primary direction and the daughter axis are currently sampled isotropically and independently in their respective decay frames. This is a simplifying assumption; it is not a substitute for the angular-momentum-dependent sequential model or measured differential emission distributions.

## 4. Generated source and velocity-space projection

The v1.4 runner produces 4,000 events per channel at each of five incident proton energies: 0.34, 0.675, 1.85, 2.57 and 4.73 MeV. The total is 10 source cases and 120,000 individual alpha records.

Outputs include each particle's kinetic energy, three-velocity, event ID, role (`primary`, `be8_daughter_1`, `be8_daughter_2`) and pitch cosine.

For use as a gyrotropic input to a future kinetic susceptibility, the CM-frame samples are projected to \((v_\parallel,v_\perp)\). The histogram density includes the cylindrical velocity-space Jacobian:

\[
d^3v = 2\pi v_\perp\,dv_\perp\,dv_\parallel.
\]

The stored distribution is a unit-normalized probability density, not a physical alpha number density and not yet a susceptibility. The grid is a source handoff format for the next implementation stage.

## 5. What is deliberately not inferred

The source model does **not** apply:

- partial cross sections or `alpha0`/`alpha1` branch weights;
- reaction-energy convolution over actual non-Maxwellian reactants;
- a full R-matrix energy-dependent line shape, penetrability or interference terms;
- angular correlations and partial-wave amplitudes;
- plasma stopping, target stopping, spatial birth gradients or alpha escape;
- detector solid angle, thresholds, dead layers or response.

This limitation matters. The 2016 reaction-rate evaluation uses a sequential spectrum model with an \(\ell=3\) primary-alpha assumption; that is beyond this isotropic phase-space sampler. The 2025 silicon-telescope spectra were recorded at a fixed laboratory angle and discuss possible aluminum-support contributions at some incident energies. The measured spectra are therefore not used as uncorrected, isotropic source weights here. [2,3]

The outputs are branch-resolved kinematic source samples, not a predictive total alpha spectrum. An initial comparison with the 2025 reported CM spectra finds that the prototype's `alpha1` primary histogram mode is below 4.5 MeV for the 0.34 and 0.675 MeV proton-beam cases, whereas that paper describes the primary `alpha1`-associated spectral feature as roughly 4.5–7 MeV across its beam-energy range. This is only a preliminary diagnostic: the paper reports measured peak locations, while this code estimates a histogram mode from finite Monte Carlo samples with 0.05 MeV bins. It is not a like-for-like detector-level comparison. The mismatch is not tuned away; it blocks quantitative validation and indicates that the simple truncated Cauchy line shape and isotropic kinematics are inadequate for a spectrum fit. A reactor-grade source requires a validated R-matrix/sequential-decay model, differential cross sections and branch fractions over the reacting-particle energy distribution. [3]

## 6. References

1. *Diagnostic Methodologies of Laser-Initiated 11B(p,α)2α Fusion Reactions*, Frontiers in Physics (2020), discussion of the 8Be ground and first-excited channels, resonance energies, Q values and alpha spectra: https://doi.org/10.3389/fphy.2020.561492
2. M. H. Sikora and H. R. Weller, “A New Evaluation of the 11B(p,α)αα Reaction Rates,” *Journal of Fusion Energy* 35, 538–543 (2016), sequential spectrum model and alpha0 branch: https://doi.org/10.1007/s10894-016-0069-y
3. D. Mazzucconi et al., “Evaluation of the p-11B reaction cross section through a silicon telescope in the 0.3–4.7 MeV range,” *European Physical Journal A* 61, 114 (2025), measured alpha spectra and partial-channel discussion: https://doi.org/10.1140/epja/s10050-025-01589-3
