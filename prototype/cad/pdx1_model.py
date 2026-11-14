"""PDX-1 parametric 3D CAD model (build123d / OpenCascade).

All dimensions come from design/pdx1_params.py (mm). Machine axis = +X, Z up,
machine-axis height 1300 mm above the floor.

Outputs (prototype/cad/out/):
  pdx1_assembly.step       labelled, coloured STEP assembly
  stl/full/<group>.stl     tessellated material groups for Blender
  stl/cut/<group>.stl      same, with the front-top quadrant of the central cell cut away
  pdx1_parts.json          part list (name, group, role, bounding box, volume)
"""
from __future__ import annotations

import json
import math
import sys
import time
from collections import defaultdict
from pathlib import Path

from build123d import (
    Box,
    Circle,
    Color,
    Compound,
    Cone,
    Cylinder,
    Helix,
    Plane,
    Polygon,
    Pos,
    Rot,
    Sphere,
    Torus,
    export_step,
    export_stl,
    extrude,
    scale,
    sweep,
)

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "design"))
import pdx1_params as P  # noqa: E402

OUT = HERE / "out"
(OUT / "stl" / "full").mkdir(parents=True, exist_ok=True)
(OUT / "stl" / "cut").mkdir(parents=True, exist_ok=True)

FLOOR_Z = -P.AXIS_HEIGHT_MM
GROUP_COLOR = {
    "stainless": (0.72, 0.74, 0.77), "coil_case": (0.55, 0.64, 0.78), "winding": (0.62, 0.36, 0.20),
    "copper": (0.85, 0.50, 0.28), "quartz": (0.80, 0.90, 0.95), "boron": (0.10, 0.10, 0.12),
    "frame": (0.22, 0.24, 0.28), "red": (0.75, 0.12, 0.12), "accel": (0.92, 0.88, 0.78),
    "alu": (0.82, 0.83, 0.85), "black": (0.08, 0.08, 0.09), "panel": (0.35, 0.37, 0.40),
    "turbo": (0.78, 0.79, 0.80), "cryo": (0.90, 0.92, 0.93),
}
PARTS: list[tuple[str, str, str, object, bool]] = []   # (name, group, role, shape, cuttable)


def add(name, group, role, shape, cuttable=False):
    PARTS.append((name, group, role, shape, cuttable))


# ------------------------------------------------------------------ helpers
def tube_x(r_out, r_in, x0, x1):
    h = x1 - x0
    s = Cylinder(r_out, h)
    if r_in > 0:
        s = s - Cylinder(r_in, h)
    return Pos((x0 + x1) / 2, 0, 0) * Rot(0, 90, 0) * s


def cone_x(r0, r1, x0, x1, wall=None):
    h = x1 - x0
    s = Cone(r0, r1, h)
    if wall:
        s = s - Cone(r0 - wall, r1 - wall, h + 0.02)
    return Pos((x0 + x1) / 2, 0, 0) * Rot(0, 90, 0) * s


def radial(shape_along_z, x, angle_deg):
    """Place a part built along +Z (radius measured from the machine axis)."""
    return Pos(x, 0, 0) * Rot(angle_deg - 90, 0, 0) * shape_along_z


def zcyl(r, z0, z1):
    return Pos(0, 0, (z0 + z1) / 2) * Cylinder(r, z1 - z0)


def wedge_x(x0, x1, a0, a1, r=2000.0):
    pts = [(0.0, 0.0)] + [(r * math.cos(math.radians(a)), r * math.sin(math.radians(a)))
                          for a in [a0 + (a1 - a0) * k / 16 for k in range(17)]]
    return extrude(Plane.YZ.offset(x0) * Polygon(*pts, align=None), amount=x1 - x0)


# ------------------------------------------------------------------ central vessel
ri, ro = P.VESSEL_R_IN, P.VESSEL_R_IN + P.VESSEL_WALL
vessel = tube_x(ro, ri, P.VESSEL_X0, P.VESSEL_X1)
for port in P.PORTS:
    vessel = vessel - radial(zcyl(port.r_tube - 3, ri - 20, ro + 20), port.x, port.angle_deg)
add("Central vacuum vessel (316L, ID 600)", "stainless", "vacuum boundary", vessel, True)
for sx in (-1, 1):
    x0 = P.VESSEL_X1 if sx > 0 else P.VESSEL_X0 - P.FLANGE_T
    add(f"Vessel end flange {'R' if sx > 0 else 'L'}", "stainless", "flange",
        tube_x(P.FLANGE_R_OUT, ri if sx < 0 else 80, x0, x0 + P.FLANGE_T) if sx > 0 else
        tube_x(P.FLANGE_R_OUT, ri, x0, x0 + P.FLANGE_T), True)

# ------------------------------------------------------------------ coils + cryostat cases
for c in P.COILS:
    x0, x1 = c.x - c.width / 2, c.x + c.width / 2
    pad = c.case_pad
    add(f"Coil {c.name} winding (REBCO)", "winding", f"{c.group} coil winding pack",
        tube_x(c.r_out, c.r_in, x0, x1), True)
    case = tube_x(c.r_out + pad, c.r_in - pad, x0 - pad, x1 + pad) - tube_x(c.r_out + 2, c.r_in - 2, x0 - 2, x1 + 2)
    add(f"Coil {c.name} cryostat case", "coil_case", "20 K conduction-cooled coil cryostat", case, True)
    # saddle cradle down to the base frame
    ro_case = c.r_out + pad
    cradle = Pos(c.x, 0, (FLOOR_Z + 100 + (-ro_case + 120)) / 2) * Box(c.width + 2 * pad - 30, 820,
                                                                      (-ro_case + 120) - (FLOOR_Z + 100))
    cradle = cradle - tube_x(ro_case + 1, 0, x0 - pad - 5, x1 + pad + 5)
    add(f"Coil {c.name} support cradle", "frame", "structure", cradle)

# cold-mass thermal bus + cryocoolers
bus_r = 0.5 * (P.MAIN_COILS[0].r_in + P.MAIN_COILS[0].r_out)
add("Thermal bus (OFHC copper)", "copper", "conduction cooling link",
    Pos(0, bus_r * math.cos(math.radians(45)), bus_r * math.sin(math.radians(45))) * tube_x(22, 0, -1080, 1080))
for c in P.MIRROR_COILS:
    base = c.r_out + c.case_pad
    cc = zcyl(55, base - 5, base + 320) + zcyl(85, base + 320, base + 450) + zcyl(40, base + 450, base + 520)
    add(f"GM cryocooler on {c.name}", "cryo", "20 K cryocooler cold head", radial(cc, c.x, 45))

# ------------------------------------------------------------------ radial ports + devices
for port in P.PORTS:
    L0, L1 = ri - 2, port.r_end - 22
    tube = zcyl(port.r_tube, L0, L1) - zcyl(port.r_tube - 3, L0 - 1, L1 + 1)
    flange = zcyl(76 if port.r_tube > 45 else 60, L1, port.r_end)
    add(f"Port {port.tag} tube", "stainless", port.role, radial(tube, port.x, port.angle_deg))
    add(f"Port {port.tag} CF flange", "stainless", port.role,
        radial(flange - zcyl(port.r_tube - 3, L1 - 1, port.r_end + 1), port.x, port.angle_deg))
    top = port.r_end
    tag = port.tag
    if tag.startswith("A"):
        box = Pos(0, 0, top + 110) * Box(170, 230, 200)
        add(f"Matching network {tag}", "alu", "IBW antenna L-match + vacuum feedthrough",
            radial(box + zcyl(40, top, top + 12), port.x, port.angle_deg))
        add(f"Coax 7/16 connector {tag}", "copper", "RF input",
            radial(Pos(0, 140, top + 140) * Rot(90, 0, 0) * Cylinder(22, 60), port.x, port.angle_deg))
    elif tag == "P1":
        bellows = zcyl(52, top, top + 12)
        for k in range(10):
            bellows = bellows + zcyl(60 if k % 2 == 0 else 50, top + 12 + 16 * k, top + 28 + 16 * k)
        act = Pos(0, 0, top + 260) * Box(140, 140, 120) + zcyl(45, top + 320, top + 420)
        add("Target bellows", "stainless", "target insertion bellows", radial(bellows, 0, 90))
        add("Target linear actuator", "alu", "stepper-driven linear actuator", radial(act, 0, 90))
    elif tag in ("P2", "P3"):
        add(f"Viewport {tag}", "quartz", port.role, radial(zcyl(50, top, top + 8), port.x, port.angle_deg))
        add(f"Optics box {tag}", "alu", port.role,
            radial(Pos(0, 0, top + 110) * Box(150, 150, 200), port.x, port.angle_deg))
    elif tag == "P4":
        add("Si alpha spectrometer housing", "alu", port.role,
            radial(zcyl(70, top, top + 160) + zcyl(30, top + 160, top + 240), port.x, port.angle_deg))
    elif tag in ("D1", "D2"):
        drv = zcyl(18, top, top + 420) + Pos(0, 0, top + 470) * Box(110, 110, 110)
        add(f"Probe drive {tag}", "alu", port.role, radial(drv, port.x, port.angle_deg))
    elif tag == "D3":
        add("Interferometer horn", "alu", port.role,
            radial(Pos(0, 0, top + 90) * Cone(40, 75, 180) + zcyl(30, top + 180, top + 300), port.x, port.angle_deg))
    elif tag == "D4":
        add("Phase-2 blank flange", "red", port.role, radial(zcyl(76, top, top + 22), port.x, port.angle_deg))
    elif tag in ("V1", "V2"):
        gv = Pos(0, 0, top + 45) * Box(190, 190, 90)
        pump = zcyl(80, top + 90, top + 320) + zcyl(60, top + 320, top + 380)
        add(f"Gate valve {tag}", "stainless", "isolation valve", radial(gv, port.x, port.angle_deg))
        add(f"Turbomolecular pump {tag}", "turbo", "700 l/s turbo pump", radial(pump, port.x, port.angle_deg))
    elif tag.startswith("G"):
        add(f"Gauge / FILD head {tag}", "alu", port.role,
            radial(zcyl(35, top, top + 140) + Pos(0, 0, top + 175) * Box(80, 80, 70), port.x, port.angle_deg))

# ------------------------------------------------------------------ in-vessel: IBW antennas
for k, xa in enumerate(P.ANTENNA_X):
    a0, a1 = 90 - P.ANTENNA_SPAN_DEG / 2, 90 + P.ANTENNA_SPAN_DEG / 2
    w = P.ANTENNA_STRAP_W
    strap = tube_x(P.ANTENNA_STRAP_R[1], P.ANTENNA_STRAP_R[0], xa - w / 2, xa + w / 2) & wedge_x(xa - w, xa + w, a0, a1)
    feed = radial(zcyl(8, P.ANTENNA_STRAP_R[1] - 2, ri + 40), xa, 90)
    add(f"IBW antenna strap A{k+1}", "copper", f"current strap, Faraday shielded (x = {xa:.0f} mm)", strap + feed)
    rods = None
    for j in range(13):
        ang = math.radians(a0 - 4 + j * (P.ANTENNA_SPAN_DEG + 8) / 12)
        rod = Pos(xa, 255 * math.cos(ang), 255 * math.sin(ang)) * Rot(0, 90, 0) * Cylinder(3, 110)
        rods = rod if rods is None else rods + rod
    add(f"Faraday shield A{k+1}", "copper", "Faraday screen rods", rods)

# ------------------------------------------------------------------ 11B foil target on insertion arm
fr0, fr1 = P.TARGET_FRAME_R
add("11B foil target (1 um, enriched)", "boron", "fusion target", tube_x(P.TARGET_FOIL_R, 0, -0.4, 0.4))
add("Target frame ring", "copper", "water-cooled foil frame", tube_x(fr1, fr0, -2, 2))
add("Target insertion arm", "stainless", "arm", zcyl(8, fr1 - 2, P.PORTS[0].r_end))

# ------------------------------------------------------------------ left end: end-loss tank + beam dump
etx0, etx1 = P.END_TANK_X
add("Left reducer cone", "stainless", "transition", cone_x(P.END_TANK_R_IN + 8, ro, etx1, P.VESSEL_X0 - P.FLANGE_T, wall=8))
end_tank = tube_x(P.END_TANK_R_IN + 8, P.END_TANK_R_IN, etx0, etx1) - radial(zcyl(48, 150, 260), -1540, 270)
add("End-loss tank", "stainless", "end-loss / beam-dump chamber", end_tank)
add("End cap flange", "stainless", "flange", tube_x(270, 0, etx0 - 30, etx0))
add("Water-cooled end plate (Cu)", "copper", "beam dump + plasma end plate", tube_x(190, 0, P.END_PLATE_X - 10, P.END_PLATE_X + 10))
add("End-loss alpha analyzer", "alu", "electrostatic end-loss analyzer",
    tube_x(90, 0, etx0 - 230, etx0 - 30) + Pos(etx0 - 300, 0, 0) * Box(140, 160, 160))
add("End-tank pump port", "stainless", "pump port",
    radial(zcyl(51, 205, 330) - zcyl(48, 200, 335) + zcyl(76, 330, 350), -1540, 270))
add("End-tank turbo pump", "turbo", "turbo pump", radial(zcyl(80, 350, 560) + zcyl(60, 560, 610), -1540, 270))

# ------------------------------------------------------------------ right end: helicon source
hx0, hx1 = P.HELICON_X
add("Right reducer cone", "stainless", "transition", cone_x(ro, 90, P.VESSEL_X1 + P.FLANGE_T, hx0, wall=8))
add("Helicon quartz tube", "quartz", "plasma source tube", tube_x(P.HELICON_TUBE_R[1], P.HELICON_TUBE_R[0], hx0, hx1))
ant_r, ant_len = 90.0, 340.0
for xr in (hx0 + 80, hx0 + 80 + ant_len):
    add(f"Helicon antenna ring @{xr:.0f}", "copper", "half-turn helical antenna",
        Pos(xr, 0, 0) * Rot(0, 90, 0) * Torus(ant_r, 6))
try:
    helix = Helix(pitch=2 * ant_len, height=ant_len, radius=ant_r)
    strap = sweep(Plane(helix @ 0, z_dir=helix % 0) * Circle(6), path=helix)
    for rot in (0, 180):
        add(f"Helicon antenna strap {rot}", "copper", "half-turn helical antenna",
            Pos(hx0 + 80, 0, 0) * Rot(0, 90, 0) * Rot(0, 0, rot) * strap)
except Exception as exc:  # pragma: no cover - fallback geometry
    print("helix sweep failed, using straight straps:", exc)
for xr in (hx0 + 120, hx1 - 120):
    add(f"Helicon source coil @{xr:.0f}", "copper", "resistive source solenoid", tube_x(175, 115, xr - 35, xr + 35))
add("Helicon RF feed box", "alu", "13.56 MHz helicon match box", Pos(0.5 * (hx0 + hx1), 0, 230) * Box(220, 160, 130))
add("Helicon end flange", "stainless", "flange", tube_x(125, 50, hx1, hx1 + 20))
add("Helicon support", "frame", "structure", Pos(0.5 * (hx0 + hx1), 0, (FLOOR_Z + 100 - 115) / 2) *
    Box(80, 300, -115 - (FLOOR_Z + 100)))

# ------------------------------------------------------------------ beamline + accelerator
add("Beamline gate valve", "stainless", "isolation valve", Pos(1965, 0, 30) * Box(90, 300, 300))
add("Beam pipe", "stainless", "beam transport", tube_x(P.BEAMPIPE_R, P.BEAMPIPE_R - 4, 2010, P.ACCEL_X[0] + 60))
for k, xq in enumerate(P.QUADS_X):
    q = Pos(xq, 0, 0) * Box(110, 300, 300) - tube_x(70, 0, xq - 60, xq + 60)
    add(f"Quadrupole Q{k+1}", "red", "beam focusing quadrupole", q)
    add(f"Quadrupole Q{k+1} stand", "frame", "structure", Pos(xq, 0, (FLOOR_Z + 100 - 150) / 2) * Box(90, 240, -150 - (FLOOR_Z + 100)))
cross = zcyl(35, -170, 170) - zcyl(32, -171, 171) + zcyl(55, 150, 170) + zcyl(55, -170, -150)
add("Beam profile monitor cross", "stainless", "beam diagnostics", Pos(2720, 0, 0) * cross)
ax0, ax1 = P.ACCEL_X
add("Accelerator pressure tank", "accel", "0.7 MV single-ended electrostatic accelerator (SF6)",
    tube_x(P.ACCEL_R, 0, ax0 + 140, ax1 - 140)
    + Pos(ax0 + 140, 0, 0) * scale(Sphere(P.ACCEL_R), (0.31, 1, 1))
    + Pos(ax1 - 140, 0, 0) * scale(Sphere(P.ACCEL_R), (0.31, 1, 1)))
for xs in (ax0 + 400, ax1 - 400):
    s = Pos(xs, 0, (FLOOR_Z + 100 - 250) / 2) * Box(160, 760, -250 - (FLOOR_Z + 100))
    add(f"Accelerator saddle @{xs:.0f}", "frame", "structure", s - tube_x(P.ACCEL_R + 1, 0, xs - 100, xs + 100))
add("Ion source + HV supply cabinet", "alu", "RF ion source", Pos(ax1 + 120, 0, -150) * Box(260, 520, 700))
add("Accelerator base", "frame", "structure", Pos(0.5 * (ax0 + ax1) + 60, 0, FLOOR_Z + 50) * Box(ax1 - ax0 + 400, 900, 100))

# ------------------------------------------------------------------ base frame
for y in (-380, 380):
    add(f"Base beam y={y}", "frame", "structure", Pos(0, y, FLOOR_Z + 50) * Box(3900, 160, 100))
for x in (-1850, -1050, 0, 1050, 1850):
    add(f"Cross beam x={x}", "frame", "structure", Pos(x, 0, FLOOR_Z + 50) * Box(140, 920, 100))
add("End-tank stand", "frame", "structure", Pos(-1540, 0, (FLOOR_Z + 100 - 208) / 2) *
    Box(100, 300, -208 - (FLOOR_Z + 100)) - tube_x(209, 0, -1600, -1480))

# ------------------------------------------------------------------ control + RF racks
for k, x in enumerate((-650, 0)):
    rack = Pos(x, 1850, FLOOR_Z + 1000) * Box(600, 800, 2000)
    add(f"Rack {k+1}", "black", "RF amplifiers + FPGA scheduler" if k == 0 else "DAQ + control", rack)
    for j in range(5):
        add(f"Rack {k+1} unit {j+1}", "panel", "19-inch unit",
            Pos(x, 1448, FLOOR_Z + 1650 - j * 260) * Box(520, 10, 200))

# ================================================================== export
def main() -> None:
    t0 = time.time()
    cut_box = Pos(0, -80 - 1500, 60 + 1500) * Box(2520, 3000, 3000)
    groups_full, groups_cut = defaultdict(list), defaultdict(list)
    labelled = []
    parts_json = []
    for name, group, role, shape, cuttable in PARTS:
        shape.label = name
        shape.color = Color(*GROUP_COLOR[group])
        labelled.append(shape)
        groups_full[group].append(shape)
        cut_shape = (shape - cut_box) if cuttable else shape
        groups_cut[group].append(cut_shape)
        bb = shape.bounding_box()
        parts_json.append({"name": name, "group": group, "role": role,
                           "bbox_min_mm": [round(v, 1) for v in (bb.min.X, bb.min.Y, bb.min.Z)],
                           "bbox_max_mm": [round(v, 1) for v in (bb.max.X, bb.max.Y, bb.max.Z)],
                           "volume_l": round(shape.volume / 1e6, 3)})
    assembly = Compound(label="PDX-1 test stand", children=labelled)
    export_step(assembly, str(OUT / "pdx1_assembly.step"))
    for tag, groups in (("full", groups_full), ("cut", groups_cut)):
        for group, shapes in groups.items():
            export_stl(Compound(list(shapes)), str(OUT / "stl" / tag / f"{group}.stl"),
                       tolerance=0.6, angular_tolerance=0.25)
    lo = [min(p["bbox_min_mm"][i] for p in parts_json) for i in range(3)]
    hi = [max(p["bbox_max_mm"][i] for p in parts_json) for i in range(3)]
    meta = {"parts": parts_json, "part_count": len(parts_json),
            "overall_mm": [round(hi[i] - lo[i]) for i in range(3)], "bbox_min_mm": lo, "bbox_max_mm": hi,
            "group_colors": GROUP_COLOR, "build_seconds": round(time.time() - t0, 1)}
    (OUT / "pdx1_parts.json").write_text(json.dumps(meta, indent=2))
    print(f"{len(parts_json)} parts, overall {meta['overall_mm']} mm, {meta['build_seconds']} s")


if __name__ == "__main__":
    main()
