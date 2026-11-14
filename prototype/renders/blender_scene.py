"""PDX-1 Blender scene + renders (run headless):

  "$BLENDER" -b --factory-startup -P blender_scene.py -- <view> [--samples N] [--res WxH]

views: hero | cutaway | detail | turntable | blend (save .blend only)
Reads tessellated CAD from ../cad/out/stl/{full,cut}, the simulated field map and
alpha orbit tracks from ../sim/out, and writes PNGs + callout anchors (JSON).
"""
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

HERE = Path(__file__).resolve().parent
PROTO = HERE.parent
STL = PROTO / "cad" / "out" / "stl"
SIM = PROTO / "sim" / "out"
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["hero"]
VIEW = argv[0]
SAMPLES = int(argv[argv.index("--samples") + 1]) if "--samples" in argv else 128
RES = tuple(int(v) for v in (argv[argv.index("--res") + 1] if "--res" in argv else "1920x1080").split("x"))

MATS = {
    "stainless": dict(color=(0.70, 0.72, 0.75), metallic=1.0, rough=0.26),
    "coil_case": dict(color=(0.13, 0.25, 0.50), metallic=0.35, rough=0.38),
    "winding": dict(color=(0.55, 0.30, 0.16), metallic=0.9, rough=0.38),
    "copper": dict(color=(0.95, 0.56, 0.36), metallic=1.0, rough=0.22),
    "quartz": dict(color=(0.92, 0.97, 1.0), metallic=0.0, rough=0.03, transmission=1.0),
    "boron": dict(color=(0.03, 0.03, 0.035), metallic=0.3, rough=0.55),
    "frame": dict(color=(0.035, 0.04, 0.05), metallic=0.3, rough=0.5),
    "red": dict(color=(0.62, 0.04, 0.04), metallic=0.1, rough=0.33),
    "accel": dict(color=(0.50, 0.48, 0.43), metallic=0.15, rough=0.34),
    "alu": dict(color=(0.82, 0.83, 0.86), metallic=1.0, rough=0.36),
    "black": dict(color=(0.015, 0.016, 0.02), metallic=0.2, rough=0.45),
    "panel": dict(color=(0.20, 0.22, 0.25), metallic=0.6, rough=0.35),
    "turbo": dict(color=(0.80, 0.81, 0.83), metallic=1.0, rough=0.18),
    "cryo": dict(color=(0.75, 0.77, 0.78), metallic=0.6, rough=0.28),
}


def principled(name, color, metallic=0.0, rough=0.4, transmission=0.0, emission=None, strength=0.0, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough
    if transmission:
        b.inputs["Transmission Weight"].default_value = transmission
        b.inputs["IOR"].default_value = 1.46
    if emission:
        b.inputs["Emission Color"].default_value = (*emission, 1)
        b.inputs["Emission Strength"].default_value = strength
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
    return m


def glow(name, color, strength, edge=True):
    """Transparent emissive shell (plasma / beams): brighter at grazing angles."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1)
    em.inputs["Strength"].default_value = strength
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    if edge:
        lw = nt.nodes.new("ShaderNodeLayerWeight")
        lw.inputs["Blend"].default_value = 0.55
        nt.links.new(lw.outputs["Facing"], mix.inputs["Fac"])
    else:
        mix.inputs["Fac"].default_value = 0.85
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    m.blend_method = "BLEND" if hasattr(m, "blend_method") else None
    return m


def import_group(tag):
    objs = []
    for f in sorted((STL / tag).glob("*.stl")):
        bpy.ops.wm.stl_import(filepath=str(f), global_scale=0.001, forward_axis="Y", up_axis="Z")
        o = bpy.context.selected_objects[0]
        o.name = f"{tag}_{f.stem}"
        bm = bmesh.new(); bm.from_mesh(o.data)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=2e-5)
        bm.to_mesh(o.data); bm.free()
        bpy.context.view_layer.objects.active = o
        o.select_set(True)
        try:
            bpy.ops.object.shade_smooth_by_angle(angle=math.radians(32))
        except Exception:
            bpy.ops.object.shade_smooth()
        spec = MATS[f.stem]
        o.data.materials.append(principled(f"M_{f.stem}", **spec))
        o.select_set(False)
        objs.append(o)
    return objs


def plasma_column():
    fm = np.load(SIM / "field_map.npz")
    z, bz = fm["z"], np.abs(fm["bz"][0])
    b0 = np.interp(0, z, bz)
    xs = np.linspace(-1.70, 1.85, 220)
    r0 = 0.12
    bm = bmesh.new()
    rings = []
    nseg = 48
    for x in xs:
        b = np.interp(x, z, bz) if abs(x) <= 1.69 else np.interp(np.sign(x) * 1.69, z, bz)
        r = min(r0 * math.sqrt(b0 / b), 0.19 if x < -1.2 else (0.068 if x > 1.38 else 0.29))
        rings.append([bm.verts.new((x, r * math.cos(2 * math.pi * k / nseg), r * math.sin(2 * math.pi * k / nseg)))
                      for k in range(nseg)])
    for a, b in zip(rings[:-1], rings[1:]):
        for k in range(nseg):
            bm.faces.new((a[k], a[(k + 1) % nseg], b[(k + 1) % nseg], b[k]))
    me = bpy.data.meshes.new("plasma"); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("plasma_column", me)
    bpy.context.collection.objects.link(o)
    for p in me.polygons:
        p.use_smooth = True
    o.data.materials.append(glow("M_plasma", (0.62, 0.22, 1.0), 0.55))
    return o


def tube_curve(name, pts, radius, mat):
    cd = bpy.data.curves.new(name, "CURVE")
    cd.dimensions = "3D"
    cd.bevel_depth = radius
    cd.bevel_resolution = 2
    sp = cd.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        sp.points[i].co = (*p, 1)
    o = bpy.data.objects.new(name, cd)
    o.data.materials.append(mat)
    bpy.context.collection.objects.link(o)
    return o


def beams_and_orbits(n_orbits=14, max_frames=900):
    beam = glow("M_beam", (0.20, 0.80, 1.0), 5.0, edge=False)
    tube_curve("proton_beam", [(2.95, 0, 0), (0.0, 0, 0)], 0.004, beam)
    tube_curve("proton_beam_transmitted", [(0.0, 0, 0), (-1.71, 0, 0)], 0.0025, glow("M_beam2", (0.25, 0.85, 1.0), 2.5, edge=False))
    tr = np.load(SIM / "alpha_orbit_tracks.npz")
    traj = tr["traj"]
    alpha_mat = glow("M_alpha", (1.0, 0.30, 0.03), 3.2, edge=False)
    # prefer alphas that stay trapped for a while (they show the mirror bounce)
    alive_len = [(np.argmax(traj[:, j, 3] != 0) if (traj[:, j, 3] != 0).any() else traj.shape[0]) for j in range(traj.shape[1])]
    order = np.argsort(alive_len)[::-1][:n_orbits]
    for j in order:
        n = min(alive_len[j], max_frames)
        if n < 30:
            continue
        seg = traj[:n, j, :3]
        pts = [(p[2], p[0], p[1]) for p in seg]   # sim (x,y,z) -> CAD (Y,Z,X)
        tube_curve(f"alpha_{j}", pts, 0.0016, alpha_mat)


def lights_world():
    w = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes["Background"]
    grad = nt.nodes.new("ShaderNodeTexGradient")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    mapn = nt.nodes.new("ShaderNodeMapping")
    mapn.inputs["Rotation"].default_value = (0, math.radians(-90), 0)
    nt.links.new(coord.outputs["Generated"], mapn.inputs["Vector"])
    nt.links.new(mapn.outputs["Vector"], grad.inputs["Vector"])
    nt.links.new(grad.outputs["Fac"], ramp.inputs["Fac"])
    ramp.color_ramp.elements[0].color = (0.010, 0.012, 0.018, 1)
    ramp.color_ramp.elements[1].color = (0.16, 0.18, 0.23, 1)
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.55

    def area(name, loc, rot, size, energy, color=(1, 1, 1)):
        ld = bpy.data.lights.new(name, "AREA")
        ld.size = size; ld.energy = energy; ld.color = color
        o = bpy.data.objects.new(name, ld)
        o.location = loc; o.rotation_euler = [math.radians(a) for a in rot]
        bpy.context.collection.objects.link(o)
    area("key", (-2.5, -5.0, 4.5), (50, 0, -30), 5.0, 1300, (1.0, 0.96, 0.90))
    area("fill", (5.0, -4.0, 2.0), (70, 0, 45), 6.0, 380, (0.80, 0.88, 1.0))
    area("top", (1.2, 0, 6.0), (0, 0, 0), 8.0, 700)
    area("rim", (1.0, 6.0, 3.0), (-65, 0, 180), 6.0, 1300, (0.65, 0.78, 1.0))


def floor():
    bpy.ops.mesh.primitive_plane_add(size=60, location=(1.2, 0, -1.3))
    f = bpy.context.active_object
    f.name = "floor"
    m = principled("M_floor", (0.045, 0.048, 0.055), metallic=0.0, rough=0.22)
    f.data.materials.append(m)


def camera(loc, target, lens=35, name="cam"):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cam = bpy.data.objects.new(name, cd)
    bpy.context.collection.objects.link(cam)
    cam.location = loc
    tgt = bpy.data.objects.new(name + "_target", None)
    tgt.location = target
    bpy.context.collection.objects.link(tgt)
    con = cam.constraints.new("TRACK_TO")
    con.target = tgt
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"
    bpy.context.scene.camera = cam
    return cam, tgt


def setup_render(samples, res, engine="CYCLES"):
    sc = bpy.context.scene
    sc.render.engine = engine
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    if engine == "CYCLES":
        prefs = bpy.context.preferences.addons["cycles"].preferences
        try:
            prefs.compute_device_type = "METAL"
            prefs.get_devices()
            for d in prefs.devices:
                d.use = True
            sc.cycles.device = "GPU"
        except Exception as exc:
            print("GPU setup failed, CPU render:", exc)
        sc.cycles.samples = samples
        sc.cycles.use_denoising = True
        sc.cycles.max_bounces = 8
        sc.cycles.transparent_max_bounces = 16


def anchors(cam, points, tag):
    sc = bpy.context.scene
    bpy.context.view_layer.update()
    out = {}
    for name, p in points.items():
        co = world_to_camera_view(sc, cam, Vector(p))
        out[name] = [co.x * sc.render.resolution_x, (1 - co.y) * sc.render.resolution_y, co.z]
    (OUT / f"anchors_{tag}.json").write_text(json.dumps(out, indent=2))


FULL_ANCHORS = {
    "0.7 MV proton accelerator (SF6 tank)": (3.75, 0, 0.45),
    "Beamline quadrupole triplet": (2.40, 0, 0.15),
    "Helicon plasma source": (1.62, 0, 0.12),
    "REBCO mirror coil (4.9 T throat)": (1.05, -0.38, 0.38),
    "HTS main coils (3.0 T centre)": (0.45, -0.33, 0.36),
    "20 K cryocoolers": (1.05, 0.62, 0.62),
    "IBW antenna feeds + matching (A1-A4)": (0.30, 0, 0.82),
    "11B target insertion actuator": (0.0, 0, 1.08),
    "End-loss tank + beam dump": (-1.55, -0.2, 0.15),
    "RF amplifier + FPGA scheduler racks": (-0.62, 1.45, 0.66),
    "Diagnostic ports (Thomson, probes, interferometer)": (-0.6, -0.62, 0.0),
}
CUT_ANCHORS = {
    "11B foil target (1 um)": (0.0, 0.0, 0.0),
    "Proton beam, 0.675 MeV": (0.75, 0.0, 0.0),
    "Plasma column (helicon)": (-0.85, -0.09, 0.07),
    "Fusion-alpha gyro-orbits (simulated)": (0.18, -0.12, 0.08),
    "Faraday-shielded IBW strap": (-0.30, -0.08, 0.255),
    "HTS winding pack": (-0.45, -0.30, 0.30),
    "Coil cryostat case": (-0.75, -0.36, 0.36),
    "Vacuum vessel wall": (-1.05, -0.215, 0.215),
}


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
    tag = "cut" if VIEW in ("cutaway", "detail") else "full"
    import_group(tag)
    floor()
    lights_world()
    if VIEW in ("cutaway", "detail", "hero", "turntable", "blend"):
        plasma_column()
        beams_and_orbits(n_orbits=7 if VIEW == "detail" else 14)
    if VIEW == "hero":
        cam, _ = camera((-2.9, -5.9, 2.15), (1.35, 0.0, -0.32), lens=30)
        anchors(cam, FULL_ANCHORS, "hero")
        if "--anchors-only" in argv:
            return
    elif VIEW == "cutaway":
        cam, _ = camera((-1.05, -3.1, 1.75), (-0.02, 0.0, -0.02), lens=32)
        anchors(cam, CUT_ANCHORS, "cutaway")
    elif VIEW == "detail":
        cam, _ = camera((0.55, -1.05, 0.62), (-0.02, 0.0, 0.08), lens=38)
        anchors(cam, CUT_ANCHORS, "detail")
    elif VIEW in ("turntable", "blend"):
        cam, tgt = camera((-3.4, -6.6, 2.5), (1.25, 0.0, -0.25), lens=30)
    if VIEW == "blend":
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "pdx1_scene.blend"))
        return
    if VIEW == "turntable":
        sc = bpy.context.scene
        setup_render(SAMPLES, RES, engine="CYCLES")
        sc.cycles.samples = SAMPLES
        frames = int(argv[argv.index("--frames") + 1]) if "--frames" in argv else 120
        piv = bpy.data.objects.new("pivot", None)
        piv.location = (1.25, 0, -0.25)
        bpy.context.collection.objects.link(piv)
        cam.parent = piv
        cam.location = Vector((-3.4 - 1.25, -6.6, 2.75))
        piv.rotation_euler = (0, 0, 0)
        piv.keyframe_insert("rotation_euler", frame=1)
        piv.rotation_euler = (0, 0, math.radians(360))
        piv.keyframe_insert("rotation_euler", frame=frames + 1)
        for fc in piv.animation_data.action.fcurves if hasattr(piv.animation_data.action, "fcurves") else []:
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
        sc.frame_start, sc.frame_end = 1, frames
        (OUT / "turntable").mkdir(exist_ok=True)
        sc.render.filepath = str(OUT / "turntable" / "f_")
        sc.render.image_settings.file_format = "PNG"
        bpy.ops.render.render(animation=True)
        return
    setup_render(SAMPLES, RES)
    bpy.context.scene.render.filepath = str(OUT / f"pdx1_{VIEW}.png")
    bpy.ops.render.render(write_still=True)


main()
