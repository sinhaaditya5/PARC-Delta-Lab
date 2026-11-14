# Contributing to PARC-Delta Lab

Thanks for your interest! This is a research codebase, so correctness and honesty about scope matter
more than feature count. Please read this guide before opening an issue or pull request.

## Ground rules

1. **Keep claims bounded.** Do not add language implying fusion gain, net electricity, reactor
   readiness or validated channeling unless a reproducible result in this repository supports it.
   Module docstrings state scope; keep them accurate.
2. **`parc-delta/` is a frozen release.** Its files are byte-locked by `parc-delta/SHA256SUMS.txt`
   and CI fails on any change. Physics changes belong in a new research version: bump `VERSION` and
   `pyproject.toml`, add a design note under `parc-delta/docs/`, regenerate `results/`, and update
   `FILE_MANIFEST.txt` and `SHA256SUMS.txt` in the same pull request.
3. **One source of truth.** Device geometry and targets live only in
   `prototype/design/pdx1_params.py`. Never hard-code a dimension in a downstream script.
4. **Generated files are not committed.** Each stage writes to its own `out/` (git-ignored). Update
   `deliverables/` or `docs/assets/` only when results intentionally change, and say so in the PR.

## Development setup

```bash
python3 -m venv .venv && source .venv/bin/activate
make install-dev      # package, prototype deps, ruff, pytest, pre-commit hooks
make check            # lint + integrity + tests + CLI smoke test
```

## Workflow

1. Open an issue first for anything beyond a small fix, so the approach can be agreed.
2. Branch from `main`: `feat/…`, `fix/…`, `docs/…`, `ci/…`.
3. Keep commits focused and use [Conventional Commits](https://www.conventionalcommits.org/):
   `feat(sim): …`, `fix(drawings): …`, `docs: …`, `ci: …`, `build: …`, `chore: …`.
4. Add or update tests for behaviour changes. New physics needs a benchmark against an analytic
   result or a published reference, not just a regression snapshot.
5. Run `make check` (and the relevant pipeline stage, e.g. `make sims`) before pushing.
6. Fill in the pull-request template, including the effect on any published number.

## Code style

- Python ≥ 3.10, formatted for 120 columns and linted with Ruff (`ruff check .`).
- Physics notation is welcome (`I` for current, `B0`, `Te`); name units in identifiers
  (`_mm`, `_m3`, `_ev`, `_us`) as the existing code does.
- Every module starts with a docstring stating what it models **and what it does not**.

## Reporting results that disagree with ours

Disagreement is the most valuable contribution. Open an issue with the *Physics / results question*
template, the inputs, your numbers and how you obtained them.
