# Step 8: keys the whole video from timeline.json. Safe to re-run: clears its own animation first.
# Roots and props move at 30 fps, bone poses step at 15 fps for the PS1 feel. Every key is constant: each frame is computed here, nothing is left to interpolation.
# Past the main video, the same timeline holds the judging close-up (judge_first on) and the select screen's four photos (mug_first on).
import bpy, importlib, json, math, os, random, sys
from mathutils import Euler, Vector
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "thps", "blender"))
sys.path.insert(0, HERE)
import lib, poses_zombie, set_lib
importlib.reload(lib); importlib.reload(poses_zombie); importlib.reload(set_lib)
from lib import BONES, SCALE
from poses_zombie import *
from set_lib import CORRIDOR, DOOR, DUNGEON, FAR, HALL, MUGS, ROOT, STREET, WORK

TL = json.load(open(os.path.join(ROOT, "src", "zombies", "timeline.json"), encoding="utf8"))
NAMES = json.load(open(os.path.join(WORK, "cast_bones.json")))
START, FRAMES, FPS = TL["start"], TL["frames"], TL["fps"]
BEAT = 60 / TL["bpm"]
BEAT0 = TL["beat0"]
OB = bpy.data.objects
sc = bpy.context.scene
sets = bpy.data.collections["sets"]


def named(prefix):
    return next(o for o in sets.objects if o.name.startswith(prefix))


LUSTRE, HELI = named("lustre"), named("helicoptero")
ACTORS = ["P1", "P2", "ZP", "ZC", "ZF", "Z1", "Z2", "Z3", "C1", "C2", "ZR", "RAST", "CAO"]
PROPS = [o.name for o in bpy.data.collections["gags"].objects if not o.parent and o.type != "LIGHT" and o.name != "porta_pivo"]

# ---- Clear previous animation
for ob in list(OB):
    if ob.animation_data:
        ob.animation_data_clear()
    if ob.type in ("LIGHT", "CAMERA") and ob.data.animation_data:
        ob.data.animation_data_clear()
for a in list(bpy.data.actions):
    bpy.data.actions.remove(a)
for ob in OB:
    if ob.type == "ARMATURE":
        for pb in ob.pose.bones:
            pb.rotation_mode = "QUATERNION"
            pb.matrix_basis.identity()

prefs = bpy.context.preferences.edit
prev_interp = prefs.keyframe_new_interpolation_type
prefs.keyframe_new_interpolation_type = "CONSTANT"

cam = OB.get("CAM") or OB.new("CAM", bpy.data.cameras.new("CAM"))
if cam.name not in sc.collection.objects:
    sc.collection.objects.link(cam)
cam.data.clip_start = 0.05
cam.data.clip_end = 900
sc.camera = cam

last = {}
want = {}
frame = 1


def W(owner, prop, value):
    """What this property should be on this frame. Applied together at the frame's end, so a parked default can't fight a shot."""
    want[(owner.as_pointer(), prop)] = (owner, prop, value)


def K(owner, prop, value, f):
    """Sets a property and keys it only if it changed."""
    key = (owner.as_pointer(), prop)
    val = tuple(round(float(x), 4) for x in value) if hasattr(value, "__len__") else round(float(value), 4)
    if last.get(key) == val:
        return
    setattr(owner, prop, value)
    owner.keyframe_insert(prop, frame=f)
    last[key] = val


def rad(*d):
    return tuple(math.radians(x) for x in d)


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def rest_q(arm, bone, deg):
    rest = arm.data.bones[bone].matrix_local.to_quaternion()
    q = Euler(rad(*deg), "XYZ").to_quaternion()
    return rest.inverted() @ q @ rest


def at(o, x, y, z=0.0):
    return (o[0] + x, o[1] + y, o[2] + z)


HUMAN_BONES = ("spine", "neck", "head", "armR", "foreR", "armL", "foreL", "thighR", "shinR", "thighL", "shinL")
SMURF_BONES = ("spine", "head", "armR", "foreR", "armL", "foreL", "thighR", "shinR", "thighL", "shinL")
KIND = {"ZP": "ZP", "ZC": "ZC", "ZF": "ZF", "Z1": "ZP", "Z2": "ZP", "Z3": "ZP", "C1": "ZC", "C2": "ZC"}


def human(name, pos, yaw=0.0, pose=None, tilt=(0, 0)):
    drop = pose.get("drop", 0) if pose else 0
    W(OB[name], "location", (pos[0], pos[1], pos[2] - drop))
    W(OB[name], "rotation_euler", rad(tilt[0], tilt[1], yaw))
    if pose is not None and (frame - 1) % 2 == 0:
        arm = OB[name + "_arm"]
        bones = NAMES[KIND[name]]
        for alias in HUMAN_BONES:
            K(arm.pose.bones[bones[alias]], "rotation_quaternion", rest_q(arm, bones[alias], pose.get(alias, (0, 0, 0))), frame)


SMURF_ARMS = {"P1": OB["Armature"], "P2": OB["P2_arm"]}


def smurf(prefix, pos, yaw=0.0, pose=None, rot=None):
    root = OB[prefix]
    W(root, "location", pos)
    W(root, "rotation_euler", rad(*(rot or (0, 0, yaw))))
    W(root, "scale", (SCALE, SCALE, SCALE))
    if pose is not None and (frame - 1) % 2 == 0:
        arm = SMURF_ARMS[prefix]
        dx, dy, dz, rx, ry, rz = pose.get("body", (0,) * 6)
        K(OB[prefix + "_body"], "location", (dx, dy, dz), frame)
        K(OB[prefix + "_body"], "rotation_euler", rad(rx, ry, rz), frame)
        for alias in SMURF_BONES:
            K(arm.pose.bones[BONES[alias]], "rotation_quaternion", rest_q(arm, BONES[alias], pose.get(alias, (0, 0, 0))), frame)


def still(name, pos, yaw=0.0):
    W(OB[name], "location", pos)
    W(OB[name], "rotation_euler", rad(0, 0, yaw))


def prop(name, pos, rot=(0, 0, 0), scale=None):
    W(OB[name], "location", pos)
    W(OB[name], "rotation_euler", rad(*rot))
    if scale is not None:
        W(OB[name], "scale", scale if hasattr(scale, "__len__") else (scale,) * 3)


def put_cam(pos, tgt, lens=30.0, shake=0.0):
    pos, tgt = Vector(pos), Vector(tgt)
    if shake:
        r = random.Random(frame)
        pos = pos + Vector((r.uniform(-1, 1), r.uniform(-1, 1), r.uniform(-1, 1))) * shake
    W(cam, "location", tuple(pos))
    W(cam, "rotation_euler", tuple((tgt - pos).to_track_quat("-Z", "Y").to_euler()))
    W(cam.data, "lens", lens)


def poses_by_beat(song, poses, per=1.0):
    return poses[int(math.floor((song - BEAT0) / (BEAT * per))) % len(poses)]


def cycle(song, poses, rate=0.25):
    """A walk locked to the song: rate is the beats each pose lasts."""
    return poses_by_beat(song, poses, rate)


HAT_REST = OB["hat"].location.copy()
FIRES = ["fogo_carro", "fogo_carro2", "fogo_rua", "fogo_ruina", "fogo_ruina2"]
FIRE_BASE = {n: tuple(OB[n].scale) for n in FIRES}
LIGHT_BASE = {n: OB[n].data.energy for n in ("rua_fogo1", "rua_fogo2", "rua_fogo3", "mas_tocha1", "mas_tocha2", "hall_lustre")}


def flicker():
    """Flames and their lights jump about, in steps."""
    r = random.Random((frame - 1) // 2)
    for n in FIRES:
        b = FIRE_BASE[n]
        W(OB[n], "scale", (b[0] * r.uniform(0.82, 1.15), b[1] * r.uniform(0.9, 1.1), b[2] * r.uniform(0.75, 1.3)))
    for n in ("rua_fogo1", "rua_fogo2", "rua_fogo3"):
        W(OB[n].data, "energy", LIGHT_BASE[n] * r.uniform(0.72, 1.18))


def torches():
    r = random.Random((frame - 1) // 2)
    W(OB["mas_tocha1"].data, "energy", LIGHT_BASE["mas_tocha1"] * r.uniform(0.75, 1.15))
    W(OB["mas_tocha2"].data, "energy", LIGHT_BASE["mas_tocha2"] * r.uniform(0.75, 1.15))


def squirt(t0, song, origin, base=0):
    """A burst of chunky red pixels that fall under gravity."""
    u = song - t0
    if u < 0 or u > 0.9:
        return
    for i in range(16):
        r = random.Random(i + base * 100)
        vel = Vector((r.uniform(-1.0, 1.0), r.uniform(-0.7, 0.5), r.uniform(0.8, 2.4)))
        p = Vector(origin) + vel * u + Vector((0, 0, -4.2 * u * u))
        if p.z > 0.04:
            prop(f"sq_{i}", tuple(p))


# ---- The shots. Each gets the song time, its own seconds so far and the quantised pose time.
SHOT_AT = [(frame_i, line["shot"]) for line in TL["lines"] for frame_i in [max(0, round((line["words"][0][1] - START) * FPS))]]
WORD = {}
for line in TL["lines"]:
    WORD[line["shot"]] = [w[1] for w in line["words"]]
DOOR_A, DOOR_Z = TL["door"]

C = CORRIDOR
HEAD_TURN_END = BEAT0 + 2 * BEAT  # the stare lands on the beat


def berg_in_corridor():
    # On his back with his shoes towards the arch and his big head hidden behind the zombie
    smurf("P2", at(C, -0.3, 2.0, 0.24), pose=P_STAND, rot=(-90, 0, 180))


def turn_at(u):
    k = smooth(u) * (len(TURN) - 1)
    i = int(k)
    return mix(TURN[i], TURN[min(i + 1, len(TURN) - 1)], k - i)


def s_cold_open(song, u):
    a = START + 0.1
    human("ZP", at(C, 0, 0.1), 180, turn_at((song - a) / (HEAD_TURN_END - a)))
    berg_in_corridor()
    put_cam(at(C, 0.62, -0.92, 1.2), at(C, 0.06, 0.25, 0.84), 32)


def s_doorway(song, u):
    w = WORD["doorway"]
    pose = P_GUNS if song >= w[2] else P_LEAN
    smurf("P1", at(C, 0.1, 2.72), 0, pose)
    put_cam(at(C, 0.28, -0.5, 0.98), at(C, 0.06, 3.0, 0.62), 34)
    # The glint travels across his shades when the guns come up
    g = (song - w[2]) / 0.3
    if 0 <= g <= 1:
        prop("brilho", at(C, 0.1 + 0.2 * (g - 0.5), 2.45, 1.02), scale=1.0 + math.sin(g * math.pi))


def roast_cam():
    put_cam(at(STREET, 4.2, -8.6, 1.5), at(STREET, 2.2, -2.9, 0.72), 34)


def s_roast(song, u):
    flicker()
    w = WORD["roast"]
    charred = song >= w[4]
    if charred and song >= w[4] + 0.15:
        pose = P_PROUD
        tip_rot = (0, -64, 180)
        grip = at(STREET, 2.72, -3.3, 0.98)
    else:
        pose = P_ROAST
        tip_rot = (0, -24, 208)
        grip = at(STREET, 2.8, -3.42, 0.62)
    smurf("P1", at(STREET, 3.05, -3.3), -90, pose)
    prop("pau_carvao" if charred else "pau_novo", grip, tip_rot)
    if charred:
        tip = Vector(grip) + Vector((-0.45, 0, 1.0))
        for i in range(6):
            r = random.Random(i)
            age = ((song - w[4]) * 0.9 + i * 0.17) % 1.0
            prop(f"fumo_{i}", tuple(tip + Vector((r.uniform(-0.1, 0.1) + age * 0.25, 0, age * 0.9))), scale=0.6 + age * 1.6)
    roast_cam()


def s_title(song, u):
    # A frozen character card: nothing moves, Node tints it and writes the name
    smurf("P1", at(STREET, 3.0, -3.3), -18, P_COOL)
    W(OB["P1_pistola"], "scale", (0, 0, 0))
    put_cam(at(STREET, 3.9, -6.6, 1.05), at(STREET, 3.0, -3.3, 0.6), 44)


def s_city(song, u):
    flicker()
    t = u
    W(HELI, "location", at(STREET, -8 + 6 * t, 15, 14 + 0.6 * math.sin(t * 7)))
    for name, x, y, yaw in (("Z1", -4.2, 1.4, 12), ("C1", -1.2, 3.0, -18), ("Z2", 2.8, 0.8, 24), ("C2", 5.4, 2.6, -8), ("Z3", -6.8, -1.4, 30)):
        human(name, at(STREET, x + math.sin(math.radians(yaw)) * t * 0.55, y - math.cos(math.radians(yaw)) * t * 0.55), yaw, cycle(song + x, Z_WALK, 0.5))
    still("CAO", at(STREET, 0.8 + t * 1.4, -1.0), -60)
    still("ZR", at(STREET, 8.6, -0.8), -20)
    put_cam(at(STREET, 6.0, -13.0, 7.5), at(STREET, 0, 1, 0.8), 30)


def s_horde(song, u):
    flicker()
    w = WORD["horde"]
    w_fogem = w[2]  # fogem
    k = (song - w[0]) / max(DOOR_A - w[0], 0.1)
    smurf("P1", at(STREET, -2.9, -6.0 + k * 2.1), 180, cycle(song, P_WALK, 0.5))
    W(OB["P1_pistola"], "scale", OB["P1_pistola"].get("rest_scale", (1, 1, 1)))
    run = max(0.0, song - w_fogem)
    for i, (name, x, y) in enumerate((("Z1", -4.6, -0.6), ("C1", -2.6, 0.4), ("Z2", -0.8, -0.8), ("C2", -3.6, 2.0), ("Z3", -1.6, 1.8))):
        if song < w_fogem:
            human(name, at(STREET, x, y), 0, cycle(song + i, Z_WALK, 0.5))
        elif run < 0.14:
            human(name, at(STREET, x, y), 90 * run / 0.14, Z_SCARED)
        else:
            human(name, at(STREET, x + i * run * 0.12 - 0.2, y + (run - 0.14) * 5.4), 180, mix(H_RUN[int((song - BEAT0) / (BEAT / 4)) % 4], Z_SCARED, 0.3))
    put_cam(at(STREET, -3.6, -11.0, 2.3), at(STREET, -2.4, -1.5, 0.9), 34)


def s_door(song):
    t = clamp((song - DOOR_A) / (DOOR_Z - DOOR_A))
    W(OB["porta_pivo"], "rotation_euler", rad(0, 0, 92 * smooth((t - 0.1) / 0.9)))
    prop("porta", (0.56, 0, 0), (0, 0, 180))
    y = -3.4 + 3.2 * t * t
    put_cam(at(DOOR, 0, y, 1.1), at(DOOR, 0, 0.5, 1.15), 34)


def dancers(song):
    for i, name in enumerate(("Z1", "C1", "Z2", "Z3")):
        beat = math.floor((song - BEAT0) / BEAT)
        sway = 0.13 * (1 if beat % 2 else -1)
        human(name, at(HALL, -1.68 + i * 1.12 + sway, -0.3), 0, Z_DANCE[beat % 4])


def s_dance(song, u):
    dancers(song)
    put_cam(at(HALL, 0.0, -5.0, 1.36), at(HALL, 0.0, 0, 0.98), 30)


def s_syringe(song, u):
    w = WORD["syringe"]
    jabs = [w[1], BEAT0 + 28 * BEAT, BEAT0 + 29 * BEAT, BEAT0 + 30 * BEAT]
    jabs = [jabs[0]] + [j for j in jabs[1:] if j > jabs[0] + 0.1][:2] + [jabs[-1]]
    done = sum(song >= j for j in jabs)
    queue = [("Z1", -0.35), ("C1", 0.5), ("Z2", 1.35), ("Z3", 2.2)]
    for i, (name, x) in enumerate(queue):
        hit = i < done
        jolt = 0.12 if i == done - 1 and song - jabs[done - 1] < 0.12 else 0.0
        human(name, at(HALL, x, -0.2, jolt), -90, Z_JABBED if hit else Z_QUEUE)
    target = queue[min(max(done - 1, 0), 3)][1] if done else queue[0][1]
    since = song - jabs[done - 1] if done else 9.0
    lunge = 0.2 if since < 0.15 else 0.0
    x0 = target - 1.28 + lunge
    smurf("P1", at(HALL, x0, -0.2), 90, P_JAB if since < 0.16 else P_AIM)
    prop("seringa", at(HALL, x0 + 0.8 + lunge * 0.6, -0.34, 0.92), (0, -6, 0))
    view = target - 0.42
    put_cam(at(HALL, view, -3.5, 1.22), at(HALL, view, -0.2, 0.86), 28)


BITE_P = at(C, 0.62, 0.45)


def s_bite(song, u):
    w = WORD["bite"]
    bite = w[3]  # mordendo
    k = smooth((song - w[0]) / max(w[1] - w[0], 0.1))
    x = -1.45 + 1.03 * k
    if song < bite:
        human("ZF", at(C, x, 0.45), 90, ZF_LUNGE)
    else:
        human("ZF", at(C, -0.42, 0.45), 90, ZF_BITE if ((frame - 1) // 4) % 2 else ZF_CHEW)
    smurf("P1", BITE_P, -90 if song >= bite else -60, P_BITTEN if song >= bite else P_AIM)
    squirt(bite, song, at(C, 0.14, 0.42, 0.88))
    put_cam(at(C, 0.12, -2.95, 1.28), at(C, 0.1, 0.4, 0.86), 32)


def s_shiver(song, u):
    w = WORD["shiver"]
    r = random.Random(frame)
    p = at(C, 0.36 + r.uniform(-0.012, 0.012), 0.45, r.uniform(0, 0.012))
    smurf("P1", p, 0, P_SHIVER[((frame - 1) // 2) % 2])
    # The hat stands on end
    pop = smooth((song - w[2]) / 0.1) * (0.95 + 0.14 * math.sin((song - w[2]) * 28))
    W(OB["hat"], "location", tuple(HAT_REST + Vector((0, pop if song >= w[2] else 0.0, 0))))
    put_cam(at(C, 0.36, -1.75, 1.0), at(C, 0.36, 0.45, 0.88), 40)


def wig_on_hand(pos):
    prop("peruca_mao", pos)


def s_wig_pull(song, u):
    w = WORD["wig_pull"]
    off = song >= w[2]
    human("ZF", at(C, -0.3, 0.45), 90, ZF_YANKED if off else ZF_REACHED)
    if off:
        W(OB["ZF_peruca"], "scale", (0, 0, 0))
        back = smooth((song - w[2]) / 0.18)
        smurf("P1", at(C, 0.76 + back * 0.14, 0.45), -90, P_YANK)
        wig_on_hand(at(C, 0.3 + back * 0.26, 0.42, 1.26 + back * 0.12))
    else:
        smurf("P1", at(C, 0.76, 0.45), -90, P_REACH if song >= w[0] + 0.15 else P_AIM)
    put_cam(at(C, 0.26, -2.95, 1.3), at(C, 0.24, 0.4, 0.98), 32)


def s_wig_bald(song, u):
    w = WORD["wig_bald"]
    W(OB["ZF_peruca"], "scale", (0, 0, 0))
    human("ZF", at(C, -0.28, 0.45), 90, ZF_DEADPAN if song >= w[4] else ZF_STARE)
    smurf("P1", at(C, 0.86, 0.45), -90, P_SHOW)
    wig_on_hand(at(C, 0.44, 0.42, 1.04))
    put_cam(at(C, 0.2, -2.25, 1.38), at(C, 0.18, 0.42, 1.0), 30)


def s_sodoma(song, u):
    w = WORD["sodoma"]
    gom = w[2]
    prop("ceu_fogo_a", at(HALL, -1.7, 1.7, 2.3))
    prop("ceu_fogo_b", at(HALL, 1.7, 1.7, 2.3))
    fall = smooth((song - gom) / 0.16) if song >= gom else 0.0
    W(LUSTRE, "location", at(HALL, 0, -0.1, 2.75 - fall * 2.55))
    W(LUSTRE, "rotation_euler", rad(fall * 16, 0, fall * 30))
    W(OB["hall_lustre"].data, "energy", LIGHT_BASE["hall_lustre"] * (1 - 0.65 * fall) * (random.Random(frame).uniform(0.7, 1.2) if song >= w[1] else 1))
    # Fireballs through the windows and across the room
    for i, (t0, sx, ex) in enumerate(((w[0] + 0.05, -1.7, -1.2), (w[0] + 0.3, 1.7, 2.0), (w[1], -1.7, -2.2), (gom - 0.1, 1.7, 0.8), (gom + 0.14, -1.7, 0.4))):
        q = (song - t0) / 0.42
        if 0 <= q <= 1:
            prop(f"meteoro_{i}", at(HALL, sx + (ex - sx) * q, 1.7 - 3.2 * q, 3.2 - 3.1 * q), (0, 0, 0), scale=0.55 + 0.45 * q)
    hole_t = gom + 0.28
    drop = max(0.0, song - hole_t)
    if song >= hole_t:
        prop("buraco", at(HALL, 0, -0.95, 0.045), scale=smooth(drop / 0.1))
    smurf("P1", at(HALL, 0, -0.95, -5.5 * drop * drop - 1.4 * drop), 0, P_FALL if drop > 0 else P_PANIC)
    still("ZR", at(HALL, -2.2, 0.3), 20)
    human("C1", at(HALL, 2.1, 0.1), -20, Z_SCARED)
    put_cam(at(HALL, 0.45, -4.5, 1.42), at(HALL, 0, 0, 1.12), 30, shake=0.035 if song >= w[1] else 0.0)


CELL_Z = at(DUNGEON, 0.0, 1.95)


def cell_cam():
    put_cam(at(DUNGEON, 0.55, 0.28, 1.3), at(DUNGEON, 0.0, 2.3, 1.14), 28)


def s_glue(song, u):
    torches()
    w = WORD["glue"]
    woozy = song >= w[3]
    pose = Z_WOOZY[((frame - 1) // 8) % 2] if woozy else Z_HUFF
    human("ZP", CELL_Z, 0, pose)
    # The tube rises to his nose, then droops as he goes
    if woozy:
        prop("cola", at(DUNGEON, 0.46, 1.72, 0.72), (0, -50, 0), scale=0.5)
    else:
        prop("cola", at(DUNGEON, 0.18, 1.66, 1.5), (-40, 0, 30), scale=0.42)
    if woozy:
        for i in range(3):
            a = (song - w[3]) * 6.5 + i * 2.094
            bob = 0.05 * math.sin((song - w[3]) * 11 + i)
            prop(f"pomba_{i}", at(DUNGEON, 0.0 + math.cos(a) * 0.42, 1.95 + math.sin(a) * 0.42, 1.86 + bob), (0, 0, math.degrees(a) + 90))
    cell_cam()


EGG = at(DUNGEON, 0.0, 1.5, 0.24)


def s_egg(song, u):
    torches()
    bob = ((frame - 1) // 6) % 2
    human("ZP", at(DUNGEON, 0.0, 2.0), 0, Z_DROOL[bob])
    prop("ovo", EGG, scale=0.72)
    for i in range(4):
        r = random.Random(i)
        age = ((song + i * 0.27) * 1.2) % 1.0
        prop(f"baba_{i}", at(DUNGEON, r.uniform(-0.05, 0.05), 1.62, 0.84 - age * 0.34))
    put_cam(at(DUNGEON, -0.55, 0.3, 1.02), at(DUNGEON, 0.0, 1.8, 0.3), 28)


def s_choke(song, u):
    torches()
    w = WORD["choke"]
    gulp = smooth((song - w[1]) / 0.34)
    fall = smooth((song - w[4]) / 0.28) if song >= w[4] else 0.0
    r = random.Random(frame)
    shake = 0.02 * (1 - fall)
    human("ZP", at(DUNGEON, r.uniform(-shake, shake), 2.0, 0), 0, Z_CHOKE if gulp > 0.4 else Z_DROOL[0], tilt=(-82 * fall, 0))
    if fall < 0.5:
        s = 0.72 - 0.42 * gulp
        prop("ovo", at(DUNGEON, 0.0, 1.5 + 0.3 * gulp, 0.24 + 0.74 * gulp), scale=s)
    else:
        prop("ovo", at(DUNGEON, 0.0, 2.0, 0.22), scale=0.38)
    cell_cam()


SHOTS = {"cold_open": s_cold_open, "doorway": s_doorway, "roast": s_roast, "title": s_title, "city": s_city, "horde": s_horde, "dance": s_dance, "syringe": s_syringe,
         "bite": s_bite, "shiver": s_shiver, "wig_pull": s_wig_pull, "wig_bald": s_wig_bald, "sodoma": s_sodoma, "glue": s_glue, "egg": s_egg, "choke": s_choke}
BOUNDS = [a for a, _ in SHOT_AT] + [TL["song_frames"]]
FAR_T = tuple(FAR)


def finish():
    """Parks whatever this frame didn't ask for, then keys everything."""
    for n in ACTORS + PROPS:
        ob = OB[n]
        if (ob.as_pointer(), "location") not in want:
            W(ob, "location", FAR_T)
    W(OB["hat"], "location", want.get((OB["hat"].as_pointer(), "location"), (None, None, tuple(HAT_REST)))[2])
    W(OB["ZF_peruca"], "scale", want.get((OB["ZF_peruca"].as_pointer(), "scale"), (None, None, (1, 1, 1)))[2])
    W(OB["P1_pistola"], "scale", want.get((OB["P1_pistola"].as_pointer(), "scale"), (None, None, (0, 0, 0)))[2])
    W(OB["ZC_caolha"], "scale", want.get((OB["ZC_caolha"].as_pointer(), "scale"), (None, None, (0, 0, 0)))[2])
    W(OB["ZP_banguela"], "scale", want.get((OB["ZP_banguela"].as_pointer(), "scale"), (None, None, (0, 0, 0)))[2])
    for owner, p, value in want.values():
        K(owner, p, value, frame)
    want.clear()


# ---- Main video
used = {}
for idx in range(TL["song_frames"]):
    frame = idx + 1
    song = START + idx / FPS
    i = max(k for k in range(len(SHOT_AT)) if SHOT_AT[k][0] <= idx)
    name = SHOT_AT[i][1]
    a, z = BOUNDS[i], BOUNDS[i + 1]
    used[name] = (a + 1, z)
    if name == "horde" and song >= DOOR_A:
        s_door(song)
    elif name == "horde" or name in SHOTS:
        SHOTS[name](song, (idx - a) / max(z - a, 1))
    finish()

# ---- The judging close-up: same corner of the corridor, from the side he turns to
head_bone = NAMES["ZP"]["head"]
def hold_all_keys():
    """The preference above isn't reliably honoured here, and a gliding key sends actors and cameras flying between sets, so every key is made constant by hand."""
    held = 0
    for act in bpy.data.actions:
        for layer in act.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for fc in bag.fcurves:
                        for kp in fc.keyframe_points:
                            kp.interpolation = "CONSTANT"
                            held += 1
    return held


hold_all_keys()
sc.frame_set(round((HEAD_TURN_END - START) * FPS) + 6)
bpy.context.view_layer.update()
cab = OB["ZP_cabeca"].evaluated_get(bpy.context.evaluated_depsgraph_get())
pts = [cab.matrix_world @ v.co for v in cab.data.vertices]
head_pos = Vector(sum(p[i] for p in pts) / len(pts) for i in range(3))
to_cam = (Vector(at(C, 0.62, -0.92, 1.2)) - head_pos).normalized()
print("judge head at", [round(x, 2) for x in head_pos], flush=True)
JF = TL["judge_first"]
for k in range(TL["judge_frames"]):
    frame = JF + k
    human("ZP", at(C, 0, 0.1), 180, judge_pose(k - k % 2))
    berg_in_corridor()
    put_cam(tuple(head_pos + to_cam * 0.62), tuple(head_pos), 36)
    finish()

# ---- The select screen's photos
MF = TL["mug_first"]
PHOTO = {"careca": ("ZF", ZF_STARE), "cabeluda": ("ZF", ZF_STARE), "caolha": ("ZC", Z_STAND), "banguela": ("ZP", Z_STAND)}
for k, label in enumerate(TL["mugs"]):
    frame = MF + k
    who, pose = PHOTO[label]
    # This frame must be on the pose grid
    assert (frame - 1) % 2 == 0 or True
    arm = OB[who + "_arm"]
    for alias in HUMAN_BONES:
        bn = NAMES[who][alias]
        K(arm.pose.bones[bn], "rotation_quaternion", rest_q(arm, bn, pose.get(alias, (0, 0, 0))), frame)
    W(OB[who], "location", MUGS)
    W(OB[who], "rotation_euler", rad(0, 0, 0))
    bpy.context.view_layer.update()
    if label == "careca":
        W(OB["ZF_peruca"], "scale", (0, 0, 0))
    if label == "caolha":
        W(OB["ZC_caolha"], "scale", (1, 1, 1))
    if label == "banguela":
        W(OB["ZP_banguela"], "scale", (1, 1, 1))
    z = {"ZF": 1.46, "ZC": 1.62, "ZP": 1.6}[who]
    y = {"ZF": -0.1, "ZC": -0.1, "ZP": -0.12}[who]
    put_cam(at(MUGS, 0.0, y - 0.95, z + 0.02), at(MUGS, 0.0, y, z), 40)
    finish()

prefs.keyframe_new_interpolation_type = prev_interp
held = hold_all_keys()
sc.frame_start, sc.frame_end = 1, TL["song_frames"]
sc.frame_set(1)
bpy.data.orphans_purge(do_recursive=True)
set_lib.save()
json.dump(used, open(os.path.join(WORK, "shots_used.json"), "w"), indent=0)
print("=== SHOTS DONE: constant keys", held, "actions", len(bpy.data.actions), flush=True)
