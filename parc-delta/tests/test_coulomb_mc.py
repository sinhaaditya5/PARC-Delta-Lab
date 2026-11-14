import numpy as np
import pytest
from scipy.constants import e, m_e, m_p, physical_constants

from parc_delta_v10.coulomb_mc import (
    CollisionSpecies,
    MultiSpeciesCoulombMonteCarlo,
    maxwellian_velocity_samples,
)

M_ALPHA = physical_constants["alpha particle mass"][0]


def make_neutral_three_species(seed_offset=0):
    n_p = 1.0e17
    n_alpha = 0.5e17
    n_e = n_p + 2.0 * n_alpha
    count_p, count_alpha, count_e = 12, 6, 24
    return [
        CollisionSpecies(
            "electron", m_e, -e, n_e, 1.0e4,
            maxwellian_velocity_samples(count_e, mass_kg=m_e, temperature_ev=1.0e4, seed=10 + seed_offset),
        ),
        CollisionSpecies(
            "proton", m_p, e, n_p, 1.0e4,
            maxwellian_velocity_samples(count_p, mass_kg=m_p, temperature_ev=1.0e4, seed=20 + seed_offset),
        ),
        CollisionSpecies(
            "alpha", M_ALPHA, 2 * e, n_alpha, 1.0e4,
            maxwellian_velocity_samples(count_alpha, mass_kg=M_ALPHA, temperature_ev=1.0e4, seed=30 + seed_offset),
        ),
    ]


def test_multispecies_collision_step_conserves_momentum_energy_and_counts():
    op = MultiSpeciesCoulombMonteCarlo(make_neutral_three_species())
    before = {s.name: s.velocity_m_s.copy() for s in op.species}
    diag = op.step(1.0e-8, seed=55)
    assert diag.pair_count > 0
    assert diag.skipped_strong_coupling_pairs == 0
    assert diag.relative_momentum_error < 5e-13
    assert diag.relative_energy_error < 5e-13
    assert diag.particle_counts_before == diag.particle_counts_after
    assert all(not np.array_equal(before[s.name], s.velocity_m_s) for s in op.species)
    assert diag.debye_length_m > 0
    assert diag.coulomb_log_min > 0


def test_pair_operator_requires_equal_macro_particle_weights():
    species = make_neutral_three_species()
    bad = list(species)
    bad[0] = CollisionSpecies(
        "electron", m_e, -e, 1.1 * species[0].density_m3, 1.0e4,
        species[0].velocity_m_s,
    )
    with pytest.raises(ValueError, match="equal macro-particle"):
        MultiSpeciesCoulombMonteCarlo(bad)


def test_rejected_large_kick_leaves_state_unchanged():
    op = MultiSpeciesCoulombMonteCarlo(make_neutral_three_species(), max_deflection_rad=0.01)
    before = [s.velocity_m_s.copy() for s in op.species]
    with pytest.raises(ValueError, match="reduce dt_s"):
        op.step(1.0e-2, seed=8)
    for old, current in zip(before, op.species):
        assert np.array_equal(old, current.velocity_m_s)


def test_operator_rejects_invalid_time_step():
    op = MultiSpeciesCoulombMonteCarlo(make_neutral_three_species())
    with pytest.raises(ValueError):
        op.step(0.0)
    with pytest.raises(ValueError):
        op.step(-1e-10)


def test_single_species_self_collisions_preserve_invariants():
    velocities = maxwellian_velocity_samples(
        32, mass_kg=m_p, temperature_ev=1000, seed=19,
    )
    velocities[:, 2] *= 0.3
    species = [CollisionSpecies("proton", m_p, e, 1.0e17, 1000, velocities)]
    op = MultiSpeciesCoulombMonteCarlo(species)
    diag = op.step(1e-8, seed=91)
    assert diag.pair_count == 32 * 31 // 2
    assert diag.relative_momentum_error < 5e-13
    assert diag.relative_energy_error < 5e-13


def test_fixed_coulomb_logarithm_is_available_for_controlled_benchmarks():
    op = MultiSpeciesCoulombMonteCarlo(
        make_neutral_three_species(), coulomb_logarithm=12.5
    )
    diag = op.step(1.0e-10, seed=93)
    assert diag.coulomb_log_min == pytest.approx(12.5)
    assert diag.coulomb_log_max == pytest.approx(12.5)


def test_fixed_logarithm_overrides_debye_cutoff_for_controlled_comparator():
    op = MultiSpeciesCoulombMonteCarlo(
        make_neutral_three_species(), debye_length_m=1.0e-15,
        coulomb_logarithm=8.0,
    )
    diag = op.step(1.0e-10, seed=17)
    assert diag.pair_count > 0
    assert diag.skipped_strong_coupling_pairs == 0
    assert diag.coulomb_log_min == pytest.approx(8.0)
    assert diag.coulomb_log_max == pytest.approx(8.0)
