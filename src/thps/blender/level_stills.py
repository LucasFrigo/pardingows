# Renders review stills of the plaza from the chase-cam height. Temporary camera; does not save.
import bpy, os
from mathutils import Vector

OUT = r"C:\Users\lukeg\AppData\Local\Temp\claude\c--Users-lukeg-Projetos-pardingows\ba1c12be-02d2-4a8a-b38f-e6838288c6d1\scratchpad\level"
os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene
cam_data = bpy.data.cameras.new("ls")
cam_data.lens = 24
cam_data.clip_end = 600
cam = bpy.data.objects.new("ls", cam_data)
sc.collection.objects.link(cam)
prev = sc.camera
sc.camera = cam
root = bpy.data.objects["P1"]
keep = root.location.copy()
for i, (pos, tgt, skater) in enumerate((
    ((1.2, -3.2, 1.8), (9, 0, 1.0), (3.5, 0, 0)),
    ((22, -8, 2.2), (30, 2, 3), (24, 0, 0)),
    ((33, -6, 2.0), (43, 1, 1.8), (36.5, 0, 0)),
    ((60, -6, 2.0), (76, 0, 4), (66, 0, 0.03)),
)):
    root.location = skater
    cam.location = pos
    cam.rotation_euler = (Vector(tgt) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    sc.render.filepath = os.path.join(OUT, f"l{i}.png")
    bpy.ops.render.render(write_still=True)
root.location = keep
sc.camera = prev
bpy.data.objects.remove(cam, do_unlink=True)
bpy.data.cameras.remove(cam_data)
print("level stills done")
