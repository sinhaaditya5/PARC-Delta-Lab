# PARC-Delta acceptance gates — v1.6 status

## Gate 0 — input and energy accounting
Implemented in the inherited research package. This is bookkeeping validation,
not a reactor balance.

## Gate 1 — collisionless linear IBW benchmark
Implemented as a narrow collisionless LAPD reference reproduction. The
published exact-crossing residue/mass-convention discrepancy remains open.

## Gate 2 — finite-width and collisional kinetic extension
Partially implemented:
- finite perpendicular alpha energy width and finite parallel wavenumber;
- separate p–11B `alpha0` and `alpha1` sequential kinematic branches;
- conservative pair-rotation primitive and instantaneous Landau energy-moment
  benchmark from v1.4/v1.5;
- non-relativistic test-particle Rosenbluth/Langevin alpha slowing-down in
  fixed Maxwellian electron, proton and thermal-alpha reservoirs;
- independent test-particle TA and Nanbu samplers and symmetric multispecies
  splitting;
- full-history time evolution, species-resolved expected deposition,
  timestep/particle-count/source-energy/Coulomb-log sensitivities.

Open validation requirements:
- resolve the remaining full-mixture TA/Nanbu energy-transfer discrepancy:
  even at 32 substeps per species per half-pass, TA/Nanbu capture only
  92.9%/93.9% of the Rosenbluth-predicted alpha energy loss;
- field-particle sampling/importance-sampling convergence for electron
  collisions and multiple-seed uncertainty;
- conserving field-particle multispecies operator and discrete H theorem;
- boron-11 ion collisions and a complete p–11B plasma composition;
- experimental/R-matrix weighted p–11B source spectrum and angular data;
- relativistic and magnetized/finite-Larmor-radius collision corrections;
- generalized IBW susceptibility using the complete reaction-derived source;
- collisional kinetic dispersion and species power closure.

## Gate 3 — nonlinear kinetic benchmark
Not implemented. Reproduce at least one published beam-driven IBW cascade
benchmark with PIC or validated equivalent before proposing a new control law.

## Gate 4 — coherent response versus irreversible heat
Not implemented. Track proton distribution evolution, phase mixing,
collisional relaxation, trapping, reabsorption, and irreversible temperature
rise separately.

## Gate 5 — fair baseline comparison
Not implemented. Compare no-channeling, single-mode and multi-mode cases under
identical source, auxiliary power, geometry, collisions, boundaries and
resolution.

## Gate 6 — self-consistent p–11B energy balance
Not implemented. Requires validated fusion reactivity over evolving
non-Maxwellian p/B distributions, complete alpha birth source, radiation,
transport, ash and secondary channels, conversion and parasitic loads.

## v1.6 implementation facts
- The main Fokker–Planck solver is test-particle and non-relativistic; field
  reservoirs remain fixed and receive no feedback.
- The test-alpha density is a post-processing tracer normalization, not a
  self-consistent alpha inventory.
- Main backgrounds contain electrons, protons and thermal alphas, but omit
  boron ions and reactant depletion.
- The alpha source is inherited from the v1.4 sequential kinematic proxy;
  branch yields are not weighted or experimentally validated.
- The 1-second slowing-down calculation approaches the 15 keV mean energy of
  a 10 keV three-dimensional Maxwellian reservoir. Expected deposition is
  approximately 73% to electrons, 26–27% to protons and 0.6% to thermal alphas
  for this illustrative case.
- The single-proton-bath TA/Nanbu benchmark agrees closely with the
  Rosenbluth reference, but the full electron–proton–thermal-alpha comparison
  differs by 2.487% (TA) and 2.085% (Nanbu). This blocks a claim of
  full-mixture collision cross-validation.

## Stop rules
Stop or redesign if multi-mode control does not beat the simplest baseline
within uncertainty, if energy closure depends on omitted sinks, if proton
response remains reversible/coherent, or if RF/engineering loads erase the
available gain.
