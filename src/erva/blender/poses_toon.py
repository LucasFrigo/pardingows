# Pose library for PARDÃO E A ERVA. Degrees in each rig's rest axes (rest_q). Everyone faces -Y, and "R" is always the +X side.
#
# Pardo rigs (P1 Pardão, VOVO, EVA, P2-P4, ALMA): arms and legs hang in the rest pose. -X swings a hanging limb forward,
#   +X on a shin bends the knee, +X on spine or head bows forward. For the R arm -Y raises it out to the side, for the L arm +Y.
#   "body": (dx, dy, dz, rx, ry, rz) moves <prefix>_body, in rig units (x 0.23 for metres), on top of the ground offset.
#   "glove": (right shape, left shape), one of open, fist, point, thumb, hold.
# The arms are rubber hoses (hose.py): the tube arcs from shoulder to wrist through the elbow's pull, so the elbow angle only
#   sets how much it bows.
import math

import bpy
from mathutils import Euler

PARDO_BONES = {
    "spine": "Bone.016", "head": "Bone.001",
    "armR": "Bone.002", "foreR": "Bone.003", "handR": "Bone.004", "armL": "Bone.009", "foreL": "Bone.010", "handL": "Bone.011",
    "thighR": "Bone.005", "shinR": "Bone.006", "footR": "Bone.007", "thighL": "Bone.012", "shinL": "Bone.013", "footL": "Bone.014",
}

STAND = {"spine": (2, 0, 0), "armR": (0, -14, 0), "foreR": (-20, 0, 0), "armL": (0, 14, 0), "foreL": (-20, 0, 0),
         "glove": ("open", "open")}
# The 1930s strut: chest out, knees up high, arms swinging wide. Four keys per stride, on twos.
WALK = [
    {"body": (0, 0, 0.25, 0, 0, 0), "spine": (-8, 0, 4), "head": (-4, 0, -4),
     "armR": (40, -22, 0), "foreR": (-50, 0, 0), "armL": (-60, 22, 0), "foreL": (-60, 0, 0),
     "thighR": (-70, 0, 0), "shinR": (80, 0, 0), "thighL": (20, 0, 0), "shinL": (10, 0, 0), "glove": ("open", "open")},
    {"body": (0, 0, -0.1, 0, 0, 0), "spine": (-4, 0, 0), "head": (-2, 0, 0),
     "armR": (10, -22, 0), "foreR": (-30, 0, 0), "armL": (-20, 22, 0), "foreL": (-30, 0, 0),
     "thighR": (-20, 0, 0), "shinR": (20, 0, 0), "thighL": (0, 0, 0), "shinL": (40, 0, 0), "glove": ("open", "open")},
    {"body": (0, 0, 0.25, 0, 0, 0), "spine": (-8, 0, -4), "head": (-4, 0, 4),
     "armR": (-60, -22, 0), "foreR": (-60, 0, 0), "armL": (40, 22, 0), "foreL": (-50, 0, 0),
     "thighL": (-70, 0, 0), "shinL": (80, 0, 0), "thighR": (20, 0, 0), "shinR": (10, 0, 0), "glove": ("open", "open")},
    {"body": (0, 0, -0.1, 0, 0, 0), "spine": (-4, 0, 0), "head": (-2, 0, 0),
     "armR": (-20, -22, 0), "foreR": (-30, 0, 0), "armL": (10, 22, 0), "foreL": (-30, 0, 0),
     "thighL": (-20, 0, 0), "shinL": (20, 0, 0), "thighR": (0, 0, 0), "shinR": (40, 0, 0), "glove": ("open", "open")},
]
# Tiptoe sneak: hunched, high knees, hands up by the chest like paws
SNEAK = {"body": (0, 0, 0.4, 0, 0, 0), "spine": (24, 0, 0), "head": (-20, 0, 0),
         "armR": (-70, -10, 0), "foreR": (-100, 0, 0), "armL": (-70, 10, 0), "foreL": (-100, 0, 0),
         "thighR": (-80, 0, 0), "shinR": (110, 0, 0), "thighL": (10, 0, 0), "shinL": (20, 0, 0), "footL": (40, 0, 0),
         "glove": ("open", "open")}
# Pipe or cigarette to the mouth with the right hand, left hand on the hip
PUFF = {"spine": (-4, 0, 0), "head": (-10, 0, 0), "armR": (-40, -16, 0), "foreR": (-130, 0, 0),
        "armL": (10, 50, 0), "foreL": (-90, 0, 30), "glove": ("hold", "fist")}
SHRUG = {"body": (0, 0, 0.1, 0, 0, 0), "spine": (-4, 0, 0), "head": (0, 0, 14),
         "armR": (0, -60, 0), "foreR": (-30, -60, 0), "armL": (0, 60, 0), "foreL": (-30, 60, 0), "glove": ("open", "open")}
# Soul gone: knees buckled, arms dangling, head lolled
SLUMP = {"body": (0, 0, -0.42, 8, 0, 0), "spine": (40, 0, 8), "head": (34, 0, 16),
         "armR": (-10, -6, 0), "foreR": (0, 0, 0), "armL": (-14, 6, 0), "foreL": (0, 0, 0),
         "thighR": (-60, -8, 0), "shinR": (90, 0, 0), "thighL": (-60, 8, 0), "shinL": (90, 0, 0), "glove": ("open", "open")}
CROSSED = {"spine": (-6, 0, 0), "head": (-10, 0, 0),
           "armR": (-55, 0, -40), "foreR": (-20, 0, -95), "armL": (-50, 0, 40), "foreL": (-20, 0, 95),
           "thighR": (0, -6, 0), "thighL": (0, 6, 0), "glove": ("fist", "fist")}
POINT = {"spine": (0, 0, 0), "head": (-6, 0, 0), "armR": (-90, -14, 0), "foreR": (-6, 0, 0),
         "armL": (10, 50, 0), "foreL": (-90, 0, 30), "glove": ("point", "fist")}
# The 1930s two-step: knees in, knees out, hands flapping, on the half beat
DANCE_A = {"body": (0, 0, -0.2, 0, 0, 10), "spine": (0, 0, -8), "head": (0, 0, 10),
           "armR": (-30, -70, 0), "foreR": (-60, -40, 0), "armL": (-30, 70, 0), "foreL": (-60, 40, 0),
           "thighR": (-50, -20, 0), "shinR": (70, 0, 0), "thighL": (0, 10, 0), "shinL": (10, 0, 0), "glove": ("open", "open")}
DANCE_B = {"body": (0, 0, -0.2, 0, 0, -10), "spine": (0, 0, 8), "head": (0, 0, -10),
           "armR": (-30, -70, 0), "foreR": (-60, -40, 0), "armL": (-30, 70, 0), "foreL": (-60, 40, 0),
           "thighL": (-50, 20, 0), "shinL": (70, 0, 0), "thighR": (0, -10, 0), "shinR": (10, 0, 0), "glove": ("open", "open")}
# Grandpa in his rocking chair: seated, back curved, book on his lap
SIT = {"body": (0, 0.6, -1.25, 0, 0, 0), "spine": (12, 0, 0), "head": (-14, 0, 0),
       "armR": (-50, -12, 0), "foreR": (-50, 0, 0), "armL": (-50, 12, 0), "foreL": (-50, 0, 0),
       "thighR": (-88, -6, 0), "shinR": (82, 0, 0), "thighL": (-88, 6, 0), "shinL": (82, 0, 0), "glove": ("hold", "open")}
OFFER = {"spine": (6, 0, 0), "head": (-4, 0, 0), "armR": (-80, -20, 0), "foreR": (-20, 0, 0),
         "armL": (0, 14, 0), "foreL": (-20, 0, 0), "glove": ("hold", "open")}
SCARED = {"body": (0, 0.2, 0.3, -8, 0, 0), "spine": (-18, 0, 0), "head": (-14, 0, 0),
          "armR": (-150, -40, 0), "foreR": (-20, 0, 0), "armL": (-150, 40, 0), "foreL": (-20, 0, 0),
          "thighR": (-30, 0, 0), "shinR": (40, 0, 0), "glove": ("open", "open")}

STRIP = ["STAND", "WALK0", "WALK2", "SNEAK", "PUFF", "SHRUG", "SLUMP", "CROSSED", "POINT", "DANCE_A", "OFFER", "SCARED"]


def get(name):
    if name.startswith("WALK"):
        return WALK[int(name[4:])]
    return globals()[name]


def rest_q(arm, bone, deg):
    rest = arm.data.bones[bone].matrix_local.to_quaternion()
    q = Euler([math.radians(a) for a in deg], "XYZ").to_quaternion()
    return rest.inverted() @ q @ rest


def pose_pardo(prefix, pose, ground):
    """Sets (doesn't key) a rig's pose, gloves included. ground is cast.json's pardo_ground_body_z."""
    OB = bpy.data.objects
    arm = OB[prefix + "_arm"]
    body = OB[prefix + "_body"]
    dx, dy, dz, rx, ry, rz = pose.get("body", (0,) * 6)
    body.location = (dx, dy, dz + ground)
    body.rotation_euler = [math.radians(a) for a in (rx, ry, rz)]
    for alias, bone in PARDO_BONES.items():
        pb = arm.pose.bones[bone]
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = rest_q(arm, bone, pose.get(alias, (0, 0, 0)))
    gl = pose.get("glove", ("open", "open"))
    for side, shape in zip("RL", gl):
        for o in OB:
            if o.get("glove_of") == f"{prefix}{side}":
                on = o.get("glove_shape") == shape
                o.hide_viewport = o.hide_render = not on
