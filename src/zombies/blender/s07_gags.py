# Step 7: the gag props, each its own object parked out of sight until a shot wants it.
# Held props are placed in world space by the shots: at this resolution a hand that is close enough reads as holding it.
import bpy, bmesh, importlib, json, math, os, sys
from mathutils import Matrix, Vector
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "thps", "blender"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "planeta", "blender"))
sys.path.insert(0, HERE)
import lib, build, set_lib
importlib.reload(lib); importlib.reload(build); importlib.reload(set_lib)
from lib import BONES, SCALE, Mesh, make_mat
from build import attach
from set_lib import DOOR, FAR, MUGS, WORK, fresh, place

OB = bpy.data.objects
sc = bpy.context.scene
gags = fresh("gags", sc)
NAMES = json.load(open(os.path.join(WORK, "cast_bones.json")))
coll_rigs = bpy.data.collections["rigs"]


def prop(name, mesh_builder, mats):
    ob = mesh_builder.build(name, mats, None, gags)
    ob.location = FAR
    return ob


def ball(name, radii, mat, u=10, v=8):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=u, v_segments=v, radius=1.0, matrix=Matrix.Diagonal((*radii, 1)))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = False
    ob = OB.new(name, me)
    gags.objects.link(ob)
    ob.location = FAR
    return ob


def own_copy(name, source, centre=True):
    """A prefab's mesh as an object with its own data, origin at its centre."""
    me = OB["PF_" + source].data.copy()
    pts = [v.co for v in me.vertices]
    lo = Vector(min(p[i] for p in pts) for i in range(3))
    hi = Vector(max(p[i] for p in pts) for i in range(3))
    if centre:
        me.transform(Matrix.Translation(-(lo + hi) / 2))
    ob = OB.new(name, me)
    gags.objects.link(ob)
    ob.location = FAR
    return ob


# ---- The roasted stick: origin at the grip, pointing along +X, one new and one burnt
WOOD = make_mat("pau", "8a5a2c")
COAL = make_mat("pau carvao", "120e0c")
EMBER = make_mat("brasa", "ff5a18", emit=3.0)
for name, mat, tip in (("pau_novo", WOOD, WOOD), ("pau_carvao", COAL, EMBER)):
    m = Mesh()
    m.box((0.55, 0, 0), (0.55, 0.022, 0.022), 0)
    m.box((1.06, 0, 0), (0.05, 0.034, 0.034), 1)
    prop(name, m, [mat, tip])

# ---- Small flying bits
BLOOD = bpy.data.materials["sangue"]
SMOKE = make_mat("fumaca", "3a3a3e")
for i in range(16):
    m = Mesh()
    m.box((0, 0, 0), (0.028, 0.028, 0.028), 0)
    prop(f"sq_{i}", m, [BLOOD])
for i in range(6):
    m = Mesh()
    m.box((0, 0, 0), (0.05, 0.05, 0.05), 0)
    prop(f"fumo_{i}", m, [SMOKE])

# ---- Fire from the sky: a ball with a tail along +Z behind it
HOT = make_mat("meteoro", "ffb040", emit=5.0)
TAIL = make_mat("meteoro cauda", "e8501a", emit=3.0)
for i in range(5):
    m = Mesh()
    k = 0.2
    m.box((0, 0, 0), (k, k, k), 0)
    m.box((0, 0, 0), (k * 0.7, k * 1.25, k * 0.7), 0)
    m.box((0, 0, 0), (k * 1.25, k * 0.7, k * 0.7), 0)
    for dx, dy, h in ((0, 0, 3.4), (0.14, 0.05, 2.5), (-0.13, -0.06, 2.8), (0.06, -0.13, 2.2), (-0.05, 0.13, 2.4)):
        j = len(m.v)
        w = k * 0.55
        m.v += [(dx - w, dy - w, k * 0.5), (dx + w, dy - w, k * 0.5), (dx + w, dy + w, k * 0.5), (dx - w, dy + w, k * 0.5), (dx * 1.5, dy * 1.5, k * h)]
        m.f += [(j, j + 1, j + 4), (j + 1, j + 2, j + 4), (j + 2, j + 3, j + 4), (j + 3, j, j + 4)]
        m.fm += [1] * 4
    prop(f"meteoro_{i}", m, [HOT, TAIL])
sky_fire = make_mat("hall ceu fogo", "e8601a", emit=2.5)
for side in "ab":
    m = Mesh()
    m.v += [(-0.6, 0, -1.25), (0.6, 0, -1.25), (0.6, 0, 1.25), (-0.6, 0, 1.25)]
    m.f.append((0, 1, 2, 3))
    m.fm.append(0)
    prop(f"ceu_fogo_{side}", m, [sky_fire])

# A jagged black hole in the floor, scaled up from nothing
hole = Mesh()
n = 13
hole.v += [((0.75 + 0.35 * ((k * 5) % 3) / 2) * math.cos(2 * math.pi * k / n), (0.75 + 0.35 * ((k * 5) % 3) / 2) * math.sin(2 * math.pi * k / n), 0) for k in range(n)]
hole.f.append(tuple(range(n)))
hole.fm.append(0)
prop("buraco", hole, [make_mat("buraco", "020202")])

# ---- The egg and the drool
ovo_mat = make_mat("ovo", "e8dfc8")
ball("ovo", (0.24, 0.24, 0.33), ovo_mat)
DROOL = make_mat("baba", "b8c8a0")
for i in range(4):
    m = Mesh()
    m.box((0, 0, 0), (0.006, 0.006, 0.04), 0)
    prop(f"baba_{i}", m, [DROOL])

# ---- The syringe, needle along +X
# Built here: the Sketchfab model is too fine to read at 270 px. Chunky barrel, glowing green fluid, needle along +X.
m = Mesh()
m.box((-0.1, 0, 0), (0.36, 0.1, 0.1), 0)        # barrel
m.box((-0.02, 0, 0), (0.27, 0.075, 0.105), 1)   # fluid, showing front and back
m.box((-0.02, 0.075, 0), (0.27, 0.03, 0.075), 1)
m.box((-0.02, -0.075, 0), (0.27, 0.03, 0.075), 1)
m.box((0.28, 0, 0), (0.03, 0.12, 0.12), 2)      # collar
m.box((0.58, 0, 0), (0.28, 0.012, 0.012), 3)    # needle
m.box((-0.56, 0, 0), (0.12, 0.035, 0.035), 2)   # plunger
m.box((-0.68, 0, 0), (0.02, 0.1, 0.1), 2)
m.box((-0.46, 0, 0), (0.02, 0.17, 0.17), 2)     # finger grip
prop("seringa", m, [make_mat("seringa vidro", "c8d8d0"), make_mat("seringa fluido", "40e850", emit=1.4), make_mat("seringa metal", "6a7078"), make_mat("seringa agulha", "e8e8f0", emit=0.5)])

own_copy("cola", "cola")
white = make_mat("pomba branca", "e8e8e0")
for i in range(3):
    dove = own_copy(f"pomba_{i}", "pomba") if i == 0 else None
    if dove:
        dove.data.materials.clear()
        dove.data.materials.append(white)
        dove_mesh = dove.data
    else:
        ob = OB.new(f"pomba_{i}", dove_mesh)
        gags.objects.link(ob)
        ob.location = FAR

# ---- The wig once it's off her head: the same mesh, origin at its cap, world size
wig_src = OB["ZF_peruca"]
me = wig_src.data.copy()
top = max(v.co.z for v in me.vertices)
xs = [v.co.x for v in me.vertices]
ys = [v.co.y for v in me.vertices]
me.transform(Matrix.Translation(Vector((-(min(xs) + max(xs)) / 2, -(min(ys) + max(ys)) / 2, -top))))
wig = OB.new("peruca_mao", me)
gags.objects.link(wig)
wig.location = FAR

# ---- The door swings on an empty at its hinge
pivot = OB.new("porta_pivo", None)
gags.objects.link(pivot)
pivot.location = (DOOR[0] - 0.56, DOOR[1], DOOR[2])
door = own_copy("porta", "porta", centre=False)
door.parent = pivot
door.location = (0.56, 0, 0)

# ---- A glint across his shades
glint = make_mat("brilho", "ffffff", emit=4.0)
m = Mesh()
m.v += [(-0.09, 0, 0), (0, 0, 0.022), (0.09, 0, 0), (0, 0, -0.022), (0, 0, 0.09), (0.022, 0, 0), (0, 0, -0.09), (-0.022, 0, 0)]
m.f += [(0, 1, 2, 3), (4, 5, 6, 7)]
m.fm += [0, 0]
prop("brilho", m, [glint])

# ---- Pistol on his hand, hidden by scale until a shot wants it. Barrel down the arm, grip towards the front of the hand.
pist = own_copy("P1_pistola", "pistola")
hb = OB["Armature"].data.bones[BONES["handR"]]
along = (hb.tail_local - hb.head_local).normalized()
upv = Vector((0, -1, 0))
upv = (upv - along * upv.dot(along)).normalized()
side = upv.cross(along)
R = Matrix((along, side, upv)).transposed().to_4x4()
pist.data.transform(Matrix.Translation(hb.head_local + along * 0.75) @ R @ Matrix.Scale(1.15 / SCALE * 0.42, 4))
for c in list(pist.users_collection):
    c.objects.unlink(pist)
coll_rigs.objects.link(pist)
attach(pist, OB["Armature"], BONES["handR"])
pist["rest_scale"] = list(pist.scale)

# ---- Mugshot props: one eye for caolha, the missing teeth for banguela
EYE_B = make_mat("olho vazio", "e8e0c0", emit=0.6)
PATCH = make_mat("tapa olho", "06060a")
g = OB["ZC_skin"].vertex_groups[NAMES["ZC"]["head"]].index
pts = [v.co for v in OB["ZC_skin"].data.vertices if any(e.group == g and e.weight > 0.5 for e in v.groups)]
lo = Vector(min(p[i] for p in pts) for i in range(3))
hi = Vector(max(p[i] for p in pts) for i in range(3))
c = (lo + hi) / 2
hx, hz = (hi.x - lo.x) / 2, (hi.z - lo.z) / 2
m = Mesh()
m.box((c.x - hx * 0.42, lo.y + 0.02, c.z + hz * 0.1), (hx * 0.3, 0.02, hz * 0.16), 0)
m.box((c.x + hx * 0.42, lo.y + 0.02, c.z + hz * 0.1), (hx * 0.3, 0.02, hz * 0.16), 0)
m.box((c.x + hx * 0.42, lo.y + 0.005, c.z + hz * 0.1), (hx * 0.13, 0.01, hz * 0.08), 1)
ca = attach(m.build("ZC_caolha", [PATCH, EYE_B], None, coll_rigs), OB["ZC_arm"], NAMES["ZC"]["head"])
ca.scale = (0, 0, 0)

head = OB["ZP_cabeca"]
inv = OB["ZP_arm"].matrix_world.inverted() @ head.matrix_world
pts = [inv @ v.co for v in head.data.vertices]
lo = Vector(min(p[i] for p in pts) for i in range(3))
hi = Vector(max(p[i] for p in pts) for i in range(3))
c = (lo + hi) / 2
hx, hz = (hi.x - lo.x) / 2, (hi.z - lo.z) / 2
TOOTH = make_mat("dente", "e8e0b8")
MOUTH = make_mat("boca aberta", "060202")
m = Mesh()
m.box((c.x, lo.y + 0.012, lo.z + hz * 1.1), (hx * 0.42, 0.02, hz * 0.14), 0)
m.box((c.x + hx * 0.16, lo.y - 0.004, lo.z + hz * 1.18), (hx * 0.09, 0.006, hz * 0.06), 1)
ba = attach(m.build("ZP_banguela", [MOUTH, TOOTH], None, coll_rigs), OB["ZP_arm"], NAMES["ZP"]["head"])
ba.scale = (0, 0, 0)

# ---- Black void lit from the front, for the select screen's photos
for name, x, y, z, e in (("mug_luz", 0.8, -2.2, 2.4, 95), ("mug_fill", -1.5, -1.6, 1.4, 40)):
    li = OB.new(name, bpy.data.lights.new(name, "POINT"))
    gags.objects.link(li)
    li.location = (MUGS[0] + x, MUGS[1] + y, MUGS[2] + z)
    li.data.energy = e
    li.data.color = (1.0, 0.9, 0.8)
    li.data.use_shadow = False

set_lib.save()
print("=== GAGS DONE", len(gags.objects), flush=True)
