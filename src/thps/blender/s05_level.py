# Step 3b: the plaza, in metres. Travel is +X. Safe to re-run: rebuilds the "level" collection.
#   x -12..20   run-up plaza, ledge at x 6..16
#   x  20..32   avenue crossing the plaza (the police stop)
#   x  32..90   second plaza: funbox and stairs at 38..47, quarter pipe at 74
import bpy, os, sys, math, importlib, random
sys.path.insert(0, r"C:\Users\lukeg\Projetos\pardingows\src\thps\blender")
import lib; importlib.reload(lib)
from lib import Mesh, collection, make_mat, srgb

TEX = r"C:\Users\lukeg\Projetos\pardingows\blender\solucao\textures"
coll = collection("level")
rnd = random.Random(4)


def tex_mat(name, image, metres_per_tile, tint=None):
    """Box-projected texture in object space, so patterns stay continuous across a level at the origin."""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    n = m.node_tree.nodes
    n.clear()
    out = n.new("ShaderNodeOutputMaterial")
    bsdf = n.new("ShaderNodeBsdfDiffuse")
    coord = n.new("ShaderNodeTexCoord")
    mp = n.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1 / metres_per_tile,) * 3
    tex = n.new("ShaderNodeTexImage")
    img = bpy.data.images.get(image)
    if img is None:
        img = bpy.data.images.load(os.path.join(TEX, image + ".png"))
    tex.image = img
    tex.interpolation = "Closest"
    tex.projection = "BOX"
    tex.projection_blend = 0.0
    tree = m.node_tree
    tree.links.new(coord.outputs["Object"], mp.inputs["Vector"])
    tree.links.new(mp.outputs[0], tex.inputs["Vector"])
    if tint:
        mul = n.new("ShaderNodeMix")
        mul.data_type = "RGBA"
        mul.blend_type = "MULTIPLY"
        mul.inputs[0].default_value = 1.0
        mul.inputs[6].default_value = (*srgb(tint), 1)
        tree.links.new(tex.outputs[0], mul.inputs[7])
        tree.links.new(mul.outputs[2], bsdf.inputs["Color"])
    else:
        tree.links.new(tex.outputs[0], bsdf.inputs["Color"])
    tree.links.new(bsdf.outputs[0], out.inputs[0])
    return m


concrete = tex_mat("lv concrete", "tx_concrete", 2.0)
ledge = tex_mat("lv ledge", "tx_ledge", 1.0)
asphalt = tex_mat("lv asphalt", "tx_asphalt", 5.0)
pedra = tex_mat("lv pedra", "tx_pedra", 6.0)
pich = tex_mat("lv pichacao", "tx_pichacao", 9.0)
tower = [tex_mat("lv tower a", "tx_tower", 12.0), tex_mat("lv tower b", "tx_tower", 12.0, "e0b48c"),
         tex_mat("lv tower c", "tx_tower", 12.0, "9fb6c9"), tex_mat("lv tower d", "tx_tower", 12.0, "d8cfa0")]
louvre = tex_mat("lv louvre", "tx_louvre", 5.0)
white = make_mat("lv white", "ece8da")
yellow = make_mat("lv yellow", "e8b923")
green = make_mat("lv green", "3e7a35")
green_d = make_mat("lv green dark", "2b5a2a")
trunk = make_mat("lv trunk", "5a3d27")
steel = make_mat("lv steel", "8f949c")
dark = make_mat("lv dark", "23252b")
blue = make_mat("lv orelhao", "1e70c9")
red_neon = make_mat("lv sign red", "ff3a2f", emit=1.2)
plate = make_mat("lv plate", "1a3fa0")


def box_obj(name, x0, x1, y0, y1, z0, z1, mat):
    m = Mesh().box(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), ((x1 - x0) / 2, (y1 - y0) / 2, (z1 - z0) / 2))
    return m.build(name, [mat], None, coll)


# ---- Ground
box_obj("ground", -60, 200, -90, 90, -0.2, 0.0, asphalt)
box_obj("plaza a", -40, 20, -11, 11, 0.0, 0.03, pedra)
box_obj("plaza b", 32, 92, -11, 11, 0.0, 0.03, pedra)

# Road markings on the avenue: zebra crossing along the plaza line, then a centre dash either way
m = Mesh()
for k in range(10):
    y = -9.5 + k * 2.1
    m.box((26, y, 0.012), (5.0, 0.55, 0.012))
for y in list(range(-88, -12, 7)) + list(range(13, 88, 7)):
    m.box((26, y, 0.012), (0.1, 1.6, 0.012))
m.build("road paint", [white], None, coll)

# ---- First plaza
box_obj("ledge", 6, 16, -0.35, 0.35, 0.0, 0.5, ledge)
m = Mesh()
m.box((11, -0.36, 0.25), (5.0, 0.01, 0.25))
m.build("ledge edge", [yellow], None, coll)

# low stained walls with tags frame the plaza
for name, y0, y1 in (("wall south", -11, -10.6), ("wall north", 10.6, 11)):
    box_obj(name + " a", -40, 19, y0, y1, 0, 3.2, pich)
    box_obj(name + " b", 33, 92, y0, y1, 0, 3.2, pich)


def planter(x, y, r=1.1):
    outline = [(x + r * math.cos(k * math.pi / 3), y + r * math.sin(k * math.pi / 3)) for k in range(6)]
    Mesh().prism(outline, 0, 0.6, 0).build("planter", [concrete], None, coll)
    Mesh().prism([(x + 0.8 * (p[0] - x), y + 0.8 * (p[1] - y)) for p in outline], 0.5, 0.64, 0).build("soil", [dark], None, coll)
    # tree: trunk plus three stacked octagonal cones
    Mesh().prism([(x + 0.13 * math.cos(k * math.pi / 2), y + 0.13 * math.sin(k * math.pi / 2)) for k in range(4)], 0.6, 2.4).build("trunk", [trunk], None, coll)
    # Rounded, wide canopy like Sao Paulo street trees: squat double-cones overlapping
    me = Mesh()
    for dx, dy, cz, rad, h, mi in ((0, 0, 3.4, 1.9, 1.05, 0), (0.9, 0.5, 3.0, 1.1, 0.75, 1), (-0.8, -0.6, 3.1, 1.15, 0.8, 1), (0.1, -0.2, 4.2, 1.2, 0.8, 0)):
        i = len(me.v)
        for k in range(8):
            a = k * math.pi / 4 + rnd.uniform(-0.1, 0.1)
            me.v.append((x + dx + rad * math.cos(a), y + dy + rad * math.sin(a), cz))
        me.v.append((x + dx, y + dy, cz + h))
        me.v.append((x + dx, y + dy, cz - h))
        for k in range(8):
            b = (k + 1) % 8
            me.f.append((i + k, i + b, i + 8))
            me.fm.append(mi)
            me.f.append((i + b, i + k, i + 9))
            me.fm.append(mi)
    me.build("leaves", [green, green_d], None, coll)


for x, y in ((-4, -7), (3, 7), (14, -8), (19 - 3, 8), (40, 8.5), (56, -8), (64, 8)):
    planter(x, y)


def bench(x, y):
    m = Mesh()
    m.box((x, y, 0.45), (1.1, 0.25, 0.05), 0)
    for sx in (-0.85, 0.85):
        m.box((x + sx, y, 0.2), (0.06, 0.22, 0.2), 1)
    m.build("bench", [ledge, steel], None, coll)


bench(-8, 6.5)
bench(10, 5.5)
bench(52, 7.5)


def street_light(x, y, side):
    m = Mesh()
    m.box((x, y, 3.6), (0.07, 0.07, 3.6), 0)
    m.box((x, y + side * 0.9, 7.1), (0.05, 0.9, 0.05), 0)
    m.box((x, y + side * 1.7, 7.0), (0.18, 0.3, 0.07), 1)
    m.build("street light", [steel, white], None, coll)


for x in (-10, 18, 34, 58, 86):
    street_light(x, -9.5, 1)
    street_light(x + 6, 9.5, -1)

# Orelhao: the Brazilian phone shell on a post, the most local thing on set
def orelhao(x, y, yaw):
    me = Mesh()
    rings = [(0.05, 2.32), (0.34, 2.28), (0.5, 2.1), (0.56, 1.8), (0.5, 1.5), (0.4, 1.32)]
    sides = 10
    for r, z in rings:
        for k in range(sides):
            a = 2 * math.pi * k / sides
            me.v.append((x + r * math.cos(a), y + r * math.sin(a) * 0.9 - 0.08, z))
    n = len(rings)
    for ring in range(n - 1):
        for k in range(sides):
            # leave a gap at the front so it reads as a shell
            if ring >= 2 and k in (6, 7, 8):
                continue
            a, b = k, (k + 1) % sides
            me.f.append((ring * sides + a, (ring + 1) * sides + a, (ring + 1) * sides + b, ring * sides + b))
            me.fm.append(0)
    me.box((x, y + 0.28, 0.75), (0.05, 0.05, 0.75), 1)
    me.box((x, y + 0.15, 1.55), (0.15, 0.08, 0.2), 2)
    o = me.build("orelhao", [blue, steel, dark], None, coll)
    return o


orelhao(11, -7.5, 0)
orelhao(44, -8.8, 0)

# Street sign, in the blue of real Sao Paulo plates
sign_bg = box_obj("sign plate", 17.0, 19.2, -9.6, -9.55, 2.6, 3.1, plate)

# ---- Second plaza: funbox (ramp, deck, stairs, rail)
RUN_UP = [(36, 0.0), (39, 1.2)]
m = Mesh()
y0, y1 = -5, 5
# ramp up, deck, solid side walls
m.v += [(36, y0, 0.03), (36, y1, 0.03), (39, y1, 1.2), (39, y0, 1.2)]
m.f.append((0, 3, 2, 1)); m.fm.append(0)
m.build("funbox ramp", [concrete], None, coll)
box_obj("funbox deck", 39, 44, y0, y1, 0, 1.2, concrete)
for k in range(6):
    h = 1.2 - k * 0.2
    box_obj("stair", 44 + k * 0.45, 44.45 + k * 0.45, y0, y1, 0, h - 0.2, ledge)
for sy in (-1, 1):
    m = Mesh()
    m.box((37.5, sy * 5.05, 0.6), (1.5, 0.05, 0.6))
    m.build("funbox side", [yellow], None, coll)

# Handrail down the stairs
rail = Mesh()
z = lambda x: 1.2 - (x - 44) * (1.2 / 2.7) + 0.75
for k in range(7):
    x = 44 + k * 0.45
    rail.box((x, 2.0, (z(x) + (1.2 - k * 0.2)) / 2), (0.03, 0.03, (z(x) - (1.2 - k * 0.2)) / 2))
slope = math.atan2(1.2, 2.7)
rail.build("handrail posts", [steel], None, coll)
tube = Mesh().box((0, 0, 0), (1.55, 0.04, 0.04)).build("handrail", [yellow], None, coll)
tube.location = (45.35, 2.0, z(45.35))
tube.rotation_euler = (0, slope, 0)

# ---- Quarter pipe: concrete wall with a curved transition, grey coping on top
QP_X, QP_H, QP_R = 74.0, 3.5, 3.5
profile = [(QP_X + QP_R * math.sin(a), QP_R * (1 - math.cos(a))) for a in [k * (math.pi / 2) * 0.98 / 8 for k in range(9)]]
qy0, qy1 = -10, 10
m = Mesh()
n = len(profile)
for x, z_ in profile:
    m.v.append((x, qy0, z_ + 0.03))
for x, z_ in profile:
    m.v.append((x, qy1, z_ + 0.03))
for k in range(n - 1):
    m.f.append((k, k + 1, n + k + 1, n + k))
    m.fm.append(0)
top_x, top_z = profile[-1]
m.build("quarter pipe face", [concrete], None, coll)
box_obj("quarter pipe back", QP_X + QP_R, QP_X + QP_R + 0.6, qy0, qy1, 0, top_z + 0.03, pich)
box_obj("quarter pipe deck", top_x - 0.02, QP_X + QP_R + 0.6, qy0, qy1, top_z, top_z + 0.04, ledge)
c = Mesh().box((top_x, 0, top_z + 0.02), (0.06, 10, 0.06)).build("coping", [steel], None, coll)

# ---- City backdrop: blocks of towers along both sides and behind
def tower_box(x, y, w, d, h, mat, skirt=True):
    box_obj("tower", x - w / 2, x + w / 2, y - d / 2, y + d / 2, 0, h, mat)
    if rnd.random() < 0.6:  # tags climbing the top of the building, the Sao Paulo signature
        box_obj("tags", x - w / 2 - 0.1, x + w / 2 + 0.1, y - d / 2 - 0.1, y + d / 2 + 0.1, h - 7, h, pich)
    if rnd.random() < 0.5:
        box_obj("water tank", x - 2, x + 2, y - 2, y + 2, h, h + 3, concrete)


for x in range(-40, 190, 17):
    for side, base in ((-1, -30), (1, 30)):
        if abs(x - 26) < 9:
            continue
        w, d = rnd.randint(12, 15), rnd.randint(12, 18)
        tower_box(x, side * (base + rnd.randint(-2, 8)), w, d, rnd.randint(18, 62), rnd.choice(tower))
    if rnd.random() < 0.9:
        tower_box(x + 5, rnd.choice((-1, 1)) * rnd.randint(50, 80), 14, 16, rnd.randint(30, 80), rnd.choice(tower))
for y in range(-70, 75, 18):
    tower_box(150 + rnd.randint(-8, 8), y, 15, 15, rnd.randint(22, 70), rnd.choice(tower))

# A wavy Copan-style block in louvres behind the quarter pipe: the skyline's landmark
outline = []
for k in range(25):
    t = k / 24
    outline.append((118 + 20 * math.sin(t * math.pi * 2) * 0.35, -46 + 92 * t))
for k in range(24, -1, -1):
    t = k / 24
    outline.append((118 + 20 * math.sin(t * math.pi * 2) * 0.35 + 12, -46 + 92 * t))
outline.reverse()
Mesh().prism(outline, 0, 80).build("copan", [louvre], None, coll)

# Rooftop letters over the plaza
curve = bpy.data.curves.new("rooftop", "FONT")
curve.body = "PARDINGOWS"
curve.size = 7.0
curve.extrude = 0.5
curve.align_x = "CENTER"
curve.resolution_u = 1
curve.materials.append(red_neon)
sign = bpy.data.objects.new("rooftop", curve)
coll.objects.link(sign)
sign.location = (112, 2, 84)
sign.rotation_euler = (math.radians(90), 0, math.radians(90))
Mesh().box((112.5, 2, 82.5), (0.4, 24, 1.5)).build("rooftop frame", [steel], None, coll)
box_obj("rooftop base", 103, 124, -32, 36, 0, 81, tower[0])

bpy.ops.wm.save_mainfile()
print("level ok,", len(coll.objects), "objects,", sum(len(o.data.polygons) for o in coll.objects if o.type == "MESH"), "polys")
