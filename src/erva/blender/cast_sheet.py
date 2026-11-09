# Step 3 review renders: turnarounds (front, 3/4, side, back) of every cast member, and pose strips of Pardão and the cobra.
# Tiles go to blender/erva/review/cast/, then src/erva/cast_sheet.mjs labels and tiles them into 03-*.png.
# The temporary camera, floor and world are removed afterwards, and everyone is stood back up.
#   node src/thps/bl.mjs run src/erva/blender/cast_sheet.py
import importlib
import json
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
import set_lib, hose, snake, poses_toon as PT  # noqa: E402
for mod in (set_lib, hose, snake, PT):
    importlib.reload(mod)
from set_lib import WORK, REVIEW, cel  # noqa: E402

OUT = os.path.join(REVIEW, "cast")
os.makedirs(OUT, exist_ok=True)
CAST = json.load(open(os.path.join(WORK, "cast.json"), encoding="utf8"))
G, Y0, SP, ORDER = CAST["pardo_ground_body_z"], CAST["lineup_y"], CAST["spacing"], CAST["order"]
RIGS = [p for p in ORDER if p != "COBRA"]
sc = bpy.context.scene
OB = bpy.data.objects
COBRA_X = len(RIGS) * SP


def members(prefix):
    return [o for o in OB if o.name == prefix or o.name.startswith(prefix + "_")]


def bbox(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    mins, maxs = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for ob in objs:
        if ob.type not in ("MESH", "CURVE") or ob.hide_viewport:
            continue
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        for v in me.vertices:
            p = ev.matrix_world @ v.co
            mins = Vector(map(min, mins, p))
            maxs = Vector(map(max, maxs, p))
        ev.to_mesh_clear()
    return mins, maxs


cam_data = bpy.data.cameras.new("review_cam")
cam_data.type = "ORTHO"
cam_data.clip_end = 500
cam = OB.new("review_cam", cam_data)
floor_me = bpy.data.meshes.new("review_floor")
floor_me.from_pydata([(-80, -120, 0), (80, -120, 0), (80, 60, 0), (-80, 60, 0)], [], [(0, 1, 2, 3)])
floor = OB.new("review_floor", floor_me)
floor_me.materials.append(cel("review floor", 0.62, shade=0.6))
temp = (cam, floor)
for o in temp:
    sc.collection.objects.link(o)
old_cam = sc.camera
sc.camera = cam
r = sc.render
old = (r.resolution_x, r.resolution_y, r.resolution_percentage, r.filepath, r.film_transparent)
r.resolution_percentage = 100
sun = OB["key_sun"]
old_sun = tuple(sun.rotation_euler)

saved = {o.name: o.hide_render for o in OB}
for o in OB:
    if o not in temp and o.type != "LIGHT":
        o.hide_render = True


def shoot(objs, path, yaw, centre, scale, w=360, h=480, pitch=84):
    # posing switches gloves on for every rig, so everyone but the subject is hidden again here
    keep = set(objs) | set(temp)
    for o in OB:
        if o.type != "LIGHT" and o not in keep:
            o.hide_render = True
    for o in objs:
        o.hide_render = o.hide_viewport
    ghost = any(o.name.startswith("ALMA") for o in objs)
    floor.hide_render = ghost
    r.film_transparent = ghost
    rot = Euler((math.radians(pitch), 0, math.radians(yaw)))
    cam.rotation_euler = rot
    cam.location = Vector(centre) + rot.to_matrix() @ Vector((0, 0, 40))
    cam_data.ortho_scale = scale
    # the key light turns with the camera, so every view is lit from the front-left
    sun.rotation_euler = (math.radians(50), 0, math.radians(yaw - 35))
    r.resolution_x, r.resolution_y = w, h
    r.filepath = path
    bpy.ops.render.render(write_still=True)
    for o in objs:
        o.hide_render = True


def frame(objs):
    bpy.context.view_layer.update()
    mins, maxs = bbox(objs)
    c = (mins + maxs) / 2
    size = max(maxs.z - mins.z, (maxs.x - mins.x) * 0.75, (maxs.y - mins.y) * 0.75) * 1.2
    return c, size


def stand_all():
    for p in RIGS:
        PT.pose_pardo(p, {**PT.STAND, "spine": (14, 0, 0), "head": (-10, 0, 0)} if p == "VOVO" else PT.STAND, G)
    bpy.context.view_layer.update()
    for p in RIGS:
        hose.update(p)
    snake.pose(**snake.stand((COBRA_X, Y0, 0), (0, -1, 0)))


stand_all()
listing = {"turn": [], "pardo": [], "cobra": []}
VIEWS = (("frente", 0), ("3/4", 35), ("lado", 90), ("costas", 180))
for name in ORDER:
    objs = members(name)
    c, size = frame(objs)
    row = []
    for label, yaw in VIEWS:
        path = os.path.join(OUT, f"turn_{name}_{yaw}.png")
        shoot(objs, path, yaw, c, size)
        row.append([label, os.path.basename(path)])
    listing["turn"].append([name, row])
    print("turnaround", name)
    set_lib.redraw()

# Pardão's pose strip, at one fixed scale so the poses compare
P1 = members("P1")
base = OB["P1"].location
for pname in PT.STRIP:
    PT.pose_pardo("P1", PT.get(pname), G)
    bpy.context.view_layer.update()
    hose.update("P1")
    path = os.path.join(OUT, f"pose_{pname}.png")
    shoot(P1, path, 28, (base.x, base.y, 0.95), 2.7)
    listing["pardo"].append([pname, os.path.basename(path)])
print("pardo strip done")

cob = members("COBRA")
for pname in ("stand", "sneak", "laugh", "limp", "giant"):
    args = snake.POSES[pname]((COBRA_X, Y0, 0), (0, -1, 0), **({"held": (COBRA_X, Y0, 1.0)} if pname == "limp" else {}))
    snake.pose(**args)
    bpy.context.view_layer.update()
    path = os.path.join(OUT, f"cobra_{pname}.png")
    if pname == "giant":
        shoot(cob, path, 28, (COBRA_X, Y0, 2.4), 6.5)
    else:
        shoot(cob, path, 28, (COBRA_X, Y0, 0.85), 2.7)
    listing["cobra"].append([pname, os.path.basename(path)])
print("cobra strip done")

stand_all()
for o in OB:
    if o.name in saved:
        o.hide_render = saved[o.name]
sun.rotation_euler = old_sun
r.resolution_x, r.resolution_y, r.resolution_percentage, r.filepath, r.film_transparent = old
sc.camera = old_cam
for o in temp:
    bpy.data.objects.remove(o, do_unlink=True)
bpy.data.cameras.remove(cam_data)
bpy.data.meshes.remove(floor_me)
json.dump(listing, open(os.path.join(OUT, "listing.json"), "w", encoding="utf8"), indent=1)
set_lib.save()
print("done")
