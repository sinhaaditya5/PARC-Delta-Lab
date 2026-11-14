# PARC-Delta v1.4 — multispecies Coulomb collision Monte Carlo prototype

**Status:** stochastic pairwise weak-deflection operator implemented with exact pair-level momentum and kinetic-energy conservation. It is not yet a deterministic finite-grid Landau operator or a collisional IBW susceptibility.

## 1. Operator scope

The prototype advances local velocity-space collisions among charged species in a homogeneous plasma cell. It updates both partners for every sampled pair, including cross-species collisions. This avoids treating an evolving species as a fixed Maxwellian test-particle bath and gives exact pairwise conservation in the centre-of-mass frame.

The algorithm is a stochastic small-angle binary-scattering realization of the Landau limit. It is not presented as a new collision theory. Cumulative small-angle Monte Carlo collisions are established plasma-simulation methodology; Nanbu's 1997 treatment is a foundational reference. [1]

## 2. Weak-deflection rate

For a pair \((a,b)\), define relative speed \(g=|\mathbf v_a-\mathbf v_b|\), reduced mass

\[
\mu_{ab}=\frac{m_am_b}{m_a+m_b},
\]

and the classical 90-degree impact parameter

\[
b_{90}=\frac{|q_aq_b|}{4\pi\epsilon_0\mu_{ab}g^2}.
\]

The upper impact-parameter cutoff is the Debye screening length \(b_{\max}=\lambda_D\); the lower cutoff is

\[
b_{\min}=\max\left(b_{90},\frac{\hbar}{2\mu_{ab}g}\right),\qquad
\ln\Lambda=\ln\left(\frac{b_{\max}}{b_{\min}}\right).
\]

The two-dimensional small-angle variance follows by integrating the Rutherford small-angle relation \(\theta\simeq2b_{90}/b\) over the impact-parameter annulus:

\[
\frac{d\langle\theta^2\rangle}{dt}
 = 8\pi n_{\mathrm{partner}}g b_{90}^2\ln\Lambda
 = \frac{n_{\mathrm{partner}}q_a^2q_b^2\ln\Lambda}
 {2\pi\epsilon_0^2\mu_{ab}^2g^3}.
\]

In the all-pairs macroparticle discretization, `n_partner` is the common physical number density represented by one partner macroparticle, \(n_s/N_s\). Therefore all species must have equal physical number weight per macroparticle. The operator rejects inconsistent weights rather than silently breaking pair symmetry.

For each pair, two independent transverse deflection components are sampled with variance one half of the integrated \(\langle\theta^2\rangle\). The relative velocity is rotated at fixed magnitude; the pair centre-of-mass velocity is unchanged. The two post-collision velocities are reconstructed from the rotated relative velocity and the physical masses.

## 3. Conservation and numerical controls

Each pair update conserves:

- pair momentum;
- pair kinetic energy;
- one particle of each species (particle counts are unchanged).

The global operator reports momentum-density and kinetic-energy-density residuals after all pairs are advanced. A requested timestep is rejected if a sampled kick exceeds the configured small-angle bound; the update is transactional and does not leave partially modified particle arrays after rejection.

Pairs with non-positive Coulomb logarithm are skipped and counted. This marks encounters outside the weak-coupling small-angle model; it does not make them physically disappear. A high skipped-pair fraction is a model-validity failure and requires a different collision treatment.

A Maxwellian-mixture Debye length is estimated from species densities and temperatures by default. A caller may supply a background screening length explicitly, which is useful when the alpha birth distribution is nonthermal and should not be assigned an artificial scalar temperature for screening.

## 4. Benchmarks in this release

The equilibrium-mixture conservation benchmark uses electrons, protons and alphas with equal macroparticle number weights. For one `1e-8 s` step it records:

- 3,486 pair updates;
- no skipped strong-coupling pairs;
- maximum sampled pair deflection of `3.82e-3 rad`;
- minimum/maximum sampled Coulomb logarithm of `18.33` / `25.05`;
- relative momentum-density error `3.06e-16`;
- relative kinetic-energy-density error `8.77e-16`.

A separate source-coupled smoke test uses six alpha particles from two `alpha1` reaction events with Maxwellian 10 keV electron/proton background. The screening length is computed from electrons and protons only; the nonthermal alpha contribution to screening is omitted. The one-step relative momentum and energy errors are `2.08e-16` and `1.28e-15`.

These checks validate pairwise invariants and software plumbing. They do not validate collision rates, energy slowing-down histories, thermalization times, or reactor conditions.

## 5. Explicit open limitations

The current scheme is **not**:

- a deterministic finite-grid discretization of the full nonlinear Landau operator;
- a linearized test-particle plus field-particle operator around evolving distributions;
- a finite-Larmor-radius gyrokinetic collision operator;
- a proof of a discrete H theorem or non-negative coarse-grained entropy production;
- coupled to the finite-`k_parallel` IBW eigenvalue equation;
- a model of alpha slowing down in the presence of wave-particle interactions.

The collision operator is local and isotropic in velocity space. The magnetic field acts through the kinetic streaming/Lorentz dynamics; no gyroaveraging or FLR correction is applied to the collision discretization. Timestep/order convergence, collision-rate validation against analytic relaxation rates, statistical entropy tests, a continuum-limit comparison and a collisionally modified IBW root remain required.

The 2024 collisional PIC method of Bailo, Carrillo and Hu gives a deterministic structure-preserving route for Vlasov–Landau simulations, with mass, charge, momentum and energy conservation and entropy increase in its regularized formulation. A separate conservative discretization by Hirvijoki and Adams also demonstrates algebraic moment conservation. These are relevant validation targets, not implementations copied into this v1.4 package. [2,3]

## 6. References

1. K. Nanbu, “Theory of cumulative small-angle collisions in plasmas,” *Physical Review E* 55, 4642 (1997), https://doi.org/10.1103/PhysRevE.55.4642
2. R. Bailo, J. A. Carrillo and J. Hu, “The collisional particle-in-cell method for the Vlasov–Maxwell–Landau equations,” *Journal of Plasma Physics* 90, 905900415 (2024), https://doi.org/10.1017/S0022377824001077
3. E. Hirvijoki and M. Adams, “Conservative discretization of the Landau collision integral,” *Physics of Plasmas* 24, 102311 (2017), https://doi.org/10.1063/1.4979122
4. Coulomb impact-parameter cutoffs and Coulomb logarithm formulation, PlasmaPy formulary documentation: https://docs.plasmapy.org/en/latest/notebooks/formulary/coulomb.html
