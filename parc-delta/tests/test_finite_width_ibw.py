from dataclasses import replace

import pytest

from parc_delta_v10.linear_ibw import CollisionlessIBWModel, LAPDReferenceCase

CODATA_ALPHA_TO_PROTON_MASS_RATIO = 3.972599690252


def _physical_mass_crossing_case() -> LAPDReferenceCase:
    seed = LAPDReferenceCase(alpha_mass_ratio_proton=CODATA_ALPHA_TO_PROTON_MASS_RATIO)
    model = CollisionlessIBWModel(seed)
    crossing = model.exact_thermal_crossing()
    return replace(seed, k_perp_m_inv=crossing["k_perp_exact_thermal_crossing_m_inv"])


def test_codata_mass_convention_changes_exact_crossing_residue_sign():
    approximate = CollisionlessIBWModel().exact_thermal_crossing()
    physical = CollisionlessIBWModel(
        LAPDReferenceCase(alpha_mass_ratio_proton=CODATA_ALPHA_TO_PROTON_MASS_RATIO)
    ).exact_thermal_crossing()

    assert approximate["thermal_crossing_residue"] < 0
    assert physical["thermal_crossing_residue"] > 0
    assert physical["k_perp_exact_thermal_crossing_m_inv"] == pytest.approx(245.14319, abs=2e-4)
    assert physical["b_proton_at_crossing"] == pytest.approx(1.25475, abs=2e-5)


def test_physical_mass_exact_crossing_has_growing_collisionless_mode():
    model = CollisionlessIBWModel(_physical_mass_crossing_case())
    mode = model.solve_full_mode()
    assert mode.omega_real_over_omega_p == pytest.approx(1.510346, abs=2e-5)
    assert mode.gamma_over_omega_p == pytest.approx(1.697e-3, rel=0.01)
    assert mode.normalized_dispersion_residual < 1e-8


def test_finite_energy_spread_averages_residues_without_moving_cyclotron_poles():
    case = _physical_mass_crossing_case()
    cold = CollisionlessIBWModel(case)
    spread = CollisionlessIBWModel(case, alpha_energy_coefficient_of_variation=0.02)

    assert spread.alpha_poles == pytest.approx(cold.alpha_poles, abs=0.0)
    assert spread.alpha_residues[case.alpha_harmonic - 1] < cold.alpha_residues[case.alpha_harmonic - 1]
    assert spread.alpha_residues[case.alpha_harmonic - 1] > 0
    assert spread.plasma.alpha_ring_lambda == pytest.approx(cold.plasma.alpha_ring_lambda)


def test_two_percent_energy_cv_reduces_exact_crossing_growth_substantially():
    case = _physical_mass_crossing_case()
    cold = CollisionlessIBWModel(case).solve_full_mode()
    finite = CollisionlessIBWModel(
        case, alpha_energy_coefficient_of_variation=0.02, alpha_quadrature_order=64
    ).solve_full_mode()

    assert finite.gamma_over_omega_p < 0.30 * cold.gamma_over_omega_p
    assert finite.gamma_over_omega_p == pytest.approx(4.862e-4, rel=0.01)
    assert finite.normalized_dispersion_residual < 1e-8


def test_five_percent_energy_cv_quadrature_is_converged():
    case = _physical_mass_crossing_case()
    low_order = CollisionlessIBWModel(
        case, alpha_energy_coefficient_of_variation=0.05, alpha_quadrature_order=32
    )
    high_order = CollisionlessIBWModel(
        case, alpha_energy_coefficient_of_variation=0.05, alpha_quadrature_order=128
    )
    assert low_order.alpha_residues[2] == pytest.approx(high_order.alpha_residues[2], rel=2e-7)


def test_alpha_pole_broadening_reduces_but_does_not_masquerade_as_heat():
    model = CollisionlessIBWModel()
    collisionless = model.solve_broadened_mode(alpha_broadening_over_omega_p=0.0)
    broadened = model.solve_broadened_mode(alpha_broadening_over_omega_p=1e-3)

    assert collisionless.gamma_over_omega_p > broadened.gamma_over_omega_p > 0
    assert broadened.normalized_dispersion_residual < 1e-8
    assert broadened.is_growing is True


def test_broadened_dispersion_reduces_to_collisionless_dispersion_at_zero_rate():
    model = CollisionlessIBWModel()
    omega = complex(1.498, 0.001)
    assert model.broadened_dispersion_omega(
        omega, alpha_broadening_over_omega_p=0.0
    ) == pytest.approx(model.full_dispersion(omega * omega), abs=1e-13)


def test_invalid_distribution_and_broadening_inputs_rejected():
    with pytest.raises(ValueError):
        CollisionlessIBWModel(alpha_energy_coefficient_of_variation=-0.1)
    with pytest.raises(ValueError):
        CollisionlessIBWModel(alpha_quadrature_order=4)
    with pytest.raises(ValueError):
        CollisionlessIBWModel().solve_broadened_mode(alpha_broadening_over_omega_p=-1e-3)


def test_physical_mass_at_the_published_fixed_wavenumber_is_detuned():
    model = CollisionlessIBWModel(
        LAPDReferenceCase(alpha_mass_ratio_proton=CODATA_ALPHA_TO_PROTON_MASS_RATIO)
    )
    analysis = model.pole_analysis()
    assert analysis["locally_unstable"] is False
    assert analysis["critical_alpha_density_fraction_of_reference"] == pytest.approx(78.97, rel=2e-3)


def test_twenty_percent_energy_cv_requires_and_converges_at_high_order():
    case = _physical_mass_crossing_case()
    with pytest.raises(ValueError):
        CollisionlessIBWModel(
            case, alpha_energy_coefficient_of_variation=0.20, alpha_quadrature_order=256
        )
    order_512 = CollisionlessIBWModel(
        case, alpha_energy_coefficient_of_variation=0.20, alpha_quadrature_order=512
    )
    order_768 = CollisionlessIBWModel(
        case, alpha_energy_coefficient_of_variation=0.20, alpha_quadrature_order=768
    )
    assert order_512.alpha_residues[2] == pytest.approx(order_768.alpha_residues[2], rel=2e-6)


def test_broadened_mode_accepts_explicit_seed_and_rejects_nonfinite_seed():
    model = CollisionlessIBWModel()
    cold = model.solve_full_mode()
    seeded = model.solve_broadened_mode(
        alpha_broadening_over_omega_p=0.0,
        initial_omega=complex(cold.omega_real_over_omega_p, cold.gamma_over_omega_p),
    )
    assert seeded.omega_real_over_omega_p == pytest.approx(cold.omega_real_over_omega_p, abs=1e-10)
    assert seeded.gamma_over_omega_p == pytest.approx(cold.gamma_over_omega_p, abs=1e-10)
    with pytest.raises(ValueError):
        model.solve_broadened_mode(
            alpha_broadening_over_omega_p=1e-3,
            initial_omega=complex(float("nan"), 0.0),
        )
