# Step 5: the eight worlds, each its own collection far from the others, so only the one on screen is rendered. Each is built facing -Y:
# the action is around its origin, the camera on the -Y side, and x, y below are in studs from that origin.
import bpy, importlib, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import set_lib, brick_lib, world_data
importlib.reload(set_lib); importlib.reload(brick_lib); importlib.reload(world_data)
from set_lib import BRICK, FIG, P, PLATE, TEXTURES, abs_mat, fresh, place, save, srgb
from brick_lib import Bricks, linear
from world_data import SETS, origin

OB = bpy.data.objects
scene = bpy.context.scene

WHITE, GREY, DARK, BLACK = "f2f2ee", "a8acb0", "5c6166", "22252a"
RED, BRICKRED, TAN, SAND, BROWN = "c8202a", "9c3a2c", "d9c08f", "c7b083", "6e4628"
BLUE, SKY, YELLOW, GREEN, DGREEN = "0d62b5", "6fb7e8", "f2c300", "2c9a48", "1c6a35"


def lights(coll, o, name, sun=None, spots=()):
    """Lights belong to their set, so they switch off with it."""
    if sun:
        en, rot, col, ang = sun
        s = bpy.data.objects.new(name + " sun", bpy.data.lights.new(name + " sun", "SUN"))
        coll.objects.link(s)
        s.data.energy = en
        s.data.color = srgb(col)
        s.data.angle = math.radians(ang)
        s.rotation_euler = [math.radians(a) for a in rot]
    for i, (kind, pos, en, col, size) in enumerate(spots):
        l = bpy.data.lights.new(f"{name} l{i}", kind)
        l.energy = en
        l.color = srgb(col)
        if kind == "SPOT":
            l.spot_size = math.radians(size)
            l.spot_blend = 0.5
            l.shadow_soft_size = 0.05
        elif kind == "AREA":
            l.size = size
        else:
            l.shadow_soft_size = size
        ob = bpy.data.objects.new(f"{name} l{i}", l)
        coll.objects.link(ob)
        ob.location = (o[0] + pos[0], o[1] + pos[1], o[2] + pos[2])
        if kind in ("SPOT", "AREA"):
            tgt = pos[3:] if len(pos) > 3 else (0, 0, 0)
            d = (o[0] + tgt[0] - ob.location.x, o[1] + tgt[1] - ob.location.y, o[2] + tgt[2] - ob.location.z)
            from mathutils import Vector
            ob.rotation_euler = Vector(d).to_track_quat("-Z", "Y").to_euler()


def facade(b, x, y, w, courses, col, frame=WHITE, glass="4f86b8", win_w=4, win_c=5, door=False, trim=None):
    """A building front: staggered bricks with rows of windows, a band of trim and a flat top."""
    openings = []
    rows = max((courses - 4) // (win_c + 3), 1)
    per = max((w - 2) // (win_w + 3), 1)
    margin = (w - per * win_w - (per - 1) * 3) // 2
    wins = []
    for r in range(rows):
        c0 = 4 + r * (win_c + 3)
        for i in range(per):
            a = margin + i * (win_w + 3)
            if door and r == 0 and i == per // 2:
                continue
            openings.append((a, a + win_w, c0, c0 + win_c - 1))
            wins.append((a, c0))
    if door:
        a = margin + (per // 2) * (win_w + 3)
        openings.append((a, a + win_w, 0, 7))
    b.wall(x, y, 0, w, "x", courses, col, openings, studs_top=False)
    for a, c0 in wins:
        # Glass panel, set back, with a white frame around it
        b.brick(x + a, y + 1, c0 * 3, win_w, 1, win_c * 3, glass, jitter=0.0)
        for k in range(win_w):
            b.brick(x + a + k, y, c0 * 3, 1, 1, 1, frame, jitter=0.0)
            b.brick(x + a + k, y, (c0 + win_c) * 3 - 1, 1, 1, 1, frame, jitter=0.0)
        for zz in range(c0 * 3 + 1, (c0 + win_c) * 3 - 1):
            b.brick(x + a, y, zz, 1, 1, 1, frame, jitter=0.0)
            b.brick(x + a + win_w - 1, y, zz, 1, 1, 1, frame, jitter=0.0)
    if door:
        a = margin + (per // 2) * (win_w + 3)
        b.brick(x + a, y + 1, 0, win_w, 1, 24, BROWN, jitter=0.0)
    if trim:
        b.brick(x - 1, y - 1, courses * 3, w + 2, 3, 2, trim, studs=True, stud_n=6)


def cloud(b, x, y, z, seed):
    r = random.Random(seed)
    for k in range(r.randint(5, 8)):
        nx, ny = r.choice((6, 8, 10, 12)), r.choice((4, 6))
        b.brick(x + r.randint(-14, 8), y, z + r.randint(0, 2) * 3, nx, ny, 3, "ffffff", jitter=0.0)


def backdrop_blocks(b, y, x0, x1, cols, hmin, hmax, seed):
    """A distant skyline of plain brick blocks, to close off every view."""
    r = random.Random(seed)
    x = x0
    while x < x1:
        w = r.randint(12, 26)
        h = r.randint(hmin, hmax)
        b.brick(x, y, 0, w, 6, h * 3, r.choice(cols))
        x += w


def build_rua():
    name = "rua"
    c = fresh("set_" + name, scene)
    o = origin(name)
    b = Bricks("rua bricks", c, o, seed=11)
    near = (-16, -24, 16, 12)
    b.floor(-56, -44, 112, 26, -1, ["3c3f45", "43464c"], near=near)  # road
    for i in range(-50, 54, 14):
        b.brick(i, -32, 0, 8, 2, 1, WHITE, jitter=0.0)
    b.brick(-56, -18, -1, 112, 2, 2, GREY, jitter=0.0)  # kerb
    b.floor(-56, -16, 112, 34, -1, ["b9bcbe", "aeb2b5"], near=near)  # pavement
    facade(b, -60, 18, 34, 42, ["b43a2c", "a93327", "bb4331"], door=True, trim=WHITE)
    facade(b, -26, 18, 26, 34, ["e0c88f", "d8bf85"], door=True, trim=BROWN)
    facade(b, 0, 18, 28, 50, ["3f7fb8", "3a76ad"], frame=WHITE, door=True, trim=YELLOW)
    facade(b, 28, 18, 34, 38, ["e7b53a", "dfad33"], frame=BROWN, door=True, trim=RED)
    backdrop_blocks(b, 60, -110, 110, ["88a0b6", "97acc0", "7f97ad"], 30, 70, 5)
    cloud(b, -40, 90, 260, 1)
    cloud(b, 26, 90, 300, 2)
    b.build()
    place("lamp", c, (o[0] - 1.45, o[1] - 0.7, o[2]))
    place("lamp", c, (o[0] + 1.75, o[1] - 0.7, o[2]))
    place("bike", c, (o[0] + 1.3, o[1] + 0.7, o[2]), rz=20)
    place("car_red", c, (o[0] - 0.95, o[1] - 2.05, o[2]), rz=90)
    place("bush", c, (o[0] - 1.1, o[1] + 1.1, o[2]))
    lights(c, o, name, sun=(3.2, (52, 6, 32), "fff1d8", 8))


def build_calendario():
    name = "calendario"
    c = fresh("set_" + name, scene)
    o = origin(name)
    b = Bricks("calendario bricks", c, o, seed=12)
    b.floor(-36, -36, 72, 56, -1, ["a9763f", "9f6e39", "b27f47"], tiles=(4, 6, 8), near=(-14, -24, 14, 14))
    b.wall(-36, 20, 0, 72, "x", 34, ["e6d2a4", "ddc896"], openings=[(10, 26, 10, 24)], studs_top=False)
    b.wall(-38, -36, 0, 56, "y", 34, ["d86c3a", "cf6434"], studs_top=False)
    b.wall(36, -36, 0, 56, "y", 34, ["d86c3a", "cf6434"], studs_top=False)
    b.brick(10, 21, 30, 16, 1, 45, "9fd4f5", jitter=0.0)
    for k in range(0, 16, 8):
        b.brick(10 + k, 20, 30, 1, 1, 45, WHITE, jitter=0.0)
    b.brick(25, 20, 30, 1, 1, 45, WHITE, jitter=0.0)
    b.brick(10, 20, 30, 16, 1, 1, WHITE, jitter=0.0)
    b.brick(10, 20, 74, 16, 1, 1, WHITE, jitter=0.0)
    b.brick(-36, 17, 0, 72, 3, 3, WHITE, jitter=0.0)  # skirting
    for i, col in enumerate((RED, BLUE, YELLOW)):  # a shelf of colourful bricks
        b.brick(-26 + i * 5, 18, 54, 4, 2, 6, col, studs=True)
    b.brick(-30, 18, 51, 22, 2, 1, BROWN)
    b.build()
    place("sofa", c, (o[0] + 0.85, o[1] + 1.12, o[2]))
    place("flowers", c, (o[0] - 1.9, o[1] + 1.2, o[2] + 0.02))
    # The calendar itself, large on the wall, until the gag brings it down
    img = bpy.data.images.load(os.path.join(TEXTURES, "calendar.png"), check_existing=True)
    m = abs_mat("calendar", "ffffff", 0.4)
    t = m.node_tree
    tex = t.nodes.new("ShaderNodeTexImage")
    tex.image = img
    t.links.new(tex.outputs[0], next(n for n in t.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"])
    w, h = 0.86, 1.14
    me = bpy.data.meshes.new("calendar")
    me.from_pydata([(-w / 2, 0, 0), (w / 2, 0, 0), (w / 2, 0, h), (-w / 2, 0, h)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name="UVMap")
    for l, q in zip(uv.data, ((0, 0), (1, 0), (1, 1), (0, 1))):
        l.uv = q
    me.materials.append(m)
    cal = bpy.data.objects.new("calendar", me)
    c.objects.link(cal)
    cal.location = (o[0] - 0.42, o[1] + 1.56, o[2] + 0.34)
    lights(c, o, name, sun=(2.2, (55, 0, 25), "fff0d0", 8), spots=[("AREA", (0, -1.4, 2.2, 0, 0, 0.3), 16, "fff4e0", 3)])


def build_cofre():
    name = "cofre"
    c = fresh("set_" + name, scene)
    o = origin(name)
    b = Bricks("cofre bricks", c, o, seed=13)
    b.floor(-40, -40, 80, 62, -1, ["4a4f55", "53585e", "454a50"], near=(-16, -28, 16, 16))
    walls = ["70767d", "666c73", "787e85"]
    b.wall(-40, 22, 0, 80, "x", 40, walls, openings=[(28, 52, 0, 19)], studs_top=False)  # a hole for the vault door, whose model runs deep
    b.wall(-42, -40, 0, 62, "y", 40, walls, studs_top=False)
    b.wall(40, -40, 0, 62, "y", 40, walls, studs_top=False)
    # Gold shelves on either side of the door
    for sx in (-34, 18):
        for lvl in (24, 48, 72):
            b.brick(sx, 19, lvl, 16, 3, 2, "3a3e44", studs=True, stud_n=8)
    b.build()
    place("vault", c, (o[0], o[1] + 1.76 + 1.69, o[2]))
    r = random.Random(4)
    for sx in (-2.72 + 0.64, 1.44 + 0.64):
        for lvl in (24, 48, 72):
            for k in range(7):
                place(r.choice(("gold", "cash")), c, (o[0] + sx + (k - 3) * 0.17, o[1] + 1.65, o[2] + (lvl + 2) * PLATE + 0.018), rz=r.choice((0, 180, 5, -6)))
    # Piles of cash on the floor
    for i in range(46):
        x, y = r.uniform(-1.5, 1.5), r.uniform(0.3, 1.45)
        if abs(x) < 0.5 and y < 1.0:
            continue
        place(r.choice(("cash", "cash", "gold")), c, (o[0] + x, o[1] + y, o[2] + r.randint(0, 2) * 0.05), rz=r.uniform(-40, 40))
    # The robbery is paused: bundles of cash and gold bars hang frozen in mid-air
    for i in range(34):
        x, y, z = r.uniform(-0.75, 0.75), r.uniform(-0.35, 1.0), r.uniform(0.3, 1.05)
        if abs(x) < 0.16 and y < 0.2 and z < 0.5:
            continue  # keep Pardo's face clear
        place(r.choice(("cash", "cash", "cash", "gold")), c, (o[0] + x, o[1] + y, o[2] + z), rz=r.uniform(0, 360), rx=r.uniform(-70, 70), ry=r.uniform(-70, 70))
    lights(c, o, name, spots=[("AREA", (0, -1.2, 2.6, 0, 0.4, 0.2), 150, "e6eeff", 3.5), ("SPOT", (-1.8, 0.8, 2.0, 0, 0.3, 0.3), 90, "ff3a22", 70), ("SPOT", (1.8, 0.8, 2.0, 0, 0.3, 0.3), 90, "ff3a22", 70), ("AREA", (0, 1.0, 2.2, 0, 1.76, 0.8), 70, "ffe0b0", 1.6)])


def build_parque():
    name = "parque"
    c = fresh("set_" + name, scene)
    o = origin(name)
    b = Bricks("parque bricks", c, o, seed=14)
    near = (-16, -24, 16, 14)
    b.floor(-64, -44, 128, 110, -1, ["3aa356", "349a4f", "42ab5c"], near=near)
    # A tan path crossing in front
    for i in range(-64, 64, 4):
        wob = int(3 * math.sin(i * 0.18))
        b.brick(i, -22 + wob, 0, 4, 12, 1, ["d9c08f", "cfb684"][(i // 4) % 2], studs=True, stud_n=12 if abs(i) < 20 else 6)
    # A brick bench behind Pardo
    for sx in (-7, 5):
        b.brick(sx, 2, 0, 2, 4, 6, BROWN, jitter=0.0)
    b.brick(-9, 1, 6, 18, 5, 1, "a06a38", studs=True)
    for sx in (-8, -1, 6):  # slats, so the bench back doesn't read as a wall
        b.brick(sx, 6, 7, 3, 1, 6, "a06a38")
    b.brick(-9, 6, 13, 18, 1, 2, "a06a38")
    # Rolling hills of stacked plates in the distance, then trees against the sky
    for k, (x, w, h, col) in enumerate(((-90, 80, 18, "2c8a45"), (-30, 70, 26, "2f934a"), (30, 80, 15, "2c8a45"))):
        for lvl in range(h):
            inset = lvl * 2
            b.brick(x + inset, 66, lvl * 3, w - inset * 2, 12, 3, col, jitter=0.02)
    cloud(b, -36, 96, 230, 3)
    cloud(b, 18, 96, 280, 4)
    cloud(b, -6, 96, 180, 5)
    b.build()
    place("tree", c, (o[0] - 1.7, o[1] + 1.4, o[2]))
    place("tree", c, (o[0] + 2.2, o[1] + 2.6, o[2]), rz=70, s=1.2)
    place("stump", c, (o[0] + 1.5, o[1] + 0.8, o[2]))
    place("plants", c, (o[0] - 0.1, o[1] + 2.6, o[2]))
    place("bush", c, (o[0] - 1.05, o[1] + 0.2, o[2]))
    place("flowers", c, (o[0] + 0.85, o[1] - 0.65, o[2] + 0.02))
    place("flowers", c, (o[0] - 0.9, o[1] - 0.55, o[2] + 0.02), rz=120)
    lights(c, o, name, sun=(3.4, (48, 6, 40), "fff0d0", 8))


def build_corrida():
    name = "corrida"
    c = fresh("set_" + name, scene)
    o = origin(name)
    b = Bricks("corrida bricks", c, o, seed=15)
    near = (-14, -26, 14, 10)
    b.floor(-60, -48, 120, 66, -1, ["3a3b41", "424349"], near=near)  # the street they run down
    for i in range(-14, 16, 4):  # zebra crossing
        b.brick(i, -10, 0, 2, 12, 1, WHITE, jitter=0.0, studs=True)
    b.brick(-60, 18, -1, 120, 2, 3, GREY, jitter=0.0)
    b.floor(-60, 20, 120, 12, 0, ["c5b9a7", "bbafa0"], near=None)
    facade(b, -62, 32, 40, 56, ["8d4a33", "85432e", "96513a"], frame="efe6d0", door=True, trim="efe6d0")
    facade(b, -22, 32, 30, 66, ["d2a26a", "c99a63"], frame=WHITE, door=True, trim=BROWN)
    facade(b, 8, 32, 26, 48, ["7c5c9e", "735592"], frame=WHITE, door=True, trim=YELLOW)
    facade(b, 34, 32, 30, 60, ["a74a3a", "9d4334"], frame="efe6d0", door=True, trim=WHITE)
    backdrop_blocks(b, 74, -110, 110, ["d59a78", "c98d70", "b98068"], 40, 90, 8)
    cloud(b, 28, 110, 300, 6)
    b.build()
    place("bus", c, (o[0] + 0.1, o[1] + 0.95, o[2]), rz=90)
    place("car_red", c, (o[0] + 1.95, o[1] + 0.2, o[2]), rz=90)
    place("lamp", c, (o[0] - 1.3, o[1] + 1.65, o[2] + 2 * PLATE))
    lights(c, o, name, sun=(3.4, (72, 0, 24), "ffc488", 8), spots=[("AREA", (0, -1.6, 1.3, 0, -0.2, 0.2), 14, "ffd9b0", 2.0)])


def build_praca():
    name = "praca"
    c = fresh("set_" + name, scene)
    o = origin(name)
    b = Bricks("praca bricks", c, o, seed=16)
    # A checker of pale tiles, wide enough to fill a crane shot
    for i in range(-96, 96, 8):
        for j in range(-96, 96, 8):
            col = "e4dcc8" if ((i + j) // 8) % 2 == 0 else "b9b4a8"
            b.brick(i, j, -1, 8, 8, 1, col, studs=True, stud_n=12 if -18 <= i < 18 and -30 <= j < 20 else 6)
    facade(b, -96, 96, 40, 60, ["c3613f", "b95a3a"], frame=WHITE, door=True, trim=WHITE)
    facade(b, -56, 96, 36, 76, ["e0c88f", "d8bf85"], frame=BROWN, door=True, trim=BROWN)
    facade(b, -20, 96, 44, 54, ["5f97c2", "578cb5"], frame=WHITE, door=True, trim=YELLOW)
    facade(b, 24, 96, 36, 70, ["e7b53a", "dfad33"], frame=BROWN, door=True, trim=RED)
    facade(b, 60, 96, 36, 58, ["b43a2c", "a93327"], frame=WHITE, door=True, trim=WHITE)
    backdrop_blocks(b, 120, -140, 140, ["9ab0c4", "8ea6bb"], 60, 110, 9)
    cloud(b, 40, 150, 420, 7)
    cloud(b, -60, 150, 460, 8)
    b.build()
    lights(c, o, name, sun=(3.3, (50, 8, 25), "fff1d8", 8))
    # The packed crowd: instances of each crowd figure, so hundreds cost next to nothing. Keep the front middle clear for Pardo.
    src = bpy.data.collections.get("crowd_src")
    if not src:
        src = bpy.data.collections.new("crowd_src")
        scene.collection.children.link(src)
    protos = {}
    for n in ("crook", "escapee", "policeman", "banker", "pepper", "brickster", "henchman", "sky", "dewey"):
        cc = bpy.data.collections.get("crowd " + n) or bpy.data.collections.new("crowd " + n)
        if cc.name not in src.children:
            src.children.link(cc)
        arm = OB[n + "_arm"]
        for ob in [OB["CH_" + n], arm] + list(arm.children):
            for u in list(ob.users_collection):
                if u.name != cc.name:
                    u.objects.unlink(ob)
            if cc.name not in [u.name for u in ob.users_collection]:
                cc.objects.link(ob)
        OB["CH_" + n].location = (0, 0, OB["CH_" + n]["z0"])
        protos[n] = cc
    # Excluded from the layer: they only render through their instances
    vl = bpy.context.view_layer.layer_collection.children
    if src.name in vl:
        vl[src.name].exclude = True
    r = random.Random(23)
    names = list(protos)
    spacing = 0.285
    count = 0
    for iy in range(-5, 34):
        for ix in range(-20, 21):
            x, y = ix * spacing + r.uniform(-0.035, 0.035), iy * spacing + r.uniform(-0.035, 0.035)
            if abs(x) < 0.3 and y < -0.2:
                continue
            e = bpy.data.objects.new(f"crowd.{count}", None)
            e.instance_type = "COLLECTION"
            e.instance_collection = protos[names[r.randrange(len(names))]]
            e.location = (o[0] + x, o[1] + y, o[2])
            e.rotation_euler = (0, 0, math.radians(r.uniform(-16, 16)))
            c.objects.link(e)
            count += 1
    print("  crowd instances", count, flush=True)


def build_interrogatorio():
    name = "interrogatorio"
    c = fresh("set_" + name, scene)
    o = origin(name)
    b = Bricks("interrogatorio bricks", c, o, seed=17)
    b.floor(-28, -30, 56, 44, -1, ["2c3037", "272a30"], near=(-14, -24, 14, 14))
    walls = ["3a414b", "353b44", "40474f"]
    # Behind Pardo, a dark one-way mirror
    b.wall(-28, 14, 0, 56, "x", 26, walls, openings=[(16, 40, 5, 17)], studs_top=False)
    b.brick(-12, 15, 15, 24, 1, 39, "0c0f14", jitter=0.0)
    b.wall(-30, -30, 0, 44, "y", 26, walls, studs_top=False)
    b.wall(28, -30, 0, 44, "y", 26, walls, studs_top=False)
    # A steel table at chest height for a seated figure, and Pardo's stool behind it
    b.brick(-8, -2, 8, 16, 9, 1, "6c7078", studs=True)
    for sx, sy in ((-7, -1), (5, -1), (-7, 5), (5, 5)):
        b.brick(sx, sy, 0, 2, 2, 8, "1f2226", jitter=0.0)
    b.brick(-2, 7, 0, 4, 3, 7, "1f2226", jitter=0.0)
    b.build()
    # The lamp hangs from one point, so it can swing: shade, cord, bulb, its light and a faint beam of light through the dust
    pivot = (o[0], o[1] + 0.2, o[2] + 1.5)
    lb = Bricks("interrog_lamp", c, (0, 0, 0), seed=3)
    lb.brick(-4, -4, -24, 8, 8, 2, "1a1c20", jitter=0.0)
    lb.brick(-3, -3, -22, 6, 6, 2, "1a1c20", jitter=0.0)
    lb.brick(-2, -2, -20, 4, 4, 2, "1a1c20", jitter=0.0)
    for z in range(-18, 0, 3):
        lb.brick(-0.5, -0.5, z, 1, 1, 3, BLACK, jitter=0.0)
    lamp = lb.build()
    lamp.location = pivot
    bulb = abs_mat("bulb", "fff2c4", 0.3, emit=18)
    from lib_shapes import plane
    bu = plane("bulb", c, (0, 0, -24 * PLATE - 0.003), 0.2, 0.2, bulb)
    bu.rotation_euler = (math.radians(90), 0, 0)
    bu.parent = lamp
    beam_m = bpy.data.materials.get("beam") or bpy.data.materials.new("beam")
    beam_m.use_nodes = True
    t = beam_m.node_tree
    t.nodes.clear()
    out = t.nodes.new("ShaderNodeOutputMaterial")
    mix = t.nodes.new("ShaderNodeMixShader")
    tr = t.nodes.new("ShaderNodeBsdfTransparent")
    em = t.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*srgb("ffe2a8"), 1)
    em.inputs["Strength"].default_value = 1.0
    mix.inputs[0].default_value = 0.07
    t.links.new(tr.outputs[0], mix.inputs[1])
    t.links.new(em.outputs[0], mix.inputs[2])
    t.links.new(mix.outputs[0], out.inputs[0])
    beam_m.surface_render_method = "BLENDED"
    v, f = [], []
    top_z, bot_z, r0, r1, n = -24 * PLATE, -1.2, 0.08, 0.42, 24
    for k in range(n):
        a = 2 * math.pi * k / n
        v.append((r0 * math.cos(a), r0 * math.sin(a), top_z))
        v.append((r1 * math.cos(a), r1 * math.sin(a), bot_z))
    for k in range(n):
        a, b2 = 2 * k, 2 * ((k + 1) % n)
        f.append((a, b2, b2 + 1, a + 1))
    me = bpy.data.meshes.new("beam")
    me.from_pydata(v, [], f)
    me.materials.append(beam_m)
    beam = bpy.data.objects.new("beam", me)
    c.objects.link(beam)
    beam.parent = lamp
    beam.visible_shadow = False
    sp = bpy.data.lights.new("interrog spot", "SPOT")
    sp.energy, sp.spot_size, sp.spot_blend, sp.shadow_soft_size = 90, math.radians(72), 0.25, 0.03
    sp.color = srgb("ffe6b8")
    spo = bpy.data.objects.new("interrog spot", sp)
    c.objects.link(spo)
    spo.parent = lamp
    spo.location = (0, 0, -24 * PLATE - 0.01)
    # Two interrogators, instanced from the crowd, near the camera with their backs half to it, both turned towards Pardo
    for n_, x, y, rz in (("policeman", -0.36, -0.32, 159), ("banker", 0.36, -0.3, -159)):
        e = bpy.data.objects.new("interrogator " + n_, None)
        e.instance_type = "COLLECTION"
        e.instance_collection = bpy.data.collections["crowd " + n_]
        e.location = (o[0] + x, o[1] + y, o[2])
        e.rotation_euler = (0, 0, math.radians(rz))
        c.objects.link(e)
    # Cold rim light from behind the mirror, and almost nothing else: the lamp does the work
    lights(c, o, name, spots=[("AREA", (0, 1.05, 1.1, 0, 0.2, 0.35), 45, "6f95d8", 1.2), ("AREA", (0, -1.8, 1.2, 0, 0.4, 0.3), 3, "8aa0c8", 2)])


def build_quarto():
    name = "quarto"
    c = fresh("set_" + name, scene)
    o = origin(name)
    b = Bricks("quarto bricks", c, o, seed=18)
    b.floor(-28, -30, 56, 42, -1, ["7b5433", "6f4b2e", "86603c"], near=(-16, -24, 16, 12))
    walls = ["3a4a86", "344279", "40508f"]
    b.wall(-28, 10, 0, 56, "x", 22, walls, openings=[(34, 44, 4, 12)], studs_top=False)  # the window, x from 6 to 16 studs
    b.wall(-30, -30, 0, 42, "y", 22, walls, studs_top=False)
    b.wall(28, -30, 0, 42, "y", 22, walls, studs_top=False)
    # A minifig-sized bed, 6 by 8 studs, head against the wall: base, mattress, blanket and pillow
    b.brick(-3, 0, 0, 6, 8, 3, BROWN, jitter=0.0)
    b.brick(-3, 0, 3, 6, 8, 2, WHITE, jitter=0.0)
    b.brick(-3, 0, 5, 6, 5, 1, "b52a2a", studs=True)
    b.brick(-2, 5, 5, 4, 2, 2, "eeeeea", studs=True)
    b.brick(-3, 8, 0, 6, 1, 12, BROWN, studs=True, jitter=0.0)
    # The bedside table
    b.brick(4, 5, 0, 3, 3, 7, "a06a38", studs=True, jitter=0.0)
    # A small striped rug at the foot of the bed
    for i in range(-6, 6, 2):
        b.brick(i, -7, 0, 2, 5, 1, ["d9a13a", "c23a2a"][(i // 2) % 2], studs=True)
    # A poster on the wall
    b.brick(-14, 9, 18, 7, 1, 15, "f2c300", jitter=0.0)
    b.brick(-13, 8, 20, 5, 1, 11, "c8202a", jitter=0.0)
    b.build()
    place("clock", c, (o[0] + 0.44, o[1] + 0.52, o[2] + 7 * PLATE + 0.018), rz=-20, s=0.6)
    place("flowers", c, (o[0] - 1.2, o[1] + 0.6, o[2] + 0.02), s=0.7)
    lights(c, o, name, spots=[("POINT", (0.55, 0.3, 0.55), 6, "ffcf8a", 0.12), ("AREA", (-0.9, -0.9, 1.6, 0, 0.3, 0.1), 40, "9bb4ff", 2), ("AREA", (0.8, 0.5, 0.8, 0, 0.3, 0.2), 10, "a8c0ff", 0.8)])
    # The night outside the window, with a moon
    mw = abs_mat("night window", "16224f", 0.5, emit=0.8)
    moon = abs_mat("moon", "fff6c9", 0.5, emit=5)
    from lib_shapes import plane
    plane("night window", c, (o[0] + 0.88, o[1] + 0.82, o[2] + 0.8), 0.9, 0.9, mw)
    plane("moon", c, (o[0] + 0.98, o[1] + 0.81, o[2] + 0.95), 0.16, 0.16, moon)


BUILD = dict(rua=build_rua, calendario=build_calendario, cofre=build_cofre, parque=build_parque, corrida=build_corrida, praca=build_praca, interrogatorio=build_interrogatorio, quarto=build_quarto)
only = os.environ.get("LEGO_SET")
for name in (only.split(",") if only else SETS):
    print("set", name, flush=True)
    BUILD[name]()
save()
print("=== SETS DONE", flush=True)
