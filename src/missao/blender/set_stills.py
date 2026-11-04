# Stills of the sets through a temporary camera at the real panel size. Puts everything back.
#   node src/thps/bl.mjs run src/missao/blender/set_stills.py [via STILLS below]
# Writes blender/missao/review/03-sets.png.
import bpy, math, os, sys, tempfile, importlib
import numpy as np
from mathutils import Vector

OUT = r"C:\Users\lukeg\Projetos\pardingows\blender\missao\review\03-sets.png"
SCENE = bpy.data.scenes
W, H, COLS = 270, 240, 3

STILLS = [
    ("RUN", (0, 5.8, 3.3), (0, -6, 0.9), 26),
    ("RUN", (2, -60, 3.3), (2, -72, 0.9), 26),
    ("RUN", (-2, -130, 3.3), (-2, -142, 0.9), 26),
    ("RUN", (0, -88, 1.6), (6, -96, 2.4), 24),
    ("STORY", (0, -100, 1.5), (-6, -108, 3), 24),
    ("STORY", (3, -150, 1.2), (-6, -152, 3.5), 28),
]
if bpy.data.collections.get("quarto"):
    STILLS += [("STORY", (0.6, 598.6, 1.35), (-0.3, 601, 0.5), 24), ("STORY", (-1.1, 599.2, 0.55), (0.3, 600.8, 0.35), 30), ("STORY", (0, 598.3, 1.5), (0, 601, 1.2), 22)]
if bpy.data.collections.get("lixao"):
    STILLS += [("STORY", (0, 695, 1.6), (0, 702, 1.1), 24)]
if bpy.data.collections.get("lanchonete"):
    STILLS += [("STORY", (0, 794.5, 1.4), (0, 800, 1.5), 24), ("STORY", (1.2, 798, 1.2), (0, 800.4, 1.15), 34)]

tmp = tempfile.mkdtemp(prefix="missao_sets_")
cells = []
for i, (scene, pos, tgt, lens) in enumerate(STILLS):
    sc = SCENE[scene]
    r = sc.render
    prev = (sc.camera, r.filepath)
    d = bpy.data.cameras.new("still")
    d.lens = lens
    d.clip_start = 0.05
    d.clip_end = 900
    cam = bpy.data.objects.new("still", d)
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.location = pos
    cam.rotation_euler = (Vector(tgt) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
    path = os.path.join(tmp, f"{i}.png")
    r.filepath = path
    bpy.ops.render.render(write_still=True, scene=sc.name)
    im = bpy.data.images.load(path)
    px = np.empty(W * H * 4, np.float32)
    im.pixels.foreach_get(px)
    bpy.data.images.remove(im)
    cells.append(px.reshape(H, W, 4))
    sc.camera, r.filepath = prev
    bpy.data.objects.remove(cam, do_unlink=True)
    bpy.data.cameras.remove(d)

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
print("sheet", OUT, w, h)
