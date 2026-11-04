# Turnaround sheet: every character from four angles. Works on a temporary copy of the state and never saves the file.
#   "$BLENDER" -b blender/feliz/feliz.blend -P src/feliz/blender/cast_sheet.py -- [out.png]
import bpy, math, os, sys, tempfile
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import set_lib
from set_lib import REVIEW
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = args[0] if args else os.path.join(REVIEW, "03-cast.png")
OB = bpy.data.objects
sc = bpy.context.scene
W, H = 360, 420
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = W, H, 100
sc.eevee.taa_render_samples = 16

cam = OB.new("sheet", bpy.data.cameras.new("sheet"))
sc.collection.objects.link(cam)
cam.data.lens = 40
cam.data.clip_end = 900
sc.camera = cam

# Plain green floor so shading and contact read
bpy.ops.mesh.primitive_plane_add(size=300, location=(0, 0, 0))
floor = bpy.context.active_object
floor.data.materials.append(set_lib.gloss("sheet floor", rgb="7ccb66", rough=0.8, coat=0))

spots = {}
for i, n in enumerate(("P1", "P2", "B1")):
    OB[n].location = (i * 5, 0, 0)
    spots[n] = ((i * 5, 0, 0), 0.72, 3.6)
for i, ob in enumerate(sorted((o for o in OB if o.name.startswith("V_") and o.parent is None and o.name.count(".") == 0), key=lambda o: o.name)):
    ob.location = (i * 5, 12, 0)
    spots[ob.name] = ((i * 5, 12, 0), 0.5, 3.2)
bpy.context.view_layer.update()

tmp = tempfile.mkdtemp(prefix="feliz_sheet_")


def shot(tag, pos, tgt):
    cam.location = pos
    cam.rotation_euler = (Vector(tgt) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    path = os.path.join(tmp, tag + ".png")
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(path)
    px = np.empty(W * H * 4, np.float32)
    im.pixels.foreach_get(px)
    bpy.data.images.remove(im)
    return px.reshape(H, W, 4)


rows = []
for name, (loc, up, dist) in spots.items():
    target = Vector(loc) + Vector((0, -0.05, up))
    cells = []
    for i, ang in enumerate((-22, 35, 110, 195)):
        a = math.radians(ang)
        cells.append(shot(f"{name}_{i}", target + Vector((math.sin(a) * dist, -math.cos(a) * dist, 0.35)), target))
    rows.append(np.hstack(cells))
sheet = np.vstack(rows[::-1])
h, w = sheet.shape[:2]
img = bpy.data.images.new("sheet_out", w, h)
img.pixels.foreach_set(sheet.ravel())
img.filepath_raw = OUT
img.file_format = "PNG"
img.save()
print("sheet", OUT, w, h)
