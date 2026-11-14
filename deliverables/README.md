# Deliverables

Curated outputs of the PDX-1 concept study. Small, diffable artifacts live
here in git. Large binaries are attached to the
[**v1.6.0 GitHub Release**](https://github.com/aditbytes/PARC-Delta-Lab/releases/tag/v1.6.0)
so cloning stays fast. Everything here can be regenerated from source with `make all`.

## In this folder

| Path | What it is | Produced by |
|---|---|---|
| [`data/results_summary.json`](data/results_summary.json) | Every test (T1–T11), open questions, magnet/orbit/bench results | `prototype/report/collect_results.py` |
| [`data/magnet_summary.json`](data/magnet_summary.json) | Coil currents, B0, mirror ratio, stored energy, conductor field, hoop stress | `prototype/sim/magnet_field.py` |
| [`data/alpha_orbit_summary.json`](data/alpha_orbit_summary.json) | Alpha fates vs field (1–4 T), loss cone, target-offset scan | `prototype/sim/alpha_orbits.py` |
| [`data/bench_physics_summary.json`](data/bench_physics_summary.json) | Slowing-down, alpha inventory budget, IBW resonance map | `prototype/sim/bench_physics.py` |
| [`cad/pdx1_parts.json`](cad/pdx1_parts.json) | 150-part list with groups, roles and bounding boxes | `prototype/cad/pdx1_model.py` |
| [`drawing/PDX1-GA-001.pdf`](drawing/PDX1-GA-001.pdf) | General-arrangement drawing, A0 at 1:10 | `prototype/drawings/make_ga_drawing.py` |
| [`drawing/PDX1-GA-001.dxf`](drawing/PDX1-GA-001.dxf) | Same drawing as editable DXF | ″ |
| [`video/PDX1_explainer.srt`](video/PDX1_explainer.srt) | Captions for the explainer video | `prototype/video/make_video.py` |

## Release assets (v1.6.0)

| File | Size | Description |
|---|---:|---|
| `PDX1_explainer.mp4` | 23 MB | 3 min 22 s narrated 1080p explainer |
| `PARC-Delta_PDX-1_Test_Report.docx` | 4 MB | Full test report (T1–T11, claims boundary, open questions) |
| `PARC-Delta_PDX-1_Investor_Deck.pptx` | 2 MB | 18-slide deck with speaker notes |
| `pdx1_assembly.step` | 4 MB | Labelled, coloured STEP assembly (150 parts) |
| `pdx1_scene.blend` | 2 MB | Blender scene used for the renders |
| `pdx1_renders_full_res.zip` | 13 MB | Hero, cutaway and detail renders at 1920×1080, plain and annotated |
| `pdx1_figures_full_res.zip` | 3 MB | All simulation charts and diagrams at full resolution |
| `PARC-Delta-Lab_v1.6.0_deliverables.zip` | ~46 MB | Everything above in one archive |

## Status

Concept study. PDX-1 is **not** a reactor and is **not** engineered for
fabrication. See the claims boundary in the [top-level README](../README.md#claims-boundary).
