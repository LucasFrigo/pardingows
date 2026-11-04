# Review stills of the cop and car, with the skater for scale. Temporary camera; does not save.
import bpy, os
from mathutils import Vector

OUT = r"C:\Users\lukeg\AppData\Local\Temp\claude\c--Users-lukeg-Projetos-pardingows\ba1c12be-02d2-4a8a-b38f-e6838288c6d1\scratchpad\actors"
os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene
cam_data = bpy.data.cameras.new("as")
cam_data.lens = 28
cam_data.clip_end = 600
cam = bpy.data.objects.new("as", cam_data)
sc.collection.objects.link(cam)
prev = sc.camera
sc.camera = cam
p1 = bpy.data.objects["P1"]
keep = p1.location.copy()
p1.location = (29, 0.5, 0)
shots = (((27.5, -5, 1.4), (29.5, 1, 0.8)), ((21, -6.5, 1.8), (24, -2, 0.6)), ((27.5, -6.0, 1.6), (24, -2, 0.6)), ((29.2, -1.5, 1.2), (30, 3, 1.1)))
for i, (pos, tgt) in enumerate(shots):
    cam.location = pos
    cam.rotation_euler = (Vector(tgt) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    sc.render.filepath = os.path.join(OUT, f"a{i}.png")
    bpy.ops.render.render(write_still=True)
p1.location = keep
sc.camera = prev
bpy.data.objects.remove(cam, do_unlink=True)
bpy.data.cameras.remove(cam_data)
print("actor stills done")
