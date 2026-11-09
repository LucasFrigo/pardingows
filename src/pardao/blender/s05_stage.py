# Step 4a: the stage, a favela stairway at night, built in the open window. Re-runnable: it clears the "stage" collection first.
# Layout (local metres, +Y uphill and away from the camera, which looks up the hill from the street):
#   T0 street z=0 (road, Kombi, trash)  ->  flight F1 along +X  ->  T1 landing z=3 (bar corner, fire barrel)
#   ->  F2 along -X  ->  T2 landing z=6 in front of the graffiti wall (the muro)  ->  F3 along +X  ->  T3 top plaza z=9, the baile.
# Every terrace sits further up the hill, so in a 9:16 frame the climb reads bottom to top. Houses are built here from the kit's
# own wall textures (blocks of floors, windows, water tanks), kit models are placed as prefabs (collection instances).
# The whole stage is offset to ORIGIN so it never overlaps the step-2 gallery or the cast lineup. stage.json records the anchors.
#   node src/thps/bl.mjs run src/pardao/blender/s05_stage.py
import bpy, bmesh, json, math, os, random, sys
from mathutils import Matrix, Vector
try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    HERE = os.path.join(os.environ.get("PARDAO_ROOT", r"E:\Projetos\pardingows"), "src", "pardao", "blender")
sys.path.insert(0, HERE)
import importlib, set_lib
importlib.reload(set_lib)
from set_lib import WORK, TEXTURES, ASSETS, redraw

OB = bpy.data.objects
ORIGIN = Vector((-150.0, 0.0, 0.0))
W = 7.0  # half width of the playing lane; houses start beyond it
TERRACES = [  # (z, y_front, y_back)
    (0.0, -1.0, 6.0), (3.0, 6.0, 11.0), (6.0, 11.0, 16.0), (9.0, 16.0, 28.0),
    (12.0, 28.0, 34.0), (15.0, 34.0, 41.0), (18.0, 41.0, 49.0), (21.0, 49.0, 58.0),
]
rnd = random.Random(2000)

# ---------------------------------------------------------------- clear
stage = bpy.data.collections.get("stage")
if stage:
    for o in list(stage.all_objects):
        OB.remove(o, do_unlink=True)
    for c in list(stage.children_recursive):
        bpy.data.collections.remove(c)
else:
    stage = bpy.data.collections.new("stage")
    bpy.context.scene.collection.children.link(stage)
for c in [c for c in bpy.data.collections if c.name.startswith("PF_")]:
    for o in list(c.objects):
        OB.remove(o, do_unlink=True)
    bpy.data.collections.remove(c)
for m in [m for m in bpy.data.meshes if m.get("stage_made") and m.users == 0]:
    bpy.data.meshes.remove(m)


def sub(name):
    c = bpy.data.collections.new(name)
    stage.children.link(c)
    return c


C_GROUND, C_HOUSES, C_PROPS, C_LIGHTS, C_FAR = (sub(n) for n in ("st_chao", "st_casas", "st_objetos", "st_luzes", "st_fundo"))

# ---------------------------------------------------------------- materials
MATS = {}


def tex(file):
    p = os.path.join(TEXTURES, "small " + file)
    return bpy.data.images.load(p, check_existing=True)


def mat_tex(name, file, tint=None, emit=None, rough=0.85):
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.get("st " + name) or bpy.data.materials.new("st " + name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Roughness"].default_value = rough
    b.inputs["Specular IOR Level"].default_value = 0.2
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = tex(file)
    t.interpolation = "Linear"
    src = t.outputs[0]
    if tint:
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type, mix.blend_type = "RGBA", "MULTIPLY"
        mix.inputs["Factor"].default_value = 1.0
        nt.links.new(src, mix.inputs[6])
        mix.inputs[7].default_value = (*tint, 1)
        src = mix.outputs[2]
    nt.links.new(src, b.inputs["Base Color"])
    if emit:
        b.inputs["Emission Color"].default_value = (*emit[0], 1)
        b.inputs["Emission Strength"].default_value = emit[1]
    nt.links.new(b.outputs[0], out.inputs[0])
    MATS[name] = m
    return m


def mat_flat(name, rgb, emit=0.0, rough=0.8, metal=0.0):
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.get("st " + name) or bpy.data.materials.new("st " + name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*rgb, 1)
        b.inputs["Emission Strength"].default_value = emit
    MATS[name] = m
    return m


# Texture files picked from the kit (contact sheet in the step-4 notes); tile = metres one image repeat covers
WALLS = {  # name: (file, tile)
    "tijolo": ("casa1 Materiais_baseColor.jpeg.png", 1.6), "tijolo2": ("casas_pack Materiais.024_baseColor.jpeg.png", 1.6),
    "tijolo3": ("casa2 Materiais.013_baseColor.jpeg.png", 1.6),
    "reboco_azul": ("casa2 Materiais.006_baseColor.jpeg.png", 3.0), "reboco_verde": ("casas_pack Materiais.012_baseColor.jpeg.png", 3.0),
    "reboco_cinza": ("casas_pack Materiais.014_baseColor.jpeg.png", 3.0), "reboco_musgo": ("casa1 Materiais.002_baseColor.jpeg.png", 3.0),
    "reboco_azul2": ("casas_pack2 Materiais.019_baseColor.jpeg.png", 3.0), "reboco_rosa": ("favelas Bottom_baseColor.png.png", 3.0),
    "reboco_velho": ("casas_pack2 Materiais.008_baseColor.jpeg.001.png", 3.0),
}
PAINT = {"reboco_amarelo": ("casas_pack Materiais.014_baseColor.jpeg.png", (1.0, 0.78, 0.35)),
         "reboco_laranja": ("casas_pack Materiais.014_baseColor.jpeg.png", (1.0, 0.55, 0.32)),
         "reboco_lilas": ("casas_pack Materiais.014_baseColor.jpeg.png", (0.75, 0.6, 0.95))}
for n, (f, tile) in WALLS.items():
    mat_tex(n, f)
for n, (f, tint) in PAINT.items():
    mat_tex(n, f, tint)
TILE = {**{n: t for n, (f, t) in WALLS.items()}, **{n: 3.0 for n in PAINT}}
mat_tex("concreto", "casa1 Materiais.001_baseColor.jpeg.png")
mat_tex("escada", "escada Stairs_Texture_baseColor.jpeg.png")
mat_tex("asfalto", "casas_pack Materiais.001_baseColor.jpeg.png", (0.55, 0.55, 0.6), rough=0.6)
mat_tex("porta", "casa1 Materiais.005_baseColor.jpeg.png")
mat_tex("porta_azul", "casas_pack Materiais.031_baseColor.jpeg.png")
mat_tex("portao", "casa1 Materiais.004_baseColor.jpeg.png")
mat_tex("portao2", "casas_pack Materiais.034_baseColor.jpeg.png")
mat_tex("laje", "escada2 Concrete012_baseColor.jpeg.png")
mat_tex("telha", "casa2 Materiais.007_baseColor.jpeg.png")
GRAFF = ["grafite lambert11_baseColor.jpeg.png", "grafite lambert17_baseColor.jpeg.png", "grafite lambert24_baseColor.jpeg.png",
         "grafite lambert29_baseColor.jpeg.png", "grafite lambert31_baseColor.jpeg.png", "grafite lambert38_baseColor.jpeg.png",
         "grafite lambert55_baseColor.jpeg.png", "grafite lambert57_baseColor.jpeg.png", "grafite lambert58_baseColor.jpeg.png",
         "grafite M_side1_baseColor.jpeg.png", "grafite M_side2_baseColor.jpeg.png"]
for i, f in enumerate(GRAFF):
    mat_tex(f"grafite{i}", f)
mat_flat("janela", (0.02, 0.025, 0.03), rough=0.25)
mat_flat("janela_luz", (1.0, 0.6, 0.28), emit=1.5)
mat_flat("janela_tv", (0.35, 0.55, 1.0), emit=1.3)
mat_flat("janela_fluor", (0.75, 0.9, 0.95), emit=1.2)
mat_flat("led_vermelho", (1.0, 0.08, 0.15), emit=6.0)
mat_flat("led_azul", (0.1, 0.4, 1.0), emit=6.0)
mat_flat("caixa_dagua", (0.08, 0.25, 0.62), rough=0.45)
mat_flat("ferro", (0.12, 0.1, 0.09), rough=0.6, metal=0.6)
mat_flat("fio", (0.01, 0.01, 0.01), rough=0.7)
mat_flat("poste", (0.42, 0.41, 0.39), rough=0.9)
mat_flat("lampada", (1.0, 0.62, 0.25), emit=25.0)
mat_flat("ar_cond", (0.75, 0.75, 0.72), rough=0.5)


# ---------------------------------------------------------------- mesh builder with metre-based UVs
class Builder:
    def __init__(self):
        self.v, self.f, self.uv, self.mi, self.mats = [], [], [], [], []

    def _m(self, name):
        m = MATS[name]
        if m not in self.mats:
            self.mats.append(m)
        return self.mats.index(m)

    def quad(self, a, b, c, d, mat, tile=None, flip=False):
        """Quad a-b-c-d (counter-clockwise seen from the front). UVs in metres / tile, from a."""
        tile = tile or TILE.get(mat, 2.5)
        a, b, c, d = (Vector(p) for p in (a, b, c, d))
        i = len(self.v)
        self.v += [tuple(a), tuple(b), tuple(c), tuple(d)]
        self.f.append((i, i + 1, i + 2, i + 3) if not flip else (i + 3, i + 2, i + 1, i))
        w, h = (b - a).length / tile, (d - a).length / tile
        self.uv.append([(0, 0), (w, 0), (w, h), (0, h)] if not flip else [(0, h), (w, h), (w, 0), (0, 0)])
        self.mi.append(self._m(mat))

    def box(self, x0, x1, y0, y1, z0, z1, mat, top=None, bottom=False, faces="nsewt", tile=None):
        """Axis box. faces: n(+Y) s(-Y) e(+X) w(-X) t(top) b(bottom)."""
        P = lambda x, y, z: (x, y, z)
        if "s" in faces:
            self.quad(P(x0, y0, z0), P(x1, y0, z0), P(x1, y0, z1), P(x0, y0, z1), mat, tile)
        if "n" in faces:
            self.quad(P(x1, y1, z0), P(x0, y1, z0), P(x0, y1, z1), P(x1, y1, z1), mat, tile)
        if "e" in faces:
            self.quad(P(x1, y0, z0), P(x1, y1, z0), P(x1, y1, z1), P(x1, y0, z1), mat, tile)
        if "w" in faces:
            self.quad(P(x0, y1, z0), P(x0, y0, z0), P(x0, y0, z1), P(x0, y1, z1), mat, tile)
        if "t" in faces:
            self.quad(P(x0, y0, z1), P(x1, y0, z1), P(x1, y1, z1), P(x0, y1, z1), top or mat, tile)
        if "b" in faces or bottom:
            self.quad(P(x0, y1, z0), P(x1, y1, z0), P(x1, y0, z0), P(x0, y0, z0), mat, tile)

    def cyl(self, c, r, h, mat, n=10, z0=0.0):
        i0 = len(self.v)
        for k in range(n):
            a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
            p0 = (c[0] + r * math.cos(a0), c[1] + r * math.sin(a0))
            p1 = (c[0] + r * math.cos(a1), c[1] + r * math.sin(a1))
            self.quad((*p0, z0), (*p1, z0), (*p1, z0 + h), (*p0, z0 + h), mat, 1.0)
        top = [(c[0] + r * math.cos(2 * math.pi * k / n), c[1] + r * math.sin(2 * math.pi * k / n), z0 + h) for k in range(n)]
        i = len(self.v)
        self.v += top
        self.f.append(tuple(range(i, i + n)))
        self.uv.append([(0.5 + 0.5 * math.cos(2 * math.pi * k / n), 0.5 + 0.5 * math.sin(2 * math.pi * k / n)) for k in range(n)])
        self.mi.append(self._m(mat))

    def build(self, name, coll):
        me = bpy.data.meshes.new(name)
        me["stage_made"] = True
        verts = [tuple(Vector(p) + ORIGIN) for p in self.v]
        me.from_pydata(verts, [], self.f)
        for m in self.mats:
            me.materials.append(m)
        layer = me.uv_layers.new(name="UVMap")
        for p, uvs, mi in zip(me.polygons, self.uv, self.mi):
            p.material_index = mi
            p.use_smooth = False
            for l, uv in zip(p.loop_indices, uvs):
                layer.data[l].uv = uv
        ob = OB.new(name, me)
        coll.objects.link(ob)
        return ob


# ---------------------------------------------------------------- ground, retaining walls, stairs
g = Builder()
g.box(-60, 60, -14, -1, -0.3, 0.0, "asfalto", faces="t")  # the road
g.box(-60, 60, -1.0, -0.85, 0.0, 0.18, "concreto", faces="st")  # kerb
for k, (z, y0, y1) in enumerate(TERRACES):
    g.box(-60, 60, y0, y1, z - 0.3, z, "laje" if k else "concreto", faces="t", tile=3.0)
    if k:
        zp = TERRACES[k - 1][0]
        # The terrace's front face: plain concrete outside the lane, graffiti where the camera looks
        g.box(-60, -W, y0 - 0.35, y0, zp, z, "concreto", faces="s", tile=3.0)
        g.box(W, 60, y0 - 0.35, y0, zp, z, "concreto", faces="s", tile=3.0)
        if k <= 3:
            panels = 4
            for i in range(panels):
                x0, x1 = -W + 2 * W * i / panels, -W + 2 * W * (i + 1) / panels
                g.box(x0, x1, y0 - 0.35, y0, zp, z, f"grafite{(k * 3 + i) % len(GRAFF)}", faces="s", tile=3.5)
        else:
            g.box(-W, W, y0 - 0.35, y0, zp, z, "concreto", faces="s", tile=3.0)
ground = g.build("st_chao", C_GROUND)

STEP_R, STEP_T = 0.15, 0.30
FLIGHTS = []  # (x_start, direction, y0, y1, z_start)
for k in range(1, 4):
    zp, y0 = TERRACES[k - 1][0], TERRACES[k][1]
    d = 1 if k % 2 else -1
    xs = -6.6 if d > 0 else 6.6
    FLIGHTS.append((xs, d, y0 - 1.7, y0 - 0.35, zp))
s = Builder()
for xs, d, y0, y1, zp in FLIGHTS:
    for i in range(20):
        xa, xb = xs + d * i * STEP_T, xs + d * (i + 1) * STEP_T
        top = zp + (i + 1) * STEP_R
        s.box(min(xa, xb), max(xa, xb), y0, y1, zp, top, "escada", faces="sewt" if i else "sewt", tile=1.2)
    # Low side wall along the open edge of each flight
    xe = xs + d * 20 * STEP_T
    s.box(min(xs, xe), max(xs, xe), y0 - 0.15, y0, zp, zp + 0.5, "concreto", faces="sewnt", tile=2.0)
stairs = s.build("st_escadas", C_GROUND)

# Pipe railings on the flights
rail = Builder()
for xs, d, y0, y1, zp in FLIGHTS:
    for i in range(0, 21, 5):
        x = xs + d * i * STEP_T
        z = zp + i * STEP_R
        rail.box(x - 0.03, x + 0.03, y0 - 0.1, y0 - 0.04, z + 0.4, z + 1.35, "ferro")
    xe, ze = xs + d * 6.0, zp + 3.0
    # A slanted handrail as a thin box chain
    for i in range(20):
        xa, xb = xs + d * i * STEP_T, xs + d * (i + 1) * STEP_T
        za = zp + i * STEP_R + 1.3
        rail.box(min(xa, xb), max(xa, xb), y0 - 0.1, y0 - 0.04, za, za + 0.06, "ferro")
rail.build("st_corrimao", C_GROUND)


# ---------------------------------------------------------------- houses
def house(b, x0, x1, y0, y1, z0, floors, front="s", side=None):
    """A favela house: stacked floors (upper ones sometimes overhang), windows, door, slab roof with a water tank."""
    wall = rnd.choice(list(TILE))
    raw = rnd.random() < 0.45  # unfinished brick on part of the house
    z = z0
    fh = 2.9
    for f in range(floors):
        dx = rnd.uniform(-0.35, 0.35) if f else 0.0
        dy = rnd.uniform(-0.6, 0.0) if f else 0.0
        fx0, fx1, fy0, fy1 = x0 + dx, x1 + dx, y0 + dy, y1
        mat = "tijolo" if (raw and f == floors - 1) else (rnd.choice(["tijolo2", "tijolo3"]) if raw and f else wall)
        b.box(fx0, fx1, fy0, fy1, z, z + fh, mat, faces="nsew")
        # slab edge between floors
        b.box(fx0 - 0.05, fx1 + 0.05, fy0 - 0.05, fy1 + 0.05, z + fh - 0.12, z + fh, "laje", faces="nsewt" if f == floors - 1 else "nsew")
        # windows on the front (and the given side)
        faces = [front] + ([side] if side else [])
        for fc in faces:
            if fc == "s":
                span, n = fx1 - fx0, max(1, int((fx1 - fx0) / 2.2))
                for i in range(n):
                    cx = fx0 + span * (i + 0.5) / n
                    if f == 0 and i == 0 and front == "s":
                        b.quad((cx - 0.45, fy0 - 0.02, z), (cx + 0.45, fy0 - 0.02, z), (cx + 0.45, fy0 - 0.02, z + 2.1), (cx - 0.45, fy0 - 0.02, z + 2.1),
                               rnd.choice(["porta", "porta_azul", "portao", "portao2"]), 2.1)
                        continue
                    lit = rnd.random()
                    m = "janela_luz" if lit < 0.32 else "janela_tv" if lit < 0.4 else "janela_fluor" if lit < 0.46 else "janela"
                    b.quad((cx - 0.5, fy0 - 0.02, z + 1.0), (cx + 0.5, fy0 - 0.02, z + 1.0), (cx + 0.5, fy0 - 0.02, z + 2.1), (cx - 0.5, fy0 - 0.02, z + 2.1), m, 1.0)
            else:
                xw = fx1 + 0.02 if fc == "e" else fx0 - 0.02
                span, n = fy1 - fy0, max(1, int((fy1 - fy0) / 2.4))
                for i in range(n):
                    cy = fy0 + span * (i + 0.5) / n
                    lit = rnd.random()
                    m = "janela_luz" if lit < 0.3 else "janela_tv" if lit < 0.36 else "janela"
                    if fc == "e":
                        b.quad((xw, cy - 0.5, z + 1.0), (xw, cy + 0.5, z + 1.0), (xw, cy + 0.5, z + 2.1), (xw, cy - 0.5, z + 2.1), m, 1.0)
                    else:
                        b.quad((xw, cy + 0.5, z + 1.0), (xw, cy - 0.5, z + 1.0), (xw, cy - 0.5, z + 2.1), (xw, cy + 0.5, z + 2.1), m, 1.0)
        # an AC box on some floors
        if rnd.random() < 0.3 and front == "s":
            ax = rnd.uniform(fx0 + 0.4, fx1 - 0.9)
            b.box(ax, ax + 0.6, fy0 - 0.35, fy0, z + 2.2, z + 2.6, "ar_cond")
        z += fh
    # Roof: water tank, rebar stubs or a tiled lean-to
    if rnd.random() < 0.7:
        cx, cy = rnd.uniform(x0 + 0.8, x1 - 0.8), rnd.uniform(y0 + 0.8, max(y0 + 0.9, y1 - 0.8))
        b.cyl((cx, cy), 0.55, 0.85, "caixa_dagua", 10, z)
    if rnd.random() < 0.5:
        for i in range(4):
            px = x0 + (x1 - x0) * (i + 0.5) / 4
            b.box(px - 0.02, px + 0.02, y0 + 0.1, y0 + 0.14, z, z + rnd.uniform(0.5, 1.1), "ferro")
    elif rnd.random() < 0.4:
        b.quad((x0, y0 - 0.3, z + 0.6), (x1, y0 - 0.3, z + 0.6), (x1, y1, z + 1.4), (x0, y1, z + 1.4), "telha", 2.0)
    return z


def fill_side(b, xa, xb, y0, y1, z0, face_side, floors_rng=(2, 4)):
    """Packs houses between xa and xb (|x| growing outwards) on one terrace."""
    sgn = 1 if xb > xa else -1
    x = xa
    while abs(x - xa) < abs(xb - xa) - 1.5:
        w = rnd.uniform(3.2, 5.5)
        x0, x1 = sorted((x, x + sgn * w))
        house(b, x0, x1, y0 + rnd.uniform(0.0, 0.8), y1 - 0.2, z0, rnd.randint(*floors_rng), "s", face_side if abs(x - xa) < 0.1 else None)
        x += sgn * (w + rnd.uniform(0.0, 0.25))


hb = Builder()
for k, (z, y0, y1) in enumerate(TERRACES):
    if k == 0:
        # The street: houses either side of the stair foot, facing the road
        fill_side(hb, -W - 0.3, -40, 0.5, 6.0, 0.0, "e", (2, 4))
        fill_side(hb, W + 0.3, 40, 0.5, 6.0, 0.0, "w", (2, 4))
        continue
    fl = (2, 3) if k <= 3 else (2, 4)
    fill_side(hb, -W - 0.3, -42, y0 + 0.4, y1, z, "e", fl)
    fill_side(hb, W + 0.3, 42, y0 + 0.4, y1, z, "w", fl)
    if k >= 4:
        # Behind the plaza the hill is solid houses
        fill_side(hb, -W - 0.3, W + 0.3, y0 + 0.6, y1, z, None, (2, 3))
houses = hb.build("st_casas", C_HOUSES)
redraw()


# ---------------------------------------------------------------- prefabs from the kit (collection instances)
def prefab(name):
    """A collection holding a copy of the import centred on its base, for collection instances."""
    pc = bpy.data.collections.get("PF_" + name)
    if pc:
        return pc
    pc = bpy.data.collections.new("PF_" + name)
    src = OB[name + "_import"]
    mapping = {}
    for o in [src] + list(src.children_recursive):
        n = o.copy()
        n.hide_render = n.hide_viewport = False
        pc.objects.link(n)
        mapping[o] = n
    for o, n in mapping.items():
        if o.parent in mapping:
            n.parent = mapping[o.parent]
    root = mapping[src]
    root.location = (0, 0, 0)
    root.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()
    # The copies aren't in the view layer, so their world matrices come from the parent chain by hand
    def world(o):
        m = Matrix.LocRotScale(o.location, o.rotation_euler.to_quaternion() if o.rotation_mode != "QUATERNION" else o.rotation_quaternion, o.scale)
        if o.parent:
            return world(o.parent) @ o.matrix_parent_inverse @ m
        return m
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for o in mapping.values():
        if o.type != "MESH":
            continue
        mw = world(o)
        for c in o.bound_box:
            p = mw @ Vector(c)
            lo, hi = Vector(map(min, lo, p)), Vector(map(max, hi, p))
    root.location = (-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)
    return pc


def put(name, loc, rz=0.0, s=1.0, coll=C_PROPS):
    inst = OB.new(f"{name}.{len(coll.objects)}", None)
    inst.instance_type = "COLLECTION"
    inst.instance_collection = prefab(name)
    inst.location = Vector(loc) + ORIGIN
    inst.rotation_euler = (0, 0, math.radians(rz))
    inst.scale = (s, s, s)
    coll.objects.link(inst)
    return inst


def zat(y):
    """Ground height of the terrace containing y."""
    for z, y0, y1 in TERRACES:
        if y0 <= y < y1:
            return z
    return 0.0


# Street (T0)
put("kombi", (-3.5, -4.2, 0), 90)
put("moto", (4.6, -2.6, 0), 200)
put("lixeira", (6.2, 1.2, 0), 10)
for x, y in ((5.4, 1.0), (5.9, 0.4), (-6.3, 1.5)):
    put("saco_lixo", (x, y, 0), rnd.uniform(0, 360), 0.8)
put("caixas", (-5.8, 4.4, 0), 15)
put("cacamba", (3.2, 4.6, 0), 0)
# Landing 1 (T1): the bar corner and the hobos' fire barrel
for i, (x, y, r) in enumerate(((3.6, 8.2, 20), (4.6, 8.8, -40), (2.9, 9.3, 160))):
    put("cadeira", (x, y, 3), r)
put("engradado", (5.6, 7.2, 3), 10)
put("engradado", (5.6, 7.2, 3.3), 35)
put("engradado", (6.2, 7.7, 3), 80)
put("tambor_fogo", (-4.6, 7.8, 3), 0)
put("carrinho", (-6.0, 8.6, 3), 70)
# Landing 2 (T2): trash under the graffiti wall
for x in (-5.5, -4.9, 5.2):
    put("saco_lixo", (x, 15.2, 6), rnd.uniform(0, 360), 0.75)
put("caixas", (6.0, 14.7, 6), -10)
put("engradado", (-6.2, 12.4, 6), 30)
# Top plaza (T3): the baile. Speaker wall either side of the DJ table, crates and chairs around
for side in (-1, 1):
    for i in range(3):
        for j in range(3):
            put("caixa_som", (side * (2.3 + i * 1.8), 25.6, 9 + j * 1.2), 180)
# LED strips along the speaker wall, the paredão's signature glow
led = Builder()
for side in (-1, 1):
    x0, x1 = sorted((side * 1.4, side * 7.2))
    for j in range(4):
        led.box(x0, x1, 24.95, 25.0, 9 + j * 1.2 - 0.03, 9 + j * 1.2 + 0.03, "led_vermelho" if j % 2 else "led_azul", faces="s")
led.build("st_leds", C_PROPS)
put("dj", (0, 24.6, 9), 180)
put("microfone", (0, 22.2, 9), 0)
for x, y, r in ((-5.5, 18.5, 30), (5.8, 19.0, -20), (6.2, 18.0, 100)):
    put("cadeira", (x, y, 9), r)
put("engradado", (-6.3, 21.0, 9), 0)
put("engradado", (-6.3, 21.0, 9.3), 20)
# Hand props: prefabs that ride on bones (actors.hand_prop), not placed in the set
for name in ("pistola", "baseado", "radio", "calendario", "taco", "microfone"):
    prefab(name)
# The pistol model ships its magazine and a bullet as loose pieces beside the gun
for o in list(bpy.data.collections["PF_pistola"].objects):
    if o.name.startswith(("ammo", "bullet")):
        OB.remove(o, do_unlink=True)
redraw()

# ---------------------------------------------------------------- street lights and wires
lights_made = []


def light(name, kind, loc, energy, rgb, radius=0.15, rot=None, spot=None, aim=None):
    """aim: a stage-local point the light (spot or sun) points at, instead of rot."""
    ld = bpy.data.lights.new(name, kind)
    ld.energy = energy
    ld.color = rgb
    if kind in ("POINT", "SPOT"):
        ld.shadow_soft_size = radius
    if spot:
        ld.spot_size, ld.spot_blend = math.radians(spot[0]), spot[1]
    ob = OB.new(name, ld)
    ob.location = Vector(loc) + ORIGIN
    if aim:
        ob.rotation_euler = (Vector(aim) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    elif rot:
        ob.rotation_euler = [math.radians(a) for a in rot]
    C_LIGHTS.objects.link(ob)
    lights_made.append(name)
    return ob


SODIUM = (1.0, 0.55, 0.22)
pb = Builder()
POLES = [(5.8, -0.6, 0.0), (-6.4, 6.6, 3.0), (6.4, 11.6, 6.0), (-6.4, 16.7, 9.0), (6.6, 27.0, 9.0)]
for i, (x, y, z) in enumerate(POLES):
    pb.box(x - 0.11, x + 0.11, y - 0.11, y + 0.11, z, z + 7.5, "poste", tile=2.0)
    arm = -1 if x > 0 else 1
    pb.box(min(x, x + arm * 1.4), max(x, x + arm * 1.4), y - 0.05, y + 0.05, z + 7.0, z + 7.1, "poste")
    hx = x + arm * 1.4
    pb.box(hx - 0.22, hx + 0.22, y - 0.12, y + 0.12, z + 6.85, z + 7.0, "lampada")
    light(f"luz_poste{i}", "POINT", (hx, y, z + 6.7), 900, SODIUM, 0.2)
pb.build("st_postes", C_LIGHTS)
# Wires: sagging curves from pole to pole and pole to houses, the tangle every favela street has
def wire(a, b, sag=0.6, n=8):
    cu = bpy.data.curves.new("fio", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 0.012
    cu.bevel_resolution = 0
    sp = cu.splines.new("POLY")
    sp.points.add(n)
    a, b = Vector(a) + ORIGIN, Vector(b) + ORIGIN
    for i in range(n + 1):
        t = i / n
        p = a.lerp(b, t) - Vector((0, 0, sag * 4 * t * (1 - t)))
        sp.points[i].co = (*p, 1)
    cu.materials.append(MATS["fio"])
    ob = OB.new("fio", cu)
    C_LIGHTS.objects.link(ob)


for (x0, y0, z0), (x1, y1, z1) in zip(POLES, POLES[1:]):
    for dz in (6.2, 6.5, 6.8):
        wire((x0, y0, z0 + dz), (x1, y1, z1 + dz), 0.7)
for x, y, z in POLES:
    for _ in range(4):
        side = -1 if x < 0 else 1
        wire((x, y, z + rnd.uniform(5.8, 6.8)), (side * rnd.uniform(8, 14), y + rnd.uniform(-1.5, 2.5), z + rnd.uniform(4.5, 7.5)), rnd.uniform(0.3, 0.9))
# Across the plaza: strings of bandeirolas (flags) between the houses
FLAG = [mat_flat(f"bandeira{i}", c, emit=0.25) for i, c in enumerate(((0.95, 0.15, 0.12), (1.0, 0.8, 0.05), (0.1, 0.55, 0.2), (0.12, 0.3, 0.9), (0.95, 0.4, 0.75)))]
fb = Builder()
for j, y in enumerate((18.0, 20.5, 23.0)):
    a, b_ = Vector((-W - 0.5, y, 13.4)), Vector((W + 0.5, y + 1.2, 13.0))
    wire(tuple(a), tuple(b_), 1.1, 12)
    for i in range(1, 24):
        t = i / 24
        p = a.lerp(b_, t) - Vector((0, 0, 1.1 * 4 * t * (1 - t)))
        mname = f"bandeira{(i + j) % 5}"
        fb.v += [tuple(p + Vector((-0.17, 0, 0))), tuple(p + Vector((0.17, 0, 0))), tuple(p + Vector((0, 0, -0.38)))]
        k = len(fb.v)
        fb.f.append((k - 3, k - 2, k - 1))
        fb.uv.append([(0, 1), (1, 1), (0.5, 0)])
        fb.mi.append(fb._m(mname))
fb.build("st_bandeirolas", C_LIGHTS)
# Baile lights: coloured spots over the plaza, a warm work light by the DJ, a red glow behind the speakers
light("baile_magenta", "SPOT", (-5.5, 17.5, 15.0), 3200, (1.0, 0.15, 0.8), 0.3, spot=(50, 0.4), aim=(1.0, 22.0, 9.0))
light("baile_ciano", "SPOT", (5.5, 17.5, 15.0), 3200, (0.1, 0.8, 1.0), 0.3, spot=(50, 0.4), aim=(-1.0, 22.0, 9.0))
light("baile_verde", "SPOT", (0.0, 18.5, 15.5), 1800, (0.3, 1.0, 0.3), 0.3, spot=(40, 0.5), aim=(0.0, 23.5, 9.0))
light("baile_dj", "POINT", (0.0, 23.0, 11.5), 400, (1.0, 0.75, 0.45), 0.3)
light("baile_fundo", "POINT", (0.0, 27.0, 12.0), 1200, (1.0, 0.1, 0.25), 1.0)
light("barril_fogo", "POINT", (-4.6, 7.8, 4.4), 250, (1.0, 0.45, 0.12), 0.2)
light("lua", "SUN", (0, 0, 40), 0.25, (0.55, 0.65, 1.0), rot=(55, 0, 200))

# ---------------------------------------------------------------- far background: the hill across the valley, covered in lit windows
far = bpy.data.materials.get("st morro longe") or bpy.data.materials.new("st morro longe")
far.use_nodes = True
nt = far.node_tree
nt.nodes.clear()
out = nt.nodes.new("ShaderNodeOutputMaterial")
emi = nt.nodes.new("ShaderNodeEmission")
vor = nt.nodes.new("ShaderNodeTexVoronoi")
vor.inputs["Scale"].default_value = 90.0
ramp = nt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].position = 0.0
ramp.color_ramp.elements[0].color = (1.0, 0.7, 0.35, 1)
ramp.color_ramp.elements[1].position = 0.09
ramp.color_ramp.elements[1].color = (0.006, 0.008, 0.018, 1)
ramp.color_ramp.interpolation = "CONSTANT"
nt.links.new(vor.outputs["Distance"], ramp.inputs[0])
nt.links.new(ramp.outputs[0], emi.inputs["Color"])
emi.inputs["Strength"].default_value = 1.6
nt.links.new(emi.outputs[0], out.inputs[0])
fm = bpy.data.meshes.new("st_morro_longe")
fm["stage_made"] = True
bmf = bmesh.new()
res, size = 48, 900.0
for i in range(res + 1):
    for j in range(res + 1):
        x = -size / 2 + size * i / res
        y = 160 + 400 * j / res
        h = 70 * math.exp(-((x - 60) / 260) ** 2) * (0.4 + 0.6 * math.sin(j / res * math.pi)) + 25 * math.sin(i * 0.7) * math.sin(j * 0.5) - 20
        bmf.verts.new((x + ORIGIN.x, y, h))
bmf.verts.ensure_lookup_table()
for i in range(res):
    for j in range(res):
        a = i * (res + 1) + j
        bmf.faces.new((bmf.verts[a], bmf.verts[a + res + 1], bmf.verts[a + res + 2], bmf.verts[a + 1]))
bmf.to_mesh(fm)
bmf.free()
fm.uv_layers.new(name="UVMap")
fm.materials.append(far)
fob = OB.new("st_morro_longe", fm)
C_FAR.objects.link(fob)

json.dump({
    "_": "Written by s05_stage.py. Local stage coordinates: add origin for world coordinates.",
    "origin": list(ORIGIN), "half_width": W, "terraces": TERRACES,
    "flights": [{"x_start": xs, "dir": d, "y0": y0, "y1": y1, "z": zp, "steps": 20, "rise": STEP_R, "run": STEP_T} for xs, d, y0, y1, zp in FLIGHTS],
    "poles": POLES, "lights": lights_made,
    "spots": {"rua": [0, 2.0, 0], "patamar1": [0, 8.5, 3], "muro": [0, 13.8, 6], "baile": [0, 20.5, 9]},
}, open(os.path.join(WORK, "stage.json"), "w", encoding="utf8"), indent=1)

# Show it in the open window: from the street looking up the hill
if not bpy.app.background:
    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            sp = area.spaces[0]
            sp.shading.type = "MATERIAL"
            r3 = sp.region_3d
            r3.view_location = ORIGIN + Vector((0, 12, 6))
            r3.view_distance = 30
            r3.view_rotation = Vector((0, -1, 0.42)).normalized().to_track_quat("Z", "Y")
            r3.update()
            area.tag_redraw()
set_lib.save()
print("stage built:", len(stage.all_objects), "objects,", len(houses.data.polygons), "house polys")
