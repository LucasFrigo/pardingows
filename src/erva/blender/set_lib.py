# Helpers shared by the PARDÃO E A ERVA scene scripts: paths, saving, collections, flat cartoon materials.
# Scripts run either headless (blender -b -P file) or inside the open window through bl.mjs, which has no __file__:
# then the repo root comes from ERVA_ROOT or the default below.
import math
import os
import time

import bpy

try:
    ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
except NameError:
    ROOT = os.environ.get("ERVA_ROOT", r"E:\Projetos\pardingows")
WORK = os.path.join(ROOT, "blender", "erva")
BLEND = os.path.join(WORK, "erva.blend")
ASSETS = os.path.join(WORK, "assets")
TEXTURES = os.path.join(WORK, "textures")
REVIEW = os.path.join(WORK, "review")
SOLUCAO = os.path.join(ROOT, "blender", "solucao", "solucao.blend")
RENDER_W, RENDER_H = 1080, 1920


def save():
    """Saves, waiting out whatever on Windows briefly holds a just-written file while Blender swaps in its .blend1 backup."""
    for attempt in range(6):
        try:
            bpy.ops.wm.save_mainfile()
            return
        except RuntimeError:
            if attempt == 5:
                raise
            time.sleep(2)


def fresh(name, parent=None):
    """An empty collection under the scene (or under parent), cleared if it already exists."""
    c = bpy.data.collections.get(name)
    if c:
        for o in list(c.all_objects):
            bpy.data.objects.remove(o, do_unlink=True)
        for ch in list(c.children):
            bpy.data.collections.remove(ch)
    else:
        c = bpy.data.collections.new(name)
    host = parent.children if parent else bpy.context.scene.collection.children
    if c.name not in host:
        host.link(c)
    return c


def redraw():
    """Lets the open window repaint between long steps, so progress shows while a script runs through bl.mjs."""
    if bpy.app.background:
        return
    try:
        bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=1)
    except Exception:
        pass


# ---------------------------------------------------------------- cartoon materials
# 1930s cartoons were painted in a few flat greys. A cel material is Diffuse -> Shader to RGB -> a constant ramp:
# the lit side gets the fill tone, the shadow side a darker step of it. 'tone' is the fill's grey (0 black .. 1 white).

def cel(name, tone, shade=0.55, emit=0.0, alpha=None):
    """Flat two-step cel material. shade is the shadow tone as a fraction of the fill."""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    t = m.node_tree
    t.nodes.clear()
    out = t.nodes.new("ShaderNodeOutputMaterial")
    if emit or tone <= 0.02:
        # pure ink black (and glowing bits) take no light
        em = t.nodes.new("ShaderNodeEmission")
        em.inputs["Color"].default_value = (tone, tone, tone, 1)
        em.inputs["Strength"].default_value = 1.0
        t.links.new(em.outputs[0], out.inputs[0])
    else:
        dif = t.nodes.new("ShaderNodeBsdfDiffuse")
        dif.inputs["Color"].default_value = (1, 1, 1, 1)
        s2r = t.nodes.new("ShaderNodeShaderToRGB")
        ramp = t.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.interpolation = "CONSTANT"
        e = ramp.color_ramp.elements
        lo = tone * shade
        e[0].position, e[0].color = 0.0, (lo, lo, lo, 1)
        e[1].position, e[1].color = 0.18, (tone, tone, tone, 1)
        em = t.nodes.new("ShaderNodeEmission")
        t.links.new(dif.outputs[0], s2r.inputs[0])
        t.links.new(s2r.outputs[0], ramp.inputs[0])
        t.links.new(ramp.outputs[0], em.inputs[0])
        t.links.new(em.outputs[0], out.inputs[0])
    if alpha is not None:
        mix = t.nodes.new("ShaderNodeMixShader")
        tr = t.nodes.new("ShaderNodeBsdfTransparent")
        src = out.inputs[0].links[0].from_socket
        t.links.new(tr.outputs[0], mix.inputs[1])
        t.links.new(src, mix.inputs[2])
        mix.inputs[0].default_value = alpha
        t.links.new(mix.outputs[0], out.inputs[0])
        m.surface_render_method = "BLENDED"
    m.diffuse_color = (tone, tone, tone, 1)
    m["cel"] = tone
    return m


def lum(rgb):
    r, g, b = rgb[:3]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def view(target, yaw=20, pitch=80, dist=4.0, overlays=False, shading="RENDERED"):
    """Points the open window's 3D view at target (world point) from yaw/pitch degrees, overlays off for a clean look.
    yaw 0 looks from the front (-Y side) of a cast member facing -Y."""
    if bpy.app.background:
        return
    from mathutils import Euler, Vector
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type != "VIEW_3D":
                continue
            sp = area.spaces.active
            sp.shading.type = shading
            sp.overlay.show_overlays = overlays
            r3 = sp.region_3d
            r3.view_perspective = "PERSP"
            r3.view_location = Vector(target)
            r3.view_rotation = Euler((math.radians(pitch), 0, math.radians(yaw))).to_quaternion()
            r3.view_distance = dist
            area.tag_redraw()
    redraw()


def cel_pattern(name, tone, kind, tone2=0.32, scale=1.0):
    """cel() with a print on it, in object space so it sticks to the part: stripes, dots or checks of tone2 over tone."""
    m = cel(name, tone)
    t = m.node_tree
    ramp = next(n for n in t.nodes if n.type == "VALTORGB")
    em = next(n for n in t.nodes if n.type == "EMISSION")
    tc = t.nodes.new("ShaderNodeTexCoord")
    mix = t.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    k = tone2 / max(tone, 1e-3)
    mix.inputs["B"].default_value = (k, k, k, 1)
    if kind == "stripes":
        tex = t.nodes.new("ShaderNodeTexWave")
        tex.wave_type = "BANDS"
        tex.bands_direction = "Z"
        tex.inputs["Scale"].default_value = 0.9 * scale
        fac_src = tex.outputs["Fac"]
        gt = t.nodes.new("ShaderNodeMath")
        gt.operation = "GREATER_THAN"
        gt.inputs[1].default_value = 0.55
        t.links.new(tc.outputs["Object"], tex.inputs["Vector"])
        t.links.new(fac_src, gt.inputs[0])
        fac = gt.outputs[0]
    elif kind == "dots":
        tex = t.nodes.new("ShaderNodeTexVoronoi")
        tex.inputs["Scale"].default_value = 2.2 * scale
        tex.inputs["Randomness"].default_value = 0.0
        lt = t.nodes.new("ShaderNodeMath")
        lt.operation = "LESS_THAN"
        lt.inputs[1].default_value = 0.22
        t.links.new(tc.outputs["Object"], tex.inputs["Vector"])
        t.links.new(tex.outputs["Distance"], lt.inputs[0])
        fac = lt.outputs[0]
    else:  # checks
        tex = t.nodes.new("ShaderNodeTexChecker")
        tex.inputs["Scale"].default_value = 1.6 * scale
        tex.inputs["Color1"].default_value = (1, 1, 1, 1)
        tex.inputs["Color2"].default_value = (0, 0, 0, 1)
        t.links.new(tc.outputs["Object"], tex.inputs["Vector"])
        fac = tex.outputs["Fac"]
    t.links.new(fac, mix.inputs["Factor"])
    t.links.new(ramp.outputs[0], mix.inputs["A"])
    t.links.new(mix.outputs["Result"], em.inputs["Color"])
    return m


def instance_geom(empty):
    """World vertices and a BVH of a collection-instance empty's model (library objects' transforms, then the empty's)."""
    from mathutils.bvhtree import BVHTree
    mw = empty.matrix_world
    verts, polys = [], []
    for o in empty.instance_collection.all_objects:
        if o.type != "MESH":
            continue
        base = len(verts)
        m = mw @ o.matrix_world
        verts += [m @ v.co for v in o.data.vertices]
        polys += [[base + i for i in p.vertices] for p in o.data.polygons]
    return verts, BVHTree.FromPolygons(verts, polys)


def chair_measure(empty):
    """A chair's measurements, from its own geometry (no scene raycasts: spindle backs let rays through):
    back = unit vector (flat) from the centre towards the backrest; seat = seat height (a ray down the middle);
    back_d = how far behind the centre the backrest's front face is; centre = the footprint's centre."""
    from mathutils import Vector
    vs, bvh = instance_geom(empty)
    zmax = max(v.z for v in vs)
    cx = (min(v.x for v in vs) + max(v.x for v in vs)) / 2
    cy = (min(v.y for v in vs) + max(v.y for v in vs)) / 2
    centre = Vector((cx, cy, 0))
    hi = [v for v in vs if v.z > 0.8 * zmax]
    back = Vector((sum(v.x for v in hi) / len(hi) - cx, sum(v.y for v in hi) / len(hi) - cy, 0)).normalized()
    seat = 0.0
    for k in (-0.1, -0.05, 0.0, 0.05):  # straight down onto the seat, a little in front of the middle
        o = centre - back * k + Vector((0, 0, 0.62 * zmax))
        loc, _n, _i, _d = bvh.ray_cast(o, Vector((0, 0, -1)))
        if loc is not None:
            seat = max(seat, loc.z)
    back_d = 0.25
    for h in (0.25, 0.4):  # towards the backrest from in front, above the seat
        loc, _n, _i, _d = bvh.ray_cast(centre - back * 1.0 + Vector((0, 0, seat + h)), back)
        if loc is not None:
            back_d = min(back_d, (loc - centre).dot(back))
    lat = Vector((-back.y, back.x, 0))
    band = [(v - centre).dot(back) for v in vs if seat + 0.2 < v.z < seat + 0.5 and abs((v - centre).dot(lat)) < 0.2]
    band = [d for d in band if d > 0.02]
    if band:  # spindle backs: the nearest backrest vertex, since rays slip between the spindles
        back_d = min(back_d, min(band))
    return {"back": back, "seat": seat, "back_d": back_d, "centre": centre}
