# Step 3: the moon. Cratered ground, a real road with a dashed line down the middle, a street sign, rocks and stars.
# Safe to re-run: rebuilds the "moon" collection. Run s04_look afterwards so the new materials get the distance fade.
import bpy, math, os, random, sys, importlib
import numpy as np
sys.path.insert(0, r"C:\Users\lukeg\Projetos\pardingows\src\thps\blender")
sys.path.insert(0, r"C:\Users\lukeg\Projetos\pardingows\src\planeta\blender")
import lib, build
importlib.reload(lib); importlib.reload(build)
from lib import Mesh, collection, empty, make_mat, srgb
from build import ROAD, height

coll = collection("moon")
TEXTURES = r"C:\Users\lukeg\Projetos\pardingows\blender\planeta\textures"
os.makedirs(TEXTURES, exist_ok=True)
rng = random.Random(11)


def tex_mat(name, pixels):
    """Material from a small numpy image (rows top first, values 0-1), filtered hard and saved to disk."""
    h, w = pixels.shape[:2]
    rgba = np.dstack((pixels, np.ones((h, w)))) if pixels.shape[2] == 3 else pixels
    img = bpy.data.images.get(name) or bpy.data.images.new(name, w, h)
    img.scale(w, h)
    img.pixels.foreach_set(rgba[::-1].astype(np.float32).ravel())
    img.filepath_raw = os.path.join(TEXTURES, name + ".png")
    img.file_format = "PNG"
    img.save()
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    n = m.node_tree.nodes
    n.clear()
    out = n.new("ShaderNodeOutputMaterial")
    bsdf = n.new("ShaderNodeBsdfDiffuse")
    t = n.new("ShaderNodeTexImage")
    t.image = img
    t.interpolation = "Closest"
    m.node_tree.links.new(t.outputs[0], bsdf.inputs["Color"])
    m.node_tree.links.new(bsdf.outputs[0], out.inputs["Surface"])
    return m


def blocks(size, cell, seed, lo, hi):
    """Tileable blocky noise, to look like a texture drawn by hand at a tiny size."""
    r = np.random.default_rng(seed)
    coarse = r.uniform(lo, hi, (size // cell, size // cell))
    return np.kron(coarse, np.ones((cell, cell)))


def regolith(base):
    v = (blocks(64, 2, 1, -0.05, 0.05) + blocks(64, 8, 2, -0.05, 0.05))[..., None]
    return np.clip(np.array(srgb(base)) * (1 + v * 3.2), 0, 1)


ground = tex_mat("moon ground", regolith("cfccc4"))
dust = tex_mat("moon road", regolith("8c8a84"))

# ---- Ground: one big faceted sheet with planar UVs, cut wide of the fade so the edge is never seen
STEP = 4.0
NX, NY = 110, 62
m = Mesh()
x0, y0 = -NX * STEP / 2 + 30, -NY * STEP / 2
for j in range(NY + 1):
    for i in range(NX + 1):
        x, y = x0 + i * STEP, y0 + j * STEP
        m.v.append((x, y, height(x, y)))
for j in range(NY):
    for i in range(NX):
        a = j * (NX + 1) + i
        m.f.append((a, a + 1, a + NX + 2, a + NX + 1))
        m.fm.append(0)
ob = m.build("moon ground", [ground], None, coll)
uv = ob.data.uv_layers.new(name="uv")
for loop in ob.data.loops:
    v = ob.data.vertices[loop.vertex_index].co
    uv.uv[loop.index].vector = (v.x / 7, v.y / 7)

# ---- Road: slightly darker strip, kerb stones and the dashed line that gives the joke away
m = Mesh()
m.box((30, 0, 0.01), (220, ROAD, 0.012), 0)
line = make_mat("moon line", "e8c62a", emit=0.25)
kerb = make_mat("moon kerb", "c9c5ba")
for k in range(-30, 70):
    m.box((k * 4 + 2, 0, 0.026), (0.9, 0.08, 0.006), 1)
for side in (-1, 1):
    for k in range(-60, 140):
        if k % 2 == 0:
            m.box((k * 2 + 1, side * (ROAD + 0.1), 0.06), (0.98, 0.1, 0.06), 2)
road = m.build("moon road", [dust, line, kerb], None, coll)
uv = road.data.uv_layers.new(name="uv")
for loop in road.data.loops:
    v = road.data.vertices[loop.vertex_index].co
    uv.uv[loop.index].vector = (v.x / 7, v.y / 7)

# ---- Street sign, in the blue and white of a Brazilian corner
blue = make_mat("sign blue", "1c4fa8")
white = make_mat("sign white", "f4f4ee", emit=0.2)
pole = make_mat("sign pole", "5b5e66")
SIGN_X, SIGN_Y = 10.0, ROAD + 0.7
sign = empty("sign root", None, loc=(SIGN_X, SIGN_Y, 0), coll=coll)
sign.rotation_euler = (0, 0, math.radians(-50))  # turned to face someone walking down the road
m = Mesh()
m.box((0, 0, 1.3), (0.05, 0.05, 1.3), 2)
m.box((0, -0.06, 2.55), (1.42, 0.03, 0.38), 0)
m.build("sign", [blue, white, pole], sign, coll)
for text, z, size, name in (("RUA DOS PARDOS", 2.52, 0.29, "sign text"),):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = text
    cu.size = size
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.resolution_u = 1
    cu.materials.append(white)
    t = bpy.data.objects.new(name, cu)
    coll.objects.link(t)
    t.parent = sign
    t.location = (0, -0.1, z)
    t.rotation_euler = (math.radians(90), 0, 0)

# ---- Rocks: squashed octahedra, chunky and few, kept off the road
rock_m = make_mat("moon rock", "7e7a72")
m = Mesh()
for _ in range(90):
    x, y = rng.uniform(-70, 120), rng.choice((-1, 1)) * rng.uniform(ROAD + 1.4, 70)
    s = rng.uniform(0.2, 1.1) * (1 + max(abs(y) - 10, 0) * 0.02)
    z = height(x, y)
    top = (x, y, z + s * rng.uniform(0.7, 1.3))
    bot = (x, y, z - s * 0.5)
    i = len(m.v)
    ang = rng.uniform(0, 6.28)
    ring5 = [(x + s * rng.uniform(0.8, 1.2) * math.cos(ang + k * 1.257), y + s * rng.uniform(0.8, 1.2) * math.sin(ang + k * 1.257), z + s * rng.uniform(0, 0.3)) for k in range(5)]
    m.v += ring5 + [top, bot]
    for k in range(5):
        a, b = i + k, i + (k + 1) % 5
        m.f.append((a, b, i + 5)); m.fm.append(0)
        m.f.append((b, a, i + 6)); m.fm.append(0)
m.build("moon rocks", [rock_m], None, coll)

# ---- Stars: small flat crosses on a dome, seen from anywhere in the set. Sky materials skip the distance fade.
stars = make_mat("sky_stars", "ffffff", emit=1.0)
stars2 = make_mat("sky_stars_dim", "8f9bb8", emit=1.0)
m = Mesh()
for k in range(900):
    a, e = rng.uniform(0, 6.283), math.asin(rng.uniform(0.02, 1.0))
    R = 640
    c = (R * math.cos(e) * math.cos(a) + 30, R * math.cos(e) * math.sin(a), R * math.sin(e))
    s = rng.choice((0.7, 0.7, 1.0, 1.0, 1.5, 2.2))
    m.box(c, (s, s, s), 0 if k % 3 == 0 else 1)
m.build("sky stars", [stars, stars2], None, coll)

bpy.ops.wm.save_mainfile()
print("moon ok;", len(ob.data.polygons), "ground faces; height at (20,20):", round(height(20, 20), 2), "(9,24):", round(height(9, 24), 2))
