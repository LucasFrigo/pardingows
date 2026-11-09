# The head turn at the real 270x480 framing, with Berg on the floor, plus her wig on and off up close. Doesn't save the .blend.
# Writes blender/zombies/review/03-head-turn.png.
#   "$BLENDER" -b blender/zombies/zombies.blend -P src/zombies/blender/turn_test.py
import bpy, json, math, os, sys, tempfile
import numpy as np
from mathutils import Euler, Vector
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "thps", "blender"))
sys.path.insert(0, HERE)
import lib, poses_zombie, set_lib
from lib import BONES, SCALE
from poses_zombie import ZF_STAND, TURN
from set_lib import WORK

OUT = os.path.join(WORK, "review", "03-head-turn.png")
NAMES = json.load(open(os.path.join(WORK, "cast_bones.json")))
OB = bpy.data.objects
sc = bpy.context.scene
W, H = 270, 480
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
sc.world.node_tree.nodes["Background"].inputs[0].default_value = (0.02, 0.03, 0.03, 1)
sc.world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
for name, energy, rot in (("sheet_sun", 2.4, (50, 10, 150)), ("sheet_fill", 0.9, (60, 0, -20))):
    s = OB.new(name, bpy.data.lights.new(name, "SUN"))
    sc.collection.objects.link(s)
    s.data.energy = energy
    s.data.use_shadow = False
    s.rotation_euler = [math.radians(a) for a in rot]
bpy.data.collections["assets"].hide_viewport = True
bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0))
bpy.context.object.data.materials.append(lib.make_mat("sheet floor", "3a3028"))
OB["P1"].location = (300, 300, 0)

cam_data = bpy.data.cameras.new("t")
cam_data.clip_end = 900
cam = OB.new("t", cam_data)
sc.collection.objects.link(cam)
sc.camera = cam
tmp = tempfile.mkdtemp(prefix="zombies_turn_")


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


def shot(tag, pos, tgt, lens):
    bpy.context.view_layer.update()
    cam.location = pos
    cam.rotation_euler = (Vector(tgt) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
    cam_data.lens = lens
    path = os.path.join(tmp, tag + ".png")
    r.filepath = path
    bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(path)
    px = np.empty(W * H * 4, np.float32)
    im.pixels.foreach_get(px)
    bpy.data.images.remove(im)
    return px.reshape(H, W, 4)


# Berg on his back in front of the zombie
OB["P2"].location = (0.0, -0.45, 0.28)
OB["P2"].rotation_euler = (math.radians(-90), 0, math.radians(165))
OB["P2"].scale = (SCALE,) * 3

row = []
for k, pose in enumerate(TURN):
    pose_human("ZP", "ZP", pose)
    OB["ZP"].location = (0, 0, -pose.get("drop", 0))
    row.append(shot(f"t{k}", (-1.0, 2.4, 1.0), (0, -0.05, 0.72), 62))

OB["ZP"].location = (300, 0, 0)
OB["P2"].location = (300, 40, 0)
OB["ZF"].location = (0, 0, 0)
pose_human("ZF", "ZF", ZF_STAND)
row2 = [shot("w0", (-0.25, -0.95, 1.6), (0, -0.05, 1.45), 42), shot("w1", (0.85, -0.5, 1.6), (0, -0.05, 1.45), 42), shot("w2", (0.3, 0.95, 1.6), (0, -0.05, 1.45), 42)]
OB["ZF_peruca"].hide_render = True
row2 += [shot("w3", (-0.25, -0.95, 1.6), (0, -0.05, 1.45), 42), shot("w4", (0.3, 0.95, 1.6), (0, -0.05, 1.45), 42)]

sheet = np.vstack([np.hstack(row2), np.hstack(row)])
h, w = sheet.shape[:2]
img = bpy.data.images.new("turn_out", w, h)
img.pixels.foreach_set(sheet.ravel())
img.filepath_raw = OUT
img.file_format = "PNG"
img.save()
print("sheet", OUT, w, h, flush=True)
sys.stdout.flush()
os._exit(0)
