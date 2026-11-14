"""Energy-conserving instantaneous power ledger.

The ledger is an accounting/verification layer. It does not calculate plasma
susceptibilities, collision operators, nonlinear saturation, or fusion rates.
Those must be supplied by an independently validated kinetic or experimental
model. All powers are in watts and all stored energies are in joules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Iterable


def _finite_nonnegative(value: float, name: str) -> None:
    if not math.isfinite(value) or value < 0.0:
        raise ValueError(f"{name} must be finite and non-negative")


def _nonblank(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


@dataclass(frozen=True)
class PowerTransfer:
    """Internal directed power flow from one reservoir to another."""

    source: str
    destination: str
    power_w: float
    kind: str
    source_ref: str
    sigma_w: float = 0.0

    def __post_init__(self) -> None:
        _nonblank(self.source, "source")
        _nonblank(self.destination, "destination")
        _nonblank(self.kind, "kind")
        _nonblank(self.source_ref, "source_ref")
        if self.source == self.destination:
            raise ValueError("A transfer must connect two different reservoirs")
        _finite_nonnegative(self.power_w, "power_w")
        _finite_nonnegative(self.sigma_w, "sigma_w")


@dataclass(frozen=True)
class ExternalFlow:
    """Power entering or leaving the model boundary at a named reservoir."""

    reservoir: str
    power_w: float
    direction: str  # 'in' or 'out'
    label: str
    source_ref: str
    sigma_w: float = 0.0

    def __post_init__(self) -> None:
        _nonblank(self.reservoir, "reservoir")
        _nonblank(self.label, "label")
        _nonblank(self.source_ref, "source_ref")
        if self.direction not in {"in", "out"}:
            raise ValueError("direction must be 'in' or 'out'")
        _finite_nonnegative(self.power_w, "power_w")
        _finite_nonnegative(self.sigma_w, "sigma_w")


@dataclass
class EnergyLedger:
    """Instantaneous balance over particle, wave, and loss reservoirs.

    `net_power_w[r]` is dE_r/dt. Internal transfers cancel in the global sum;
    only boundary sources and boundary losses change total stored energy.
    """

    transfers: list[PowerTransfer] = field(default_factory=list)
    external_flows: list[ExternalFlow] = field(default_factory=list)
    reservoirs: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        self.reservoirs = set(self.reservoirs)
        for flow in self.transfers:
            self.reservoirs.update((flow.source, flow.destination))
        for flow in self.external_flows:
            self.reservoirs.add(flow.reservoir)

    def add_transfer(self, transfer: PowerTransfer) -> None:
        self.transfers.append(transfer)
        self.reservoirs.update((transfer.source, transfer.destination))

    def add_external_flow(self, flow: ExternalFlow) -> None:
        self.external_flows.append(flow)
        self.reservoirs.add(flow.reservoir)

    @property
    def net_power_w(self) -> dict[str, float]:
        rates = {name: 0.0 for name in sorted(self.reservoirs)}
        for flow in self.transfers:
            rates[flow.source] -= flow.power_w
            rates[flow.destination] += flow.power_w
        for flow in self.external_flows:
            sign = 1.0 if flow.direction == "in" else -1.0
            rates[flow.reservoir] += sign * flow.power_w
        return rates

    @property
    def external_input_w(self) -> float:
        return sum(f.power_w for f in self.external_flows if f.direction == "in")

    @property
    def external_output_w(self) -> float:
        return sum(f.power_w for f in self.external_flows if f.direction == "out")

    @property
    def closure_residual_w(self) -> float:
        """Should be zero up to floating-point roundoff."""
        return (
            sum(self.net_power_w.values())
            - (self.external_input_w - self.external_output_w)
        )

    @property
    def relative_closure_error(self) -> float:
        scale = max(self.external_input_w, self.external_output_w, 1.0)
        return abs(self.closure_residual_w) / scale

    def assert_closed(self, tolerance: float = 1e-10) -> None:
        _finite_nonnegative(tolerance, "tolerance")
        if self.relative_closure_error > tolerance:
            raise ArithmeticError(
                "Energy ledger failed closure: "
                f"relative residual={self.relative_closure_error:.6e}, "
                f"tolerance={tolerance:.6e}"
            )

    def transfers_from(self, reservoir: str) -> list[PowerTransfer]:
        return [x for x in self.transfers if x.source == reservoir]

    def transfers_to(self, reservoir: str) -> list[PowerTransfer]:
        return [x for x in self.transfers if x.destination == reservoir]

    def flows(self, *, direction: str | None = None, label: str | None = None) -> list[ExternalFlow]:
        out = self.external_flows
        if direction is not None:
            out = [x for x in out if x.direction == direction]
        if label is not None:
            out = [x for x in out if x.label == label]
        return list(out)


def combine_ledgers(ledgers: Iterable[EnergyLedger]) -> EnergyLedger:
    """Combine independent subsystem ledgers without losing provenance."""
    combined = EnergyLedger()
    for ledger in ledgers:
        for transfer in ledger.transfers:
            combined.add_transfer(transfer)
        for flow in ledger.external_flows:
            combined.add_external_flow(flow)
    return combined
