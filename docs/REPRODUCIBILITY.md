# Reproducibility guide

Everything in this repository can be rebuilt from source. This guide walks the pipeline stage by stage.

## 1. Environment

```bash
python3 -m venv .venv && source .venv/bin/activate
make install          # pip install -e "parc-delta[test]" -r requirements/prototype.txt
make install-dev      # optional: ruff, pytest, pre-commit + git hooks
```

Python 3.10–3.13 is supported and tested in CI. The reference run used Python 3.12 with
numpy 2.5, scipy 1.18, matplotlib 3.11, magpylib 6.1 and build123d 0.13.

## 2. Verify the research package

```bash
make verify           # parc-delta/ matches SHA256SUMS.txt (84 files)
make test             # 76 tests, a few seconds
make cli-smoke        # evaluates examples/synthetic_unit_test_snapshot.json
```

> [!NOTE]
> Running the campaign scripts *inside* `parc-delta/` rewrites `results/` and will (correctly) fail
> `make verify`. Use `make rerun`, which works on an isolated copy.

## 3. Re-run the v1.6 campaign (test T2)

```bash
make rerun            # copies parc-delta/ to runs/v16_rerun/ and runs scripts_run_v16.py (~17 s)
```

`make report` then compares every number in the eleven `v16_*` result files against the shipped
release. Expected: 1,122 values, max relative difference ≈ 7.5 × 10⁻¹⁰ (floating-point level).

The other campaigns run the same way from an isolated copy:

```bash
python scripts_run_v16.py                          # main campaign (also provides the K = 16 point)
python scripts_run_v16_subcycling.py               # runs K = 1, 4, 8; reuses K = 16 from the main run
python scripts_run_v16_subcycling.py --include-32  # adds K = 32 (slow)
```

## 4. Device simulations

```bash
make sims             # magnet (~14 s) → orbits (~18 s) → bench physics (~1 s)
```

Outputs land in `prototype/sim/out/`. Physics outputs are deterministic: a re-run reproduces
`magnet_summary.json` and `bench_physics_summary.json` byte for byte, and
`alpha_orbit_summary.json` differs only in its wall-clock `runtime_s` field.

## 5. CAD and drawing

```bash
make cad              # build123d → STEP (150 parts) + STL groups + parts list
make drawing          # needs cadcraft-cli
```

The drawing stage uses [CADCraft](https://github.com/storytold/cadcraft) headlessly. Build it with
Cargo and point the pipeline at the binary:

```bash
git clone https://github.com/storytold/cadcraft.git tools/cadcraft
(cd tools/cadcraft && cargo build --release)
export CADCRAFT_CLI="$PWD/tools/cadcraft/target/release/cadcraft-cli"
```

(`tools/` is git-ignored; the script also looks there automatically.)

## 6. Renders

```bash
export BLENDER="/Applications/Blender.app/Contents/MacOS/Blender"
make renders SAMPLES=160    # hero, cutaway, detail + annotated callouts
make turntable              # frames for the video
```

`annotate.py` uses the Arial Bold font that ships with macOS; on other systems edit `FONT_B`.

## 7. Diagrams, report data, documents

```bash
make diagrams
make report
make docs             # npm install + docx report + pptx deck (Node ≥ 20)
```

`make_deck.js` optionally post-processes the deck with an external theme script: set
`PPTX_SKILL` to a directory containing `scripts/apply_theme.js`. Without it the deck uses its built-in
masters.

## 8. Video

```bash
make video            # macOS only: narration uses the `say` command; needs ffmpeg
```

## 9. README imagery

```bash
make assets           # docs/assets/* from the pipeline outputs
```

## Integrity of published artifacts

| Artifact | How to check |
|---|---|
| Research package | `make verify` |
| Campaign reproducibility | `make rerun && make report`, then read `reproducibility` in `prototype/report/out/results_summary.json` |
| Release binaries | Built from the tagged commit; the `release.yml` workflow attaches the `parc-delta` sdist and wheel |
