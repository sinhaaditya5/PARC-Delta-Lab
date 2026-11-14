"""Command-line interface for a v1.0 instantaneous snapshot ledger."""

from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Any

from .ledger import ExternalFlow, PowerTransfer
from .modes import GrowthRate, WaveModeSnapshot, assemble_ledger
from .diagnostics import ledger_summary, routing_metrics


def load_payload(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read valid JSON from {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("snapshot root must be a JSON object")
    return payload


def evaluate(payload: dict[str, Any]) -> dict[str, Any]:
    modes = []
    for raw in payload.get("modes", []):
        rates = {
            species: GrowthRate(
                gamma_s_inv=float(item["gamma_s_inv"]),
                sigma_s_inv=float(item.get("sigma_s_inv", 0.0)),
                source_ref=str(item["source_ref"]),
                method=str(item["method"]),
            )
            for species, item in raw["species_growth_rates"].items()
        }
        modes.append(WaveModeSnapshot(
            name=str(raw["name"]),
            energy_j=float(raw["energy_j"]),
            sigma_energy_j=float(raw.get("sigma_energy_j", 0.0)),
            species_growth_rates=rates,
            escape_damping_s_inv=float(raw.get("escape_damping_s_inv", 0.0)),
            sigma_escape_s_inv=float(raw.get("sigma_escape_s_inv", 0.0)),
            rf_drive_w=float(raw.get("rf_drive_w", 0.0)),
            source_ref=str(raw["source_ref"]),
        ))
    external = [ExternalFlow(**x) for x in payload.get("external_flows", [])]
    collisions = [PowerTransfer(**x) for x in payload.get("collisional_transfers", [])]
    nonlinear = [PowerTransfer(**x) for x in payload.get("nonlinear_wave_transfers", [])]
    ledger = assemble_ledger(
        modes,
        external_flows=external,
        collisional_transfers=collisions,
        nonlinear_wave_transfers=nonlinear,
    )
    return {
        "model": "PARC-Delta v1.0 research ledger",
        "scope": "instantaneous power accounting; not a kinetic or reactor prediction",
        "ledger": ledger_summary(ledger),
        "routing_metrics": routing_metrics(
            ledger,
            irreversible_proton_heating_w=payload.get("irreversible_proton_heating_w"),
        ).as_dict(),
        "provenance": payload.get("metadata", {}),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path, help="JSON snapshot satisfying docs/INPUT_CONTRACT.md")
    parser.add_argument("--output", type=Path, help="Optional JSON output path")
    args = parser.parse_args()
    try:
        result = evaluate(load_payload(args.snapshot))
    except (ValueError, KeyError, TypeError, ArithmeticError) as exc:
        parser.error(str(exc))
        return
    rendered = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
