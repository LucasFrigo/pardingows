# Poses for this video, in degrees in the rest axes (see lib.set_bone_rot). +X bends forward, so -X swings a hanging limb out in front.
# Everyone faces -Y and "R" is always the +X side. Motion is smooth: poses are blended per frame, and solve_lift keeps the lowest sole on the ground.
import math
from mathutils import Euler, Quaternion, Vector

ALIASES = ("spine", "head", "armR", "foreR", "armL", "foreL", "thighR", "shinR", "thighL", "shinL")

# Rest head positions of the bones, in armature space (read from the rig)
REST = {"spine": (0, -0.16, 0.46), "armR": (0.55, -0.64, 1.78), "foreR": (0.83, -0.42, 0.97), "handR": (1.09, -0.22, 0.30), "handTipR": (1.34, 0.01, -0.48),
        "armL": (-0.57, -0.64, 1.78), "foreL": (-0.85, -0.42, 0.97), "handL": (-1.11, -0.22, 0.30), "handTipL": (-1.36, 0.01, -0.48),
        "thighR": (0.48, 0, 0.24), "shinR": (0.89, -0.76, -0.38), "ankleR": (0.56, -0.10, -1.35), "thighL": (-0.49, 0, 0.24), "shinL": (-0.91, -0.76, -0.38), "ankleL": (-0.57, -0.10, -1.35),
        "head": (0, -0.76, 1.79)}
ARM_Z = 1.87  # the armature's height above the body empty: rest soles land on z = 0
SOLE = 0.52  # ankle height above the sole


def q(deg):
    return Euler([math.radians(a) for a in deg], "XYZ").to_quaternion()


def _body_of(pose):
    return pose.get("body", (0, 0, 0, 0, 0, 0))


def fk(pose):
    """Points of a pose in the body empty's space, before any lift: hands, soles and head."""
    dx, dy, dz, rx, ry, rz = _body_of(pose)
    B = q((rx, ry, rz))
    off = Vector((dx, dy, dz))

    def to_body(p):
        return off + B @ (Vector(p) + Vector((0, 0, ARM_Z)))

    out = {}
    Qs = q(pose.get("spine", (0, 0, 0)))
    ps = Vector(REST["spine"])
    for side in "RL":
        Qa = Qs @ q(pose.get("arm" + side, (0, 0, 0)))
        pa = ps + Qs @ (Vector(REST["arm" + side]) - ps)
        pf = pa + Qa @ (Vector(REST["fore" + side]) - Vector(REST["arm" + side]))
        Qf = Qa @ q(pose.get("fore" + side, (0, 0, 0)))
        ph = pf + Qf @ (Vector(REST["hand" + side]) - Vector(REST["fore" + side]))
        tip = ph + Qf @ (Vector(REST["handTip" + side]) - Vector(REST["hand" + side])) * 0.6
        out["hand" + side] = to_body(tip)
        Qt = q(pose.get("thigh" + side, (0, 0, 0)))
        pt = Vector(REST["thigh" + side])
        pn = pt + Qt @ (Vector(REST["shin" + side]) - pt)
        Qn = Qt @ q(pose.get("shin" + side, (0, 0, 0)))
        pk = pn + Qn @ (Vector(REST["ankle" + side]) - Vector(REST["shin" + side]))
        sole = pk + Qn @ Vector((0, 0, -SOLE))
        out["sole" + side] = to_body(sole)
    ph = ps + Qs @ (Vector(REST["head"]) - ps)
    out["head"] = to_body(ph)
    return out


def solve_lift(pose):
    """How far the body must rise for its lowest sole to touch the ground."""
    pts = fk(pose)
    return -min(pts["soleR"].z, pts["soleL"].z)


def mix(a, b, u):
    """Blends two poses key by key."""
    out = {}
    for k in set(a) | set(b):
        n = 6 if k == "body" else 3
        va, vb = a.get(k, (0,) * n), b.get(k, (0,) * n)
        out[k] = tuple(x + (y - x) * u for x, y in zip(va, vb))
    return out


def ease(u):
    u = 0.0 if u < 0 else 1.0 if u > 1 else u
    return u * u * (3 - 2 * u)


STAND = {"spine": (2, 0, 0), "armR": (0, -8, 0), "foreR": (5, 0, 0), "armL": (0, 8, 0), "foreL": (5, 0, 0)}
PROUD = {"body": (0, 0, 0, -4, 0, 0), "spine": (-6, 0, 0), "head": (-4, 0, 0), "armR": (6, -26, 0), "foreR": (-30, 0, 0), "armL": (6, 26, 0), "foreL": (-30, 0, 0)}
THUMB = {"body": (0, 0, 0, -3, 0, 0), "spine": (-4, 0, 6), "head": (-4, 0, 8), "armR": (-62, -34, 0), "foreR": (-74, 0, 0), "armL": (4, 18, 0), "foreL": (-10, 0, 0)}
POINT = {"body": (0, 0, 0, 7, 0, 0), "spine": (9, 0, -8), "head": (-13, 0, 4), "armR": (-92, -4, 0), "foreR": (-6, 0, 0), "armL": (6, 34, 0), "foreL": (-44, 0, 0),
         "thighR": (-18, 0, 0), "shinR": (14, 0, 0), "thighL": (14, 0, 0), "shinL": (10, 0, 0)}
SWOLLEN = {"body": (0, 0, 0, 3, 0, 0), "spine": (4, 0, 0), "head": (-2, 0, 0), "armR": (-12, -58, 0), "foreR": (-30, 0, 0), "armL": (-12, 58, 0), "foreL": (-30, 0, 0)}
PIT = {"spine": (0, 0, 0), "head": (-6, 0, 0), "armR": (0, -6, 0), "armL": (0, 6, 0)}
HOLD_FRONT = {"spine": (3, 0, 0), "head": (2, 0, 0), "armR": (-78, -20, 0), "foreR": (-22, 0, 0), "armL": (-78, 20, 0), "foreL": (-22, 0, 0)}
TORN = {"spine": (-5, 0, 0), "head": (-10, 0, 0), "armR": (-58, -78, 0), "foreR": (-12, 0, 0), "armL": (-58, 78, 0), "foreL": (-12, 0, 0)}
HAND_OUT = {"body": (0, 0, 0, 4, 0, 0), "spine": (5, 0, 0), "head": (-6, 0, 0), "armR": (-82, -6, 0), "foreR": (-8, 0, 0), "armL": (4, 16, 0), "foreL": (-30, 0, 0)}
HOLD_UP = {"spine": (-3, 0, 0), "head": (-12, 0, 0), "armR": (-160, -24, 0), "foreR": (-14, 0, 0), "armL": (-160, 24, 0), "foreL": (-14, 0, 0)}
TORN_UP = {"spine": (-6, 0, 0), "head": (-14, 0, 0), "armR": (-128, -74, 0), "foreR": (-8, 0, 0), "armL": (-128, 74, 0), "foreL": (-8, 0, 0)}
LETTER_SIDE = {"spine": (0, 0, 0), "head": (-6, 0, 0), "armR": (-34, -122, 0), "foreR": (-34, 0, 0), "armL": (4, 16, 0), "foreL": (-30, 0, 0)}
LETTER_UP = {"spine": (0, 0, 0), "head": (-8, 0, 0), "armR": (-122, -8, 0), "foreR": (-12, 0, 0), "armL": (4, 16, 0), "foreL": (-30, 0, 0)}
WINDUP = {"body": (0, 0, 0, 10, 0, -8), "spine": (8, 0, -6), "head": (-8, 0, 0), "armR": (20, -36, 0), "foreR": (-30, 0, 0), "armL": (-40, 36, 0), "foreL": (-30, 0, 0),
          "thighR": (38, 0, 0), "shinR": (56, 0, 0), "thighL": (-16, 0, 0), "shinL": (14, 0, 0)}
KICK = {"body": (0, 0, 0, -18, 0, 10), "spine": (-12, 0, 8), "head": (-6, 0, 0), "armR": (40, -46, 0), "foreR": (-20, 0, 0), "armL": (-50, 40, 0), "foreL": (-20, 0, 0),
        "thighR": (-98, 0, 0), "shinR": (6, 0, 0), "thighL": (8, 0, 0), "shinL": (8, 0, 0)}
ORB_UP = {"body": (0, 0, 0, -4, 0, 0), "spine": (-5, 0, 0), "head": (-5, 0, 0), "armR": (-20, -128, 0), "foreR": (0, -28, 0), "armL": (10, 52, 0), "foreL": (-20, 0, 0),
          "thighR": (-12, -8, 0), "shinR": (8, 0, 0), "thighL": (10, 8, 0), "shinL": (8, 0, 0)}
DANCE_A = {"body": (0, 0, 0, 2, 8, 14), "spine": (2, 8, 8), "head": (-6, -8, -5), "armR": (0, -104, 0), "foreR": (0, -66, 0), "armL": (-22, 44, 0), "foreL": (-58, 0, 0),
           "thighR": (-30, 0, 0), "shinR": (34, 0, 0), "thighL": (14, 0, 0), "shinL": (10, 0, 0)}
DANCE_B = {"body": (0, 0, 0, 2, -8, -14), "spine": (2, -8, -8), "head": (-6, 8, 5), "armR": (-22, -44, 0), "foreR": (-58, 0, 0), "armL": (0, 104, 0), "foreL": (0, 66, 0),
           "thighR": (14, 0, 0), "shinR": (10, 0, 0), "thighL": (-30, 0, 0), "shinL": (34, 0, 0)}
FUME = {"body": (0, 0, 0, 6, 0, 0), "spine": (10, 0, 0), "head": (6, 0, 0), "armR": (-20, -30, 0), "foreR": (-96, 0, 0), "armL": (-20, 30, 0), "foreL": (-96, 0, 0),
        "thighR": (-16, -6, 0), "shinR": (24, 0, 0), "thighL": (-16, 6, 0), "shinL": (24, 0, 0)}
SHOCK_A = {"body": (0, 0, 0, -6, 4, 0), "spine": (-8, 6, 0), "head": (-14, 8, 0), "armR": (-20, -128, 0), "foreR": (-20, 0, 0), "armL": (-20, 118, 0), "foreL": (-20, 0, 0),
           "thighR": (-16, -18, 0), "shinR": (24, 0, 0), "thighL": (-6, 18, 0), "shinL": (10, 0, 0)}
SHOCK_B = {"body": (0, 0, 0, -3, -4, 0), "spine": (-5, -6, 0), "head": (-8, -8, 0), "armR": (-30, -112, 0), "foreR": (-40, 0, 0), "armL": (-30, 132, 0), "foreL": (-40, 0, 0),
           "thighR": (-6, -18, 0), "shinR": (10, 0, 0), "thighL": (-16, 18, 0), "shinL": (24, 0, 0)}
HIT = {"body": (0, 0, 0, -44, 0, 0), "spine": (-20, 0, 0), "head": (-30, 0, 0), "armR": (-30, -100, 0), "foreR": (-10, 0, 0), "armL": (-30, 100, 0), "foreL": (-10, 0, 0),
       "thighR": (-50, 0, 0), "shinR": (20, 0, 0), "thighL": (-30, 0, 0), "shinL": (30, 0, 0)}
TURN_LOOK = {"spine": (-4, 0, 0), "head": (-16, 0, 0), "armR": (-10, -30, 0), "foreR": (-30, 0, 0), "armL": (-10, 30, 0), "foreL": (-30, 0, 0)}
HOP_TUCK = {"spine": (0, 0, 0), "head": (-6, 0, 0), "armR": (-30, -70, 0), "foreR": (-50, 0, 0), "armL": (-30, 70, 0), "foreL": (-50, 0, 0),
            "thighR": (-30, 0, 0), "shinR": (40, 0, 0), "thighL": (-30, 0, 0), "shinL": (40, 0, 0)}


def strut(p, swagger=1.0):
    """The strut, as a function of stride phase p (one stride, two steps, per unit). Hips roll, chest out, arms swinging wide."""
    a = math.sin(2 * math.pi * p)
    b = math.cos(2 * math.pi * p)
    return {
        "body": (0, 0, 0, -5, 4 * a * swagger, 10 * a * swagger),
        "spine": (-6, 3 * a * swagger, -9 * a * swagger),
        "head": (-5 + 3 * abs(b), -4 * a * swagger, 6 * a * swagger),
        "armR": (32 * a, -20, 0), "foreR": (-24 - 14 * max(0, -a), 0, 0),
        "armL": (-32 * a, 20, 0), "foreL": (-24 - 14 * max(0, a), 0, 0),
        "thighR": (-30 * a, 0, 0), "shinR": (44 * max(0, b), 0, 0),
        "thighL": (30 * a, 0, 0), "shinL": (44 * max(0, -b), 0, 0),
    }
