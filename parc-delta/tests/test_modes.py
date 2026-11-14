import pytest

from parc_delta_v10.ledger import ExternalFlow
from parc_delta_v10.modes import GrowthRate, WaveModeSnapshot, assemble_ledger, mode_to_ledger_terms


def rate(gamma, species):
    return GrowthRate(gamma, 0.0, f"synthetic://{species}", "synthetic unit test")


def test_positive_species_gamma_means_species_drives_wave():
    mode = WaveModeSnapshot(
        name="m1",
        energy_j=2.0,
        sigma_energy_j=0.0,
        species_growth_rates={"alpha_fast": rate(0.25, "alpha")},
        escape_damping_s_inv=0.0,
        sigma_escape_s_inv=0.0,
        source_ref="synthetic://mode",
    )
    transfers, _ = mode_to_ledger_terms(mode)
    assert transfers[0].source == "alpha_fast"
    assert transfers[0].destination == "wave:m1"
    assert transfers[0].power_w == pytest.approx(1.0)
    ledger = assemble_ledger([mode], external_flows=[
        ExternalFlow("alpha_fast", 1.0, "in", "fusion_alpha_birth_power", "synthetic://source")
    ])
    assert ledger.net_power_w["alpha_fast"] == pytest.approx(0.0)
    assert ledger.net_power_w["wave:m1"] == pytest.approx(1.0)
    ledger.assert_closed()


def test_negative_species_gamma_means_species_absorbs_wave():
    mode = WaveModeSnapshot(
        name="m2",
        energy_j=5.0,
        sigma_energy_j=0.0,
        species_growth_rates={"protons": rate(-0.1, "p")},
        escape_damping_s_inv=0.0,
        sigma_escape_s_inv=0.0,
        source_ref="synthetic://mode",
    )
    transfers, _ = mode_to_ledger_terms(mode)
    assert transfers[0].source == "wave:m2"
    assert transfers[0].destination == "protons"
    assert transfers[0].power_w == pytest.approx(1.0)


def test_mode_wave_energy_rate_matches_species_and_escape_balance():
    mode = WaveModeSnapshot(
        name="m3",
        energy_j=4.0,
        sigma_energy_j=0.0,
        species_growth_rates={
            "alpha_fast": rate(0.10, "alpha"),
            "protons": rate(-0.07, "protons"),
            "electrons": rate(-0.01, "electrons"),
        },
        escape_damping_s_inv=0.01,
        sigma_escape_s_inv=0.0,
        rf_drive_w=0.2,
        source_ref="synthetic://mode",
    )
    ledger = assemble_ledger([mode], external_flows=[
        ExternalFlow("alpha_fast", 1.0, "in", "fusion_alpha_birth_power", "synthetic://source")
    ])
    assert ledger.net_power_w["wave:m3"] == pytest.approx(mode.net_wave_power_w)
    ledger.assert_closed()


def test_rejects_missing_provenance_and_negative_energy():
    with pytest.raises(ValueError):
        GrowthRate(0.1, 0.0, "", "method")
    with pytest.raises(ValueError):
        WaveModeSnapshot("bad", -1.0, 0.0, {"alpha_fast": rate(0.1, "a")}, 0.0, 0.0, source_ref="synthetic://x")


def test_nonlinear_wave_transfer_is_internal_and_conservative():
    from parc_delta_v10.ledger import PowerTransfer
    mode_a = WaveModeSnapshot("a", 1.0, 0.0, {"alpha_fast": rate(0.0, "alpha")}, 0.0, 0.0, source_ref="synthetic://a")
    mode_b = WaveModeSnapshot("b", 1.0, 0.0, {"protons": rate(0.0, "p")}, 0.0, 0.0, source_ref="synthetic://b")
    coupling = PowerTransfer("wave:a", "wave:b", 0.25, "nonlinear_wave_coupling", "synthetic://coupler")
    ledger = assemble_ledger([mode_a, mode_b], nonlinear_wave_transfers=[coupling])
    assert ledger.net_power_w["wave:a"] == pytest.approx(-0.25)
    assert ledger.net_power_w["wave:b"] == pytest.approx(0.25)
    ledger.assert_closed()
