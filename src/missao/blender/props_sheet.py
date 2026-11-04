# Review sheet of the baked props, one view each at the real panel size. Puts everything back.
# Writes blender/missao/review/02-props.png.
#   node src/thps/bl.mjs run src/missao/blender/props_sheet.py
import bpy, math, os, tempfile
import numpy as np
from mathutils import Vector

OUT = r"C:\Users\lukeg\Projetos\pardingows\blender\missao\review\02-props.png"
OB = bpy.data.objects
sc = bpy.context.scene
W, H, COLS = 270, 240, 5
r = sc.render
prev_cam, prev_path = sc.camera, r.filepath
r.resolution_x, r.resolution_y = W, H
cam_data = bpy.data.cameras.new("sheet")
cam_data.lens = 30
cam_data.clip_end = 900
cam = bpy.data.objects.new("sheet", cam_data)
sc.collection.objects.link(cam)
sc.camera = cam
tmp = tempfile.mkdtemp(prefix="missao_props_")

NAMES = ["CASA1", "CASA2", "RUA1", "RUA2", "CERCA", "VAN", "BARREIRA", "LIXO_RUA", "COLCHAO", "RELOGIO", "CRIADO", "ABAJUR", "GRANA", "GRANA2",
         "LIXEIRA", "SACOS", "LATA", "BOSTA", "POCA", "RATO", "KIOSK", "CAIXA", "POSTE"]
cells = []
for i, name in enumerate(NAMES):
    root = OB[name]
    saved = root.location.copy()
    root.location = (0, 0, 0)
    size = Vector(root["size"])
    d = max(size) * 1.25 + 0.2
    tgt = Vector((0, 0, size.z * 0.45))
    pos = tgt + Vector((-0.55, -0.85, 0.4)) * d
    cam.location = pos
    cam.rotation_euler = (tgt - pos).to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    path = os.path.join(tmp, f"{i}.png")
    r.filepath = path
    bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(path)
    px = np.empty(W * H * 4, np.float32)
    im.pixels.foreach_get(px)
    bpy.data.images.remove(im)
    cells.append(px.reshape(H, W, 4))
    root.location = saved

while len(cells) % COLS:
    cells.append(np.zeros((H, W, 4), np.float32) + np.array([0, 0, 0, 1], np.float32))
rows = [np.hstack(cells[i:i + COLS]) for i in range(0, len(cells), COLS)]
sheet = np.vstack(rows[::-1])
h, w = sheet.shape[:2]
img = bpy.data.images.new("sheet_out", w, h)
img.pixels.foreach_set(sheet.ravel())
img.filepath_raw = OUT
img.file_format = "PNG"
img.save()
bpy.data.images.remove(img)
sc.camera, r.filepath = prev_cam, prev_path
bpy.data.objects.remove(cam, do_unlink=True)
bpy.data.cameras.remove(cam_data)
print("sheet", OUT, w, h)
