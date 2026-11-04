# Renders every library pose on P1 with a chase-style camera. Scratch only; does not save.
import bpy, math, os, sys, importlib
from mathutils import Vector
sys.path.insert(0, r"C:\Users\lukeg\Projetos\pardingows\src\thps\blender")
import lib, poses
importlib.reload(lib); importlib.reload(poses)

OUT = r"C:\Users\lukeg\AppData\Local\Temp\claude\c--Users-lukeg-Projetos-pardingows\ba1c12be-02d2-4a8a-b38f-e6838288c6d1\scratchpad\poses"
os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene
cam_data = bpy.data.cameras.new("ps")
cam_data.lens = 35
cam = bpy.data.objects.new("ps", cam_data)
sc.collection.objects.link(cam)
sc.camera = cam
sc.render.engine = "BLENDER_EEVEE"
sc.render.resolution_x, sc.render.resolution_y = 270, 480
sc.render.resolution_percentage = 100
sc.render.filter_size = 0.01
sc.render.image_settings.file_format = "PNG"

sun_data = bpy.data.lights.new("ps", "SUN")
sun_data.energy = 3.0
sun = bpy.data.objects.new("ps", sun_data)
sc.collection.objects.link(sun)
sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(-30))
sc.world.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.62, 0.72, 1)
sc.world.node_tree.nodes["Background"].inputs[1].default_value = 1.0

root = bpy.data.objects["P1"]
target = Vector((0, 0, 0.85))
pos = Vector((-2.4, -3.4, 1.5))
cam.location = pos
cam.rotation_euler = (target - pos).to_track_quat("-Z", "Y").to_euler()

names = []
for name, p in poses.ALL.items():
    lib.apply_pose("P1", p)
    bpy.data.objects["P1_board"].hide_render = bool(p.get("free"))
    bpy.context.view_layer.update()
    sc.render.filepath = os.path.join(OUT, f"{name}.png")
    bpy.ops.render.render(write_still=True)
    names.append(name)

bpy.data.objects["P1_board"].hide_render = False
lib.apply_pose("P1", poses.RIDE)
bpy.data.objects.remove(cam, do_unlink=True)
bpy.data.cameras.remove(cam_data)
bpy.data.objects.remove(sun, do_unlink=True)
bpy.data.lights.remove(sun_data)
print(",".join(names))
