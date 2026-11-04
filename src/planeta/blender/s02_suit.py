# Step 2: dresses both smurfs. P1 is the white-suited hero with an open-window helmet, shades and chain.
# P2 is Pardomon: orange suit and an original creature mask that covers his whole head.
# Every piece is a rigid mesh on one bone, like the smurf itself. Safe to re-run: removes its own objects first.
import bpy, math, sys, importlib
from mathutils import Vector
sys.path.insert(0, r"C:\Users\lukeg\Projetos\pardingows\src\thps\blender")
sys.path.insert(0, r"C:\Users\lukeg\Projetos\pardingows\src\planeta\blender")
import lib, build
importlib.reload(lib); importlib.reload(build)
from lib import Mesh, make_mat
from build import attach, disc, on_ball, ring, shell

OB = bpy.data.objects
coll = bpy.data.collections["rigs"]
HEAD_C = Vector((0, -0.69, 2.85))  # helmet centre in armature space, just above the head sphere's
HEAD_R = 1.62

for ob in list(OB):
    if ob.name.startswith(("suit_", "mask_", "P2_marker", "ears", "tail", "P2_ears", "P2_tail", "P2_nose", "P2_shades", "P2_chain", "P2_medallion", "P2_head")):
        OB.remove(ob, do_unlink=True)

arms = {"P1": OB["Armature"], "P2": OB["P2_arm"]}
OB["P1"].location, OB["P2"].location = (0, 0, 0), (6, 0, 0)
for a in arms.values():
    a.data.pose_position = "REST"
bpy.context.view_layer.update()

PALETTE = {
    "P1": dict(suit=make_mat("suit white", "e8e6dc"), trim=make_mat("suit grey", "6d7078"), band=make_mat("suit green", "1f9e4a"),
               band2=make_mat("suit yellow", "f2c81e"), glove=make_mat("suit glove", "9a9ca2"), boot=make_mat("suit boot", "55575e")),
    "P2": dict(suit=make_mat("suit orange", "e8742a"), trim=make_mat("suit grey", "6d7078"), band=make_mat("suit dark", "33343c"),
               band2=make_mat("suit cream", "f0e2bd"), glove=make_mat("suit dark", "33343c"), boot=make_mat("suit dark", "33343c")),
}
RED, LIT_Y, LIT_G = make_mat("suit lamp red", "ff3a2e", emit=1.5), make_mat("suit lamp yellow", "ffd21e", emit=1.5), make_mat("suit lamp green", "3aff6a", emit=1.5)
GOLD = make_mat("suit visor", "d9a520", emit=0.15)
RIM = make_mat("suit rim", "2a2b31")


def surface_y(prefix, z, side):
    """Where the torso's front (-1) or back (+1) surface is at height z."""
    torso = OB["body" if prefix == "P1" else "P2_torso"]
    ev = torso.evaluated_get(bpy.context.evaluated_depsgraph_get())
    to_local = torso.matrix_world.inverted() @ arms[prefix].matrix_world
    origin = to_local @ Vector((0, side * 6, z))
    hit, loc, _, _ = ev.ray_cast(origin, (to_local.to_3x3() @ Vector((0, -side, 0))).normalized())
    return (to_local.inverted() @ loc).y if hit else side * 0.6


def dress(prefix):
    pal = PALETTE[prefix]
    arm = arms[prefix]
    pre = "" if prefix == "P1" else "P2_"
    for part, mat in (("body" if prefix == "P1" else "P2_torso", pal["suit"]), (pre + "upper arms", pal["suit"]), (pre + "upper arms.001", pal["suit"]),
                      (pre + "lower arms", pal["suit"]), (pre + "lower arms.001", pal["suit"]), (pre + "upper legs", pal["suit"]), (pre + "upper legs.001", pal["suit"]),
                      (pre + "lower legs", pal["suit"]), (pre + "lower legs.001", pal["suit"]), (pre + "hands", pal["glove"]), (pre + "hands.001", pal["glove"]),
                      (pre + "heels", pal["boot"]), (pre + "heels.001", pal["boot"]), (pre + "toes", pal["boot"]), (pre + "toes.001", pal["boot"])):
        ob = OB[part]
        # P2 shares its meshes with P1 until now, so it needs its own before recolouring
        if ob.data.users > 1:
            ob.data = ob.data.copy()
        ob.data.materials.clear()
        ob.data.materials.append(mat)
        for p in ob.data.polygons:
            p.material_index = 0

    # Backpack and front control box, placed on the real torso surface
    back = surface_y(prefix, 1.0, 1)
    front = surface_y(prefix, 0.55, -1)
    m = Mesh()
    m.box((0, back + 0.42, 1.05), (0.72, 0.42, 0.95), 0)
    m.box((0, back + 0.42, 2.05), (0.5, 0.3, 0.1), 1)
    m.box((0, back + 0.86, 1.05), (0.5, 0.03, 0.68), 2)
    for sx in (-1, 1):
        ring(m, (sx * 0.3, back + 0.42, 2.15), (sx * 0.3, back + 0.42, 2.45), 0.14, 1, 6)
    m.box((0, front - 0.13, 0.55), (0.42, 0.13, 0.26), 1)
    attach(m.build(f"suit_pack {prefix}", [pal["suit"], pal["trim"], pal["band"]], None, coll), arm, "Bone.016")

    m = Mesh()
    for x, mi in ((-0.24, 0), (0, 1), (0.24, 2)):
        m.box((x, front - 0.28, 0.6), (0.08, 0.03, 0.08), mi)
    m.box((0, front - 0.28, 0.42), (0.3, 0.02, 0.05), 3)
    attach(m.build(f"suit_lamps {prefix}", [RED, LIT_Y, LIT_G, pal["band2"]], None, coll), arm, "Bone.016")

    # Rings at the waist, shoulders, wrists and ankles, each on the bone it should follow
    m = Mesh()
    ring(m, (0, -0.28, 0.02), (0, -0.28, 0.26), 0.86, 0, 8)
    attach(m.build(f"suit_waist {prefix}", [pal["trim"]], None, coll), arm, "Bone.016")
    for side, upper, fore, shin in ((1, "Bone.002", "Bone.003", "Bone.006"), (-1, "Bone.009", "Bone.010", "Bone.013")):
        m = Mesh()
        ring(m, (side * 0.6, -0.6, 1.62), (side * 0.72, -0.5, 1.28), 0.36, 0, 8)
        attach(m.build(f"suit_shoulder {prefix}{side}", [pal["band"]], None, coll), arm, upper)
        m = Mesh()
        ring(m, (side * 1.03, -0.27, 0.46), (side * 1.09, -0.22, 0.30), 0.34, 0, 8)
        attach(m.build(f"suit_cuff {prefix}{side}", [pal["band2"]], None, coll), arm, fore)
        m = Mesh()
        ring(m, (side * 0.62, -0.2, -1.12), (side * 0.56, -0.1, -1.32), 0.42, 0, 8)
        attach(m.build(f"suit_ankle {prefix}{side}", [pal["band"]], None, coll), arm, shin)


dress("P1")
dress("P2")

# Hero's helmet: a window for the face, a gold sun visor pushed up over the brow, comm caps where the ears were
WIN_LAT, WIN_LON = (-2, -1, 0, 1), (-2, -1, 0, 1)
keep = lambda la, lo: la >= -3 and not (la in WIN_LAT and lo in WIN_LON)
paint = lambda la, lo: 1 if la == 2 and lo in WIN_LON else 0
m = Mesh()
shell(m, HEAD_C, HEAD_R, keep, paint, rim_mi=2)
for side in (-1, 1):
    ring(m, (side * (HEAD_R - 0.04), HEAD_C.y, HEAD_C.z), (side * (HEAD_R + 0.16), HEAD_C.y, HEAD_C.z), 0.4, 3, 8)
    ring(m, (side * (HEAD_R + 0.16), HEAD_C.y, HEAD_C.z), (side * (HEAD_R + 0.22), HEAD_C.y, HEAD_C.z), 0.2, 2, 6)
ring(m, (1.2, HEAD_C.y + 0.1, HEAD_C.z + 1.0), (1.32, HEAD_C.y + 0.1, HEAD_C.z + 2.0), 0.05, 2, 4)  # antenna
attach(m.build("suit_helmet", [PALETTE["P1"]["suit"], GOLD, RIM, PALETTE["P1"]["trim"]], None, coll), arms["P1"], "Bone.001")
m = Mesh()
ring(m, (0, -0.72, 1.45), (0, -0.74, 1.85), 1.02, 0, 12)
attach(m.build("suit_collar", [PALETTE["P1"]["trim"]], None, coll), arms["P1"], "Bone.016")

# Pardomon's mask: an original creature, teal with long swept ears, huge eyes, a cream muzzle and a gem on the brow
C = Vector((0, -0.69, 2.8))
R = 1.6
TEAL, TEAL_D, CREAM = make_mat("mask teal", "1fa8a0"), make_mat("mask teal dark", "0d5f63"), make_mat("mask cream", "f4e6c4")
EYE, SHINE, IRIS = make_mat("mask eye", "12121c"), make_mat("mask shine", "ffffff", emit=0.6), make_mat("mask iris", "ffd02e", emit=0.3)
BLUSH, GEM = make_mat("mask blush", "ff7a3c"), make_mat("mask gem", "ff3a7a", emit=1.0)
m = Mesh()
shell(m, C, R, lambda la, lo: la >= -4, lambda la, lo: 1 if la <= -2 and lo in (-2, -1, 0, 1) else 0, rim_mi=0)
ALL = [TEAL, CREAM, EYE, SHINE, IRIS, BLUSH, GEM, TEAL_D]
for side in (-1, 1):
    disc(m, C, R, side * 27, 16, 0.5, 0.62, 2, lift=0.03)
    disc(m, C, R, side * 27, 22, 0.28, 0.34, 4, lift=0.06)
    disc(m, C, R, side * 22, 30, 0.13, 0.15, 3, lift=0.09)
    disc(m, C, R, side * 66, -8, 0.36, 0.26, 5, lift=0.03)
    # long ear swept up and back: a four-sided spike, dark at the tip
    base = on_ball(C, R * 0.92, side * 62, 40)
    tip = Vector((side * 2.25, 0.75, 6.0))
    mid = base.lerp(tip, 0.55)
    i = len(m.v)
    for c, w in ((base, 0.62), (mid, 0.42)):
        for dx, dy in ((-1, -0.45), (1, -0.45), (1, 0.45), (-1, 0.45)):
            m.v.append((c.x + dx * w, c.y + dy * w, c.z))
    m.v.append(tuple(tip))
    for k in range(4):
        a, b = k, (k + 1) % 4
        m.f.append((i + a, i + b, i + 4 + b, i + 4 + a)); m.fm.append(0)
        m.f.append((i + 4 + a, i + 4 + b, i + 8)); m.fm.append(7)
# Snout, little fangs and the gem
muzzle = on_ball(C, R * 0.93, 0, -22)
ring(m, muzzle, muzzle + Vector((0, -0.42, -0.08)), 0.62, 1, 8)
m.box(muzzle + Vector((0, -0.45, 0.2)), (0.14, 0.05, 0.09), 2)
m.box(muzzle + Vector((0, -0.45, -0.22)), (0.36, 0.05, 0.05), 2)
for sx in (-1, 1):
    m.box(muzzle + Vector((sx * 0.2, -0.47, -0.33)), (0.06, 0.02, 0.07), 3)
m.box(on_ball(C, R + 0.02, 0, 48), (0.17, 0.08, 0.17), 6)
attach(m.build("mask_pardomon", ALL, None, coll), arms["P2"], "Bone.001")

for a in arms.values():
    a.data.pose_position = "POSE"
bpy.ops.wm.save_mainfile()
print("suits ok;", sum(1 for o in OB if o.name.startswith(("suit_", "mask_"))), "new objects")
