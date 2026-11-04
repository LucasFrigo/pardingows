# Step 2: imports the Sketchfab models into the "assets" collection, each under its own "<name>_import" empty, and reports what they contain.
# Safe to re-run: it clears everything built after step 1 so s03 onwards can run again in order.
import bpy, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib, set_lib; importlib.reload(set_lib)
from set_lib import ASSETS
from mathutils import Vector

NAMES = ("arvore", "arvore2", "coqueiro", "casa", "casa2", "casa3", "flor", "bambu", "lirio", "lotus", "cerca", "poste", "banco", "mesa",
         "correio", "maca", "gato", "pato", "cachorro", "guaxinim", "abelha", "celular", "aero", "koi", "golfinho", "ilha", "balao")

scene = bpy.context.scene
# Keep only the two rigs from step 1
KEEP = {"rigs", "smurf"}
for c in list(bpy.data.collections):
    if c.name not in KEEP:
        for ob in list(c.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.collections.remove(c)
for ob in list(bpy.data.objects):
    if ob.users_collection and all(c.name in KEEP for c in ob.users_collection):
        continue
    bpy.data.objects.remove(ob, do_unlink=True)
for a in list(bpy.data.actions):
    bpy.data.actions.remove(a)
bpy.data.orphans_purge(do_recursive=True)

coll = bpy.data.collections.new("assets")
scene.collection.children.link(coll)

for name in NAMES:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(ASSETS, name, "gltf", "scene.gltf"))
    new = [o for o in bpy.data.objects if o not in before]
    root = bpy.data.objects.new(name + "_import", None)
    coll.objects.link(root)
    for ob in new:
        for c in list(ob.users_collection):
            c.objects.unlink(ob)
        coll.objects.link(ob)
        ob["asset"] = name
        if not ob.parent:
            ob.parent = root
    bpy.context.view_layer.update()
    mins, maxs = [1e9] * 3, [-1e9] * 3
    polys, tex = 0, set()
    arms = []
    for ob in new:
        if ob.type == "ARMATURE":
            arms.append((ob.name, len(ob.data.bones)))
        if ob.type != "MESH":
            continue
        polys += len(ob.data.polygons)
        for m in ob.data.materials:
            if m and m.use_nodes:
                tex |= {f"{n.image.size[0]}x{n.image.size[1]}" for n in m.node_tree.nodes if n.type == "TEX_IMAGE" and n.image}
        for c in ob.bound_box:
            p = ob.matrix_world @ Vector(c)
            for i in range(3):
                mins[i], maxs[i] = min(mins[i], p[i]), max(maxs[i], p[i])
    meshes = [o.name for o in new if o.type == "MESH"]
    print(f"== {name}: {len(meshes)} meshes, {polys} polys, tex {sorted(tex)} arm {arms}")
    print("   bbox", [round(v, 2) for v in mins], [round(v, 2) for v in maxs], meshes[:10] if len(meshes) <= 10 else f"{len(meshes)} meshes")

# Rendering and the viewport stay clean: the originals are only read by later steps.
coll.hide_render = True
coll.hide_viewport = False
set_lib.save()
print("images", len(bpy.data.images), "materials", len(bpy.data.materials))
