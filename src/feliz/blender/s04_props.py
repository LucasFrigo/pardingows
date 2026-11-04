# Step 4: turns the imports into single-mesh prefabs ("<name>_mesh" in the hidden "prefabs" collection) and makes the villagers, each with shades and a chain.
import bpy, math, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib, set_lib; importlib.reload(set_lib)
from set_lib import flatten, fresh, gloss, place, recentre, shrink, soften_asset_material
from mathutils import Vector
from mathutils.bvhtree import BVHTree

OB = bpy.data.objects
assets = bpy.data.collections["assets"]
scene = bpy.context.scene

# The glTF importer adds a helper mesh per armature for its bone shapes. They aren't part of any model. So are the ground planes some authors include.
for ob in list(assets.objects):
    drop = re.fullmatch(r"Icosphere(\.\d+)?", ob.name) or ob.name in ("Plane_0",)
    if ob.type == "MESH" and drop:
        OB.remove(ob, do_unlink=True)
# The raccoon comes as a whole diorama: only the raccoon stays
for ob in list(assets.objects):
    if ob.get("asset") == "guaxinim" and ob.type == "MESH" and re.search(r"Arrow|Footprint|Ground|Name|Speech|Suitcase|Spork|Leaf|Leaves|Pile|Text", ob.name):
        OB.remove(ob, do_unlink=True)

for ob in assets.objects:
    if ob.type == "MESH":
        for m in ob.data.materials:
            soften_asset_material(m)
            shrink(m)
bpy.context.view_layer.update()

prefabs = fresh("prefabs")
# name: (height in metres, yaw so its front looks along -Y)
PREFABS = {
    "arvore": (5.2, 0), "arvore2": (4.4, 0), "coqueiro": (5.6, 0), "casa": (5.4, 0), "casa2": (6.0, 0), "casa3": (4.2, 0),
    "flor": (0.42, 0), "bambu": (3.2, 0), "lirio": (0.5, 0), "lotus": (0.8, 0), "cerca": (1.0, 0), "poste": (3.2, 0), "banco": (0.9, 0),
    "mesa": (0.8, 0), "correio": (1.3, 0), "maca": (0.3, 0), "abelha": (0.34, 0), "celular": (0.5, 0), "aero": (1.1, 0), "koi": (0.9, 0),
    "golfinho": (0.9, 0), "ilha": (6.0, 0), "balao": (9.0, 0),
    "gato": (1.2, 0), "pato": (1.15, 0), "cachorro": (1.15, 0), "guaxinim": (1.3, 0),
}
for name, (h, yaw) in PREFABS.items():
    ob = flatten(name, target_h=h, face_yaw=yaw)
    print(name, "faces", len(ob.data.polygons), "dims", [round(d, 2) for d in ob.dimensions])
prefabs.hide_render = True

# Shades and chain as loose pieces with their own origin, for dropping onto villagers
acc = fresh("acessorios")
acc.hide_render = True


def loose(src_names, name):
    """Joins pieces of the pardo's outfit into one mesh, origin at its centre, in pardo armature units."""
    verts, faces, mats, fm = [], [], [], []
    for n in src_names:
        me = OB[n].data
        base = len(verts)
        verts += [v.co.copy() for v in me.vertices]
        slots = []
        for m in me.materials:
            if m not in mats:
                mats.append(m)
            slots.append(mats.index(m))
        for p in me.polygons:
            faces.append([base + i for i in p.vertices])
            fm.append(slots[p.material_index])
    c = sum(verts, Vector()) / len(verts)
    out = bpy.data.meshes.new(name)
    out.from_pydata([tuple(v - c) for v in verts], [], faces)
    for m in mats:
        out.materials.append(m)
    for p, i in zip(out.polygons, fm):
        p.material_index = i
    out.update()
    ob = OB.new(name, out)
    acc.objects.link(ob)
    return ob


loose(["shades"], "acc_shades")
loose(["chain", "medallion"], "acc_chain")

# Villagers: root object is the mesh, feet at its origin. Accessories hang on it at "off" scale until they land.
# name: (eye height, shades scale, chest height, chain scale). The depth comes from a ray fired at the model, so they sit on its surface.
VILLAGERS = {
    "gato": (0.93, 0.19, 0.60, 0.24),
    "pato": (0.92, 0.17, 0.52, 0.22),
    "cachorro": (0.72, 0.21, 0.40, 0.22),
    "guaxinim": (0.95, 0.19, 0.52, 0.22),
}
cast = fresh("villagers")
dg = bpy.context.evaluated_depsgraph_get()
for name, (ez, ss, cz, cs) in VILLAGERS.items():
    v = place(name, cast, label="V_" + name)
    bpy.context.view_layer.update()
    dg.update()
    tree = BVHTree.FromObject(v.evaluated_get(dg), dg)
    for acc_name, z, s, lift in (("acc_shades", ez, ss, 0.01), ("acc_chain", cz, cs, 0.02)):
        hit = tree.ray_cast(Vector((0, -20, z)), Vector((0, 1, 0)))[0]
        y = (hit.y if hit else -0.3) - lift
        a = OB.new(f"V_{name}_{acc_name[4:]}", OB[acc_name].data)
        cast.objects.link(a)
        a.parent = v
        a.location = (0, y, z)
        a.scale = (s, s, s)
        a["rest_scale"] = s
        a["rest_z"] = z
        print(name, acc_name, "on surface at y", round(y, 3), "hit" if hit else "MISS")
set_lib.save()
print("props ok")
