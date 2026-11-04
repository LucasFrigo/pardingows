# Step 7: the small story sets, each far from the street along +Y so their lights never reach it:
# quarto (y = 600), lixao (y = 700), lanchonete (y = 800). Also the coxinha, coins and R$ notes that both scenes use.
# Safe to re-run after s05.
import bpy, math, os, random, sys, importlib
import numpy as np
from mathutils import Matrix
sys.path.insert(0, r"C:\Users\lukeg\Projetos\pardingows\src\thps\blender")
sys.path.insert(0, r"C:\Users\lukeg\Projetos\pardingows\src\missao\blender")
import lib, set_lib
importlib.reload(lib); importlib.reload(set_lib)
from lib import Mesh, make_mat, srgb
from set_lib import tex_mat, quads, place, fresh

OB = bpy.data.objects
story = bpy.data.scenes["STORY"]
assets = bpy.data.collections["assets"]
TEX = r"C:\Users\lukeg\Projetos\pardingows\blender\missao\textures"
SOL = r"C:\Users\lukeg\Projetos\pardingows\blender\solucao\textures"
rng = random.Random(11)


def light(name, coll, loc, energy, col):
    d = bpy.data.lights.new(name, "POINT")
    d.energy = energy
    d.color = srgb(col)
    d.shadow_soft_size = 0.15
    d.use_shadow = False
    ob = bpy.data.objects.new(name, d)
    ob.location = loc
    coll.objects.link(ob)
    return ob


def tinted_tex(name, path_, rgb):
    m = tex_mat(name, path_)
    t = m.node_tree
    tex = next(n for n in t.nodes if n.type == "TEX_IMAGE")
    bsdf = next(n for n in t.nodes if n.type == "BSDF_DIFFUSE")
    mix = t.nodes.new("ShaderNodeMixRGB")
    mix.blend_type = "MULTIPLY"
    mix.inputs[0].default_value = 1.0
    mix.inputs[2].default_value = (*srgb(rgb), 1)
    t.links.new(tex.outputs[0], mix.inputs[1])
    t.links.new(mix.outputs[0], bsdf.inputs["Color"])
    return m


def lathe(name, profile, mat, n=10, mat_top=None):
    """Spun around Z from (radius, height) pairs. An open top gets a flat cap in mat_top."""
    v, f, fm = [], [], []
    for r, z in profile:
        for k in range(n):
            a = 2 * math.pi * (k + 0.5) / n
            v.append((r * math.cos(a), r * math.sin(a), z))
    for i in range(len(profile) - 1):
        for k in range(n):
            a, b = i * n + k, i * n + (k + 1) % n
            f.append((a, b, b + n, a + n))
            fm.append(0)
    f.append(tuple(range(n - 1, -1, -1)))
    fm.append(0)
    top = (len(profile) - 1) * n
    f.append(tuple(top + k for k in range(n)))
    fm.append(1 if mat_top else 0)
    me = bpy.data.meshes.new(name)
    me.from_pydata(v, [], f)
    uv = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = (math.atan2(co.y, co.x) / 3.14159 + 1.0, co.z * 2)
    me.materials.append(mat)
    if mat_top:
        me.materials.append(mat_top)
    for p, i in zip(me.polygons, fm):
        p.material_index = i
        p.use_smooth = False
    ob = bpy.data.objects.new(name + "_mesh", me)
    assets.objects.link(ob)
    return ob


# ---- The coxinha: golden crumbs, teardrop, with a bitten version showing the chicken
for o in ("COXINHA_mesh", "COXINHA_MORD_mesh", "MOEDA_mesh", "GRANA_NOTA_mesh"):
    if OB.get(o):
        OB.remove(OB[o], do_unlink=True)
r2 = np.random.default_rng(5)
crumb = np.dstack([0.78 + r2.normal(0, 0.09, (32, 32)), 0.43 + r2.normal(0, 0.08, (32, 32)), 0.10 + r2.normal(0, 0.04, (32, 32)), np.ones((32, 32))]).clip(0, 1).astype(np.float32)
img = bpy.data.images.get("coxinha") or bpy.data.images.new("coxinha", 32, 32)
img.pixels.foreach_set(crumb.ravel())
img.filepath_raw = os.path.join(TEX, "coxinha.png")
img.file_format = "PNG"
img.save()
COX = tex_mat("coxinha", os.path.join(TEX, "coxinha.png"), emit=0.35)
FRANGO = make_mat("frango", "f2e0b0", emit=0.3)
TEAR = [(0.02, 0.0), (0.30, 0.05), (0.43, 0.2), (0.41, 0.4), (0.31, 0.6), (0.18, 0.78), (0.07, 0.92), (0.015, 1.0)]
lathe("COXINHA", TEAR, COX)
lathe("COXINHA_MORD", TEAR[:4] + [(0.36, 0.5)], COX, mat_top=FRANGO)

# ---- Coins and the note that sits on every cash stack
COIN = tex_mat("moeda", os.path.join(TEX, "coin.png"), emit=0.5)
m = lathe("MOEDA", [(0.26, -0.035), (0.26, 0.035)], COIN, n=8)
m.data.transform(Matrix.Rotation(math.pi / 2, 4, "X"))
uv = m.data.uv_layers["UVMap"]
for poly in m.data.polygons:
    for li in poly.loop_indices:
        co = m.data.vertices[m.data.loops[li].vertex_index].co
        uv.data[li].uv = (co.x / 0.52 + 0.5, co.z / 0.52 + 0.5)
NOTA = tex_mat("nota", os.path.join(TEX, "nota.png"))
size = OB["GRANA"]["size"]
hx, hy, top = size[0] / 2, size[1] / 2, size[2] + 0.004
# The note's long side runs along the stack, so its UVs turn with it
nm = bpy.data.meshes.new("GRANA_NOTA")
nm.from_pydata([(-hx, -hy, top), (hx, -hy, top), (hx, hy, top), (-hx, hy, top)], [], [(0, 1, 2, 3)])
nu = nm.uv_layers.new(name="UVMap")
for loop, c in zip(nu.data, ((1, 0), (1, 1), (0, 1), (0, 0))):
    loop.uv = c
nm.materials.append(NOTA)
assets.objects.link(bpy.data.objects.new("GRANA_NOTA_mesh", nm))
# The loose pile can't be repainted note by note, so it just shifts from dollar green to the note's blue
pile = OB["GRANA2_mesh"].data.materials[0]
if pile.use_nodes and not pile.node_tree.nodes.get("azul"):
    t = pile.node_tree
    tex = next(n for n in t.nodes if n.type == "TEX_IMAGE")
    sock = next((n.inputs["Base Color"] for n in t.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if sock:
        hs = t.nodes.new("ShaderNodeHueSaturation")
        hs.name = "azul"
        hs.inputs["Hue"].default_value = 0.75
        t.links.new(tex.outputs[0], hs.inputs["Color"])
        t.links.new(hs.outputs[0], sock)

# ---- Quarto: a bare room with a mattress on the floor. The room is open towards the camera at y = 598.
q = fresh("quarto", story)
Y0, Y1, XW, ZH = 597.0, 603.0, 2.4, 2.7
WALL = tinted_tex("parede", os.path.join(SOL, "tx_concrete.png"), "8a9a78")
FLOOR = tinted_tex("piso", os.path.join(SOL, "tx_concrete.png"), "9a7a5c")
quads("q_paredes", [([(-XW, Y1, 0), (XW, Y1, 0), (XW, Y1, ZH), (-XW, Y1, ZH)], (3, 2)),
                    ([(-XW, Y0, 0), (-XW, Y1, 0), (-XW, Y1, ZH), (-XW, Y0, ZH)], (3, 2)),
                    ([(XW, Y1, 0), (XW, Y0, 0), (XW, Y0, ZH), (XW, Y1, ZH)], (3, 2)),
                    ([(XW, Y0, 0), (-XW, Y0, 0), (-XW, Y0, ZH), (XW, Y0, ZH)], (3, 2))], WALL, q)
quads("q_piso", [([(-XW, Y0, 0), (XW, Y0, 0), (XW, Y1, 0), (-XW, Y1, 0)], (3, 4))], FLOOR, q)
quads("q_teto", [([(-XW, Y1, ZH), (XW, Y1, ZH), (XW, Y0, ZH), (-XW, Y0, ZH)], (1, 1))], make_mat("teto", "2a2c2a"), q)
# Window: dark night glass with bars and a slab of moonlight
GLASS = make_mat("vidro", "16245a", emit=0.9)
BAR = make_mat("grade", "101014")
wy = Y1 - 0.01
quads("q_janela", [([(0.7, wy, 1.1), (1.8, wy, 1.1), (1.8, wy, 2.1), (0.7, wy, 2.1)], (1, 1))], GLASS, q)
wm = Mesh()
for x in (0.92, 1.14, 1.36, 1.58):
    wm.box((x, wy - 0.01, 1.6), (0.018, 0.012, 0.5), 0)
wm.box((1.25, wy - 0.01, 1.6), (0.55, 0.012, 0.02), 0)
wm.build("q_grade", [BAR], None, q)
quads("q_poster", [([(-1.5, wy, 1.05), (-0.75, wy, 1.05), (-0.75, wy, 2.15), (-1.5, wy, 2.15)], (1, 1))], tex_mat("poster", os.path.join(TEX, "poster.png")), q)

ob = place("COLCHAO", q, (0.25, 601.45, 0.0))
ob.name = "story_colchao"
place("CRIADO", q, (-1.1, 602.3, 0.0), 0).name = "story_criado"
clock = place("RELOGIO", q, (-1.1, 602.25, 0.55), 0)
clock.name = "story_relogio"
face_y = 602.25 - OB["RELOGIO"]["size"][1] / 2 - 0.004
quads("story_relogio_lcd", [([(-1.2, face_y, 0.565), (-1.0, face_y, 0.565), (-1.0, face_y, 0.625), (-1.2, face_y, 0.625)], (1, 1))], tex_mat("lcd", os.path.join(TEX, "clock.png"), emit=2.0), q)
place("ABAJUR", q, (-1.35, 602.45, 0.55), 0).name = "story_abajur"
place("SACOS", q, (2.0, 602.3, 0), 30).name = "story_sacos"
g = place("GRANA", q, (0.55, 601.45, 0.005), 90)
g.name = "story_grana"
n = bpy.data.objects["GRANA_NOTA_mesh"].copy()
n.name = "story_grana_nota"
n.parent = g
n.location = (0, 0, 0)
q.objects.link(n)
light("q_lua", q, (1.2, 601.5, 2.2), 30, "6a80ff")
light("q_abajur", q, (-1.25, 602.2, 1.25), 0, "ffc880")  # off until he wakes, keyed in the shots
light("q_relogio", q, (-1.1, 601.9, 0.62), 0.5, "ff3018")

# ---- Lixão: a mountain of bags at night with the fence behind it
lx = fresh("lixao", story)
quads("lx_chao", [([(-40, 680, 0), (40, 680, 0), (40, 750, 0), (-40, 750, 0)], (20, 18))], tinted_tex("lx_terra", os.path.join(SOL, "tx_asphalt.png"), "a08458"), lx)
for i in range(46):
    a, d = rng.uniform(0, 6.28), rng.uniform(0, 7.5) ** 1.0
    x, y = d * math.cos(a), 706 + d * math.sin(a) * 0.65
    z = max(0, 2.6 - d * 0.42) + rng.uniform(-0.1, 0.2)
    place("SACOS", lx, (x, y, z), rng.uniform(0, 360), rng.uniform(1.0, 1.9))
for x, y, rz in ((-4.6, 700.5, 18), (5.0, 701.5, -24)):
    place("LIXEIRA", lx, (x, y, 0), rz)
for x, y in ((-2.4, 699.5), (2.8, 699.2), (0.9, 701.2)):
    place("LATA", lx, (x, y, 0), rng.uniform(0, 360))
place("RATO", lx, (-0.9, 699.5, 0.02), 40, 1.8).name = "story_rato"
place("BOSTA", lx, (1.6, 699.0, 0), 0, 0.8)
for x in (-14, -7, 0, 7, 14):
    place("CERCA", lx, (x, 714, 0), 0, 1.4)
for x, dz in ((-20, 0), (-11, 1), (-3, 3), (6, 2), (15, 0)):
    place("CASA1" if int(x) % 2 else "CASA2", lx, (x, 722, dz), 180)
light("lx_luz", lx, (0, 698, 5.5), 2400, "d8e0a8")
light("lx_fill", lx, (-6, 694, 3), 700, "8fa0ff")

# ---- Lanchonete: the kiosk, with a sign, a counter and a warm bulb. Its door side faces the camera at y < 800.
la = fresh("lanchonete", story)
quads("la_chao", [([(-30, 780, 0), (30, 780, 0), (30, 840, 0), (-30, 840, 0)], (12, 12))], bpy.data.materials["asfalto"], la)
ks = OB["KIOSK"]["size"]
place("KIOSK", la, (0, 803.2, 0), 0).name = "story_kiosk"
front = 803.2 - ks[1] / 2 - 0.02
hw = ks[0] / 2
quads("la_placa", [([(-hw, front - 0.3, 2.75), (hw, front - 0.3, 2.75), (hw, front - 0.3, 3.3), (-hw, front - 0.3, 3.3)], (1, 1))], tex_mat("placa", os.path.join(TEX, "sign_lanchonete.png"), emit=1.2), la)
quads("la_menu", [([(-1.8, front - 0.02, 1.15), (-0.8, front - 0.02, 1.15), (-0.8, front - 0.02, 1.9), (-1.8, front - 0.02, 1.9)], (1, 1))], tex_mat("menu", os.path.join(TEX, "menu.png"), emit=0.7), la)
BALCAO = make_mat("balcao", "b03a22")
TOPO = make_mat("balcao topo", "d8d4c8")
cm = Mesh()
cm.box((0, 800.7, 0.5), (2.0, 0.42, 0.5), 0)
cm.box((0, 800.7, 1.03), (2.1, 0.5, 0.03), 1)
cm.build("la_balcao", [BALCAO, TOPO], None, la)
place("CAIXA", la, (1.2, 800.7, 1.06), 180).name = "story_caixa"
coxa = bpy.data.objects["COXINHA_mesh"].copy()
coxa.name = "story_coxinha"
coxa.location = (0.1, 800.55, 1.06)
coxa.scale = (0.75, 0.75, 0.9)
la.objects.link(coxa)
mord = bpy.data.objects["COXINHA_MORD_mesh"].copy()
mord.name = "story_coxinha_mord"
mord.location = (0.1, 800.55, 1.06)
mord.scale = (0.75, 0.75, 0.9)
mord.hide_render = True
la.objects.link(mord)
for x, kind in ((-3.8, "CASA1"), (3.9, "CASA2"), (-8.6, "CASA2"), (8.8, "CASA1")):
    place(kind, la, (x, 806, 0), 180)
crate = Mesh()
crate.box((-0.72, 800.0, 0.29), (0.3, 0.26, 0.29), 0)
crate.build("la_engradado", [make_mat("engradado", "c8a018")], None, la)
bm = Mesh()
bm.box((0, 800.0, 2.55), (0.05, 0.05, 0.07), 0)
bm.build("la_lampada", [make_mat("bulbo", "ffe6a0", emit=6.0)], None, la)
light("la_luz", la, (0, 799.6, 2.5), 260, "ffd090")

bpy.data.orphans_purge(do_recursive=True)
set_lib.save()
print("story sets ok", {c: len(bpy.data.collections[c].objects) for c in ("quarto", "lixao", "lanchonete")})
