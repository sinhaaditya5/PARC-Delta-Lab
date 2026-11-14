# PARC-Delta v1.6 research package

PARC-Delta is an exploratory p–11B fusion alpha-channeling research model.
v1.6 adds a time-dependent test-particle alpha slowing-down calculation using
Maxwellian Rosenbluth/Landau coefficients, plus independent Takizuka–Abe and
Nanbu scattering comparators. The new results describe a **classical
collisional baseline** in fixed electron, proton and thermal-alpha reservoirs.

This package is not a reactor design. It does not establish fusion gain, net
electricity, low-cost power or a new energy-generation mechanism.

**Validation status:** 76 automated tests pass. The TA/Nanbu full-mixture
cross-check remains open: at K=32 their deposited-energy shortfalls against
the Rosenbluth reference are still 7.1% and 6.1%, respectively.

## New in v1.6

- Test-particle Fokker–Planck/Langevin alpha slowing-down with electron,
  proton and thermal-alpha Maxwellian field species.
- Species-resolved expected energy-deposition moments and time histories.
- Branch-resolved `alpha0` and `alpha1` source histories, without assumed
  branching fractions.
- Test-particle Takizuka–Abe and Nanbu collision samplers.
- Symmetric species splitting for a fixed three-species background.
- Timestep, marker-count, source-energy and Coulomb-log sensitivity outputs.
- Multispecies TA/Nanbu subcycling sensitivity from K=1 to K=32. At K=32,
  final mean-energy differences fall below 0.4%, but 6.1–7.1% of the
  Rosenbluth-predicted alpha energy loss remains uncaptured; the collision
  comparison is therefore still open.

## Run

```bash
python -m pip install -e ".[test]"
pytest -q
python scripts_run_v16.py
python scripts_run_v16_subcycling.py
python scripts_run_v16_subcycling.py --include-32
```

See `docs/ALPHA_SLOWING_DOWN_v1.6.md` for equations and source/background
assumptions, `docs/MULTISPECIES_SUBCYCLING_v1.6.md` for the TA/Nanbu sweep,
and `docs/ACCEPTANCE_GATES.md` for open validation gates. Historical
v1.1–v1.5 reports and outputs are retained for reproducibility.
