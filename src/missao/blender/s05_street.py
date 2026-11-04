# Step 5: splits the file into two scenes, RUN and STORY, then builds the night street that both of them share.
# The prop library leaves the scenes (kept by a fake user) and is copied from, so nothing stray can render.
# Safe to re-run after s04 only: it joins the prefab meshes, so run s02-s04 again first if s05 has already run.
import bpy, bmesh, os, random, sys, importlib
from mathutils import Matrix, Vector
sys.path.insert(0, r"C:\Users\lukeg\Projetos\pardingows\src\thps\blender")
sys.path.insert(0, r"C:\Users\lukeg\Projetos\pardingows\src\missao\blender")
import lib, path, set_lib
importlib.reload(lib); importlib.reload(path); importlib.reload(set_lib)
from lib import make_mat, srgb, collection
from path import ROAD, FRONT
from set_lib import tex_mat, quads, place

OB = bpy.data.objects
TEXTURES = r"C:\Users\lukeg\Projetos\pardingows\blender\missao\textures"
SOL_TEX = r"C:\Users\lukeg\Projetos\pardingows\blender\solucao\textures"
assets = bpy.data.collections["assets"]
rng = random.Random(2)
Y_START, Y_END = 25.0, -285.0


def flatten(name, keep=None, base=0.0):
    """Joins a prefab's pieces into one mesh, so placing it many times costs one object each."""
    root = OB[name]
    kids = list(root.children)
    if keep:
        for k in [k for k in kids if not keep(k)]:
            OB.remove(k, do_unlink=True)
        kids = list(root.children)
    if len(kids) > 1:
        with bpy.context.temp_override(active_object=kids[0], object=kids[0], selected_editable_objects=kids, selected_objects=kids):
            bpy.ops.object.join()
    k = root.children[0]
    k.name = name + "_mesh"
    if base:
        k.data.transform(Matrix.Translation((0, 0, -base)))
    return k


def decimate(name, ratio):
    k = OB[name + "_mesh"]
    md = k.modifiers.new("ps1", "DECIMATE")
    md.ratio = ratio
    with bpy.context.temp_override(object=k, active_object=k):
        bpy.ops.object.modifier_apply(modifier=md.name)


def bbox_of(o):
    pts = [v.co for v in o.data.vertices]
    return Vector(min(p[i] for p in pts) for i in range(3)), Vector(max(p[i] for p in pts) for i in range(3))


def trim_road_side(name, beyond):
    """Removes whatever a street block still has on the road side of its front line: curb scraps, lamp posts, loose wires."""
    me = OB[name + "_mesh"].data
    bm = bmesh.new()
    bm.from_mesh(me)
    doomed = [f for f in bm.faces if all(beyond(v.co) for v in f.verts)]
    bmesh.ops.delete(bm, geom=doomed, context="FACES")
    bm.to_mesh(me)
    bm.free()
    print(name, "trimmed", len(doomed), "faces, left", len(me.polygons))


# ---- Prefabs. Road slabs come off the street blocks, since this street has its own road.
flatten("RUA1", keep=lambda k: bbox_of(k)[0].y < 0.2, base=1.1)
flatten("RUA2", keep=lambda k: bbox_of(k)[1].x > -0.3, base=0.35)
trim_road_side("RUA1", lambda p: p.y > 0.9)
trim_road_side("RUA2", lambda p: p.x < -0.7)
for n in ("CASA1", "CASA2", "CERCA", "VAN", "BARREIRA", "LIXO_RUA", "COLCHAO", "RELOGIO", "CRIADO", "ABAJUR", "GRANA", "GRANA2", "LIXEIRA", "SACOS", "LATA", "BOSTA", "POCA", "RATO", "KIOSK", "CAIXA", "POSTE"):
    flatten(n)
decimate("BOSTA", 0.18)
decimate("COLCHAO", 0.3)
decimate("LIXEIRA", 0.4)
OB["POCA_mesh"].data.materials.clear()
OB["POCA_mesh"].data.materials.append(make_mat("xixi", "e8c81e", emit=0.25))

# Models exported as unlit would glow in the dark, so they take the night's light like everything else
unlit = []
for m in bpy.data.materials:
    if not m.use_nodes or not any(n.type == "LIGHT_PATH" for n in m.node_tree.nodes) or not any(n.type == "EMISSION" for n in m.node_tree.nodes):
        continue
    t = m.node_tree
    tex_n = next((n for n in t.nodes if n.type == "TEX_IMAGE"), None)
    glow = next(n for n in t.nodes if n.type == "EMISSION")
    colour = tuple(glow.inputs[0].default_value)
    image = tex_n.image if tex_n else None
    t.nodes.clear()
    out = t.nodes.new("ShaderNodeOutputMaterial")
    bsdf = t.nodes.new("ShaderNodeBsdfDiffuse")
    bsdf.inputs["Color"].default_value = colour
    if image:
        tn = t.nodes.new("ShaderNodeTexImage")
        tn.image = image
        tn.interpolation = "Closest"
        t.links.new(tn.outputs[0], bsdf.inputs["Color"])
    t.links.new(bsdf.outputs[0], out.inputs[0])
    unlit.append(m.name)
print("unlit converted", unlit)

# Brown street rat, not a white lab one
tree = OB["RATO_mesh"].data.materials[0].node_tree
tex_n = next(n for n in tree.nodes if n.type == "TEX_IMAGE")
bsdf_n = next(n for n in tree.nodes if n.type == "BSDF_DIFFUSE")
mix = tree.nodes.new("ShaderNodeMixRGB")
mix.blend_type = "MULTIPLY"
mix.inputs[0].default_value = 1.0
mix.inputs[2].default_value = (*srgb("5c4230"), 1)
tree.links.new(tex_n.outputs[0], mix.inputs[1])
tree.links.new(mix.outputs[0], bsdf_n.inputs["Color"])

# ---- Two scenes. RUN is the file's first scene.
sc = bpy.context.scene
sc.name = "RUN"
story = bpy.data.scenes.get("STORY") or bpy.data.scenes.new("STORY")
story.render.fps = 30

run_cast = bpy.data.collections.get("run_cast") or bpy.data.collections.new("run_cast")
story_cast = bpy.data.collections.get("story_cast") or bpy.data.collections.new("story_cast")
if run_cast.name not in sc.collection.children:
    sc.collection.children.link(run_cast)
if story_cast.name not in story.collection.children:
    story.collection.children.link(story_cast)


def family(root):
    out = [root]
    for c in root.children:
        out += family(c)
    return out


def move(root_name, target):
    for o in family(OB[root_name]):
        for c in list(o.users_collection):
            c.objects.unlink(o)
        target.objects.link(o)


move("P1", run_cast)
move("P2", story_cast)
for n in ("PY1", "PY2", "PY3", "DG1", "DG2", "DG3", "DH1", "DH2"):
    move(n, run_cast)
for n in ("PY4", "PY5", "PY6", "DG4", "DG5", "DH3", "DH4", "DH5"):
    move(n, story_cast)
move("MORTO", run_cast)
# The two smurf helpers that aren't children of the roots
for o in list(OB):
    if o.users_collection and any(c.name in ("rigs", "smurf") for c in o.users_collection):
        target = story_cast if o.name.startswith("P2") else run_cast
        for c in list(o.users_collection):
            c.objects.unlink(o)
        target.objects.link(o)
for name in ("rigs", "smurf"):
    c = bpy.data.collections.get(name)
    if c:
        if name in sc.collection.children:
            sc.collection.children.unlink(c)
        bpy.data.collections.remove(c)
assets.use_fake_user = True
if assets.name in sc.collection.children:
    sc.collection.children.unlink(assets)
OB.get("sheet_sun") and OB.remove(OB["sheet_sun"], do_unlink=True)
OB.get("sheet_back") and OB.remove(OB["sheet_back"], do_unlink=True)

# ---- The street, shared by both scenes
street = bpy.data.collections.get("street")
if street:
    for o in list(street.objects):
        OB.remove(o, do_unlink=True)
else:
    street = bpy.data.collections.new("street")
if street.name not in sc.collection.children:
    sc.collection.children.link(street)
if street.name not in story.collection.children:
    story.collection.children.link(street)

ASPHALT = tex_mat("asfalto", os.path.join(SOL_TEX, "tx_asphalt.png"))
CONCRETE = tex_mat("calcada", os.path.join(SOL_TEX, "tx_concrete.png"))
CURB = make_mat("guia", "8c8a82")
PAINT = make_mat("faixa", "d8d4c0")
DIRT = make_mat("terra", "241c16")

y0, y1 = Y_START, Y_END
tile = 6.0
n = (y0 - y1) / tile
quads("road", [([(-ROAD, y1, 0), (ROAD, y1, 0), (ROAD, y0, 0), (-ROAD, y0, 0)], (2, n))], ASPHALT, street)
side = []
for s in (-1, 1):
    a, b = s * (ROAD + 0.25), s * (FRONT + 2)
    lo, hi = min(a, b), max(a, b)
    side.append(([(lo, y1, 0.16), (hi, y1, 0.16), (hi, y0, 0.16), (lo, y0, 0.16)], (1, n * 1.5)))
quads("sidewalks", side, CONCRETE, street)
curb = []
for s in (-1, 1):
    a, b = s * ROAD, s * (ROAD + 0.25)
    lo, hi = min(a, b), max(a, b)
    curb.append(([(lo, y1, 0.16), (hi, y1, 0.16), (hi, y0, 0.16), (lo, y0, 0.16)], (1, 1)))
    curb.append(([(a, y1, 0), (a, y0, 0), (a, y0, 0.16), (a, y1, 0.16)], (1, 1)))
quads("curbs", curb, CURB, street)
# Dashes between the lanes are what sell the speed
dash = []
yy = y0
while yy > y1:
    for x in (-1.0, 1.0):
        dash.append(([(x - 0.07, yy - 2.2, 0.012), (x + 0.07, yy - 2.2, 0.012), (x + 0.07, yy, 0.012), (x - 0.07, yy, 0.012)], (1, 1)))
    yy -= 4.4
quads("dashes", dash, PAINT, street)
quads("ground", [([(-90, y1 - 60, -0.05), (90, y1 - 60, -0.05), (90, y0 + 30, -0.05), (-90, y0 + 30, -0.05)], (1, 1))], DIRT, street)

# Houses down both sides. rz turns a prefab's front to the road: +90 for +X side pieces whose front faces +Y, 0 and 180 for RUA2 whose front faces -X.
def row(side):
    y = Y_START
    while y > Y_END:
        kind = rng.choice(("RUA2", "RUA1", "CASA1", "RUA2", "CASA2", "CASA1"))
        if kind == "RUA2":
            length = 16.4
            rz = 0 if side > 0 else 180
            place("RUA2", street, (side * FRONT, y - length / 2, 0), rz)
        elif kind == "RUA1":
            length = 21.4
            rz = 90 if side > 0 else -90
            place("RUA1", street, (side * (FRONT + 0.2), y - length / 2, 0), rz)
        else:
            size = OB[kind]["size"]
            length = size[0]
            rz = 90 if side > 0 else -90
            place(kind, street, (side * (FRONT + size[1] / 2), y - length / 2, 0), rz)
        y -= length + rng.choice((0.0, 0.0, 0.4, 1.6))


row(1)
row(-1)

# Favela climbing the hill behind them, so the sky is never just empty above the roofs
for s in (-1, 1):
    for tier, (dx, dz, step) in enumerate(((10.5, 3.2, 6.2), (17.5, 6.6, 7.0), (25.0, 10.0, 7.6), (33.0, 14.0, 8.4))):
        y = Y_START + rng.uniform(-3, 3)
        while y > Y_END:
            kind = rng.choice(("CASA1", "CASA2", "CASA2"))
            size = OB[kind]["size"]
            place(kind, street, (s * (FRONT + dx + rng.uniform(-1, 1)), y, dz + rng.uniform(-0.5, 0.5)), 90 if s > 0 else -90)
            y -= step + rng.uniform(-0.6, 1.4)

# Lit windows up the hill, one warm quad at a time
WARM = make_mat("janela", "ffb860", emit=1.4)
win = []
for s in (-1, 1):
    y = Y_START
    while y > Y_END:
        if rng.random() < 0.55:
            x = s * (FRONT + rng.uniform(9, 36) - 0.02)
            z = (abs(x) - FRONT) * 0.42 + rng.uniform(1.0, 3.2)
            win.append(([(x, y, z), (x, y - 0.8, z), (x, y - 0.8, z + 0.9), (x, y, z + 0.9)], (1, 1)))
        y -= rng.uniform(1.2, 3.4)
quads("windows", win, WARM, street)

# Street furniture on the sidewalks, never in the lanes
LIGHT_Y = []
y = Y_START - 6
side = 1
while y > Y_END:
    place("POSTE", street, (side * (ROAD + 0.9), y, 0.16), 90 if side > 0 else -90)
    LIGHT_Y.append((side * (ROAD + 0.4), y))
    side = -side
    y -= 15.0
y = Y_START - 12
while y > Y_END:
    x = rng.choice((-1, 1)) * (ROAD + rng.uniform(0.8, 1.8))
    place(rng.choice(("SACOS", "LATA", "LIXO_RUA", "SACOS", "BARREIRA")), street, (x, y, 0.16), rng.uniform(0, 360))
    y -= rng.uniform(5, 12)
for yy in (-70, -128, -190):
    place("VAN", street, (-(ROAD + 1.2), yy, 0.16), 90)
for yy in (-42, -105, -160):
    place("SACOS", street, (ROAD + 1.3, yy, 0.16), 40)

# Orange pool of light under each lamp, faked with a glowing lamp head and a real short-range light
LAMP = make_mat("lampada", "ffb050", emit=5.0)
heads = []
for x, yy in LIGHT_Y:
    heads.append(([(x - 0.3, yy - 0.5, 6.05), (x + 0.3, yy - 0.5, 6.05), (x + 0.3, yy + 0.5, 6.05), (x - 0.3, yy + 0.5, 6.05)], (1, 1)))
    data = bpy.data.lights.new("poste", "POINT")
    data.energy = 420
    data.color = srgb("ffa04a")
    data.shadow_soft_size = 0.2
    data.use_shadow = False
    lamp = bpy.data.objects.new("poste", data)
    lamp.location = (x * 0.6, yy, 5.6)
    street.objects.link(lamp)
quads("lamp_heads", heads, LAMP, street)

bpy.data.orphans_purge(do_recursive=True)
bpy.context.view_layer.update()
set_lib.save()
print("scenes", [s.name for s in bpy.data.scenes], "street objects", len(street.objects), "lamps", len(LIGHT_Y))
print("run", sorted(o.name for o in run_cast.objects if not o.parent))
print("story", sorted(o.name for o in story_cast.objects if not o.parent))
