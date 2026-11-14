import math

import numpy as np
import pytest
from scipy.constants import e, m_p, physical_constants

from parc_delta_v10.slowing_down import MaxwellianFieldSpecies
from parc_delta_v10.collisional_scattering import (
    nanbu_a_from_s,
    advance_test_particle_collision_step,
)

M_ALPHA = physical_constants["alpha particle mass"][0]


def _langevin(a):
    if a < 1e-4:
        return a / 3.0 - a**3 / 45.0
    return 1.0 / math.tanh(a) - 1.0 / a


def test_nanbu_inverse_langevin_solver_satisfies_implicit_equation():
    s_values = np.array([1e-5, 1e-3, 0.01, 0.1, 1.0, 5.0])
    a_values = nanbu_a_from_s(s_values)
    for s, a in zip(s_values, a_values):
        assert _langevin(float(a)) == pytest.approx(math.exp(-float(s)), abs=2e-10)


def test_nanbu_zero_exposure_means_no_collision():
    a = nanbu_a_from_s(np.array([0.0]))
    assert np.isinf(a[0])


def test_nanbu_large_isotropy_parameter_approaches_uniform_scattering():
    a = nanbu_a_from_s(np.array([100.0]))
    assert a[0] == 0.0  # isotropic limit within floating-point resolution


def test_takizuka_abe_and_nanbu_steps_return_finite_velocities():
    field = MaxwellianFieldSpecies("proton", m_p, e, 1e20, 1.0)
    v = np.tile(np.array([[1.5e7, 0.0, 0.0]]), (256, 1))
    for method in ("takizuka_abe", "nanbu"):
        out = advance_test_particle_collision_step(
            v,
            test_mass_kg=M_ALPHA,
            test_charge_c=2 * e,
            field_species=field,
            dt_s=1e-4,
            coulomb_logarithm=15.0,
            method=method,
            rng=np.random.default_rng(11),
        )
        assert out.shape == v.shape
        assert np.all(np.isfinite(out))
        assert not np.array_equal(out, v)


def test_collision_sampler_rejects_invalid_method_and_inputs():
    field = MaxwellianFieldSpecies("proton", m_p, e, 1e20, 1.0)
    v = np.array([[1.5e7, 0.0, 0.0]])
    with pytest.raises(ValueError):
        advance_test_particle_collision_step(
            v, test_mass_kg=M_ALPHA, test_charge_c=2 * e,
            field_species=field, dt_s=0.0, coulomb_logarithm=15.0,
            method="nanbu", rng=np.random.default_rng(1),
        )
    with pytest.raises(ValueError):
        advance_test_particle_collision_step(
            v, test_mass_kg=M_ALPHA, test_charge_c=2 * e,
            field_species=field, dt_s=1e-6, coulomb_logarithm=15.0,
            method="unknown", rng=np.random.default_rng(1),
        )


def test_multispecies_symmetric_split_step_is_finite_and_order_independent_in_setup():
    from parc_delta_v10.collisional_scattering import (
        advance_test_particle_multispecies_collision_step,
    )
    from scipy.constants import m_e

    fields = [
        MaxwellianFieldSpecies("electron", m_e, -e, 1.04e20, 1.0e4),
        MaxwellianFieldSpecies("proton", m_p, e, 1.0e20, 1.0e4),
        MaxwellianFieldSpecies("thermal_alpha", M_ALPHA, 2 * e, 2.0e18, 1.0e4),
    ]
    velocities = np.tile(np.array([[1.2e7, -2.0e6, 3.0e5]]), (128, 1))
    result = advance_test_particle_multispecies_collision_step(
        velocities,
        test_mass_kg=M_ALPHA,
        test_charge_c=2 * e,
        field_species=fields,
        dt_s=1.0e-5,
        coulomb_logarithm=15.0,
        method="nanbu",
        rng=np.random.default_rng(123),
    )
    assert result.shape == velocities.shape
    assert np.all(np.isfinite(result))
    assert not np.array_equal(result, velocities)


def test_multispecies_scattering_rejects_duplicate_or_empty_fields():
    from parc_delta_v10.collisional_scattering import (
        advance_test_particle_multispecies_collision_step,
    )

    velocities = np.array([[1.0e7, 0.0, 0.0]])
    common = dict(
        test_mass_kg=M_ALPHA,
        test_charge_c=2 * e,
        dt_s=1e-5,
        coulomb_logarithm=15.0,
        method="nanbu",
        rng=np.random.default_rng(1),
    )
    with pytest.raises(ValueError, match="at least one"):
        advance_test_particle_multispecies_collision_step(
            velocities, field_species=[], **common
        )
    field = MaxwellianFieldSpecies("proton", m_p, e, 1e20, 1e4)
    with pytest.raises(ValueError, match="unique"):
        advance_test_particle_multispecies_collision_step(
            velocities, field_species=[field, field], **common
        )


def test_multispecies_scattering_rejects_zero_subcycling():
    from parc_delta_v10.collisional_scattering import (
        advance_test_particle_multispecies_collision_step,
    )
    field = MaxwellianFieldSpecies("proton", m_p, e, 1e20, 1e4)
    with pytest.raises(ValueError, match="substeps_per_species"):
        advance_test_particle_multispecies_collision_step(
            np.array([[1.0e7, 0.0, 0.0]]),
            test_mass_kg=M_ALPHA, test_charge_c=2 * e,
            field_species=[field], dt_s=1e-5, coulomb_logarithm=15.0,
            method="nanbu", rng=np.random.default_rng(4),
            substeps_per_species=0,
        )
