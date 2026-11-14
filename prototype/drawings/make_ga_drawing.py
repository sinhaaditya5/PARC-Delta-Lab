"""PDX-1 general-arrangement drawing, generated in CADCraft (cadcraft-cli, headless).

Builds the drawing with CADCraft JSON commands from design/pdx1_params.py:
  - Section B-B (longitudinal section through the machine axis), 1:10
  - Section A-A (cross-section at the 11B target plane X = 0), 1:10
  - balloons + parts list, notes, title block on an A0 frame (model space x10)
Outputs: drawings/out/PDX1-GA-001.{dxf,pdf,png}
"""
from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "design"))
import pdx1_params as P  # noqa: E402

OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
CMDS: list[str] = []
SC = 10.0                      # drawing scale 1:10 on A0 -> model frame 11890 x 8410
SX, SY = 2850.0, 5750.0        # side-view origin (machine X=0, Z=0)
EX, EY = 2150.0, 2350.0        # end-view origin (Y=0, Z=0)


def cmd(cid: str, **params) -> None:
    CMDS.append(f"{cid} {json.dumps(params)}")


def layer(name):
    cmd("layer.current", name=name)


def S(x, z):
    """side-view machine coords (X, Z) -> drawing"""
    return [round(SX + x, 2), round(SY + z, 2)]


def E(y, z):
    return [round(EX + y, 2), round(EY + z, 2)]


def rect(p1, p2, hatch=None, hscale=6, angle=0):
    cmd("rectang", p1=p1, p2=p2)
    if hatch:
        layer("HATCH")
        cmd("hatch", handles=["{last}"], pattern=hatch, scale=hscale, angle=angle)


def side_rect(x0, x1, z0, z1, hatch=None, hscale=6, angle=0, lay="OUTLINE"):
    layer(lay)
    rect(S(x0, z0), S(x1, z1), hatch, hscale, angle)
    layer("OUTLINE")


def text(at, s, h=35, justify="L", lay="TEXT", rot=0):
    layer(lay)
    cmd("text", at=at, text=s, height=h, justify=justify, rotation=rot)
    layer("OUTLINE")


def balloon(n, target, at, r=55):
    layer("BALLOON")
    dx, dy = target[0] - at[0], target[1] - at[1]
    d = math.hypot(dx, dy)
    start = [at[0] + dx / d * r, at[1] + dy / d * r]
    cmd("line", points=[start, target])
    cmd("circle", center=at, radius=r)
    cmd("donut", inside=0, outside=14, center=target) if False else cmd("circle", center=target, radius=6)
    cmd("text", at=at, text=str(n), height=45, justify="MC")
    layer("OUTLINE")


def build():
    cmd("linetype", load="*")
    for name, col, lt, lw in (("OUTLINE", 7, "Continuous", 0.5), ("THIN", 7, "Continuous", 0.18),
                              ("HIDDEN", 8, "HIDDEN", 0.25), ("CENTER", 1, "CENTER", 0.18),
                              ("HATCH", 8, "Continuous", 0.13), ("DIM", 5, "Continuous", 0.18),
                              ("TEXT", 7, "Continuous", 0.25), ("BALLOON", 3, "Continuous", 0.25),
                              ("BORDER", 7, "Continuous", 0.7), ("PLASMA", 6, "PHANTOM", 0.18)):
        cmd("layer.new", name=name, color=col, linetype=lt, lineweight=lw)
    cmd("ltscale", scale=8)
    cmd("dimstyle", name="PDX", current=True, DIMSCALE=SC, DIMTXT=3.5, DIMASZ=3.0, DIMEXO=1.5, DIMEXE=2.0,
        DIMGAP=1.0, DIMDEC=0)

    # ---------------------------------------------------------------- sheet frame + title block
    layer("BORDER")
    cmd("rectang", p1=[0, 0], p2=[11890, 8410])
    cmd("rectang", p1=[200, 100], p2=[11790, 8310])
    tb0x, tb0y, tb1x, tb1y = 8090, 100, 11790, 1100
    cmd("rectang", p1=[tb0x, tb0y], p2=[tb1x, tb1y])
    for y in (350, 600, 850):
        cmd("line", points=[[tb0x, y], [tb1x, y]])
    cmd("line", points=[[10090, tb0y], [10090, 850]])
    layer("OUTLINE")
    text([tb0x + 60, 940], "PARC-Delta  |  PDX-1 LINEAR TEST STAND - GENERAL ARRANGEMENT", h=62)
    text([tb0x + 60, 700], "CONCEPT DESIGN - NOT FOR FABRICATION", h=48)
    text([tb0x + 60, 450], "DWG PDX1-GA-001   REV A   SHEET 1/1", h=48)
    text([tb0x + 60, 190], "SCALE 1:10 (A0)   UNITS mm   2026-11-01", h=42)
    text([10150, 700], "CAD: CADCraft 0.15.1 (headless)", h=36)
    text([10150, 450], "3D: build123d / OpenCascade", h=36)
    text([10150, 190], "Source: design/pdx1_params.py", h=36)

    # ---------------------------------------------------------------- SECTION B-B (longitudinal)
    floor = -P.AXIS_HEIGHT_MM
    layer("THIN")
    cmd("line", points=[S(-2200, floor), S(4950, floor)])
    for k in range(36):
        x = -2200 + k * 200
        cmd("line", points=[S(x, floor), S(x - 80, floor - 80)])
    layer("CENTER")
    cmd("line", points=[S(-2150, 0), S(4900, 0)])
    layer("OUTLINE")
    ri, ro = P.VESSEL_R_IN, P.VESSEL_R_IN + P.VESSEL_WALL
    # vessel walls (sectioned) and flanges
    for sgn in (1, -1):
        side_rect(P.VESSEL_X0, P.VESSEL_X1, sgn * ri, sgn * ro, hatch="ANSI31", hscale=4)
        for x0 in (P.VESSEL_X0 - P.FLANGE_T, P.VESSEL_X1):
            side_rect(x0, x0 + P.FLANGE_T, sgn * ri, sgn * P.FLANGE_R_OUT, hatch="ANSI31", hscale=4)
    # coils: cryostat case outline + sectioned winding pack
    for c in P.COILS:
        for sgn in (1, -1):
            pad = c.case_pad
            side_rect(c.x - c.width / 2 - pad, c.x + c.width / 2 + pad, sgn * (c.r_in - pad), sgn * (c.r_out + pad))
            side_rect(c.x - c.width / 2, c.x + c.width / 2, sgn * c.r_in, sgn * c.r_out, hatch="ANSI37", hscale=6)
        # cradle (visible, below)
        ro_case = c.r_out + c.case_pad
        side_rect(c.x - c.width / 2 - 5, c.x + c.width / 2 + 5, floor + 100, -ro_case + 60)
    # base frame
    side_rect(-1950, 1950, floor, floor + 100)
    # plasma flux tube (phantom) between mirror throats
    layer("PLASMA")
    cmd("line", points=[S(-1700, 160), S(-1050, 95), S(-500, 115), S(500, 115), S(1050, 95), S(1400, 70)])
    cmd("line", points=[S(-1700, -160), S(-1050, -95), S(-500, -115), S(500, -115), S(1050, -95), S(1400, -70)])
    layer("OUTLINE")
    # ports in the XZ plane (top/bottom) + devices
    for p in P.PORTS:
        if p.angle_deg not in (90, 270):
            continue
        sgn = 1 if p.angle_deg == 90 else -1
        layer("OUTLINE")
        cmd("line", points=[S(p.x - p.r_tube, sgn * ro), S(p.x - p.r_tube, sgn * (p.r_end - 22))])
        cmd("line", points=[S(p.x + p.r_tube, sgn * ro), S(p.x + p.r_tube, sgn * (p.r_end - 22))])
        side_rect(p.x - 76, p.x + 76, sgn * (p.r_end - 22), sgn * p.r_end)
        top = p.r_end
        if p.tag.startswith("A"):
            side_rect(p.x - 85, p.x + 85, sgn * (top + 10), sgn * (top + 210))
            side_rect(p.x - 7, p.x + 7, P.ANTENNA_STRAP_R[1], ri + 40, lay="HIDDEN")
        elif p.tag == "P1":
            for k in range(10):
                w = 60 if k % 2 == 0 else 50
                side_rect(-w, w, top + 12 + 16 * k, top + 28 + 16 * k, lay="THIN")
            side_rect(-70, 70, top + 200, top + 320)
            side_rect(-45, 45, top + 320, top + 420)
        elif p.tag == "P4":
            side_rect(-70, 70, -(top + 160), -top)
        elif p.tag.startswith("V"):
            side_rect(p.x - 95, p.x + 95, -(top + 90), -top)
            side_rect(p.x - 80, p.x + 80, -(top + 320), -(top + 90))
            side_rect(p.x - 60, p.x + 60, -(top + 380), -(top + 320))
        elif p.tag.startswith("G"):
            side_rect(p.x - 35, p.x + 35, top, top + 140)
            side_rect(p.x - 40, p.x + 40, top + 140, top + 210)
    # IBW straps (sectioned at top) + Faraday screen line
    for xa in P.ANTENNA_X:
        side_rect(xa - P.ANTENNA_STRAP_W / 2, xa + P.ANTENNA_STRAP_W / 2, P.ANTENNA_STRAP_R[0], P.ANTENNA_STRAP_R[1], hatch="SOLID")
        layer("THIN")
        cmd("line", points=[S(xa - 55, 255), S(xa + 55, 255)])
    # target: foil + frame + arm
    side_rect(-2, 2, -P.TARGET_FRAME_R[1], P.TARGET_FRAME_R[1], hatch="SOLID")
    layer("OUTLINE")
    cmd("line", points=[S(-8, 40), S(-8, P.PORTS[0].r_end)])
    cmd("line", points=[S(8, 40), S(8, P.PORTS[0].r_end)])
    # left end: reducer, end tank, end plate, cap, analyzer, pump
    etx0, etx1 = P.END_TANK_X
    rt = P.END_TANK_R_IN
    for sgn in (1, -1):
        layer("OUTLINE")
        cmd("line", points=[S(P.VESSEL_X0 - P.FLANGE_T, sgn * ro), S(etx1, sgn * (rt + 8))])
        cmd("line", points=[S(P.VESSEL_X0 - P.FLANGE_T, sgn * ri), S(etx1, sgn * rt)])
        side_rect(etx0, etx1, sgn * rt, sgn * (rt + 8), hatch="ANSI31", hscale=4)
    side_rect(etx0 - 30, etx0, -270, 270, hatch="ANSI31", hscale=4)
    side_rect(P.END_PLATE_X - 10, P.END_PLATE_X + 10, -190, 190, hatch="ANSI37", hscale=6)
    side_rect(etx0 - 230, etx0 - 30, -90, 90)
    side_rect(etx0 - 370, etx0 - 230, -80, 80)
    side_rect(-1540 - 51, -1540 + 51, -330, -208)
    side_rect(-1540 - 80, -1540 + 80, -560, -350)
    side_rect(-1540 - 50, -1540 + 50, floor + 100, -560 - 60 if False else -610)
    # right end: reducer, helicon tube + coils + antenna, gate valve, beamline, quads, cross, accelerator
    hx0, hx1 = P.HELICON_X
    for sgn in (1, -1):
        layer("OUTLINE")
        cmd("line", points=[S(P.VESSEL_X1 + P.FLANGE_T, sgn * ro), S(hx0, sgn * 90)])
        side_rect(hx0, hx1, sgn * P.HELICON_TUBE_R[0], sgn * P.HELICON_TUBE_R[1], hatch="ANSI31", hscale=3)
        for xr in (hx0 + 120, hx1 - 120):
            side_rect(xr - 35, xr + 35, sgn * 115, sgn * 175, hatch="ANSI37", hscale=5)
        side_rect(hx0 + 80, hx0 + 420, sgn * 84, sgn * 96, lay="THIN")
        side_rect(hx1, hx1 + 20, sgn * 50, sgn * 125)
        cmd("line", points=[S(2010, sgn * P.BEAMPIPE_R), S(P.ACCEL_X[0] + 140, sgn * P.BEAMPIPE_R)])
    side_rect(0.5 * (hx0 + hx1) - 110, 0.5 * (hx0 + hx1) + 110, 165, 295)
    side_rect(0.5 * (hx0 + hx1) - 40, 0.5 * (hx0 + hx1) + 40, floor + 100, -115)
    side_rect(1920, 2010, -120, 180)
    for xq in P.QUADS_X:
        side_rect(xq - 55, xq + 55, -150, 150)
        side_rect(xq - 45, xq + 45, floor + 100, -150)
    side_rect(2720 - 35, 2720 + 35, -170, 170)
    ax0, ax1, ar = P.ACCEL_X[0] + 140, P.ACCEL_X[1] - 140, P.ACCEL_R
    layer("OUTLINE")
    cmd("line", points=[S(ax0, ar), S(ax1, ar)])
    cmd("line", points=[S(ax0, -ar), S(ax1, -ar)])
    cmd("ellipse", center=S(ax0, 0), major=[0, ar], ratio=0.31, start=0, end=180)
    cmd("ellipse", center=S(ax1, 0), major=[0, ar], ratio=0.31, start=180, end=360)
    for xs in (P.ACCEL_X[0] + 400, P.ACCEL_X[1] - 400):
        side_rect(xs - 80, xs + 80, floor + 100, -ar + 40)
    side_rect(P.ACCEL_X[1] - 10, P.ACCEL_X[1] + 250, -500, 200)
    side_rect(P.ACCEL_X[0] - 140, P.ACCEL_X[1] + 260, floor, floor + 100)
    # cryocooler (projected, 45 deg)
    for c in P.MIRROR_COILS:
        base = (c.r_out + c.case_pad) * math.sin(math.radians(45))
        side_rect(c.x - 55, c.x + 55, base, base + 320 * 0.707)
        side_rect(c.x - 85, c.x + 85, base + 320 * 0.707, base + 450 * 0.707)
    text(S(-2150, 1480), "SECTION B-B  (LONGITUDINAL, THROUGH MACHINE AXIS)   SCALE 1:10", h=70)
    text(S(-2150, 1370), "Proton beam travels right -> left along the axis onto the 11B foil at X = 0", h=40)

    # ---- dimensions (side)
    layer("DIM")
    cmd("dimlinear", p1=S(P.VESSEL_X0, ro), p2=S(P.VESSEL_X1, ro), at=S(0, 1020))
    cmd("dimlinear", p1=S(-1050, -540 - 20), p2=S(1050, -540 - 20), at=S(0, -1180), text="<> (MIRROR COIL CENTRES)")
    cmd("dimlinear", p1=S(-150, -500), p2=S(150, -500), at=S(0, -1080), text="<> PITCH")
    cmd("dimlinear", p1=S(-2050, floor), p2=S(P.ACCEL_X[1] + 260, floor), at=S(1400, floor - 300), text="<> OVERALL")
    cmd("dimlinear", p1=S(-2100, floor), p2=S(-2100, 0), at=S(-2300, -650), text="<> AXIS HT")
    cmd("dimlinear", p1=S(P.VESSEL_X1 + 60, -ro), p2=S(P.VESSEL_X1 + 60, ro), at=S(1330, 0), text="%%c<> OD")
    cmd("dimlinear", p1=S(P.ACCEL_X[1] + 300, -ar), p2=S(P.ACCEL_X[1] + 300, ar), at=S(P.ACCEL_X[1] + 520, 0), text="%%c<>")
    layer("OUTLINE")

    # ---------------------------------------------------------------- SECTION A-A (X = 0)
    layer("THIN")
    cmd("line", points=[E(-1150, floor), E(1150, floor)])
    for k in range(13):
        y = -1150 + k * 200
        cmd("line", points=[E(y, floor), E(y - 80, floor - 80)])
    layer("CENTER")
    cmd("line", points=[E(-800, 0), E(800, 0)])
    cmd("line", points=[E(0, -800), E(0, 1250)])
    layer("OUTLINE")
    cmd("circle", center=E(0, 0), radius=ro)
    cmd("circle", center=E(0, 0), radius=ri)
    layer("HATCH")
    cmd("hatch", points=[E(0, ri + 4)], pattern="ANSI31", scale=4)
    layer("HIDDEN")
    cmd("circle", center=E(0, 0), radius=P.LIMITER_R)
    layer("PLASMA")
    cmd("circle", center=E(0, 0), radius=P.PLASMA_RADIUS_MM)
    layer("OUTLINE")
    c3 = P.MAIN_COILS[3]
    cmd("circle", center=E(0, 0), radius=c3.r_out + c3.case_pad)
    cmd("circle", center=E(0, 0), radius=c3.r_in - c3.case_pad)
    layer("HIDDEN")
    cmd("circle", center=E(0, 0), radius=c3.r_out)
    cmd("circle", center=E(0, 0), radius=c3.r_in)
    layer("OUTLINE")
    # target ring + foil + arm
    cmd("circle", center=E(0, 0), radius=P.TARGET_FRAME_R[1])
    cmd("circle", center=E(0, 0), radius=P.TARGET_FOIL_R)
    layer("HATCH")
    cmd("hatch", points=[E(0, 0)], pattern="SOLID")
    layer("OUTLINE")
    cmd("line", points=[E(-8, 40), E(-8, 700)])
    cmd("line", points=[E(8, 40), E(8, 700)])
    # antenna strap A3 beyond (arc) + Faraday rods
    a0, a1 = 90 - P.ANTENNA_SPAN_DEG / 2, 90 + P.ANTENNA_SPAN_DEG / 2
    for rr in P.ANTENNA_STRAP_R:
        cmd("arc", center=E(0, 0), radius=rr, start=a0, end=a1)
    for j in range(13):
        ang = math.radians(a0 - 4 + j * (P.ANTENNA_SPAN_DEG + 8) / 12)
        cmd("circle", center=E(255 * math.cos(ang), 255 * math.sin(ang)), radius=3)
    # ports at X = 0
    for p in P.PORTS:
        if p.x != 0.0:
            continue
        a = math.radians(p.angle_deg)
        ux, uz = math.cos(a), math.sin(a)
        nx, nz = -uz, ux
        for s in (1, -1):
            cmd("line", points=[E(ro * ux + s * p.r_tube * nx, ro * uz + s * p.r_tube * nz),
                                E((p.r_end - 22) * ux + s * p.r_tube * nx, (p.r_end - 22) * uz + s * p.r_tube * nz)])
        fl = [E((p.r_end - 22) * ux + 76 * nx, (p.r_end - 22) * uz + 76 * nz), E(p.r_end * ux + 76 * nx, p.r_end * uz + 76 * nz),
              E(p.r_end * ux - 76 * nx, p.r_end * uz - 76 * nz), E((p.r_end - 22) * ux - 76 * nx, (p.r_end - 22) * uz - 76 * nz)]
        cmd("line", points=fl, closed=True)
    # cradle under coil M4
    rc = c3.r_out + c3.case_pad
    ang = math.degrees(math.acos(410 / rc)) if rc > 410 else 0
    zc = -math.sqrt(max(rc**2 - 410**2, 0))
    cmd("pline", vertices=[E(-410, floor + 100), E(-410, zc), E(410, zc), E(410, floor + 100)], closed=True)
    cmd("rectang", p1=E(-460, floor), p2=E(460, floor + 100))
    text(E(-1150, 1350), "SECTION A-A  (TARGET PLANE, X = 0)   SCALE 1:10", h=70)
    layer("DIM")
    cmd("dimlinear", p1=E(-ri, 0), p2=E(ri, 0), at=E(0, -180), text="%%c<> BORE")
    cmd("dimlinear", p1=E(-rc, 0), p2=E(rc, 0), at=E(0, -760), text="%%c<> CRYOSTAT")
    cmd("dimlinear", p1=E(-P.LIMITER_R, 0), p2=E(P.LIMITER_R, 0), at=E(0, -60), text="%%c<> LIMITER")
    cmd("dimlinear", p1=E(0, 0), p2=E(0, P.PORTS[0].r_end), at=E(-300, 350), text="<>")
    layer("OUTLINE")

    # ---------------------------------------------------------------- balloons
    items = [
        (1, "Central vacuum vessel, 316L, ID 600 x 2400", "1", S(-900, ro), S(-900, 1050 - 200)),
        (2, "Main coil, REBCO HTS, 0.67 MA-t, in 20 K cryostat", "6", S(-450, 500), S(-560, 900)),
        (3, "Mirror coil, REBCO HTS, 2.79 MA-t (4.9 T throat)", "2", S(-1050, 540), S(-1300, 900)),
        (4, "IBW antenna strap + Faraday screen (A1-A4)", "4", S(-600, 267), S(-750, 650)),
        (5, "IBW matching network + 7/16 RF feed", "4", S(-300, 760), S(-180, 980)),
        (6, "11B foil target (1 um) on water-cooled frame + arm", "1", S(0, 20), S(260, 420)),
        (7, "Target bellows + linear actuator (port P1)", "1", S(60, 820), S(320, 980)),
        (8, "Helicon plasma source, quartz tube + 2 coils", "1", S(1650, 75), S(1650, 520)),
        (9, "Quadrupole triplet", "3", S(2400, 150), S(2400, 520)),
        (10, "0.7 MV electrostatic accelerator, SF6 tank", "1", S(3700, 450), S(3700, 760)),
        (11, "End-loss tank, Cu beam dump / end plate", "1", S(-1720, 150), S(-1880, 520)),
        (12, "Turbomolecular pump + gate valve", "3", S(895, -900), S(1150, -800)),
        (13, "GM cryocooler, 20 K", "2", S(1050, 640), S(900, 980)),
        (14, "Support cradles + base frame", "1 set", S(-750, -900), S(-1150, -900)),
        (15, "Si alpha spectrometer (port P4)", "1", S(0, -780), S(330, -860)),
    ]
    for n, _, _, tgt, at in items:
        balloon(n, tgt, at)

    # ---------------------------------------------------------------- parts list (manual grid)
    x0, y_top = 8090, 4350
    widths = [180, 2900, 620]
    row_h = 115
    rows = [("NO", "DESCRIPTION", "QTY")] + [(str(i[0]), i[1], i[2]) for i in items]
    layer("OUTLINE")
    total_w = sum(widths)
    text([x0, y_top + 60], "PARTS LIST", h=60)
    for r_i in range(len(rows) + 1):
        y = y_top - r_i * row_h
        cmd("line", points=[[x0, y], [x0 + total_w, y]])
    xx = x0
    for w in widths + [0]:
        cmd("line", points=[[xx, y_top], [xx, y_top - len(rows) * row_h]])
        xx += w
    for r_i, row in enumerate(rows):
        y = y_top - r_i * row_h - row_h / 2
        xx = x0
        for c_i, (w, cell) in enumerate(zip(widths, row)):
            text([xx + 40, y], cell, h=40 if r_i else 44, justify="ML")
            xx += w

    # ---------------------------------------------------------------- notes
    notes = [
        "NOTES",
        "1. ALL DIMENSIONS IN mm. MACHINE AXIS = +X, 1300 mm ABOVE FLOOR.",
        "2. MAGNET (SIMULATED, magpylib): B0 = 3.00 T, MIRROR RATIO 1.63, ~14 MJ STORED,",
        "    PEAK WINDING FIELD ~10 T -> REBCO HTS AT 20 K (NbTi REJECTED IN DESIGN ITERATION).",
        "3. BEAM: 0.675 MeV PROTONS, 10 uA, ON 1 um ENRICHED 11B FOIL AT X = 0.",
        "4. IBW CHANNEL PLAN A1-A4: 57.6 / 80.6 / 103.6 / 126.6 MHz (ILLUSTRATIVE).",
        "5. ALPHA ORBITS (SIMULATED): 0.1 % WALL LOSS AT 3 T; 40 % LOSS CONE (MATCHES THEORY).",
        "6. CONCEPT GEOMETRY FOR SIMULATION AND PLANNING. STRUCTURAL, THERMAL, VACUUM,",
        "    QUENCH-PROTECTION AND RADIATION-SAFETY ANALYSES ARE OUTSTANDING.",
    ]
    for k, line in enumerate(notes):
        text([8090, 2290 - k * 95], line, h=52 if k == 0 else 40)
    # section markers on the side view
    for sgn in (1, -1):
        text(S(-30, sgn * 1150 - (0 if sgn > 0 else 60)), "A", h=70, justify="MC")
    layer("THIN")
    cmd("line", points=[S(0, 1080), S(0, 1000)])
    cmd("line", points=[S(0, -1000), S(0, -1080)])


def main():
    build()
    # Resolution order: $CADCRAFT_CLI, cadcraft-cli on PATH, then a local build in <repo>/tools.
    cli = (os.environ.get("CADCRAFT_CLI") or shutil.which("cadcraft-cli")
           or str(HERE.parents[1] / "tools/cadcraft/target/release/cadcraft-cli"))
    if not Path(cli).exists():
        sys.exit(f"cadcraft-cli not found ({cli}). Build CADCraft and set CADCRAFT_CLI; see docs/REPRODUCIBILITY.md.")
    dxf, png, pdf = OUT / "PDX1-GA-001.dxf", OUT / "PDX1-GA-001.png", OUT / "PDX1-GA-001.pdf"
    args = [cli, "run", "--metric"]
    for c in CMDS:
        args += ["--cmd", c]
    args += ["--cmd", "exportpdf " + json.dumps({"path": str(pdf), "paper": "A0", "scale": "1:10", "landscape": True}),
             "--save", str(dxf), "--export", str(png)]
    (OUT / "commands.jsonl").write_text("\n".join(CMDS))
    res = subprocess.run(args, capture_output=True, text=True)
    errs = [l for l in res.stderr.splitlines() if "error" in l.lower()]
    print("commands:", len(CMDS), "exit:", res.returncode)
    print("\n".join(errs[:20]) or "no errors")
    print("\n".join(l for l in res.stderr.splitlines() if l.startswith("wrote")))


if __name__ == "__main__":
    main()
