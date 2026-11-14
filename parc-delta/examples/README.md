# Examples

`synthetic_unit_test_snapshot.json` is a smoke-test fixture. Every rate and power in it is fabricated solely to check the CLI and accounting identity. It is **not** a physically plausible PARC operating point, a fit to a paper, or an estimate of fusion performance.

Run:

```bash
PYTHONPATH=src python -m parc_delta_v10.cli examples/synthetic_unit_test_snapshot.json
```

Expected checks: global closure error is at floating-point zero; wave-to-proton power is reported as coherent species absorption; irreversible proton heating remains `null` because no kinetic thermalization output was supplied.
