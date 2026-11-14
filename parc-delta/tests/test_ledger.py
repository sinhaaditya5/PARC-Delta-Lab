import math
import pytest

from parc_delta_v10.ledger import EnergyLedger, ExternalFlow, PowerTransfer, combine_ledgers


def test_internal_transfer_cancels_globally():
    ledger = EnergyLedger(
        transfers=[PowerTransfer("alpha_fast", "protons", 12.5, "collision", "synthetic://test")],
        external_flows=[ExternalFlow("alpha_fast", 20.0, "in", "source", "synthetic://test")],
    )
    assert ledger.net_power_w["alpha_fast"] == pytest.approx(7.5)
    assert ledger.net_power_w["protons"] == pytest.approx(12.5)
    assert ledger.closure_residual_w == pytest.approx(0.0, abs=1e-12)
    ledger.assert_closed()


def test_external_loss_is_counted_at_boundary():
    ledger = EnergyLedger(external_flows=[
        ExternalFlow("electrons", 10.0, "in", "heating", "synthetic://test"),
        ExternalFlow("electrons", 3.0, "out", "brems", "synthetic://test"),
    ])
    assert ledger.net_power_w["electrons"] == pytest.approx(7.0)
    assert ledger.external_input_w == pytest.approx(10.0)
    assert ledger.external_output_w == pytest.approx(3.0)
    assert ledger.relative_closure_error == pytest.approx(0.0)


def test_rejects_invalid_transfers_and_flows():
    with pytest.raises(ValueError):
        PowerTransfer("alpha", "alpha", 1.0, "bad", "synthetic://test")
    with pytest.raises(ValueError):
        PowerTransfer("alpha", "p", -1.0, "bad", "synthetic://test")
    with pytest.raises(ValueError):
        ExternalFlow("p", 1.0, "sideways", "bad", "synthetic://test")


def test_combine_ledgers_preserves_all_items():
    a = EnergyLedger(external_flows=[ExternalFlow("a", 1.0, "in", "source", "synthetic://a")])
    b = EnergyLedger(transfers=[PowerTransfer("a", "b", 0.5, "exchange", "synthetic://b")])
    joined = combine_ledgers([a, b])
    assert len(joined.external_flows) == 1
    assert len(joined.transfers) == 1
    assert joined.net_power_w["a"] == pytest.approx(0.5)
    assert joined.net_power_w["b"] == pytest.approx(0.5)
