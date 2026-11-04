# Step 4: keys the whole video from timeline.json. Safe to re-run: clears its own animation first.
# Roots and camera move at 30 fps; bone poses step at 15 fps for the PS1 feel. No easing between keys.
import bpy, json, math, random, sys, importlib
from mathutils import Euler, Matrix, Quaternion, Vector
sys.path.insert(0, r"C:\Users\lukeg\Projetos\pardingows\src\thps\blender")
import lib, poses
importlib.reload(lib); importlib.reload(poses)
from lib import BONES, DECK_Z, SCALE, UPPER
from poses import (RIDE, PUSH, CROUCH, OLLIE, GRAB, GRIND, STAND, HANDS_UP, HAND_OUT, BAIL_A, SPECIAL, PLEAD,
                   COP_BONES, COP_STAND, COP_DEMAND, COP_PHONE, COP_SHOCK, COP_OVERHEAD, COP_FLAT)

TL = json.load(open(r"C:\Users\lukeg\Projetos\pardingows\src\thps\timeline.json", encoding="utf8"))
START, FRAMES = TL["start"], TL["frames"]
BEAT = 60 / TL["bpm"]
S = {k: (a - START, b - START) for k, (a, b) in TL["shots"].items()}
C = {k: t - START for k, t in TL["cues"].items()}
FAR = (500, 500, -50)

sc = bpy.context.scene
OB = bpy.data.objects
p1, p2, cop_root, car = OB["P1"], OB["P2"], OB["COP"], OB["CAR"]
arm1, arm2, cop_arm = OB["Armature"], OB["P2_arm"], OB["Object_4"]
ARMS = {"P1": arm1, "P2": arm2}

cam = OB.get("CAM")
if not cam:
    cam = bpy.data.objects.new("CAM", bpy.data.cameras.new("CAM"))
    sc.collection.objects.link(cam)
cam.data.clip_start = 0.05
cam.data.clip_end = 800
sc.camera = cam
sc.frame_start, sc.frame_end = 1, FRAMES

glow = OB.get("phone light")
if not glow:
    glow = bpy.data.objects.new("phone light", bpy.data.lights.new("phone light", "POINT"))
    sc.collection.objects.link(glow)
glow.data.color = (0.75, 0.87, 1.0)
glow.data.use_shadow = False

P1_PARTS = [c for c in arm1.children if c.type == "MESH" and not c.name.startswith("phone")]
PIECES = [OB["piece " + c.name] for c in P1_PARTS]
SPARKS = [OB[f"spark {i}"] for i in range(16)]

# ---- Where each smurf part sits at rest, relative to the player root, for the falling-apart gag
arm1.data.pose_position = "REST"
body1 = OB["P1_body"]
body1.location = (0, 0, 0)
p1.location, p1.rotation_euler = (0, 0, 0), (0, 0, 0)
bpy.context.view_layer.update()
root_inv = p1.matrix_world.inverted()
REST_M = {c.name: root_inv @ c.matrix_world for c in P1_PARTS}
arm1.data.pose_position = "POSE"

# ---- Clear previous animation
animated = [p1, p2, cop_root, car, cam, glow, arm1, arm2, cop_arm, cam.data, glow.data] + PIECES + SPARKS + P1_PARTS
animated += [OB[n] for n in ("P1_body", "P2_body", "P1_board", "P2_board", "P1_stance", "P2_stance", "P1_shadow", "P2_shadow", "COP_shadow",
                             "phone smurf", "phone cop", "phone ground", "board held", "letter C", "letter P", "letter F", "bang", "blood",
                             "banana split", "oil bottle", "oil stream", "cop_cap", "cop_mouth", "P2_marker", "flash red", "flash blue")]
for ob in animated:
    if ob.animation_data:
        ob.animation_data_clear()
for pb in list(arm1.pose.bones) + list(arm2.pose.bones):
    pb.rotation_mode = "QUATERNION"
for a in list(bpy.data.actions):
    if a.users == 0:
        bpy.data.actions.remove(a)

prefs = bpy.context.preferences.edit
prev_interp = prefs.keyframe_new_interpolation_type
prefs.keyframe_new_interpolation_type = "CONSTANT"

last = {}
def K(owner, path, value, f):
    """Sets a property and keys it only if it changed. With constant keys that is all we need."""
    key = (owner.as_pointer(), path)
    val = tuple(round(float(x), 4) for x in value) if hasattr(value, "__len__") else value
    if last.get(key) == val:
        return
    setattr(owner, path, value)
    owner.keyframe_insert(path, frame=f)
    last[key] = val

def rad(*d):
    return tuple(math.radians(x) for x in d)

def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x

def phase(v, a, b):
    return clamp((v - a) / (b - a))

def arc(v, t0, t1, z0, z1, h):
    u = phase(v, t0, t1)
    return z0 + (z1 - z0) * u + 4 * h * u * (1 - u)

def blend(a, b, t):
    """Pose mix. Used over one or two pose steps so transitions stay abrupt."""
    out = {}
    for k in set(a) | set(b):
        if k == "free":
            continue
        va, vb = a.get(k, (0, 0, 0) if k != "body" else (0,) * 6), b.get(k, (0, 0, 0) if k != "body" else (0,) * 6)
        out[k] = tuple(x + (y - x) * t for x, y in zip(va, vb))
    if (a if t < 0.5 else b).get("free"):
        out["free"] = True
    return out

def rest_q(arm, bone_name, deg):
    rest = arm.data.bones[bone_name].matrix_local.to_quaternion()
    q = Euler(rad(*deg), "XYZ").to_quaternion()
    return rest.inverted() @ q @ rest

def put_pose(prefix, f, pose, lift=0.0):
    arm = ARMS[prefix]
    body = OB[prefix + "_body"]
    free = pose.get("free", False)
    dx, dy, dz, rx, ry, rz = pose.get("body", (0,) * 6)
    K(body, "location", (dx, dy, dz + (0 if free else DECK_Z) + lift), f)
    K(body, "rotation_euler", rad(rx, ry, rz), f)
    K(OB[prefix + "_stance"], "location", (0, 0, DECK_Z + lift), f)
    for alias in UPPER:
        pb = arm.pose.bones[BONES[alias]]
        K(pb, "rotation_quaternion", rest_q(arm, BONES[alias], pose.get(alias, (0, 0, 0))), f)
    infl = 0.0 if free else 1.0
    for pb in arm.pose.bones:
        for c in pb.constraints:
            if c.name == "foot":
                K(c, "influence", infl, f)

def put(prefix, f, pos, yaw=0, pitch=0, roll=0, pose=None, board_loc=(0, 0, DECK_Z), board_rot=(0, 0, 0), board=True, lift=0.0, ground=0.035):
    root = OB[prefix]
    K(root, "location", pos, f)
    K(root, "rotation_euler", rad(roll, pitch, yaw), f)
    bd = OB[prefix + "_board"]
    K(bd, "location", board_loc, f)
    K(bd, "rotation_euler", rad(*board_rot), f)
    K(bd, "hide_render", not board, f)
    if pose is not None and (f - 1) % 2 == 0:
        put_pose(prefix, f, pose, lift)
    sh = OB[prefix + "_shadow"]
    height = max(pos[2] - ground, 0)
    size = clamp(1.0 - height * 0.12, 0.35, 1.0)
    K(sh, "location", (pos[0], pos[1], ground + 0.004), f)
    K(sh, "scale", (size, size, 1), f)

def aim_q(pb, aims, alias):
    """Bone rotation that points this arm segment along an aim direction. A forearm undoes its upper arm first."""
    rest = pb.bone.matrix_local.to_quaternion()
    arm_alias = alias.replace("fore", "arm")
    rest_dir = (pb.bone.tail_local - pb.bone.head_local).normalized()
    want = Vector(aims[alias]).normalized()
    if alias.startswith("fore"):
        upper = pb.parent.bone
        upper_dir = (upper.tail_local - upper.head_local).normalized()
        want = upper_dir.rotation_difference(Vector(aims[arm_alias]).normalized()).inverted() @ want
    q = rest_dir.rotation_difference(want)
    return rest.inverted() @ q @ rest

def cop_pose_q(pose):
    aims = pose.get("aim", {})
    for alias, bone in COP_BONES.items():
        pb = cop_arm.pose.bones[bone]
        pb.rotation_mode = "QUATERNION"
        yield pb, aim_q(pb, aims, alias) if alias in aims else rest_q(cop_arm, bone, pose.get(alias, (0, 0, 0)))

def put_cop(f, pos, yaw, pose, scale=(1, 1, 1), pitch=0):
    K(cop_root, "location", pos, f)
    K(cop_root, "rotation_euler", rad(pitch, 0, yaw), f)
    K(cop_root, "scale", scale, f)
    K(OB["COP_shadow"], "location", (pos[0], pos[1], 0.04), f)
    if (f - 1) % 2 == 0:
        for pb, q in cop_pose_q(pose):
            K(pb, "rotation_quaternion", q, f)

def phone_in_hand(pose):
    """Where the phone sits for this pose, in COP space: behind his fingers as the camera sees them, lit face to him."""
    for pb, q in cop_pose_q(pose):
        pb.rotation_quaternion = q
    bpy.context.view_layer.update()
    # Measured off the skinned mesh: the finger end bones in this rig don't sit on the fingers
    skin = OB["Object_7"]
    ev = skin.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    groups = {g.index for g in skin.vertex_groups if g.name.startswith(("RightHand", "RightMiddleFinger", "RightThumb"))}
    to_root = cop_root.matrix_world.inverted() @ ev.matrix_world
    pts = [to_root @ v.co for v in me.vertices if max(skin.data.vertices[v.index].groups, key=lambda g: g.weight).group in groups]
    ev.to_mesh_clear()
    lo, hi = [min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]
    palm = (Vector(lo) + Vector(hi)) / 2
    return palm + Vector((-0.02, 0.02, 0.03))

PHONE_HOLD, PHONE_SHOCK = phone_in_hand(COP_PHONE), phone_in_hand(COP_SHOCK)

def put_cam(f, pos, tgt, lens=24.0, shake=0.0):
    pos = Vector(pos)
    tgt = Vector(tgt)
    if shake:
        r = random.Random(f)
        pos = pos + Vector((r.uniform(-1, 1), r.uniform(-1, 1), r.uniform(-1, 1))) * shake
    K(cam, "location", pos, f)
    K(cam, "rotation_euler", (tgt - pos).to_track_quat("-Z", "Y").to_euler(), f)
    K(cam.data, "lens", lens, f)

def show(names, on, f):
    for n in names:
        K(OB[n], "hide_render", not on, f)

def sparks(f, center, n, spread=0.6, up=0.5):
    """Random short-lived bits, re-rolled every frame. It only has to flicker."""
    r = random.Random(f * 7)
    for i, s in enumerate(SPARKS):
        if i < n:
            K(s, "location", (center[0] + r.uniform(-spread, spread), center[1] + r.uniform(-spread, spread), center[2] + abs(r.uniform(0, up))), f)
            K(s, "hide_render", False, f)
        else:
            K(s, "hide_render", True, f)

# ---- Pre-compute the slam so pieces fall the same way on every run
SLAM = C["slam"]
SLAM_POS = Vector((19.0 - 4.0 * (SLAM - S["bail"][0]), -2.5, 0.035))
slam_root = Matrix.Translation(SLAM_POS) @ Matrix.Rotation(math.radians(180), 4, "Z")
rand = random.Random(13)
TRAJ = {}
HOLD_END = C["reassemble"] - 0.2
dt = 1 / 30
steps = int((HOLD_END - SLAM) / dt) + 2
for c in P1_PARTS:
    M = slam_root @ REST_M[c.name]
    pos = M.to_translation()
    start_pos, rot0 = pos.copy(), M.to_euler()
    dirn = Vector((pos.x - SLAM_POS.x, pos.y - SLAM_POS.y, 0))
    vel = dirn * 3.2 + Vector((rand.uniform(-1.6, 1.6), rand.uniform(-1.6, 1.6), rand.uniform(2.0, 4.6)))
    spin = Vector((rand.uniform(-9, 9), rand.uniform(-9, 9), rand.uniform(-5, 5)))
    # Parts keep their scale; piece origins sit near the part, so the floor is a simple plane
    seq = []
    p, w, rot = pos.copy(), vel.copy(), Vector(rot0)
    for _ in range(steps):
        seq.append((p.copy(), rot.copy()))
        w.z -= 9.8 * dt
        p += w * dt
        rot += spin * dt
        if p.z < 0.1:
            p.z = 0.1
            w.z *= -0.35
            w.x *= 0.5
            w.y *= 0.5
            spin *= 0.5
    TRAJ[c.name] = (start_pos, Vector(rot0), seq)
    OB["piece " + c.name].scale = M.to_scale()

for f in range(1, FRAMES + 1):
    v = (f - 1) / 30
    in_shot = lambda name: S[name][0] <= v < S[name][1]
    beat_on = int(v / (BEAT / 2)) % 2 == 0

    # ---- Defaults, overridden by the shots below
    p1_parts_on, pieces_on = True, False
    phone_s, phone_c, phone_g = False, False, False
    held_board = False
    letters = {"C": None, "P": None, "F": None}
    bang, mouth = False, False
    light = 0.0
    spark_n = 0

    # ---- The car: skids in on "vem", stays put until the end of the road section
    if v < C["car_in"]:
        car_pos, car_yaw = (23, 70, 0), 0
    elif v < C["car_stop"]:
        u = phase(v, C["car_in"], C["car_stop"])
        car_pos = (23, 46 * (1 - u) ** 2, 0)
        car_yaw = 34 * math.sin(u * 7) * (1 - u)
    else:
        car_pos, car_yaw = (23, 0, 0), 0
    if v >= S["special"][0]:
        car_pos = FAR
    K(car, "location", car_pos, f)
    K(car, "rotation_euler", rad(0, 0, car_yaw), f)
    siren = C["car_in"] <= v < S["special"][0]
    show(["flash red"], siren and beat_on, f)
    show(["flash blue"], siren and not beat_on, f)

    # ---- Cap and shadow bits with their own timing
    cap_up = 0.0
    if v >= C["shock"]:
        u = (v - C["shock"]) / 0.55
        cap_up = 0.9 * 4 * u * (1 - u) if u < 1 else 0.0
    K(OB["cop_cap"], "location", (0, 0, max(cap_up, 0)), f)
    K(OB["cop_cap"], "rotation_euler", rad(0, 0, 720 * min((v - C["shock"]) / 0.55, 1) if v >= C["shock"] else 0), f)
    K(OB["cop_cap"], "hide_render", v >= C["shock"] + 0.55, f)

    if in_shot("ride"):
        x = 0.5 + 5 * v
        z = 0.0
        y = 0.0
        yaw = 0.0
        pose = PUSH if v < 0.5 and int(v * 4) % 2 == 0 else RIDE
        ground = 0.035
        board_rot = (0, 0, 0)
        lift = 0.0
        if C["ollie"] - 0.16 <= v < C["ollie"]:
            pose = CROUCH
        elif C["ollie"] <= v < C["land_ledge"]:
            u = phase(v, C["ollie"], C["land_ledge"])
            z = arc(v, C["ollie"], C["land_ledge"], 0.035, 0.5, 0.85)
            pose = OLLIE
            board_rot = (360 * clamp(u / 0.8), 0, 0)
            lift = 0.5 * math.sin(math.pi * u)
        elif C["land_ledge"] <= v < C["ledge_exit"]:
            z, ground = 0.5, 0.5
            pose = GRIND
            spark_n = 9
        elif C["ledge_exit"] <= v < C["ledge_exit"] + 0.42:
            z = arc(v, C["ledge_exit"], C["ledge_exit"] + 0.42, 0.5, 0.035, 0.5)
            pose = OLLIE
        elif v >= C["car_stop"]:
            # powerslide to a stop on "parar"
            u = phase(v, C["car_stop"], S["ride"][1])
            x = 0.5 + 5 * C["car_stop"] + 3.0 * (1 - (1 - u) ** 2)
            yaw = -75 * clamp(u * 3)
            pose = CROUCH
        put("P1", f, (x, y, z), yaw=yaw, pose=pose, board_rot=board_rot, lift=lift, ground=ground)
        if spark_n:
            sparks(f, (x - 0.3, 0, 0.5), spark_n, 0.25, 0.3)
            spark_n = 0
            spark_set = True
        put_cam(f, (x - 3.0, y - 2.0, 1.05 + z * 0.5), (x + 3.0, y + 0.9, 1.0 + z * 0.5), 24)

    elif in_shot("cpf"):
        put("P1", f, (20.0, 0, 0.035), yaw=90, pose=HANDS_UP, board_loc=(3.4, 0, DECK_Z), board=True)
        u = phase(v, *S["cpf"])
        for ch, cue, dx in (("C", "cpf_c", -0.38), ("P", "cpf_p", 0.0), ("F", "cpf_f", 0.38)):
            if v >= C[cue]:
                letters[ch] = (20.3 + dx, -0.15, 2.0 + 0.04 * math.sin(v * 12), 22 * math.sin((v - C[cue]) * 9))
        put_cam(f, (20.65, -2.75 + u * 0.3, 0.5), (20.65, 0, 1.28), 24)

    elif in_shot("celular"):
        u = phase(v, *S["celular"])
        reach = C["phone_given"] - 0.3
        pose = HAND_OUT if v >= reach else HANDS_UP
        put("P1", f, (20.0, 0, 0.035), yaw=90, pose=pose, board_loc=(3.4, 0, DECK_Z))
        phone_s = v >= reach and v < C["phone_given"] + 0.2
        phone_c = v >= C["phone_given"] + 0.2
        put_cam(f, (18.55 + u * 0.15, -1.3, 1.4), (21.0, 0.15, 1.12), 26)

    elif in_shot("galeria"):
        put("P1", f, (18.9, 0, 0.035), yaw=90, pose=STAND, board_loc=(3.4, 0, DECK_Z))  # behind the close-up camera
        u = phase(v, S["galeria"][0], C["shock"])
        phone_c = True
        light = 2.2 + 0.9 * random.Random(f // 3).random()
        if v < C["shock"]:
            put_cam(f, (20.2 + u * 0.15, -0.12, 1.3), (21.35, 0.1, 1.33), 24)
        else:
            s = phase(v, C["shock"], C["shock"] + 0.12)
            mouth = True
            bang = True
            light = 4.5
            put_cam(f, (20.42 + s * 0.15, 0.03, 1.42), (21.35, 0.09, 1.56), 26, shake=0.012 * (1 - phase(v, C["shock"], C["shock"] + 0.6)))

    elif in_shot("bail"):
        a = S["bail"][0]
        x = 19.0 - 4.0 * (v - a)
        y = -2.5
        trip = C["slam"] - 0.52
        if v < trip:
            pose = PUSH if int((v - a) * 3) % 2 == 0 else RIDE
            put("P1", f, (x, y, 0.035), yaw=180, pose=pose)
            put_cam(f, (x + 3.0, y + 2.0, 1.05), (x - 3, y - 0.9, 1.0), 24)
        elif v < C["slam"]:
            u = phase(v, trip, C["slam"])
            z = arc(v, trip, C["slam"], 0.035, 0.035, 1.1)
            put("P1", f, (x, y, z), yaw=180, pitch=-400 * u, pose=BAIL_A, board=False)
            put_cam(f, (x + 3.0, y + 2.0, 1.05), (x - 3, y - 0.9, 1.0 + z * 0.4), 24)
        else:
            # Everything flies apart; the camera holds, low, as the pool spreads
            p1_parts_on, pieces_on = False, True
            xs = SLAM_POS.x
            put("P1", f, FAR, pose=STAND, board=False)
            put_cam(f, (xs + 3.8, y + 3.4, 2.0), (xs, y, 0.5), 24, shake=0.03 * (1 - phase(v, SLAM, SLAM + 0.35)))

    elif in_shot("goonar"):
        a = S["goonar"][0]
        x = 16.5 + 3.4 * (v - a)
        z, pose, board_rot, lift = 0.035, RIDE, (0, 0, 0), 0.0
        if v < C["goon_up"] - 0.5:
            pose = PUSH if int((v - a) * 4) % 2 == 0 else RIDE
        elif v < C["goon_up"]:
            pose = CROUCH
        elif v < C["goon_down"]:
            u = phase(v, C["goon_up"], C["goon_down"])
            z = arc(v, C["goon_up"], C["goon_down"], 0.035, 0.035, 3.3)
            pose = GRAB if 0.25 < u < 0.8 else OLLIE
            board_rot = (720 * clamp(u / 0.25), 0, 0) if u < 0.25 else (0, 0, 0)
            lift = 0.7 * math.sin(math.pi * u)
        put("P1", f, (x, 0, z), pose=pose, board_rot=board_rot, lift=lift)
        put_cam(f, (x - 3.0, -2.2, 1.05 + z * 0.55), (x + 3.0, 0.9, 1.0 + z * 0.85), 24)

    elif in_shot("devolve"):
        u = phase(v, *S["devolve"])
        if v < C["confiscate"]:
            x = 16.5 + 3.4 * (v - S["goonar"][0])
            put("P1", f, (x, 0, 0.035), pose=CROUCH)
        else:
            nod = math.sin(v * 2 * math.pi / (BEAT * 2))
            pose = dict(PLEAD)
            pose["head"] = (-14 + 12 * nod, 0, 0)
            put("P1", f, (26.2, 0, 0.035), yaw=90, pose=pose, board=False)
            held_board = True
        put_cam(f, (26.6 + u * 0.1, -3.05, 0.7), (26.75, 0, 1.3), 26)

    elif in_shot("player2"):
        pose = dict(PLEAD)
        if v >= C["reboard"]:
            put("P1", f, (26.2, 0, 0.035), pose=RIDE)
        else:
            put("P1", f, (26.2, 0, 0.035), yaw=90, pose=pose, board=False)
        held_board = v < C["p2_hit"]
        hit = C["p2_hit"]
        quake = 0.05 * (1 - phase(v, hit, hit + 0.4)) if v >= hit else 0.0
        put_cam(f, (25.2, -6.2, 1.3), (26.75, 0, 1.95), 24, shake=quake)

    elif in_shot("special"):
        a, enter, launch, held, end = S["special"][0], C["qp_enter"], C["launch"], C["held_note"], S["special"][1]
        speed = (74 - 56) / (enter - a)
        if v < enter:
            x, z, pitch, yaw, spin = 56 + (v - a) * speed, 0.035, 0.0, 0.0, 0.0
            pose = PUSH if int((v - a) * 5) % 2 == 0 else RIDE
        elif v < launch:
            ang = math.radians(88) * phase(v, enter, launch)
            x, z = 74 + 3.5 * math.sin(ang), 0.035 + 3.5 * (1 - math.cos(ang))
            pitch, yaw, spin = -math.degrees(ang), 0.0, 0.0
            pose = CROUCH
        else:
            p = phase(v, launch, end)
            x = 77.5 + 0.6 * p
            z = 3.53 + 11.5 * (1 - (1 - p) ** 3)
            pitch = -88 * (1 - clamp((v - launch) / 0.28))
            yaw = 1260 * (1 - (1 - p) ** 2.4)
            pose = SPECIAL if v >= held - 0.3 else OLLIE
            spin = (v - launch) * 200
        lift = 0.55 if v >= launch else 0.0
        put("P1", f, (x, -1.5, z), yaw=yaw, pitch=pitch, pose=pose, board_rot=(spin, 0, 0), lift=lift)
        z2 = max(z - 1.3, 0.035) if v >= launch else z
        put("P2", f, (x, 1.5, z2), yaw=-yaw, pitch=pitch, pose=pose, board_rot=(-spin, 0, 0), lift=lift)
        if v < launch:
            put_cam(f, (x - 5.2, -5.0, 2.1), (x + 2.2, 0, 1.2 + z * 0.7), 24)
        elif v < held:
            put_cam(f, (71.0, -6.5, z * 0.45 + 1.2), (77.6, 0, z + 0.3), 24)
        else:
            ang = math.radians(-125 + (v - held) * 48)
            cx, cz = x, z - 0.3
            put_cam(f, (cx + 6.2 * math.cos(ang), 6.2 * math.sin(ang), cz - 1.4), (cx, 0, cz + 0.2), 24)

    elif in_shot("banana"):
        put("P1", f, FAR, pose=STAND, board=False)
        phone_g = True
        put_cam(f, (65.5, -1.68, 0.42), (66.02, -0.95, 0.12), 26, shake=0.012 if v >= C["phone_dies"] and v < C["phone_dies"] + 0.3 else 0)
        if v >= C["sparks"]:
            spark_n = 16 if v >= C["phone_dies"] else 6

    # ---- Where the shots above don't place P1 or P2 they stay put; park P2 until the flash
    if not in_shot("special"):
        if in_shot("player2") and v >= C["p2_flash"]:
            hit = C["p2_hit"]
            if v < hit + 0.06:
                z = 15 * (1 - phase(v, C["p2_flash"], hit)) + 1.1 * (1 - phase(v, hit, hit + 0.06))
                put("P2", f, (27.4, 0, z), pose=GRAB)
            else:
                put("P2", f, (27.4, 0, 0.035), pose=RIDE)
        else:
            put("P2", f, FAR, pose=STAND, board=False)

    # ---- Cop placement per shot
    if v < S["cpf"][0]:
        put_cop(f, FAR, 0, COP_STAND)
    elif v < S["goonar"][0]:
        pose = COP_DEMAND if v < C["phone_given"] + 0.2 else (COP_PHONE if v < C["shock"] else COP_SHOCK)
        put_cop(f, (21.35, 0, 0), -90, pose)
    elif v < S["player2"][0] or (in_shot("player2") and v < C["p2_hit"]):
        pose = COP_STAND if v < C["confiscate"] else COP_OVERHEAD
        put_cop(f, (27.4, 0, 0), -90, pose)
    elif in_shot("player2"):
        put_cop(f, (27.75, 0, 0.14), -90, COP_FLAT, pitch=-90, scale=(1, 1, 0.5))
    elif v < S["special"][0]:
        put_cop(f, FAR, 0, COP_STAND)
    else:
        put_cop(f, FAR, 0, COP_STAND)

    # ---- Pieces and the rig visibility
    if pieces_on:
        reform = phase(v, HOLD_END, C["reassemble"])
        i = min(int((v - SLAM) / dt), steps - 1)
        for c in P1_PARTS:
            start_pos, rot0, seq = TRAJ[c.name]
            p, r = seq[i]
            piece = OB["piece " + c.name]
            K(piece, "location", p.lerp(start_pos, reform), f)
            K(piece, "rotation_euler", r.lerp(rot0, reform), f)
    for c in P1_PARTS:
        K(c, "hide_render", not p1_parts_on, f)
        K(OB["piece " + c.name], "hide_render", not pieces_on, f)

    # ---- Props
    show(["phone smurf"], phone_s, f)
    show(["phone cop"], phone_c, f)
    show(["phone ground"], phone_g, f)
    show(["board held"], held_board, f)
    for ch in "CPF":
        ob = OB["letter " + ch]
        if letters[ch]:
            x, y, z, spin = letters[ch]
            K(ob, "location", (x, y, z), f)
            K(ob, "rotation_euler", rad(90, 0, spin), f)
        K(ob, "hide_render", not letters[ch], f)
    K(OB["bang"], "location", (21.3, -0.12, 1.84 + 0.02 * math.sin(v * 30)), f)
    K(OB["bang"], "rotation_euler", rad(0, 0, 90), f)
    # The phone in his hand, back to camera: the lit face points at him
    if (f - 1) % 2 == 0:  # steps with his pose
        phone_at = PHONE_SHOCK if v >= C["shock"] else PHONE_HOLD
        K(OB["phone cop"], "location", phone_at, f)
    show(["bang"], bang, f)
    show(["cop_mouth"], mouth, f)

    K(glow, "location", (21.35 + phone_at.y + 0.08, -phone_at.x, phone_at.z), f)  # just off the lit face, in world space
    K(glow.data, "energy", light * 3, f)

    show(["P2_marker"], in_shot("player2") or in_shot("special"), f)

    # Blood stays down for the shot
    if in_shot("bail") and v >= SLAM:
        s = phase(v, SLAM, SLAM + 0.75) * 0.95
        K(OB["blood"], "location", (SLAM_POS.x, SLAM_POS.y, 0.036), f)
        K(OB["blood"], "scale", (s, s, 1), f)
        K(OB["blood"], "hide_render", v >= HOLD_END + 0.1, f)
    else:
        K(OB["blood"], "hide_render", True, f)

    # Sparks: the grind sets them in the ride shot, the finale here
    if in_shot("banana"):
        if spark_n:
            sparks(f, (66, -1, 0.08), spark_n, 0.22 if spark_n < 16 else 0.4, 0.25 if spark_n < 16 else 0.5)
        else:
            sparks(f, (0, 0, 0), 0)
    elif not (in_shot("ride") and C["land_ledge"] <= v < C["ledge_exit"]):
        sparks(f, (0, 0, 0), 0)

    # ---- Banana split: falls, lands with a squash
    split = OB["banana split"]
    if in_shot("banana") and v >= C["banana_land"] - 0.42:
        land = C["banana_land"]
        if v < land:
            u = phase(v, land - 0.42, land)
            K(split, "location", (66, -0.98, 2.2 * (1 - u * u) + 0.08), f)
            K(split, "scale", (1.5, 1.5, 1.5), f)
        else:
            k = phase(v, land, land + 0.2)
            sq = 1 - 0.45 * math.sin(k * math.pi) * (1 - k)
            K(split, "location", (66, -0.98, 0.08), f)
            K(split, "scale", (1.5 * (2 - sq), 1.5 * (2 - sq), 1.5 * sq), f)
        K(split, "rotation_euler", rad(0, 0, 25), f)
        K(split, "hide_render", False, f)
    else:
        K(split, "hide_render", True, f)
        K(split, "location", FAR, f)

    # ---- Olive oil: bottle tips in from above and pours until the phone dies
    bottle, stream = OB["oil bottle"], OB["oil stream"]
    if in_shot("banana") and C["oil_on"] <= v < C["phone_dies"] + 0.25:
        u = phase(v, C["oil_on"], C["oil_on"] + 0.2)
        K(bottle, "location", (66.42, -0.98, 0.76 + 1.2 * (1 - u)), f)
        K(bottle, "rotation_euler", rad(0, -125 * u, 0), f)
        K(bottle, "hide_render", False, f)
        pouring = u >= 1
        K(stream, "location", (66.01, -0.98, 0.475), f)
        K(stream, "scale", (1.6, 1.6, 0.33 + 0.02 * math.sin(v * 40)), f)
        K(stream, "hide_render", not pouring, f)
    else:
        K(bottle, "location", FAR, f)
        K(bottle, "hide_render", True, f)
        K(stream, "hide_render", True, f)

prefs.keyframe_new_interpolation_type = prev_interp

# The preference above doesn't reach keys inserted from a script, so force it on every key
keys = 0
for a in bpy.data.actions:
    for layer in a.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for fc in bag.fcurves:
                    for kp in fc.keyframe_points:
                        kp.interpolation = "CONSTANT"
                        keys += 1
                    fc.update()
print("constant keys:", keys)
sc.frame_set(1)
bpy.ops.wm.save_mainfile()
print("shots keyed:", FRAMES, "frames,", len(last), "keyed channels")
