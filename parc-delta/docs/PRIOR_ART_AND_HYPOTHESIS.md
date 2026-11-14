# PARC-Delta — prior art boundary and research hypothesis

## Established prior art — excluded from novelty claims

1. **Alpha channeling using IBWs:** Fisch (1995) described extracting alpha-particle energy into plasma waves and channeling it to fuel ions. The paper specifically notes that particles at different velocities and locations can require different waves.
2. **Two-wave alpha channeling:** Fisch and Herrmann (1995) explicitly proposed that complete channeling may require a variety of waves and that combining two waves can relax single-wave constraints.
3. **Pole-resonance alpha-to-proton response:** Qin and Fisch (2026), arXiv:2609.07732, report a thresholdless ideal-collisionless root-pole mechanism and 99.96% alpha-power transfer into the *coherent proton response* in an LAPD example. That number is not an irreversible heating efficiency or a reactor result.
4. **Beam-driven nonlinear IBW energization in p–B11 mixtures:** Liu et al. (2026), arXiv:2603.02728, report fully kinetic PIC simulations in which a nonlinear IBW spectral cascade shifts energy transfer toward background protons and suppresses electron coupling. Their drive is an injected proton beam, not the proposed fusion-born alpha self-excitation path.
5. **General multi-wave channeling, resonant diffusion, and adaptive RF control:** these are established research or patent areas. Generic claims around multiple waves, resonance tuning, feedback, or alpha energy recovery are not sufficient novelty.

## Narrow hypothesis to test

The research question is not whether two or more waves can channel alpha energy; this is already in the literature. It is whether a **closed-loop, distribution-aware resonance scheduler** can continuously reconfigure a coupled set of IBW modes from measured/estimated species-resolved phase-space gradients and damping, such that it:

- avoids a single-mode plateau or loss of the resonant alpha population;
- reduces alpha hard-landings and energetic wall losses;
- directs a larger fraction of alpha-derived wave power into useful proton phase-space regions;
- converts more of that coherent proton response into irreversible proton heating;
- avoids increasing electron heating, boron heating, RF drive or total wall load enough to erase the gain.

This is a research hypothesis, not an established invention. Its elements may overlap with prior art in multi-wave channeling, nonlinear spectral cascades, RF feedback and wave-particle diffusion. Novelty must be assessed on the exact control method, sensing/estimation inputs, mode-selection constraints, actuator architecture and demonstrated performance—not on the broad objective.

## Falsifiable hypothesis

Under matched initial distributions, fuel source, magnetic geometry, external heating, collision model and boundary conditions, the closed-loop multi-mode case (B2) will yield a statistically significant increase in time-integrated irreversible proton heating per unit fusion-born alpha energy relative to both B0 and B1, without increasing the total required external RF power or electron heating by an amount that removes the net gain.

The hypothesis is falsified if:

- the apparent advantage disappears when nonlinear saturation and collisions are included;
- proton energy remains predominantly coherent/reversible;
- the alpha distribution is depleted or flattened faster than replenishment can maintain useful transfer;
- more energy is sent to electrons, boron ions, escaping waves or walls;
- the same result is achieved by a simpler fixed multi-wave spectrum with no scheduler;
- uncertainty intervals overlap zero improvement or the result is not robust to grid/time-step/particle-number convergence.

## Patent and freedom-to-operate rule

Do not file broad claims that cover alpha channeling, IBW coupling, two-wave channeling, pole-resonance excitation or feedback control in isolation. Before any filing, commission a claim-chart review against the relevant publications and patents, then define only the specific technical implementation that survives the review. This note is a technical prior-art screen, not legal advice or a patentability opinion.

## Selected references

- N. J. Fisch, “Alpha power channeling using ion-Bernstein waves,” *Physics of Plasmas* 2, 2375–2380 (1995), DOI: [10.1063/1.871454](https://doi.org/10.1063/1.871454).
- N. J. Fisch and M. C. Herrmann, “Alpha power channelling with two waves,” *Nuclear Fusion* 35, 1753–1760 (1995), DOI: [10.1088/0029-5515/35/12/I40](https://doi.org/10.1088/0029-5515/35/12/I40).
- H. Qin and N. J. Fisch, “Thresholdless IBW Emission and Alpha-to-Thermal-Ion Energy Channeling via Pole Resonance of Fusion-Product Ions,” arXiv:2609.07732 (v2, 15 September 2026), [arXiv:2609.07732](https://arxiv.org/abs/2609.07732).
- Y. Liu et al., “Energization of Proton via Beam-Driven Ion Bernstein Waves in p11B Plasmas,” arXiv:2603.02728 (3 March 2026), [arXiv:2603.02728](https://arxiv.org/abs/2603.02728).
- I. M. Ahmad et al., “Evaluation of the Lawson criterion for aneutronic proton-boron-11 fusion: effects of ion temperature and bremsstrahlung losses,” *Frontiers in Nuclear Engineering* 5 (24 February 2026), DOI: [10.3389/fnuen.2026.1714531](https://doi.org/10.3389/fnuen.2026.1714531).
- M. Mazzucconi et al., *European Physical Journal A* 61, 114 (2025), DOI: [10.1140/epja/s10050-025-01589-3](https://doi.org/10.1140/epja/s10050-025-01589-3).
