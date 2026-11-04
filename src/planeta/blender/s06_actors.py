# Step 6: turns the raw imports into clean actors, each a root empty at ground level with its transforms baked in.
# Rigid props: LANDER, MODULE, MOONBASE, POLE, PISTOL, FARDO, EARTH, SUN, ASTEROIDS. Rigged: CESAR, CHIMP1-3.
# Needs a fresh import (run s05 first); re-running s05 + s06 together is safe.
import bpy, os, sys, math, importlib
from mathutils import Matrix, Vector
sys.path.insert(0, r"C:\Users\lukeg\Projetos\pardingows\src\thps\blender")
sys.path.insert(0, r"C:\Users\lukeg\Projetos\pardingows\src\planeta\blender")
import lib, build
importlib.reload(lib); importlib.reload(build)
from lib import Mesh, empty, make_mat
from build import attach, ring, shell

OB = bpy.data.objects
coll = bpy.data.collections["assets"]
TEXTURES = r"C:\Users\lukeg\Projetos\pardingows\blender\planeta\textures"
os.makedirs(TEXTURES, exist_ok=True)
FAR = (500, 500, -50)


def parts(asset, kind="MESH"):
    return [o for o in OB if o.get("asset") == asset and o.type == kind]


def wipe_asset(asset, keep=()):
    for o in [o for o in OB if o.get("asset") == asset and o not in keep]:
        OB.remove(o, do_unlink=True)
    e = OB.get(asset + "_import")
    if e:
        OB.remove(e, do_unlink=True)


def ps1_material(m):
    """Hard texels, no shine, opaque."""
    if not m or not m.use_nodes:
        return
    for n in m.node_tree.nodes:
        if n.type == "TEX_IMAGE":
            n.interpolation = "Closest"
        if n.type == "BSDF_PRINCIPLED":
            n.inputs["Roughness"].default_value = 1.0
            n.inputs["Specular IOR Level"].default_value = 0.0
            n.inputs["Metallic"].default_value = 0.0


def shrink(m, size):
    """Replaces a material's texture with a small copy, saved next to the project."""
    for n in m.node_tree.nodes:
        if n.type != "TEX_IMAGE" or not n.image or max(n.image.size) <= size:
            continue
        w, h = n.image.size
        k = size / max(w, h)
        small = n.image.copy()
        small.name = "small " + n.image.name
        small.scale(max(int(w * k), 1), max(int(h * k), 1))
        small.filepath_raw = os.path.join(TEXTURES, small.name.replace(":", "_") + ".png")
        small.file_format = "PNG"
        small.save()
        n.image = small


def bake(asset, root_name, size=None, axis="z", meshes=None, drop=None):
    """Bakes world transforms into copies of the meshes, then puts their bottom centre on a new root at the origin.
    size scales the chosen axis to that many metres."""
    obs = meshes if meshes is not None else parts(asset)
    if drop:
        for o in [o for o in obs if drop(o)]:
            obs.remove(o)
    bpy.context.view_layer.update()
    root = empty(root_name, None, coll=coll, size=0.5)
    baked = []
    for o in obs:
        me = o.data.copy()
        me.transform(o.matrix_world)
        new = bpy.data.objects.new(root_name + " " + o.name, me)
        coll.objects.link(new)
        baked.append(new)
    wipe_asset(asset)
    pts = [v.co.copy() for b in baked for v in b.data.vertices]
    lo = Vector(min(p[i] for p in pts) for i in range(3))
    hi = Vector(max(p[i] for p in pts) for i in range(3))
    s = size / (hi - lo)["xyz".index(axis)] if size else 1.0
    shift = Matrix.Scale(s, 4) @ Matrix.Translation(-Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z)))
    for b in baked:
        b.data.transform(shift)
        b.parent = root
        for p in b.data.polygons:
            p.use_smooth = False
        for m in b.data.materials:
            ps1_material(m)
    root["size"] = tuple((hi - lo) * s)
    root.location = FAR
    return root, baked, (lambda x, y, z: shift @ Vector((x, y, z)))


# ---- Set pieces and props
bake("lander", "LANDER", 6.5)
bake("moonbase", "MOONBASE", 8.0)
bake("poles", "POLE", 6.0)
# The capsule shares its file with an astronaut standing beside it, which sits entirely at x > 0.9
bake("module", "MODULE", 6.0, drop=lambda o: min((o.matrix_world @ v.co).x for v in o.data.vertices) > 0.9)
pistol_root, pistol, _ = bake("pistol", "PISTOL", 0.4, axis="x")

# Asteroids stay separate so they can hang around the sky
ast_root, asteroids, _ = bake("asteroids", "ASTEROIDS", 9.0)

# Earth and sun: the moon in the bundle is dropped, since that's where we're standing. Sky materials skip the distance fade.
sky = {o.name.split("_")[0]: o for o in parts("sky")}
sky_mats = {}
for key in ("earth", "sun"):
    sky_root, sky_mesh, _ = bake("x", key.upper(), meshes=[sky[key]])
    # bake() wipes "x" objects only, so the originals go below
    sky_mats[key] = sky_mesh[0].data.materials[0]
wipe_asset("sky")
sky_mats["earth"].name = "sky_earth"
sun_tex = next((n.image for n in sky_mats["sun"].node_tree.nodes if n.type == "TEX_IMAGE" and n.image), None)
sky_mats["sun"].name = "sky_sun"
tree = sky_mats["sun"].node_tree
out = next(n for n in tree.nodes if n.type == "OUTPUT_MATERIAL")
for n in list(tree.nodes):
    if n.type != "OUTPUT_MATERIAL":
        tree.nodes.remove(n)
glow = tree.nodes.new("ShaderNodeEmission")
glow.inputs["Strength"].default_value = 1.0
if sun_tex:
    tn = tree.nodes.new("ShaderNodeTexImage")
    tn.image = sun_tex
    tn.interpolation = "Closest"
    tree.links.new(tn.outputs[0], glow.inputs[0])
tree.links.new(glow.outputs[0], out.inputs["Surface"])

# The bale: the crushed heap of boxes, bound with black straps
fardo_root, fardo, _ = bake("boxes", "FARDO", 2.2)
size = Vector(fardo_root["size"])
strap = make_mat("fardo strap", "16161c")
core = make_mat("fardo kraft", "b58a55")
m = Mesh()
m.box((0, 0, size.z * 0.48), (size.x * 0.4, size.y * 0.4, size.z * 0.44), 1)  # fills the gaps between the boxes
sx, sy, sz = size.x / 2 + 0.03, size.y / 2 + 0.03, size.z / 2 + 0.03
for x in (-0.22, 0.22):
    for bar in (((0, 0, sz), (0.04, sy, 0.03)), ((0, 0, -sz), (0.04, sy, 0.03)), ((0, sy, 0), (0.04, 0.03, sz)), ((0, -sy, 0), (0.04, 0.03, sz))):
        m.box((x * size.x + bar[0][0], bar[0][1], size.z / 2 + bar[0][2]), bar[1], 0)
for bar in (((0, 0, sz), (sx, 0.04, 0.03)), ((0, 0, -sz), (sx, 0.04, 0.03)), ((sx, 0, 0), (0.03, 0.04, sz)), ((-sx, 0, 0), (0.03, 0.04, sz))):
    m.box((bar[0][0], bar[0][1], size.z / 2 + bar[0][2]), bar[1], 0)
m.build("FARDO straps", [strap, core], fardo_root, coll)


# ---- César: stray sphere out, polygon count and texture down to PS1 size, feet on the ground
OB.remove(next(o for o in parts("cesar") if len(o.data.polygons) < 1000), do_unlink=True)
ces_mesh = parts("cesar")[0]
ces_arm = parts("cesar", "ARMATURE")[0]
ces_arm.name, ces_mesh.name = "CESAR_arm", "CESAR_skin"
for pb in ces_arm.pose.bones:
    pb.matrix_basis = Matrix.Identity(4)
for mat in ces_mesh.data.materials:
    ps1_material(mat)
    shrink(mat, 256)
    # His fur is close to black, so it glows a little to keep his face readable from below
    tree = mat.node_tree
    bsdf = next(n for n in tree.nodes if n.type == "BSDF_PRINCIPLED")
    tex = next(n for n in tree.nodes if n.type == "TEX_IMAGE")
    tree.links.new(tex.outputs[0], bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = 0.6
for p in ces_mesh.data.polygons:
    p.use_smooth = False
dec = ces_mesh.modifiers.new("ps1 decimate", "DECIMATE")
dec.ratio = 0.3
ces_mesh.modifiers.move(len(ces_mesh.modifiers) - 1, 0)
cesar = empty("CESAR", None, coll=coll, size=0.5)
top = OB["Sketchfab_model"] if "Sketchfab_model" in OB else next(o for o in OB if o.get("asset") == "cesar" and o.name.startswith("Sketchfab_model"))
OB.remove(OB["cesar_import"], do_unlink=True)
top.parent = cesar
top.matrix_parent_inverse = Matrix.Identity(4)
top.location = (0, 0, 1.04)  # he stands 2.08 m with his hips at the model origin
cesar.location = FAR

# ---- Chimp: a small skeleton with one bone per vertex, which is how the console skinned its characters
root, chimp_parts, P = bake("chimp", "CHIMP_src", 1.5)
skin = chimp_parts[0]
skin.name = "CHIMP_skin"
for mat in skin.data.materials:
    shrink(mat, 256)
BONES = {
    # name: (parent, head, tail), in the source model's centimetres. Facing -Y, +X is his left in view (matches lib.BONES naming "R").
    "hips": (None, (0, 3, 72), (0, 3, 92)),
    "spine": ("hips", (0, 3, 92), (0, 3, 122)),
    "head": ("spine", (0, 3, 122), (0, -2, 157)),
    "armR": ("spine", (22, 7, 114), (58, 7, 114)),
    "foreR": ("armR", (58, 7, 114), (84, 7, 113)),
    "handR": ("foreR", (84, 7, 113), (99, 6, 112)),
    "armL": ("spine", (-22, 7, 114), (-58, 7, 114)),
    "foreL": ("armL", (-58, 7, 114), (-84, 7, 113)),
    "handL": ("foreL", (-84, 7, 113), (-99, 6, 112)),
    "thighR": ("hips", (13, 3, 72), (15, 3, 38)),
    "shinR": ("thighR", (15, 3, 38), (16, 6, 12)),
    "footR": ("shinR", (16, 6, 12), (24, -10, 0)),
    "thighL": ("hips", (-13, 3, 72), (-15, 3, 38)),
    "shinL": ("thighL", (-15, 3, 38), (-16, 6, 12)),
    "footL": ("shinL", (-16, 6, 12), (-24, -10, 0)),
}
arm_data = bpy.data.armatures.new("CHIMP")
arm = bpy.data.objects.new("CHIMP_arm", arm_data)
coll.objects.link(arm)
bpy.context.view_layer.objects.active = arm
arm.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
for name, (parent, a, b) in BONES.items():
    eb = arm_data.edit_bones.new(name)
    eb.head, eb.tail = P(*a), P(*b)
    if parent:
        eb.parent = arm_data.edit_bones[parent]
bpy.ops.object.mode_set(mode="OBJECT")
arm.select_set(False)

def seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
    return (a + ab * t - p).length

skin.parent = None
segments = {n: (arm_data.bones[n].head_local.copy(), arm_data.bones[n].tail_local.copy()) for n in BONES}
for n in BONES:
    skin.vertex_groups.new(name=n)
counts = dict.fromkeys(BONES, 0)
for v in skin.data.vertices:
    best = min(segments, key=lambda n: seg_dist(v.co, *segments[n]))
    skin.vertex_groups[best].add([v.index], 1.0, "REPLACE")
    counts[best] += 1
print("chimp verts per bone", counts)
skin.modifiers.new("rig", "ARMATURE").object = arm
skin.parent = arm
OB.remove(OB["CHIMP_src"], do_unlink=True)

# His suit: helmet with the same window as the hero, backpack, chest band, cuffs. Rigid pieces on the bones.
WHITE, GREY, RIM, GOLD = bpy.data.materials["suit white"], bpy.data.materials["suit grey"], bpy.data.materials["suit rim"], bpy.data.materials["suit visor"]
GREEN, YEL = bpy.data.materials["suit green"], bpy.data.materials["suit yellow"]
head_c = P(0, 0, 140)
HEAD_R = 0.31
m = Mesh()
shell(m, head_c, HEAD_R, lambda la, lo: la >= -3 and not (la in (-2, -1, 0, 1) and lo in (-2, -1, 0, 1)), lambda la, lo: 1 if la == 2 and lo in (-2, -1, 0, 1) else 0, rim_mi=2)
attach(m.build("CHIMP helmet", [WHITE, GOLD, RIM], None, coll), arm, "head")
m = Mesh()
back = P(0, 19, 106)
m.box(back, (0.17, 0.09, 0.21), 0)
m.box(back + Vector((0, 0.1, 0)), (0.11, 0.01, 0.13), 1)
ring(m, P(0, 3, 96), P(0, 3, 122), 0.215, 0, 8)
ring(m, P(0, 3, 90), P(0, 3, 96), 0.2, 2, 8)
ring(m, P(0, 2, 120), P(0, 2, 124), 0.17, 2, 8)
m.box(P(0, -13, 112), (0.09, 0.02, 0.05), 2)
attach(m.build("CHIMP pack", [WHITE, GREEN, GREY], None, coll), arm, "spine")
for side, tag in ((1, "R"), (-1, "L")):
    m = Mesh()
    ring(m, P(side * 62, 7, 114), P(side * 68, 7, 114), 0.075, 0, 6)
    attach(m.build("CHIMP cuff" + tag, [YEL], None, coll), arm, "fore" + tag)
    m = Mesh()
    ring(m, P(side * 15, 4, 22), P(side * 16, 5, 16), 0.1, 0, 6)
    attach(m.build("CHIMP sock" + tag, [GREEN], None, coll), arm, "shin" + tag)

# Three of them. The first keeps the source objects, the others copy them and share the mesh data.
family = [arm] + [c for c in arm.children]
for i in range(1, 4):
    r = empty(f"CHIMP{i}", None, coll=coll, size=0.5)
    r.location = FAR
    if i == 1:
        arm.parent = r
        arm.name = "CHIMP1_arm"
        continue
    a2 = arm.copy()
    a2.name = f"CHIMP{i}_arm"
    coll.objects.link(a2)
    a2.parent = r
    for c in family[1:]:
        c2 = c.copy()
        c2.name = c.name.replace("CHIMP", f"CHIMP{i}")
        coll.objects.link(c2)
        c2.parent = a2
        c2.parent_type = c.parent_type
        c2.parent_bone = c.parent_bone
        c2.matrix_parent_inverse = c.matrix_parent_inverse
        for md in c2.modifiers:
            if md.type == "ARMATURE":
                md.object = a2

bpy.data.orphans_purge(do_recursive=True)
bpy.context.view_layer.update()
bpy.ops.wm.save_mainfile()
print("roots", sorted(o.name for o in coll.objects if not o.parent))
print("cesar faces after decimate", len(ces_mesh.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.polygons))
print("chimp bbox", [round(v, 2) for v in P(0, 0, 160)])
