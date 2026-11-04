# Step 3: turns the rigged imports into the cast. Every skeleton is baked to Z up, facing -Y, feet on z = 0, so bone axes match the world.
# PY1-6 are Paraguayans in striped jerseys, DG1-10 are dingows (two looks), MORTO is the guy passed out on the sidewalk.
# Needs a fresh import (run s02 first); re-running s02 + s03 together is safe.
import bpy, os, sys, importlib
from mathutils import Matrix, Vector
sys.path.insert(0, r"C:\Users\lukeg\Projetos\pardingows\src\thps\blender")
sys.path.insert(0, r"C:\Users\lukeg\Projetos\pardingows\src\planeta\blender")
sys.path.insert(0, r"C:\Users\lukeg\Projetos\pardingows\src\missao\blender")
import lib, build, set_lib
importlib.reload(lib); importlib.reload(build); importlib.reload(set_lib)
from lib import Mesh, empty, make_mat, srgb
from build import attach
from set_lib import ps1_material, shrink

OB = bpy.data.objects
coll = bpy.data.collections["assets"]
TEXTURES = set_lib.TEXTURES
FAR = (500, 500, -50)

# Bone aliases. "R" is the +X side once baked, which is the skeleton's anatomical left.
MIXAMO = {"hips": "mixamorig:Hips_01", "spine": "mixamorig:Spine1_03", "head": "mixamorig:Head_06",
          "armR": "mixamorig:LeftArm_", "foreR": "mixamorig:LeftForeArm_", "armL": "mixamorig:RightArm_", "foreL": "mixamorig:RightForeArm_",
          "thighR": "mixamorig:LeftUpLeg_", "shinR": "mixamorig:LeftLeg_", "thighL": "mixamorig:RightUpLeg_", "shinL": "mixamorig:RightLeg_",
          "footR": "mixamorig:LeftFoot_", "toeR": "mixamorig:LeftToeBase_"}
MANNEQUIN = {"hips": "pelvis_02", "spine": "spine_02_08", "head": "head_022",
             "armR": "arm_l_010", "foreR": "forearm_l_011", "armL": "arm_r_024", "foreL": "forearm_r_025",
             "thighR": "thigh_l_03", "shinR": "calf_l_04", "thighL": "thigh_r_036", "shinL": "calf_r_037",
             "footR": "foot_l_05", "toeR": "toe_l_06"}


def full_name(arm, prefix):
    if prefix in arm.data.bones:
        return prefix
    return next(b.name for b in arm.data.bones if b.name.startswith(prefix))


def parts(asset, kind="MESH"):
    return [o for o in OB if o.get("asset") == asset and o.type == kind]


def freeze_pose(arm, skin):
    """Makes the pose the model was exported in its new rest pose, for a rig whose true rest lies on its back."""
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
    """Straightens every arm along X and makes that the rest pose, so one pose library fits all three skeletons."""
    for alias, x in (("armR", 1), ("foreR", 1), ("armL", -1), ("foreL", -1)):
        bpy.context.view_layer.update()
        pb = arm.pose.bones[names[alias]]
        # Bone tails from glTF don't follow the limb, the next joint does
        q = (pb.children[0].head - pb.head).normalized().rotation_difference(Vector((x, 0, 0)))
        m = pb.matrix.copy()
        n = q.to_matrix().to_4x4() @ m
        n.translation = m.translation
        pb.matrix = n
    freeze_pose(arm, skin)


def rig(asset, name, height, aliases, keep_pose=False):
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
    names = {a: full_name(arm, b) for a, b in aliases.items()}

    pts = [mw_skin @ v.co for v in skin.data.vertices]
    lo = Vector(min(p[i] for p in pts) for i in range(3))
    hi = Vector(max(p[i] for p in pts) for i in range(3))
    # Whichever axis the model stands along becomes Z. Sketchfab exports are normally already Z up by now.
    k = height / (hi.z - lo.z)
    N = Matrix.Scale(k, 4) @ Matrix.Translation(Vector((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)))
    arm.data.pose_position = "REST"
    arm.data.transform(N @ mw_arm)
    skin.data.transform(N @ mw_skin)
    # Toes must point at -Y
    foot, toe = arm.data.bones[names["footR"]], arm.data.bones[names["toeR"]]
    if toe.tail_local.y > foot.head_local.y:
        R = Matrix.Rotation(3.14159265, 4, "Z")
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
    if not any(m.type == "ARMATURE" for m in skin.modifiers):
        skin.modifiers.new("rig", "ARMATURE")
    for m in skin.modifiers:
        if m.type == "ARMATURE":
            m.object = arm
    for o in [o for o in OB if o.get("asset") == asset and o.name not in keep]:
        OB.remove(o, do_unlink=True)
    imp = OB.get(asset + "_import")
    if imp:
        OB.remove(imp, do_unlink=True)
    arm.parent = top
    arm.name, skin.name = name + "_arm", name + "_skin"
    t_pose(arm, skin, names)
    for p in skin.data.polygons:
        p.use_smooth = False
    for m in skin.data.materials:
        ps1_material(m)
        shrink(m, 256)
    top.location = FAR
    return arm, skin, names


def head_box(arm, skin, names):
    """Bounding box of the vertices that follow the head."""
    g = skin.vertex_groups[names["head"]].index
    pts = [v.co for v in skin.data.vertices if any(e.group == g and e.weight > 0.5 for e in v.groups)]
    return Vector(min(p[i] for p in pts) for i in range(3)), Vector(max(p[i] for p in pts) for i in range(3))


def stripes_image():
    """Red and white vertical stripes, eight texels to a stripe pair."""
    im = bpy.data.images.get("jersey stripes") or bpy.data.images.new("jersey stripes", 8, 2)
    red, white = srgb("d81e28"), srgb("f4f0ea")
    px = []
    for _y in range(2):
        for x in range(8):
            c = red if x < 4 else white
            px += [*c, 1.0]
    im.pixels = px
    im.pack()
    return im


def jersey_mat():
    m = bpy.data.materials.get("jersey") or bpy.data.materials.new("jersey")
    m.use_nodes = True
    n = m.node_tree.nodes
    n.clear()
    out = n.new("ShaderNodeOutputMaterial")
    bsdf = n.new("ShaderNodeBsdfDiffuse")
    tex = n.new("ShaderNodeTexImage")
    tex.image = stripes_image()
    tex.interpolation = "Closest"
    m.node_tree.links.new(tex.outputs[0], bsdf.inputs["Color"])
    m.node_tree.links.new(bsdf.outputs[0], out.inputs[0])
    return m


def tinted(m, name, rgb):
    """A dirtier copy of a textured material."""
    c = m.copy()
    c.name = name
    t = c.node_tree
    tex = next(n for n in t.nodes if n.type == "TEX_IMAGE")
    bsdf = next(n for n in t.nodes if n.type == "BSDF_PRINCIPLED")
    mix = t.nodes.new("ShaderNodeMixRGB")
    mix.blend_type = "MULTIPLY"
    mix.inputs[0].default_value = 1.0
    mix.inputs[2].default_value = (*srgb(rgb), 1)
    t.links.new(tex.outputs[0], mix.inputs[1])
    t.links.new(mix.outputs[0], bsdf.inputs["Base Color"])
    return c


def copies(name, arm, count, first=1):
    """The source becomes the first; the rest copy it and share the mesh data."""
    family = [c for c in arm.children]
    out = {}
    src_root = arm.parent
    for i in range(first, first + count):
        r = empty(f"{name}{i}", None, coll=coll, size=0.5)
        r.location = FAR
        a2 = arm.copy()
        a2.name = f"{name}{i}_arm"
        coll.objects.link(a2)
        a2.parent = r
        for c in family:
            c2 = c.copy()
            c2.name = c.name.replace(name + "_", f"{name}{i}_")
            coll.objects.link(c2)
            c2.parent = a2
            c2.parent_type = c.parent_type
            c2.parent_bone = c.parent_bone
            c2.matrix_parent_inverse = c.matrix_parent_inverse
            for md in c2.modifiers:
                if md.type == "ARMATURE":
                    md.object = a2
        out[f"{name}{i}"] = a2
    return out


# ---- Paraguayans: the bare base man dressed by painting each face by the bone it follows
py_arm, py_skin, py_names = rig("male", "PY", 1.78, MANNEQUIN, keep_pose=True)
SKIN = make_mat("py skin", "a8693f")
HAIR = make_mat("py hair", "17120e")
SHORTS = make_mat("py shorts", "1b3a9c")
SOCK = make_mat("py sock", "e8e4dc")
SHOE = make_mat("py shoe", "1a1a20")
JERSEY = jersey_mat()
py_skin.data.materials.clear()
for m in (SKIN, JERSEY, SHORTS, SOCK, SHOE):
    py_skin.data.materials.append(m)
group_names = {g.index: g.name for g in py_skin.vertex_groups}
def paint(bone):
    if bone.startswith(("head", "neck", "hand", "thumb", "index", "fingers", "forearm")):
        return 0
    if bone.startswith(("spine", "clavicle", "arm_")):
        return 1
    if bone.startswith(("pelvis", "thigh")):
        return 2
    if bone.startswith("calf"):
        return 3
    return 4
uv = py_skin.data.uv_layers.get("jersey") or py_skin.data.uv_layers.new(name="jersey")
py_skin.data.uv_layers.active = uv
uv.active_render = True
for poly in py_skin.data.polygons:
    votes = {}
    for vi in poly.vertices:
        for e in py_skin.data.vertices[vi].groups:
            votes[group_names[e.group]] = votes.get(group_names[e.group], 0) + e.weight
    poly.material_index = paint(max(votes, key=votes.get)) if votes else 0
    for li in poly.loop_indices:
        co = py_skin.data.vertices[py_skin.data.loops[li].vertex_index].co
        uv.data[li].uv = (co.x * 6.5 + 0.5, co.z)

lo, hi = head_box(py_arm, py_skin, py_names)
c = (lo + hi) / 2
m = Mesh()
FACE_Y = lo.y - 0.004
hx, hz = (hi.x - lo.x) / 2, hi.z - lo.z
m.box((c.x, c.y + 0.015, hi.z - hz * 0.08), (hx * 1.06, (hi.y - lo.y) * 0.54, hz * 0.14), 0)  # hair
m.box((c.x, hi.y - 0.015, hi.z - hz * 0.3), (hx * 0.96, 0.03, hz * 0.26), 0)  # back of the hair
for side in (-1, 1):
    m.box((c.x + side * hx * 0.42, FACE_Y, hi.z - hz * 0.42), (hx * 0.17, 0.008, hz * 0.05), 1)  # eyes
    m.box((c.x + side * hx * 0.42, FACE_Y, hi.z - hz * 0.34), (hx * 0.24, 0.012, hz * 0.03), 0)  # brows
m.box((c.x, FACE_Y, hi.z - hz * 0.68), (hx * 0.42, 0.012, hz * 0.045), 0)  # moustache
attach(m.build("PY_face", [HAIR, make_mat("py eye", "f2f0e8")], None, coll), py_arm, py_names["head"])

# The back is what the chase camera sees, so it carries a number
m = Mesh()
back = max(v.co.y for v in py_skin.data.vertices if v.co.z > 1.05 and v.co.z < 1.45 and abs(v.co.x) < 0.1) + 0.012
NUMBER = make_mat("py number", "14141c")
Z0, S = 1.34, 0.022
digits = {"1": ["..#", "..#", "..#", "..#", "..#"], "0": ["###", "#.#", "#.#", "#.#", "###"]}
for ox, d in ((-0.1, "1"), (0.03, "0")):
    for ry, row in enumerate(digits[d]):
        for rx, ch in enumerate(row):
            if ch == "#":
                m.box((ox + rx * 2 * S, back, Z0 - ry * 2 * S), (S, 0.004, S), 0)
attach(m.build("PY_number", [NUMBER], None, coll), py_arm, py_names["spine"])
PY = copies("PY", py_arm, 6)

# ---- Dingows: the old man as he is but darker and dirtier, the second man with a beanie, both bearded
dg_arm, dg_skin, dg_names = rig("oldman", "DG", 1.72, MIXAMO)
dg_mat = dg_skin.data.materials[0]
dg_skin.data.materials[0] = tinted(dg_mat, "dingow dirt", "c9956f")
lo, hi = head_box(dg_arm, dg_skin, dg_names)
c = (lo + hi) / 2
hx, hz = (hi.x - lo.x) / 2, hi.z - lo.z
BEARD = make_mat("dingow beard", "4a4034")
EYES = make_mat("dingow eyes", "f4f0e0", emit=0.5)
m = Mesh()
m.box((c.x, lo.y + 0.02, lo.z + hz * 0.09), (hx * 0.56, 0.028, hz * 0.07), 0)
for side in (-1, 1):
    m.box((c.x + side * hx * 0.4, lo.y - 0.004, lo.z + hz * 0.62), (hx * 0.24, 0.006, hz * 0.07), 1)  # staring eyes
    m.box((c.x + side * hx * 0.4, lo.y - 0.012, lo.z + hz * 0.62), (hx * 0.09, 0.004, hz * 0.04), 0)
attach(m.build("DG_beard", [BEARD, EYES], None, coll), dg_arm, dg_names["head"])
DG_A = copies("DG", dg_arm, 5)

dh_arm, dh_skin, dh_names = rig("male2", "DH", 1.74, MIXAMO)
dh_skin.data.materials[0] = tinted(dh_skin.data.materials[0], "dingow dirt 2", "b08a68")
lo, hi = head_box(dh_arm, dh_skin, dh_names)
c = (lo + hi) / 2
hx, hz = (hi.x - lo.x) / 2, hi.z - lo.z
BEANIE = make_mat("dingow beanie", "4a2a22")
m = Mesh()
m.box((c.x, c.y, hi.z - hz * 0.14), (hx * 1.08, (hi.y - lo.y) * 0.56, hz * 0.2), 0)
m.box((c.x, lo.y + 0.02, lo.z + hz * 0.08), (hx * 0.56, 0.028, hz * 0.07), 1)
for side in (-1, 1):
    m.box((c.x + side * hx * 0.4, lo.y - 0.004, lo.z + hz * 0.58), (hx * 0.24, 0.006, hz * 0.07), 2)
    m.box((c.x + side * hx * 0.4, lo.y - 0.012, lo.z + hz * 0.58), (hx * 0.09, 0.004, hz * 0.04), 1)
attach(m.build("DH_beanie", [BEANIE, BEARD, EYES], None, coll), dh_arm, dh_names["head"])
DG_B = copies("DH", dh_arm, 5)

# ---- The guy passed out on the sidewalk stays in the pose he was modelled in, frozen into plain mesh
dead_arm = parts("deadman", "ARMATURE")[0]
dead_meshes = parts("deadman")
dead_skin = max(dead_meshes, key=lambda o: len(o.data.polygons))
dead_arm.animation_data_clear()
bpy.context.view_layer.update()
ev = dead_skin.evaluated_get(bpy.context.evaluated_depsgraph_get())
frozen = bpy.data.meshes.new_from_object(ev)
frozen.transform(ev.matrix_world)
pts = [v.co for v in frozen.vertices]
lo = Vector(min(p[i] for p in pts) for i in range(3))
hi = Vector(max(p[i] for p in pts) for i in range(3))
span = max(hi.x - lo.x, hi.y - lo.y)
k = 1.75 / span
frozen.transform(Matrix.Scale(k, 4) @ Matrix.Translation(Vector((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z))))
morto = empty("MORTO", None, coll=coll, size=0.5)
body = bpy.data.objects.new("MORTO_mesh", frozen)
coll.objects.link(body)
body.parent = morto
for p in frozen.polygons:
    p.use_smooth = False
for m_ in frozen.materials:
    ps1_material(m_)
    shrink(m_, 256)
    # The texture has blood on it, and he's only supposed to be passed out
    t = m_.node_tree
    tex = next(n for n in t.nodes if n.type == "TEX_IMAGE")
    bsdf = next(n for n in t.nodes if n.type == "BSDF_PRINCIPLED")
    hsv = t.nodes.new("ShaderNodeHueSaturation")
    hsv.inputs["Saturation"].default_value = 0.6
    t.links.new(tex.outputs[0], hsv.inputs["Color"])
    t.links.new(hsv.outputs[0], bsdf.inputs["Base Color"])
morto.location = FAR
for o in [o for o in OB if o.get("asset") == "deadman"]:
    OB.remove(o, do_unlink=True)
if OB.get("deadman_import"):
    OB.remove(OB["deadman_import"], do_unlink=True)

# The sources under PY, DG and DH stay in the file only to be copied, so they hide from every render
for src in ("PY", "DG", "DH"):
    OB[src + "_arm"].hide_render = True
    for ch in OB[src + "_arm"].children:
        ch.hide_render = True

bpy.data.orphans_purge(do_recursive=True)
bpy.context.view_layer.update()
set_lib.save()
print("cast", sorted(o.name for o in coll.objects if not o.parent and not o.name.endswith("_import")))
for nm, arm in (("PY", py_arm), ("DG", dg_arm), ("DH", dh_arm)):
    b = arm.data.bones
    al = {"PY": py_names, "DG": dg_names, "DH": dh_names}[nm]
    print(nm, "armR head", [round(v, 2) for v in b[al["armR"]].head_local], "tail", [round(v, 2) for v in b[al["armR"]].tail_local],
          "head", [round(v, 2) for v in b[al["head"]].head_local], "toeR", [round(v, 2) for v in b[al["toeR"]].tail_local])
import json
OUT = os.path.join(os.path.dirname(TEXTURES), "cast_bones.json")
json.dump({"PY": py_names, "DG": dg_names, "DH": dh_names}, open(OUT, "w"))
print("bones", OUT)
