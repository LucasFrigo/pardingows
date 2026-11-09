# Review render of the model library in the cartoon look: every AS_ collection instanced in a labelled grid on a
# temporary stage at y = +80, shot from the front. Everything temporary is removed afterwards.
#   node src/thps/bl.mjs run src/erva/blender/gallery.py
# Out: blender/erva/review/04-biblioteca.png
import importlib
import math
import os
import sys

import bpy
from mathutils import Euler, Vector

try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    HERE = os.path.join(os.environ.get("ERVA_ROOT", r"E:\Projetos\pardingows"), "src", "erva", "blender")
sys.path.insert(0, HERE)
import set_lib  # noqa: E402
importlib.reload(set_lib)
from set_lib import REVIEW, cel  # noqa: E402

lib = bpy.data.collections["library"]
packs = {c.name[3:].rsplit("_", 1)[0] for c in lib.children if c.name[-1].isdigit() and "_" in c.name[3:]}
items = [c for c in lib.children if c.name[3:] not in packs]  # a split pack shows as its pieces
g = bpy.data.collections.new("gallery_tmp")
bpy.context.scene.collection.children.link(g)
temp = []
COLS, CELL = 10, 5.0
for i, c in enumerate(sorted(items, key=lambda c: c.name)):
    x, z = (i % COLS) * CELL, -(i // COLS) * CELL * 1.1
    inst = bpy.data.objects.new("gal_" + c.name, None)
    inst.instance_type = "COLLECTION"
    inst.instance_collection = c
    inst.location = (x, 80.0, z)
    g.objects.link(inst)
    txt = bpy.data.curves.new("galtxt_" + c.name, "FONT")
    txt.body = c.name[3:]
    txt.size = 0.32
    txt.align_x = "CENTER"
    t = bpy.data.objects.new("galtxt_" + c.name, txt)
    t.location = (x, 78.0, z - 0.55)
    t.rotation_euler = (math.radians(90), 0, 0)
    txt.materials.append(cel("gallery label", 0.02))
    g.objects.link(t)
    temp += [inst, t]
rows = math.ceil(len(items) / COLS)
floor_me = bpy.data.meshes.new("gal_floor")
floor_me.from_pydata([(-5, 70, -rows * CELL * 1.1 - 2), (COLS * CELL, 70, -rows * CELL * 1.1 - 2),
                      (COLS * CELL, 95, -rows * CELL * 1.1 - 2), (-5, 95, -rows * CELL * 1.1 - 2)], [], [(0, 1, 2, 3)])
cam_d = bpy.data.cameras.new("gal_cam")
cam_d.type = "ORTHO"
cam_d.ortho_scale = COLS * CELL + 2
cam = bpy.data.objects.new("gal_cam", cam_d)
g.objects.link(cam)
cam.location = (COLS * CELL / 2 - CELL / 2, 40.0, -(rows - 1) * CELL * 1.1 / 2 + 1.5)
cam.rotation_euler = Euler((math.radians(88), 0, 0))
sc = bpy.context.scene
old = (sc.camera, sc.render.resolution_x, sc.render.resolution_y, sc.render.filepath)
saved = {o.name: o.hide_render for o in bpy.data.objects}
lib_objs = set(lib.all_objects)  # instances only show what their source shows: the library stays as it is
for o in bpy.data.objects:
    if o not in temp and o is not cam and o.type != "LIGHT" and o not in lib_objs:
        o.hide_render = True
sc.camera = cam
sc.render.resolution_x, sc.render.resolution_y = 2400, int(2400 * (rows * CELL * 1.1 + 1) / (COLS * CELL + 2))
sc.render.filepath = os.path.join(REVIEW, "04-biblioteca.png")
bpy.ops.render.render(write_still=True)
for o in bpy.data.objects:
    if o.name in saved:
        o.hide_render = saved[o.name]
sc.camera, sc.render.resolution_x, sc.render.resolution_y, sc.render.filepath = old
for o in list(g.objects):
    bpy.data.objects.remove(o, do_unlink=True)
bpy.data.collections.remove(g)
bpy.data.meshes.remove(floor_me)
bpy.data.cameras.remove(cam_d)
for cu in [c for c in bpy.data.curves if c.name.startswith("galtxt_")]:
    bpy.data.curves.remove(cu)
print("gallery:", len(items), "items")
