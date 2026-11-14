"""Convert species-resolved linear growth/damping rates into power flows.

Convention: perturbations vary as exp(-i*omega*t), with
omega = omega_r + i*gamma. Therefore gamma > 0 is amplitude growth and the
wave-energy contribution is 2*gamma*W. A positive species gamma means that
the species drives the wave and loses particle energy. A negative species
gamma means that the species damps/absorbs the wave and gains particle energy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Mapping

from .ledger import EnergyLedger, ExternalFlow, PowerTransfer


@dataclass(frozen=True)
class GrowthRate:
    gamma_s_inv: float
    sigma_s_inv: float
    source_ref: str
    method: str

    def __post_init__(self) -> None:
        if not math.isfinite(self.gamma_s_inv):
            raise ValueError("gamma_s_inv must be finite")
        if not math.isfinite(self.sigma_s_inv) or self.sigma_s_inv < 0:
            raise ValueError("sigma_s_inv must be finite and non-negative")
        if not self.source_ref.strip():
            raise ValueError("source_ref is required; use an explicit synthetic URI in tests")
        if not self.method.strip():
            raise ValueError("method is required")


@dataclass(frozen=True)
class WaveModeSnapshot:
    name: str
    energy_j: float
    sigma_energy_j: float
    species_growth_rates: Mapping[str, GrowthRate]
    escape_damping_s_inv: float
    sigma_escape_s_inv: float
    rf_drive_w: float = 0.0
    source_ref: str = ""

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("wave mode name is required")
        for value, label in (
            (self.energy_j, "energy_j"),
            (self.sigma_energy_j, "sigma_energy_j"),
            (self.escape_damping_s_inv, "escape_damping_s_inv"),
            (self.sigma_escape_s_inv, "sigma_escape_s_inv"),
            (self.rf_drive_w, "rf_drive_w"),
        ):
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{label} must be finite and non-negative")
        if not self.species_growth_rates:
            raise ValueError("at least one species growth/damping rate is required")
        if not self.source_ref.strip():
            raise ValueError("mode source_ref is required")

    @property
    def reservoir(self) -> str:
        return f"wave:{self.name}"

    @property
    def net_species_growth_s_inv(self) -> float:
        return sum(rate.gamma_s_inv for rate in self.species_growth_rates.values())

    @property
    def net_wave_power_w(self) -> float:
        return (
            2.0 * self.energy_j * (
                self.net_species_growth_s_inv - self.escape_damping_s_inv
            )
            + self.rf_drive_w
        )


def _power_and_sigma(gamma: float, sigma_gamma: float, energy: float, sigma_energy: float) -> tuple[float, float]:
    power_signed = 2.0 * gamma * energy
    # First-order independent-uncertainty propagation. Correlated uncertainties
    # must be supplied/handled by the upstream kinetic solver, not inferred here.
    sigma = 2.0 * math.sqrt((energy * sigma_gamma) ** 2 + (gamma * sigma_energy) ** 2)
    return power_signed, sigma


def mode_to_ledger_terms(mode: WaveModeSnapshot) -> tuple[list[PowerTransfer], list[ExternalFlow]]:
    """Return directed particle-wave exchanges and external mode input/losses."""
    transfers: list[PowerTransfer] = []
    external: list[ExternalFlow] = []

    for species, rate in mode.species_growth_rates.items():
        signed_power, sigma = _power_and_sigma(
            rate.gamma_s_inv, rate.sigma_s_inv, mode.energy_j, mode.sigma_energy_j
        )
        if signed_power >= 0.0:
            source, destination = species, mode.reservoir
        else:
            source, destination = mode.reservoir, species
        transfers.append(PowerTransfer(
            source=source,
            destination=destination,
            power_w=abs(signed_power),
            kind="linear_wave_particle_exchange",
            source_ref=f"{mode.source_ref} | {rate.source_ref} | {rate.method}",
            sigma_w=sigma,
        ))

    escape_power, escape_sigma = _power_and_sigma(
        -mode.escape_damping_s_inv,
        mode.sigma_escape_s_inv,
        mode.energy_j,
        mode.sigma_energy_j,
    )
    external.append(ExternalFlow(
        reservoir=mode.reservoir,
        power_w=abs(escape_power),
        direction="out",
        label="wave_escape_or_unmodelled_mode_loss",
        source_ref=mode.source_ref,
        sigma_w=escape_sigma,
    ))
    if mode.rf_drive_w > 0.0:
        external.append(ExternalFlow(
            reservoir=mode.reservoir,
            power_w=mode.rf_drive_w,
            direction="in",
            label="external_rf_drive",
            source_ref=mode.source_ref,
        ))
    return transfers, external


def assemble_ledger(
    modes: list[WaveModeSnapshot],
    *,
    external_flows: list[ExternalFlow] | None = None,
    collisional_transfers: list[PowerTransfer] | None = None,
    nonlinear_wave_transfers: list[PowerTransfer] | None = None,
) -> EnergyLedger:
    """Assemble an instantaneous multi-species/multi-wave energy ledger."""
    ledger = EnergyLedger()
    for mode in modes:
        transfers, flows = mode_to_ledger_terms(mode)
        for item in transfers:
            ledger.add_transfer(item)
        for item in flows:
            ledger.add_external_flow(item)
    for transfer in (collisional_transfers or []):
        ledger.add_transfer(transfer)
    for transfer in (nonlinear_wave_transfers or []):
        if not (transfer.source.startswith("wave:") and transfer.destination.startswith("wave:")):
            raise ValueError("nonlinear_wave_transfers must connect wave reservoirs")
        ledger.add_transfer(transfer)
    for flow in (external_flows or []):
        ledger.add_external_flow(flow)
    return ledger
