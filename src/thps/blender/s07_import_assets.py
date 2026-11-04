# Step 3d: imports the Sketchfab cop and car into the "assets" collection and reports what they contain.
import bpy, os
from mathutils import Vector

ASSETS = r"C:\Users\lukeg\Projetos\pardingows\blender\solucao\assets"
coll = bpy.data.collections.get("assets")
if coll:
    for ob in list(coll.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
else:
    coll = bpy.data.collections.new("assets")
    bpy.context.scene.collection.children.link(coll)

# Remove earlier imports completely, or the new materials come back renamed .001
for ob in list(bpy.data.objects):
    if ob.name in ("cop_cap", "cop_plug", "car_letter"):
        bpy.data.objects.remove(ob, do_unlink=True)
for m in list(bpy.data.materials):
    if m.name.startswith(("cop", "car_PS1")):
        bpy.data.materials.remove(m)
for img in list(bpy.data.images):
    if img.name.startswith(("cop", "car_PS1", "car_pardo")):
        bpy.data.images.remove(img)
for a in list(bpy.data.armatures):
    if a.users == 0:
        bpy.data.armatures.remove(a)

for name in ("cop", "car"):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(ASSETS, name, "gltf", "scene.gltf"))
    new = [o for o in bpy.data.objects if o not in before]
    for ob in new:
        for c in list(ob.users_collection):
            c.objects.unlink(ob)
        coll.objects.link(ob)
        ob["asset"] = name
    bpy.context.view_layer.update()
    print("==", name, len(new), "objects")
    mins, maxs = [1e9] * 3, [-1e9] * 3
    for ob in new:
        info = [ob.name, ob.type, "parent=" + (ob.parent.name if ob.parent else "-")]
        if ob.type == "MESH":
            info += [f"polys={len(ob.data.polygons)}", f"mats={[m.name for m in ob.data.materials if m]}", f"vg={len(ob.vertex_groups)}", f"mods={[m.type for m in ob.modifiers]}"]
            for c in ob.bound_box:
                p = ob.matrix_world @ Vector(c)
                for i in range(3):
                    mins[i], maxs[i] = min(mins[i], p[i]), max(maxs[i], p[i])
        if ob.type == "ARMATURE":
            info.append(f"bones={len(ob.data.bones)}")
        print("  " + " ".join(info))
    print("  bbox", [round(v, 2) for v in mins], [round(v, 2) for v in maxs])
print("actions", [a.name for a in bpy.data.actions])
bpy.ops.wm.save_mainfile()
