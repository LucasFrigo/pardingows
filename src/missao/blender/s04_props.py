# Step 4: turns the raw prop imports into clean actors, each a root empty at ground level with its transforms baked in.
# All the favela pieces share one scale, since they come from one artist and must match. Textures drop to PS1 size.
# Needs a fresh import (run s02 and s03 first).
import bpy, sys, importlib
from mathutils import Matrix, Vector
sys.path.insert(0, r"C:\Users\lukeg\Projetos\pardingows\src\thps\blender")
sys.path.insert(0, r"C:\Users\lukeg\Projetos\pardingows\src\missao\blender")
import lib, set_lib
importlib.reload(lib); importlib.reload(set_lib)
from lib import empty
from set_lib import ps1_material, shrink

OB = bpy.data.objects
coll = bpy.data.collections["assets"]
FAR = (500, 500, -50)
FAVELA = 0.44


def wipe(asset):
    for o in [o for o in OB if o.get("asset") == asset]:
        OB.remove(o, do_unlink=True)
    e = OB.get(asset + "_import")
    if e:
        OB.remove(e, do_unlink=True)


def bake(asset, root_name, size=None, axis="z", scale=None, keep=None, tex=128, leave=False):
    """Bakes world transforms into copies of the meshes and puts their bottom centre on a new root.
    size scales the chosen axis to that many metres, scale is a plain factor, keep picks meshes by name."""
    obs = [o for o in OB if o.get("asset") == asset and o.type == "MESH"]
    if keep:
        obs = [o for o in obs if keep(o.name)]
    bpy.context.view_layer.update()
    root = empty(root_name, None, coll=coll, size=0.5)
    baked = []
    for o in obs:
        me = o.data.copy()
        me.transform(o.matrix_world)
        new = bpy.data.objects.new(root_name + " " + o.name, me)
        coll.objects.link(new)
        baked.append(new)
    if not leave:
        wipe(asset)
    pts = [v.co.copy() for b in baked for v in b.data.vertices]
    lo = Vector(min(p[i] for p in pts) for i in range(3))
    hi = Vector(max(p[i] for p in pts) for i in range(3))
    s = scale if scale else size / (hi - lo)["xyz".index(axis)]
    shift = Matrix.Scale(s, 4) @ Matrix.Translation(-Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z)))
    for b in baked:
        b.data.transform(shift)
        b.parent = root
        for p in b.data.polygons:
            p.use_smooth = False
        for m in b.data.materials:
            ps1_material(m)
            shrink(m, tex)
    root["size"] = tuple((hi - lo) * s)
    root.location = FAR
    print(root_name, "size", [round(v, 2) for v in (hi - lo) * s], "meshes", len(baked), "faces", sum(len(b.data.polygons) for b in baked))
    return root


bake("casas1", "CASA1", scale=FAVELA, tex=256)
bake("casas2", "CASA2", scale=FAVELA, tex=256)
bake("rua1", "RUA1", scale=FAVELA, tex=256)
bake("rua2", "RUA2", scale=FAVELA, tex=256)
bake("cerca", "CERCA", 2.0, tex=128)
bake("van", "VAN", 5.6, axis="x", tex=128)
bake("props", "BARREIRA", 1.0, keep=lambda n: n.startswith("barriers1"), tex=128, leave=True)
bake("props", "LIXO_RUA", 1.1, keep=lambda n: n.startswith(("Tank.001", "Cap.001")), tex=128)
bake("colchao", "COLCHAO", 1.9, axis="x", tex=128)
bake("relogio", "RELOGIO", 0.26, axis="x", tex=128)
bake("criado", "CRIADO", 0.55, tex=128)
bake("abajur", "ABAJUR", 0.55, tex=128)
bake("grana", "GRANA", 0.7, axis="y", tex=128)
bake("grana2", "GRANA2", 0.9, axis="x", tex=128)
bake("lixeira", "LIXEIRA", 3.0, axis="x", tex=256)
bake("sacos", "SACOS", 0.95, tex=128)
bake("lata", "LATA", 1.0, tex=128)
bake("bosta", "BOSTA", 0.55, tex=128)
bake("poca", "POCA", 3.0, axis="x")
bake("rato", "RATO", 0.42, axis="y", tex=64)
bake("kiosk", "KIOSK", 3.2, tex=256)
bake("caixa", "CAIXA", 0.45, axis="x", tex=128)
bake("poles", "POSTE", 6.5, tex=128)

bpy.data.orphans_purge(do_recursive=True)
bpy.context.view_layer.update()
set_lib.save()
left = sorted(o.name for o in coll.objects if o.get("asset"))
print("unbaked left", left[:12], "images", len(bpy.data.images), "MB", round(sum(i.size[0] * i.size[1] * 4 for i in bpy.data.images) / 1e6))
