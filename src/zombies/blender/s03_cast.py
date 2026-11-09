# Step 3: the cast. Pardo gets a tactical vest and patch. Berg is the second rig in a suit. Rigged zombies are baked to Z up, facing -Y, feet on z = 0, in a T pose,
# so one pose library fits every skeleton. Needs a fresh import: re-running s02 + s03 together is safe.
import bpy, json, math, os, sys, importlib
from mathutils import Matrix, Vector
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "thps", "blender"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "planeta", "blender"))
import lib, build, set_lib
importlib.reload(lib); importlib.reload(build); importlib.reload(set_lib)
from lib import BONES, Mesh, empty, make_mat, srgb
from build import attach, shell
from set_lib import FAR, TEXTURES, WORK, parts, tex_mat

OB = bpy.data.objects
coll = bpy.data.collections["rigs"]
ARM1, ARM2 = OB["Armature"], OB["P2_arm"]

# The two old foot rigs hold constraints this video never uses
for arm in (ARM1, ARM2):
    for pb in arm.pose.bones:
        for c in list(pb.constraints):
            pb.constraints.remove(c)
for ob in list(OB):
    if ob.type == "EMPTY" and ob.name.startswith(("P1_ankle", "P2_ankle", "P1_stance", "P2_stance", "P1_heel", "P2_heel", "P1_toe", "P2_toe")):
        OB.remove(ob, do_unlink=True)
for p in ("P1", "P2"):
    OB[p + "_body"].location = (0, 0, 0)
    OB[p].location = (0, 0, 0)
bpy.context.view_layer.update()


def arm_box(ob, arm):
    """Bounding box of a rigid piece in armature space. Rest pose assumed."""
    inv = arm.matrix_world.inverted()
    pts = [inv @ (ob.matrix_world @ v.co) for v in ob.data.vertices]
    return Vector(min(p[i] for p in pts) for i in range(3)), Vector(max(p[i] for p in pts) for i in range(3)), pts


# ---- Pardo's vest: the torso's own shape, slightly bigger, in dark cloth. Nothing to line up, and it bends with him.
VEST = make_mat("colete", "27322c")
STRAP = make_mat("colete tira", "161c19")
POCKET = make_mat("colete bolso", "39463c")
body = OB["body"]
lo, hi, pts = arm_box(body, ARM1)
centre = (lo + hi) / 2
inv = ARM1.matrix_world.inverted()
vest = body.copy()
vest.data = body.data.copy()
vest.name = "P1_colete"
coll.objects.link(vest)
for v in vest.data.vertices:
    v.co = v.co * 1.0
to_arm = inv @ body.matrix_world
from_arm = to_arm.inverted()
for v in vest.data.vertices:
    p = to_arm @ v.co
    p = centre + Vector(((p.x - centre.x) * 1.09, (p.y - centre.y) * 1.09, (p.z - centre.z) * 1.0))
    v.co = from_arm @ p
vest.data.materials.clear()
vest.data.materials.append(VEST)

# The spine leans, so the chest plate and back lettering lie on its axis
sp = ARM1.data.bones[BONES["spine"]]
up = (sp.tail_local - sp.head_local).normalized()
right = Vector((1, 0, 0))
front = up.cross(right).normalized()
if front.y > 0:
    front = -front
mid = (sp.head_local + sp.tail_local) / 2
reach_f = max((p - mid).dot(front) for p in pts) * 1.09 + 0.012
reach_b = max((p - mid).dot(-front) for p in pts) * 1.09 + 0.012


def plate(name, c, w, h, normal, mat, top=None, bone=None):
    """A flat textured quad facing along normal, its top edge towards top."""
    top = top or up
    x = top.cross(normal).normalized()
    a, b = c - x * w / 2, c + x * w / 2
    v = [a - top * h / 2, b - top * h / 2, b + top * h / 2, a + top * h / 2]
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(p) for p in v], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name="UVMap")
    for l, q in zip(uv.data, ((0, 0), (1, 0), (1, 1), (0, 1))):
        l.uv = q
    me.materials.append(mat)
    ob = OB.new(name, me)
    coll.objects.link(ob)
    return attach(ob, ARM1, bone or BONES["spine"])


# The chain and medallion fill his chest, so the lettering goes large across the back and the badge on both shoulders
plate("P1_costas", mid - front * reach_b - up * 0.1, 1.02, 0.4, -front, tex_mat("costas", "back.png"))  # above his tail, which would hide the middle letters
patch = tex_mat("patch", "patch.png")
for obname, alias, side in (("upper arms.001", "armR", 1), ("upper arms", "armL", -1)):
    bn = ARM1.data.bones[BONES[alias]]
    axis = (bn.tail_local - bn.head_local).normalized()
    centre_a = (bn.head_local + bn.tail_local) / 2
    n = Vector((side, 0, 0))
    n = (n - axis * n.dot(axis)).normalized()
    _, _, arm_pts = arm_box(OB[obname], ARM1)
    reach = max((q - centre_a).dot(n) for q in arm_pts) + 0.012
    plate(f"P1_patch_{alias}", centre_a + n * reach, 0.5, 0.25, n, patch, top=-axis, bone=BONES[alias])

m = Mesh()
for side in (-1, 1):
    # Pouches at the sides of the waist
    c = mid + front * (reach_f - 0.2) - up * 0.42 + right * side * 0.5
    m.box(tuple(c), (0.12, 0.08, 0.14), 0)
    # Shoulder straps over the collar
    c = mid + up * 0.56 + right * side * 0.28
    m.box(tuple(c), (0.1, 0.4, 0.05), 1)
pouches = attach(m.build("P1_bolsos", [POCKET, STRAP], None, coll), ARM1, BONES["spine"])


# ---- Berg, the body in the cold open: a dark suit and a small lizard head. Only ever seen lying down and half hidden.
SUIT = make_mat("berg terno", "23283c")
SHOE = make_mat("berg sapato", "101014")
LIZARD = make_mat("berg pele", "3f8f78")
SHIRT = make_mat("berg camisa", "c8c4b8")
TIE = make_mat("berg gravata", "9c1e24")
EYE = make_mat("berg olho", "e8e4d8")
BLOOD = make_mat("sangue", "6a0c0c")
WEAR = {"P2_torso": SUIT, "P2_upper arms": SUIT, "P2_upper arms.001": SUIT, "P2_lower arms": SUIT, "P2_lower arms.001": SUIT, "P2_hands": LIZARD, "P2_hands.001": LIZARD,
        "P2_upper legs": SUIT, "P2_upper legs.001": SUIT, "P2_lower legs": SUIT, "P2_lower legs.001": SUIT, "P2_heels": SHOE, "P2_heels.001": SHOE, "P2_toes": SHOE, "P2_toes.001": SHOE,
        "P2_head": LIZARD, "P2_tail": LIZARD}
for n in ("P2_hat", "P2_ears", "P2_nose", "P2_shades", "P2_chain", "P2_medallion"):
    OB.remove(OB[n], do_unlink=True)
for n, mat in WEAR.items():
    ob = OB[n]
    ob.data = ob.data.copy()
    ob.data.materials.clear()
    ob.data.materials.append(mat)
blo, bhi, _ = arm_box(OB["P2_head"], ARM2)
bc = (blo + bhi) / 2
m = Mesh()
m.box((bc.x, blo.y - 0.34, bc.z - 0.22), (0.62, 0.5, 0.34), 0)  # snout
for side in (-1, 1):
    m.box((bc.x + side * 0.46, blo.y + 0.08, bc.z + 0.82), (0.26, 0.18, 0.2), 1)
m.box((bc.x, blo.y - 0.3, bc.z - 0.66), (0.4, 0.3, 0.1), 2)  # a smear on the chin
attach(m.build("P2_cara", [LIZARD, EYE, BLOOD], None, coll), ARM2, BONES["head"])
tlo, thi, _ = arm_box(OB["P2_torso"], ARM2)
m = Mesh()
m.box(tuple(mid + front * (reach_f - 0.06) + up * 0.1), (0.2, 0.05, 0.42), 0)
m.box(tuple(mid + front * (reach_f - 0.02) + up * 0.1), (0.07, 0.05, 0.36), 1)
attach(m.build("P2_camisa", [SHIRT, TIE], None, coll), ARM2, BONES["spine"])
OB["P2_tail"].scale = [s * 1.3 for s in OB["P2_tail"].scale]


# ---- Baking the imported rigs, as in Missão
def aliases(prefix, l="Left", r="Right", arm="Arm", fore="ForeArm", thigh="UpLeg", shin="Leg", foot="Foot", toe="ToeBase"):
    return {"hips": prefix + "Hips", "spine": prefix + "Spine1", "neck": prefix + "Neck_", "head": prefix + "Head_",
            "armR": f"{prefix}{l}{arm}_", "foreR": f"{prefix}{l}{fore}_", "armL": f"{prefix}{r}{arm}_", "foreL": f"{prefix}{r}{fore}_",
            "thighR": f"{prefix}{l}{thigh}_", "shinR": f"{prefix}{l}{shin}_", "thighL": f"{prefix}{r}{thigh}_", "shinL": f"{prefix}{r}{shin}_",
            "footR": f"{prefix}{l}{foot}_", "toeR": f"{prefix}{l}{toe}_"}


MIXAMO = aliases("mixamorig:")
BIPED = {"hips": "Bip01 Pelvis", "spine": "Bip01 Spine1", "neck": "Bip01 Neck", "head": "Bip01 Head_",
         "armR": "Bip01 L UpperArm", "foreR": "Bip01 L Forearm", "armL": "Bip01 R UpperArm", "foreL": "Bip01 R Forearm",
         "thighR": "Bip01 L Thigh", "shinR": "Bip01 L Calf", "thighL": "Bip01 R Thigh", "shinL": "Bip01 R Calf",
         "footR": "Bip01 L Foot", "toeR": "Bip01 L Toe0_"}


def full_name(arm, prefix):
    return next(b.name for b in arm.data.bones if b.name.startswith(prefix))


def freeze_pose(arm, skin):
    """Makes the current pose the new rest pose."""
    bpy.context.view_layer.update()
    ev = skin.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    coords = [v.co.copy() for v in me.vertices]
    ev.to_mesh_clear()
    for v, co in zip(skin.data.vertices, coords):
        v.co = co
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="POSE")
    bpy.ops.pose.armature_apply(selected=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    arm.select_set(False)


def t_pose(arm, skin, names):
    """Straightens every arm along X and makes that the rest pose, so one pose library fits every skeleton."""
    for alias, x in (("armR", 1), ("foreR", 1), ("armL", -1), ("foreL", -1)):
        bpy.context.view_layer.update()
        pb = arm.pose.bones[names[alias]]
        # Bone tails from glTF don't follow the limb, the next joint does
        q = (pb.children[0].head - pb.head).normalized().rotation_difference(Vector((x, 0, 0)))
        mx = pb.matrix.copy()
        n = q.to_matrix().to_4x4() @ mx
        n.translation = mx.translation
        pb.matrix = n
    freeze_pose(arm, skin)


def rig(asset, name, height, alias_map, keep_pose=False):
    """Bakes one rigged import. Returns the armature, its skin and the alias map with full bone names."""
    arm = parts(asset, "ARMATURE")[0]
    meshes = parts(asset)
    skin = max(meshes, key=lambda o: len(o.data.polygons))
    arm.animation_data_clear()
    if keep_pose:
        freeze_pose(arm, skin)
    for pb in arm.pose.bones:
        pb.matrix_basis.identity()
    bpy.context.view_layer.update()
    mw_skin, mw_arm = skin.matrix_world.copy(), arm.matrix_world.copy()
    names = {a: full_name(arm, b) for a, b in alias_map.items()}

    world = [mw_skin @ v.co for v in skin.data.vertices]
    lo = Vector(min(p[i] for p in world) for i in range(3))
    hi = Vector(max(p[i] for p in world) for i in range(3))
    k = height / (hi.z - lo.z)
    N = Matrix.Scale(k, 4) @ Matrix.Translation(Vector((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)))
    arm.data.pose_position = "REST"
    arm.data.transform(N @ mw_arm)
    skin.data.transform(N @ mw_skin)
    # Toes must point at -Y
    foot, toe = arm.data.bones[names["footR"]], arm.data.bones[names["toeR"]]
    if toe.tail_local.y > foot.head_local.y:
        R = Matrix.Rotation(math.pi, 4, "Z")
        arm.data.transform(R)
        skin.data.transform(R)

    top = empty(name, None, coll=coll, size=0.5)
    for o in meshes:
        if o is not skin:
            OB.remove(o, do_unlink=True)
    keep = {arm.name, skin.name}
    arm.parent = None
    arm.matrix_world = Matrix.Identity(4)
    arm.data.pose_position = "POSE"
    skin.parent = None
    skin.matrix_world = Matrix.Identity(4)
    skin.parent = arm
    skin.matrix_parent_inverse = Matrix.Identity(4)
    if not any(md.type == "ARMATURE" for md in skin.modifiers):
        skin.modifiers.new("rig", "ARMATURE")
    for md in skin.modifiers:
        if md.type == "ARMATURE":
            md.object = arm
    for o in [o for o in OB if o.get("asset") == asset and o.name not in keep]:
        OB.remove(o, do_unlink=True)
    imp = OB.get(asset + "_import")
    if imp:
        OB.remove(imp, do_unlink=True)
    arm.parent = top
    arm.name, skin.name = name + "_arm", name + "_skin"
    # Off the assets collection, so a hidden collection can't take the cast with it
    for o in (arm, skin):
        for c in list(o.users_collection):
            c.objects.unlink(o)
        coll.objects.link(o)
        del o["asset"]  # it's cast now: s04 clears whatever still carries this tag
    t_pose(arm, skin, names)
    for p in skin.data.polygons:
        p.use_smooth = False
    top.location = FAR
    return arm, skin, names


def head_box(skin, names):
    """Bounding box of the vertices that follow the head."""
    g = skin.vertex_groups[names["head"]].index
    pts_ = [v.co for v in skin.data.vertices if any(e.group == g and e.weight > 0.5 for e in v.groups)]
    return Vector(min(p[i] for p in pts_) for i in range(3)), Vector(max(p[i] for p in pts_) for i in range(3))


def frozen(asset, name, height, facing_fix=None):
    """An import flattened into one static mesh in the pose it was exported in, feet on z = 0."""
    meshes = [o for o in parts(asset) if not o.name.startswith("Icosphere")]
    arms = parts(asset, "ARMATURE")
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    combined = bpy.data.meshes.new(name)
    v, f, fm = [], [], []
    mats = []
    uvs = []
    for ob in meshes:
        ev = ob.evaluated_get(dg)
        me = bpy.data.meshes.new_from_object(ev)
        me.transform(ev.matrix_world)
        off = len(v)
        base = len(mats)
        mats += list(me.materials)
        v += [tuple(x.co) for x in me.vertices]
        uv = me.uv_layers.active
        for p in me.polygons:
            f.append(tuple(off + i for i in p.vertices))
            fm.append(base + p.material_index)
            uvs.append([tuple(uv.data[l].uv) if uv else (0, 0) for l in p.loop_indices])
        bpy.data.meshes.remove(me)
    combined.from_pydata(v, [], f)
    for mt in mats:
        combined.materials.append(mt)
    layer = combined.uv_layers.new(name="UVMap")
    i = 0
    for p, q, mi in zip(combined.polygons, uvs, fm):
        p.material_index = mi
        p.use_smooth = False
        for l, uv in zip(p.loop_indices, q):
            layer.data[l].uv = uv
    pts_ = [x.co for x in combined.vertices]
    lo = Vector(min(p[i] for p in pts_) for i in range(3))
    hi = Vector(max(p[i] for p in pts_) for i in range(3))
    k = height / (hi.z - lo.z)
    combined.transform(Matrix.Scale(k, 4) @ Matrix.Translation(Vector((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z))))
    if facing_fix:
        combined.transform(Matrix.Rotation(math.radians(facing_fix), 4, "Z"))
    top = empty(name, None, coll=coll, size=0.5)
    ob = OB.new(name + "_mesh", combined)
    coll.objects.link(ob)
    ob.parent = top
    top.location = FAR
    for o in [o for o in OB if o.get("asset") == asset]:
        OB.remove(o, do_unlink=True)
    imp = OB.get(asset + "_import")
    if imp:
        OB.remove(imp, do_unlink=True)
    return top


# ---- The two rigged zombies up for the hero's part
zp_arm, zp_skin, zp_names = rig("zumbi_psx", "ZP", 1.78, MIXAMO)
zc_arm, zc_skin, zc_names = rig("zumbi_cyber", "ZC", 1.82, MIXAMO)


def paint_mouth(skin, names):
    """Cartoonish gore only: the polygons around the mouth and chin turn blood red. Painted on, so nothing sticks out of the face."""
    lo, hi = head_box(skin, names)
    c = (lo + hi) / 2
    g = skin.vertex_groups[names["head"]].index
    skin.data.materials.append(BLOOD)
    idx = len(skin.data.materials) - 1
    hz = hi.z - lo.z
    for poly in skin.data.polygons:
        vs = [skin.data.vertices[i] for i in poly.vertices]
        if not all(any(e.group == g and e.weight > 0.5 for e in v.groups) for v in vs):
            continue
        centre = sum((v.co for v in vs), Vector()) / len(vs)
        if centre.y < c.y and lo.z + hz * 0.12 < centre.z < lo.z + hz * 0.34 and abs(centre.x - c.x) < (hi.x - lo.x) * 0.3:
            poly.material_index = idx


def swap_head(arm, skin, names, source, name):
    """Takes a head mesh from another import and hangs it on this rig's head bone, removing the rig's own head faces."""
    import bmesh
    lo, hi = head_box(skin, names)
    c = (lo + hi) / 2
    g = skin.vertex_groups[names["head"]].index
    bm = bmesh.new()
    bm.from_mesh(skin.data)
    deform = bm.verts.layers.deform.active
    doomed = [f for f in bm.faces if all(g in v[deform] and v[deform][g] > 0.5 for v in f.verts)]
    bmesh.ops.delete(bm, geom=doomed, context="FACES")
    bm.to_mesh(skin.data)
    bm.free()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(source.evaluated_get(dg))
    me.transform(source.matrix_world)
    pts_ = [v.co for v in me.vertices]
    l2 = Vector(min(p[i] for p in pts_) for i in range(3))
    h2 = Vector(max(p[i] for p in pts_) for i in range(3))
    k = (hi.z - lo.z) * 1.08 / (h2.z - l2.z)
    me.transform(Matrix.Translation(Vector((c.x, c.y, lo.z - (hi.z - lo.z) * 0.2))) @ Matrix.Scale(k, 4) @ Matrix.Translation(Vector((-(l2.x + h2.x) / 2, -(l2.y + h2.y) / 2, -l2.z))))
    for p in me.polygons:
        p.use_smooth = False
    ob = OB.new(name, me)
    coll.objects.link(ob)
    return attach(ob, arm, names["head"])


# The hero: the rigged PSX body wearing the realistic head from the static zombie, whose face holds up in close-up
real_head = next(o for o in parts("zumbi_real") if o.name.startswith("MN_Head"))
swap_head(zp_arm, zp_skin, zp_names, real_head, "ZP_cabeca")
for mt in zp_skin.data.materials:
    t = mt.node_tree
    tex = next((n for n in t.nodes if n.type == "TEX_IMAGE"), None)
    bsdf = next((n for n in t.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if tex and bsdf:
        hsv = t.nodes.new("ShaderNodeHueSaturation")
        hsv.inputs["Saturation"].default_value = 0.35
        hsv.inputs["Value"].default_value = 0.92
        t.links.new(tex.outputs[0], hsv.inputs["Color"])
        t.links.new(hsv.outputs[0], bsdf.inputs["Base Color"])
paint_mouth(zc_skin, zc_names)

# ---- The long-haired zombie: an untextured model, dressed by painting each face by the bone it follows.
# Her skeleton's true rest pose lies on its back, so she is baked from the pose she was exported in.
zf_arm, zf_skin, zf_names = rig("zumbi_f", "ZF", 1.68, BIPED, keep_pose=True)
GREY = make_mat("zf pele", "8c9682")
DRESS = make_mat("zf vestido", "6a5c4c")
DRESS2 = make_mat("zf vestido rasgado", "4a3e34")
zf_skin.data.materials.clear()
for mt in (GREY, DRESS, DRESS2, BLOOD):
    zf_skin.data.materials.append(mt)
groups = {g.index: g.name for g in zf_skin.vertex_groups}


def zf_paint(bone):
    if any(s in bone for s in ("Head", "Neck", "Hand", "Finger", "Forearm", "Calf", "Foot", "Toe")):
        return 0
    return 1


for i, poly in enumerate(zf_skin.data.polygons):
    votes = {}
    for vi in poly.vertices:
        for e in zf_skin.data.vertices[vi].groups:
            n = groups[e.group]
            votes[n] = votes.get(n, 0) + e.weight
    idx = zf_paint(max(votes, key=votes.get)) if votes else 0
    # Darker and torn towards the hem, with a little blood at the collar
    if idx == 1:
        z = sum(zf_skin.data.vertices[vi].co.z for vi in poly.vertices) / len(poly.vertices)
        y = sum(zf_skin.data.vertices[vi].co.y for vi in poly.vertices) / len(poly.vertices)
        h = (i * 2654435761) % 100
        idx = 3 if z > 1.3 and y < 0 and h < 9 else 2 if z < 0.75 and h < 55 else 1
    poly.material_index = idx
# The model wears its hair up in a bun, which would survive the wig coming off, so everything above the skull is pulled back onto it
g = zf_skin.vertex_groups[zf_names["head"]].index
head_vs = [v for v in zf_skin.data.vertices if any(e.group == g and e.weight > 0.5 for e in v.groups)]
mean = sum((v.co for v in head_vs), Vector()) / len(head_vs)
dists = sorted((v.co - mean).length for v in head_vs)
R = dists[int(len(dists) * 0.6)] * 1.04
for v in head_vs:
    d = v.co - mean
    if (d.z > 0 or d.y > 0) and d.length > R:
        v.co = mean + d.normalized() * R
zf_skin.data.update()
# The mean sits low because of the neck, so the skull is placed down from the very top of the head, at an adult head's proportions
top = max(v.co.z for v in head_vs)
c = Vector((mean.x, mean.y, top - R * 1.05))
print("ZF skull", [round(x, 3) for x in c], "R", round(R, 3))


def face_y(x, z, reach):
    """How far forward the face comes at this spot, so features sit on it rather than floating at the nose tip."""
    near = [v.co.y for v in head_vs if math.hypot(v.co.x - x, v.co.z - z) < reach]
    return min(near) if near else c.y - R


DARK = make_mat("zf escuro", "14100e")
EYES = make_mat("zf olho", "c8c49c")
m = Mesh()
eye_z = c.z - R * 0.02
for side in (-1, 1):
    ex = c.x + side * R * 0.36
    y = face_y(ex, eye_z, R * 0.3)
    m.box((ex, y + 0.003, eye_z), (R * 0.15, 0.004, R * 0.09), 0)  # sunken sockets
    m.box((ex, y - 0.001, eye_z), (R * 0.06, 0.002, R * 0.05), 1)
mouth_z = c.z - R * 0.72
y = face_y(c.x, mouth_z, R * 0.3)
m.box((c.x, y + 0.003, mouth_z), (R * 0.28, 0.004, R * 0.09), 0)
m.box((c.x, y + 0.002, mouth_z - R * 0.2), (R * 0.15, 0.004, R * 0.12), 2)  # blood on the chin
attach(m.build("ZF_cara", [DARK, EYES, BLOOD], None, coll), zf_arm, zf_names["head"])

# The wig is its own object: the shot takes it off her head and puts it in his hand.
# A faceted ball around the skull with a window for the face, then thin hanging strands, repeatable.
HAIR = make_mat("zf cabelo", "1c120c")
HAIR2 = make_mat("zf cabelo 2", "33221a")


def wig_mesh():
    m = Mesh()
    shell(m, tuple(c), R * 1.12, lambda lat, lon: lat >= 1 or (abs(lon) >= 2 and lat >= -2), lambda lat, lon: 0 if (lat + lon) % 2 else 1, lats=8, lons=10)
    for k in range(11):
        t = -1 + 2 * k / 10
        length = R * (0.9 + 0.5 * (((k * 7) % 5) / 4))
        y = c.y + R * 1.06 * math.sqrt(max(0.0, 1 - t * t))
        m.box((c.x + t * R * 1.06, y, c.z - R * 0.2 - length), (R * 0.15, 0.01, length), k % 2)
    return m


wig = attach(wig_mesh().build("ZF_peruca", [HAIR, HAIR2], None, coll), zf_arm, zf_names["head"])

# ---- Static extras
zr = frozen("zumbi_real", "ZR", 1.76)
rast = frozen("rastejante", "RAST", 0.8)
dog = frozen("cao", "CAO", 0.72)



def copies(name, arm, count, prefix):
    """Full copies of a baked rig, sharing the mesh data. They hold their own poses."""
    family = list(arm.children)
    for i in range(1, count + 1):
        r = empty(f"{prefix}{i}", None, coll=coll, size=0.5)
        r.location = FAR
        a2 = arm.copy()
        a2.name = f"{prefix}{i}_arm"
        coll.objects.link(a2)
        a2.parent = r
        for ch in family:
            c2 = ch.copy()
            c2.name = f"{prefix}{i}_{ch.name}"
            coll.objects.link(c2)
            c2.parent = a2
            c2.parent_type = ch.parent_type
            c2.parent_bone = ch.parent_bone
            c2.matrix_parent_inverse = ch.matrix_parent_inverse
            for md in c2.modifiers:
                if md.type == "ARMATURE":
                    md.object = a2


copies("ZP", zp_arm, 3, "Z")
copies("ZC", zc_arm, 2, "C")

bpy.data.orphans_purge(do_recursive=True)
bpy.context.view_layer.update()
set_lib.save()
json.dump({"ZP": zp_names, "ZC": zc_names, "ZF": zf_names}, open(os.path.join(WORK, "cast_bones.json"), "w"))
print("cast", sorted(o.name for o in coll.objects if not o.parent))
print("=== CAST DONE", flush=True)
