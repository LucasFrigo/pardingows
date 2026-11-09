# Review renders of the imported kit: every model alone, framed from a 3/4 front view (blender/pardao/review/gallery/<name>.png),
# plus a lineup of the characters next to the Pardo for scale (review/02-lineup.png). src/pardao/gallery_sheet.mjs labels and tiles them.
# A temporary camera, sun and world are removed afterwards, and every visibility flag is put back.
#   node src/thps/bl.mjs run src/pardao/blender/gallery.py
import bpy, json, math, os, sys
from mathutils import Vector, Euler
try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    HERE = os.path.join(os.environ.get("PARDAO_ROOT", r"E:\Projetos\pardingows"), "src", "pardao", "blender")
sys.path.insert(0, HERE)
import importlib, set_lib
importlib.reload(set_lib)
from set_lib import REVIEW

OUT = os.path.join(REVIEW, "gallery")
os.makedirs(OUT, exist_ok=True)
rep = json.load(open(os.path.join(REVIEW, "02-import.json"), encoding="utf8"))
sc = bpy.context.scene
OB = bpy.data.objects


def tree(root):
    return [root] + list(root.children_recursive)


def bbox(objs):
    mins, maxs = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for ob in objs:
        if ob.type != "MESH":
            continue
        for c in ob.bound_box:
            p = ob.matrix_world @ Vector(c)
            mins = Vector(map(min, mins, p))
            maxs = Vector(map(max, maxs, p))
    return mins, maxs


cam_data = bpy.data.cameras.new("review_cam")
cam_data.type = "ORTHO"
cam_data.clip_end = 2000
cam = OB.new("review_cam", cam_data)
sun_data = bpy.data.lights.new("review_sun", "SUN")
sun_data.energy = 3.0
sun = OB.new("review_sun", sun_data)
sun.rotation_euler = (math.radians(50), 0, math.radians(-35))
for o in (cam, sun):
    sc.collection.objects.link(o)
old_world, old_cam = sc.world, sc.camera
world = bpy.data.worlds.new("review_world")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.30, 0.32, 0.36, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
sc.world, sc.camera = world, cam
r = sc.render
old = (r.engine, r.resolution_x, r.resolution_y, r.resolution_percentage, r.filepath, r.film_transparent)
r.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in {e.identifier for e in r.bl_rna.properties["engine"].enum_items} else "BLENDER_EEVEE"
r.resolution_percentage = 100
r.film_transparent = False

# Everything that renders goes dark, then each subject is switched on alone
assets = bpy.data.collections["assets"]
assets.hide_render = False
saved = {o.name: o.hide_render for o in OB}
for o in OB:
    if o not in (cam, sun):
        o.hide_render = True


def shoot(objs, path, w, h, view=(68, 0, 28)):
    for o in objs:
        o.hide_render = False
    mins, maxs = bbox(objs)
    centre = (mins + maxs) / 2
    rot = Euler(tuple(math.radians(a) for a in view))
    cam.rotation_euler = rot
    # Fit the box's corners in camera space
    m = rot.to_matrix()
    inv = m.transposed()
    pts = [inv @ (Vector((x, y, z)) - centre) for x in (mins.x, maxs.x) for y in (mins.y, maxs.y) for z in (mins.z, maxs.z)]
    sx = max(abs(p.x) for p in pts) * 2
    sy = max(abs(p.y) for p in pts) * 2
    depth = max(abs(p.z) for p in pts)
    r.resolution_x, r.resolution_y = w, h
    cam_data.ortho_scale = max(sx, sy * w / h) * 1.08
    cam.location = centre + m @ Vector((0, 0, depth + 20))
    r.filepath = path
    bpy.ops.render.render(write_still=True)
    for o in objs:
        o.hide_render = True


for name in rep:
    shoot(tree(OB[name + "_import"]), os.path.join(OUT, name + ".png"), 480, 480)
    print("tile", name)

# Lineup: the Pardo and the three hobo bases and the donkey side by side, straight on, at true scale
P1 = OB["P1"]
p1_loc = P1.location.copy()
line = ["mendigo_capuz", "thug_lp", "homem_lp", "jumento"]
saved_loc = {n: OB[n + "_import"].location.copy() for n in line}
x = 0.0
P1.location = (x, 0, 0.04)
objs = tree(P1)
x += 1.4
for n in line:
    root = OB[n + "_import"]
    root.location = (0, 0, 0)
    bpy.context.view_layer.update()
    mins, maxs = bbox(tree(root))
    root.location = (x - mins.x, -(mins.y + maxs.y) / 2, -mins.z)
    x += (maxs.x - mins.x) + 0.5
    objs += tree(root)
bpy.context.view_layer.update()
shoot(objs, os.path.join(REVIEW, "02-lineup.png"), 1600, 520, view=(84, 0, 0))
P1.location = p1_loc
for n, loc in saved_loc.items():
    OB[n + "_import"].location = loc

for o in OB:
    if o.name in saved:
        o.hide_render = saved[o.name]
assets.hide_render = True
r.engine, r.resolution_x, r.resolution_y, r.resolution_percentage, r.filepath, r.film_transparent = old
sc.world, sc.camera = old_world, old_cam
for o in (cam, sun):
    bpy.data.objects.remove(o, do_unlink=True)
bpy.data.cameras.remove(cam_data)
bpy.data.lights.remove(sun_data)
bpy.data.worlds.remove(world)
set_lib.save()
print("done")
