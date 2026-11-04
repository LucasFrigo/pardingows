# Step 9: the gag pieces. Pistols in hand, the cardboard head and its stamp and tape, César's jaw and mouth,
# lander flame, dust, blob shadows. Safe to re-run: removes its own objects first.
import bpy, math, os, sys, importlib
import numpy as np
from mathutils import Matrix, Vector
sys.path.insert(0, r"C:\Users\lukeg\Projetos\pardingows\src\thps\blender")
sys.path.insert(0, r"C:\Users\lukeg\Projetos\pardingows\src\planeta\blender")
import lib, build
importlib.reload(lib); importlib.reload(build)
from lib import Mesh, make_mat, srgb
from build import attach, on_ball, ring

OB = bpy.data.objects
coll = bpy.data.collections.get("gags") or bpy.data.collections.new("gags")
if coll.name not in bpy.context.scene.collection.children:
    bpy.context.scene.collection.children.link(coll)
for ob in list(coll.objects):
    OB.remove(ob, do_unlink=True)
TEXTURES = r"C:\Users\lukeg\Projetos\pardingows\blender\planeta\textures"
SKIN = np.array((0xa0, 0x62, 0x3a)) / 255

arm1 = OB["Armature"]
chimp1 = OB["CHIMP1_arm"]
ces_arm, ces_skin = OB["CESAR_arm"], OB["CESAR_skin"]
for a in (arm1, chimp1):
    a.data.pose_position = "REST"
for name in ("P1", "CHIMP1", "CESAR"):
    OB[name].location = (0, 0, 0)
    OB[name].rotation_euler = (0, 0, 0)
OB["P1"].scale = (lib.SCALE,) * 3
OB["P1_body"].location = (0, 0, 0)
OB["P1_body"].rotation_euler = (0, 0, 0)
bpy.context.view_layer.update()

# ---- Pistols. The source points along +X with the grip down, its origin under the middle of the gun.
src = next(c for c in OB["PISTOL"].children if c.type == "MESH")
gun_mats = list(src.data.materials)
pts = [v.co for v in src.data.vertices]
grip = Vector((min(p.x for p in pts) * 0.72, 0, max(p.z for p in pts) * 0.42))


def pistol(name, arm, bone, matrix):
    me = src.data.copy()
    me.transform(matrix @ Matrix.Translation(-grip))
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    attach(ob, arm, bone)
    return ob


# Hero's arm hangs down in its rest pose. Aiming swings it forward, which turns his -Y into up, so the gun's top goes to -Y.
head, tail = Vector((1.09, -0.22, 0.30)), Vector((1.34, 0.01, -0.48))
d = (tail - head).normalized()
up = (Vector((0, -1, 0)) - d * Vector((0, -1, 0)).dot(d)).normalized()
side = up.cross(d)
R = Matrix((d, side, up)).transposed().to_4x4()
pistol("pistol hero", arm1, lib.BONES["handR"], Matrix.Translation(head.lerp(tail, 0.45)) @ R @ Matrix.Scale(1.05 / lib.SCALE, 4))
# The chimp is in metres and T-posed, so the arm already points down the barrel
hand = Vector(chimp1.data.bones["handR"].head_local).lerp(Vector(chimp1.data.bones["handR"].tail_local), 0.4)
pistol("pistol chimp", chimp1, "handR", Matrix.Translation(hand) @ Matrix.Scale(0.85, 4))

# ---- The cardboard head: same meshes, repainted texture, hidden until "PAPELÃO"
def to_cardboard(path, out_name):
    img = bpy.data.images.load(path, check_existing=True)
    w, h = img.size
    px = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(h, w, 4)
    rgb = px[..., :3]
    # The stored texture is in the file's colour space, so it compares directly with the hex skin tone
    skinish = np.clip(1 - np.abs(rgb - SKIN).sum(axis=2) / 0.55, 0, 1)[..., None]
    y = np.arange(h)[:, None]
    x = np.arange(w)[None, :]
    flutes = 0.86 + 0.14 * ((y // 3) % 2)
    rng = np.random.default_rng(3)
    blotch = 1 + np.kron(rng.uniform(-0.09, 0.09, (h // 8 + 1, w // 8 + 1)), np.ones((8, 8)))[:h, :w]
    crease = 1 - 0.28 * (np.abs((x * 0.6 + y) % 90 - 45) < 1.2)
    kraft = np.array((0.80, 0.60, 0.36))
    card = kraft[None, None, :] * (flutes * blotch * crease)[..., None]
    out = px.copy()
    out[..., :3] = rgb * (1 - skinish) + card * skinish
    new = bpy.data.images.get(out_name) or bpy.data.images.new(out_name, w, h, alpha=True)
    new.scale(w, h)
    new.pixels.foreach_set(np.clip(out, 0, 1).ravel())
    new.filepath_raw = os.path.join(TEXTURES, out_name + ".png")
    new.file_format = "PNG"
    new.save()
    return new


def card_copy(name, part):
    ob = OB[part]
    tex = next(n.image for n in ob.data.materials[0].node_tree.nodes if n.type == "TEX_IMAGE")
    img = to_cardboard(bpy.path.abspath(tex.filepath), f"card {part}")
    me = ob.data.copy()
    mat = bpy.data.materials.get(f"card {part}") or bpy.data.materials.new(f"card {part}")
    mat.use_nodes = True
    n = mat.node_tree.nodes
    n.clear()
    out = n.new("ShaderNodeOutputMaterial")
    bsdf = n.new("ShaderNodeBsdfDiffuse")
    t = n.new("ShaderNodeTexImage")
    t.image = img
    t.interpolation = "Closest"
    mat.node_tree.links.new(t.outputs[0], bsdf.inputs["Color"])
    mat.node_tree.links.new(bsdf.outputs[0], out.inputs["Surface"])
    me.materials.clear()
    me.materials.append(mat)
    new = ob.copy()
    new.data = me
    new.name = name
    coll.objects.link(new)
    new.parent = ob.parent
    new.parent_type = ob.parent_type
    new.parent_bone = ob.parent_bone
    new.matrix_parent_inverse = ob.matrix_parent_inverse
    return new


card_copy("card head", "head")
card_copy("card nose", "nose")

# Red stamp over the brow and a strip of packing tape across the cheek, on the skull's real surface
stamp = bpy.data.curves.new("card stamp", "FONT")
stamp.body = "FRÁGIL"
stamp.size = 0.36
stamp.align_x = "CENTER"
stamp.align_y = "CENTER"
stamp.resolution_u = 1
stamp.materials.append(make_mat("card red", "c81e1e"))
ob = bpy.data.objects.new("card stamp", stamp)
coll.objects.link(ob)
SKULL_C, SKULL_R = Vector((0, -0.69, 2.77)), 1.38
world = arm1.matrix_world @ Matrix.Translation(on_ball(SKULL_C, SKULL_R + 0.02, 0, 33)) @ Matrix.Rotation(math.radians(90 - 33), 4, "X")
ob.parent = arm1
ob.parent_type = "BONE"
ob.parent_bone = lib.BONES["head"]
bpy.context.view_layer.update()
ob.matrix_world = world
m = Mesh()
tape = make_mat("card tape", "e2cf9c")
for a0, a1, e0, e1 in ((-58, -18, -22, -11), (22, 44, -44, 2)):
    i = len(m.v)
    m.v += [tuple(on_ball(SKULL_C, SKULL_R + 0.02, a, e)) for a, e in ((a0, e0), (a1, e0), (a1, e1), (a0, e1))]
    m.f.append((i, i + 1, i + 2, i + 3))
    m.fm.append(0)
attach(m.build("card tape", [tape], None, coll), arm1, lib.BONES["head"])

# ---- César's jaw. A shape key drops everything below the mouth line, so he really opens up. The Decimate modifier runs on top.
to_root = ces_skin.matrix_world
inv = to_root.inverted().to_3x3()
MOUTH_Z = 1.792
me = ces_skin.data
if me.shape_keys:
    ces_skin.shape_key_clear()
ces_skin.shape_key_add(name="Basis")
key = ces_skin.shape_key_add(name="open", from_mix=False)
moved = 0
for i, v in enumerate(me.vertices):
    p = to_root @ v.co
    if p.y > -0.075 or abs(p.x) > 0.13 or p.z < 1.6 or p.z > 1.84:
        continue
    width = max(0.0, 1 - abs(p.x) / 0.13) ** 0.6
    front = min((-0.075 - p.y) / 0.07, 1.0)
    if p.z < MOUTH_Z:
        drop = min((MOUTH_Z - p.z) / 0.02, 1.0) * 0.082
        low = min((p.z - 1.6) / 0.06, 1.0)
        delta = Vector((0, 0.008, -drop * low))
    else:
        delta = Vector((0, 0, 0.018 * (1 - (p.z - MOUTH_Z) / 0.048)))
    key.data[i].co = v.co + inv @ (delta * width * front)
    moved += 1
print("cesar jaw verts", moved)

# Inside of the mouth: dark, with a row of teeth along the top and two fangs
ces_inv = ces_arm.matrix_world.inverted()
dark, teeth = make_mat("cesar mouth", "180808"), make_mat("cesar teeth", "e8dfc8")
m = Mesh()
FACE_Y = -0.252  # in front of the stretched skin, which the decimated mesh keeps closed across the gap
oct_pts = [(0.066 * math.cos(k * math.pi / 4), FACE_Y, 1.745 + 0.05 * math.sin(k * math.pi / 4)) for k in range(8)]
m.v += [tuple(ces_inv @ Vector(p)) for p in oct_pts]
m.f.append(tuple(range(8)))
m.fm.append(0)
def tbox(x, z, hx, hz):
    c = ces_inv @ Vector((x, FACE_Y - 0.004, z))
    s = 1 / ces_arm.matrix_world.to_scale()[0]
    m.box(tuple(c), (hx * s, 0.004 * s, hz * s), 1)
tbox(0, 1.792, 0.052, 0.008)
for sx in (-1, 1):
    tbox(sx * 0.044, 1.775, 0.009, 0.016)
ob = m.build("cesar mouth", [dark, teeth], None, coll)
ob.parent = ces_arm
ob.parent_type = "BONE"
ob.parent_bone = "mixamorig:Head_06"
bpy.context.view_layer.update()
ob.matrix_world = ces_arm.matrix_world

# ---- Lander flame: two nested cones, flickered by scale in the shots
fl = make_mat("flame outer", "ff8a1f", emit=2.0)
fl2 = make_mat("flame inner", "fff2a0", emit=3.0)
m = Mesh()
for r, length, mi in ((1.0, 4.2, 0), (0.55, 2.6, 1)):
    i = len(m.v)
    for k in range(6):
        t = k * math.pi / 3
        m.v.append((r * math.cos(t), r * math.sin(t), 0))
    m.v.append((0, 0, -length))
    for k in range(6):
        m.f.append((i + k, i + (k + 1) % 6, i + 6))
        m.fm.append(mi)
    m.f.append(tuple(i + k for k in range(5, -1, -1)))
    m.fm.append(mi)
flame = m.build("lander flame", [fl, fl2], None, coll)
flame.parent = OB["LANDER"]
flame.location = (0, 0, 1.4)

# ---- Dust and blob shadows
dust = make_mat("dust", "d8d4cb", emit=0.5)
for i in range(30):
    s = 0.04 + 0.03 * (i % 4)
    Mesh().box((0, 0, 0), (s, s, s)).build(f"dust {i}", [dust], None, coll)
shadow = make_mat("blob shadow", "05060c", alpha=0.6)
for name, r in (("P1", 0.5), ("P2", 0.5), ("CHIMP1", 0.42), ("CHIMP2", 0.42), ("CHIMP3", 0.42), ("CESAR", 0.6)):
    outline = [(r * math.cos(k * math.pi / 4), r * math.sin(k * math.pi / 4)) for k in range(8)]
    Mesh().prism(outline, 0, 0.005).build(name + "_shadow", [shadow], None, coll)

for a in (arm1, chimp1):
    a.data.pose_position = "POSE"
bpy.context.view_layer.update()
bpy.ops.wm.save_mainfile()
print("props ok;", len(coll.objects), "gag objects; pistol grip offset", [round(v, 3) for v in grip])
