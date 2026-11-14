import math

import pytest

from parc_delta_v10.linear_ibw import (
    CollisionlessIBWModel,
    LAPDReferenceCase,
    derive_plasma,
)


def test_reference_case_quasineutrality_and_harmonic_ratio():
    case = LAPDReferenceCase()
    plasma = derive_plasma(case)
    assert plasma.electron_density_m3 == pytest.approx(
        case.proton_density_m3 + 2 * plasma.alpha_density_m3
    )
    assert plasma.alpha_cyclotron_s_inv / plasma.proton_cyclotron_s_inv == pytest.approx(0.5)
    assert plasma.alpha_pole_frequency_over_omega_p == pytest.approx(1.5)
    assert plasma.b_proton == pytest.approx(1.3232, rel=3e-4)


def test_reference_mode_reproduces_published_lapd_growth_rate():
    model = CollisionlessIBWModel()
    result = model.solve_full_mode()
    assert result.omega_real_over_omega_p == pytest.approx(1.50, abs=0.003)
    assert result.gamma_over_omega_p == pytest.approx(1.33e-3, rel=0.03)
    assert result.normalized_dispersion_residual < 1e-5
    assert result.selected_residue_normalized > 0


def test_root_pole_density_threshold_near_published_value():
    analysis = CollisionlessIBWModel().pole_analysis()
    critical = analysis["critical_alpha_density_fraction_of_reference"]
    assert critical is not None
    assert critical == pytest.approx(0.62, abs=0.04)
    assert analysis["locally_unstable"] is True


def test_linear_power_partition_is_conservative_and_proton_directed():
    result = CollisionlessIBWModel().power_partition()
    assert result.closure_sum == pytest.approx(1.0, abs=1e-12)
    assert result.proton_fraction_of_alpha_loss == pytest.approx(0.9996, abs=2e-4)
    assert result.electron_fraction_of_alpha_loss < 0.001
    assert result.proton_fraction_of_alpha_loss > result.electron_fraction_of_alpha_loss


def test_exact_thermal_root_crossing_also_checks_residue_sign():
    result = CollisionlessIBWModel().exact_thermal_crossing()
    assert result["thermal_root_matches_alpha_pole"] is True
    # In this independent reproduction, the residue at the exact crossing is
    # negative. Root coincidence without a positive residue is not unstable.
    assert result["destabilizing_residue_at_crossing"] is False
    assert result["thermal_crossing_residue"] < 0


def test_invalid_reference_parameters_rejected():
    with pytest.raises(ValueError):
        LAPDReferenceCase(proton_density_m3=0)
    with pytest.raises(ValueError):
        LAPDReferenceCase(alpha_harmonic=0)


def test_no_growth_claim_for_a_negative_residue():
    model = CollisionlessIBWModel()
    crossing = model.exact_thermal_crossing()
    assert crossing["thermal_crossing_residue"] < 0
    # Negative residue makes the quadratic discriminant positive at exact
    # resonance, hence no complex pair from this selected root-pole crossing.
    disc = -4 * crossing["thermal_crossing_residue"]
    assert disc > 0


def test_wavenumber_scan_identifies_finite_unstable_band():
    rows = CollisionlessIBWModel().scan_wavenumber_band(k_min=248.0, k_max=255.0, points=141)
    unstable = [row for row in rows if row["unstable_at_reference_alpha_density"]]
    assert len(rows) == 141
    assert len(unstable) > 10
    assert min(row["k_perp_m_inv"] for row in unstable) == pytest.approx(250.9, abs=0.06)
    assert max(row["k_perp_m_inv"] for row in unstable) == pytest.approx(252.5, abs=0.06)
    assert max(row["local_gamma_over_omega_p"] for row in unstable) == pytest.approx(1.33e-3, rel=0.03)
