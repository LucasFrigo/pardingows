# The pose library. A pose is a dict {bone key: (location, quaternion)} using the rig's own bone keys, so it fits every figure.
# Poses come from the base rig's 48 actions, sampled at any point, or are built by hand here, like the six-seven.
import bpy, math
from mathutils import Euler, Quaternion, Vector
from set_lib import bone_key, bones_of

_cache = {}


def _channels(name):
    """{bone key: {"location": [fcurves], "rotation_quaternion": [fcurves]}} for one of the base rig's actions."""
    if name in _cache:
        return _cache[name]
    a = bpy.data.actions["U_" + name]
    out = {}
    bag = a.layers[0].strips[0].channelbags[0]
    for fc in bag.fcurves:
        dp = fc.data_path
        if not dp.startswith('pose.bones["'):
            continue
        bone = dp.split('"')[1]
        prop = dp.rsplit(".", 1)[1]
        if prop not in ("location", "rotation_quaternion", "scale"):
            continue
        out.setdefault(bone_key(bone), {}).setdefault(prop, {})[fc.array_index] = fc
    _cache[name] = (out, a.frame_range[1])
    return _cache[name]


def sample(name, u):
    """The action at u, where 0 to 1 is one pass of it. Past 1 it loops."""
    chans, last = _channels(name)
    f = (u % 1.0) * last
    pose = {}
    for bone, props in chans.items():
        loc = props.get("location")
        rot = props.get("rotation_quaternion")
        sca = props.get("scale")
        pose[bone] = (
            Vector(loc[i].evaluate(f) if loc and i in loc else 0.0 for i in range(3)),
            Quaternion(rot[i].evaluate(f) if rot and i in rot else (1.0 if i == 0 else 0.0) for i in range(4)),
            Vector(sca[i].evaluate(f) if sca and i in sca else 1.0 for i in range(3)),
        )
    return pose


def duration(name):
    """One pass of an action in seconds. They're keyed at 24 fps."""
    return _channels(name)[1] / 24.0


def clear(arm):
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.location = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.scale = (1, 1, 1)


def apply(arm, pose):
    """Puts a figure in a pose. Bones the pose doesn't name go back to rest, so poses never leak into each other."""
    names = bones_of(arm)
    clear(arm)
    for key, val in pose.items():
        real = names.get(key)
        if real:
            pb = arm.pose.bones[real]
            pb.location = val[0]
            pb.rotation_quaternion = val[1]
            pb.scale = val[2] if len(val) > 2 else (1, 1, 1)


def rest_axes(arm, key, deg):
    """A bone's rotation given as Euler degrees in the armature's axes, where the figure faces -Y and +X is its left."""
    pb = arm.pose.bones[bones_of(arm)[key]]
    rest = pb.bone.matrix_local.to_quaternion()
    q = Euler([math.radians(a) for a in deg], "XYZ").to_quaternion()
    return rest.inverted() @ q @ rest


def adjust(arm, pose, key, deg):
    """Adds a rotation in armature axes on top of a pose."""
    val = pose.get(key, (Vector((0, 0, 0)), Quaternion((1, 0, 0, 0)), Vector((1, 1, 1))))
    pose[key] = (val[0], rest_axes(arm, key, deg) @ val[1], val[2] if len(val) > 2 else Vector((1, 1, 1)))
    return pose


# The six-seven meme: forearms out in front, palms up, the two hands alternating up and down like weighing two things.
# The rig's rest pose already holds its forearms forward, so the swing is small and centred near rest.
SIX_LIFT = -24  # shoulder forward, degrees, at the middle of the swing
SIX_SWING = 15  # up or down from the middle
SIX_OUT = 5  # elbows away from the body
SIX_TWIST = 180  # wrists turn the C-hands palm up


def six_seven(arm, u, twist=None):
    """u runs 0 to 1 per full swing: at 0 the left hand is high, at 0.5 the right. Lean goes with the high hand."""
    swing = math.cos(u * 2 * math.pi)
    tw = SIX_TWIST if twist is None else twist
    pose = {}
    for side, s in (("L", 1), ("R", -1)):
        lift = SIX_LIFT - SIX_SWING * swing * s
        adjust(arm, pose, f"armUp_{side}", (lift, 0, s * SIX_OUT))
        adjust(arm, pose, f"wristTwist_{side}", (0, s * tw, 0))
    adjust(arm, pose, "spine03", (0, -5 * swing, 0))
    adjust(arm, pose, "head", (0, -3 * swing, 0))
    return pose


# Left out of the shots: these actions pull the figure's body apart (see review/03-acoes.png).
BROKEN = {"Walk", "Wave", "LookingDown", "RightHandReactive", "Sleeping"}


def walk(arm, u):
    """A hand-keyed minifig walk: stiff legs and arms swinging from their pivots, as real minifigs do. u runs 0 to 1 per two steps."""
    s = math.sin(u * 2 * math.pi)
    pose = {}
    adjust(arm, pose, "legUp_L", (32 * s, 0, 0))
    adjust(arm, pose, "legUp_R", (-32 * s, 0, 0))
    adjust(arm, pose, "armUp_L", (-22 * s, 0, 0))
    adjust(arm, pose, "armUp_R", (22 * s, 0, 0))
    adjust(arm, pose, "spine03", (0, 0, 4 * s))
    return pose


def wave(arm, u, side="R"):
    """One arm up, hand swinging from side to side."""
    s = 1 if side == "L" else -1
    pose = {}
    adjust(arm, pose, f"armUp_{side}", (-100, 0, s * (24 + 14 * math.sin(u * 2 * math.pi))))
    return pose


def sit(arm):
    """Sitting: legs straight out in front, as a real minifig sits, hands on the knees."""
    pose = {}
    adjust(arm, pose, "legUp_L", (-90, 0, 0))
    adjust(arm, pose, "legUp_R", (-90, 0, 0))
    return pose


def ground(name):
    """How far up a figure must be lifted for an action: the rig's actions sink it by a fixed amount (measured in s03_cast)."""
    import json, os
    from set_lib import WORK
    global _ground
    if "_ground" not in globals():
        _ground = json.load(open(os.path.join(WORK, "cast.json")))["ground"]
    return _ground[name]
