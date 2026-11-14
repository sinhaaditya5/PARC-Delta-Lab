#!/usr/bin/env python3
"""PARC-Delta zero-dimensional p-B11 screening model.

Scope
-----
This is a transparent, literature-anchored *screening* calculation. It is not
an integrated fusion-reactor simulation, a plasma kinetic solver, or a power-
plant design. It evaluates Maxwellian p-B11 reactivity, a published
relativistic bremsstrahlung approximation, a zero-dimensional plasma energy
content, and a simplified Lawson-style confinement screen.

The model intentionally does NOT claim to model PARC-Delta's proposed
phase-space adaptive alpha routing. It identifies the plasma operating points
and effective energy-recovery fraction that such an architecture would have
to beat. A separate kinetic/particle-transport model is required to evaluate
whether the proposed routing mechanism can achieve those targets.

Equations and parameter sources are documented in ../REPORT.md.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

KEV_TO_J = 1.602176634e-16
ME_C2_KEV = 510.99895
E_FUSION_KEV = 8680.0
C_BREMS = 5.39e-37
BREMS_UNIT_FACTOR = 6.242e15


@dataclass(frozen=True)
class ReactivityFit:
    name: str
    p1: float  # keV m^3 s^-1
    p2: float  # keV^-1
    p3: float  # keV^-1
    p4: float  # keV^-2
    p5: float  # keV^-2
    p6: float  # keV^-3
    p7: float  # keV^-3
    e_g: float = 22589.0  # keV
    mu_c2: float = 859526.0  # keV
    valid_min_keV: float = 70.0
    valid_max_keV: float = 500.0


TENTORI_BELLONI = ReactivityFit(
    name="Tentori-Belloni-2023",
    p1=9.7827e-14,
    p2=-5.1610e-2,
    p3=1.3240e-1,
    p4=3.8446e-4,
    p5=1.2499e-3,
    p6=-5.6715e-6,
    p7=1.1615e-6,
)

NEVINS_SWAIN = ReactivityFit(
    name="Nevins-Swain-2000",
    p1=4.4467e-14,
    p2=-5.9357e-2,
    p3=2.0165e-1,
    p4=1.0404e-3,
    p5=2.7621e-3,
    p6=-9.1653e-6,
    p7=9.8305e-7,
)

FITS = {fit.name: fit for fit in (TENTORI_BELLONI, NEVINS_SWAIN)}


def maxwellian_reactivity(ti_keV: float, fit: ReactivityFit = TENTORI_BELLONI) -> float:
    """Return <sigma v> [m^3/s] from the high-temperature Peres fit.

    The published fit is stated for 70 <= Ti <= 500 keV. Extrapolation is
    intentionally rejected. The Padé truncation keeps P2/P4/P6 in the
    numerator and P3/P5/P7 in the denominator, as in the source parameter set.
    """
    if not (fit.valid_min_keV <= ti_keV <= fit.valid_max_keV):
        raise ValueError(
            f"Ti={ti_keV:g} keV outside fit validity "
            f"[{fit.valid_min_keV:g}, {fit.valid_max_keV:g}] keV"
        )
    if ti_keV <= 0:
        raise ValueError("Ion temperature must be positive")

    numerator = fit.p2 + ti_keV * (fit.p4 + ti_keV * fit.p6)
    denominator = 1.0 + ti_keV * (fit.p3 + ti_keV * (fit.p5 + ti_keV * fit.p7))
    theta = ti_keV / (1.0 - ti_keV * numerator / denominator)
    if not math.isfinite(theta) or theta <= 0:
        raise ArithmeticError(f"Invalid Padé effective temperature theta={theta}")

    xi = (fit.e_g / (4.0 * theta)) ** (1.0 / 3.0)
    value = (
        fit.p1
        * theta
        * math.sqrt(xi / (fit.mu_c2 * ti_keV**3))
        * math.exp(-3.0 * xi)
    )
    if not math.isfinite(value) or value <= 0:
        raise ArithmeticError(f"Invalid reactivity value: {value}")
    return value


def mixture_properties(boron_ion_fraction: float = 0.10) -> dict[str, float]:
    """Return charge-balanced mixture factors for p + B11.

    `boron_ion_fraction` is n_B/(n_p+n_B). Both ion species are singly
    counted in n_i; their nuclear charges are Z_p=1 and Z_B=5.
    """
    if not 0.0 < boron_ion_fraction < 1.0:
        raise ValueError("Boron ion fraction must be between 0 and 1")
    a_b = boron_ion_fraction
    a_p = 1.0 - a_b
    z_p, z_b = 1.0, 5.0
    z_i = a_p * z_p + a_b * z_b
    z_eff = (a_p * z_p**2 + a_b * z_b**2) / z_i
    x = a_p / a_b  # n_p / n_B
    pair_factor = x / (x + z_b) ** 2
    ion_to_electron_density = 1.0 / z_i
    return {
        "boron_ion_fraction": a_b,
        "proton_to_boron_density_ratio": x,
        "Z_i_average": z_i,
        "Z_eff": z_eff,
        "fusion_pair_factor": pair_factor,
        "n_i_over_n_e": ion_to_electron_density,
    }


def bremsstrahlung_relativistic_factor(te_keV: float, z_eff: float) -> float:
    """Relativistic correction gamma(Zeff) from the 2026 screening paper."""
    if te_keV <= 0 or z_eff <= 0:
        raise ValueError("Te and Zeff must be positive")
    t = te_keV / ME_C2_KEV
    return z_eff * (1.0 + 1.78 * t**1.34) + 2.12 * t * (
        1.0 + 1.1 * t + t**2 - 1.25 * t**2.5
    )


def evaluate_state(
    ti_keV: float,
    te_over_ti: float,
    ne_m3: float,
    tau_e_s: float,
    *,
    fit: ReactivityFit = TENTORI_BELLONI,
    boron_ion_fraction: float = 0.10,
    energy_recovery_factor: float = 1.0 / 3.0,
    direct_converter_efficiency: float = 0.80,
    auxiliary_fraction_of_fusion: float = 0.0,
) -> dict[str, float | str | bool]:
    """Evaluate one 0-D screening state.

    `energy_recovery_factor` is the effective fraction used in the published
    Lawson-style inequality eta*(P_fus-P_brem) >= W/tau_E. The 1/3 default is
    the convention used by Ahmad et al. (2026); it is not a measured PARC
    alpha-channeling efficiency.

    The direct-electricity result is an intentionally optimistic accounting
    bound: eta_DEC*(1-eta)*(P_fus-P_brem)-P_aux. It assumes all residual
    post-bremsstrahlung fusion power is accessible to the converter. It omits
    many real losses and must not be interpreted as predicted plant output.
    """
    if ne_m3 <= 0 or tau_e_s <= 0:
        raise ValueError("Density and energy confinement time must be positive")
    if not 0 < te_over_ti <= 1.5:
        raise ValueError("Te/Ti must be in (0, 1.5]")
    if not 0 <= energy_recovery_factor <= 1:
        raise ValueError("Energy recovery factor must be in [0, 1]")
    if not 0 <= direct_converter_efficiency <= 1:
        raise ValueError("Direct converter efficiency must be in [0, 1]")
    if not 0 <= auxiliary_fraction_of_fusion < 2:
        raise ValueError("Auxiliary fraction must be in [0, 2)")

    mix = mixture_properties(boron_ion_fraction)
    te_keV = ti_keV * te_over_ti
    sigv = maxwellian_reactivity(ti_keV, fit)

    # P_fus = n_p*n_B*<sigma v>*E_fus, charge balance expressed via n_e.
    pfus_keV_m3_s = (
        mix["fusion_pair_factor"] * ne_m3**2 * sigv * E_FUSION_KEV
    )

    gamma = bremsstrahlung_relativistic_factor(te_keV, mix["Z_eff"])
    pbrem_keV_m3_s = (
        BREMS_UNIT_FACTOR
        * C_BREMS
        * ne_m3**2
        * math.sqrt(te_keV)
        * gamma
    )

    pfus_W_m3 = pfus_keV_m3_s * KEV_TO_J
    pbrem_W_m3 = pbrem_keV_m3_s * KEV_TO_J
    net_fusion_minus_brem_W_m3 = pfus_W_m3 - pbrem_W_m3

    ni_m3 = ne_m3 * mix["n_i_over_n_e"]
    energy_density_J_m3 = 1.5 * (
        ti_keV * ni_m3 + te_keV * ne_m3
    ) * KEV_TO_J
    transport_loss_W_m3 = energy_density_J_m3 / tau_e_s

    if net_fusion_minus_brem_W_m3 > 0:
        eta_required = transport_loss_W_m3 / net_fusion_minus_brem_W_m3
        n_tau_required = (
            ne_m3 * energy_density_J_m3
            / (energy_recovery_factor * net_fusion_minus_brem_W_m3)
        )
    else:
        eta_required = math.inf
        n_tau_required = math.inf

    plasma_margin_W_m3 = (
        energy_recovery_factor * net_fusion_minus_brem_W_m3
        - transport_loss_W_m3
    )
    # Avoid classifying a mathematically threshold-matched state as failing
    # because of floating-point roundoff (typically ~1e-5 W/m^3 here).
    numerical_tolerance = max(1e-12, 1e-10 * max(
        abs(energy_recovery_factor * net_fusion_minus_brem_W_m3),
        abs(transport_loss_W_m3),
        1.0,
    ))
    self_sustaining_in_screen = plasma_margin_W_m3 >= -numerical_tolerance

    # Deliberately optimistic upper bound; excludes unmodelled losses.
    dc_gross_W_m3 = (
        direct_converter_efficiency
        * (1.0 - energy_recovery_factor)
        * max(0.0, net_fusion_minus_brem_W_m3)
    )
    auxiliary_W_m3 = auxiliary_fraction_of_fusion * pfus_W_m3
    dc_net_upper_bound_W_m3 = dc_gross_W_m3 - auxiliary_W_m3

    return {
        "fit": fit.name,
        "Ti_keV": ti_keV,
        "Te_over_Ti": te_over_ti,
        "Te_keV": te_keV,
        "ne_m3": ne_m3,
        "tau_E_s": tau_e_s,
        "reactivity_m3_s": sigv,
        "Z_eff": mix["Z_eff"],
        "P_fusion_W_m3": pfus_W_m3,
        "P_brems_W_m3": pbrem_W_m3,
        "P_fusion_minus_brems_W_m3": net_fusion_minus_brem_W_m3,
        "brems_over_fusion": pbrem_W_m3 / pfus_W_m3,
        "plasma_energy_density_J_m3": energy_density_J_m3,
        "transport_loss_W_m3": transport_loss_W_m3,
        "eta_support_required": eta_required,
        "n_e_tau_required_m3_s": n_tau_required,
        "eta_support_assumed": energy_recovery_factor,
        "plasma_margin_W_m3": plasma_margin_W_m3,
        "self_sustaining_in_screen": self_sustaining_in_screen,
        "direct_electric_gross_upper_bound_W_m3": dc_gross_W_m3,
        "auxiliary_power_assumed_W_m3": auxiliary_W_m3,
        "direct_electric_net_upper_bound_W_m3": dc_net_upper_bound_W_m3,
    }


def sweep(
    *,
    fit: ReactivityFit,
    te_ratios: Iterable[float] = (1.0, 0.5, 0.25),
    ti_min: int = 75,
    ti_max: int = 500,
    ti_step: int = 5,
    ne_m3: float = 1e20,
    tau_e_s: float = 1.0,
    eta: float = 1.0 / 3.0,
) -> list[dict[str, float | str | bool]]:
    rows = []
    for ratio in te_ratios:
        for ti in range(ti_min, ti_max + 1, ti_step):
            row = evaluate_state(
                float(ti), ratio, ne_m3, tau_e_s, fit=fit,
                energy_recovery_factor=eta,
                direct_converter_efficiency=0.0,
                auxiliary_fraction_of_fusion=0.0,
            )
            rows.append(row)
    return rows


def summarize_lawson(rows: list[dict[str, float | str | bool]]) -> list[dict[str, float | str | bool]]:
    summaries = []
    grouped: dict[tuple[str, float], list[dict[str, float | str | bool]]] = {}
    for row in rows:
        grouped.setdefault((str(row["fit"]), float(row["Te_over_Ti"])), []).append(row)
    for (fit_name, ratio), group in grouped.items():
        viable = [r for r in group if math.isfinite(float(r["n_e_tau_required_m3_s"]))]
        if viable:
            best = min(viable, key=lambda r: float(r["n_e_tau_required_m3_s"]))
            summaries.append({
                "fit": fit_name,
                "Te_over_Ti": ratio,
                "best_Ti_keV": float(best["Ti_keV"]),
                "min_n_e_tau_required_m3_s": float(best["n_e_tau_required_m3_s"]),
                "brems_over_fusion_at_minimum": float(best["brems_over_fusion"]),
                "positive_fusion_minus_brems_window": True,
            })
        else:
            summaries.append({
                "fit": fit_name,
                "Te_over_Ti": ratio,
                "best_Ti_keV": math.nan,
                "min_n_e_tau_required_m3_s": math.inf,
                "brems_over_fusion_at_minimum": math.nan,
                "positive_fusion_minus_brems_window": False,
            })
    return summaries


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("results"))
    parser.add_argument("--density", type=float, default=1e20, help="Electron density [m^-3]")
    parser.add_argument("--tau-e", type=float, default=1.0, help="Energy confinement time [s]")
    parser.add_argument("--eta", type=float, default=1.0 / 3.0, help="Effective energy-recovery factor")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict] = []
    for fit in (TENTORI_BELLONI, NEVINS_SWAIN):
        all_rows.extend(sweep(
            fit=fit, ne_m3=args.density, tau_e_s=args.tau_e, eta=args.eta
        ))

    summaries = summarize_lawson(all_rows)
    write_csv(args.out / "lawson_sweep.csv", all_rows)
    write_csv(args.out / "lawson_summary.csv", summaries)
    (args.out / "lawson_summary.json").write_text(
        json.dumps(summaries, indent=2, allow_nan=True), encoding="utf-8"
    )

    # Example PARC-Delta screening state at a literature-relevant operating point.
    # The selected density/confinement pair is mathematical normalization only;
    # it is not claimed to be an achievable reactor operating point.
    example_ti = 260.0
    example_ratio = 0.25
    example_ne = 1e21
    base = evaluate_state(
        example_ti, example_ratio, example_ne, tau_e_s=15.0904457236,
        fit=TENTORI_BELLONI, energy_recovery_factor=1.0/3.0,
        direct_converter_efficiency=0.80,
        auxiliary_fraction_of_fusion=0.0,
    )
    (args.out / "example_state.json").write_text(
        json.dumps(base, indent=2, allow_nan=True), encoding="utf-8"
    )

    try:
        import matplotlib.pyplot as plt
        for ratio in (1.0, 0.5, 0.25):
            subset = [r for r in all_rows if r["fit"] == TENTORI_BELLONI.name and r["Te_over_Ti"] == ratio]
            xs = [float(r["Ti_keV"]) for r in subset]
            ys = [float(r["n_e_tau_required_m3_s"]) if math.isfinite(float(r["n_e_tau_required_m3_s"])) else math.nan for r in subset]
            plt.plot(xs, ys, label=f"Te/Ti = {ratio:g}")
        plt.yscale("log")
        plt.xlabel("Ion temperature Ti (keV)")
        plt.ylabel("Required ne × tauE (m^-3 s), eta = 1/3")
        plt.title("p-B11 Maxwellian Lawson screening (Tentori–Belloni fit)")
        plt.legend()
        plt.grid(True, which="both", alpha=0.25)
        plt.tight_layout()
        plt.savefig(args.out / "lawson_screen.png", dpi=180)
        plt.close()

        # Plot the fusion-minus-bremsstrahlung margin normalized by fusion power.
        plt.figure()
        for ratio in (1.0, 0.5, 0.25):
            subset = [r for r in all_rows if r["fit"] == TENTORI_BELLONI.name and r["Te_over_Ti"] == ratio]
            xs = [float(r["Ti_keV"]) for r in subset]
            ys = [1.0 - float(r["brems_over_fusion"]) for r in subset]
            plt.plot(xs, ys, label=f"Te/Ti = {ratio:g}")
        plt.axhline(0.0, linewidth=1)
        plt.xlabel("Ion temperature Ti (keV)")
        plt.ylabel("(P_fusion - P_brems) / P_fusion")
        plt.title("Radiative margin before transport and engineering losses")
        plt.legend()
        plt.grid(True, alpha=0.25)
        plt.tight_layout()
        plt.savefig(args.out / "radiative_margin.png", dpi=180)
        plt.close()
    except ImportError:
        print("matplotlib not installed; CSV/JSON results written without plots")

    print(json.dumps(summaries, indent=2, allow_nan=True))
    print(f"Results written to: {args.out.resolve()}")


if __name__ == "__main__":
    main()
