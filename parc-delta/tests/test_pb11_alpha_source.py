import numpy as np
import pytest
from scipy.constants import c, e

from parc_delta_v10.pb11_alpha_source import (
    M_ALPHA_MEV,
    Q_TOTAL_MEV,
    e_cm_from_proton_lab_energy,
    proton_lab_energy_from_e_cm,
    sample_pb11_alpha_birth,
)


def test_q_value_and_beam_cm_conversion_round_trip():
    assert 8.67 < Q_TOTAL_MEV < 8.69
    for beam_energy in (0.148, 0.675, 1.85, 4.73):
        ecm = e_cm_from_proton_lab_energy(beam_energy)
        assert proton_lab_energy_from_e_cm(ecm) == pytest.approx(beam_energy, rel=2e-10)


@pytest.mark.parametrize("channel", ["alpha0", "alpha1"])
def test_three_alpha_kinematics_conserves_event_energy_and_cm_momentum(channel):
    sample = sample_pb11_alpha_birth(512, channel=channel, e_cm_mev=0.620, seed=27)
    kinetic = sample.kinetic_energy_mev.reshape(-1, 3)
    assert np.allclose(np.sum(kinetic, axis=1), Q_TOTAL_MEV + 0.620, rtol=0, atol=2e-9)

    alpha_mass_kg = M_ALPHA_MEV * 1.0e6 * e / c**2
    velocity = sample.velocity_m_s.reshape(-1, 3, 3)
    speed2 = np.sum(velocity**2, axis=2)
    gamma = 1.0 / np.sqrt(1.0 - speed2 / c**2)
    momenta = gamma[:, :, None] * alpha_mass_kg * velocity
    assert np.max(np.linalg.norm(np.sum(momenta, axis=1), axis=1)) < 2e-25

    assert sample.velocity_m_s.shape == (1536, 3)
    assert set(sample.role) == {"primary", "be8_daughter_1", "be8_daughter_2"}
    assert abs(float(np.mean(sample.pitch_cosine))) < 0.04


def test_alpha1_channel_has_a_broader_primary_spectrum_than_alpha0():
    alpha0 = sample_pb11_alpha_birth(6000, channel="alpha0", e_cm_mev=0.620, seed=1)
    alpha1 = sample_pb11_alpha_birth(6000, channel="alpha1", e_cm_mev=0.620, seed=1)
    p0 = alpha0.kinetic_energy_mev[alpha0.role == "primary"]
    p1 = alpha1.kinetic_energy_mev[alpha1.role == "primary"]
    assert np.std(p0) < 1e-6
    assert np.std(p1) > 0.2
    assert np.mean(p0) > np.mean(p1)


def test_beam_lab_frame_has_positive_mean_forward_momentum():
    sample = sample_pb11_alpha_birth(
        2000, channel="alpha0", e_cm_mev=0.620, frame="beam_lab", seed=9
    )
    assert float(np.mean(sample.velocity_m_s[:, 2])) > 0
    per_event_energy = np.bincount(sample.event_id, weights=sample.kinetic_energy_mev)
    e_lab = proton_lab_energy_from_e_cm(0.620)
    assert np.mean(per_event_energy) == pytest.approx(Q_TOTAL_MEV + e_lab, rel=1e-10)
    assert sample.metadata["cross_section_weighting"] == "not applied"


def test_source_rejects_invalid_inputs_and_does_not_invent_branching():
    with pytest.raises(ValueError):
        sample_pb11_alpha_birth(0, channel="alpha0", e_cm_mev=0.620)
    with pytest.raises(ValueError):
        sample_pb11_alpha_birth(10, channel="alpha0", e_cm_mev=-0.1)
    with pytest.raises(ValueError):
        sample_pb11_alpha_birth(10, channel="alpha2", e_cm_mev=0.620)
    sample = sample_pb11_alpha_birth(10, channel="alpha0", e_cm_mev=0.620)
    assert sample.metadata["branching_fraction_assumed"] == 0.0


def test_gyrotropic_velocity_projection_is_normalized():
    from parc_delta_v10.pb11_alpha_source import gyrotropic_velocity_histogram

    sample = sample_pb11_alpha_birth(5000, channel="alpha1", e_cm_mev=0.620, seed=84)
    speed_max = float(np.max(np.linalg.norm(sample.velocity_m_s, axis=1)))
    hist = gyrotropic_velocity_histogram(
        sample,
        v_parallel_edges_m_s=np.linspace(-1.05 * speed_max, 1.05 * speed_max, 81),
        v_perp_edges_m_s=np.linspace(0.0, 1.05 * speed_max, 81),
    )
    assert hist["captured_particle_fraction"] == pytest.approx(1.0)
    assert hist["normalization"] == pytest.approx(1.0, abs=1e-12)
    assert hist["f_v_s3_per_m3"].shape == (80, 80)
