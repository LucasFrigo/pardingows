# Step 3: the cast. Pardo restyled as a glossy vinyl toy, with a mouth and a thumb. Berg is the second rig with a lizard head modelled here, a suit and a tie.
# Three more rigged Bergs make the crew. Everything lands in the "rigs" collection, and the rigs stay in their rest pose.
import bpy, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib, set_lib; importlib.reload(set_lib)
from set_lib import blobs, gloss, recentre, smooth, srgb
import lib; importlib.reload(lib)
from lib import BONES, SCALE
from mathutils import Matrix, Vector

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


def tex_image(mat):
    for n in mat.node_tree.nodes:
        if n.type == "TEX_IMAGE" and n.image:
            return n.image
    return None


# ---- Materials: each textured part turns into glossy plastic
rig_mats = {m for o in OB if o.type == "MESH" and o.parent in (ARM1, ARM2) for m in o.data.materials if m and m.name.startswith("Material.")}
for m in rig_mats:
    im = tex_image(m)
    if im:
        gloss(m.name, image=im, rough=0.27, coat=0.65, spec=0.55)
gloss("gold", rgb="f2c230", rough=0.2, coat=0.3, metal=1.0)
gloss("gold dark", rgb="b98a18", rough=0.3, coat=0.2, metal=1.0)
gloss("shades black", rgb="10121f", rough=0.08, coat=1.0, spec=0.8)
gloss("shades shine", rgb="ffffff", rough=0.2, emit=1.0)

# ---- Smooth the rigid parts. Fine bits like the chain and glasses keep their own shape.
STIFF = {"chain", "medallion", "shades"}
for ob in [o for o in OB if o.type == "MESH" and o.parent == ARM1]:
    smooth(ob, 0 if ob.name in STIFF else 1)
for p in OB["shades"].data.polygons:
    p.use_smooth = False
OB["shades"].data.update()


# ---- Where the head and chest are, in armature space
def arm_centre(ob, arm):
    inv = arm.matrix_world.inverted()
    pts = [inv @ (ob.matrix_world @ Vector(c)) for c in ob.bound_box]
    lo = Vector(tuple(min(p[i] for p in pts) for i in range(3)))
    hi = Vector(tuple(max(p[i] for p in pts) for i in range(3)))
    return (lo + hi) / 2, (hi - lo) / 2


HEAD_C, HEAD_R = arm_centre(OB["head"], ARM1)
BODY_C, BODY_R = arm_centre(OB["body"], ARM1)
print("head centre", HEAD_C, "radii", HEAD_R, "body", BODY_C, BODY_R)


def on_bone(ob, arm, alias, centre):
    """Hangs a piece on a bone with its origin at centre (armature space), so scaling it later pivots there. Rest pose assumed."""
    recentre(ob, centre)
    ob.parent = arm
    ob.parent_type = "BONE"
    ob.parent_bone = BONES[alias]
    bpy.context.view_layer.update()
    ob.matrix_world = arm.matrix_world @ Matrix.Translation(centre)
    bpy.context.view_layer.update()
    ob["rest_scale"] = list(ob.scale)
    ob["rest_rot"] = list(ob.rotation_euler)
    return ob


# ---- Pardo's mouth: closed it sinks behind the painted smile, open it covers it. Its size follows the vocals.
dark, tongue = gloss("boca", rgb="3a1218", rough=0.5, coat=0.2), gloss("lingua", rgb="e8626c", rough=0.4, coat=0.4)
mc = HEAD_C + Vector((0, -HEAD_R.y * 0.86, -HEAD_R.z * 0.52))
mouth = blobs("P1_boca", [("ball", mc, (0.62, 0.34, 0.42), 0, None), ("ball", mc + Vector((0, -0.2, -0.17)), (0.38, 0.2, 0.16), 1, None)], [dark, tongue], coll)
on_bone(mouth, ARM1, "head", mc)

# ---- Thumb for the thumbs up, on the +X hand. Hidden at scale 0 until wanted.
hand_b = ARM1.data.bones[BONES["handR"]]
tc = hand_b.head_local + (hand_b.tail_local - hand_b.head_local) * 0.5 + Vector((-0.1, -0.35, 0))
skin = OB["hands.001"].data.materials[0]
thumb = blobs("P1_polegar", [("ball", tc + Vector((0, 0, 0.42)), (0.2, 0.2, 0.55), 0, None)], [skin], coll)
on_bone(thumb, ARM1, "handR", tc)

# ---- Berg: own copies of the meshes, so he can wear other materials
lizard = gloss("berg pele", rgb="3fa98a", rough=0.28, coat=0.7, spec=0.6)
lizard2 = gloss("berg pele escura", rgb="2a7a68", rough=0.3, coat=0.6)
nose_m = gloss("berg nariz", rgb="d9c23f", rough=0.16, coat=1.0, spec=0.8)
suit = gloss("berg terno", rgb="2c3350", rough=0.42, coat=0.25)
shoe = gloss("berg sapato", rgb="15141a", rough=0.12, coat=1.0, spec=0.8)
shirt = gloss("berg camisa", rgb="f4f3ee", rough=0.45, coat=0.1)
tie = gloss("berg gravata", rgb="d4262f", rough=0.25, coat=0.7)
crest = gloss("berg crista", rgb="6a46b8", rough=0.3, coat=0.6)
eye_w = gloss("berg olho", rgb="ffffff", rough=0.1, coat=1.0)
eye_p = gloss("berg pupila", rgb="101018", rough=0.05, coat=1.0)

WEAR = {"P2_torso": suit, "P2_upper arms": suit, "P2_upper arms.001": suit, "P2_lower arms": suit, "P2_lower arms.001": suit, "P2_hands": lizard, "P2_hands.001": lizard,
        "P2_upper legs": suit, "P2_upper legs.001": suit, "P2_lower legs": suit, "P2_lower legs.001": suit, "P2_heels": shoe, "P2_heels.001": shoe, "P2_toes": shoe, "P2_toes.001": shoe,
        "P2_head": lizard, "P2_tail": lizard2}
for n in ("P2_hat", "P2_ears", "P2_nose", "P2_shades", "P2_chain", "P2_medallion"):
    OB.remove(OB[n], do_unlink=True)
for n, m in WEAR.items():
    ob = OB[n]
    ob.data = ob.data.copy()
    ob.data.materials.clear()
    ob.data.materials.append(m)
    smooth(ob, 1)

c = HEAD_C
face = []
# Snout comes forward from the face. Eyes bulge on top, like a lizard villager.
face.append(("ball", c + Vector((0, -1.05, -0.28)), (1.0, 0.92, 0.58), 0, None))
face.append(("ball", c + Vector((0, -1.08, -0.78)), (0.82, 0.74, 0.24), 1, None))  # lower jaw
for sx in (-1, 1):
    face.append(("ball", c + Vector((sx * 0.68, -0.42, 0.86)), (0.5, 0.5, 0.5), 0, None))
    face.append(("ball", c + Vector((sx * 0.68, -0.74, 0.94)), (0.36, 0.26, 0.36), 2, None))
    face.append(("ball", c + Vector((sx * 0.62, -0.98, 0.92)), (0.15, 0.08, 0.2), 3, None))
    face.append(("ball", c + Vector((sx * 0.68, -0.72, 1.3)), (0.5, 0.2, 0.14), 1, (0, sx * 14, 0)))  # cross brows
for k, (y, h) in enumerate(((-0.45, 0.42), (-0.05, 0.56), (0.35, 0.58), (0.72, 0.44), (1.02, 0.3))):
    face.append(("cone", c + Vector((0, y, 1.0 - k * 0.08 - (0.25 if k > 2 else 0))), (0.2, 0.26, h), 4, (-12 + k * 14, 0, 0)))
face.append(("ball", c + Vector((0, -1.5, -0.56)), (0.86, 0.3, 0.05), 5, None))  # the mouth line
head_parts = blobs("P2_cara", face, [lizard, lizard2, eye_w, eye_p, crest, gloss("berg boca", rgb="20301c", rough=0.6, coat=0)], coll)
on_bone(head_parts, ARM2, "head", c)

# His nose is its own object: the close-up points at it and it glows in the last shot.
nc = c + Vector((0, -1.96, 0.02))
nose = blobs("P2_nariz", [("ball", nc, (0.74, 0.66, 0.6), 0, None), ("ball", nc + Vector((-0.28, -0.52, 0.2)), (0.13, 0.1, 0.13), 1, None),
                          ("ball", nc + Vector((0.28, -0.52, 0.2)), (0.13, 0.1, 0.13), 1, None)], [nose_m, eye_p], coll)
on_bone(nose, ARM2, "head", nc)

# Shirt front and tie on the chest. The tie pivots at the knot so it can stand straight up.
chest = BODY_C + Vector((0, -BODY_R.y * 0.8, BODY_R.z * 0.32))
sh = blobs("P2_camisa", [("ball", chest, (0.44, 0.34, 0.58), 0, None)], [shirt], coll)
on_bone(sh, ARM2, "spine", chest)
knot = chest + Vector((0, -0.32, 0.3))
tie_ob = blobs("P2_gravata", [("ball", knot, (0.17, 0.12, 0.14), 0, None), ("ball", knot + Vector((0, -0.03, -0.62)), (0.25, 0.08, 0.56), 0, None)], [tie], coll)
on_bone(tie_ob, ARM2, "spine", knot)
OB["P2_tail"].scale = [s * 1.5 for s in OB["P2_tail"].scale]  # the tail grows into a lizard's


# ---- Crew: full copies of the Berg rig, sharing meshes
def copy_rig(prefix):
    arm = ARM2.copy()
    arm.name = prefix + "_arm"
    coll.objects.link(arm)
    root = OB.new(prefix, None)
    coll.objects.link(root)
    root.scale = (SCALE,) * 3
    body = OB.new(prefix + "_body", None)
    coll.objects.link(body)
    body.parent = root
    arm.parent = body
    arm.matrix_parent_inverse = Matrix.Identity(4)
    arm.location = ARM2.location
    for child in [o for o in OB if o.parent == ARM2]:
        ch = child.copy()
        ch.name = child.name.replace("P2_", prefix + "_")
        coll.objects.link(ch)
        ch.parent = arm
        ch.parent_type = "BONE"
        ch.parent_bone = child.parent_bone
        ch.matrix_parent_inverse = child.matrix_parent_inverse
    return root


for p in ("B1", "B2", "B3"):
    copy_rig(p)
set_lib.save()
print("cast ok", sorted(o.name for o in OB if o.type == "ARMATURE"))
