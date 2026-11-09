# Putting the cast into the stage: world placement from stage-local coordinates, facing, poses, hand props.
# Used by set_stills.py and later s08_shots.py. Facing: yaw in degrees, 0 = towards -Y (the camera side), 90 = towards +X.
import bpy, json, math, os
from mathutils import Matrix, Vector
import poses_brawl as PB
from set_lib import WORK

OB = bpy.data.objects
STAGE = json.load(open(os.path.join(WORK, "stage.json"), encoding="utf8"))
CAST = json.load(open(os.path.join(WORK, "cast.json"), encoding="utf8"))
ORIGIN = Vector(STAGE["origin"])
G = CAST["pardo_ground_body_z"]


def world(local):
    return Vector(local) + ORIGIN


def pardo(prefix, local, yaw, pose):
    root = OB[prefix]
    root.location = world(local)
    root.rotation_euler = (0, 0, math.radians(yaw))
    PB.pose_pardo(prefix, pose, G)


def hobo(name, local, yaw, pose):
    root = OB[name]
    root.location = world(local)
    root.rotation_euler = (0, 0, math.radians(yaw))
    PB.pose_hobo(name, pose)


def static(name, local, yaw, scale=1.0):
    root = OB[name]
    root.location = world(local)
    root.rotation_euler = (0, 0, math.radians(yaw))
    root.scale = (scale,) * 3


def hand_prop(tag, prefab, arm_name, bone, loc=(0, 0, 0), rot=(0, 0, 0), scale=1.0):
    """A prefab instance riding on a bone (bone space: +Y runs along the bone, from its tail). Re-used by tag."""
    ob = OB.get(tag)
    if not ob:
        ob = OB.new(tag, None)
        ob.instance_type = "COLLECTION"
        bpy.data.collections["cast"].objects.link(ob)
    ob.instance_collection = bpy.data.collections["PF_" + prefab]
    ob.parent = OB[arm_name]
    ob.parent_type, ob.parent_bone = "BONE", bone
    ob.location = loc
    ob.rotation_euler = [math.radians(a) for a in rot]
    ob.scale = (scale,) * 3
    ob.hide_render = ob.hide_viewport = False
    return ob


def gun_in_hand(tag, arm_name, bone="LeftHand"):
    """The pistol prefab fitted to a hand in its current pose: barrel along the hand, grip in the palm, top up.
    Then it rides on the bone, so later poses carry it. Pistol prefab space: barrel +X, top +Z, grip near (-0.085, -0.068, 0.035)."""
    ob = hand_prop(tag, "pistola", arm_name, bone)
    bpy.context.view_layer.update()
    arm = OB[arm_name]
    pb = arm.pose.bones[bone]
    head, tail = arm.matrix_world @ pb.head, arm.matrix_world @ pb.tail
    x = (tail - head).normalized()
    z = Vector((0, 0, 1))
    z = (z - x * z.dot(x)).normalized()
    y = z.cross(x)
    rot = Matrix((x, y, z)).transposed().to_4x4()
    palm = head + x * 0.035 - z * 0.065
    ob.matrix_world = Matrix.Translation(palm) @ rot @ Matrix.Translation(Vector((0.085, 0.068, -0.035)))
    return ob


def camera(name, local_pos, local_target, lens):
    cd = bpy.data.cameras.get(name) or bpy.data.cameras.new(name)
    cam = OB.get(name) or OB.new(name, cd)
    if cam.name not in bpy.context.scene.collection.objects:
        bpy.context.scene.collection.objects.link(cam)
    p, t = world(local_pos), world(local_target)
    cam.location = p
    cam.rotation_euler = (t - p).to_track_quat("-Z", "Y").to_euler()
    cd.lens = lens
    cd.clip_start, cd.clip_end = 0.1, 900
    return cam


def fill_light(cam, energy=60.0):
    """A soft light riding just above the camera: games of the era lit the player from the camera so they always read."""
    ob = OB.get("luz_camera")
    if not ob:
        ld = bpy.data.lights.new("luz_camera", "POINT")
        ld.color = (0.8, 0.85, 1.0)
        ld.shadow_soft_size = 1.5
        ld.use_shadow = False
        ob = OB.new("luz_camera", ld)
        bpy.context.scene.collection.objects.link(ob)
    ob.data.energy = energy
    ob.parent = cam
    ob.location = (0, 0.6, 0)
    return ob
