# Renders the character from several angles at the real internal resolution (no save, temp camera).
import bpy, math, os
from mathutils import Vector

OUT = r"C:\Users\lukeg\AppData\Local\Temp\claude\c--Users-lukeg-Projetos-pardingows\ba1c12be-02d2-4a8a-b38f-e6838288c6d1\scratchpad\turn"
os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene
prev = (sc.camera, sc.render.engine, sc.render.resolution_x, sc.render.resolution_y, sc.render.filepath, sc.render.filter_size, sc.render.resolution_percentage)

cam_data = bpy.data.cameras.new("tt")
cam_data.lens = 50
cam = bpy.data.objects.new("tt", cam_data)
sc.collection.objects.link(cam)
sc.camera = cam
sc.render.engine = "BLENDER_EEVEE"
sc.render.resolution_x, sc.render.resolution_y = 270, 480
sc.render.resolution_percentage = 100
sc.render.filter_size = 0.01
sc.render.image_settings.file_format = "PNG"

world = sc.world
bg = world.node_tree.nodes.get("Background") if world and world.use_nodes else None
prev_bg = tuple(bg.inputs[0].default_value) if bg else None
prev_str = bg.inputs[1].default_value if bg else None
if bg:
    bg.inputs[0].default_value = (0.35, 0.6, 0.95, 1)
    bg.inputs[1].default_value = 1.0

target = Vector((0, -0.4, 3.0))
for i, ang in enumerate((-25, 35, 110, 200)):
    a = math.radians(ang)
    pos = target + Vector((math.sin(a) * 15, -math.cos(a) * 15, 1.5))
    cam.location = pos
    cam.rotation_euler = (target - pos).to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    sc.render.filepath = os.path.join(OUT, f"t{i}.png")
    bpy.ops.render.render(write_still=True)

sc.camera, sc.render.engine, sc.render.resolution_x, sc.render.resolution_y, sc.render.filepath, sc.render.filter_size, sc.render.resolution_percentage = prev
if bg:
    bg.inputs[0].default_value = prev_bg
    bg.inputs[1].default_value = prev_str
bpy.data.objects.remove(cam, do_unlink=True)
bpy.data.cameras.remove(cam_data)
print("turntable done", OUT)
