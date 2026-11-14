from parc_delta_v10.cli import evaluate


def test_cli_evaluate_payload_is_auditable():
    payload = {
        "metadata": {"run_id": "test-run"},
        "external_flows": [
            {"reservoir": "alpha_fast", "power_w": 2.0, "direction": "in", "label": "fusion_alpha_birth_power", "source_ref": "synthetic://source"}
        ],
        "modes": [
            {
                "name": "ibw1",
                "energy_j": 1.0,
                "source_ref": "synthetic://mode",
                "species_growth_rates": {
                    "alpha_fast": {"gamma_s_inv": 0.1, "source_ref": "synthetic://ga", "method": "synthetic"},
                    "protons": {"gamma_s_inv": -0.05, "source_ref": "synthetic://gp", "method": "synthetic"}
                }
            }
        ],
        "irreversible_proton_heating_w": None
    }
    result = evaluate(payload)
    assert result["ledger"]["relative_closure_error"] < 1e-12
    assert result["routing_metrics"]["wave_to_protons_w"] == 0.1
    assert result["routing_metrics"]["irreversible_proton_heating_w"] is None
