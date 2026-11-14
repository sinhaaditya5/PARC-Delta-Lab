import math

import numpy as np
import pytest
from scipy.constants import e, m_e, m_p, physical_constants

from parc_delta_v10.collision_benchmarks import (
    landau_spitzer_temperature_rate_ev_s,
    temperature_ev_from_velocities,
)
from parc_delta_v10.coulomb_mc import maxwellian_velocity_samples
from parc_delta_v10.slowing_down import (
    MaxwellianFieldSpecies,
    RosenbluthSlowingDownSolver,
    chandrasekhar_g,
    expected_kinetic_energy_rate_per_marker_j_s,
    rosenbluth_test_particle_coefficients,
)

M_ALPHA = physical_constants["alpha particle mass"][0]


def test_chandrasekhar_g_limits_and_validation():
    values = chandrasekhar_g(np.array([0.0, 1.0e-8, 1.0e-4, 0.1, 1.0, 10.0]))
    assert values[0] == 0.0
    assert values[1] == pytest.approx(2.0e-8 / (3.0 * math.sqrt(math.pi)), rel=1e-7)
    assert np.all(values >= 0.0)
    assert values[-1] == pytest.approx(0.005, rel=0.01)
    with pytest.raises(ValueError):
        chandrasekhar_g(np.array([-1.0]))


def test_rosenbluth_coefficients_are_finite_at_zero_and_positive():
    field = MaxwellianFieldSpecies("proton", M_ALPHA, 2 * e, 1e20, 1e4)
    coeff = rosenbluth_test_particle_coefficients(
        np.array([0.0, 1e3, 1e6]),
        test_mass_kg=m_p,
        test_charge_c=e,
        field_species=field,
        coulomb_logarithm=15.0,
    )
    assert np.all(np.isfinite(coeff.k_s_inv))
    assert np.all(np.isfinite(coeff.d_parallel_kg2_m2_s))
    assert np.all(np.isfinite(coeff.d_perp_kg2_m2_s))
    assert np.all(coeff.k_s_inv > 0)
    assert np.all(coeff.d_parallel_kg2_m2_s > 0)
    assert np.all(coeff.d_perp_kg2_m2_s > 0)


def test_rosenbluth_energy_moment_matches_landau_spitzer_for_maxwellians():
    n = 1.0e20
    test_v = maxwellian_velocity_samples(
        100_000, mass_kg=m_p, temperature_ev=100.0, seed=1001
    )
    field = MaxwellianFieldSpecies("alpha", M_ALPHA, 2 * e, n, 10.0)
    coeff = rosenbluth_test_particle_coefficients(
        np.linalg.norm(test_v, axis=1),
        test_mass_kg=m_p,
        test_charge_c=e,
        field_species=field,
        coulomb_logarithm=11.5,
    )
    q_fp = n * np.mean(expected_kinetic_energy_rate_per_marker_j_s(
        np.linalg.norm(test_v, axis=1), test_mass_kg=m_p, coefficients=coeff
    ))
    temp_test = temperature_ev_from_velocities(test_v, m_p)
    rate_ls = landau_spitzer_temperature_rate_ev_s(
        mass_a_kg=m_p,
        mass_b_kg=M_ALPHA,
        charge_a_c=e,
        charge_b_c=2 * e,
        density_b_m3=n,
        temperature_a_ev=temp_test,
        temperature_b_ev=10.0,
        coulomb_logarithm=11.5,
    )
    q_ls = 1.5 * n * e * rate_ls
    assert q_fp < 0.0
    assert q_fp == pytest.approx(q_ls, rel=0.005)


def test_hot_test_particles_deposit_positive_expected_energy_to_cold_bath():
    field = MaxwellianFieldSpecies("proton", m_p, e, 1e20, 1.0)
    solver = RosenbluthSlowingDownSolver(
        test_mass_kg=M_ALPHA,
        test_charge_c=2 * e,
        field_species=[field],
        coulomb_logarithm=15.0,
    )
    velocities = np.tile(np.array([1.5e7, 0.0, 0.0]), (64, 1))
    # The explicit expected moment is independent of the random draw.
    speed = np.linalg.norm(velocities, axis=1)
    coeff = rosenbluth_test_particle_coefficients(
        speed, test_mass_kg=M_ALPHA, test_charge_c=2 * e,
        field_species=field, coulomb_logarithm=15.0,
    )
    rate = expected_kinetic_energy_rate_per_marker_j_s(
        speed, test_mass_kg=M_ALPHA, coefficients=coeff
    )
    assert np.mean(rate) < 0.0


def test_solver_advances_energy_and_closes_expected_energy_budget():
    field = MaxwellianFieldSpecies("proton", m_p, e, 1e20, 1.0)
    solver = RosenbluthSlowingDownSolver(
        test_mass_kg=M_ALPHA,
        test_charge_c=2 * e,
        field_species=[field],
        coulomb_logarithm=15.0,
    )
    v0 = np.tile(np.array([1.5e7, 1.0e5, 0.0]), (1024, 1))
    result = solver.run(
        v0, dt_s=1e-4, steps=100, alpha_density_m3=2e18,
        seed=8, record_every=20,
    )
    assert result.final_energy_density_j_m3 < result.initial_energy_density_j_m3
    assert result.deposited_energy_j_m3["proton"] > 0.0
    assert result.relative_energy_budget_residual < 0.03
    assert len(result.snapshots) == 6
    assert result.marker_count == 1024


def test_solver_rejects_timestep_that_violates_explicit_stability_gate():
    field = MaxwellianFieldSpecies("proton", m_p, e, 1e20, 1.0)
    solver = RosenbluthSlowingDownSolver(
        test_mass_kg=M_ALPHA,
        test_charge_c=2 * e,
        field_species=[field],
        coulomb_logarithm=15.0,
        max_dt_k=1e-4,
    )
    v = np.tile(np.array([1.5e7, 0.0, 0.0]), (8, 1))
    with pytest.raises(ValueError, match="max_dt_k"):
        solver.step(v, 1.0, rng=np.random.default_rng(1))


def test_solver_enforces_nonrelativistic_speed_boundary():
    field = MaxwellianFieldSpecies("proton", m_p, e, 1e20, 1.0)
    solver = RosenbluthSlowingDownSolver(
        test_mass_kg=M_ALPHA,
        test_charge_c=2 * e,
        field_species=[field],
        coulomb_logarithm=15.0,
    )
    with pytest.raises(ValueError, match="speed limit"):
        solver.step(np.array([[0.2 * 299_792_458.0, 0.0, 0.0]]), 1e-6, rng=np.random.default_rng(1))
