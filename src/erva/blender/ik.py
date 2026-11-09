# Reaching for things: solves a Pardo rig's arm so the palm lands on a world point, instead of guessing angles.
# Forward kinematics are done here in plain maths from the rest matrices (no depsgraph per try), so a solve is cheap.
#   reach(prefix, side, target, pose)  -> pose with arm/fore angles changed so the palm of 'side' ("R" or "L") is at target
#   palm(prefix, side, pose)           -> where that palm is for a pose (world)
# The rig's root and body empty must already be placed and evaluated (view_layer.update()) before calling.
import math

import bpy
from mathutils import Euler, Matrix, Vector

CHAIN = {"R": ("Bone.016", "Bone.002", "Bone.003", "Bone.004"), "L": ("Bone.016", "Bone.009", "Bone.010", "Bone.011")}
ALIAS = {"Bone.016": "spine", "Bone.002": "armR", "Bone.003": "foreR", "Bone.004": "handR",
         "Bone.009": "armL", "Bone.010": "foreL", "Bone.011": "handL"}
PALM = Vector((0, 0.62 * 1.35, 0))  # the same point shots.hand() uses: the base of the fingers, in hand-bone space


def _basis(arm, bone, deg):
    rest = arm.data.bones[bone].matrix_local.to_quaternion()
    q = Euler([math.radians(a) for a in deg], "XYZ").to_quaternion()
    return (rest.inverted() @ q @ rest).to_matrix().to_4x4()


def palm(prefix, side, pose):
    arm = bpy.data.objects[prefix + "_arm"]
    bones = arm.data.bones
    m = bones["Bone"].matrix_local.copy()  # the root bone is never posed
    parent = "Bone"
    for b in CHAIN[side]:
        rel = bones[parent].matrix_local.inverted() @ bones[b].matrix_local
        m = m @ rel @ _basis(arm, b, pose.get(ALIAS[b], (0, 0, 0)))
        parent = b
    return arm.matrix_world @ m @ PALM


def reach(prefix, side, target, pose, keep_up=0.0):
    """Coordinate descent on the shoulder (x, y, z) and the elbow (x, z). Returns a new pose dict.
    keep_up > 0 adds a small pull towards the starting angles, so the arm doesn't wander into odd shapes."""
    target = Vector(target)
    a, f = "arm" + side, "fore" + side
    start = {a: list(pose.get(a, (0, 0, 0))), f: list(pose.get(f, (0, 0, 0)))}
    cur = {a: list(start[a]), f: list(start[f])}
    knobs = [(a, 0), (a, 1), (a, 2), (f, 0), (f, 2)]

    def cost(c):
        p = palm(prefix, side, {**pose, a: tuple(c[a]), f: tuple(c[f])})
        reg = sum((c[k][i] - start[k][i]) ** 2 for k, i in knobs) * keep_up * 1e-6
        return (p - target).length_squared + reg

    best = cost(cur)
    step = 24.0
    while step > 0.4:
        improved = False
        for k, i in knobs:
            for d in (step, -step):
                c = {a: list(cur[a]), f: list(cur[f])}
                c[k][i] += d
                if k == f and i == 0:
                    c[k][i] = max(-150.0, min(10.0, c[k][i]))  # elbows bend one way
                v = cost(c)
                if v < best - 1e-9:
                    best, cur, improved = v, c, True
        if not improved:
            step *= 0.5
    out = dict(pose)
    out[a], out[f] = tuple(cur[a]), tuple(cur[f])
    return out, math.sqrt(best)
