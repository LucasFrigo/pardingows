# Step 2: imports every Sketchfab model into the "assets" collection, each under its own "<name>_import" empty, and reports what it contains.
# Textures are capped so one scene with many figures fits on 8 GB. Crowd figures drop their own 48 actions: all figures share the base rig's.
# Safe to re-run: it clears everything built after step 1 so s03 onwards can run again in order.
import bpy, os, sys, importlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import set_lib; importlib.reload(set_lib)
from set_lib import ASSETS, save, shrink

NAMES = sorted(n for n in os.listdir(ASSETS) if os.path.isdir(os.path.join(ASSETS, n)))
CAPS = {"rig_unity": 1024}
FIG_CAP, OTHER_CAP = 512, 1024

scene = bpy.context.scene
for c in list(bpy.data.collections):
    for ob in list(c.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.collections.remove(c)
for ob in list(bpy.data.objects):
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
    # Every import carries a bone-shape helper sphere, and the rigs an invisible picking box
    for ob in list(new):
        if ob.name.startswith("Icosphere") or "AssetPicking" in ob.name:
            new.remove(ob)
            bpy.data.objects.remove(ob, do_unlink=True)
    root = bpy.data.objects.new(name + "_import", None)
    coll.objects.link(root)
    for ob in new:
        for c in list(ob.users_collection):
            c.objects.unlink(ob)
        coll.objects.link(ob)
        ob["asset"] = name
        if not ob.parent:
            ob.parent = root
    acts = [a for a in bpy.data.actions if a not in acts_before]
    if name == "rig_unity":
        for a in acts:
            a.name = "U_" + a.name
            a.use_fake_user = True
    else:
        for ob in new:
            if ob.animation_data:
                ob.animation_data.action = None
        for a in acts:
            bpy.data.actions.remove(a)
    mats = {m for ob in new if ob.type == "MESH" for m in ob.data.materials if m}
    cap = CAPS.get(name, FIG_CAP if name.startswith("fig_") else OTHER_CAP)
    for m in mats:
        shrink(m, cap, name)
    bpy.data.orphans_purge(do_recursive=True)
    meshes = [o for o in new if o.type == "MESH"]
    arms = [o for o in new if o.type == "ARMATURE"]
    print(f"== {name}: {len(meshes)} meshes, {sum(len(o.data.polygons) for o in meshes)} polys, {len(mats)} mats, armature bones {[len(a.data.bones) for a in arms]}, actions {len(acts)}", flush=True)

coll.hide_render = True
for ob in coll.objects:
    ob.hide_set(True)
save()
print("images", len(bpy.data.images), "materials", len(bpy.data.materials))
print("=== IMPORT DONE", flush=True)
