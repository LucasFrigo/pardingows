# Step 3: the cast, built live in the open window. Re-runnable: it reopens blender/erva/erva_base.blend (saved by s01_setup.py)
# and saves the result as erva.blend.
#   node src/thps/bl.mjs run src/erva/blender/s03_cast.py
# Pardão (P1) gets the rubber-hose kit: noodle arms and legs, four-finger gloves, big shoes, flat cel tones and ink lines.
# Grandpa (VOVO), Eva (EVA), the crew (P2-P4, P2 is Pardjhonson) and the soul (ALMA) are copies of him, each with their
# own pieces; the cobra is built by snake.py. Everyone stands in a lineup at y = LINEUP_Y.
import importlib
import json
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    HERE = os.path.join(os.environ.get("ERVA_ROOT", r"E:\Projetos\pardingows"), "src", "erva", "blender")
sys.path.insert(0, HERE)
import set_lib, hose, snake, poses_toon as PT  # noqa: E402
for mod in (set_lib, hose, snake, PT):
    importlib.reload(mod)
from set_lib import WORK, BLEND, cel, cel_pattern, redraw, save  # noqa: E402

BASE = os.path.join(WORK, "erva_base.blend")
bpy.ops.wm.open_mainfile(filepath=BASE)
bpy.ops.wm.save_as_mainfile(filepath=BLEND)
OB = bpy.data.objects
LINEUP_Y = -40.0
SPACING = 2.2
ORDER = ["P1", "VOVO", "EVA", "P2", "P3", "P4", "ALMA"]

# ---------------------------------------------------------------- P1: names, tones
root = OB["P1"]
for o in [root] + list(root.children_recursive):
    if o.name == "Armature":
        o.name = "P1_arm"
    elif o.name == "body" and o.type == "MESH":
        o.name = "P1_torso"  # "P1_body" is the rig's own empty
    elif not o.name.startswith("P1"):
        o.name = "P1_" + o.name
if "P2" in OB:
    for o in [OB["P2"]] + list(OB["P2"].children_recursive):
        bpy.data.objects.remove(o, do_unlink=True)
bpy.data.orphans_purge(do_recursive=True)

root.location = (0, LINEUP_Y, 0.035)
root.rotation_euler = (0, 0, 0)
# The source rig's body empty is turned (about 31 deg round, 12 deg tipped): straightened before anything is fitted to it,
# or the pieces placed in world space (shoes, trousers) end up askew once a pose straightens the body
OB["P1_body"].rotation_euler = (0, 0, 0)
arm = OB["P1_arm"]
cast = bpy.data.collections["rigs"]
cast.name = "cast"
for o in list(bpy.data.collections["smurf"].objects):
    bpy.data.collections["smurf"].objects.unlink(o)
    if o.name not in cast.objects:
        cast.objects.link(o)
bpy.data.collections.remove(bpy.data.collections["smurf"])

# Skin is a mid grey in sepia, the white cap and trousers near paper white, the gold chain light grey
WHITE, SKIN, GOLD = 0.9, 0.42, 0.74
TONES = {"hat": WHITE, "upper legs": WHITE, "lower legs": WHITE, "tail": WHITE, "heels": WHITE, "toes": WHITE, "hands": WHITE,
         "head": SKIN, "ears": SKIN, "nose": SKIN, "torso": SKIN, "upper arms": SKIN, "lower arms": SKIN}
MATS = {"gold": cel("gold", GOLD), "gold dark": cel("gold dark", GOLD * 0.62), "shades black": cel("shades black", 0.015),
        "shades shine": cel("shades shine", 0.97, emit=1)}
done = set()
for o in root.children_recursive:
    if o.type != "MESH" or o.data.name in done:
        continue
    done.add(o.data.name)
    base = o.name[3:].split(".")[0]
    for i, m in enumerate(o.data.materials):
        if m and m.name in MATS:
            o.data.materials[i] = MATS[m.name]
        elif base in TONES:
            o.data.materials[i] = cel(f"cel {base}", TONES[base])
HIDE = ("upper arms", "lower arms", "hands", "upper legs", "lower legs", "heels", "toes")
for o in root.children_recursive:
    if o.type == "MESH" and o.name[3:].split(".")[0] in HIDE:
        o.hide_viewport = o.hide_render = True
        o["hose_hidden"] = True

hose.lengthen_arms(arm, 1.3)
for pb in arm.pose.bones:
    # assigned, not pb.matrix_basis.identity(): that only resets a copy, which left the source rig's feet turned 31 deg
    # when the shoes were fitted, so the shoes sat askew once a pose straightened the feet
    pb.matrix_basis = Matrix.Identity(4)
bpy.context.view_layer.update()


def wbox(ob):
    pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return Vector([min(p[i] for p in pts) for i in range(3)]), Vector([max(p[i] for p in pts) for i in range(3)])


def surface_y(ob, x, z, default):
    """World y where a ray from the front (-Y) at (x, z) first meets ob, so pieces can sit on the face."""
    mw = ob.matrix_world
    inv = mw.inverted()
    o = inv @ Vector((x, mw.translation.y - 50, z))
    d = (inv.to_3x3() @ Vector((0, 1, 0))).normalized()
    hit, loc, _n, _i = ob.ray_cast(o, d)
    return (mw @ loc).y if hit else default


def curve_ob(name, splines, depth, mat):
    """A bevelled curve of several splines; each spline is a list of (point, radius), smooth through its points."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_mode = "ROUND"
    cu.bevel_depth = depth
    cu.bevel_resolution = 4
    cu.resolution_u = 10
    cu.use_fill_caps = True
    for pts in splines:
        sp = cu.splines.new("BEZIER")
        sp.bezier_points.add(len(pts) - 1)
        for bp, (c, r) in zip(sp.bezier_points, pts):
            bp.co = c
            bp.radius = r
            bp.handle_left_type = bp.handle_right_type = "AUTO"
    cu.materials.append(mat)
    return cu


def blobs_mesh(name, parts, mats):
    """parts: (material index, centre, radii[, along]) ellipsoids, in world metres."""
    bm = bmesh.new()
    for part in parts:
        mi, c, r = part[:3]
        along = part[3] if len(part) > 3 else None
        before = set(bm.faces)
        rot = Matrix.Identity(4)
        if isinstance(along, Matrix):  # an explicit frame: its columns are the ellipsoid's X, Y, Z axes
            rot = along.to_4x4()
        elif along is not None:
            rot = Vector((0, 1, 0)).rotation_difference(Vector(along).normalized()).to_matrix().to_4x4()
        bmesh.ops.create_uvsphere(bm, u_segments=18, v_segments=12, radius=1.0,
                                  matrix=Matrix.Translation(Vector(c)) @ rot @ Matrix.Diagonal(Vector((*r, 1))))
        for f in set(bm.faces) - before:
            f.material_index = mi
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    for m in mats:
        me.materials.append(m)
    return me


def put(name, data, bone, prefix="P1", ink=True, width=hose.INK_W):
    """Links a world-built piece and parents it to a bone of a rig, keeping where it is."""
    a = OB[prefix + "_arm"]
    ob = bpy.data.objects.new(name, data)
    cast.objects.link(ob)
    pb = a.pose.bones[bone]
    hose.attach(ob, a, bone, (a.matrix_world @ pb.matrix).inverted())
    if ink:
        hose.outline(ob, width)
    return ob


# ---------------------------------------------------------------- P1's hose kit: gloves, shoes, trousers
white = cel("cel glove", 0.96)
for side, bone in (("R", "Bone.004"), ("L", "Bone.011")):
    u, w = hose.bone_axes(arm, bone)
    for shape, me in hose.glove_meshes(u, w, white, None).items():
        ob = bpy.data.objects.new(f"P1_glove{side}_{shape}", me)
        cast.objects.link(ob)
        hose.attach(ob, arm, bone, Matrix.Scale(1.35, 4))
        ob["glove_of"], ob["glove_shape"] = f"P1{side}", shape
        hose.outline(ob)

shoe_me = hose.shoe_mesh(cel("cel shoe", 0.1), None)
for side, bone in (("R", "Bone.007"), ("L", "Bone.014")):
    pb = arm.pose.bones[bone]
    ankle = arm.matrix_world @ pb.head
    want = Matrix.Translation((ankle.x, ankle.y + 0.02, 0.0)) @ Matrix.Diagonal((0.27, 0.27, 0.27, 1))
    ob = bpy.data.objects.new(f"P1_shoe{side}", shoe_me)
    cast.objects.link(ob)
    hose.attach(ob, arm, bone, (arm.matrix_world @ pb.matrix).inverted() @ want)
    hose.outline(ob)

# White trousers: the hips are one rounded piece on the root bone, the legs are the white hoses
hipR = arm.matrix_world @ arm.pose.bones["Bone.005"].head
hipL = arm.matrix_world @ arm.pose.bones["Bone.012"].head
mid = (hipR + hipL) / 2
half = (hipR - hipL).length / 2
pants = cel("cel pants", WHITE)
put("P1_pelvis", blobs_mesh("pelvis", [(0, mid + Vector((0, 0.0, 0.07)), (half + hose.LEG_R + 0.03, 0.155, 0.17))], [pants]), "Bone")

skin_tube = cel("cel hose skin", SKIN)


def tubes(prefix, leg_mat, arm_mat=skin_tube, legs=True):
    for limb in hose.LIMBS:
        is_arm = limb.startswith("arm")
        ob = hose.tube(f"{prefix}_{limb}", hose.ARM_R if is_arm else hose.LEG_R, arm_mat if is_arm else leg_mat, cast)
        if not is_arm and not legs:
            ob.hide_viewport = ob.hide_render = True
        hose.outline(ob)


tubes("P1", pants)
for o in [root] + list(root.children_recursive):
    if o.type in ("MESH", "CURVE") and not o.get("hose_hidden"):
        hose.outline(o)

GROUND = OB["P1_body"].location.z
PT.pose_pardo("P1", PT.STAND, GROUND)
bpy.context.view_layer.update()
hose.update("P1")
redraw()

# ---------------------------------------------------------------- the copies


def copy_tree(prefix):
    """P1's whole hierarchy, renamed. Meshes stay shared until a variant changes one."""
    mapping = {}
    src = OB["P1"]
    for o in [src] + list(src.children_recursive):
        n = o.copy()
        n.name = prefix + o.name[2:]
        cast.objects.link(n)
        mapping[o] = n
        for k in ("glove_of",):
            if k in o:
                n[k] = prefix + o[k][2:]
    for o, n in mapping.items():
        if o.parent in mapping:
            n.parent = mapping[o.parent]
            n.parent_type, n.parent_bone = o.parent_type, o.parent_bone
            n.matrix_parent_inverse = o.matrix_parent_inverse.copy()
    return mapping


def own(ob, mat_map):
    """Gives a copied piece its own mesh with some materials swapped (by name, or '*' for all but ink)."""
    ob.data = ob.data.copy()
    for i, m in enumerate(ob.data.materials):
        if not m or m.name == "ink":
            continue
        if m.name in mat_map:
            ob.data.materials[i] = mat_map[m.name]
        elif "*" in mat_map:
            ob.data.materials[i] = mat_map["*"]


for i, prefix in enumerate(ORDER[1:], 1):
    copy_tree(prefix)
    OB[prefix].location = (i * SPACING, LINEUP_Y, 0.035)
bpy.context.view_layer.update()

# Grandpa: a big white beard and moustache
nb0, nb1 = wbox(OB["VOVO_nose"])
hb0, hb1 = wbox(OB["VOVO_head"])
hw = hb1.x - hb0.x
nc = (nb0 + nb1) / 2
beard = cel("cel beard", 0.95)
# Placed against the face found by raycasts, so beard, moustache and nose all touch
face_y = surface_y(OB["VOVO_head"], nc.x, nb0.z - 0.06, nc.y + 0.1)
chin_y = surface_y(OB["VOVO_head"], nc.x, nb0.z - 0.2, face_y)
under_nose_y = surface_y(OB["VOVO_nose"], nc.x, nb0.z + 0.03, nc.y)
mo_y = (under_nose_y + face_y) / 2
put("VOVO_beard", blobs_mesh("beard", [
    (0, (nc.x, face_y + 0.02, nb0.z - 0.15), (0.23 * hw, 0.13 * hw, 0.21 * hw)),
    (0, (nc.x, chin_y + 0.04, nb0.z - 0.33), (0.15 * hw, 0.1 * hw, 0.13 * hw)),
    (0, (nc.x - 0.085, mo_y, nb0.z - 0.01), (0.06 * hw, 0.14 * hw, 0.062 * hw), (-1, 0.3, -0.5)),
    (0, (nc.x + 0.085, mo_y, nb0.z - 0.01), (0.06 * hw, 0.14 * hw, 0.062 * hw), (1, 0.3, -0.5)),
    (0, (nc.x, mo_y + 0.01, nb0.z + 0.0), (0.07 * hw, 0.06 * hw, 0.05 * hw)),
], [beard]), "Bone.001", "VOVO")
# (no spectacles: over his shades they read as floating rings, removed at the step-3 review)

# Eva: the leaf dress, a flower on her cap, no shades but big eyes with lashes, long hair, pearls instead of the chain
for n in ("EVA_chain", "EVA_medallion", "EVA_pelvis", "EVA_shades", "EVA_ears", "EVA_tail"):  # ears and tail under her hair
    OB[n].hide_viewport = OB[n].hide_render = True
    OB[n]["hose_hidden"] = True
bb0, bb1 = wbox(OB["EVA_torso"])
bc = (bb0 + bb1) / 2
leaf = cel("cel leaf", 0.5)
leaf_dark = cel("cel leaf vein", 0.28)


def dress(bm):
    top, bot = bb1.z - 0.16, 0.3
    rt, rb = (bb1.x - bb0.x) * 0.52, (bb1.x - bb0.x) * 0.95
    ring = 32
    rows = 7
    verts = []
    for r in range(rows + 1):
        t = r / rows
        z = top + (bot - top) * t
        rad = rt + (rb - rt) * t ** 0.8
        row = []
        for j in range(ring):
            a = j / ring * math.tau
            scallop = 0.075 * abs(math.sin(a * 5)) if r == rows else 0.0
            row.append(bm.verts.new((bc.x + rad * math.cos(a), bc.y + rad * 0.85 * math.sin(a), z + scallop)))
        verts.append(row)
    for r in range(rows):
        for j in range(ring):
            bm.faces.new((verts[r][j], verts[r][(j + 1) % ring], verts[r + 1][(j + 1) % ring], verts[r + 1][j]))


me = bpy.data.meshes.new("dress")
bm = bmesh.new()
dress(bm)
bm.normal_update()
for f in bm.faces:  # normals out, away from the body axis, so the ink shell sits outside
    c = f.calc_center_median()
    if f.normal.dot(c - Vector((bc.x, bc.y, c.z))) < 0:
        f.normal_flip()
bm.to_mesh(me)
bm.free()
me.materials.append(leaf)
me.materials.append(leaf_dark)
for i, p in enumerate(me.polygons):
    p.use_smooth = True
    p.material_index = 0 if i < 32 * 7 else 1
d = put("EVA_dress", me, "Bone.016", "EVA")
# an open shell gets no ink line, so the dress gets a little thickness first
th = d.modifiers.new("thick", "SOLIDIFY")
th.thickness, th.offset = 0.015, 0.0
d.modifiers.move(len(d.modifiers) - 1, 0)
# ---- Eva's face, hair, flower and pearls. Everything is fitted to her head and cap by raycasts: the cap's rim runs at
# a different height in every direction (down to the nape behind, at the temples on the sides, over the eyes in front).
head_ob, cap_ob = OB["EVA_head"], OB["EVA_hat"]
eh0, eh1 = wbox(head_ob)
ehc = (eh0 + eh1) / 2
en0, en1 = wbox(OB["EVA_nose"])
enc = (en0 + en1) / 2
_hp = [head_ob.matrix_world @ v.co for v in head_ob.data.vertices]
axis = sum(_hp, Vector()) / len(_hp)  # the head's centre: rays go out horizontally from its vertical axis

# She wears her cap pushed back a little, Smurfette-style, so her fringe shows under the brim
pivot = Vector((axis.x, axis.y + 0.28, axis.z - 0.05))  # the back of her head
cap_ob.matrix_world = (Matrix.Translation(pivot) @ Matrix.Rotation(math.radians(-11), 4, "X") @ Matrix.Translation(-pivot)
                       @ cap_ob.matrix_world)
bpy.context.view_layer.update()


def ray_out(ob, z, deg):
    """Distance from the head's axis out to ob's surface, horizontally at height z, towards deg (0 = back, 180 = front)."""
    mw = ob.matrix_world
    inv = mw.inverted()
    o = Vector((axis.x, axis.y, z))
    a = math.radians(deg)
    hit, loc, _n, _i = ob.ray_cast(inv @ o, (inv.to_3x3() @ Vector((math.sin(a), math.cos(a), 0.0))).normalized())
    return ((mw @ loc) - o).length if hit else None


def front_hit(ob, x, z):
    """Where a ray from the front at (x, z) meets ob, and the surface's outward normal there (world)."""
    mw = ob.matrix_world
    inv = mw.inverted()
    hit, loc, n, _i = ob.ray_cast(inv @ Vector((x, axis.y - 5.0, z)), (inv.to_3x3() @ Vector((0, 1, 0))).normalized())
    if not hit:
        return None, None
    return mw @ loc, (inv.transposed().to_3x3() @ n).normalized()


def visible_rim(deg):
    """How low the cap covers the head in this direction. The cap's edge tucks into the head at the sides, so this is
    where the head starts to show, not the cap's lowest point."""
    z = eh1.z
    while z > eh0.z:
        h, c = ray_out(head_ob, z, deg), ray_out(cap_ob, z, deg)
        if h is not None and (c is None or c < h - 0.004):
            return z + 0.01
        z -= 0.01
    return eh0.z


def brim_z(x):
    """The bottom edge of the cap's front brim at this x: scanning up from the nose, the first height where a ray from
    the front meets the front of the cap (below it, the ray passes under the brim)."""
    z = en0.z
    while z < eh1.z + 0.3:
        hp, _n = front_hit(cap_ob, x, z)
        if hp is not None and hp.y < axis.y - 0.05:
            return z
        z += 0.005
    return eh1.z


def forehead_y(x, z):
    hp, _n = front_hit(head_ob, x, z)
    return None if hp is None else hp.y


# The eyes fit between the nose (which overlaps their lower inner corners, the cartoon way) and the brim
EYE_RX, EYE_RZ = 0.058, 0.07
eye_parts, lashes = [], []
eye_top = 0.0
for sx in (-1, 1):
    ex = enc.x + sx * 0.112
    ez = min(en1.z - 0.03, brim_z(ex) - EYE_RZ - 0.025)
    eye_top = max(eye_top, ez + EYE_RZ)
    ey = surface_y(head_ob, ex, ez, en1.y) + 0.018
    eye_parts += [(0, (ex, ey, ez), (EYE_RX, 0.032, EYE_RZ)),
                  (1, (ex - sx * 0.006, ey - 0.027, ez - 0.008), (0.031, 0.015, 0.045)),
                  (0, (ex - sx * 0.016, ey - 0.04, ez + 0.012), (0.008, 0.005, 0.012))]
    for k, phi_deg in enumerate((40, 63, 86)):  # three tapered lashes curling up out of the outer top corner
        phi = math.radians(phi_deg)
        base = Vector((ex + sx * EYE_RX * math.sin(phi) * 0.96, ey - 0.022, ez + EYE_RZ * math.cos(phi) * 0.96))
        out = Vector((sx * math.sin(phi) / EYE_RX, 0.0, math.cos(phi) / EYE_RZ)).normalized()
        L = 0.036 - 0.005 * k
        mid = base + (out + Vector((0, 0, 0.3))).normalized() * L * 0.55 + Vector((0, -0.004, 0))
        tip = base + (out * 0.55 + Vector((0, 0, 0.85))).normalized() * L + Vector((sx * 0.006, -0.007, 0))
        lashes.append([(base, 1.0), (mid, 0.62), (tip, 0.12)])
put("EVA_eyes", blobs_mesh("eva eyes", eye_parts, [cel("cel eye white", 0.97), cel("cel pupil", 0.015)]), "Bone.001", "EVA", width=0.006)
put("EVA_lashes", curve_ob("eva lashes", lashes, 0.0062, cel("cel lash", 0.015)), "Bone.001", "EVA", ink=False)

# The hair: metaball puffs that melt into one soft mass, turned into a mesh so it takes the ink line. Each column round
# the sides and back starts right at the cap's visible rim, already full, so it puffs out from under the hat; it follows
# the head out to its widest, then hangs straight down in soft waves to a hem that flips out.
hair_m = cel("cel hair", 0.64, shade=0.82)
mb = bpy.data.metaballs.new("eva hair")
mb.resolution = mb.render_resolution = 0.02
mb.threshold = 0.6
mob = bpy.data.objects.new("eva_hair_mb", mb)
cast.objects.link(mob)
HAIR_R = 0.08  # puff size
SPAN = 114  # round the sides and back; the front 2 x 66 degrees is her face


def sweep(deg, t):
    """Long hair drapes back behind the shoulders as it falls: the sides drift round towards the back."""
    s_ = min(1.0, max(0.0, (t - 0.15) / 0.55))
    return deg * (1.0 - 0.4 * s_ * s_ * (3 - 2 * s_))


def hem_of(deg):
    """Down to the waist, a little shorter beside the face, with locks of different lengths."""
    return 0.5 + 0.15 * (abs(deg) / SPAN) ** 1.5 - 0.05 * abs(math.sin(math.radians(deg) * 2.6))


rims, hems = {}, {}
for deg in range(-SPAN, SPAN + 1, 6):
    top = visible_rim(deg) + 0.005
    hem = hem_of(deg)
    rims[deg], hems[deg] = top, hem
    r_in, z = 0.0, top
    while z >= hem:
        t = (top - z) / max(top - hem, 1e-3)
        sd = sweep(deg, t)
        out = Vector((math.sin(math.radians(sd)), math.cos(math.radians(sd)), 0.0))
        r_in = max(r_in, ray_out(head_ob, z, sd) or 0.0)
        g = min(1.0, (top - z) / 0.035)  # full almost at once: the hair puffs out from under the cap's edge
        R = HAIR_R * (1.0 + 0.2 * t) * (0.7 + 0.3 * g)
        wave = 0.013 * math.sin((top - z) / 0.17 * math.tau + deg * 0.045) * min(1.0, t * 4)
        rc = r_in + R * 0.5 * g + 0.045 * t * t + wave
        e = mb.elements.new()
        e.co = Vector((axis.x, axis.y, z)) + out * rc
        e.radius = R
        z -= 0.025
    sd = sweep(deg, 1.0)
    out = Vector((math.sin(math.radians(sd)), math.cos(math.radians(sd)), 0.0))
    e = mb.elements.new()  # the ends flip out
    e.co = Vector((axis.x, axis.y, hem + 0.03)) + out * (r_in + HAIR_R * 0.55 + 0.075)
    e.radius = HAIR_R * 0.7
print("eva hair starts at the cap's rim:", {k: round(v, 3) for k, v in rims.items() if k % 30 == 0})

# The fringe: one band of bangs on the forehead, from just under the brim to just above the eyes, its lower edge
# scalloped into six locks (each lock's tip dips lowest at its middle). It lies close on the forehead, behind the brim.
FR = 0.031
fringe, x = 0, enc.x - 0.19
lock_w = 0.38 / 6
while x <= enc.x + 0.19 + 1e-6:
    lock = (x - (enc.x - 0.19)) / lock_w
    z0 = brim_z(x) - 0.01
    z1 = eye_top + 0.012 + FR * 0.5 + 0.02 * (1 + math.cos(math.tau * lock)) / 2
    z = z0
    while z >= z1:
        fy = forehead_y(x, z)
        if fy is not None:  # off the side of her forehead: no puff floating in the air
            e = mb.elements.new()
            e.co = (x, fy - FR * 0.35, z)
            e.radius = FR
            fringe += 1
        z -= 0.012
    x += 0.02
print("eva fringe puffs:", fringe, "brim at the eyes:", round(brim_z(enc.x + 0.112), 3), "eye top:", round(eye_top, 3))
bpy.context.view_layer.update()
hme = bpy.data.meshes.new_from_object(mob.evaluated_get(bpy.context.evaluated_depsgraph_get()))
bpy.data.objects.remove(mob, do_unlink=True)
bpy.data.metaballs.remove(mb)
hme.materials.clear()
hme.materials.append(hair_m)
for poly in hme.polygons:
    poly.use_smooth = True
# Ink strands drawn on the hair's outer surface (found by raycasts against it), so it reads as hair from every side,
# and short ones parting the fringe into its locks
from mathutils.bvhtree import BVHTree  # noqa: E402
hair_bvh = BVHTree.FromPolygons([v.co.copy() for v in hme.vertices], [list(p.vertices) for p in hme.polygons])
strands = []
for deg in range(-112, 113, 16):
    top, hem = rims[min(rims, key=lambda d: abs(d - deg))], hems[min(hems, key=lambda d: abs(d - deg))]
    pts = []
    for k in range(8):
        z = top - 0.06 - (top - hem - 0.12) * k / 7
        t = (top - z) / max(top - hem, 1e-3)
        sd = math.radians(sweep(deg, t))
        out = Vector((math.sin(sd), math.cos(sd), 0.0))
        hit = hair_bvh.ray_cast(Vector((axis.x, axis.y, z)) + out * 1.5, -out)
        if hit[0] is not None:
            pts.append((hit[0] + out * 0.004, 1.0 if 0 < k < 7 else 0.4))
    if len(pts) >= 4:
        strands.append(pts)
for k in range(1, 6):  # the fringe's partings
    fx = enc.x - 0.19 + k * lock_w
    pts = []
    for z in (brim_z(fx) - 0.02, eye_top + 0.04):
        hit = hair_bvh.ray_cast(Vector((fx, axis.y - 2.0, z)), Vector((0, 1, 0)))
        if hit[0] is not None:
            pts.append((hit[0] + Vector((0, -0.004, 0)), 0.8))
    if len(pts) == 2:
        strands.append(pts)
put("EVA_hair_shell", hme, "Bone.001", "EVA", width=0.009)
put("EVA_hair_strands", curve_ob("eva strands", strands, 0.0045, cel("cel strand", 0.2)), "Bone.001", "EVA", ink=False)

# The flower: six petals and a centre lying flat on the cap's surface (its normal from a raycast), up on the side
fp, fn = front_hit(cap_ob, enc.x + 0.2, 1.5)
if fp is None:
    fp, fn = Vector((enc.x + 0.2, eh0.y, 1.5)), Vector((0.3, -1.0, 0.2)).normalized()
t1 = Vector((0, 0, 1)).cross(fn).normalized()
t2 = fn.cross(t1).normalized()
fl = []
for k in range(6):
    th = math.radians(15 + 60 * k)
    dv = t1 * math.cos(th) + t2 * math.sin(th)
    fl.append((0, fp + fn * 0.009 + dv * 0.039, (0.02, 0.034, 0.008), Matrix((dv.cross(fn), dv, fn)).transposed()))
fl.append((1, fp + fn * 0.017, (0.022, 0.022, 0.012), Matrix((t1, t2, fn)).transposed()))
put("EVA_flower", blobs_mesh("flower", fl, [cel("cel petal", 0.97), cel("cel flower eye", 0.45)]), "Bone.001", "EVA", width=0.005)

# Pearls: small, in a U lying on her chest below the chin (right under the chin they read as teeth)
neck = Vector((bc.x, bc.y, bb1.z - 0.05))
pearls = []
for k in range(22):
    a = k * math.tau / 22
    front = max(0.0, -math.sin(a))
    x, y, z = neck.x + 0.15 * math.cos(a), neck.y + 0.13 * math.sin(a), neck.z - 0.09 * front ** 1.2
    if front > 0.2:
        y = min(y, surface_y(OB["EVA_torso"], x, z, y) - 0.014)
    pearls.append((0, (x, y, z), (0.021, 0.021, 0.021)))
put("EVA_pearls", blobs_mesh("pearls", pearls, [cel("cel pearl", 0.95)]), "Bone.016", "EVA", width=0.005)

# The crew: patterns where colour can't tell them apart (stripes, dots, checks on the cap and trousers)
CREW = {"P2": "stripes", "P3": "dots", "P4": "checks"}
for prefix, kind in CREW.items():
    cap = cel_pattern(f"{prefix} cap", WHITE, kind)
    trousers = cel_pattern(f"{prefix} trousers", WHITE, kind, scale=2.2)
    own(OB[f"{prefix}_hat"], {"*": cap})
    own(OB[f"{prefix}_pelvis"], {"*": trousers})
# Pardjhonson's name-tag sticker
b0, b1 = wbox(OB["P2_torso"])
tag_c = Vector(((b0.x + b1.x) / 2 + 0.05, b0.y + 0.02, (b0.z + b1.z) / 2 + 0.05))
plate = put("P2_tag", blobs_mesh("tag", [(0, tag_c, (0.15, 0.012, 0.055))], [cel("cel tag", 0.97)]), "Bone.016", "P2", width=0.005)
txt = bpy.data.curves.new("P2_tag_text", "FONT")
txt.body = "PARDJHONSON"
txt.size = 0.042
txt.align_x, txt.align_y = "CENTER", "CENTER"
txt.extrude = 0.002
txt.materials.append(cel("cel tag ink", 0.02))
t_ob = bpy.data.objects.new("P2_tag_text", txt)
cast.objects.link(t_ob)
t_ob.matrix_world = Matrix.Translation(tag_c + Vector((0, -0.016, 0))) @ Matrix.Rotation(math.radians(90), 4, "X")
pb = OB["P2_arm"].pose.bones["Bone.016"]
hose.attach(t_ob, OB["P2_arm"], "Bone.016", (OB["P2_arm"].matrix_world @ pb.matrix).inverted() @ t_ob.matrix_world)

# The soul: an opaque white here, so its parts merge into one shape; the render fades it as a whole (a see-through
# material would show every overlap inside it). No feet: one long tapered ghost's tail instead.
ghost = cel("cel ghost", 0.95, shade=0.82)
for o in [OB["ALMA"]] + list(OB["ALMA"].children_recursive):
    if o.type == "MESH":
        own(o, {"*": ghost})
for n in ("ALMA_shoeR", "ALMA_shoeL", "ALMA_pelvis"):
    OB[n].hide_viewport = OB[n].hide_render = True
    OB[n]["hose_hidden"] = True
hipR = OB["ALMA_arm"].matrix_world @ OB["ALMA_arm"].pose.bones["Bone.005"].head
hipL = OB["ALMA_arm"].matrix_world @ OB["ALMA_arm"].pose.bones["Bone.012"].head
gm = (hipR + hipL) / 2
put("ALMA_tail", curve_ob("ghost tail", [[
    (gm + Vector((0, 0, 0.1)), 1.0), (gm + Vector((0.01, 0.02, -0.1)), 0.85), (gm + Vector((0.06, 0.06, -0.27)), 0.6),
    (gm + Vector((0.16, 0.08, -0.37)), 0.33), (gm + Vector((0.27, 0.05, -0.36)), 0.12)]], 0.21, ghost), "Bone", "ALMA")
soul = bpy.data.collections.new("soul")  # its own collection: the render fades it in a separate view layer
bpy.context.scene.collection.children.link(soul)

for prefix in ORDER[1:]:
    leg = {"EVA": skin_tube}.get(prefix, pants)
    arms = ghost if prefix == "ALMA" else skin_tube
    tubes(prefix, ghost if prefix == "ALMA" else leg, arm_mat=arms, legs=prefix != "ALMA")
for o in list(bpy.data.objects):
    if o.name == "ALMA" or o.name.startswith("ALMA_"):
        for c in list(o.users_collection):
            c.objects.unlink(o)
        soul.objects.link(o)

# ---------------------------------------------------------------- the cobra
snake.build(cast, cel, hose.outline)
cx = len(ORDER) * SPACING
snake.pose(**snake.stand((cx, LINEUP_Y, 0), (0, -1, 0)))

# ---------------------------------------------------------------- stand everyone up, light, save
for prefix in ORDER:
    PT.pose_pardo(prefix, {**PT.STAND, "spine": (14, 0, 0), "head": (-10, 0, 0)} if prefix == "VOVO" else PT.STAND, GROUND)
bpy.context.view_layer.update()
for prefix in ORDER:
    hose.update(prefix)

sun = bpy.data.objects.get("key_sun") or bpy.data.objects.new("key_sun", bpy.data.lights.new("key_sun", "SUN"))
if sun.name not in bpy.context.scene.collection.objects:
    bpy.context.scene.collection.objects.link(sun)
sun.data.energy = 3.0
sun.rotation_euler = (math.radians(50), 0, math.radians(-35))
w = bpy.context.scene.world or bpy.data.worlds.new("World")
bpy.context.scene.world = w
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.5, 0.42, 1)
bpy.context.scene.render.engine = "BLENDER_EEVEE"
bpy.context.scene.view_settings.view_transform = "Standard"

json.dump({"pardo_ground_body_z": GROUND, "lineup_y": LINEUP_Y, "spacing": SPACING, "order": ORDER + ["COBRA"]},
          open(os.path.join(WORK, "cast.json"), "w"), indent=1)
set_lib.view(((len(ORDER)) * SPACING / 2, LINEUP_Y, 0.9), yaw=0, pitch=86, dist=13)
save()
print("cast built:", ORDER + ["COBRA"], "ground", round(GROUND, 3))
