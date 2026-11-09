# Step 5: the four locations, far apart in one scene so a shot only has to move its camera. Each one has its own lights.
# The lamps are sharp and few, so most of each room stays dark, as in RE1's pre-rendered rooms.
import bpy, importlib, math, os, random, sys
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "thps", "blender"))
sys.path.insert(0, HERE)
import lib, set_lib
importlib.reload(lib); importlib.reload(set_lib)
from lib import Mesh, make_mat, srgb
from set_lib import CORRIDOR, DOOR, DUNGEON, HALL, STREET, fresh, place, quads, tex_mat

OB = bpy.data.objects
sc = bpy.context.scene
sets = fresh("sets", sc)


def at(origin, x, y, z=0.0):
    return (origin[0] + x, origin[1] + y, origin[2] + z)


def lamp(name, origin, x, y, z, energy, colour, radius=0.15, shadow=True, kind="POINT"):
    li = OB.get(name)
    if li:
        OB.remove(li, do_unlink=True)
    li = OB.new(name, bpy.data.lights.new(name, kind))
    sets.objects.link(li)
    li.location = at(origin, x, y, z)
    li.data.energy = energy
    li.data.color = srgb(colour)
    li.data.shadow_soft_size = radius
    li.data.use_shadow = shadow
    return li


def plane(name, a, b, c, d, mat, rep=(1, 1)):
    return quads(name, [([a, b, c, d], rep)], mat, sets)


def fire(name, origin, x, y, z, s=1.0):
    """Blocky low-poly flames in two colours. The shots flicker them by scaling, in steps."""
    core, edge = make_mat("fogo claro", "ffd060", emit=4.0), make_mat("fogo", "e8501a", emit=3.0)
    m = Mesh()
    rnd = random.Random(name)
    tongues = [(rnd.uniform(-0.3, 0.3), rnd.uniform(-0.12, 0.12), rnd.uniform(0.28, 0.7), rnd.uniform(0.05, 0.11), 1) for _ in range(9)]
    tongues += [(rnd.uniform(-0.17, 0.17), rnd.uniform(-0.1, 0.0), rnd.uniform(0.14, 0.36), rnd.uniform(0.03, 0.07), 0) for _ in range(6)]
    for (dx, dy, h, w, mi) in tongues:
        i = len(m.v)
        lean = rnd.uniform(-0.09, 0.09)
        m.v += [(dx - w, dy - w, 0), (dx + w, dy - w, 0), (dx + w, dy + w, 0), (dx - w, dy + w, 0), (dx + lean, dy, h)]
        m.f += [(i, i + 1, i + 4), (i + 1, i + 2, i + 4), (i + 2, i + 3, i + 4), (i + 3, i, i + 4)]
        m.fm += [mi] * 4
    ob = m.build(name, [core, edge], None, sets)
    ob.location = at(origin, x, y, z)
    ob.scale = (s, s, s)
    return ob


# ---- Corridor: the closed green-wallpaper room, carpet along Y, arch at the +Y end
o = CORRIDOR
place("corredor", sets, at(o, 0, 0))
ceil = make_mat("teto", "0c0a08")
plane("cor_teto", at(o, -1.7, -3.2, 3.5), at(o, 1.7, -3.2, 3.5), at(o, 1.7, 3.2, 3.5), at(o, -1.7, 3.2, 3.5), ceil)
# Behind the arch: only dark
plane("cor_fundo", at(o, -1.7, 3.3, 0), at(o, 1.7, 3.3, 0), at(o, 1.7, 3.3, 3.4), at(o, -1.7, 3.3, 3.4), make_mat("fundo", "030303"))
place("retrato", sets, at(o, 1.53, 0.8, 1.35), rz=-90)
place("teias", sets, at(o, 1.45, 2.9, 2.75), rz=-40, s=0.6)
poca = tex_mat("poca", "sangue.png", alpha=True)
plane("cor_sangue", at(o, -0.75, -0.55, 0.05), at(o, 0.75, -0.55, 0.05), at(o, 0.75, 0.95, 0.05), at(o, -0.75, 0.95, 0.05), poca)
lamp("cor_luz1", o, 0.2, 1.1, 3.0, 70, "ffc98a", radius=0.1)
lamp("cor_luz2", o, -0.6, -2.0, 2.6, 30, "9fb8a0", radius=0.25)
lamp("cor_rosto", o, 0.75, -0.75, 1.35, 16, "c8d8c8", radius=0.3, shadow=False)

# ---- Burning street: a road along X, ruins on the far side, the police car in the foreground
o = STREET
asf = tex_mat("asfalto", "asfalto.png")
plane("rua_chao", at(o, -40, -22), at(o, 40, -22), at(o, 40, 46), at(o, -40, 46), asf, rep=(40, 34))
faixa = tex_mat("faixa", "faixa.png")
plane("rua_faixa", at(o, -40, -0.25, 0.01), at(o, 40, -0.25, 0.01), at(o, 40, 0.25, 0.01), at(o, -40, 0.25, 0.01), faixa, rep=(27, 0.17))
place("ruina", sets, at(o, -6, 8), rz=180)
place("ruina2", sets, at(o, 9, 11), rz=90, s=0.9)
place("ruina", sets, at(o, 22, 9), rz=170)
place("ruina2", sets, at(o, -22, 10), rz=95)
# Far blocks, just dark shapes with a few windows
predio = tex_mat("predio", "predio.png", emit=0.35)
items = []
for i, (x, y, w, h) in enumerate(((-36, 38, 7, 16), (-22, 42, 8, 22), (-8, 40, 7, 14), (6, 44, 9, 24), (20, 39, 7, 16), (33, 43, 8, 20))):
    a, b = (x - w, y), (x + w, y)
    items.append(([at(o, a[0], a[1]), at(o, b[0], b[1]), at(o, b[0], b[1], h), at(o, a[0], a[1], h)], (w / 6, h / 24)))
quads("rua_predios", items, predio, sets)
place("viatura", sets, at(o, 0.6, -2.4), rz=78)
place("barreira", sets, at(o, -4.6, 2.6), rz=12)
place("barreira", sets, at(o, 6.2, 3.4), rz=-20)
place("semaforo", sets, at(o, 8, 5.2), rz=180)
place("poste", sets, at(o, -9, 5.4), rz=180)
place("poste", sets, at(o, 18, 5.4), rz=180)
place("soda", sets, at(o, -1.8, 5.2), rz=180)
place("lixeira", sets, at(o, 3.2, 3.6))
place("fita", sets, at(o, -10.5, -3.6), rz=10)
place("giz", sets, at(o, 3.2, -6.6, 0.02), rz=30)
place("helicoptero", sets, at(o, -4, 16, 15), rz=25, rx=8)
fire("fogo_carro", o, 0.2, -2.3, 0.95, s=1.5)
fire("fogo_carro2", o, 1.3, -2.55, 0.85, s=1.1)
fire("fogo_rua", o, -3.2, 4.4, 0.0, s=2.4)
fire("fogo_ruina", o, 7.6, 6.5, 0.0, s=3.6)
fire("fogo_ruina2", o, -12, 7.0, 0.0, s=3.2)
lamp("rua_fogo1", o, 0.7, -2.5, 1.9, 170, "ff7a30", radius=0.3)
lamp("rua_fogo2", o, -3.2, 3.6, 1.6, 260, "ff6a20", radius=0.4, shadow=False)
lamp("rua_fogo3", o, 7.6, 5.6, 2.4, 420, "ff6a20", radius=0.4, shadow=False)
lamp("rua_lua", o, -6, -14, 22, 6500, "7f96d8", radius=1.0)

# ---- Mansion hall: the long lamp-lit wall at +Y, carpeted floor, chandelier in the middle
o = HALL
place("hall", sets, at(o, 0, 0))
plane("hall_teto", at(o, -6, -3, 4.3), at(o, 6, -3, 4.3), at(o, 6, 2, 4.3), at(o, -6, 2, 4.3), ceil)
plane("hall_chao", at(o, -6, -9, -0.01), at(o, 6, -9, -0.01), at(o, 6, -2.0, -0.01), at(o, -6, -2.0, -0.01), make_mat("hall chao", "1c120c"))
place("lustre", sets, at(o, 0, -0.1, 2.75))
place("tapete", sets, at(o, 0, -0.2, 0.02))
place("armario", sets, at(o, -3.9, 1.55), rz=0)
place("piano", sets, at(o, 3.4, 1.2))
place("banqueta", sets, at(o, 3.4, 0.2))
place("relogio", sets, at(o, -5.0, 1.55))
place("estante", sets, at(o, 5.2, 1.3), rz=90, s=0.9)
place("janela", sets, at(o, -1.7, 1.86, 1.0), rz=90)
place("janela", sets, at(o, 1.7, 1.86, 1.0), rz=90)
# Night sky behind the frames. The shots turn this to fire for sodoma e gomorra.
ceu = make_mat("hall ceu", "101a38", emit=1.0)
for side, x in (("a", -1.7), ("b", 1.7)):
    plane(f"hall_ceu_{side}", at(o, x - 0.6, 1.88, 1.05), at(o, x + 0.6, 1.88, 1.05), at(o, x + 0.6, 1.88, 3.55), at(o, x - 0.6, 1.88, 3.55), ceu)
lamp("hall_lustre", o, 0, -0.1, 3.1, 210, "ffcf90", radius=0.2)
lamp("hall_lampa", o, -3.6, 1.2, 2.9, 50, "ffb870", radius=0.1, shadow=False)
lamp("hall_lampb", o, 3.6, 1.2, 2.9, 50, "ffb870", radius=0.1, shadow=False)
lamp("hall_ceu", o, 0, 1.2, 2.2, 20, "6078c0", radius=0.5, shadow=False)
lamp("hall_frente", o, 0.4, -2.6, 2.3, 90, "ffd8b0", radius=0.5, shadow=False)

# ---- Dungeon: walls tiled from the brick-and-torch panel, flagstones, bars across the middle
o = DUNGEON
lajes = tex_mat("lajes", "lajes.png")
plane("mas_chao", at(o, -5, -7), at(o, 5, -7), at(o, 5, 5), at(o, -5, 5), lajes, rep=(5, 6))
plane("mas_teto", at(o, -5, -7, 2.6), at(o, 5, -7, 2.6), at(o, 5, 5, 2.6), at(o, -5, 5, 2.6), ceil)
PANEL = 2.19  # width of one panel at this height
for k in range(-2, 3):
    place("parede_tocha", sets, at(o, k * PANEL, 3.2))
for k in range(-2, 2):
    place("parede_tocha", sets, at(o, -3.3, k * PANEL + 1.0), rz=90)
    place("parede_tocha", sets, at(o, 3.3, k * PANEL + 1.0), rz=-90)
# The bars divide the room at y = 0: the cell is on the +Y side
place("grades", sets, at(o, -1.1, 0), rz=90)
place("grades", sets, at(o, 1.1, 0), rz=90)
place("esqueleto", sets, at(o, -2.4, 2.4), rz=20, s=0.9)
place("caixa", sets, at(o, 2.3, 2.4), rz=15)
place("barata", sets, at(o, 1.5, 1.2), rz=120)
place("teias", sets, at(o, 2.9, 3.0, 2.0), rz=-35, s=0.7)
lamp("mas_tocha1", o, 0, 2.7, 1.9, 80, "ff9a40", radius=0.1)
lamp("mas_tocha2", o, -2.2, -1.8, 2.0, 55, "ff8a30", radius=0.1, shadow=False)
lamp("mas_frio", o, 1.8, -3.2, 2.3, 34, "7088c0", radius=0.3, shadow=False)
lamp("mas_cela", o, 0.4, 0.45, 1.9, 60, "ffd0a0", radius=0.2, shadow=False)

# ---- The door screen: one door in a dark wall, opening onto nothing
o = DOOR
parede_porta = make_mat("parede porta", "1a1410")
plane("porta_parede_a", at(o, -4, 0.02, 0), at(o, -0.62, 0.02, 0), at(o, -0.62, 0.02, 4), at(o, -4, 0.02, 4), parede_porta)
plane("porta_parede_b", at(o, 0.62, 0.02, 0), at(o, 4, 0.02, 0), at(o, 4, 0.02, 4), at(o, 0.62, 0.02, 4), parede_porta)
plane("porta_parede_c", at(o, -0.62, 0.02, 2.32), at(o, 0.62, 0.02, 2.32), at(o, 0.62, 0.02, 4), at(o, -0.62, 0.02, 4), parede_porta)
plane("porta_chao", at(o, -4, -6, 0), at(o, 4, -6, 0), at(o, 4, 0, 0), at(o, -4, 0, 0), make_mat("chao porta", "0e0a08"))
lamp("porta_luz", o, 0.2, -1.6, 2.2, 110, "e8d8b0", radius=0.15, shadow=False)

set_lib.save()
print("=== SETS DONE", len(sets.objects), "objects", flush=True)
