"""Diagnostics that distinguish coherent response from irreversible heating."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .ledger import EnergyLedger


@dataclass(frozen=True)
class RoutingMetrics:
    alpha_to_wave_w: float
    wave_to_protons_w: float
    wave_to_boron_w: float
    wave_to_electrons_w: float
    wave_to_other_species_w: float
    wave_absorption_total_w: float
    proton_share_of_wave_absorption: float | None
    irreversible_proton_heating_w: float | None
    irreversible_proton_heating_fraction_of_alpha_birth: float | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "alpha_to_wave_w": self.alpha_to_wave_w,
            "wave_to_protons_w": self.wave_to_protons_w,
            "wave_to_boron_w": self.wave_to_boron_w,
            "wave_to_electrons_w": self.wave_to_electrons_w,
            "wave_to_other_species_w": self.wave_to_other_species_w,
            "wave_absorption_total_w": self.wave_absorption_total_w,
            "proton_share_of_wave_absorption": self.proton_share_of_wave_absorption,
            "irreversible_proton_heating_w": self.irreversible_proton_heating_w,
            "irreversible_proton_heating_fraction_of_alpha_birth": self.irreversible_proton_heating_fraction_of_alpha_birth,
        }


def _sum_transfer(ledger: EnergyLedger, source_prefix: str, destination: str | None = None) -> float:
    return sum(
        x.power_w for x in ledger.transfers
        if x.source.startswith(source_prefix)
        and (destination is None or x.destination == destination)
    )


def _wave_absorption(ledger: EnergyLedger, destination: str) -> float:
    return sum(
        x.power_w for x in ledger.transfers
        if x.source.startswith("wave:") and x.destination == destination
    )


def routing_metrics(
    ledger: EnergyLedger,
    *,
    irreversible_proton_heating_w: float | None = None,
) -> RoutingMetrics:
    """Calculate routing fractions without treating coherent energy as heat.

    `irreversible_proton_heating_w` must come from a collision/phase-mixing or
    kinetic calculation. It is deliberately not inferred from wave->proton
    coherent power absorption.
    """
    if irreversible_proton_heating_w is not None and irreversible_proton_heating_w < 0:
        raise ValueError("irreversible_proton_heating_w must be non-negative")

    # Only count alpha->wave transfers, not alpha->any-particle collisions.
    alpha_to_wave = sum(
        x.power_w for x in ledger.transfers
        if x.source == "alpha_fast" and x.destination.startswith("wave:")
    )
    p_abs = _wave_absorption(ledger, "protons")
    b_abs = _wave_absorption(ledger, "boron_ions")
    e_abs = _wave_absorption(ledger, "electrons")
    all_wave_abs = sum(
        x.power_w for x in ledger.transfers
        if x.source.startswith("wave:") and not x.destination.startswith("wave:")
    )
    known_abs = p_abs + b_abs + e_abs
    other_abs = max(0.0, all_wave_abs - known_abs)
    p_share = p_abs / all_wave_abs if all_wave_abs > 0 else None

    alpha_birth = sum(
        f.power_w for f in ledger.external_flows
        if f.direction == "in" and f.reservoir == "alpha_fast"
    )
    heat_fraction = (
        irreversible_proton_heating_w / alpha_birth
        if irreversible_proton_heating_w is not None and alpha_birth > 0
        else None
    )
    return RoutingMetrics(
        alpha_to_wave_w=alpha_to_wave,
        wave_to_protons_w=p_abs,
        wave_to_boron_w=b_abs,
        wave_to_electrons_w=e_abs,
        wave_to_other_species_w=other_abs,
        wave_absorption_total_w=all_wave_abs,
        proton_share_of_wave_absorption=p_share,
        irreversible_proton_heating_w=irreversible_proton_heating_w,
        irreversible_proton_heating_fraction_of_alpha_birth=heat_fraction,
    )


def ledger_summary(ledger: EnergyLedger, *, tolerance: float = 1e-10) -> dict[str, Any]:
    ledger.assert_closed(tolerance=tolerance)
    return {
        "reservoir_net_power_w": ledger.net_power_w,
        "external_input_w": ledger.external_input_w,
        "external_output_w": ledger.external_output_w,
        "closure_residual_w": ledger.closure_residual_w,
        "relative_closure_error": ledger.relative_closure_error,
        "transfer_count": len(ledger.transfers),
        "external_flow_count": len(ledger.external_flows),
    }


def compare_scenarios(
    baseline_name: str,
    baseline: EnergyLedger,
    candidate_name: str,
    candidate: EnergyLedger,
    *,
    relative_input_tolerance: float = 1e-6,
) -> dict[str, Any]:
    """Compare two snapshots only when boundary input vectors match.

    This is a guard against comparing scenarios with different fuel-source or
    auxiliary-power assumptions. It is not a statistical comparison; the
    caller must propagate shared and unshared uncertainties from upstream data.
    """
    if relative_input_tolerance < 0:
        raise ValueError("relative_input_tolerance must be non-negative")

    def input_map(ledger: EnergyLedger) -> dict[tuple[str, str], float]:
        result: dict[tuple[str, str], float] = {}
        for flow in ledger.external_flows:
            if flow.direction == "in":
                key = (flow.reservoir, flow.label)
                result[key] = result.get(key, 0.0) + flow.power_w
        return result

    a = input_map(baseline)
    b = input_map(candidate)
    if set(a) != set(b):
        raise ValueError("scenario boundary inputs differ; comparison is not controlled")
    for key in a:
        scale = max(abs(a[key]), abs(b[key]), 1.0)
        if abs(a[key] - b[key]) / scale > relative_input_tolerance:
            raise ValueError(f"scenario boundary input mismatch for {key}")

    a_rates = baseline.net_power_w
    b_rates = candidate.net_power_w
    names = sorted(set(a_rates) | set(b_rates))
    return {
        "baseline": baseline_name,
        "candidate": candidate_name,
        "delta_reservoir_net_power_w": {
            name: b_rates.get(name, 0.0) - a_rates.get(name, 0.0)
            for name in names
        },
        "delta_external_output_w": candidate.external_output_w - baseline.external_output_w,
        "boundary_inputs_matched": True,
        "warning": "Snapshot delta only; not a time-integrated plant performance or uncertainty-qualified result.",
    }
