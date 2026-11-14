# PARC-Delta v1.0 — model specification

**Release class:** research infrastructure / instantaneous energy-closure layer  
**Not:** a Vlasov–Maxwell solver, PIC code, nonlinear saturation model, reactor design, or prediction of net electrical power.

## 1. Research question

Can a fusion-born alpha distribution drive one or more ion-Bernstein-wave (IBW) modes whose species-resolved, collision-aware damping transfers a larger fraction of alpha energy into *irreversible proton heating* than a no-channeling or single-mode baseline, while reducing electron heating and not requiring an offsetting amount of external RF power?

The comparison is only meaningful under matched plasma profiles, fuel source, magnetic field, density, temperature, confinement, geometry, numerical resolution, and external heating assumptions.

## 2. Physics hierarchy

The software separates three levels that must not be conflated:

1. **Linear coherent response:** species contribute signed growth/damping rates to each wave eigenmode. A proton response can be coherent wave absorption without yet being irreversible heat.
2. **Nonlinear kinetic transfer:** the distribution functions evolve under wave-particle diffusion, mode coupling, collisions, phase mixing, trapping, and particle losses. This level must determine how much coherent response becomes irreversible heating.
3. **Plant energy balance:** the useful particle energy, radiation, transport, wave launch, magnets, pumping, cooling, ash handling and electrical conversion are accounted for. Only this level can establish net electrical output.

v1.0 implements the accounting contract between levels 1 and 2, and the validation rules needed by level 3. The kinetic solvers that generate the rates are external inputs and are not yet implemented in this package.

## 3. Sign convention and wave-energy equation

Use perturbations proportional to `exp(-i omega t)` and write `omega = omega_r + i gamma`. Positive `gamma` is amplitude growth; wave energy changes as `exp(2 gamma t)`.

For mode `j`, with instantaneous wave energy `W_j`, species-resolved rates `gamma_sj`, escape damping `gamma_escape,j`, and external RF input `P_RF,j`:

\[
\frac{dW_j}{dt}=2W_j\left(\sum_s\gamma_{sj}-\gamma_{\mathrm{escape},j}\right)+P_{\mathrm{RF},j}.
\]

The signed power associated with species `s` is:

\[
P_{s\rightarrow j}=2\gamma_{sj}W_j.
\]

- `gamma_sj > 0`: species `s` drives the wave and loses particle energy.
- `gamma_sj < 0`: species `s` damps/absorbs the wave and gains particle energy.
- `gamma_escape,j >= 0`: wave energy leaves the modelled plasma/mode system.

The package converts each signed species contribution into an explicitly directed internal transfer. RF input and wave escape are boundary flows. Thus, for each wave mode, the ledger reproduces the equation above exactly, subject to floating-point roundoff.

This is an instantaneous weak-growth/linear-response power identity. It does **not** calculate `gamma_sj`; that requires a validated species-resolved kinetic dispersion calculation using the actual distributions. The additive species-rate decomposition assumes the weak-growth/damping regime (`|gamma| << omega_r`) and a consistently normalized eigenmode. The supplied `W_j` must be the solver's canonical/dispersive wave energy, not an arbitrary electric-field norm. If the upstream solver cannot provide a consistent species-resolved decomposition and wave-energy normalization, this interface must not be used for quantitative power claims.

## 4. Particle and wave reservoirs

Minimum species keys:

- `alpha_fast` — fusion-born energetic alpha population;
- `protons` — background and/or energetic fuel protons;
- `boron_ions` — boron fuel ions;
- `electrons` — electron population.

Recommended additional species/reservoirs when supported by the kinetic model:

- `helium_ash` — slowed-down alpha ash, distinct from the fast birth population;
- `impurity_ions` — each important impurity species separately;
- `neutrons` — for secondary neutron-producing channels where relevant;
- `wall` — particle and heat loads to material boundaries;
- `wave:<mode-name>` — one reservoir per resolved wave mode.

Coulomb and nonlinear wave-to-wave transfer terms are internal transfers. Bremsstrahlung, transport, orbit loss, charge exchange, wall loss and wave escape are boundary losses unless explicitly represented as a receiving reservoir.

## 5. Energy closure

For each reservoir `r`, the ledger calculates `dE_r/dt` from external inputs, external outputs and directed internal transfers. Internal transfers cancel exactly in the global sum:

\[
\sum_r\frac{dE_r}{dt}=P_{\mathrm{external,in}}-P_{\mathrm{external,out}}.
\]

The code's closure diagnostic is an accounting invariant, not evidence that the upstream plasma physics is correct. A wrong damping coefficient can still produce a perfectly closed ledger.

## 6. Distribution-function and kinetic-solver contract

The next physics solver must provide, at each time sample:

1. `f_alpha(v_perp, v_parallel, r, t)` derived from the fusion source and subsequent orbit/collision evolution. Do not substitute a monoenergetic isotropic source for a reactor calculation.
2. `f_p`, `f_B`, `f_e` and, where needed, impurity and ash distributions.
3. A mode set with complex frequencies, wavevectors, polarizations and consistently normalized canonical/dispersive wave energies.
4. Species-resolved growth/damping rates, with the sign convention above, uncertainty estimates and provenance. The sum of species contributions plus explicitly represented escape/damping terms must reproduce the mode's net growth rate.
5. Nonlinear mode-coupling power transfer between wave reservoirs.
6. A collision/phase-mixing calculation that separates coherent proton response from irreversible proton heating.
7. Particle/energy boundary fluxes and a complete source/loss inventory.

The cyclotron resonance condition must be evaluated for each species and harmonic:

\[
\omega-k_{\parallel}v_{\parallel}-n\Omega_s=0,
\qquad \Omega_s=\frac{q_sB}{m_s}.
\]

For IBWs, retain finite-Larmor-radius dependence and the relevant `k_perp rho_s` structure. A single cold-plasma resonance estimate is not an adequate replacement for the kinetic dielectric response.

## 7. Nonlinear update loop (target architecture, not yet implemented)

At each time step:

1. Advance all species distributions with source, orbit, collision and transport operators.
2. Solve the kinetic dispersion relation for candidate modes using the current distributions.
3. Compute species-resolved wave growth/damping and wave energy.
4. Apply quasilinear diffusion and/or a fully kinetic field-particle update; enforce particle, momentum and energy conservation.
5. Apply nonlinear wave-wave transfer, saturation, phase mixing and resonant trapping.
6. Recompute collisionally irreversible proton heating; do not equate it to coherent proton response.
7. Update ash and wall reservoirs.
8. Close the complete energy and particle ledgers before the next step.

For final validation, selected cases must be cross-checked against a fully kinetic PIC or equivalent solver. A reduced-order model must not be used to claim nonlinear saturation unless its closure has been benchmarked against such a solver.

## 8. Required matched baselines

Run the same initial plasma and source conditions for:

- **B0 — no channeling:** no alpha-driven IBW coupling; retain the same collision, transport and radiation models.
- **B1 — single mode:** one alpha-driven IBW mode with self-consistent kinetic rates and saturation.
- **B2 — multi-mode:** the proposed coupled-mode control/cascade with the same total external input and the same particle, collision and boundary models.
- **B3 — externally driven control:** optional control case to separate alpha self-excitation from injected RF-wave effects.

Compare trajectories and time-integrated energy, not isolated peak growth rates. The B2 architecture only advances if it outperforms B0 and B1 beyond propagated uncertainty and remains advantageous over a defensible parameter envelope.

## 9. Required outputs

Every run must export:

- time histories of each species distribution and energy;
- wave spectra and per-mode wave energy;
- per-species signed growth/damping rates;
- alpha-to-wave power;
- wave absorption by protons, boron, electrons and other species;
- irreversible proton heating, separately from coherent proton response;
- alpha collisional losses, ash accumulation and particle escape;
- RF input and wave escape;
- bremsstrahlung, transport and wall loads;
- particle, momentum and energy closure residuals;
- parameter provenance and uncertainty propagation.

Do not report an alpha-to-proton *thermalization efficiency* unless the irreversible heating term is independently calculated. Do not report reactor `Q`, LCOE or net electric power from this ledger alone.
