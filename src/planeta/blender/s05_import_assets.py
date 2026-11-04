# Step 5: imports the Sketchfab models into the "assets" collection, each under its own "<name>_import" empty,
# and reports what they contain. Safe to re-run: removes the previous imports first.
import bpy, os
from mathutils import Vector

ASSETS = r"C:\Users\lukeg\Projetos\pardingows\blender\planeta\assets"
NAMES = ("cesar", "chimp", "sky", "asteroids", "lander", "module", "moonbase", "poles", "pistol", "boxes")

coll = bpy.data.collections.get("assets")
if coll:
    for ob in list(coll.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
else:
    coll = bpy.data.collections.new("assets")
    bpy.context.scene.collection.children.link(coll)
bpy.data.orphans_purge(do_recursive=True)

for name in NAMES:
    before = set(bpy.data.objects)
    actions_before = set(bpy.data.actions)
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
    polys, tex, keys = 0, set(), []
    arms = []
    for ob in new:
        if ob.type == "ARMATURE":
            arms.append((ob.name, len(ob.data.bones), [b.name for b in ob.data.bones][:60]))
        if ob.type != "MESH":
            continue
        polys += len(ob.data.polygons)
        if ob.data.shape_keys:
            keys += [k.name for k in ob.data.shape_keys.key_blocks]
        for m in ob.data.materials:
            if m and m.use_nodes:
                tex |= {f"{n.image.size[0]}x{n.image.size[1]}" for n in m.node_tree.nodes if n.type == "TEX_IMAGE" and n.image}
        for c in ob.bound_box:
            p = ob.matrix_world @ Vector(c)
            for i in range(3):
                mins[i], maxs[i] = min(mins[i], p[i]), max(maxs[i], p[i])
    meshes = [o.name for o in new if o.type == "MESH"]
    print(f"== {name}: {len(new)} objects, {len(meshes)} meshes, {polys} polys, textures {sorted(tex)}")
    print("   bbox", [round(v, 2) for v in mins], [round(v, 2) for v in maxs])
    if len(meshes) <= 8:
        print("   meshes", meshes)
    for a in arms:
        print("   armature", a[0], a[1], "bones:", a[2])
    if keys:
        print("   shape keys", keys[:30])
    acts = [a.name for a in bpy.data.actions if a not in actions_before]
    if acts:
        print("   actions", acts)
bpy.ops.wm.save_mainfile()
