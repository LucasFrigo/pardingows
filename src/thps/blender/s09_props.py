# Step 3f: small props and the fallen-apart smurf. Safe to re-run: rebuilds the "props" collection.
import bpy, sys, math, importlib, random
from mathutils import Matrix, Vector
sys.path.insert(0, r"C:\Users\lukeg\Projetos\pardingows\src\thps\blender")
import lib; importlib.reload(lib)
from lib import Mesh, collection, empty, make_mat, SCALE

coll = collection("props")
rnd = random.Random(7)


def sphere(m, c, r, mi=0, rings=4, sides=8, squash=1.0):
    """Low-poly UV sphere appended to a Mesh."""
    base = len(m.v)
    for i in range(1, rings):
        a = math.pi * i / rings
        for k in range(sides):
            t = 2 * math.pi * k / sides
            m.v.append((c[0] + r * math.sin(a) * math.cos(t), c[1] + r * math.sin(a) * math.sin(t), c[2] + r * squash * math.cos(a)))
    top, bot = len(m.v), len(m.v) + 1
    m.v += [(c[0], c[1], c[2] + r * squash), (c[0], c[1], c[2] - r * squash)]
    for k in range(sides):
        b = (k + 1) % sides
        m.f.append((top, base + k, base + b)); m.fm.append(mi)
        m.f.append((bot, base + (rings - 2) * sides + b, base + (rings - 2) * sides + k)); m.fm.append(mi)
        for i in range(rings - 2):
            m.f.append((base + i * sides + k, base + (i + 1) * sides + k, base + (i + 1) * sides + b, base + i * sides + b))
            m.fm.append(mi)


def bone_child(ob, arm, bone, world):
    ob.parent = arm
    ob.parent_type = "BONE"
    ob.parent_bone = bone
    bpy.context.view_layer.update()
    ob.matrix_world = world


def phone(name, screen_up=False):
    """Back faces outwards, so no shot ever shows the screen contents: the lit face is plain light."""
    shell = make_mat("phone shell", "16171d")
    glow = make_mat("phone glow", "9fc4ee", emit=0.9)
    m = Mesh()
    m.box((0, 0, 0), (0.06, 0.012, 0.12), 0)
    m.box((0, -0.0135, 0), (0.052, 0.002, 0.108), 1)
    m.box((-0.03, 0.0135, 0.09), (0.015, 0.003, 0.015), 2)  # camera bump
    return m.build(name, [shell, glow, make_mat("phone lens", "5a5f6a")], None, coll)


arm1 = bpy.data.objects["Armature"]
cop = bpy.data.objects["Object_4"]

# The phone in the smurf's hand, in the cop's hand, and on the ground for the finale
p_smurf = phone("phone smurf")
p_smurf.scale = (1.3, 1.3, 1.3)
bpy.context.view_layer.update()
bone_child(p_smurf, arm1, "Bone.011", p_smurf.matrix_world)  # the hand on the camera side when he faces the cop
p_smurf.location = (0, 0, 0)
p_smurf.scale = (1.3 / SCALE,) * 3

p_cop = phone("phone cop")
p_cop.parent = bpy.data.objects["COP"]
p_cop.rotation_euler = (math.radians(-8), 0, math.radians(180))  # back to camera, lit face towards him
p_cop.scale = (0.8,) * 3  # s10 keeps it in his hand

p_ground = phone("phone ground")
p_ground.rotation_euler = (math.radians(-90), 0, math.radians(25))  # lit face up: plain light, nothing on it
p_ground.location = (65.9, -1.22, 0.05)
p_ground.scale = (2.0,) * 3

# Copy of the board for the cop to hold overhead
held = bpy.data.objects["P1_board"].copy()
held.name = "board held"
coll.objects.link(held)
held.parent = None
held.scale = (SCALE,) * 3
bone_child(held, cop, "RightHand_016", Matrix.Identity(4))
held.location = (0.05, 0.1, 0)
held.rotation_euler = (0, 0, 0)
held.scale = (SCALE,) * 3

# C-P-F letters, collected like S-K-A-T-E
gold = make_mat("letter gold", "ffd23f", emit=1.2)
for ch in "CPF":
    cu = bpy.data.curves.new("letter " + ch, "FONT")
    cu.body = ch
    cu.size = 0.55
    cu.align_x = "CENTER"
    cu.extrude = 0.05
    cu.resolution_u = 1
    cu.materials.append(gold)
    ob = bpy.data.objects.new("letter " + ch, cu)
    coll.objects.link(ob)
    ob.rotation_euler = (math.radians(90), 0, 0)

# "!" over the cop's head
m = Mesh()
m.box((0, 0, 0.14), (0.05, 0.03, 0.17))
m.box((0, 0, -0.14), (0.05, 0.03, 0.05))
m.build("bang", [make_mat("bang", "ffe23a", emit=2.0)], None, coll)

# Blood pool: an irregular flat blob
outline = []
for k in range(14):
    r = 1.0 + (0.28 if k % 2 else -0.18) * rnd.uniform(0.5, 1.2)
    a = 2 * math.pi * k / 14
    outline.append((r * math.cos(a), r * math.sin(a)))
Mesh().prism(outline, 0, 0.004).build("blood", [make_mat("blood", "8e0d0d")], None, coll)

# Blob shadows, as the game had
shadow = make_mat("blob shadow", "0a0a12", alpha=0.55)
for name in ("P1_shadow", "P2_shadow", "COP_shadow"):
    Mesh().prism([(0.42 * math.cos(k * math.pi / 4), 0.42 * math.sin(k * math.pi / 4)) for k in range(8)], 0, 0.002).build(name, [shadow], None, coll)

# Sparks pool, grind and short-circuit
spark = make_mat("spark", "ffd35a", emit=4.0)
for i in range(16):
    Mesh().box((0, 0, 0), (0.018, 0.018, 0.018)).build(f"spark {i}", [spark], None, coll)

# Banana split, big enough to read in close-up: boat, bananas, three scoops, whipped cream, cherry
dish = make_mat("split dish", "c8e6f0")
banana = make_mat("split banana", "f4d23c")
pink = make_mat("split pink", "f08ab0")
vanilla = make_mat("split vanilla", "f7edd0")
choc = make_mat("split choc", "5e3620")
red = make_mat("split cherry", "d81f2a")
m = Mesh()
outline = [(0.25, 0), (0.16, 0.07), (-0.16, 0.07), (-0.25, 0), (-0.16, -0.07), (0.16, -0.07)]
m.prism(outline, 0.0, 0.05, 0)
for sy in (-1, 1):
    m.box((0, sy * 0.055, 0.075), (0.21, 0.025, 0.025), 1)
for x, mi in ((-0.11, 2), (0, 3), (0.11, 4)):
    sphere(m, (x, 0, 0.1), 0.055, mi)
sphere(m, (0, 0, 0.165), 0.03, 3, 3, 6)
sphere(m, (0, 0, 0.2), 0.016, 5, 3, 6)
split = m.build("banana split", [dish, banana, pink, vanilla, choc, red], None, coll)
split.scale = (1.5,) * 3

# Olive oil bottle and its pour
m = Mesh()
hexa = [(0.05 * math.cos(k * math.pi / 3), 0.05 * math.sin(k * math.pi / 3)) for k in range(6)]
m.prism(hexa, 0, 0.2, 0)
m.prism([(x * 0.42, y * 0.42) for x, y in hexa], 0.2, 0.3, 0)
m.prism([(x * 0.5, y * 0.5) for x, y in hexa], 0.3, 0.33, 1)
m.box((0, -0.0505, 0.1), (0.04, 0.002, 0.05), 2)
bottle = m.build("oil bottle", [make_mat("oil glass", "2f5d2a"), make_mat("oil cap", "c7a22e"), make_mat("oil label", "efe6c2")], None, coll)
bottle.scale = (1.5,) * 3
stream = Mesh().box((0, 0, -0.5), (0.008, 0.008, 0.5)).build("oil stream", [make_mat("oil", "c9b01c", emit=0.5)], None, coll)

# Fallen-apart smurf: one copy of each part, unparented, animated in the shots script
pieces = collection("pieces")
for child in arm1.children:
    if child.type != "MESH" or child.name.startswith("phone"):
        continue
    c = child.copy()
    c.name = "piece " + child.name
    c.parent = None
    pieces.objects.link(c)
    c.matrix_parent_inverse = Matrix.Identity(4)
print("props ok,", len(coll.objects), "props,", len(pieces.objects), "pieces")
bpy.ops.wm.save_mainfile()
