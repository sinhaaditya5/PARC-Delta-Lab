## Summary

<!-- What does this change and why? Link the issue it resolves (e.g. "Closes #12"). -->

## Type of change

- [ ] Bug fix
- [ ] New feature / pipeline stage
- [ ] Physics or model change (new research version)
- [ ] Documentation
- [ ] CI / build / tooling

## Effect on published results

<!-- Does any number in deliverables/data, docs/RESULTS.md or the README change?
     If yes, list old → new values and explain why. Write "None" otherwise. -->

## Checklist

- [ ] `make check` passes (lint, integrity, tests, CLI smoke test)
- [ ] Relevant pipeline stages re-run (e.g. `make sims regress`)
- [ ] Tests added or updated for behaviour changes
- [ ] Docs and module docstrings still state scope accurately (no unsupported claims)
- [ ] `parc-delta/` untouched, **or** a new research version with updated `SHA256SUMS.txt`
- [ ] `CHANGELOG.md` updated under *Unreleased*
