# Review sheet of the raw imports: every asset framed to its own size, from the front (-Y) and a raised three-quarter view, so orientation and scale can be read.
# Also prints each asset's real size and, for kits, its parts. Doesn't save the .blend. Writes blender/zombies/review/02-props.png.
#   "$BLENDER" -b blender/zombies/zombies.blend -P src/zombies/blender/props_sheet.py
import bpy, math, os, sys, tempfile
import numpy as np
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from set_lib import WORK

OUT = os.path.join(WORK, "review", "02-props.png")
OB = bpy.data.objects
sc = bpy.context.scene
CW, CH = 180, 180
r = sc.render
r.engine = "BLENDER_EEVEE"
r.resolution_x, r.resolution_y, r.resolution_percentage = CW, CH, 100
r.filter_size = 0.01
r.image_settings.file_format = "PNG"
sc.eevee.taa_render_samples = 1
sc.view_settings.view_transform = "Standard"
sc.view_settings.look = "None"
sc.world = sc.world or bpy.data.worlds.new("sheet")
sc.world.use_nodes = True
sc.world.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.10, 0.09, 1)
sc.world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
for name, energy, rot in (("sheet_sun", 3.0, (50, 10, -30)), ("sheet_back", 2.0, (-55, 0, 20))):
    s = OB.new(name, bpy.data.lights.new(name, "SUN"))
    sc.collection.objects.link(s)
    s.data.energy = energy
    s.data.use_shadow = False
    s.rotation_euler = [math.radians(a) for a in rot]
for c in ("rigs", "smurf"):
    bpy.data.collections[c].hide_render = True
bpy.data.collections["assets"].hide_render = False

cam = OB.new("sheet", bpy.data.cameras.new("sheet"))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.lens = 35
cam.data.clip_end = 5000
tmp = tempfile.mkdtemp(prefix="zombies_props_")

roots = sorted((o for o in OB if o.name.endswith("_import")), key=lambda o: o.name)
for k, root in enumerate(roots):
    root.location = (k * 3000, 0, 0)
bpy.context.view_layer.update()


def shot(tag, pos, tgt):
    cam.location = pos
    cam.rotation_euler = (Vector(tgt) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    path = os.path.join(tmp, tag + ".png")
    r.filepath = path
    bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(path)
    px = np.empty(CW * CH * 4, np.float32)
    im.pixels.foreach_get(px)
    bpy.data.images.remove(im)
    return px.reshape(CH, CW, 4)


cells = []
for k, root in enumerate(roots):
    name = root.name[:-7]
    meshes = [o for o in OB if o.get("asset") == name and o.type == "MESH" and not o.name.startswith("Icosphere")]
    if not meshes:
        continue
    pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
    lo = Vector(min(p[i] for p in pts) for i in range(3))
    hi = Vector(max(p[i] for p in pts) for i in range(3))
    c = (lo + hi) / 2
    size = hi - lo
    d = max(size) * 1.7
    print(f"## {k} {name}: size {size.x:.2f} {size.y:.2f} {size.z:.2f} centre {c.x - k * 3000:.2f} {c.y:.2f} {c.z:.2f}", flush=True)
    if len(meshes) > 1:
        for o in meshes:
            q = [o.matrix_world @ Vector(cc) for cc in o.bound_box]
            l2 = Vector(min(p[i] for p in q) for i in range(3))
            h2 = Vector(max(p[i] for p in q) for i in range(3))
            print(f"     {o.name[:44]:44} {len(o.data.polygons):5}p c {((l2.x + h2.x) / 2 - k * 3000):7.2f} {(l2.y + h2.y) / 2:7.2f} {(l2.z + h2.z) / 2:7.2f} s {h2.x - l2.x:6.2f} {h2.y - l2.y:6.2f} {h2.z - l2.z:6.2f}", flush=True)
    cells.append(shot(name + "a", c + Vector((0, -d, 0)), c))
    cells.append(shot(name + "b", c + Vector((d * 0.6, -d * 0.6, d * 0.6)), c))

COLS = 10
while len(cells) % COLS:
    cells.append(np.zeros((CH, CW, 4), np.float32))
rows = [np.hstack(cells[i:i + COLS]) for i in range(0, len(cells), COLS)]
sheet = np.vstack(rows[::-1])
h, w = sheet.shape[:2]
img = bpy.data.images.new("props_out", w, h)
img.pixels.foreach_set(sheet.ravel())
img.filepath_raw = OUT
img.file_format = "PNG"
img.save()
print("sheet", OUT, w, h, flush=True)
sys.stdout.flush()
os._exit(0)
