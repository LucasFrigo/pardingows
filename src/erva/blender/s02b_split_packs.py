# Step 4a (continued): splits the multi-model packs into one library collection per piece, AS_<pack>_<k>, by grouping
# the pack's meshes whose footprints touch (a tree's trunk and leaves stay together). Each piece sits at the origin,
# base on the ground. Also fixes the two props whose length runs along Y (cigarette, joints). Re-runnable.
#   node src/thps/bl.mjs run src/erva/blender/s02b_split_packs.py
import importlib
import json
import os
import sys

import bpy
from mathutils import Matrix, Vector

try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    HERE = os.path.join(os.environ.get("ERVA_ROOT", r"E:\Projetos\pardingows"), "src", "erva", "blender")
sys.path.insert(0, HERE)
import set_lib  # noqa: E402
importlib.reload(set_lib)
from set_lib import WORK, save  # noqa: E402

PACKS = ("arvores_toon", "arvores_pack", "pedras", "flores", "cogumelos")
LONG_Y = {"cigarro": 0.14, "baseados": 0.16}  # length along Y, metres
PER_MESH = {"arvores_toon"}  # each mesh is already one tree (their footprints overlap a little)
lib = bpy.data.collections["library"]
OB = bpy.data.objects


def wbox(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return Vector([min(p[i] for p in pts) for i in range(3)]), Vector([max(p[i] for p in pts) for i in range(3)])


bpy.context.view_layer.layer_collection.children["library"].exclude = False  # matrices only update when included
bpy.context.view_layer.update()

for name, metres in LONG_Y.items():
    root = OB[name + "_root"]
    meshes = [o for o in bpy.data.collections["AS_" + name].objects if o.type == "MESH"]
    lo = Vector((1e9,) * 3)
    hi = Vector((-1e9,) * 3)
    for o in meshes:
        a, b = wbox(o)
        lo, hi = Vector(map(min, lo, a)), Vector(map(max, hi, b))
    k = metres / (hi.y - lo.y)
    root.scale = root.scale * k
    root.location = root.location * k
    bpy.context.view_layer.update()

pieces = {}
for pack in PACKS:
    for c in [c for c in lib.children if c.name.startswith(f"AS_{pack}_")]:
        for o in list(c.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.collections.remove(c)
    # ground planes that run under the whole pack would join everything into one piece: dropped
    meshes = [o for o in bpy.data.collections["AS_" + pack].objects if o.type == "MESH" and len(o.data.vertices) > 8]
    boxes = {o: wbox(o) for o in meshes}
    parent = {o: o for o in meshes}

    def find(o):
        while parent[o] is not o:
            parent[o] = parent[parent[o]]
            o = parent[o]
        return o

    for i, a in enumerate(meshes if pack not in PER_MESH else []):
        for b in meshes[i + 1:]:
            (a0, a1), (b0, b1) = boxes[a], boxes[b]
            if a0.x - 0.05 <= b1.x and b0.x - 0.05 <= a1.x and a0.y - 0.05 <= b1.y and b0.y - 0.05 <= a1.y:
                parent[find(a)] = find(b)
    groups = {}
    for o in meshes:
        groups.setdefault(find(o), []).append(o)
    groups = sorted(groups.values(), key=lambda g: min(boxes[o][0].x for o in g))
    out = []
    for k, grp in enumerate(groups):
        lo = Vector((1e9,) * 3)
        hi = Vector((-1e9,) * 3)
        for o in grp:
            lo, hi = Vector(map(min, lo, boxes[o][0])), Vector(map(max, hi, boxes[o][1]))
        coll = bpy.data.collections.new(f"AS_{pack}_{k}")
        lib.children.link(coll)
        shift = Matrix.Translation(Vector((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)))
        for o in grp:
            n = o.copy()  # shares the mesh, keeps its modifiers (the ink line)
            n.parent = None
            n.matrix_world = shift @ o.matrix_world
            coll.objects.link(n)
        out.append([round(v, 2) for v in (hi - lo)])
    pieces[pack] = out
    print(pack, len(out), "pieces:", out)

bpy.context.view_layer.layer_collection.children["library"].exclude = True
rep = os.path.join(WORK, "review", "02-import.json")
r = json.load(open(rep, encoding="utf8"))
r["_pieces"] = pieces
json.dump(r, open(rep, "w", encoding="utf8"), indent=1)
save()
