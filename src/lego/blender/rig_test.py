# Imports each candidate base rig into a clean scene, reports its bones and meshes, and renders it at rest, from behind and in a pose or its own animations.
#   blender -b --factory-startup -P src/lego/blender/rig_test.py
# Out: blender/lego/review/02-rig-<name>-<view>.png. Touches no project .blend.
import bpy, math, os
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
ASSETS = os.path.join(ROOT, "blender", "lego", "assets")
REVIEW = os.path.join(ROOT, "blender", "lego", "review")
NAMES = sorted(n for n in os.listdir(ASSETS) if n.startswith("rig_"))
UNITY_SHOTS = [("Dance", 0.3), ("AirGuitar", 0.4), ("Flexing", 0.5), ("Run", 0.25), ("Walk", 0.25), ("Wave", 0.4), ("Sit", 0.5)]


def bbox(meshes):
    """Real, skinned extent: the evaluated vertices, not the rest-pose bound box."""
    dg = bpy.context.evaluated_depsgraph_get()
    lo, hi = [1e9] * 3, [-1e9] * 3
    for ob in meshes:
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        for v in me.vertices:
            p = ev.matrix_world @ v.co
            for i in range(3):
                lo[i], hi[i] = min(lo[i], p[i]), max(hi[i], p[i])
        ev.to_mesh_clear()
    return Vector(lo), Vector(hi)


def shoot(path, meshes, view_y=1.0):
    sc = bpy.context.scene
    lo, hi = bbox(meshes)
    c, size = (lo + hi) / 2, max((hi - lo).length, 1e-4)
    cam = bpy.data.objects.get("cam")
    if not cam:
        cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
        sc.collection.objects.link(cam)
        sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
        sun.data.energy = 4
        sun.rotation_euler = (math.radians(50), 0, math.radians(30))
        sc.collection.objects.link(sun)
        w = bpy.data.worlds.new("w")
        w.use_nodes = True
        w.node_tree.nodes["Background"].inputs[0].default_value = (0.75, 0.8, 0.85, 1)
        sc.world = w
    d = size * 1.6
    cam.location = c + Vector((d * 0.35, d * view_y, d * 0.15))
    cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.clip_start, cam.data.clip_end = size * 0.01, size * 100
    sc.camera = cam
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y = 300, 400
    sc.render.filepath = path
    sc.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)


for name in NAMES:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=os.path.join(ASSETS, name, "gltf", "scene.gltf"))
    # Every import carries a bone-shape helper sphere, which would take over the framing
    for ob in list(bpy.data.objects):
        if ob.name.startswith("Icosphere"):
            bpy.data.objects.remove(ob, do_unlink=True)
    bpy.context.view_layer.update()
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    acts = {a.name: a for a in bpy.data.actions}
    lo, hi = bbox(meshes)
    print(f"\n=== {name}: {len(meshes)} meshes, {sum(len(o.data.polygons) for o in meshes)} polys, {len(arms)} armatures, {len(acts)} actions; size {[round(x, 4) for x in hi - lo]}")
    if name == "rig_unity":
        print("  actions", sorted(acts))
        print("  meshes", [(o.name, o.data.materials[0].name if o.data.materials else None, len(o.data.polygons)) for o in meshes])
        print("  bones", [b.name for b in arms[0].data.bones])
        print("  arm obj", arms[0].matrix_world.to_scale(), [p.name for p in arms[0].children][:3], arms[0].parent.name if arms[0].parent else None)
    for ob in bpy.data.objects:
        if ob.animation_data:
            ob.animation_data.action = None
    shoot(os.path.join(REVIEW, f"02-rig-{name}-rest.png"), meshes)
    shoot(os.path.join(REVIEW, f"02-rig-{name}-back.png"), meshes, -1.0)
    if name == "rig_unity":
        arm = arms[0]
        arm.animation_data_create()
        for act, u in UNITY_SHOTS:
            a = acts.get(act) or next((acts[k] for k in acts if k.lower().startswith(act.lower())), None)
            if not a:
                print("  no action", act)
                continue
            arm.animation_data.action = a
            if a.slots:
                arm.animation_data.action_slot = a.slots[0]
            f0, f1 = a.frame_range
            bpy.context.scene.frame_set(int(f0 + (f1 - f0) * u))
            bpy.context.view_layer.update()
            print("  ", a.name, f0, f1)
            shoot(os.path.join(REVIEW, f"02-rig-{name}-{act}.png"), meshes)
print("RIG TEST DONE")
