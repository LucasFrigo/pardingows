# Review sheet at the real internal resolution: four rows of characters from four angles, then four views of the set.
# Uses a temporary camera and puts everything back. Writes blender/planeta/review/01-personagens.png.
#   node src/thps/bl.mjs run src/planeta/blender/char_sheet.py
import bpy, math, os, sys, tempfile, importlib
import numpy as np
from mathutils import Vector
sys.path.insert(0, r"C:\Users\lukeg\Projetos\pardingows\src\thps\blender")
import lib, poses
importlib.reload(lib); importlib.reload(poses)
from lib import apply_pose
from poses import STAND

OUT = r"C:\Users\lukeg\Projetos\pardingows\blender\planeta\review\01-personagens.png"
OB = bpy.data.objects
sc = bpy.context.scene
W, H, CROP = 270, 480, 50
prev_cam, prev_path = sc.camera, sc.render.filepath
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = W, H, 100

cam_data = bpy.data.cameras.new("sheet")
cam_data.lens = 40
cam_data.clip_end = 900
cam = bpy.data.objects.new("sheet", cam_data)
sc.collection.objects.link(cam)
sc.camera = cam
apply_pose("P1", STAND)
apply_pose("P2", STAND)

SPOTS = {"P1": ((0, 0, 0), 0.75, 3.4), "P2": ((5, 0, 0), 0.8, 3.6), "CHIMP1": ((10, 0, 0), 0.8, 3.8), "CESAR": ((15, 0, 0), 1.05, 4.6)}
saved = {n: OB[n].location.copy() for n in SPOTS}
SETS = (((-3, -9, 1.5), (-7, 9, 3)), ((-18, -3, 1.2), (-21, 12, 2)), ((8, -6, 1.4), (10, 3.9, 2)), ((24, -8, 1.4), (34, 26, 6)))

tmp = tempfile.mkdtemp(prefix="planeta_sheet_")

def shot(tag):
    bpy.context.view_layer.update()
    path = os.path.join(tmp, tag + ".png")
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(path)
    px = np.empty(W * H * 4, np.float32)
    im.pixels.foreach_get(px)
    bpy.data.images.remove(im)
    return px.reshape(H, W, 4)[CROP:H - CROP]

rows = []
for name, (loc, up, dist) in SPOTS.items():
    OB[name].location = loc
for name, (loc, up, dist) in SPOTS.items():
    target = Vector(loc) + Vector((0, -0.1, up))
    cells = []
    for i, ang in enumerate((-22, 28, 110, 195)):
        a = math.radians(ang)
        pos = target + Vector((math.sin(a) * dist, -math.cos(a) * dist, 0.25))
        cam.location = pos
        cam.rotation_euler = (target - pos).to_track_quat("-Z", "Y").to_euler()
        cells.append(shot(f"{name}_{i}"))
    rows.append(np.hstack(cells))
cells = []
for i, (pos, tgt) in enumerate(SETS):
    cam.location = pos
    cam.rotation_euler = (Vector(tgt) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
    cells.append(shot(f"set_{i}"))
rows.append(np.hstack(cells))

# Image pixels run bottom-up, so the first row goes last to land on top
sheet = np.vstack(rows[::-1])
h, w = sheet.shape[:2]
img = bpy.data.images.new("sheet_out", w, h)
img.pixels.foreach_set(sheet.ravel())
img.filepath_raw = OUT
img.file_format = "PNG"
img.save()
bpy.data.images.remove(img)

for n, l in saved.items():
    OB[n].location = l
sc.camera, sc.render.filepath = prev_cam, prev_path
bpy.data.objects.remove(cam, do_unlink=True)
bpy.data.cameras.remove(cam_data)
print("sheet", OUT, w, h)
