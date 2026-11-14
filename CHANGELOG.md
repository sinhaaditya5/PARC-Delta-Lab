# Changelog

All notable changes to this repository are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow
[Semantic Versioning](https://semver.org/) with the research package's version.

## [Unreleased]

## [1.6.0] - 2026-11-14

First public release of PARC-Delta Lab.

### Added

- **Research package** `parc-delta/` (PARC-Delta 1.6.0-research), byte-identical to its release
  manifest: 12 modules, 76 tests, campaign runners and archived results for v1.1–v1.6.
- **PDX-1 prototype pipeline**: shared design parameters, HTS magnet solver, Boris full-orbit alpha
  confinement, bench physics budget and IBW resonance map, build123d CAD model, CADCraft GA drawing,
  Blender renders with callouts, system diagrams, results collector, docx/pptx generators and
  explainer video.
- `Makefile` covering every stage, pinned `requirements/`, portable SHA-256 integrity check and README
  asset generator.
- Curated `deliverables/` (result summaries, parts list, drawing, captions); large binaries attached to
  the GitHub Release.
- Documentation: README with gallery, architecture, reproducibility guide, full results.
- CI (lint, integrity, tests on Linux/macOS × Python 3.10–3.13, pipeline run with artifacts, docs
  check), CodeQL, release workflow, Dependabot, issue/PR templates, pre-commit hooks.

### Changed

- Research package directory renamed `PARC-Delta-v1.6/` → `parc-delta/`; version now lives in
  `VERSION`, `pyproject.toml` and git tags.
- Pipeline scripts use repository-relative paths instead of a machine-specific lab folder.
- `make_deck.js` no longer requires an external theme script (`PPTX_SKILL` is optional).

### Fixed

- `collect_results.py` no longer crashes on a fresh clone before `make rerun`.
- `make_ga_drawing.py` found `cadcraft-cli` only via `PATH`; it now honours `CADCRAFT_CLI` and
  `<repo>/tools`.
- The deck's title-slide render had a local filesystem path as its alt text.

## Research package history

Summarised from `parc-delta/docs/`; see each design note for detail.

| Version | Change |
|---|---|
| 1.6 | Time-dependent Rosenbluth test-particle alpha slowing-down; TA and Nanbu comparators; multispecies subcycling sweep (K = 32 still captures only 92.9 % / 93.9 % of energy loss) |
| 1.5 | Landau–Spitzer collision-rate validation and reaction-source collision moments |
| 1.4 | Sequential p–¹¹B → 3α birth kinematics (α0, α1); conserving pairwise Coulomb Monte Carlo |
| 1.3 | Finite-k∥ kinetic IBW susceptibility |
| 1.2 | Mass-convention, finite-width and pole-broadening sensitivity |
| 1.1 | Reproduction of the published collisionless perpendicular p–α IBW model |
| 1.0 | Instantaneous energy ledger, wave-mode snapshots and CLI |
| 0.9 | Zero-dimensional p–¹¹B screening model (archived in `parc-delta/legacy/`) |

[Unreleased]: https://github.com/aditbytes/PARC-Delta-Lab/compare/v1.6.0...HEAD
[1.6.0]: https://github.com/aditbytes/PARC-Delta-Lab/releases/tag/v1.6.0
