# Look check: a still of each location with the cast standing in, and the time a real frame takes. Doesn't save the file.
#   "$BLENDER" -b blender/zombies/zombies.blend -P src/zombies/blender/set_stills.py -- [out_dir]
# Writes one PNG per location. Node runs them through the PS1 filter afterwards (src/zombies/stills.mjs).
import bpy, json, math, os, sys, time
from mathutils import Euler, Vector
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "thps", "blender"))
sys.path.insert(0, HERE)
import lib, poses_zombie, set_lib
from lib import BONES, SCALE
from poses_zombie import Z_REACH, Z_STAND, Z_WALK, TURN
from set_lib import CORRIDOR, DUNGEON, HALL, STREET, WORK

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = args[0] if args else os.path.join(WORK, "frames", "stills")
os.makedirs(OUT, exist_ok=True)
NAMES = json.load(open(os.path.join(WORK, "cast_bones.json")))
OB = bpy.data.objects
sc = bpy.context.scene
cam = OB.new("still", bpy.data.cameras.new("still"))
sc.collection.objects.link(cam)
cam.data.clip_start = 0.05
cam.data.clip_end = 900
sc.camera = cam


def rest_q(arm, bone, deg):
    rest = arm.data.bones[bone].matrix_local.to_quaternion()
    q = Euler([math.radians(a) for a in deg], "XYZ").to_quaternion()
    return rest.inverted() @ q @ rest


def human(name, pose, loc, rz=0.0):
    arm = OB[name + "_arm"]
    for alias, bone in NAMES[name].items():
        if alias in ("hips", "footR", "toeR"):
            continue
        pb = arm.pose.bones[bone]
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = rest_q(arm, bone, pose.get(alias, (0, 0, 0)))
    OB[name].location = (loc[0], loc[1], loc[2] - pose.get("drop", 0))
    OB[name].rotation_euler = (0, 0, math.radians(rz))


def smurf(prefix, loc, rz=0.0, rot=None):
    arm = OB["Armature" if prefix == "P1" else "P2_arm"]
    pose = {"spine": (2, 0, 0), "armR": (0, -8, 0), "foreR": (5, 0, 0), "armL": (0, 8, 0), "foreL": (5, 0, 0)}
    for alias in ("spine", "head", "armR", "foreR", "armL", "foreL", "thighR", "shinR", "thighL", "shinL"):
        pb = arm.pose.bones[BONES[alias]]
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = rest_q(arm, BONES[alias], pose.get(alias, (0, 0, 0)))
    OB[prefix].location = loc
    OB[prefix].rotation_euler = rot or (0, 0, math.radians(rz))
    OB[prefix].scale = (SCALE,) * 3


def at(o, x, y, z=0.0):
    return (o[0] + x, o[1] + y, o[2] + z)


def shot(tag, pos, tgt, lens):
    cam.location = pos
    cam.rotation_euler = (Vector(tgt) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = lens
    bpy.context.view_layer.update()
    sc.render.filepath = os.path.join(OUT, tag + ".png")
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"RENDER {tag}: {time.time() - t0:.2f}s at {sc.render.resolution_x}x{sc.render.resolution_y}, {sc.eevee.taa_render_samples} samples", flush=True)


# Corridor: the opening shot, the moment he has turned. He kneels facing +Y, with the camera behind him at -Y.
human("ZP", TURN[-1], at(CORRIDOR, 0, 0.1), rz=180)
smurf("P2", at(CORRIDOR, 0.75, 0.8, 0.28), rot=(math.radians(-90), 0, math.radians(80)))
smurf("P1", (500, 0, 0))
shot("1-corredor", at(CORRIDOR, 0.8, -1.7, 1.12), at(CORRIDOR, 0.04, 0.3, 0.74), 30)

# Street
OB["ZP"].location = (900, 0, 0)
OB["P2"].location = (900, 40, 0)
smurf("P1", at(STREET, 1.7, -4.2), rz=-30)
human("ZF", Z_WALK[0], (900, 80, 0))
human("ZC", Z_WALK[1], at(STREET, -3.5, 1.2), rz=20)
OB["ZR"].location = at(STREET, 3.8, 1.8)
OB["ZR"].rotation_euler = (0, 0, math.radians(-25))
OB["CAO"].location = at(STREET, -1.6, -1.0)
shot("2-rua", at(STREET, 6.0, -13.0, 7.5), at(STREET, 0, 1, 0.8), 30)

# Hall
OB["ZR"].location = at(HALL, 1.5, 0.2)
OB["ZR"].rotation_euler = (0, 0, 0)
human("ZC", Z_REACH, at(HALL, -1.4, -0.1), rz=0)
OB["CAO"].location = (900, 120, 0)
smurf("P1", at(HALL, 0.1, -0.9), rz=180)
shot("3-hall", at(HALL, 0.9, -6.5, 1.9), at(HALL, 0, 0, 1.35), 30)

# Dungeon: behind the bars
OB["ZR"].location = (900, 160, 0)
OB["ZC"].location = (900, 200, 0)
human("ZP", Z_STAND, at(DUNGEON, 0.25, 0.75), rz=0)
OB["P1"].location = (500, 0, 0)
shot("4-masmorra", at(DUNGEON, 0.6, -2.6, 1.35), at(DUNGEON, 0, 1, 1.0), 26)
print("=== STILLS DONE", flush=True)
sys.stdout.flush()
os._exit(0)
