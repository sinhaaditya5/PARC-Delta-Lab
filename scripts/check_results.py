#!/usr/bin/env python3
"""Regression-check regenerated pipeline outputs against the published results.

Compares every numeric leaf of the freshly generated simulation summaries in
prototype/sim/out/ with the curated copies in deliverables/data/, ignoring
wall-clock fields. Optionally asserts the T2 reproducibility bound recorded by
prototype/report/collect_results.py.

Usage:
  python scripts/check_results.py [--rtol 1e-6] [--atol 1e-12] [--only magnet bench]
                                  [--tol orbits 0.05 0.01] [--rerun-max 1e-6]

Exit status is non-zero if any value is outside tolerance or an input is missing.
When $GITHUB_STEP_SUMMARY is set, a Markdown table is appended to it.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections.abc import Iterator
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIM = ROOT / "prototype" / "sim" / "out"
PUBLISHED = ROOT / "deliverables" / "data"
REPORT = ROOT / "prototype" / "report" / "out" / "results_summary.json"

TARGETS = {
    "magnet": "magnet_summary.json",
    "orbits": "alpha_orbit_summary.json",
    "bench": "bench_physics_summary.json",
}
IGNORED_KEYS = {"runtime_s", "build_seconds"}


def numeric_leaves(obj: object, path: str = "") -> Iterator[tuple[str, float]]:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key not in IGNORED_KEYS:
                yield from numeric_leaves(value, f"{path}.{key}" if path else str(key))
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            yield from numeric_leaves(value, f"{path}[{i}]")
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        yield path, float(obj)


def compare(name: str, rtol: float, atol: float) -> tuple[bool, str]:
    new_path, ref_path = SIM / TARGETS[name], PUBLISHED / TARGETS[name]
    if not new_path.exists():
        return False, f"| {name} | missing `{new_path.relative_to(ROOT)}` (run the pipeline first) | ❌ |"
    new = dict(numeric_leaves(json.loads(new_path.read_text())))
    ref = dict(numeric_leaves(json.loads(ref_path.read_text())))
    missing = sorted(set(ref) ^ set(new))
    worst_key, worst_abs, worst_rel, failures = "", 0.0, 0.0, 0
    for key in sorted(set(ref) & set(new)):
        a, b = new[key], ref[key]
        if math.isnan(a) and math.isnan(b):
            continue
        diff = abs(a - b)
        rel = diff / abs(b) if b else (0.0 if diff == 0 else math.inf)
        if diff > atol + rtol * abs(b):
            failures += 1
        if rel > worst_rel or (rel == worst_rel and diff > worst_abs):
            worst_key, worst_abs, worst_rel = key, diff, rel
    ok = failures == 0 and not missing
    worst = "exact match" if worst_rel == 0 else f"worst `{worst_key}` rel {worst_rel:.2e} abs {worst_abs:.2e}"
    detail = f"{len(ref)} values; {worst}; {failures} outside rtol={rtol:g}, atol={atol:g}"
    if missing:
        detail += f"; key mismatch: {missing[:5]}"
    return ok, f"| {name} | {detail} | {'✅' if ok else '❌'} |"


def check_rerun(limit: float) -> tuple[bool, str]:
    if not REPORT.exists():
        return False, "| T2 rerun | missing results_summary.json (run `make rerun report`) | ❌ |"
    repro = json.loads(REPORT.read_text())["reproducibility"]
    value = repro["max_rel_diff"]
    ok = repro["values_compared"] > 0 and isinstance(value, (int, float)) and value <= limit
    return ok, (f"| T2 rerun | {repro['values_compared']} values in {repro['file_count']} files; "
                f"max rel diff {value:.2e} (limit {limit:g}) | {'✅' if ok else '❌'} |")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rtol", type=float, default=1e-6)
    ap.add_argument("--atol", type=float, default=1e-12)
    ap.add_argument("--tol", nargs=3, action="append", default=[], metavar=("NAME", "RTOL", "ATOL"),
                    help="per-output tolerance override, e.g. --tol orbits 0.05 0.01")
    ap.add_argument("--only", nargs="+", choices=sorted(TARGETS), default=sorted(TARGETS))
    ap.add_argument("--rerun-max", type=float, default=None, help="assert T2 max relative difference")
    args = ap.parse_args()

    overrides = {name: (float(rtol), float(atol)) for name, rtol, atol in args.tol}
    rows, all_ok = [], True
    for name in args.only:
        rtol, atol = overrides.get(name, (args.rtol, args.atol))
        ok, row = compare(name, rtol, atol)
        rows.append(row)
        all_ok &= ok
    if args.rerun_max is not None:
        ok, row = check_rerun(args.rerun_max)
        rows.append(row)
        all_ok &= ok

    table = "\n".join(["| Output | Comparison with published results | |", "|---|---|:--:|", *rows])
    print(table)
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write("### Results regression\n\n" + table + "\n")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
