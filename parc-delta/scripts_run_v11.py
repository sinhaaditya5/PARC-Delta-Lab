"""Reproduce the v1.1 linear IBW benchmark and write JSON results."""
from pathlib import Path
from parc_delta_v10.linear_ibw import run_reference_case

if __name__ == "__main__":
    output = Path("results/v11_linear_ibw_reference.json")
    run_reference_case(output)
    print(f"Wrote {output}")
