# Review sheet at the real internal pixel size: every character from several angles, then the head-turn test on both hero candidates.
# Doesn't save the .blend. Writes blender/zombies/review/03-cast.png.
#   "$BLENDER" -b blender/zombies/zombies.blend -P src/zombies/blender/cast_sheet.py
import bpy, json, math, os, sys, tempfile, importlib
import numpy as np
from mathutils import Euler, Vector
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "thps", "blender"))
sys.path.insert(0, HERE)
import lib, poses_zombie, set_lib
from lib import BONES, SCALE
from poses_zombie import Z_STAND, Z_REACH, Z_WALK, TURN
from set_lib import WORK

OUT = os.path.join(WORK, "review", "03-cast.png")
NAMES = json.load(open(os.path.join(WORK, "cast_bones.json")))
OB = bpy.data.objects
sc = bpy.context.scene
W, H = 216, 300
r = sc.render
r.engine = "BLENDER_EEVEE"
r.resolution_x, r.resolution_y, r.resolution_percentage = W, H, 100
r.filter_size = 0.01
r.image_settings.file_format = "PNG"
sc.eevee.taa_render_samples = 1
sc.view_settings.view_transform = "Standard"
sc.view_settings.look = "None"
sc.world = sc.world or bpy.data.worlds.new("sheet")
sc.world.use_nodes = True
bg = sc.world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.05, 0.10, 0.09, 1)
bg.inputs[1].default_value = 1.0


def sun(name, energy, rot):
    s = bpy.data.objects.new(name, bpy.data.lights.new(name, "SUN"))
    sc.collection.objects.link(s)
    s.data.energy = energy
    s.data.use_shadow = False
    s.rotation_euler = [math.radians(a) for a in rot]


sun("sheet_sun", 3.0, (50, 10, -30))
sun("sheet_back", 2.0, (-55, 0, 20))
bpy.data.collections["assets"].hide_viewport = True

cam_data = bpy.data.cameras.new("sheet")
cam_data.lens = 35
cam_data.clip_end = 900
cam = bpy.data.objects.new("sheet", cam_data)
sc.collection.objects.link(cam)
sc.camera = cam
tmp = tempfile.mkdtemp(prefix="zombies_sheet_")


def rest_q(arm, bone, deg):
    rest = arm.data.bones[bone].matrix_local.to_quaternion()
    q = Euler([math.radians(a) for a in deg], "XYZ").to_quaternion()
    return rest.inverted() @ q @ rest


def pose_human(kind, name, pose):
    arm = OB[name + "_arm"]
    for alias, bone in NAMES[kind].items():
        if alias in ("hips", "footR", "toeR"):
            continue
        pb = arm.pose.bones[bone]
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = rest_q(arm, bone, pose.get(alias, (0, 0, 0)))


def pose_smurf(prefix, pose):
    arm = OB["Armature" if prefix == "P1" else "P2_arm"]
    for alias in ("spine", "head", "armR", "foreR", "armL", "foreL", "thighR", "shinR", "thighL", "shinL"):
        pb = arm.pose.bones[BONES[alias]]
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = rest_q(arm, BONES[alias], pose.get(alias, (0, 0, 0)))


def shot(tag, target, ang, dist, up=0.3, lens=35):
    bpy.context.view_layer.update()
    a = math.radians(ang)
    pos = Vector(target) + Vector((math.sin(a) * dist, -math.cos(a) * dist, up))
    cam.location = pos
    cam.rotation_euler = (Vector(target) - pos).to_track_quat("-Z", "Y").to_euler()
    cam_data.lens = lens
    path = os.path.join(tmp, tag + ".png")
    r.filepath = path
    bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(path)
    px = np.empty(W * H * 4, np.float32)
    im.pixels.foreach_get(px)
    bpy.data.images.remove(im)
    return px.reshape(H, W, 4)


SMURF_STAND = {"spine": (2, 0, 0), "armR": (0, -8, 0), "foreR": (5, 0, 0), "armL": (0, 8, 0), "foreL": (5, 0, 0)}
HIDE_WIG = "ZF_peruca"
rows = []

# Pardo and Berg. Both are set up first: they start on the same spot.
for name, x in (("P1", 0), ("P2", 40)):
    OB[name].location = (x, 0, 0)
    OB[name].scale = (SCALE,) * 3
    pose_smurf(name, SMURF_STAND)
for i, (name, x) in enumerate((("P1", 0), ("P2", 40))):
    # The rig's origin isn't at his feet: place him by his hips
    t = (x, 0, 0.62)
    rows.append(np.hstack([shot(f"{name}{k}", t, a, 2.6) for k, a in enumerate((-20, 40, 110, 180, 250, 0))]))

# Rigged zombies in their stand, reach and walk poses
for name, kind, x in (("ZP", "ZP", 80), ("ZC", "ZC", 120), ("ZF", "ZF", 160)):
    OB[name].location = (x, 0, 0)
    cells = []
    target = (x, 0, 0.95)
    for k, (a, pose) in enumerate(((-20, Z_STAND), (180, Z_STAND), (-50, Z_REACH), (90, Z_WALK[0]), (-20, Z_WALK[2]))):
        pose_human(kind, name, pose)
        cells.append(shot(f"{name}{k}", target, a, 3.0))
    pose_human(kind, name, Z_STAND)
    cells.append(shot(f"{name}face", (x, 0, 1.55), -15, 1.0, up=0.05))
    rows.append(np.hstack(cells))

# She loses the wig
x = 160
OB[HIDE_WIG].hide_render = True
pose_human("ZF", "ZF", Z_STAND)
OB["ZR"].location = (200, 0, 0)
OB["RAST"].location = (240, 0, 0)
OB["CAO"].location = (280, 0, 0)
cells = [shot("bald0", (x, 0, 1.45), -20, 1.3, up=0.05), shot("bald1", (x, 0, 1.45), 150, 1.3, up=0.05)]
OB[HIDE_WIG].hide_render = False
cells += [shot("zr", (200, 0, 0.95), -20, 3.0), shot("zrface", (200, 0, 1.5), -15, 1.0, up=0.05), shot("rast", (240, 0, 0.4), -20, 2.6), shot("cao", (280, 0, 0.4), -60, 2.4)]
rows.append(np.hstack(cells))

# Pardo's vest up close, then the head turn as the opening shot sees it, from behind and off to the side he turns towards.
pose_smurf("P1", SMURF_STAND)
rows.insert(1, np.hstack([shot(f"vest{k}", (0, -0.03, 0.62), a, 1.1, up=0.06) for k, a in enumerate((0, -35, 35, 180, 150, 210))]))
bpy.ops.mesh.primitive_plane_add(size=400, location=(100, 0, 0))
bpy.context.object.data.materials.append(lib.make_mat("sheet floor", "2a2a2e"))
for name, kind, x in (("ZP", "ZP", 80), ("ZC", "ZC", 120)):
    cells = []
    for k, pose in enumerate(TURN):
        pose_human(kind, name, pose)
        OB[name].location = (x, 0, -pose.get("drop", 0))
        cells.append(shot(f"{name}turn{k}", (x, 0.1, 0.72), 205, 1.5, up=0.12, lens=40))
    cells.append(shot(f"{name}side", (x, 0, 0.55), 120, 2.4, up=0.3))
    rows.append(np.hstack(cells))

# Image pixels run bottom-up, so the first row goes last to land on top
sheet = np.vstack(rows[::-1])
h, w = sheet.shape[:2]
img = bpy.data.images.new("sheet_out", w, h)
img.pixels.foreach_set(sheet.ravel())
img.filepath_raw = OUT
img.file_format = "PNG"
img.save()
print("sheet", OUT, w, h, flush=True)
os._exit(0)
