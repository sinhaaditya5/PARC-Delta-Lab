"""PDX-1 shared design parameters (single source of truth for CAD + simulations).

PDX-1 is a *concept* bench-scale linear magnetized test stand for the PARC-Delta
research programme. It is not an engineering-validated design, not a reactor and
not a power-producing device.

Coordinates
-----------
CAD:        machine axis = +X (mm), Z up, Y horizontal. Machine axis height = 0.
Simulation: cylindrical (r, z) with z == CAD X, in metres.

The proton beam travels in the -X direction (right to left), through the helicon
source tube, onto a thin 11B foil at X = 0, and the transmitted beam is stopped
on the water-cooled end plate at the left end.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------- physics targets
B0_TARGET_T = 3.0            # central-cell field on axis at X = 0
MIRROR_RATIO_TARGET = 1.6    # B(mirror throat) / B0
BEAM_ENERGY_MEV = 0.675      # proton lab energy (matches PARC-Delta v1.6 source)
BEAM_CURRENT_UA = 10.0       # DC beam current on target (concept value)
BEAM_SIGMA_MM = 5.0          # Gaussian beam spot sigma at the foil

# ---------------------------------------------------------------- vacuum vessel
VESSEL_R_IN = 300.0
VESSEL_WALL = 8.0
VESSEL_X0, VESSEL_X1 = -1200.0, 1200.0
FLANGE_R_OUT = 380.0
FLANGE_T = 30.0
LIMITER_R = 250.0            # first-wall / antenna Faraday-shield radius (alpha loss surface)

# ---------------------------------------------------------------- superconducting coils
@dataclass(frozen=True)
class Coil:
    name: str
    x: float          # centre (mm)
    r_in: float       # winding-pack inner radius (mm)
    r_out: float      # winding-pack outer radius (mm)
    width: float      # axial width (mm)
    group: str        # "main" or "mirror"
    case_pad: float = 20.0   # cryostat case clearance around the winding (mm)

    @property
    def area_mm2(self) -> float:
        return (self.r_out - self.r_in) * self.width


MAIN_COILS = [Coil(f"M{i+1}", x, 380.0, 480.0, 120.0, "main")
              for i, x in enumerate((-750.0, -450.0, -150.0, 150.0, 450.0, 750.0))]
MIRROR_COILS = [Coil("MR-L", -1050.0, 380.0, 520.0, 140.0, "mirror"),
                Coil("MR-R", 1050.0, 380.0, 520.0, 140.0, "mirror")]
COILS = MIRROR_COILS[:1] + MAIN_COILS + MIRROR_COILS[1:]

# ---------------------------------------------------------------- ports (radial, through coil gaps)
@dataclass(frozen=True)
class Port:
    tag: str
    x: float
    angle_deg: float      # 90 = top (+Z), 0 = +Y side, 180 = -Y side, 270 = bottom
    r_tube: float         # tube outer radius (mm)
    r_end: float          # radial distance of flange face from axis (mm)
    role: str


PORTS = [
    Port("P1", 0.0, 90, 51.0, 700.0, "11B target insertion (bellows actuator)"),
    Port("P2", 0.0, 0, 51.0, 650.0, "Thomson scattering laser input"),
    Port("P3", 0.0, 180, 51.0, 650.0, "Thomson collection / alpha spectrometer view"),
    Port("P4", 0.0, 270, 51.0, 650.0, "Silicon alpha-spectrometer array"),
    Port("A1", -600.0, 90, 51.0, 650.0, "IBW antenna A1 feed"),
    Port("A2", -300.0, 90, 51.0, 650.0, "IBW antenna A2 feed"),
    Port("A3", 300.0, 90, 51.0, 650.0, "IBW antenna A3 feed"),
    Port("A4", 600.0, 90, 51.0, 650.0, "IBW antenna A4 feed"),
    Port("D1", -300.0, 0, 51.0, 650.0, "B-dot probe array (wave spectrum)"),
    Port("D2", 300.0, 0, 51.0, 650.0, "Langmuir / RFEA probe (proton heating)"),
    Port("D3", -600.0, 180, 51.0, 650.0, "mm-wave interferometer"),
    Port("D4", 600.0, 180, 51.0, 650.0, "Phase-2 fast-ion injector port (blanked)"),
    Port("V1", -895.0, 270, 51.0, 700.0, "Turbo pump 1"),
    Port("V2", 895.0, 270, 51.0, 700.0, "Turbo pump 2"),
    Port("G1", -895.0, 90, 40.0, 640.0, "Gas puff / gauge"),
    Port("G2", 895.0, 90, 40.0, 640.0, "Fast-ion loss detector (FILD)"),
]

# ---------------------------------------------------------------- IBW antenna array
ANTENNA_X = (-600.0, -300.0, 300.0, 600.0)
ANTENNA_STRAP_R = (262.0, 272.0)
ANTENNA_STRAP_W = 60.0
ANTENNA_SPAN_DEG = 70.0

# ---------------------------------------------------------------- 11B target
TARGET_FOIL_R = 25.0
TARGET_FRAME_R = (25.0, 40.0)
TARGET_FOIL_THICKNESS_UM = 1.0

# ---------------------------------------------------------------- plasma (bench, helicon-sustained)
PLASMA_RADIUS_MM = 120.0
BENCH_PLASMA = dict(n_e_m3=1.0e19, T_e_eV=10.0, T_p_eV=2.0, ln_lambda=12.0)

# ---------------------------------------------------------------- right end: helicon + beamline + accelerator
HELICON_X = (1400.0, 1900.0)
HELICON_TUBE_R = (70.0, 75.0)
BEAMPIPE_R = 50.0
QUADS_X = (2250.0, 2400.0, 2550.0)
ACCEL_X = (2900.0, 4500.0)
ACCEL_R = 450.0

# ---------------------------------------------------------------- left end: end-loss tank + beam dump
END_TANK_X = (-1750.0, -1330.0)
END_TANK_R_IN = 200.0
END_PLATE_X = -1720.0

AXIS_HEIGHT_MM = 1300.0       # floor is at Z = -1300
