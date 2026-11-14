from dataclasses import replace

import numpy as np
import pytest

from parc_delta_v10.finite_k_ibw import (
    FiniteKParallelIBWModel,
    make_reference_case,
    plasma_dispersion_zeta,
    plasma_dispersion_zeta_derivative,
)
from parc_delta_v10.linear_ibw import CollisionlessIBWModel


def test_cold_perpendicular_limit_reproduces_v12_dispersion():
    finite_case = make_reference_case()
    old_model = CollisionlessIBWModel(finite_case.plasma)
    old_mode = old_model.solve_full_mode()
    omega = complex(old_mode.omega_real_over_omega_p, old_mode.gamma_over_omega_p)

    finite_model = FiniteKParallelIBWModel(finite_case)
    assert abs(finite_model.dispersion(omega)) < 1e-8
    assert finite_model.solve_mode(omega).gamma_over_omega_p == pytest.approx(
        old_mode.gamma_over_omega_p, rel=1e-8, abs=1e-11
    )


def test_parallel_alpha_temperature_has_no_effect_at_kparallel_zero():
    cold_parallel = FiniteKParallelIBWModel(make_reference_case(
        k_parallel_over_perp=0.0, alpha_parallel_temperature_ev=0.0
    ))
    warm_parallel = FiniteKParallelIBWModel(make_reference_case(
        k_parallel_over_perp=0.0, alpha_parallel_temperature_ev=100.0
    ))
    omega = 1.5103 + 1.0e-3j
    assert cold_parallel.dispersion(omega) == pytest.approx(
        warm_parallel.dispersion(omega), rel=1e-12, abs=1e-12
    )


def test_plasma_dispersion_function_derivative_identity():
    z = 0.7 + 0.3j
    numeric = (
        plasma_dispersion_zeta(z + 1e-6) - plasma_dispersion_zeta(z - 1e-6)
    ) / 2e-6
    assert plasma_dispersion_zeta_derivative(z) == pytest.approx(numeric, rel=1e-8)


def test_large_argument_derivative_asymptotic_is_finite_and_positive_real():
    value = plasma_dispersion_zeta_derivative(1000.0 + 0.01j)
    assert np.isfinite(value.real)
    assert np.isfinite(value.imag)
    assert value.real > 0


def test_finite_kparallel_root_has_small_residual_and_parallel_spread_is_active():
    cold = make_reference_case(
        k_parallel_over_perp=1e-3,
        alpha_parallel_temperature_ev=0.0,
    )
    warm = make_reference_case(
        k_parallel_over_perp=1e-3,
        alpha_parallel_temperature_ev=100.0,
    )
    old = CollisionlessIBWModel(cold.plasma).solve_full_mode()
    seed = complex(old.omega_real_over_omega_p, old.gamma_over_omega_p)

    cold_model = FiniteKParallelIBWModel(cold)
    warm_model = FiniteKParallelIBWModel(warm)
    cold_mode = cold_model.solve_mode(seed)
    warm_mode = warm_model.solve_mode(seed)

    assert cold_mode.normalized_residual < 1e-7
    assert warm_mode.normalized_residual < 1e-7
    assert warm_mode.gamma_over_omega_p != pytest.approx(
        cold_mode.gamma_over_omega_p, rel=1e-3
    )


def test_perpendicular_energy_width_reduces_to_v12_distribution_at_kparallel_zero():
    finite_case = make_reference_case(
        k_parallel_over_perp=0.0,
        alpha_perp_energy_cv=0.02,
        energy_quadrature_order=64,
    )
    old_model = CollisionlessIBWModel(
        finite_case.plasma,
        alpha_energy_coefficient_of_variation=0.02,
        alpha_quadrature_order=64,
    )
    old_mode = old_model.solve_full_mode()
    omega = complex(old_mode.omega_real_over_omega_p, old_mode.gamma_over_omega_p)
    finite_model = FiniteKParallelIBWModel(finite_case)
    assert abs(finite_model.dispersion(omega)) < 1e-7


def test_parallel_landau_response_can_remove_growth_on_tracked_branch():
    case = make_reference_case(
        k_parallel_over_perp=5e-3,
        alpha_parallel_temperature_ev=0.0,
    )
    perpendicular = CollisionlessIBWModel(case.plasma).solve_full_mode()
    seed = complex(perpendicular.omega_real_over_omega_p, perpendicular.gamma_over_omega_p)
    mode = FiniteKParallelIBWModel(case).solve_mode(seed)
    assert mode.gamma_over_omega_p < 0.0
    assert mode.normalized_residual < 1e-7


def test_finite_parallel_case_rejects_invalid_inputs():
    with pytest.raises(ValueError):
        make_reference_case(k_parallel_over_perp=-1e-3)
    with pytest.raises(ValueError):
        make_reference_case(alpha_parallel_temperature_ev=-1.0)
    with pytest.raises(ValueError):
        make_reference_case(alpha_perp_energy_cv=0.25)
