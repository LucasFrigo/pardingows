# Step 2: imports the Sketchfab models into the "assets" collection, each under its own "<name>_import" empty, and reports what they contain.
# Textures are capped at 256 px on import: some corridor maps are 4K, and a PS1 look needs none of that.
# Safe to re-run: it clears everything built after step 1 so s03 onwards can run again in order.
import bpy, os, sys, importlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import set_lib; importlib.reload(set_lib)
from set_lib import ASSETS, ps1_material, shrink
from mathutils import Vector

NAMES = sorted(n for n in os.listdir(ASSETS) if os.path.isdir(os.path.join(ASSETS, n)))
TEX_CAP = 256

scene = bpy.context.scene
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
    acts_before = set(bpy.data.actions)
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
    polys, tex, arms = 0, set(), []
    mats = set()
    for ob in new:
        if ob.type == "ARMATURE":
            arms.append((ob.name, len(ob.data.bones), [b.name for b in ob.data.bones][:70]))
        if ob.type != "MESH":
            continue
        polys += len(ob.data.polygons)
        for m in ob.data.materials:
            if m:
                mats.add(m)
                if m.use_nodes:
                    tex |= {f"{n.image.size[0]}x{n.image.size[1]}" for n in m.node_tree.nodes if n.type == "TEX_IMAGE" and n.image}
        for c in ob.bound_box:
            p = ob.matrix_world @ Vector(c)
            for i in range(3):
                mins[i], maxs[i] = min(mins[i], p[i]), max(maxs[i], p[i])
    for m in mats:
        ps1_material(m)
        shrink(m, TEX_CAP, name)
    bpy.data.orphans_purge(do_recursive=True)
    meshes = [o.name for o in new if o.type == "MESH"]
    print(f"== {name}: {len(meshes)} meshes, {polys} polys, {len(mats)} mats, tex {sorted(tex)}")
    print("   bbox", [round(v, 2) for v in mins], [round(v, 2) for v in maxs], meshes[:14] if len(meshes) <= 14 else f"{len(meshes)} meshes")
    for a in arms:
        print("   armature", a[0], a[1], "bones:", a[2])
    acts = [a.name for a in bpy.data.actions if a not in acts_before]
    if acts:
        print("   actions", acts[:10])

coll.hide_render = True
set_lib.save()
print("images", len(bpy.data.images), "materials", len(bpy.data.materials))
print("=== IMPORT DONE", flush=True)
