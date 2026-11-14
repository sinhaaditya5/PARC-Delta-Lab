# PARC-Delta Lab — build every result from source.
#
#   make help        list targets
#   make install     research package + prototype dependencies
#   make check       lint + integrity + tests (what CI runs)
#   make sims        magnet → alpha orbits → bench physics
#   make all         the full pipeline (needs Blender, cadcraft-cli, Node, ffmpeg)
#
# External tools are optional and only needed by the stages that use them:
#   BLENDER       Blender 4.x/5.x executable   (renders, turntable)
#   CADCRAFT_CLI  cadcraft-cli binary          (drawing)
#   npm / node    Node >= 20                   (docs)
#   ffmpeg, say   ffmpeg + macOS `say`         (video)

PYTHON  ?= python3
BLENDER ?= blender
NPM     ?= npm
SAMPLES ?= 160
VIEWS   ?= hero cutaway detail

PROTO := prototype

.DEFAULT_GOAL := help
.PHONY: help install install-dev check lint verify test cli-smoke rerun \
        sims magnet orbits bench cad drawing renders turntable diagrams report docs video \
        regress assets all clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "} {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

# ── setup ────────────────────────────────────────────────────────────────
install: ## Install the research package and prototype dependencies
	"$(PYTHON)" -m pip install -e "parc-delta[test]" -r requirements/prototype.txt

install-dev: install ## Also install lint/test tooling and git hooks
	"$(PYTHON)" -m pip install -r requirements/dev.txt
	pre-commit install

# ── quality gates ────────────────────────────────────────────────────────
check: lint verify test cli-smoke ## Run every gate CI runs

lint: ## Ruff on prototype/, fatal-error check on parc-delta/
	ruff check .
	ruff check --select E9,F63,F7,F82 parc-delta

verify: ## Verify parc-delta/ against its SHA-256 release manifest
	./scripts/verify_integrity.sh

test: ## Run the 76-test research suite
	cd parc-delta && "$(PYTHON)" -m pytest -q

cli-smoke: ## Evaluate the synthetic snapshot through the CLI
	cd parc-delta && PYTHONPATH=src "$(PYTHON)" -m parc_delta_v10.cli examples/synthetic_unit_test_snapshot.json > /dev/null

rerun: ## Re-run the v1.6 campaign in an isolated copy (test T2)
	rm -rf runs/v16_rerun && mkdir -p runs
	cp -R parc-delta runs/v16_rerun
	cd runs/v16_rerun && "$(PYTHON)" scripts_run_v16.py > run_v16.log

# ── prototype pipeline ───────────────────────────────────────────────────
sims: bench ## Magnet, alpha-orbit and bench-physics simulations

magnet: ## S2 HTS coil set: field map, mirror ratio, stored energy
	cd $(PROTO)/sim && "$(PYTHON)" magnet_field.py > /dev/null

orbits: magnet ## S3 Boris full-orbit alpha confinement (1-4 T scan)
	cd $(PROTO)/sim && "$(PYTHON)" alpha_orbits.py > /dev/null

bench: orbits ## S4-S6 slowing-down, alpha budget, resonance map
	cd $(PROTO)/sim && "$(PYTHON)" bench_physics.py > /dev/null

cad: ## Parametric STEP assembly + STL groups (build123d)
	cd $(PROTO)/cad && "$(PYTHON)" pdx1_model.py

drawing: ## General-arrangement drawing PDX1-GA-001 (needs cadcraft-cli)
	cd $(PROTO)/drawings && "$(PYTHON)" make_ga_drawing.py

renders: cad sims ## Blender stills with callouts (needs Blender)
	cd $(PROTO)/renders && for v in $(VIEWS); do \
	  "$(BLENDER)" -b --factory-startup -P blender_scene.py -- $$v --samples $(SAMPLES) > out_$$v.log 2>&1 || exit 1; \
	done && "$(PYTHON)" annotate.py $(VIEWS)

turntable: cad sims ## Turntable frames for the video (needs Blender)
	cd $(PROTO)/renders && "$(BLENDER)" -b --factory-startup -P blender_scene.py -- turntable --samples $(SAMPLES)

diagrams: sims ## Architecture, control-loop, energy-flow, validation, roadmap
	cd $(PROTO)/diagrams && "$(PYTHON)" make_diagrams.py

report: sims cad ## Collect T1-T11 into results_summary.json
	cd $(PROTO)/report && "$(PYTHON)" collect_results.py > /dev/null

docs: report diagrams ## Test report (.docx) and deck (.pptx)
	cd $(PROTO)/docs && "$(NPM)" ci --no-audit --no-fund && "$(NPM)" run build

video: report diagrams turntable ## Narrated explainer (macOS: needs `say`)
	cd $(PROTO)/video && "$(PYTHON)" make_video.py

regress: ## Compare regenerated results with deliverables/data (after sims, rerun, report)
	"$(PYTHON)" scripts/check_results.py --rerun-max 1e-6

assets: ## Regenerate README imagery in docs/assets from pipeline outputs
	"$(PYTHON)" scripts/make_readme_assets.py

all: check rerun sims cad drawing renders diagrams report docs video ## Everything

clean: ## Remove generated outputs
	rm -rf $(PROTO)/*/out runs $(PROTO)/renders/out_*.log
