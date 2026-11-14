import pytest

from parc_delta_v10.ledger import EnergyLedger, ExternalFlow, PowerTransfer
from parc_delta_v10.diagnostics import compare_scenarios, ledger_summary, routing_metrics


def test_coherent_proton_response_is_not_inferred_as_irreversible_heat():
    ledger = EnergyLedger(
        transfers=[
            PowerTransfer("alpha_fast", "wave:ibw", 8.0, "wave_drive", "synthetic://a"),
            PowerTransfer("wave:ibw", "protons", 6.0, "wave_absorption", "synthetic://p"),
            PowerTransfer("wave:ibw", "electrons", 1.0, "wave_absorption", "synthetic://e"),
        ],
        external_flows=[ExternalFlow("alpha_fast", 10.0, "in", "fusion_alpha_birth_power", "synthetic://source")],
    )
    result = routing_metrics(ledger)
    assert result.alpha_to_wave_w == pytest.approx(8.0)
    assert result.wave_to_protons_w == pytest.approx(6.0)
    assert result.proton_share_of_wave_absorption == pytest.approx(6.0 / 7.0)
    assert result.irreversible_proton_heating_w is None
    assert result.irreversible_proton_heating_fraction_of_alpha_birth is None


def test_irreversible_heat_requires_separate_kinetic_input():
    ledger = EnergyLedger(
        external_flows=[ExternalFlow("alpha_fast", 20.0, "in", "fusion_alpha_birth_power", "synthetic://source")]
    )
    result = routing_metrics(ledger, irreversible_proton_heating_w=5.0)
    assert result.irreversible_proton_heating_fraction_of_alpha_birth == pytest.approx(0.25)


def test_summary_checks_global_energy_closure():
    ledger = EnergyLedger(external_flows=[
        ExternalFlow("plasma", 10.0, "in", "heating", "synthetic://input"),
        ExternalFlow("plasma", 2.0, "out", "loss", "synthetic://loss"),
    ])
    summary = ledger_summary(ledger)
    assert summary["external_input_w"] == pytest.approx(10.0)
    assert summary["external_output_w"] == pytest.approx(2.0)
    assert summary["relative_closure_error"] == pytest.approx(0.0)


def test_scenario_comparison_requires_matched_external_inputs():
    baseline = EnergyLedger(external_flows=[ExternalFlow("plasma", 10.0, "in", "heater", "synthetic://input")])
    candidate = EnergyLedger(external_flows=[ExternalFlow("plasma", 10.0, "in", "heater", "synthetic://input")])
    result = compare_scenarios("B0", baseline, "B2", candidate)
    assert result["boundary_inputs_matched"] is True
    assert result["delta_external_output_w"] == 0.0
    bad = EnergyLedger(external_flows=[ExternalFlow("plasma", 11.0, "in", "heater", "synthetic://input")])
    with pytest.raises(ValueError):
        compare_scenarios("B0", baseline, "bad", bad)


def test_invalid_irreversible_proton_heating_is_rejected():
    with pytest.raises(ValueError):
        routing_metrics(EnergyLedger(), irreversible_proton_heating_w=-1.0)
