"""PARC-Delta v1.6 kinetic model and test-particle collision validation."""

__version__ = "1.6.0-research"

from .ledger import EnergyLedger, ExternalFlow, PowerTransfer
from .modes import GrowthRate, WaveModeSnapshot, mode_to_ledger_terms
from .diagnostics import ledger_summary, routing_metrics, compare_scenarios
from .linear_ibw import (
    CODATA_ALPHA_TO_PROTON_MASS_RATIO,
    CollisionlessIBWModel,
    LAPDReferenceCase,
    run_reference_case,
)
from .finite_k_ibw import (
    FiniteKParallelIBWModel,
    FiniteParallelCase,
    KineticMode,
    make_reference_case,
    plasma_dispersion_zeta,
)

__all__ = [
    "EnergyLedger",
    "ExternalFlow",
    "PowerTransfer",
    "GrowthRate",
    "WaveModeSnapshot",
    "mode_to_ledger_terms",
    "ledger_summary",
    "routing_metrics",
    "compare_scenarios",
    "CODATA_ALPHA_TO_PROTON_MASS_RATIO",
    "CollisionlessIBWModel",
    "LAPDReferenceCase",
    "run_reference_case",
    "FiniteKParallelIBWModel",
    "FiniteParallelCase",
    "KineticMode",
    "make_reference_case",
    "plasma_dispersion_zeta",
]

from .pb11_alpha_source import (
    AlphaBirthSample,
    sample_pb11_alpha_birth,
    gyrotropic_velocity_histogram,
)
from .coulomb_mc import (
    CollisionSpecies,
    CollisionDiagnostics,
    MultiSpeciesCoulombMonteCarlo,
    maxwellian_velocity_samples,
)

__all__ += [
    "AlphaBirthSample",
    "sample_pb11_alpha_birth",
    "gyrotropic_velocity_histogram",
    "CollisionSpecies",
    "CollisionDiagnostics",
    "MultiSpeciesCoulombMonteCarlo",
    "maxwellian_velocity_samples",
]

from .collision_benchmarks import (
    PairwiseEnergyExchange,
    landau_pairwise_energy_exchange,
    landau_spitzer_temperature_rate_ev_s,
    landau_spitzer_power_density_w_m3,
    temperature_ev_from_velocities,
)

__all__ += [
    "PairwiseEnergyExchange",
    "landau_pairwise_energy_exchange",
    "landau_spitzer_temperature_rate_ev_s",
    "landau_spitzer_power_density_w_m3",
    "temperature_ev_from_velocities",
]

from .slowing_down import (
    MaxwellianFieldSpecies,
    SpeciesCoefficients,
    SlowingDownSnapshot,
    SlowingDownResult,
    RosenbluthSlowingDownSolver,
    chandrasekhar_g,
    rosenbluth_test_particle_coefficients,
    expected_kinetic_energy_rate_per_marker_j_s,
)
from .collisional_scattering import (
    nanbu_a_from_s,
    advance_test_particle_collision_step,
    run_test_particle_scattering,
    advance_test_particle_multispecies_collision_step,
    run_test_particle_multispecies_scattering,
)

__all__ += [
    "MaxwellianFieldSpecies",
    "SpeciesCoefficients",
    "SlowingDownSnapshot",
    "SlowingDownResult",
    "RosenbluthSlowingDownSolver",
    "chandrasekhar_g",
    "rosenbluth_test_particle_coefficients",
    "expected_kinetic_energy_rate_per_marker_j_s",
    "nanbu_a_from_s",
    "advance_test_particle_collision_step",
    "run_test_particle_scattering",
    "advance_test_particle_multispecies_collision_step",
    "run_test_particle_multispecies_scattering",
]
