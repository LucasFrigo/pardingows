# Step 3: the cast, built in the open window.
#   P1-P4  Smurf Pardo and three recoloured copies (P2 is Pardjhonson). The skate-era foot IK goes, so legs take poses like arms.
#   M1-M3  Mildingows: the Thug LP import rigged here (it came with no skeleton), dressed as hobos with a jacket shell and a beard.
#          They share one T-pose rest, so one pose library (poses_brawl.H_*) fits all three.
#   MB     the crouching Beggar import as a static extra.
#   JUMENTO the cartoon donkey, decimated, one rigid mesh under a root.
# Everyone faces -Y with "R" on the +X side, feet on z = 0 at their root. The step-2 imports are only copied, never changed,
# so this script can be re-run: it deletes what it made last time (tagged "cast_made") first.
#   node src/thps/bl.mjs run src/pardao/blender/s03_cast.py
import bpy, bmesh, json, math, os, sys
from mathutils import Matrix, Vector
try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    HERE = os.path.join(os.environ.get("PARDAO_ROOT", r"E:\Projetos\pardingows"), "src", "pardao", "blender")
sys.path.insert(0, HERE)
import importlib, set_lib
importlib.reload(set_lib)
from set_lib import ROOT, WORK, redraw
sys.path.insert(0, os.path.join(ROOT, "src", "thps", "blender"))
import lib
importlib.reload(lib)
from lib import BONES, Mesh, make_mat, srgb

OB = bpy.data.objects
SMURF_SCALE = 0.23
LINEUP_Y = -40.0

# ---- Clear the last run
for ob in [o for o in OB if o.get("cast_made")]:
    OB.remove(ob, do_unlink=True)
for d in (bpy.data.meshes, bpy.data.armatures, bpy.data.materials):
    for x in [x for x in d if x.get("cast_made") and x.users == 0]:
        d.remove(x)
cast = bpy.data.collections.get("cast") or bpy.data.collections.new("cast")
if cast.name not in bpy.context.scene.collection.children:
    bpy.context.scene.collection.children.link(cast)
rigs = bpy.data.collections["rigs"]


def made(x):
    x["cast_made"] = True
    return x


def new_ob(name, data, coll=cast):
    ob = made(OB.new(name, data))
    coll.objects.link(ob)
    return ob


def tinted(m, rgb, name):
    """A copy of a textured material with a colour multiplied over its texture (white cloth takes the colour)."""
    t = m.copy()
    t.name = name
    made(t)
    nt = t.node_tree
    bsdf = next(n for n in nt.nodes if n.type in ("BSDF_PRINCIPLED", "BSDF_DIFFUSE"))
    sock = bsdf.inputs["Base Color" if bsdf.type == "BSDF_PRINCIPLED" else "Color"]
    src = sock.links[0].from_socket
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = 1.0
    mix.inputs[7].default_value = (*srgb(rgb), 1)  # B colour
    nt.links.new(src, mix.inputs[6])  # A colour
    nt.links.new(mix.outputs[2], sock)
    return t


# ---- P1-P4
for arm in (OB["Armature"], OB["P2_arm"]):
    for pb in arm.pose.bones:
        for c in list(pb.constraints):
            pb.constraints.remove(c)
        pb.matrix_basis.identity()
for ob in list(OB):
    if ob.type == "EMPTY" and ob.name.startswith(tuple(f"{p}_{k}" for p in ("P1", "P2") for k in ("ankle", "stance", "heel", "toe"))):
        OB.remove(ob, do_unlink=True)

# Feet on the ground: the body offset that puts the lowest sole vertex at z = 0 with the root at the origin, in smurf units
P1 = OB["P1"]
P1.location, P1.rotation_euler = (0, 0, 0), (0, 0, 0)
OB["P1_body"].location = (0, 0, 0)
OB["P1_body"].rotation_euler = (0, 0, 0)
bpy.context.view_layer.update()
pardo_parts = [o for o in OB["Armature"].children if o.type == "MESH"]
low = min((o.matrix_world @ v.co).z for o in pardo_parts for v in o.data.vertices)
PARDO_GROUND = round(-low / SMURF_SCALE, 4)
top = max((o.matrix_world @ v.co).z for o in pardo_parts for v in o.data.vertices) - low

PLAYERS = {"P1": None, "P2": "d8262c", "P3": "2a62d8", "P4": "2fa84a"}  # cap and trousers; P1 keeps the classic white
CLOTH = ("hat", "upper legs", "upper legs.001", "lower legs", "lower legs.001")


def copy_tree(src_root, prefix):
    """Copies a player's whole hierarchy (root, body, armature, rigid parts). Meshes are shared until recoloured."""
    mapping = {}
    for o in [src_root] + list(src_root.children_recursive):
        n = o.copy()
        n.name = o.name.replace("P2", prefix, 1)
        made(n)
        rigs.objects.link(n)
        mapping[o] = n
    for o, n in mapping.items():
        if o.parent in mapping:
            n.parent = mapping[o.parent]
            n.parent_type, n.parent_bone = o.parent_type, o.parent_bone
            n.matrix_parent_inverse = o.matrix_parent_inverse.copy()
    return mapping


for prefix in ("P3", "P4"):
    copy_tree(OB["P2"], prefix)
tint_cache = {}
for prefix, rgb in PLAYERS.items():
    arm = OB["Armature" if prefix == "P1" else prefix + "_arm"]
    for o in arm.children:
        base = o.name if prefix == "P1" else o.name.split("_", 1)[1]
        if base not in CLOTH or not rgb:
            continue
        # Always tint from P1's untouched piece, so a re-run never tints an already tinted copy
        o.data = made(o.data.copy())
        for i, m in enumerate(OB[base].data.materials):
            key = (m.name, prefix)
            if key not in tint_cache:
                tint_cache[key] = tinted(m, rgb, f"{prefix} {m.name}")
            o.data.materials[i] = tint_cache[key]
    root = OB[prefix]
    root.scale = (SMURF_SCALE,) * 3
    OB[prefix + "_body"].location = (0, 0, PARDO_GROUND)
    OB[prefix + "_body"].rotation_euler = (0, 0, 0)
    root.location = (list(PLAYERS).index(prefix) * 1.3, LINEUP_Y, 0)
    root.rotation_euler = (0, 0, 0)
redraw()

# Pardjhonson's handheld mic, on P2's right hand, hidden unless a shot shows it
MIC = make_mat("mic preto", "1a1a1e")
MIC_HEAD = make_mat("mic grade", "9aa0a8")
arm2 = OB["P2_arm"]
hb = arm2.data.bones[BONES["handR"]]
m = Mesh()
c = hb.tail_local
m.box((c.x, c.y - 0.05, c.z + 0.1), (0.07, 0.07, 0.32), 0)
m.box((c.x, c.y - 0.05, c.z + 0.5), (0.13, 0.13, 0.13), 1)
mic = m.build("P2_mic", [MIC, MIC_HEAD], None, rigs)
made(mic)
mic.parent = arm2
mic.parent_type, mic.parent_bone = "BONE", BONES["handR"]
bpy.context.view_layer.update()
mic.matrix_world = arm2.matrix_world.copy()
mic.hide_render = mic.hide_viewport = True

# ---- Mildingows: rig the Thug LP mesh
thug = next(o for o in OB if o.get("asset") == "thug_lp" and o.type == "MESH")
me = made(thug.data.copy())
me.transform(thug.matrix_world)
pts = [v.co.copy() for v in me.vertices]
lo = Vector([min(p[i] for p in pts) for i in range(3)])
hi = Vector([max(p[i] for p in pts) for i in range(3)])
H = 1.78
me.transform(Matrix.Scale(H / (hi.z - lo.z), 4) @ Matrix.Translation(Vector((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z))))
pts = [v.co.copy() for v in me.vertices]
for p in me.polygons:
    p.use_smooth = False


def centroid(sel, fallback):
    return sum(sel, Vector()) / len(sel) if sel else Vector(fallback)


def leg_joint(z, s):
    sel = [p for p in pts if abs(p.z - z) < 0.025 and 0.02 < s * p.x < 0.3]
    c = centroid(sel, (s * 0.12, 0, z))
    return Vector((c.x, c.y, z))


def near(q, s, r=0.05, xmin=0.2):
    sel = [p for p in pts if (p - q).length < r and s * p.x > xmin]
    return centroid(sel, q)


J = {}
for s, side in ((1, "Left"), (-1, "Right")):  # Mixamo names: "Left" is the character's left, the +X side here
    sh = centroid([p for p in pts if 1.38 < p.z < 1.46 and 0.14 < s * p.x < 0.24], (s * 0.18, 0, 1.42))
    sh = Vector((s * 0.18, sh.y, 1.42))
    tip = max(pts, key=lambda p: s * p.x)
    elbow = near(sh.lerp(tip, 0.45), s)
    wrist = near(sh.lerp(tip, 0.80), s, 0.04, 0.3)
    J[side] = dict(shoulder=sh, elbow=elbow, wrist=wrist, tip=tip, hip=leg_joint(0.92, s), knee=leg_joint(0.50, s), ankle=leg_joint(0.12, s))

ad = made(bpy.data.armatures.new("M_rig"))
ad.display_type = "STICK"
marm = new_ob("M1_arm", ad)
bpy.context.view_layer.objects.active = marm
for o in bpy.context.selected_objects:
    o.select_set(False)
marm.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
eb = ad.edit_bones


def bone(name, head, tail, parent=None, connect=False):
    b = eb.new(name)
    b.head, b.tail = Vector(head), Vector(tail)
    if parent:
        b.parent = eb[parent]
        b.use_connect = connect
    return b


yc = centroid([p for p in pts if 1.0 < p.z < 1.3 and abs(p.x) < 0.15], (0, 0, 0)).y
bone("Hips", (0, yc, 0.95), (0, yc, 1.05))
bone("Spine", (0, yc, 1.05), (0, yc, 1.20), "Hips", True)
bone("Spine1", (0, yc, 1.20), (0, yc, 1.38), "Spine", True)
neck_y = centroid([p for p in pts if 1.48 < p.z < 1.54 and abs(p.x) < 0.06], (0, yc, 0)).y
bone("Neck", (0, neck_y, 1.46), (0, neck_y, 1.55), "Spine1")
bone("Head", (0, neck_y, 1.55), (0, neck_y, 1.78), "Neck", True)
for side, j in J.items():
    s = 1 if side == "Left" else -1
    bone(f"{side}Shoulder", (s * 0.04, yc, 1.41), j["shoulder"], "Spine1")
    bone(f"{side}Arm", j["shoulder"], j["elbow"], f"{side}Shoulder", True)
    bone(f"{side}ForeArm", j["elbow"], j["wrist"], f"{side}Arm", True)
    bone(f"{side}Hand", j["wrist"], j["tip"], f"{side}ForeArm", True)
    bone(f"{side}UpLeg", j["hip"], j["knee"], "Hips")
    bone(f"{side}Leg", j["knee"], j["ankle"], f"{side}UpLeg", True)
    a = j["ankle"]
    bone(f"{side}Foot", a, (a.x, a.y - 0.11, 0.03), f"{side}Leg", True)
    bone(f"{side}ToeBase", (a.x, a.y - 0.11, 0.03), (a.x, a.y - 0.17, 0.02), f"{side}Foot", True)
bpy.ops.object.mode_set(mode="OBJECT")

skin = new_ob("M1_skin", me)
for o in bpy.context.selected_objects:
    o.select_set(False)
skin.select_set(True)
marm.select_set(True)
bpy.context.view_layer.objects.active = marm
bpy.ops.object.parent_set(type="ARMATURE_AUTO")
used = {e.group for v in me.vertices for e in v.groups if e.weight > 0.01}
empty_groups = [g.name for g in skin.vertex_groups if g.index not in used]
weighted = sum(1 for v in me.vertices if any(e.weight > 0.01 for e in v.groups))
print(f"auto weights: {weighted}/{len(me.vertices)} vertices weighted, empty groups: {empty_groups}")
if weighted < len(me.vertices) * 0.95:
    # Bone heat failed somewhere: fall back to each vertex following its nearest bone segment
    print("bone heat incomplete, using nearest-segment weights")
    for g in list(skin.vertex_groups):
        skin.vertex_groups.remove(g)
    segs = [(b.name, b.head_local, b.tail_local) for b in ad.bones]
    groups = {n: skin.vertex_groups.new(name=n) for n, _, _ in segs}

    def dist(p, a, b):
        ab = b - a
        t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
        return (a + ab * t - p).length

    for v in me.vertices:
        d = sorted((dist(v.co, a, b), n) for n, a, b in segs)
        w0 = 1.0 / max(d[0][0], 1e-4)
        w1 = 1.0 / max(d[1][0], 1e-4) if d[1][0] < d[0][0] * 1.25 else 0.0
        groups[d[0][1]].add([v.index], w0 / (w0 + w1), "REPLACE")
        if w1:
            groups[d[1][1]].add([v.index], w1 / (w0 + w1), "REPLACE")


def freeze_pose(arm, mesh_ob):
    """Makes the current pose the new rest pose."""
    bpy.context.view_layer.update()
    ev = mesh_ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
    tmp = ev.to_mesh()
    coords = [v.co.copy() for v in tmp.vertices]
    ev.to_mesh_clear()
    for v, co in zip(mesh_ob.data.vertices, coords):
        v.co = co
    for o in bpy.context.selected_objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="POSE")
    bpy.ops.pose.armature_apply(selected=False)
    bpy.ops.object.mode_set(mode="OBJECT")


# T pose: arms straight out along X, the rest every H_* pose is written against
for name, x in (("LeftArm", 1), ("LeftForeArm", 1), ("RightArm", -1), ("RightForeArm", -1)):
    bpy.context.view_layer.update()
    pb = marm.pose.bones[name]
    q = (pb.tail - pb.head).normalized().rotation_difference(Vector((x, 0, 0)))
    mx = pb.matrix.copy()
    n = q.to_matrix().to_4x4() @ mx
    n.translation = mx.translation
    pb.matrix = n
freeze_pose(marm, skin)
redraw()

# Jacket: the body's own torso, arms and hips pushed out along the normals, so it inherits the weights and bends with him
JACKETS = {"M1": "5a4632", "M2": "4d5534", "M3": "5c5a58"}
BEARDS = {"M1": "9e978c", "M2": "3a2a1e", "M3": "a2501e"}
COAT_GROUPS = {"Hips", "Spine", "Spine1", "LeftShoulder", "RightShoulder", "LeftArm", "RightArm", "LeftForeArm", "RightForeArm", "LeftUpLeg", "RightUpLeg"}
idx_name = {g.index: g.name for g in skin.vertex_groups}


def top_group(v):
    return idx_name.get(max(v.groups, key=lambda e: e.weight).group) if v.groups else None


coat_v = {v.index for v in skin.data.vertices if top_group(v) in COAT_GROUPS and v.co.z >= 0.80}
# Beard: the front of the jaw and chin, from just under the nose tip (the head's most forward vertex) down to the throat
nose = min((v for v in skin.data.vertices if top_group(v) == "Head" and abs(v.co.x) < 0.02), key=lambda v: v.co.y).co.copy()
beard_v = {v.index for v in skin.data.vertices if top_group(v) in ("Head", "Neck") and nose.z - 0.13 < v.co.z < nose.z - 0.018
           and v.co.y < neck_y and abs(v.co.x) < 0.085}
print("nose tip", tuple(round(x, 3) for x in nose), "beard vertices", len(beard_v))


def shell(name, keep, offset):
    """A copy of the skin keeping only the given vertices, welded and pushed out along its normals. Weights come along."""
    sm = made(skin.data.copy())
    sm.name = name
    bm = bmesh.new()
    bm.from_mesh(sm)
    bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in keep], context="VERTS")
    # The thug mesh is split along its UV seams: weld them first, or pushing out along the normals opens cracks there
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0005)
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * offset
    bm.to_mesh(sm)
    bm.free()
    for p in sm.polygons:
        p.use_smooth = True
    sm.materials.clear()
    return sm


jme = shell("M_jacket", coat_v, 0.034)
jme.materials.append(made(make_mat("jaqueta", JACKETS["M1"])))
bme_ = shell("M_beard", beard_v, 0.012)
bme_.materials.append(made(make_mat("barba", BEARDS["M1"])))

# This model's arms and torso don't meet at the shoulder, so a gap opens there when an arm drops. The skin's own texture is
# painted in the jacket (and beard) colour under the shells, so whatever shows through a gap is cloth, not tattoos.
import numpy as np
skin_mat = skin.data.materials[0]
src_img = next(n for n in skin_mat.node_tree.nodes if n.type == "TEX_IMAGE").image
TW_, TH_ = src_img.size
src_px = np.empty(TW_ * TH_ * 4, np.float32)
src_img.pixels.foreach_get(src_px)
src_px = src_px.reshape(TH_, TW_, 4)
uv = skin.data.uv_layers.active.data


def uv_mask(vset):
    """Texture pixels covered by the faces whose vertices are all in vset, grown by 2 px."""
    mask = np.zeros((TH_, TW_), bool)
    for p in skin.data.polygons:
        if not all(i in vset for i in p.vertices):
            continue
        q = [Vector((uv[l].uv.x * TW_, uv[l].uv.y * TH_)) for l in p.loop_indices]
        for k in range(1, len(q) - 1):
            a, b, c = q[0], q[k], q[k + 1]
            x0, x1 = int(max(0, min(a.x, b.x, c.x) - 1)), int(min(TW_ - 1, max(a.x, b.x, c.x) + 1))
            y0, y1 = int(max(0, min(a.y, b.y, c.y) - 1)), int(min(TH_ - 1, max(a.y, b.y, c.y) + 1))
            d = (b.y - c.y) * (a.x - c.x) + (c.x - b.x) * (a.y - c.y)
            if x1 < x0 or y1 < y0 or abs(d) < 1e-9:
                continue
            gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            l1 = ((b.y - c.y) * (gx - c.x) + (c.x - b.x) * (gy - c.y)) / d
            l2 = ((c.y - a.y) * (gx - c.x) + (a.x - c.x) * (gy - c.y)) / d
            mask[y0:y1 + 1, x0:x1 + 1] |= (l1 >= -0.02) & (l2 >= -0.02) & (1 - l1 - l2 >= -0.02)
    for _ in range(2):  # bleed past the island edges so filtering never samples the old colours
        g = mask.copy()
        g[1:] |= mask[:-1]
        g[:-1] |= mask[1:]
        g[:, 1:] |= mask[:, :-1]
        g[:, :-1] |= mask[:, 1:]
        mask = g
    return mask


coat_mask = uv_mask(coat_v)
noise = np.random.default_rng(7).uniform(0.82, 1.08, (TH_, TW_, 1)).astype(np.float32)


def skin_variant(name):
    """The thug texture with the jacket and beard areas painted, saved as a PNG beside the project, in a material of its own."""
    px = src_px.copy()
    for mask, hexcol, shade in ((coat_mask, JACKETS[name], 0.8),):  # the beard shell covers its own area; painting it smeared onto the nose
        col = np.array([int(hexcol[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32) * shade  # byte image pixels are sRGB values
        px[mask, :3] = np.broadcast_to(col * noise, (TH_, TW_, 3))[mask]
    img = bpy.data.images.get(f"{name} pele") or bpy.data.images.new(f"{name} pele", TW_, TH_)
    if tuple(img.size) != (TW_, TH_):
        img.scale(TW_, TH_)
    img.pixels.foreach_set(px.ravel())
    img.filepath_raw = os.path.join(WORK, "textures", f"{name}_pele.png")
    img.file_format = "PNG"
    img.save()
    m = made(skin_mat.copy())
    m.name = f"pele {name}"
    next(n for n in m.node_tree.nodes if n.type == "TEX_IMAGE").image = img
    return m


jacket = new_ob("M1_jacket", jme)
beard = new_ob("M1_beard", bme_)
skin.parent = marm
for o in (jacket, beard):
    o.parent = marm
    o.modifiers.new("rig", "ARMATURE").object = marm
for o in (skin, jacket, beard):
    o.matrix_parent_inverse = Matrix.Identity(4)

mroot = new_ob("M1", None)
mroot.empty_display_size = 0.4
marm.parent = mroot
H_BONES = {"hips": "Hips", "spine": "Spine1", "spine0": "Spine", "neck": "Neck", "head": "Head",
           "armR": "LeftArm", "foreR": "LeftForeArm", "handR": "LeftHand", "armL": "RightArm", "foreL": "RightForeArm", "handL": "RightHand",
           "thighR": "LeftUpLeg", "shinR": "LeftLeg", "footR": "LeftFoot", "thighL": "RightUpLeg", "shinL": "RightLeg", "footL": "RightFoot"}

# M2 and M3: their own armature objects (own poses) sharing the rig, skin and jacket meshes. Colours are per object.
for k, name in enumerate(("M1", "M2", "M3")):
    if name == "M1":
        root, arm_o, sk, jk, bd = mroot, marm, skin, jacket, beard
    else:
        root = new_ob(name, None)
        root.empty_display_size = 0.4
        arm_o = new_ob(name + "_arm", ad)
        arm_o.parent = root
        sk = new_ob(name + "_skin", skin.data)
        jk = new_ob(name + "_jacket", jme)
        bd = new_ob(name + "_beard", bme_)
        for o in (sk, jk, bd):
            o.parent = arm_o
            o.matrix_parent_inverse = Matrix.Identity(4)
            o.modifiers.new("rig", "ARMATURE").object = arm_o
    for o, mat in ((jk, make_mat(f"jaqueta {name}", JACKETS[name])), (bd, make_mat(f"barba {name}", BEARDS[name])), (sk, skin_variant(name))):
        o.material_slots[0].link = "OBJECT"
        o.material_slots[0].material = made(mat)
    root.location = (5.6 + k * 1.2, LINEUP_Y, 0)
redraw()

# ---- MB: the begging extra, frozen as one mesh, turned from facing -X to facing -Y
beg = next(o for o in OB if o.get("asset") == "mendigo_capuz" and o.type == "MESH")
bme = made(beg.data.copy())
bme.transform(beg.matrix_world)
bp = [v.co for v in bme.vertices]
blo = Vector([min(p[i] for p in bp) for i in range(3)])
bhi = Vector([max(p[i] for p in bp) for i in range(3)])
bme.transform(Matrix.Rotation(math.radians(90), 4, "Z") @ Matrix.Translation(Vector((-(blo.x + bhi.x) / 2, -(blo.y + bhi.y) / 2, -blo.z))))
mb = new_ob("MB", None)
mb_mesh = new_ob("MB_mesh", bme)
mb_mesh.parent = mb
mb.location = (9.6, LINEUP_Y, 0)

# ---- JUMENTO: decimated to a PS2 boss budget, turned from facing +X to facing -Y
don = next(o for o in OB if o.get("asset") == "jumento" and o.type == "MESH")
dme = made(don.data.copy())
dme.transform(don.matrix_world)
dp = [v.co for v in dme.vertices]
dlo = Vector([min(p[i] for p in dp) for i in range(3)])
dhi = Vector([max(p[i] for p in dp) for i in range(3)])
dme.transform(Matrix.Rotation(math.radians(-90), 4, "Z") @ Matrix.Translation(Vector((-(dlo.x + dhi.x) / 2, -(dlo.y + dhi.y) / 2, -dlo.z))))
jroot = new_ob("JUMENTO", None)
jmesh = new_ob("JUMENTO_mesh", dme)
jmesh.parent = jroot
dec = jmesh.modifiers.new("decimate", "DECIMATE")
dec.ratio = 0.25
for o in bpy.context.selected_objects:
    o.select_set(False)
bpy.context.view_layer.objects.active = jmesh
jmesh.select_set(True)
bpy.ops.object.modifier_apply(modifier="decimate")
for p in jmesh.data.polygons:
    p.use_smooth = True
jroot.location = (11.6, LINEUP_Y, 0)

data = {
    "_": "Written by s03_cast.py. Lengths in metres unless noted.",
    "smurf_scale": SMURF_SCALE, "pardo_ground_body_z": PARDO_GROUND, "pardo_height": round(top, 3),
    "players": {p: (c or "ffffff") for p, c in PLAYERS.items()},
    "mildingows": {"names": ["M1", "M2", "M3"], "height": H, "bones": H_BONES, "jackets": JACKETS, "beards": BEARDS},
    "jumento_polys": len(jmesh.data.polygons),
}
json.dump(data, open(os.path.join(WORK, "cast.json"), "w", encoding="utf8"), indent=1)

# Show the lineup in the open window
if not bpy.app.background:
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            r3 = area.spaces[0].region_3d
            r3.view_location = (6.0, LINEUP_Y, 0.9)
            r3.view_distance = 9.0
            r3.view_rotation = Vector((0, -1, 0.15)).normalized().to_track_quat("Z", "Y")
set_lib.save()
print(json.dumps(data, indent=1))
