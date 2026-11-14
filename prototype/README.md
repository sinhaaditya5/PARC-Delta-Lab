# PDX-1 prototype pipeline

PDX-1 is a **concept** bench-scale linear magnetized test stand for the PARC-Delta programme. Every
stage here reads the same parameter file, [`design/pdx1_params.py`](design/pdx1_params.py), and
writes only to its own `out/` folder (git-ignored). Run stages from the repository root with `make`.

| Folder | Script | `make` target | Produces |
|---|---|---|---|
| `design/` | `pdx1_params.py`, `plotstyle.py` | — | Shared geometry, physics targets and figure style |
| `sim/` | `magnet_field.py` | `magnet` | Coil currents, (r, z) field map, mirror ratio, stored energy |
| `sim/` | `alpha_orbits.py` | `orbits` | Boris full-orbit alpha fates for 1–4 T and a target-offset scan |
| `sim/` | `bench_physics.py` | `bench` | Slowing-down, alpha inventory budget, IBW resonance map |
| `cad/` | `pdx1_model.py` | `cad` | 150-part STEP assembly, STL groups, parts list |
| `drawings/` | `make_ga_drawing.py` | `drawing` | PDX1-GA-001 general arrangement (DXF, PDF, PNG) |
| `renders/` | `blender_scene.py`, `annotate.py` | `renders`, `turntable` | Cycles stills with callouts, turntable frames |
| `diagrams/` | `make_diagrams.py` | `diagrams` | Architecture, control loop, energy flow, validation ladder, roadmap |
| `report/` | `collect_results.py` | `report` | `results_summary.json` (tests T1–T11, open questions) |
| `docs/` | `make_docx.js`, `make_deck.js` | `docs` | Test report (.docx) and 18-slide deck (.pptx) |
| `video/` | `make_video.py` | `video` | Narrated 1080p explainer + SRT captions |

`docs/img/` holds the JPEG stills the report and deck embed.

## Coordinates

CAD uses the machine axis as +X (mm) with Z up; simulations use cylindrical (r, z) in metres with
z ≡ CAD X. The proton beam travels in −X onto the ¹¹B foil at X = 0.

## Scope

The simulations are screens, not transport calculations: the orbit pusher is collisionless with no
plasma electric fields and no foil energy loss; the magnet model ignores iron, leads and eddy
currents; hoop stress is a J×B×R estimate. Each script's docstring lists its assumptions.

See [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md) and
[`../docs/REPRODUCIBILITY.md`](../docs/REPRODUCIBILITY.md).
