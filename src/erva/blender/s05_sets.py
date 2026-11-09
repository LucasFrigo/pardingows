# Step 4b: the sets, built live in the open window from library instances plus pieces made in code. Re-runnable: it
# clears and rebuilds its own collections. Writes blender/erva/stage.json with each set's origin and named spots.
#   node src/thps/bl.mjs run src/erva/blender/s05_sets.py
# The frame is vertical (9:16): sets are composed tall and narrow, the camera on the -Y side, characters facing -Y.
#   SALA   storyteller room       origin (-30, 0)
#   TREVAS darkness, a spotlight  origin (-15, 0)
#   SELVA  the jungle garden      origin (0, 0); the spooky jungle (ASSOMBRADA) is built on the same spot
import importlib
import json
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    HERE = os.path.join(os.environ.get("ERVA_ROOT", r"E:\Projetos\pardingows"), "src", "erva", "blender")
sys.path.insert(0, HERE)
import set_lib, hose  # noqa: E402
for mod in (set_lib, hose):
    importlib.reload(mod)
from set_lib import WORK, cel, fresh, redraw, save  # noqa: E402

OB = bpy.data.objects
rng = random.Random(7)
SALA, TREVAS, SELVA = Vector((-30, 0, 0)), Vector((-15, 0, 0)), Vector((0, 0, 0))
stage = {"sala": list(SALA), "trevas": list(TREVAS), "selva": list(SELVA), "spots": {}}


def spot(name, v):
    stage["spots"][name] = [round(c, 3) for c in v]


# ---------------------------------------------------------------- helpers

def inst(asset, coll, loc, rz=0.0, s=1.0, name=None):
    """An instance of a library model: an empty that shows AS_<asset>."""
    src = bpy.data.collections["AS_" + asset]
    e = OB.new(name or f"{asset}.{len(coll.objects)}", None)
    e.instance_type = "COLLECTION"
    e.instance_collection = src
    e.location = loc
    e.rotation_euler = (0, 0, math.radians(rz))
    e.scale = (s, s, s) if isinstance(s, (int, float)) else s
    e["asset"] = asset
    coll.objects.link(e)
    return e


def mesh_ob(name, coll, build, mats, ink=hose.INK_W, smooth=True):
    bm = bmesh.new()
    build(bm)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = smooth
    for m in mats:
        me.materials.append(m)
    ob = OB.new(name, me)
    coll.objects.link(ob)
    if ink:
        hose.outline(ob, ink)
    return ob


def blob(bm, c, r, mi=0, along=None, seg=(18, 12)):
    before = set(bm.faces)
    rot = Matrix.Identity(4)
    if isinstance(along, Matrix):
        rot = along.to_4x4()
    elif along is not None:
        rot = Vector((0, 1, 0)).rotation_difference(Vector(along).normalized()).to_matrix().to_4x4()
    bmesh.ops.create_uvsphere(bm, u_segments=seg[0], v_segments=seg[1], radius=1.0,
                              matrix=Matrix.Translation(Vector(c)) @ rot @ Matrix.Diagonal(Vector((*r, 1))))
    for f in set(bm.faces) - before:
        f.material_index = mi


def box(bm, lo, hi, mi=0):
    before = set(bm.faces)
    c = (Vector(lo) + Vector(hi)) / 2
    d = Vector(hi) - Vector(lo)
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation(c) @ Matrix.Diagonal(Vector((*d, 1))))
    for f in set(bm.faces) - before:
        f.material_index = mi


def quad(bm, corners, mi=0):
    vs = [bm.verts.new(c) for c in corners]
    f = bm.faces.new(vs)
    f.material_index = mi


def cel_tex(name, tone, tone2, kind, scale=1.0, coord="Object"):
    """A cel material with a printed pattern (planks, wallpaper stripes, bricks, grass patches, diamonds)."""
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
    if kind == "bricks":
        tex = t.nodes.new("ShaderNodeTexBrick")
        tex.inputs["Scale"].default_value = 4.0 * scale
        tex.inputs["Color1"].default_value = (0, 0, 0, 1)
        tex.inputs["Color2"].default_value = (0, 0, 0, 1)
        tex.inputs["Mortar"].default_value = (1, 1, 1, 1)
        tex.inputs["Mortar Size"].default_value = 0.025
        bw = t.nodes.new("ShaderNodeRGBToBW")
        t.links.new(tex.outputs["Color"], bw.inputs[0])
        fac = bw.outputs[0]
        t.links.new(tc.outputs[coord], tex.inputs["Vector"])
    elif kind in ("planks", "stripes"):
        tex = t.nodes.new("ShaderNodeTexWave")
        tex.wave_type = "BANDS"
        tex.bands_direction = "X"
        tex.inputs["Scale"].default_value = scale
        gt = t.nodes.new("ShaderNodeMath")
        gt.operation = "GREATER_THAN"
        gt.inputs[1].default_value = 0.82 if kind == "planks" else 0.5
        t.links.new(tc.outputs[coord], tex.inputs["Vector"])
        t.links.new(tex.outputs["Fac"], gt.inputs[0])
        fac = gt.outputs[0]
    elif kind == "patches":
        tex = t.nodes.new("ShaderNodeTexVoronoi")
        tex.inputs["Scale"].default_value = scale
        gt = t.nodes.new("ShaderNodeMath")
        gt.operation = "LESS_THAN"
        gt.inputs[1].default_value = 0.18
        t.links.new(tc.outputs[coord], tex.inputs["Vector"])
        t.links.new(tex.outputs["Distance"], gt.inputs[0])
        fac = gt.outputs[0]
    else:  # diamonds (rug, wallpaper)
        tex = t.nodes.new("ShaderNodeTexChecker")
        tex.inputs["Scale"].default_value = scale
        tex.inputs["Color1"].default_value = (1, 1, 1, 1)
        tex.inputs["Color2"].default_value = (0, 0, 0, 1)
        mp = t.nodes.new("ShaderNodeMapping")
        mp.inputs["Rotation"].default_value = (0, 0, math.radians(45))
        t.links.new(tc.outputs[coord], mp.inputs["Vector"])
        t.links.new(mp.outputs[0], tex.inputs["Vector"])
        fac = tex.outputs["Fac"]
    t.links.new(fac, mix.inputs["Factor"])
    t.links.new(ramp.outputs[0], mix.inputs["A"])
    t.links.new(mix.outputs["Result"], em.inputs["Color"])
    return m


def text_ob(name, coll, body, size, mat, loc, rot=(90, 0, 0), font_path=None, extrude=0.004):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body
    cu.size = size
    cu.align_x, cu.align_y = "CENTER", "CENTER"
    cu.extrude = extrude
    if font_path:
        cu.font = bpy.data.fonts.load(font_path, check_existing=True)
    cu.materials.append(mat)
    ob = OB.new(name, cu)
    ob.location = loc
    ob.rotation_euler = [math.radians(a) for a in rot]
    coll.objects.link(ob)
    return ob


def face(bm, c, size, front=(0, -1, 0), mats=(0, 1), mouth=True):
    """A 1930s cartoon face: two tall white eyes with pie-cut pupils and a smile, on a surface facing 'front'."""
    f = Vector(front).normalized()
    x = f.cross(Vector((0, 0, 1))).normalized()
    up = x.cross(f).normalized()
    c = Vector(c)
    for s in (-1, 1):
        e = c + x * (s * 0.42 * size) + up * (0.25 * size)
        blob(bm, e, (0.26 * size, 0.12 * size, 0.38 * size), mats[0], along=Matrix((x, -f, up)).transposed())
        blob(bm, e + f * (0.1 * size) + x * (-s * 0.04 * size) - up * (0.05 * size), (0.12 * size, 0.06 * size, 0.2 * size),
             mats[1], along=Matrix((x, -f, up)).transposed())
    if mouth:
        for k in range(7):  # the smile: a curve of small black beads
            u = (k - 3) / 3
            blob(bm, c + x * (u * 0.45 * size) + up * (-0.35 * size + 0.18 * size * u * u) + f * 0.04 * size,
                 (0.07 * size, 0.05 * size, 0.06 * size), mats[1])


# ---------------------------------------------------------------- materials
INK, WHITE = cel("set ink", 0.015), cel("set white", 0.96)
M = {
    "floor": cel_tex("sala floor", 0.46, 0.36, "planks", scale=3.0),
    "wall": cel_tex("sala wallpaper", 0.76, 0.66, "stripes", scale=2.2),
    "base": cel("sala skirting", 0.24),
    "brick": cel_tex("sala bricks", 0.4, 0.75, "bricks", scale=1.6),
    "mantel": cel("sala mantel", 0.26),
    "hearth": cel("sala hearth", 0.04),
    "flame": cel("sala flame", 0.95, emit=1),
    "flame2": cel("sala flame core", 0.75, emit=1),
    "rug": cel_tex("sala rug", 0.38, 0.28, "diamonds", scale=3.0),
    "rug_edge": cel("sala rug edge", 0.6),
    "frame": cel("sala frame", 0.2),
    "picture": cel("sala picture", 0.82),
    "table": cel("sala table", 0.3),
    "ground": cel_tex("selva ground", 0.3, 0.24, "patches", scale=0.6),
    "path": cel_tex("selva path", 0.52, 0.45, "patches", scale=1.6),
    "hill1": cel("selva hill far", 0.5),
    "hill2": cel("selva hill near", 0.4),
    "stem": cel("flower stem", 0.38),
    "leaf": cel("flower leaf", 0.5),
    "petal": cel("flower petal", 0.95),
    "fface": cel("flower face", 0.72),
    "black": cel("set black", 0.015),
    "spot": cel("trevas spot", 0.66, shade=0.9),
    "beam": cel("trevas beam", 0.9, emit=1, alpha=0.12),
    "moon": cel("moon", 0.95, emit=1),
    "glass": cel("jar glass", 0.9, emit=1, alpha=0.28),
    "cork": cel("jar cork", 0.42),
    "label": cel("jar label", 0.92),
    "wood": cel_tex("crate wood", 0.5, 0.4, "planks", scale=6.0),
    "stick": cel("trap stick", 0.36),
    "hood": cel("carapuca", 0.22),
    "paper": cel("cig paper", 0.96),
    "ember": cel("cig ember", 0.25),
    "smoke": cel("smoke", 0.9, emit=1, alpha=0.55),
    "book": cel("book cover", 0.28),
    "pages": cel("book pages", 0.92),
    "gold": cel("book gold", 0.8),
    "pipe": cel("pipe wood", 0.3),
}

# ================================================================ SALA: the storyteller's room
sala = fresh("set_sala")
O = SALA
mesh_ob("sala_floor", sala, lambda bm: quad(bm, [O + Vector(v) for v in ((-4.5, -4, 0), (4.5, -4, 0), (4.5, 3, 0), (-4.5, 3, 0))]),
        [M["floor"]], ink=0)
mesh_ob("sala_wall", sala, lambda bm: (quad(bm, [O + Vector(v) for v in ((-4.5, 3, 0), (4.5, 3, 0), (4.5, 3, 4.2), (-4.5, 3, 4.2))]),
                                        box(bm, O + Vector((-4.5, 2.92, 0)), O + Vector((4.5, 3.0, 0.16)), 1)),
        [M["wall"], M["base"]], ink=0)
# The fireplace: a brick chimney breast with an arched opening, a mantel shelf and cartoon flames
fx0 = O + Vector((0.0, 2.55, 0))


def fireplace(bm):
    box(bm, fx0 + Vector((-0.8, -0.05, 0)), fx0 + Vector((-0.42, 0.45, 1.25)), 0)   # left pier
    box(bm, fx0 + Vector((0.42, -0.05, 0)), fx0 + Vector((0.8, 0.45, 1.25)), 0)     # right pier
    box(bm, fx0 + Vector((-0.42, -0.05, 0.92)), fx0 + Vector((0.42, 0.45, 1.25)), 0)  # lintel
    box(bm, fx0 + Vector((-0.42, 0.25, 0)), fx0 + Vector((0.42, 0.45, 0.92)), 2)    # the dark hearth inside
    box(bm, fx0 + Vector((-0.95, -0.18, 1.25)), fx0 + Vector((0.95, 0.45, 1.36)), 1)  # mantel shelf
    box(bm, fx0 + Vector((-0.62, -0.02, 1.36)), fx0 + Vector((0.62, 0.45, 2.9)), 0)  # chimney breast up the wall
    box(bm, fx0 + Vector((-0.95, -0.3, 0)), fx0 + Vector((0.95, -0.05, 0.06)), 1)   # hearth stone


mesh_ob("sala_fireplace", sala, fireplace, [M["brick"], M["mantel"], M["hearth"]], ink=0.01, smooth=False)
for k, (dx, h, w) in enumerate(((-0.2, 0.55, 0.13), (0.0, 0.72, 0.16), (0.2, 0.5, 0.12))):
    fl = mesh_ob(f"sala_flame{k}", sala, lambda bm, dx=dx, h=h, w=w: (
        blob(bm, fx0 + Vector((dx, 0.3, h * 0.42)), (w, w * 0.6, h * 0.5)),
        blob(bm, fx0 + Vector((dx, 0.22, h * 0.32)), (w * 0.55, w * 0.4, h * 0.3), 1)), [M["flame"], M["flame2"]], ink=0.008)
    fl["flame"] = k
    spot(f"sala_flame{k}", fx0 + Vector((dx, 0.3, 0)))
# Picture over the mantel: a framed oval portrait (a pardo silhouette, of course)
pic = fx0 + Vector((0.0, -0.06, 2.15))
mesh_ob("sala_picture", sala, lambda bm: (blob(bm, pic, (0.42, 0.04, 0.5), 0), blob(bm, pic + Vector((0, -0.03, 0)), (0.34, 0.03, 0.42), 1),
                                          blob(bm, pic + Vector((0, -0.05, -0.08)), (0.14, 0.02, 0.17), 0),
                                          blob(bm, pic + Vector((0, -0.05, 0.14)), (0.11, 0.02, 0.14), 0)),
        [M["frame"], M["picture"]], ink=0.008)
mesh_ob("sala_rug", sala, lambda bm: (blob(bm, O + Vector((0, 0.3, 0.004)), (2.1, 1.3, 0.004), 0, seg=(48, 4)),
                                      blob(bm, O + Vector((0, 0.3, 0.002)), (2.25, 1.42, 0.003), 1, seg=(48, 4))),
        [M["rug"], M["rug_edge"]], ink=0)
# Furniture from the library
vovo_chair = inst("cadeira_balanco", sala, O + Vector((-0.74, 0.5, 0)), rz=-12, s=1.1, name="sala_rocking")
eva_chair = inst("poltrona", sala, O + Vector((0.8, 0.55, 0)), rz=14, s=1.1, name="sala_wingchair")


def aim_chair(chair, front):
    """Turns a chair so its seat faces 'front' (flat world direction): its backrest direction is measured from the model,
    because imported chairs come facing any way (the wing chair's back runs along its own X)."""
    bpy.context.view_layer.update()
    back = set_lib.chair_measure(chair)["back"]
    want = -Vector(front).normalized()
    chair.rotation_euler.z += math.atan2(want.y, want.x) - math.atan2(back.y, back.x)
    bpy.context.view_layer.update()
    return math.degrees(chair.rotation_euler.z)


# Both seats face the camera, each turned a little towards the other
print("chairs aimed:", round(aim_chair(vovo_chair, (0.14, -1, 0))), round(aim_chair(eva_chair, (-0.14, -1, 0))))
inst("relogio", sala, O + Vector((1.75, 2.55, 0)), rz=180, s=1.0, name="sala_clock")
tbl = mesh_ob("sala_table", sala, lambda bm: (box(bm, O + Vector((-1.95, 1.9, 0)), O + Vector((-1.45, 2.4, 0.06))),
                                               box(bm, O + Vector((-1.75, 2.1, 0.06)), O + Vector((-1.65, 2.2, 0.62))),
                                               box(bm, O + Vector((-2.0, 1.85, 0.62)), O + Vector((-1.4, 2.45, 0.68)))),
              [M["table"]], ink=0.008, smooth=False)
inst("gramofone", sala, O + Vector((-1.7, 2.15, 0.68)), rz=200, s=1.0, name="sala_gramophone")
inst("radio", sala, O + Vector((-1.15, 2.6, 0)), rz=180, s=1.0, name="sala_radio")
# Faces: the clock looks out from its case, the gramophone's horn has a mouth
mesh_ob("sala_clock_face", sala, lambda bm: face(bm, O + Vector((1.75, 2.3, 1.25)), 0.16), [WHITE, INK], ink=0.005)
spot("sala_vovo_seat", O + Vector((-0.56, 0.42, 0)))
spot("sala_eva_seat", O + Vector((0.64, 0.47, 0)))
spot("sala_center", O + Vector((0, 0.3, 0)))
spot("sala_fire", fx0)
redraw()

# The storybook: two hinged covers and a page block, title on the front
book = fresh("prop_book")


def book_part(name, build, mats):
    return mesh_ob(name, book, build, mats, ink=0.006, smooth=False)


back = book_part("book_back", lambda bm: (box(bm, (-0.0, -0.17, 0), (0.25, 0.17, 0.012), 0),
                                          box(bm, (0.005, -0.16, 0.012), (0.24, 0.16, 0.05), 1)), [M["book"], M["pages"]])
cover = book_part("book_cover", lambda bm: box(bm, (0.0, -0.17, 0), (0.25, 0.17, 0.012), 0), [M["book"]])
cover.parent = back
cover.location = (0, 0, 0.05)
pagel = book_part("book_page_left", lambda bm: box(bm, (0.0, -0.16, 0), (0.24, 0.16, 0.006), 0), [M["pages"]])
pagel.parent = back
pagel.location = (0, 0, 0.05)
pagel.hide_viewport = pagel.hide_render = True
font = os.path.join(set_lib.ROOT, "src", "erva", "fonts", "Limelight-Regular.ttf")
title = text_ob("book_title", book, "PARDÃO\nE A\nERVA", 0.04, M["gold"], (0.125, 0, 0.0135), rot=(0, 0, 90), font_path=font, extrude=0.001)
title.parent = cover
back.location = (-40, 0, 0)  # parked; shots put it on the storyteller's lap

# The long shared pipe
pipe = fresh("prop_pipe")
inst("cachimbo", pipe, (0, 0, 0), s=1.25, name="pipe_model")
pipe_root = OB.new("pipe", None)
pipe.objects.link(pipe_root)
OB["pipe_model"].parent = pipe_root
pipe_root.location = (-40, 2, 0)

# ================================================================ TREVAS: darkness and a spotlight
trevas = fresh("set_trevas")
T = TREVAS
mesh_ob("trevas_spot", trevas, lambda bm: blob(bm, T + Vector((0, 0, 0.003)), (0.8, 0.8, 0.003), seg=(48, 4)), [M["spot"]], ink=0)
beam = mesh_ob("trevas_beam", trevas, lambda bm: bmesh.ops.create_cone(bm, cap_ends=False, segments=40, radius1=0.8, radius2=0.08,
                                                                       depth=7.0, matrix=Matrix.Translation(T + Vector((0, 0, 3.5)))),
               [M["beam"]], ink=0, smooth=True)
for k in range(7):  # pairs of eyes blinking in the dark
    ex = rng.uniform(-1.3, 1.3)
    ez = rng.uniform(0.4, 3.0)
    ey = rng.uniform(2.0, 5.0)
    ob = mesh_ob(f"trevas_eyes{k}", trevas, lambda bm, ex=ex, ey=ey, ez=ez: [
        (blob(bm, T + Vector((ex + s * 0.07, ey, ez)), (0.05, 0.02, 0.075), 0),
         blob(bm, T + Vector((ex + s * 0.07 + 0.012, ey - 0.02, ez - 0.01)), (0.022, 0.01, 0.035), 1)) for s in (-1, 1)],
        [cel("dark eye", 0.95, emit=1), INK], ink=0)
    ob["blink"] = rng.uniform(0, 3)
spot("trevas_center", T)

# ================================================================ SELVA: the jungle garden (Eden)
selva = fresh("set_selva")
S = SELVA
mesh_ob("selva_ground", selva, lambda bm: quad(bm, [S + Vector(v) for v in ((-14, -9, 0), (14, -9, 0), (14, 20, 0), (-14, 20, 0))]),
        [M["ground"]], ink=0)


def path_strip(bm):
    # a winding dirt path across the stage, from the left wings to the right
    pts = [S + Vector((x, 0.6 * math.sin(x * 0.45) - 0.2, 0.004)) for x in [i * 0.5 - 12 for i in range(49)]]
    left, right = [], []
    for i, p in enumerate(pts):
        d = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        n = Vector((-d.y, d.x, 0)) * (0.75 + 0.12 * math.sin(i * 1.7))
        left.append(bm.verts.new(p + n))
        right.append(bm.verts.new(p - n))
    for i in range(len(pts) - 1):
        bm.faces.new((right[i], right[i + 1], left[i + 1], left[i]))


mesh_ob("selva_path", selva, path_strip, [M["path"]], ink=0)
# The painted backdrop: two rows of round hills on a card far behind
mesh_ob("selva_hills", selva, lambda bm: [blob(bm, S + Vector((x, 19 - 0.3 * (k % 2), z)), (r, 0.3, r * 0.6), k % 2, seg=(40, 16))
                                          for k, (x, z, r) in enumerate(((-9, -0.6, 6), (-1, -0.8, 7), (8, -0.5, 6.5),
                                                                         (-5, -1.5, 5), (4, -1.6, 5.5), (12, -1.4, 4)))],
        [M["hill1"], M["hill2"]], ink=0.04)
for k, (x, z, s) in enumerate(((-5, 8.5, 1.6), (3.5, 9.5, 2.0), (9, 8.0, 1.4), (-10, 10, 1.8))):
    inst("nuvem", selva, S + Vector((x, 17, z)), rz=180, s=s, name=f"selva_cloud{k}")["garden"] = 1
# Trees: the striped rubber-hose trees mid-stage, Eden's apple tree, palms and the pack's round trees behind
TOON = ["arvores_toon_0", "arvores_toon_1", "arvores_toon_2", "arvores_toon_3"]
tree_spots = [(-4.2, 3.0), (-2.2, 5.5), (2.6, 3.6), (4.6, 6.0), (-6.5, 6.5), (6.8, 3.2), (0.6, 8.5), (-8.5, 3.5), (8.8, 7.5)]
for k, (x, y) in enumerate(tree_spots):
    t = inst(TOON[k % 4], selva, S + Vector((x, y, 0)), rz=rng.uniform(0, 360), s=rng.uniform(0.95, 1.2), name=f"selva_tree{k}")
    t["sway"] = rng.uniform(0, math.tau)
    t["garden"] = 1
inst("macieira", selva, S + Vector((-1.0, 2.6, 0)), rz=170, s=1.05, name="selva_apple")["garden"] = 1
inst("pe_erva", selva, S + Vector((-0.2, 1.7, 0)), rz=180, s=1.5, name="selva_erva")["garden"] = 1
for k, (x, y, s) in enumerate(((-9.5, 11, 1.1), (9.5, 12, 1.0), (-2.5, 13, 0.9), (5.0, 14, 1.2))):
    inst("palmeira", selva, S + Vector((x, y, 0)), rz=rng.uniform(0, 360), s=s, name=f"selva_palm{k}")["garden"] = 1
for k, (x, y) in enumerate(((-7, 10), (-3.5, 11.5), (1.5, 11), (6.5, 10.5), (11, 9), (-11, 8))):
    inst(f"arvores_pack_{(1, 8, 13, 4, 16, 0)[k]}", selva, S + Vector((x, y, 0)), rz=rng.uniform(0, 360), s=1.4,
         name=f"selva_round{k}")["garden"] = 1
# Ground dressing: bushes, big leaves, mushrooms, rocks, a stump and a fallen log
dress = [("arbusto", -3.0, 1.7, 1.0), ("arbusto", 3.4, 2.0, 1.1), ("arbusto", 7.5, 1.4, 1.0), ("costela_adao", -5.5, 1.2, 1.1),
         ("orelha_elefante", 5.6, 1.0, 1.0), ("cogumelos_0", 1.8, 1.3, 0.9), ("toco", -1.9, 1.3, 0.8), ("tronco_caido", 6.0, 4.6, 1.0),
         ("pedras_0", -6.8, 2.0, 1.0), ("pedras_3", 4.3, 1.1, 0.9), ("pedras_9", -8.4, 1.5, 1.0), ("flores_0", -3.8, 0.9, 0.8),
         ("flores_0", 2.6, 0.95, 0.8), ("margarida", -1.2, 1.0, 1.4), ("margarida", 1.0, 1.1, 1.5), ("flor", 3.1, 1.4, 1.2)]
for k, (a, x, y, s) in enumerate(dress):
    d = inst(a, selva, S + Vector((x, y, 0)), rz=rng.uniform(0, 360), s=s, name=f"selva_dress{k}")
    d["garden"] = 1
# Singing flowers: daisy heads with faces on tall stems, along the path
def flower_head(bm, c, r):
    for k in range(10):
        a = k * math.tau / 10
        d = Vector((math.cos(a), 0, math.sin(a)))
        blob(bm, c + d * (r * 0.95), (r * 0.42, r * 0.08, r * 0.2), 0, along=d)
    blob(bm, c + Vector((0, -0.01, 0)), (r * 0.62, r * 0.2, r * 0.62), 1)
    face(bm, c + Vector((0, -r * 0.2, 0)), r * 0.62, mats=(2, 3))


flowers = fresh("prop_flowers")
for k, (x, y, h) in enumerate(((-1.6, 0.95, 1.15), (0.3, 1.25, 1.3), (1.9, 0.9, 1.05))):
    root = OB.new(f"flower{k}", None)
    flowers.objects.link(root)
    root.location = S + Vector((x, y, 0))
    stem = mesh_ob(f"flower{k}_stem", flowers, lambda bm, h=h: (
        bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.035, radius2=0.025, depth=h,
                              matrix=Matrix.Translation((0, 0, h / 2))),
        blob(bm, (0.12, 0, h * 0.35), (0.14, 0.03, 0.05), 1, along=(1, 0, 0.5)),
        blob(bm, (-0.12, 0, h * 0.5), (0.13, 0.03, 0.05), 1, along=(-1, 0, 0.5))), [M["stem"], M["leaf"]], ink=0.007)
    stem.parent = root
    head = mesh_ob(f"flower{k}_head", flowers, lambda bm: flower_head(bm, Vector((0, 0, 0)), 0.17),
                   [M["petal"], M["fface"], WHITE, INK], ink=0.007)
    head.parent = root
    head.location = (0, 0, h)
    root["flower"] = k
    spot(f"flower{k}", root.location)

# ================================================================ ASSOMBRADA: the spooky jungle, on the same spot
spooky = fresh("set_assombrada")
for k, (x, y) in enumerate(tree_spots[:7]):
    a = ("arvore_assombrada", "arvore_morta", "arvore_retorcida")[k % 3]
    t = inst(a, spooky, S + Vector((x, y, 0)), rz=rng.uniform(0, 360), s=rng.uniform(1.0, 1.25), name=f"spooky_tree{k}")
    t["sway"] = rng.uniform(0, math.tau)
inst("esqueletos", spooky, S + Vector((-3.0, 4.0, 0)), rz=190, s=1.5, name="spooky_skeletons")
inst("esqueletos", spooky, S + Vector((3.5, 5.0, 0)), rz=165, s=1.4, name="spooky_skeletons2")
moon = mesh_ob("spooky_moon", spooky, lambda bm: (blob(bm, S + Vector((1.5, 16, 8.5)), (1.6, 0.3, 1.6), 0, seg=(40, 24)),
                                                  face(bm, S + Vector((1.5, 15.6, 8.5)), 1.1, mats=(1, 2))),
               [M["moon"], WHITE, INK], ink=0.03)
spot("moon", S + Vector((1.5, 16, 8.5)))

# ================================================================ gag props (parked off stage; shots place them)
props = fresh("props")


def park(ob, k):
    ob.location = (-40, 6 + k * 1.5, 0)


# Cigarettes and the joint (the joint is fatter, twisted shut at the tip)
cig = mesh_ob("cigarette", props, lambda bm: (
    bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.012, radius2=0.012, depth=0.12,
                          matrix=Matrix.Translation((0, 0.06, 0)) @ Matrix.Rotation(math.radians(90), 4, "X")),
    blob(bm, (0, 0.12, 0), (0.0125, 0.008, 0.0125), 1)), [M["paper"], M["ember"]], ink=0.004)
park(cig, 0)
cig2 = cig.copy()
cig2.name = "cigarette2"
props.objects.link(cig2)
park(cig2, 1)
joint = mesh_ob("joint", props, lambda bm: (
    bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.012, radius2=0.022, depth=0.15,
                          matrix=Matrix.Translation((0, 0.075, 0)) @ Matrix.Rotation(math.radians(90), 4, "X")),
    blob(bm, (0, 0.155, 0), (0.016, 0.02, 0.016), 0, along=(0, 1, 0)),
    blob(bm, (0, 0.0, 0), (0.0125, 0.006, 0.0125), 1)), [M["paper"], M["ember"]], ink=0.004)
park(joint, 2)
# Signpost: CAMINHO NOVO
sign = fresh("prop_sign", props)
inst("placa", sign, (0, 0, 0), rz=180, s=1.0, name="sign_model")
sign_root = OB.new("sign", None)
sign.objects.link(sign_root)
OB["sign_model"].parent = sign_root
fontb = os.path.join(set_lib.ROOT, "src", "erva", "fonts", "AlfaSlabOne-Regular.ttf")
st = text_ob("sign_text", sign, "CAMINHO\nNOVO  →", 0.12, INK, (0, -0.1, 1.42), font_path=fontb)
st.parent = sign_root
park(sign_root, 3)
# Cash register: NÃO COMPENSA on the pop-up tab
reg = fresh("prop_register", props)
inst("caixa_registradora", reg, (0, 0, 0), rz=180, s=1.3, name="register_model")
reg_root = OB.new("register", None)
reg.objects.link(reg_root)
OB["register_model"].parent = reg_root
tab = mesh_ob("register_tab", reg, lambda bm: box(bm, (-0.32, -0.02, 0.0), (0.32, 0.02, 0.24)), [WHITE], ink=0.006, smooth=False)
tab.parent = reg_root
tab.location = (0, -0.1, 0.62)
tt = text_ob("register_text", reg, "NÃO\nCOMPENSA", 0.075, INK, (0, -0.03, 0.12), font_path=fontb)
tt.parent = tab
park(reg_root, 4)
# The soul jar: glass, cork, label
jar = fresh("prop_jar", props)
jar_root = OB.new("soul_jar", None)  # "jar" is taken: the downloaded jar model brings its own empty by that name
jar.objects.link(jar_root)
glass = mesh_ob("jar_glass", jar, lambda bm: (bmesh.ops.create_cone(bm, cap_ends=True, segments=32, radius1=0.22, radius2=0.22, depth=0.5,
                                                                    matrix=Matrix.Translation((0, 0, 0.25))),
                                              blob(bm, (0, 0, 0.5), (0.22, 0.22, 0.06))), [M["glass"]], ink=0.008)
glass.parent = jar_root
cork = mesh_ob("jar_cork", jar, lambda bm: bmesh.ops.create_cone(bm, cap_ends=True, segments=20, radius1=0.12, radius2=0.14, depth=0.1,
                                                                 matrix=Matrix.Translation((0, 0, 0.58))), [M["cork"]], ink=0.006)
cork.parent = jar_root
lbl = mesh_ob("jar_label", jar, lambda bm: box(bm, (-0.15, -0.235, 0.14), (0.15, -0.225, 0.3)), [M["label"]], ink=0.004, smooth=False)
lbl.parent = jar_root
jt = text_ob("jar_text", jar, "ALMA", 0.085, INK, (0, -0.24, 0.22), font_path=font, extrude=0.001)
jt.parent = jar_root
park(jar_root, 5)
# The box trap (arapuca): an upturned crate propped on a stick, a string running off
trap = fresh("prop_trap", props)
trap_root = OB.new("trap", None)
trap.objects.link(trap_root)


def crate(bm):
    box(bm, (-0.45, -0.45, 0.62), (0.45, 0.45, 0.68))  # top (upturned, so the open side faces down)
    for s in (-1, 1):
        box(bm, (s * 0.45 - 0.03, -0.45, 0.0), (s * 0.45 + 0.03, 0.45, 0.68))
        box(bm, (-0.45, s * 0.45 - 0.03, 0.0), (0.45, s * 0.45 + 0.03, 0.68))


crate_ob = mesh_ob("trap_crate", trap, crate, [M["wood"]], ink=0.01, smooth=False)
crate_ob.parent = trap_root
stick = mesh_ob("trap_stick", trap, lambda bm: bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=0.02, radius2=0.018,
                                                                     depth=0.6, matrix=Matrix.Translation((0, 0, 0.3))),
                [M["stick"]], ink=0.005)
stick.parent = trap_root
park(trap_root, 6)
# The carapuça: a pointed hood
hood = mesh_ob("hood", props, lambda bm: bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=0.2, radius2=0.01, depth=0.55,
                                                               matrix=Matrix.Translation((0, 0, 0.27))), [M["hood"]], ink=0.008)
park(hood, 7)
# The spiral of the new path, flat on the ground
spiral = mesh_ob("spiral", props, lambda bm: [
    blob(bm, (math.cos(a) * (0.15 + a * 0.12), math.sin(a) * (0.15 + a * 0.12), 0.006), (0.09 + a * 0.012, 0.09 + a * 0.012, 0.005),
         seg=(12, 4)) for a in [i * 0.25 for i in range(56)]], [M["path"]], ink=0)
park(spiral, 8)
# Smoke: a pool of puffs and rings the shots move about
smoke = fresh("props_smoke", props)
for k in range(12):
    r = mesh_ob(f"smoke_ring{k}", smoke, lambda bm: [blob(bm, (math.cos(a), math.sin(a), 0), (0.32, 0.32, 0.32), seg=(10, 8))
                                                     for a in [i * math.tau / 14 for i in range(14)]], [M["smoke"]], ink=0)
    r.location = (-40, 20 + k, 0)
for k in range(24):
    p = mesh_ob(f"smoke_puff{k}", smoke, lambda bm: blob(bm, (0, 0, 0), (1, 1, 1), seg=(14, 10)), [M["smoke"]], ink=0)
    p.location = (-40, 35 + k, 0)

# ================================================================ lights
for n in ("key_sun",):
    if n in OB:
        OB[n].data.energy = 3.0
json.dump(stage, open(os.path.join(WORK, "stage.json"), "w"), indent=1)
set_lib.view((SELVA.x, -8, 1.6), yaw=0, pitch=86, dist=4)
bpy.data.orphans_purge(do_recursive=True)  # rebuilds leave the old meshes and materials behind: memory grows otherwise
save()
print("sets built:", [c.name for c in bpy.context.scene.collection.children])
