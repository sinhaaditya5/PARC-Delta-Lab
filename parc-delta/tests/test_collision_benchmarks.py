import math

import numpy as np
import pytest
from scipy.constants import e, m_p, physical_constants

from parc_delta_v10.collision_benchmarks import (
    landau_pairwise_energy_exchange,
    landau_spitzer_power_density_w_m3,
    landau_spitzer_temperature_rate_ev_s,
    temperature_ev_from_velocities,
)
from parc_delta_v10.coulomb_mc import maxwellian_velocity_samples

M_ALPHA = physical_constants["alpha particle mass"][0]


def centered_maxwellian(count, mass, temperature_ev, seed):
    velocities = maxwellian_velocity_samples(
        count, mass_kg=mass, temperature_ev=temperature_ev, seed=seed
    )
    return velocities - np.mean(velocities, axis=0)


def proton_alpha_case(count=1024):
    n = 1.0e20
    vp = centered_maxwellian(count, m_p, 100.0, 10)
    va = centered_maxwellian(count, M_ALPHA, 10.0, 11)
    return n, vp, va


def test_landau_spitzer_rate_has_correct_sign_and_zero_at_equipartition():
    args = dict(
        mass_a_kg=m_p,
        mass_b_kg=M_ALPHA,
        charge_a_c=e,
        charge_b_c=2 * e,
        density_b_m3=1.0e20,
        coulomb_logarithm=11.5,
    )
    hot_rate = landau_spitzer_temperature_rate_ev_s(
        **args, temperature_a_ev=100.0, temperature_b_ev=10.0
    )
    cold_rate = landau_spitzer_temperature_rate_ev_s(
        **args, temperature_a_ev=10.0, temperature_b_ev=100.0
    )
    equal_rate = landau_spitzer_temperature_rate_ev_s(
        **args, temperature_a_ev=50.0, temperature_b_ev=50.0
    )
    assert hot_rate < 0
    assert cold_rate > 0
    assert equal_rate == pytest.approx(0.0, abs=1e-20)


def test_pairwise_landau_moment_closes_energy_and_matches_maxwellian_rate():
    density, vp, va = proton_alpha_case(1024)
    result = landau_pairwise_energy_exchange(
        species_a="proton",
        species_b="alpha",
        mass_a_kg=m_p,
        mass_b_kg=M_ALPHA,
        charge_a_c=e,
        charge_b_c=2 * e,
        density_a_m3=density,
        density_b_m3=density,
        velocities_a_m_s=vp,
        velocities_b_m_s=va,
        coulomb_logarithm=11.5,
        chunk_rows=64,
    )
    ls_rate = landau_spitzer_temperature_rate_ev_s(
        mass_a_kg=m_p,
        mass_b_kg=M_ALPHA,
        charge_a_c=e,
        charge_b_c=2 * e,
        density_b_m3=density,
        temperature_a_ev=temperature_ev_from_velocities(vp, m_p),
        temperature_b_ev=temperature_ev_from_velocities(va, M_ALPHA),
        coulomb_logarithm=11.5,
    )
    ls_power = landau_spitzer_power_density_w_m3(
        density_a_m3=density,
        temperature_rate_a_ev_s=ls_rate,
    )
    assert result.pair_count == 1024**2
    assert result.q_a_w_m3 < 0
    assert result.q_b_w_m3 > 0
    assert abs(result.conservation_residual_w_m3) < 1e-12 * abs(result.q_a_w_m3)
    assert result.q_a_w_m3 == pytest.approx(ls_power, rel=0.02)


def test_pairwise_landau_moment_is_chunk_size_invariant():
    density, vp, va = proton_alpha_case(256)
    kwargs = dict(
        species_a="proton", species_b="alpha",
        mass_a_kg=m_p, mass_b_kg=M_ALPHA,
        charge_a_c=e, charge_b_c=2 * e,
        density_a_m3=density, density_b_m3=density,
        velocities_a_m_s=vp, velocities_b_m_s=va,
        coulomb_logarithm=11.5,
    )
    a = landau_pairwise_energy_exchange(**kwargs, chunk_rows=16)
    b = landau_pairwise_energy_exchange(**kwargs, chunk_rows=128)
    assert a.q_a_w_m3 == pytest.approx(b.q_a_w_m3, rel=2e-13)
    assert a.q_b_w_m3 == pytest.approx(b.q_b_w_m3, rel=2e-13)


def test_pairwise_landau_moment_validates_coulomb_log_and_inputs():
    density, vp, va = proton_alpha_case(32)
    kwargs = dict(
        species_a="proton", species_b="alpha",
        mass_a_kg=m_p, mass_b_kg=M_ALPHA,
        charge_a_c=e, charge_b_c=2 * e,
        density_a_m3=density, density_b_m3=density,
        velocities_a_m_s=vp, velocities_b_m_s=va,
    )
    with pytest.raises(ValueError):
        landau_pairwise_energy_exchange(**kwargs, coulomb_logarithm=0.0)
    with pytest.raises(ValueError):
        landau_pairwise_energy_exchange(**kwargs, coulomb_logarithm=10.0, chunk_rows=0)


def test_reaction_born_alpha_source_couples_to_background_moment_without_branch_weighting():
    from parc_delta_v10.pb11_alpha_source import sample_pb11_alpha_birth

    source = sample_pb11_alpha_birth(
        128, channel="alpha1", e_cm_mev=0.6183888798, seed=99, frame="cm"
    )
    alpha_velocity = source.velocity_m_s - np.mean(source.velocity_m_s, axis=0)
    proton_velocity = centered_maxwellian(256, m_p, 1.0e4, 100)
    result = landau_pairwise_energy_exchange(
        species_a="born_alpha", species_b="proton",
        mass_a_kg=M_ALPHA, mass_b_kg=m_p,
        charge_a_c=2 * e, charge_b_c=e,
        density_a_m3=2.0e18, density_b_m3=1.0e20,
        velocities_a_m_s=alpha_velocity,
        velocities_b_m_s=proton_velocity,
        coulomb_logarithm=15.0,
    )
    assert result.q_a_w_m3 < 0
    assert result.q_b_w_m3 > 0
    assert abs(result.conservation_residual_w_m3) / abs(result.q_a_w_m3) < 1e-10
