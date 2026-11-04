# Review sheet at the real internal resolution: each character from four angles in a stand pose, then running.
# Uses a temporary camera and puts everything back. Writes blender/missao/review/01-personagens.png.
#   node src/thps/bl.mjs run src/missao/blender/cast_sheet.py
import bpy, json, math, os, sys, tempfile, importlib
import numpy as np
from mathutils import Euler, Vector
sys.path.insert(0, r"C:\Users\lukeg\Projetos\pardingows\src\thps\blender")
sys.path.insert(0, r"C:\Users\lukeg\Projetos\pardingows\src\missao\blender")
import lib, poses_run
importlib.reload(lib); importlib.reload(poses_run)
from lib import BONES, SCALE
from poses_run import STAND, RUN, H_STAND, H_RUN, H_REACH

WORK = r"C:\Users\lukeg\Projetos\pardingows\blender\missao"
OUT = os.path.join(WORK, "review", "01-personagens.png")
NAMES = json.load(open(os.path.join(WORK, "cast_bones.json")))
OB = bpy.data.objects
sc = bpy.context.scene
W, H = 270, 240
prev_cam, prev_path = sc.camera, sc.render.filepath
r = sc.render
r.engine = "BLENDER_EEVEE"
r.resolution_x, r.resolution_y, r.resolution_percentage = W, H, 100
r.filter_size = 0.01
sc.eevee.taa_render_samples = 1
sc.view_settings.view_transform = "Standard"
sc.view_settings.look = "None"
if not sc.world:
    sc.world = bpy.data.worlds.new("sheet")
sc.world.use_nodes = True
sc.world.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.16, 0.13, 1)  # dark green, so no costume melts into it
sc.world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
sun = OB.get("sheet_sun") or bpy.data.objects.new("sheet_sun", bpy.data.lights.new("sheet_sun", "SUN"))
if sun.name not in sc.collection.objects:
    sc.collection.objects.link(sun)
sun.data.energy = 3.0
sun.data.use_shadow = False
sun.rotation_euler = [math.radians(a) for a in (50, 10, -30)]
back = OB.get("sheet_back") or bpy.data.objects.new("sheet_back", bpy.data.lights.new("sheet_back", "SUN"))
if back.name not in sc.collection.objects:
    sc.collection.objects.link(back)
back.data.energy = 2.0
back.data.use_shadow = False
back.rotation_euler = [math.radians(a) for a in (-55, 0, 20)]

cam_data = bpy.data.cameras.new("sheet")
cam_data.lens = 35
cam_data.clip_end = 900
cam = bpy.data.objects.new("sheet", cam_data)
sc.collection.objects.link(cam)
sc.camera = cam


def rest_q(arm, bone_name, deg):
    rest = arm.data.bones[bone_name].matrix_local.to_quaternion()
    q = Euler([math.radians(a) for a in deg], "XYZ").to_quaternion()
    return rest.inverted() @ q @ rest


def pose_smurf(prefix, pose):
    arm = OB["Armature" if prefix == "P1" else "P2_arm"]
    dx, dy, dz, rx, ry, rz = pose.get("body", (0,) * 6)
    OB[prefix + "_body"].location = (dx, dy, dz)
    OB[prefix + "_body"].rotation_euler = [math.radians(a) for a in (rx, ry, rz)]
    for alias in ("spine", "head", "armR", "foreR", "armL", "foreL", "thighR", "shinR", "thighL", "shinL"):
        pb = arm.pose.bones[BONES[alias]]
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = rest_q(arm, BONES[alias], pose.get(alias, (0, 0, 0)))


def pose_human(kind, name, pose):
    arm = OB[name + "_arm"]
    for alias, bone in NAMES[kind].items():
        if alias in ("hips", "footR", "toeR"):
            continue
        pb = arm.pose.bones[bone]
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = rest_q(arm, bone, pose.get(alias, (0, 0, 0)))


SPOTS = [("P1", "smurf", (0, 0, 0), 0.72, 3.0), ("P2", "smurf", (60, 0, 0), 0.72, 3.0), ("PY1", "PY", (120, 0, 0), 0.95, 3.6),
         ("DG1", "DG", (180, 0, 0), 0.92, 3.6), ("DH1", "DH", (240, 0, 0), 0.92, 3.6)]
saved = {s[0]: OB[s[0]].location.copy() for s in SPOTS}
for name, kind, loc, up, dist in SPOTS:
    OB[name].location = loc
    if kind == "smurf":
        OB[name].scale = (SCALE, SCALE, SCALE)
morto_loc = OB["MORTO"].location.copy()
OB["MORTO"].location = (300, 0, 0)

tmp = tempfile.mkdtemp(prefix="missao_sheet_")


def shot(tag):
    bpy.context.view_layer.update()
    path = os.path.join(tmp, tag + ".png")
    r.filepath = path
    bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(path)
    px = np.empty(W * H * 4, np.float32)
    im.pixels.foreach_get(px)
    bpy.data.images.remove(im)
    return px.reshape(H, W, 4)


rows = []
for name, kind, loc, up, dist in SPOTS:
    target = Vector(loc) + Vector((0, 0, up))
    cells = []
    for i, (ang, pose_h, pose_s) in enumerate(((-22, H_STAND, STAND), (155, H_STAND, STAND), (-60, H_REACH, RUN[0]), (180, H_RUN[0], RUN[0]), (70, H_RUN[1], RUN[1]))):
        if kind == "smurf":
            pose_smurf(name, pose_s)
        else:
            pose_human(kind, name, pose_h)
        a = math.radians(ang)
        pos = target + Vector((math.sin(a) * dist, -math.cos(a) * dist, 0.3))
        cam.location = pos
        cam.rotation_euler = (target - pos).to_track_quat("-Z", "Y").to_euler()
        cells.append(shot(f"{name}_{i}"))
    rows.append(np.hstack(cells))
cells = []
target = Vector((300, 0, 0.2))
for i, ang in enumerate((-30, 60, 150, 210, 300)):
    a = math.radians(ang)
    pos = target + Vector((math.sin(a) * 3.0, -math.cos(a) * 3.0, 1.2))
    cam.location = pos
    cam.rotation_euler = (target - pos).to_track_quat("-Z", "Y").to_euler()
    cells.append(shot(f"morto_{i}"))
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
OB["MORTO"].location = morto_loc
sc.camera, r.filepath = prev_cam, prev_path
bpy.data.objects.remove(cam, do_unlink=True)
bpy.data.cameras.remove(cam_data)
print("sheet", OUT, w, h)
