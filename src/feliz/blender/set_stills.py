# Look check: two stills of the island, cozy and full Aero, plus the time a real frame takes. Doesn't save the file.
#   "$BLENDER" -b blender/feliz/feliz.blend -P src/feliz/blender/set_stills.py -- [out.png]
import bpy, math, os, sys, tempfile, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import set_lib, path
from set_lib import REVIEW, RENDER_H, RENDER_W
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = args[0] if args else os.path.join(REVIEW, "04-look.png")
OB = bpy.data.objects
sc = bpy.context.scene
cam = OB.new("sheet", bpy.data.cameras.new("sheet"))
sc.collection.objects.link(cam)
cam.data.lens = 26
cam.data.clip_start = 0.05
cam.data.clip_end = 900
sc.camera = cam
P = OB["P1"]
P.location = (0, 0, 0)
P.rotation_euler = (0, 0, 0)


def set_aero(k):
    sc.world.node_tree.nodes["aero"].outputs[0].default_value = k
    for m in ("chao", "agua"):
        bpy.data.materials[m].node_tree.nodes["aero"].outputs[0].default_value = k


def shot(s, pos, tgt, k):
    OB["tronco"].rotation_euler = (path.rot_for(s), 0, 0)
    set_aero(k)
    cam.location = pos
    cam.rotation_euler = (Vector(tgt) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    p = os.path.join(tempfile.gettempdir(), "feliz_still.png")
    sc.render.filepath = p
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"RENDER s={s} aero={k}: {time.time() - t0:.2f}s at {RENDER_W}x{RENDER_H}, {sc.eevee.taa_render_samples} samples", flush=True)
    im = bpy.data.images.load(p)
    px = np.empty(RENDER_W * RENDER_H * 4, np.float32)
    im.pixels.foreach_get(px)
    bpy.data.images.remove(im)
    return px.reshape(RENDER_H, RENDER_W, 4)


cells = [
    shot(path.HOME + 1.5, (1.1, -3.6, 1.0), (0, 0.5, 1.1), 0.0),
    shot(path.PRACA, (2.0, -5.5, 2.2), (0, 1.5, 1.2), 0.3),
    shot(path.CELULAR, (3.0, -4.0, 1.5), (14, 1, 0.5), 0.5),
    shot(path.AERO, (1.3, -4.0, 0.55), (0, 2, 1.7), 1.0),
]
sheet = np.hstack(cells)
h, w = sheet.shape[:2]
img = bpy.data.images.new("sheet_out", w, h)
img.pixels.foreach_set(sheet.ravel())
img.filepath_raw = OUT
img.file_format = "PNG"
img.save()
print("sheet", OUT, w, h)
