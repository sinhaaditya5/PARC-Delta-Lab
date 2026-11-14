# Results

Full results of the PDX-1 concept study (run date 2026-11-01). Machine-readable source:
[`deliverables/data/results_summary.json`](../deliverables/data/results_summary.json).

## Test matrix

| ID | Area | What | How | Result | Status |
|:--:|---|---|---|---|:--:|
| T1 | Software | PARC-Delta v1.6 unit + regression suite | 76 automated tests on a clean Python 3.12 toolchain | 76 / 76 passed | ✅ pass |
| T2 | Reproducibility | Re-run of the full v1.6 campaign | `scripts_run_v16.py` in an isolated copy; 1,122 numbers in 11 files compared to the release | max relative difference 7.5 × 10⁻¹⁰ | ✅ pass |
| T3 | Physics (inherited) | Collision-operator cross-checks | Landau–Spitzer analytic moment; single-bath and full-mixture TA/Nanbu vs Rosenbluth | single bath < 0.003 %; full mixture captures 92.9 % / 93.9 % of energy loss | ⏳ open |
| T4 | Magnet | Field, mirror ratio, stored energy, conductor field | magpylib analytic loops (8 × 10 filaments per coil); 2 × 2 current solve; inductance-matrix energy | B₀ 3.00 T, mirror ratio 1.63, 14.2 MJ, peak winding field 10.0 T | 🔁 design change |
| T5 | Orbit solver | Boris integrator vs adiabatic loss-cone theory | 4,200 alphas from the α0/α1 birth source, 4 µs, 0.4 ns steps | end loss 39.67 % vs analytic loss cone 39.69 % | ✅ pass |
| T6 | Confinement | Alpha wall loss vs central field | coil currents scaled 1–4 T; limiter at r = 250 mm | 76 % at 1 T → 0.1 % at 3 T | ✅ pass |
| T7 | Target | Foil / target re-intersection by trapped alphas | X = 0 crossings on foil, frame ring and arm; offset scanned 0–160 mm | 38 % hit the target assembly in 4 µs; median first foil re-crossing 1.5 µs | 🔶 finding |
| T8 | Collisions | Alpha slowing-down in the bench plasma | Rosenbluth drag, nₑ = 10¹⁹ m⁻³, Tₑ = 10 eV, Tₚ = 2 eV | 3.1 MeV → 50 keV in 11.7 ms; 99.94 % to electrons | ✅ pass |
| T9 | Feasibility | Fast-alpha inventory vs IBW drive | 10 µA, 1 µm ¹¹B foil, σ ≈ 1.2 b (assumed), lifetimes from T5/T7/T8 | 2.3 × 10⁸ m⁻³ vs 2 × 10¹⁷ m⁻³ needed (~10⁹× short) | 🔶 finding |
| T10 | RF | IBW channel plan and resonance layers | simulated B(X) → nΩα, nΩp, Ω(¹¹B⁵⁺); four channels at (n + ½)Ωα(B₀) | Ωα/2π = 23.0 MHz, Ωp/2π = 45.7 MHz, f_LH = 628 MHz; channels 57.6–126.6 MHz | ✅ pass |
| T11 | CAD | Model integrity and drawing traceability | build123d STEP, CADCraft drawing and simulations read one parameter file | 150 parts, 6.9 × 3.2 × 2.4 m; A0 drawing PDX1-GA-001 | ✅ pass |

## Magnet (T4)

| Quantity | Value |
|---|---:|
| Coil set | 2 mirror + 6 main REBCO HTS coils, conduction-cooled at 20 K |
| B₀ on axis | 3.00 T |
| B_max on axis | 4.88 T |
| Mirror ratio | 1.63 |
| Stored magnetic energy | 14.2 MJ |
| Peak field at conductor (mirror coils) | 10.0 T |
| Engineering current density (main / mirror) | 55.5 / 142.5 A mm⁻² |
| Hoop-stress screen J×B×R (M3 / MR-R) | 39 / 170 MPa |

The first pass assumed NbTi at 4.2 K. The ~10 T mirror-coil winding field exceeds practical NbTi
margins, so the baseline changed to REBCO at 20 K. Hoop stress is a screening estimate without
structural credit and needs FEA.

## Alpha confinement (T5–T7)

Fractions after 4 µs at the 3 T design point (α0 and α1 combined):

| Fate | Fraction |
|---|---:|
| Confined | 22.1 % |
| End loss (through mirror throats) | 39.7 % |
| Limiter / wall | 0.07 % |
| Target hit | 38.1 % |

## Alpha budget (T9)

| Quantity | Value |
|---|---:|
| Reactions per second (10 µA, 1 µm foil, σ ≈ 1.2 b assumed) | 9.6 × 10⁸ s⁻¹ |
| Alphas per second | 2.9 × 10⁹ s⁻¹ |
| Trapped fraction at birth | 60 % |
| Effective lifetime: target-limited / slowing-limited | 1.5 µs / 11.7 ms |
| Achievable alpha density (best case) | 2.3 × 10⁸ m⁻³ |
| Required for IBW self-excitation (n_α/n_p = 2 %) | 2 × 10¹⁷ m⁻³ |
| Beam power on foil (upper bound) | 6.75 W |

**Verdict:** fusion-born alphas from a µA-class beam–foil source cannot drive IBWs. PDX-1 Phase 1
measures the birth spectrum and orbit physics; Phase 2 needs a surrogate energetic-ion ring.

## PARC-Delta v1.6 baseline (inherited)

| Quantity | α0 | α1 |
|---|---:|---:|
| Initial mean energy | 3.11317 MeV | 3.11418 MeV |
| Final mean energy (1 s) | 15.303 keV | 14.734 keV |
| Electron deposition | 728.5 kJ m⁻³ | 725.1 kJ m⁻³ |
| Proton deposition | 261.6 kJ m⁻³ | 266.7 kJ m⁻³ |
| Thermal-alpha deposition | 6.0 kJ m⁻³ | 6.2 kJ m⁻³ |

TA/Nanbu subcycling at K = 32 substeps per species per half-pass: final-mean differences +0.375 % / +0.323 %,
but only 92.9 % / 93.9 % of the Fokker–Planck energy loss is captured. **Open.**

## Open questions

| Topic | Question |
|---|---|
| Collision closure | Why do TA/Nanbu still miss 6–7 % of the Rosenbluth alpha energy loss at 32 substeps, and does importance sampling of near-comoving electrons close it? |
| Trapped-alpha accumulation | An on-axis foil re-intersects ~38 % of trapped alphas within 4 µs. Pulsed or retractable targets, or a gas/pellet boron target, are needed to build a trapped population. |
| Alpha drive | Fusion alphas from a µA beam are ~10⁹× too sparse for IBW self-excitation. What surrogate energetic-ion source reaches n_fast/n_p ≈ 1 % at bench scale? |
| Coherent vs irreversible | How will PDX-1 separate coherent proton response from irreversible proton heating (Gate 4)? Candidate: RFEA/CX energy distributions with RF on/off modulation. |
| Nonlinear physics | Does the multi-mode advantage survive nonlinear saturation and mode coupling? Requires a PIC benchmark (Gate 3) before any control-law claim. |
| Magnet engineering | REBCO mirror coils see ~10 T and a ~170 MPa J×B×R screen; quench protection, structure and cost need FEA and vendor input. |
| Bench electron dominance | At Tₑ = 10 eV, 99.9 % of alpha energy goes to electrons. Which bench parameters make the α→p channel measurable against this baseline? |
| Source validation | Can the Si spectrometer resolve the α0/α1 branch structure to validate the sequential-kinematic source (an open Gate 2 item)? |
| Radiation safety | Alphas striking boron produce neutrons via ¹¹B(α,n)¹⁴N; shielding and licensing need a dose assessment even at µA currents. |
| Foil survival | ≤ 6.75 W of beam power on a 1 µm foil: thermal survival, sputtering and ¹¹B enrichment supply need testing. |
