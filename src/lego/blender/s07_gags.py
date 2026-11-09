# Step 7: what the shots switch and move. Faces that can change, the father and child's dropping shades and chains, and the joint.
# Each changing face gets one Value node per extra face, named face1, face2..., keyed 0 or 1 by the shots.
import bpy, importlib, json, os, sys
from mathutils import Matrix, Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import set_lib; importlib.reload(set_lib)
from set_lib import FAR, TEXTURES, WORK, bones_of, place, save
from world_data import origin

OB = bpy.data.objects
FACES = {
    "pardo": ["face_pardo", "face_pardo_open", "face_pardo_sleep"],
    "pardo_rob": ["face_pardo", "face_pardo_open"],
    "israel": ["face_israel", "face_israel_rant", "face_israel_shock"],
    "father": ["face_father", "face_father_run"],
    "child": ["face_child", "face_child_open"],
}


def mixer(fig, files):
    """Chains the extra faces onto the figure's face material: face i shows when its Value node is 1 (later ones win)."""
    m = bpy.data.materials[f"{fig}_Face"]
    t = m.node_tree
    for n in [n for n in t.nodes if n.name.startswith(("face", "mixc", "mixa", "extra"))]:
        t.nodes.remove(n)
    b = next(n for n in t.nodes if n.type == "BSDF_PRINCIPLED")
    # The figure's own face: the one image node that isn't an extra (safe to re-run after the mixes were removed)
    base = next(n for n in t.nodes if n.type == "TEX_IMAGE" and n.image and n.image.name.startswith("face_"))
    col, alpha = base.outputs["Color"], base.outputs["Alpha"]
    alpha_linked = b.inputs["Alpha"].is_linked
    for i, fname in enumerate(files[1:], 1):
        tex = t.nodes.new("ShaderNodeTexImage")
        tex.name = f"extra{i}"
        tex.image = bpy.data.images.load(os.path.join(TEXTURES, fname + ".png"), check_existing=True)
        val = t.nodes.new("ShaderNodeValue")
        val.name = f"face{i}"
        val.outputs[0].default_value = 0.0
        # The Mix node has a float, a vector and a colour version of each socket under the same name, so they're picked by type
        mc = t.nodes.new("ShaderNodeMix")
        mc.name = f"mixc{i}"
        mc.data_type = "RGBA"
        sock = lambda node, side, kind: next(s for s in getattr(node, side) if s.enabled and s.type == kind and (side == "outputs" or s.name in ("A", "B", "Factor")))
        ins = [s for s in mc.inputs if s.enabled]
        t.links.new(val.outputs[0], ins[0])
        rgba = [s for s in ins if s.type == "RGBA"]
        t.links.new(col, rgba[0])
        t.links.new(tex.outputs["Color"], rgba[1])
        col = next(s for s in mc.outputs if s.enabled and s.type == "RGBA")
        ma = t.nodes.new("ShaderNodeMix")
        ma.name = f"mixa{i}"
        ma.data_type = "FLOAT"
        ins = [s for s in ma.inputs if s.enabled]
        t.links.new(val.outputs[0], ins[0])
        t.links.new(alpha, ins[1])
        t.links.new(tex.outputs["Alpha"], ins[2])
        alpha = next(s for s in ma.outputs if s.enabled and s.type == "VALUE")
    t.links.new(col, b.inputs["Base Color"])
    # The face is a decal over the head, so its transparency always has to reach the shader (a re-run removes the old link with the old mix nodes)
    t.links.new(alpha, b.inputs["Alpha"])


for fig, files in FACES.items():
    mixer(fig, files)


def world_to_local(ob):
    """3x3 that turns a world offset into the piece's delta_location, taken with the rig at rest. Stored on the piece for the shots."""
    arm = ob.parent
    bone = arm.data.bones[ob.parent_bone]
    m = (arm.matrix_world.to_3x3() @ bone.matrix_local.to_3x3()).inverted()
    ob["w2l"] = [m[i][j] for i in range(3) for j in range(3)]


def copy_piece(src, arm_name, name):
    """The same piece on another figure: all the heroes share one rest pose, so the copy sits in the same place on its head or chest."""
    old = OB.get(name)
    if old:
        OB.remove(old, do_unlink=True)
    ob = src.copy()
    ob.name = name
    for c in src.users_collection:
        c.objects.link(ob)
    ob.parent = OB[arm_name]
    ob.parent_type = "BONE"
    ob.parent_bone = src.parent_bone
    ob.matrix_parent_inverse = src.matrix_parent_inverse.copy()
    ob.matrix_basis = src.matrix_basis.copy()
    return ob


for fig in ("father", "child"):
    copy_piece(OB["pardo_shades"], fig + "_arm", fig + "_shades")
    copy_piece(OB["pardo_chain"], fig + "_arm", fig + "_chain")
for n in ("pardo_shades", "pardo_rob_shades", "pardo_rob_nose", "pardo_rob_mask", "father_shades", "father_chain", "child_shades", "child_chain"):
    world_to_local(OB[n])

# The joint the interrogator snaps together, kept in its set and moved by the shots
c = bpy.data.collections["set_interrogatorio"]
old = OB.get("joint_gag")
if old:
    OB.remove(old, do_unlink=True)
j = place("joint", c, FAR)
j.name = "joint_gag"

# The bench: a thought bubble over Pardo carrying six dark "sad" bricks, which fly off one per word until it pops on "mal"
import math
from brick_lib import Bricks
from set_lib import abs_mat, mesh_ob
pc = bpy.data.collections["set_parque"]
po = origin("parque")
for ob in [o for o in pc.objects if o.name.startswith(("sad_", "thought_", "puff_"))]:
    OB.remove(ob, do_unlink=True)


def ellipsoid(name, centre, r, mat):
    v, f = [], []
    rows, cols = 10, 18
    for i in range(rows + 1):
        a = math.pi * i / rows
        for k in range(cols):
            b = 2 * math.pi * k / cols
            v.append((r[0] * math.sin(a) * math.cos(b), r[1] * math.sin(a) * math.sin(b), r[2] * math.cos(a)))
    for i in range(rows):
        for k in range(cols):
            p, q = i * cols + k, i * cols + (k + 1) % cols
            f.append((p, p + cols, q + cols, q))
    ob = mesh_ob(name, v, f, [mat], pc)
    ob.location = centre
    ob["home"] = list(centre)
    return ob


cloud_m = abs_mat("thought cloud", "f6f6f2", 0.3)
BUB = (po[0] + 0.15, po[1] + 0.3, po[2] + 0.68)
ellipsoid("thought_bubble", BUB, (0.16, 0.05, 0.11), cloud_m)
ellipsoid("puff_0", (po[0] + 0.06, po[1] + 0.27, po[2] + 0.52), (0.022, 0.022, 0.022), cloud_m)
ellipsoid("puff_1", (po[0] + 0.1, po[1] + 0.28, po[2] + 0.57), (0.034, 0.03, 0.03), cloud_m)
SAD = ["3b3f6b", "2f2f38", "4a3a5a", "34405a", "2a2a30", "45384f"]
for i, col in enumerate(SAD):
    sb = Bricks(f"sad_{i}", pc, (0, 0, 0), seed=40 + i)
    sb.brick(-1, -1, -1.5, 2, 2, 3, col, studs=True)
    ob = sb.build()
    ob.scale = (0.5, 0.5, 0.5)
    x = BUB[0] - 0.09 + (i % 3) * 0.09
    z = BUB[2] + 0.035 - (i // 3) * 0.07
    ob.location = (x, BUB[1] - 0.055, z)
    ob.rotation_euler = (math.radians(90), 0, math.radians((i * 23) % 30 - 15))
    ob["home"] = list(ob.location)
    ob["home_rot"] = list(ob.rotation_euler)
save()
print("=== GAGS DONE", flush=True)
