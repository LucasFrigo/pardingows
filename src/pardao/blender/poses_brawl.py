# Pose library for PARDÃO 2000. Degrees in each rig's rest axes (rest_q). Everyone faces -Y, and "R" is always the +X side.
#
# Pardo (P_*): his arms and legs hang in the rest pose. -X swings a hanging limb forward, +X on a shin bends the knee,
#   +X on spine or head bows forward. For the R arm -Y raises it out to the side, for the L arm +Y does.
#   "body": (dx, dy, dz, rx, ry, rz) moves Pn_body, in smurf units (x 0.23 for metres), on top of the ground offset.
# Mildingows (H_*): T-pose rest. +Y drops the R arm, -Y drops the L arm. -Z swings the R arm forward, +Z the L arm.
#   Legs as the Pardo's. "drop" lowers the root, in metres.
import math
import bpy
from mathutils import Euler

PARDO_BONES = {
    "spine": "Bone.016", "head": "Bone.001",
    "armR": "Bone.002", "foreR": "Bone.003", "handR": "Bone.004", "armL": "Bone.009", "foreL": "Bone.010", "handL": "Bone.011",
    "thighR": "Bone.005", "shinR": "Bone.006", "footR": "Bone.007", "thighL": "Bone.012", "shinL": "Bone.013", "footL": "Bone.014",
}
H_BONES = {"hips": "Hips", "spine": "Spine1", "spine0": "Spine", "neck": "Neck", "head": "Head",
           "armR": "LeftArm", "foreR": "LeftForeArm", "handR": "LeftHand", "armL": "RightArm", "foreL": "RightForeArm", "handL": "RightHand",
           "thighR": "LeftUpLeg", "shinR": "LeftLeg", "footR": "LeftFoot", "thighL": "RightUpLeg", "shinL": "RightLeg", "footL": "RightFoot"}

# ---------------------------------------------------------------- Pardo
P_STAND = {"spine": (2, 0, 0), "armR": (0, -8, 0), "foreR": (5, 0, 0), "armL": (0, 8, 0), "foreL": (5, 0, 0)}

# Fighting stance, bounced between A and B on the beat. Lead fist out, rear fist by the chin.
P_GUARD_A = {"body": (0, 0, 0, 0, 0, -18), "spine": (10, 0, 0), "head": (-6, 0, 14),
             "armR": (-40, -18, 0), "foreR": (-115, 0, 0), "armL": (-70, 14, 0), "foreL": (-80, 0, 0),
             "thighR": (-6, -10, 0), "shinR": (22, 0, 0), "thighL": (-28, 8, 0), "shinL": (22, 0, 0)}
P_GUARD_B = {**P_GUARD_A, "body": (0, 0, -0.18, 0, 0, -18), "thighR": (-14, -10, 0), "shinR": (36, 0, 0), "thighL": (-38, 8, 0), "shinL": (38, 0, 0)}

P_JAB = {"body": (0, -0.2, -0.05, 0, 0, 8), "spine": (16, 0, -10), "head": (-10, 0, 6),
         "armR": (-92, -4, 0), "foreR": (-2, 0, 0), "armL": (-50, 16, 0), "foreL": (-115, 0, 0),
         "thighR": (-34, -6, 0), "shinR": (30, 0, 0), "thighL": (18, 6, 0), "shinL": (14, 0, 0)}
P_UPPER = {"body": (0, -0.1, 0.15, 0, 0, 10), "spine": (-12, 0, -14), "head": (-18, 0, 0),
           "armR": (-165, -12, 0), "foreR": (-30, 0, 0), "armL": (-40, 18, 0), "foreL": (-110, 0, 0),
           "thighR": (-10, -6, 0), "shinR": (10, 0, 0), "thighL": (8, 6, 0), "shinL": (8, 0, 0)}
P_KICK = {"body": (0, 0.15, 0, -8, 0, 0), "spine": (-16, 0, 0), "head": (6, 0, 0),
          "armR": (-28, -38, 0), "foreR": (-60, 0, 0), "armL": (-28, 38, 0), "foreL": (-60, 0, 0),
          "thighR": (-96, 0, 0), "shinR": (0, 0, 0), "thighL": (6, 4, 0), "shinL": (10, 0, 0)}
P_FLYKICK = {"body": (0, 0, 1.4, -18, 0, 0), "spine": (-12, 0, 0), "head": (8, 0, 0),
             "armR": (40, -40, 0), "foreR": (-20, 0, 0), "armL": (40, 40, 0), "foreL": (-20, 0, 0),
             "thighR": (-92, 0, 0), "shinR": (0, 0, 0), "thighL": (-40, 0, 0), "shinL": (115, 0, 0)}
P_HIT = {"body": (0, 0.25, 0, -14, 0, 6), "spine": (-24, 0, 6), "head": (-24, 0, 0),
         "armR": (24, -52, 0), "foreR": (-30, 0, 0), "armL": (24, 52, 0), "foreL": (-30, 0, 0),
         "thighR": (-22, 0, 0), "shinR": (24, 0, 0), "thighL": (10, 0, 0), "shinL": (10, 0, 0)}
P_DOWN = {"body": (0, 0, 0.45, -86, 0, 0), "spine": (-6, 0, 0), "head": (-10, 0, 20),
          "armR": (-150, -40, 0), "foreR": (0, 0, 0), "armL": (-150, 40, 0), "foreL": (0, 0, 0),
          "thighR": (-6, -12, 0), "shinR": (6, 0, 0), "thighL": (-6, 12, 0), "shinL": (6, 0, 0)}
# Hands up against the wall. His arms are short and his ears big, so the hands go up and out in a V to stay readable
P_HANDSUP = {"spine": (-4, 0, 0), "head": (-6, 0, 0), "armR": (0, -95, 0), "foreR": (0, -40, 0), "armL": (0, 95, 0), "foreL": (0, 40, 0)}
P_STRETCH_UP = {"body": (0, 0, 0.12, 0, 0, 0), "spine": (-10, 0, 0), "head": (-16, 0, 0),
                "armR": (0, -90, 0), "foreR": (0, 0, 0), "armL": (0, 90, 0), "foreL": (0, 0, 0)}
P_STRETCH_SIDE = {"spine": (0, -22, 0), "head": (0, -8, 0), "armR": (-172, -10, 0), "foreR": (0, 0, 0),
                  "armL": (0, 30, 0), "foreL": (-70, 0, 0), "thighR": (0, -10, 0), "thighL": (0, 10, 0)}
P_LUNGE = {"body": (0, -0.3, -0.45, 0, 0, 0), "spine": (16, 0, 0), "head": (-14, 0, 0),
           "armR": (-30, -10, 0), "foreR": (-30, 0, 0), "armL": (-30, 10, 0), "foreL": (-30, 0, 0),
           "thighR": (-72, 0, 0), "shinR": (74, 0, 0), "thighL": (34, 0, 0), "shinL": (12, 0, 0)}
# Passinho: two mirrored steps swapped on each half beat
P_DANCE_A = {"body": (0, 0, -0.06, 0, 0, 16), "spine": (6, 0, -10), "head": (-4, 0, 6),
             "armR": (-60, -32, 0), "foreR": (-90, 0, 0), "armL": (-18, 30, 0), "foreL": (-40, 0, 0),
             "thighR": (-38, -10, 0), "shinR": (52, 0, 0), "thighL": (4, 4, 0), "shinL": (6, 0, 0)}
P_DANCE_B = {"body": (0, 0, -0.06, 0, 0, -16), "spine": (6, 0, 10), "head": (-4, 0, -6),
             "armR": (-18, -30, 0), "foreR": (-40, 0, 0), "armL": (-60, 32, 0), "foreL": (-90, 0, 0),
             "thighR": (4, -4, 0), "shinR": (6, 0, 0), "thighL": (-38, 10, 0), "shinL": (52, 0, 0)}
P_SMOKE = {"spine": (4, 0, 0), "head": (-6, 0, -4), "armR": (-30, -2, 0), "foreR": (-145, 0, 0), "armL": (0, 10, 0), "foreL": (5, 0, 0)}
P_POINT = {"spine": (0, 0, 0), "head": (-4, 0, 0), "armR": (-92, -12, 0), "foreR": (-4, 0, 0), "armL": (0, 10, 0), "foreL": (5, 0, 0)}
P_VICTORY = {"body": (0, 0, 0.1, 0, 0, 0), "spine": (-8, 0, 0), "head": (-12, 0, 0),
             "armR": (-150, -48, 0), "foreR": (-6, 0, 0), "armL": (0, 18, 0), "foreL": (-90, 0, 0)}

PARDO_STRIP = ["P_GUARD_A", "P_JAB", "P_UPPER", "P_KICK", "P_FLYKICK", "P_HIT", "P_HANDSUP", "P_STRETCH_UP", "P_LUNGE", "P_DANCE_A", "P_DANCE_B", "P_SMOKE", "P_VICTORY", "P_DOWN"]

# ---------------------------------------------------------------- Mildingows
H_STAND = {"spine": (12, 0, 0), "neck": (6, 0, 0), "head": (2, 0, 0),
           "armR": (0, 72, -8), "foreR": (0, 8, -12), "armL": (0, -72, 8), "foreL": (0, -8, 12)}
_ARMS = {"foreR": (0, 8, -14), "foreL": (0, -8, 14), "spine": (12, 0, 0), "neck": (6, 0, 0)}
H_WALK = [
    {**_ARMS, "armR": (0, 70, 22), "armL": (0, -70, 22), "thighR": (-26, 0, 0), "shinR": (8, 0, 0), "thighL": (18, 0, 0), "shinL": (22, 0, 0)},
    {**_ARMS, "armR": (0, 72, 4), "armL": (0, -72, 4), "thighR": (-6, 0, 0), "shinR": (6, 0, 0), "thighL": (-6, 0, 0), "shinL": (42, 0, 0), "drop": -0.02},
    {**_ARMS, "armR": (0, 70, -22), "armL": (0, -70, -22), "thighL": (-26, 0, 0), "shinL": (8, 0, 0), "thighR": (18, 0, 0), "shinR": (22, 0, 0)},
    {**_ARMS, "armR": (0, 72, -4), "armL": (0, -72, -4), "thighL": (-6, 0, 0), "shinL": (6, 0, 0), "thighR": (-6, 0, 0), "shinR": (42, 0, 0), "drop": -0.02},
]
H_GRAB = {"spine": (20, 0, 0), "neck": (0, 0, 0), "head": (-10, 0, 0),
          "armR": (0, 14, -70), "foreR": (0, 0, -20), "armL": (0, -14, 70), "foreL": (0, 0, 20),
          "thighR": (-18, 0, 0), "shinR": (14, 0, 0), "thighL": (10, 0, 0), "shinL": (10, 0, 0)}
H_AIM = {"spine": (4, 0, -8), "neck": (0, 0, 0), "head": (2, 0, -10),
         "armR": (0, 4, -86), "foreR": (0, 0, -2), "armL": (0, -72, 8), "foreL": (0, -8, 14),
         "thighR": (-8, -4, 0), "thighL": (8, 4, 0)}
H_HIT = {"spine": (-22, 0, 10), "neck": (-10, 0, 0), "head": (-16, 0, 0),
         "armR": (0, 30, 40), "foreR": (0, 0, 30), "armL": (0, -30, -40), "foreL": (0, 0, -30),
         "thighR": (-16, 0, 0), "shinR": (22, 0, 0), "thighL": (6, 0, 0), "shinL": (6, 0, 0)}
H_ALERT = {"spine": (-8, 0, 0), "neck": (-4, 0, 0), "head": (-10, 0, 0),
           "armR": (0, 45, -20), "foreR": (0, 0, -60), "armL": (0, -45, 20), "foreL": (0, 0, 60)}
H_SHOUT = {"spine": (-10, 0, 0), "neck": (-6, 0, 0), "head": (-20, 0, 0),
           "armR": (0, -40, -10), "foreR": (0, -30, 0), "armL": (0, 40, 10), "foreL": (0, 30, 0)}
# Bottle to the mouth: upper arm forward, forearm curled up in the arm's own frame (-Y bends it up there)
H_DRINK = {"spine": (-4, 0, 0), "neck": (-8, 0, 0), "head": (-26, 0, 0),
           "armR": (0, 18, -66), "foreR": (0, -125, 0), "armL": (0, -72, 8), "foreL": (0, -8, 14)}
H_DOWN = {"drop": 0.0, "spine": (0, 0, 0), "head": (0, 0, 20), "armR": (0, 10, 0), "armL": (0, -10, 0)}  # with the root tipped over in shots

H_STRIP = ["H_STAND", "H_WALK0", "H_WALK1", "H_WALK2", "H_GRAB", "H_AIM", "H_HIT", "H_ALERT", "H_SHOUT", "H_DRINK"]


def get(name):
    if name.startswith("H_WALK"):
        return H_WALK[int(name[-1])]
    return globals()[name]


def rest_q(arm, bone, deg):
    rest = arm.data.bones[bone].matrix_local.to_quaternion()
    q = Euler([math.radians(a) for a in deg], "XYZ").to_quaternion()
    return rest.inverted() @ q @ rest


def pose_pardo(prefix, pose, ground):
    """Sets (doesn't key) a player's pose. ground is cast.json's pardo_ground_body_z."""
    OB = bpy.data.objects
    arm = OB["Armature" if prefix == "P1" else prefix + "_arm"]
    body = OB[prefix + "_body"]
    dx, dy, dz, rx, ry, rz = pose.get("body", (0,) * 6)
    body.location = (dx, dy, dz + ground)
    body.rotation_euler = [math.radians(a) for a in (rx, ry, rz)]
    for alias, bone in PARDO_BONES.items():
        pb = arm.pose.bones[bone]
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = rest_q(arm, bone, pose.get(alias, (0, 0, 0)))


def pose_hobo(name, pose, base_z=0.0):
    OB = bpy.data.objects
    arm = OB[name + "_arm"]
    arm.location = (0, 0, base_z - pose.get("drop", 0.0))
    for alias, bone in H_BONES.items():
        pb = arm.pose.bones[bone]
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = rest_q(arm, bone, pose.get(alias, (0, 0, 0)))
