# Step 8: keys the whole video from timeline.json. Safe to re-run: it clears its own animation first.
# Every animated value is a function of the frame, evaluated at 30 fps, so motion stays smooth and sync fixes only need a re-run.
import bpy, json, math, os, random, sys
from mathutils import Euler, Matrix, Quaternion, Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib, set_lib, path, poses_feliz as pz
importlib.reload(set_lib); importlib.reload(path); importlib.reload(pz)
from set_lib import ROOT, TL
import lib; importlib.reload(lib)
from lib import BONES, SCALE
from path import AERO, BERG, CARTA, CELULAR, CHOQUE, CLOSE, CREW, HOME, NEST, PIT, PRACA, R, REPITA, ground, rot_for

ENV = json.load(open(os.path.join(ROOT, "src", "feliz", "vocal_env.json"), encoding="utf8"))["env"]
OB = bpy.data.objects
sc = bpy.context.scene
START, FRAMES = TL["start"], TL["frames"]
BEAT = 60 / TL["bpm"]
BAR = BEAT * 4
BEAT0 = TL["beat0"] - START
S = {k: (a - START, b - START) for k, (a, b) in TL["shots"].items()}
C = {k: t - START for k, t in TL["cues"].items()}
WORDS = [[(w[0], w[1] - START) for w in line["words"]] for line in TL["lines"]]
STASH = (0, 0, -12)
FPS = TL["fps"]
sc.frame_start, sc.frame_end = 1, FRAMES
sc.render.fps = FPS

# ---- Clear earlier animation
for a in list(bpy.data.actions):
    bpy.data.actions.remove(a)
for ob in OB:
    if ob.animation_data:
        ob.animation_data_clear()
    if ob.type == "CAMERA" and ob.data.animation_data:
        ob.data.animation_data_clear()
for m in bpy.data.materials:
    if m.use_nodes and m.node_tree.animation_data:
        m.node_tree.animation_data_clear()
if sc.world.node_tree.animation_data:
    sc.world.node_tree.animation_data_clear()
ARMS = {"P1": OB["Armature"], "P2": OB["P2_arm"], "B1": OB["B1_arm"], "B2": OB["B2_arm"], "B3": OB["B3_arm"]}
for arm in ARMS.values():
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.matrix_basis.identity()

prefs = bpy.context.preferences.edit
prefs.keyframe_new_interpolation_type = "CONSTANT"
last = {}


def K(owner, prop, value, f):
    """Sets a property and keys it only when it changed. Keys are constant: every frame is computed here, nothing is left to interpolation."""
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


def ph(v, a, b):
    return clamp((v - a) / (b - a))


def smooth_ph(v, a, b):
    return pz.ease(ph(v, a, b))


def word(line, i):
    return WORDS[line - 1][i][1]


def beat_phase(v):
    b = (v - BEAT0) / BEAT
    return b - math.floor(b), int(math.floor(b + 1e-6))


def rest_q(arm, bone_name, deg):
    rest = arm.data.bones[bone_name].matrix_local.to_quaternion()
    return rest.inverted() @ pz.q(deg) @ rest


used = set()


def actor(prefix, f, pos, yaw=0.0, pose=None, size=1.0, sink=0.0, tilt=(0, 0)):
    """Places a rig with its soles on pos. Each pose is blended by the caller, and solve_lift keeps a sole on the ground."""
    used.add(prefix)
    root = OB[prefix]
    pose = pose or pz.STAND
    K(root, "location", (pos[0], pos[1], pos[2] - sink), f)
    K(root, "rotation_euler", rad(tilt[0], tilt[1], yaw), f)
    K(root, "scale", (SCALE * size,) * 3, f)
    dx, dy, dz, rx, ry, rz = pose.get("body", (0,) * 6)
    lift = pz.solve_lift(pose)
    K(OB[prefix + "_body"], "location", (dx, dy, dz + lift), f)
    K(OB[prefix + "_body"], "rotation_euler", rad(rx, ry, rz), f)
    arm = ARMS[prefix]
    for alias in pz.ALIASES:
        pb = arm.pose.bones[BONES[alias]]
        K(pb, "rotation_quaternion", rest_q(arm, BONES[alias], pose.get(alias, (0, 0, 0))), f)


def world_of(point, pos, yaw, size=1.0, lift=0.0):
    """A point from pz.fk, in the world, for a rig placed by actor()."""
    p = Vector(point) * SCALE * size
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    return Vector((pos[0] + p.x * c - p.y * s, pos[1] + p.x * s + p.y * c, pos[2] + p.z + lift * SCALE * size))


def hand(pose, side, pos, yaw, size=1.0):
    return world_of(pz.fk(pose)["hand" + side], pos, yaw, size, pz.solve_lift(pose))


def place_at(x, y, roll=0.0):
    return (x, y, ground(x, y, roll))


# ---- Camera and sky
cam = OB.get("CAM") or OB.new("CAM", bpy.data.cameras.new("CAM"))
if cam.name not in sc.collection.objects:
    sc.collection.objects.link(cam)
cam.data.clip_start = 0.05
cam.data.clip_end = 900
sc.camera = cam


def put_cam(f, pos, tgt, lens=26.0, shake=0.0, roll=0.0):
    pos, tgt = Vector(pos), Vector(tgt)
    if shake:
        r = random.Random(f)
        pos = pos + Vector((r.uniform(-1, 1), r.uniform(-1, 1), r.uniform(-1, 1))) * shake
    e = (tgt - pos).to_track_quat("-Z", "Y")
    if roll:
        e = e @ Euler((0, 0, math.radians(roll)), "XYZ").to_quaternion()
    K(cam, "location", pos, f)
    K(cam, "rotation_euler", e.to_euler(), f)
    K(cam.data, "lens", lens, f)


LEVELS = [(line["words"][0][1] - START, line["aero"]) for line in TL["lines"]]


def aero_level(v):
    """Gloss level 0 to 5, easing up over a few frames as each line arrives."""
    lvl = 0.0
    for t, a in LEVELS:
        lvl += (a - lvl) * smooth_ph(v, t - 0.2, t + 0.15)
    return lvl


def fac(level):
    return (level / 5) ** 1.4


AERO_NODES = [sc.world.node_tree.nodes["aero"], bpy.data.materials["chao"].node_tree.nodes["aero"], bpy.data.materials["agua"].node_tree.nodes["aero"]]
RIG_MATS = {m for o in OB if o.type == "MESH" and o.parent in ARMS.values() for m in o.data.materials if m and m.use_nodes and m.node_tree.nodes.get("bsdf")}
ROUGH0 = {m: m.node_tree.nodes["bsdf"].inputs["Roughness"].default_value for m in RIG_MATS}
ROUGH0_keys = list(RIG_MATS)
NOSE = bpy.data.materials["berg nariz"].node_tree.nodes["bsdf"]
NOSE.inputs["Emission Color"].default_value = (1.0, 0.85, 0.2, 1)

# ---- Characters and gag state, per shot
VILLAGERS = ["gato", "pato", "cachorro", "guaxinim"]
BUSH_SPOTS = [(-1.55, 1.0), (-0.82, 1.7), (0.82, 1.7), (1.55, 1.0)]
ROW1 = [(-3.3, 0.3), (-2.0, 1.2), (2.0, 1.2), (3.3, 0.3)]
CROWD_SPOTS = [(-2.5, 0.7), (-1.7, 1.25), (-0.85, 0.85), (0.85, 0.85), (1.7, 1.25), (2.5, 0.7), (-2.05, -0.4), (2.05, -0.4), (-1.15, -0.2), (1.15, -0.2), (-0.65, 1.8), (0.65, 1.8), (-3.1, 0.05), (3.1, 0.05), (-1.4, 2.1), (1.4, 2.1)]


def accessories(name, f, on_time, v, base_z, base_s, y):
    """Shades or chain: hidden until a few frames before on_time, then drops from above and lands exactly on it."""
    a = OB[name]
    if v < on_time - 0.16:
        K(a, "scale", (0, 0, 0), f)
        return
    fall = 1 - smooth_ph(v, on_time - 0.16, on_time)
    K(a, "location", (0, y, base_z + fall * 1.8), f)
    pop = 1 + 0.35 * max(0, 1 - (v - on_time) / 0.12) if v >= on_time else 1
    K(a, "scale", (base_s * pop,) * 3, f)


def villager(name, f, x, y, yaw=0.0, hop=0.0, squash=0.0, sink=0.0, k=1.0):
    ob = OB[name]
    used.add(name)
    K(ob, "location", (x, y, ground(x, y) + hop - sink), f)
    K(ob, "rotation_euler", rad(0, 0, yaw), f)
    K(ob, "scale", (k * (1 + squash * 0.25), k * (1 + squash * 0.25), k * (1 - squash * 0.3)), f)


def beat_hop(v, height=0.42, offs=0.0):
    p, _ = beat_phase(v + offs)
    h = math.sin(math.pi * p)
    return height * h, (1 - p / 0.22) if p < 0.22 else 0.0


def free(name, f, pos, rot=None, scale=None):
    used.add(name)
    ob = OB[name]
    K(ob, "location", pos, f)
    if rot is not None:
        K(ob, "rotation_euler", rot, f)
    if scale is not None:
        K(ob, "scale", (scale,) * 3 if not hasattr(scale, "__len__") else scale, f)


ALL_FREE = ["ninho", "buraco", "carta_a", "carta_b", "orbe", "estrela", "celular_gag", "golfinho_gag"] + [f"gota.{i}" for i in range(3)] + [f"anel.{i}" for i in range(6)]
ALL_FREE += [f"confete.{i}" for i in range(70)] + [f"vapor.{i}" for i in range(8)] + [f"borboleta.{i}" for i in range(6)] + [f"bolha.{i}" for i in range(130)]
ALL_FREE += [f"abelha_gag.{i}" for i in range(9)] + [f"koi_gag.{i}" for i in range(7)] + [f"aero_gag.{i}" for i in range(2)]
ALL_ACTORS = ["P1", "P2", "B1", "B2", "B3"]
ALL_V = [f"V_{n}" for n in VILLAGERS] + [f"C_{i}" for i in range(16)]

# Prefab copies the gags fly around
g = bpy.data.collections["gags"]
def gag_copy(prefab, name):
    ob = OB.get(name)
    if ob:
        return ob
    ob = OB[prefab + "_mesh"].copy()
    ob.name = name
    ob.parent = None
    ob.location = STASH
    g.objects.link(ob)
    return ob


gag_copy("celular", "celular_gag")
gag_copy("golfinho", "golfinho_gag")
for i in range(9):
    gag_copy("abelha", f"abelha_gag.{i}")
for i in range(7):
    gag_copy("koi", f"koi_gag.{i}")
for i in range(2):
    gag_copy("aero", f"aero_gag.{i}")

# Random, but fixed, flight data
_r = random.Random(4)
CONF = [(_r.uniform(-1, 1), _r.uniform(-0.8, 0.5), _r.uniform(1.5, 4.2), _r.uniform(0, 6), _r.uniform(-12, 12), _r.uniform(-12, 12)) for _ in range(70)]
BUB = [(_r.uniform(-4.5, 4.5), _r.uniform(-3.5, 3.5), _r.uniform(0, 1), _r.uniform(0.28, 0.7), _r.uniform(0.05, 0.2), _r.uniform(0, 6.28)) for _ in range(130)]
BURST = [(_r.uniform(-1, 1), _r.uniform(-1, 0.2), _r.uniform(-0.3, 1), _r.uniform(1.6, 5), _r.uniform(0.07, 0.3)) for _ in range(130)]
COUNT = {0: 0, 1: 0, 2: 20, 3: 28, 4: 40, 5: 130}
BOFF = [(_r.uniform(0, 6.28), _r.uniform(0.8, 1.2)) for _ in range(9)]

ARC_ACTIVE = {p: [] for p in ("P2", "B1", "B2", "B3")}


def mouth(f, v, level=1.0):
    e = ENV[min(f - 1, len(ENV) - 1)]
    s = clamp((e - 0.38) / 0.62) ** 0.8 * level
    ob = OB["P1_boca"]
    r = list(ob["rest_scale"])
    if s < 0.05:
        K(ob, "scale", (0, 0, 0), f)
    else:
        K(ob, "scale", (r[0] * (0.55 + 0.45 * s), r[1], r[2] * (0.25 + 0.75 * s)), f)


def bubbles(f, v, level, centre, wave_t=None, wave_at=None, spread=1.0):
    """Rising soap bubbles, more with each Aero level. During the orb they also burst from it."""
    n = COUNT[int(round(level))] if wave_t is None else 130
    for i in range(130):
        name = f"bolha.{i}"
        ob = OB[name]
        if i >= n:
            K(ob, "location", STASH, f)
            K(ob, "scale", (0, 0, 0), f)
            continue
        bx, by, b0, speed, size, ph0 = BUB[i]
        if wave_t is not None and i < 46:
            dx, dy, dz, sp, sz = BURST[i]
            t = (wave_t - i * 0.006)
            if t < 0:
                K(ob, "scale", (0, 0, 0), f)
                continue
            t = t % 1.6
            k = 1 - math.exp(-t * 1.3)
            K(ob, "location", (wave_at[0] + dx * sp * k * 1.4, wave_at[1] + dy * sp * k * 1.6, wave_at[2] + dz * sp * k + 0.3 * t), f)
            K(ob, "scale", (sz * clamp(t * 4),) * 3, f)
            continue
        h = ((v * speed + b0) % 1.0) * 6.0
        K(ob, "location", (centre[0] + bx * spread + 0.16 * math.sin(v * 2 + ph0), centre[1] + by * spread, centre[2] + h - 0.4), f)
        K(ob, "scale", (size * (0.9 + 0.12 * math.sin(v * 5 + ph0)),) * 3, f)


def butterflies(f, v, c):
    for i in range(6):
        a = v * (0.8 + i * 0.13) + i
        pos = (c[0] + (0.9 + i * 0.22) * math.cos(a) * (1 if i % 2 else -1), c[1] + 1.0 + 0.45 * math.sin(a * 1.3), c[2] + 1.25 + 0.45 * math.sin(a * 1.7 + i))
        free(f"borboleta.{i}", f, pos, rad(0, 0, math.degrees(a)), 0.7)
        flap = 55 * math.sin(v * 24 + i)
        K(OB[f"asa.{i}.r"], "rotation_euler", rad(0, flap, 0), f)
        K(OB[f"asa.{i}.l"], "rotation_euler", rad(0, -flap, 0), f)


def shot_of(v):
    for name, (a, b) in S.items():
        if a - 1e-6 <= v < b - 1e-6:
            return name, a, b
    return "choque", *S["choque"]


log = OB["tronco"]
door = OB["porta"]
walk_door = HOME - 5.2 + 2.32
sea_wave = bpy.data.materials["agua"].node_tree.nodes["onda"]
aurora_wave = bpy.data.materials["aurora"].node_tree.nodes["onda"]
aurora_glow = bpy.data.materials["aurora"].node_tree.nodes["brilho"]

for f in range(1, FRAMES + 1):
    v = (f - 1) / FPS
    used.clear()
    name, a, b = shot_of(v)
    u = (v - a) / (b - a)
    level = aero_level(v)
    k = fac(level)
    for n in AERO_NODES:
        K(n.outputs[0], "default_value", k, f)
    K(sea_wave.outputs[0], "default_value", v * 0.9, f)
    K(aurora_wave.outputs[0], "default_value", v * 0.5, f)
    for m in ROUGH0_keys:
        K(m.node_tree.nodes["bsdf"].inputs["Roughness"], "default_value", ROUGH0[m] * (1 - 0.55 * k), f)
    strut_p = (v - BEAT0) / (BEAT * 2)
    cue_c = (0, 0, 0)
    wave_t, wave_at = None, None
    head_scale = 1.0
    lump_on = 0.0
    thumb_on = 0.0
    tie_rot = 0.0
    nose_glow = 0.0
    aurora_k = 0.0
    door_a = 0.0
    arcs_on = False
    mouth_level = 1.0
    spread = 1.0

    if name == "porta":
        s = walk_door - 0.2 + 2.05 * v
        K(log, "rotation_euler", (rot_for(s), 0, 0), f)
        door_a = 112 * smooth_ph(v, 0.0, 0.3)
        if v >= 0.13:  # stays out of sight until the door is partly open, then steps out already through the frame
            actor("P1", f, (0, 0, 0), 0, pz.strut(strut_p))
        butterflies(f, v, (0, 0, 0))
        put_cam(f, (1.2, -4.5 + 0.55 * u, 1.0), (0.05, 0.3, 1.2 - 0.3 * u), 25)
    elif name == "energia":
        s = walk_door - 0.2 + 2.05 * v
        K(log, "rotation_euler", (rot_for(s), 0, 0), f)
        actor("P1", f, (0, 0, 0), -16, pz.strut(strut_p, 1.3))
        butterflies(f, v, (0, 0, 0))
        put_cam(f, (1.0 + 0.5 * u, -2.15, 0.46), (-0.05, 0, 0.74), 21)
    elif name == "vespas":
        K(log, "rotation_euler", (rot_for(NEST), 0, 0), f)
        hit = a + 0.17
        h = smooth_ph(v, hit - 0.02, hit + 0.06)
        head_scale = 1 + 0.42 * h
        lump_on = h
        pose = pz.mix(pz.STAND, pz.SWOLLEN, h)
        pos = (0, 0, 0)
        actor("P1", f, pos, 0, pose)
        top = world_of(pz.fk(pose)["head"], pos, 0, 1.0, pz.solve_lift(pose)) + Vector((0, 0, 0.74 * head_scale - 0.04))
        if v < hit:
            q = ph(v, a, hit) ** 2
            free("ninho", f, (top.x + 0.3 * (1 - q), top.y, top.z + (1 - q) * 3.2), rad(0, 0, 0), 0.72)
        else:
            free("ninho", f, tuple(top + Vector((0.0, 0.0, 0.06))), rad(4, 14, 0), 0.72)
        for i in range(9):
            t = max(0, v - hit + i * 0.012)
            r0, sp = BOFF[i]
            ang = r0 + t * 8.5 * sp
            rad_b = 0.62 + 0.22 * math.sin(t * 7 + i)
            free(f"abelha_gag.{i}", f, (rad_b * math.cos(ang), rad_b * math.sin(ang) - 0.18, 1.2 + 0.32 * math.sin(t * 9 + i * 2)), rad(0, 0, math.degrees(ang) + 90), 0.85 if v > hit - 0.02 else 0)
        put_cam(f, (0.7, -3.1, 1.25), (0, 0, 1.28), 25, shake=0.012 * h)
        mouth_level = 0.75
    elif name == "buraco":
        K(log, "rotation_euler", (rot_for(PIT), 0, 0), f)
        d = smooth_ph(v, a, a + 0.08)
        bounce = 0.05 * math.sin(clamp((v - a - 0.08) * 14) * math.pi)
        actor("P1", f, (0, 0, 0), 0, pz.PIT, sink=0.73 * d - bounce)
        free("buraco", f, (0, 0, 0.012), None, 0.92)
        put_cam(f, (0.42, -2.25, 0.86), (0, 0, 0.42), 24)
    elif name == "carta":
        K(log, "rotation_euler", (rot_for(CARTA), 0, 0), f)
        P, Bp = (-0.92, -0.62, 0), (1.0, 0.05, 0)
        Py, By = 40, -34
        got = smooth_ph(v, a + 0.26, a + 0.44)
        ppose = pz.mix(pz.PROUD, pz.THUMB, got)
        bpose = pz.LETTER_UP
        actor("P1", f, P, Py, ppose)
        actor("P2", f, Bp, By, bpose)
        pop = clamp(ph(v, a, a + 0.13) * 1.15)
        at = Vector((0.3, -0.25, 1.72))
        free("carta_a", f, tuple(at), rad(0, 0, 0), pop * 0.82)
        free("carta_b", f, tuple(at), rad(0, 0, 0), pop * 0.82)
        thumb_on = got
        put_cam(f, (0, -4.0, 1.25), (0, 0, 0.92), 27)
    elif name == "repita":
        K(log, "rotation_euler", (rot_for(REPITA), 0, 0), f)
        reach = smooth_ph(v, a, a + 0.16)
        pose = pz.mix(pz.PROUD, pz.POINT, reach)
        pose["head"] = tuple(x + y for x, y in zip(pose.get("head", (0, 0, 0)), (2 * math.sin(v * 13), 0, 0)))
        actor("P1", f, (0, 0, 0), 14, pose)
        pops = (a, a + BEAT, a + BEAT * 2 - 0.1, a + BEAT * 2 + 0.14)
        lands = (a + BEAT * 2, a + BEAT * 2.5, a + BEAT * 3, a + BEAT * 3.5)
        for i, n in enumerate(VILLAGERS):
            x, y = BUSH_SPOTS[i]
            up = smooth_ph(v, pops[i], pops[i] + 0.14)
            over = 1 + 0.12 * math.sin(clamp((v - pops[i] - 0.14) * 6) * math.pi)
            hp, sq = beat_hop(v, 0.14) if v > lands[i] else (0, 0)
            villager("V_" + n, f, x, y, yaw=-x * 7, hop=hp + (over - 1) * 0.5, squash=sq * 0.5, sink=(1 - up) * 1.5, k=1.0)
            src = OB[f"V_{n}_shades"]
            accessories(f"V_{n}_shades", f, lands[i], v, src["rest_z"], src["rest_scale"], src.location.y)
            src = OB[f"V_{n}_chain"]
            accessories(f"V_{n}_chain", f, lands[i], v, src["rest_z"], src["rest_scale"], src.location.y)
        put_cam(f, (0.22, -3.8 + 0.25 * u, 1.05), (0, 0.8, 0.86), 26)
    elif name == "praca":
        K(log, "rotation_euler", (rot_for(PRACA), 0, 0), f)
        hp, sq = beat_hop(v, 0.5)
        actor("P1", f, (0, -1.1, ground(0, -1.1) + hp), 0, pz.mix(pz.PROUD, pz.HOP_TUCK, hp / 0.5))
        for i in range(16):
            x, y = CROWD_SPOTS[i]
            hp2, sq2 = beat_hop(v, 0.42 + 0.06 * (i % 3), offs=0.0)
            villager(f"C_{i}", f, x, y, yaw=-x * 6, hop=hp2, squash=sq2 * 0.7, k=0.92 + 0.1 * (i % 2))
        put_cam(f, (1.5 - 1.0 * u, -5.5 + 0.7 * u, 1.85), (0, 0.5, 1.02), 25)
    elif name == "close":
        K(log, "rotation_euler", (rot_for(CLOSE), 0, 0), f)
        x = 9.4
        pose = pz.mix(pz.PROUD, pz.strut(strut_p, 0.5), 0.35)
        actor("P1", f, (x, 0, 0), -90, pose)
        cue_c = (x, 0, 0)
        spread = 0.5
        d = 1.72 - 0.42 * u
        put_cam(f, (x - d, 0.28, 1.1), (x + 0.1, 0, 0.92), 30, roll=2 * math.sin(v * 2))
    elif name == "berg":
        K(log, "rotation_euler", (rot_for(BERG), 0, 0), f)
        Pp, Bp = (-1.5, 0, 0), (1.3, 0, 0)
        actor("P1", f, Pp, 34, pz.PROUD)
        tilt = smooth_ph(v, word(7, 2), word(7, 4)) * 8
        pose = dict(pz.LETTER_SIDE)
        pose["head"] = (-6, 0, tilt)
        actor("P2", f, Bp, 0, pose)
        # Whip pan on the first frames, then a dolly in on the nose
        w = smooth_ph(v, a, a + 0.26)
        nose_c = Vector((Bp[0], -0.6, 1.08))
        cam_a = Vector((-0.8, -2.8, 1.1)).lerp(Vector((Bp[0] + 0.3, -2.25 + 0.3 * smooth_ph(v, a + 0.26, b), 1.02)), w)
        tgt = Vector((Pp[0], 0, 1.0)).lerp(Vector((Bp[0] + 0.14, 0, 1.0)), w)
        put_cam(f, cam_a, tgt, 26 - 2 * w, roll=(1 - abs(2 * w - 1)) * 7)
        h = hand(pose, "R", Bp, 0) + Vector((0.2, 0.0, 0.3))
        free("carta_a", f, tuple(h), rad(0, -8, 0), 0.5)
        free("carta_b", f, tuple(h), rad(0, -8, 0), 0.5)
    elif name == "rasga":
        K(log, "rotation_euler", (rot_for(BERG), 0, 0), f)
        tear = C["rasga"]
        Pp, Bp = (-0.28, -0.3, 0), (1.08, 0.55, 0)
        t = v - tear
        open_u = smooth_ph(v, tear - 0.02, tear + 0.1)
        pose = pz.mix(pz.HOLD_FRONT, pz.TORN, open_u)
        actor("P1", f, Pp, 16, pose)
        hR, hL = hand(pose, "R", Pp, 16), hand(pose, "L", Pp, 16)
        if t < 0:
            mid = Vector(((hR.x + hL.x) / 2, min(hR.y, hL.y) - 0.1, 0.56))
            shake = 0.02 * math.sin(v * 44) * ph(v, tear - 0.5, tear)
            free("carta_a", f, (mid.x + shake, mid.y, mid.z), rad(0, 0, 0), 0.62)
            free("carta_b", f, (mid.x + shake, mid.y, mid.z), rad(0, 0, 0), 0.62)
        else:
            drop = max(0, t - 0.28) ** 2 * 3.6
            free("carta_a", f, (hL.x - 0.4 * open_u, hL.y - 0.2, max(0.1, hL.z + 0.1 - drop)), rad(0, 22 * open_u + t * 60, 0), 0.62)
            free("carta_b", f, (hR.x + 0.4 * open_u, hR.y - 0.2, max(0.1, hR.z + 0.1 - drop)), rad(0, -22 * open_u - t * 60, 0), 0.62)
            for i in range(70):
                dx, dy, up, ph0, rx, rz = CONF[i]
                tt = t - i * 0.002
                if tt < 0:
                    continue
                c0 = Vector((Pp[0], Pp[1] - 0.5, 0.95))
                free(f"confete.{i}", f, (c0.x + dx * 2.4 * tt, c0.y + dy * 1.4 * tt, max(0.05, c0.z + up * tt - 3.2 * tt * tt)), (ph0 + rx * tt, 0, ph0 + rz * tt), 1.0)
        anger = smooth_ph(v, tear, tear + 0.15)
        jump = abs(math.sin((v - tear) * 15)) * 0.2 * anger if t > 0 else 0
        bp = pz.mix(pz.STAND, pz.FUME, anger)
        bp = dict(bp)
        actor("P2", f, (Bp[0], Bp[1], Bp[2] + jump), -28, bp)
        if t > 0.1:
            for i in range(8):
                tt = (t * 1.7 + i / 8) % 1.0
                free(f"vapor.{i}", f, (Bp[0] + (-1) ** i * (0.34 + 0.45 * tt), Bp[1] - 0.2, 1.18 + 0.7 * tt + jump), None, 1.3 * (1 - tt) + 0.2)
        put_cam(f, (0.26, -3.7, 0.86), (0.2, 0, 0.62), 25)
    elif name == "crew":
        K(log, "rotation_euler", (rot_for(CREW), 0, 0), f)
        actor("P1", f, (0, -0.85, 0), 0, pz.PROUD)
        bx = (-1.55, -0.55, 0.55, 1.55)
        for i, p in enumerate(("P2", "B1", "B2", "B3")):
            arrive = smooth_ph(v, a + i * 0.04, a + 0.46 + i * 0.03)
            side = -1 if bx[i] < 0 else 1
            x = bx[i] + side * (1 - arrive) * 5.5
            y = 1.1 - abs(bx[i]) * 0.15
            pose = pz.strut(strut_p + i * 0.25) if arrive < 1 else pz.HAND_OUT if i == 1 else pz.FUME
            actor(p, f, (x, y, ground(x, y)), -side * 90 * (1 - arrive) - bx[i] * 7, pose)
        for i, (t, x) in enumerate(((C["gota1"], -0.95), (C["gota2"], 0.95), (C["gota3"], 0.0))):
            fall = 0.34
            y = -0.3 if i != 2 else -1.5
            if t - fall <= v < t:
                z = 8.0 * (1 - ph(v, t - fall, t) ** 2)
                free(f"gota.{i}", f, (x, y, z), None, (1.2, 1.2, 1.4))
            elif t <= v < t + 0.12:
                q = ph(v, t, t + 0.12)
                free(f"gota.{i}", f, (x, y, 0), None, (1.2 + q * 1.1, 1.2 + q * 1.1, max(0.02, 0.6 * (1 - q))))
            if v >= t:
                for j in range(2):
                    q = v - t - j * 0.11
                    if q >= 0:
                        free(f"anel.{i * 2 + j}", f, (x, y, ground(x, y) + 0.03), None, (0.3 + q * 3.0, 0.3 + q * 3.0, 1.0))
        put_cam(f, (0.1, -4.25, 1.15), (0, 0.3, 1.32), 25)
    elif name == "celular":
        K(log, "rotation_euler", (rot_for(CELULAR), 0, 0), f)
        kick_t = word(10, 2)  # com
        hit_t = word(10, 4)  # tok
        back_t = b - 0.14
        P0, B0 = (10.3, 0, 0), (11.5, 0, 0)
        w = smooth_ph(v, kick_t - 0.24, kick_t - 0.05)
        kk = smooth_ph(v, kick_t - 0.05, kick_t + 0.05)
        rel = smooth_ph(v, kick_t + 0.22, kick_t + 0.5)
        pose = pz.mix(pz.mix(pz.PROUD, pz.WINDUP, w), pz.KICK, kk)
        pose = pz.mix(pose, pz.PROUD, rel)
        actor("P1", f, P0, 82, pose)
        turn = smooth_ph(v, kick_t + 0.05, kick_t + 0.3)
        fell = smooth_ph(v, back_t, back_t + 0.1)
        by = -86 + 172 * turn
        bpose = pz.mix(pz.HAND_OUT, pz.TURN_LOOK, turn)
        bpose = pz.mix(bpose, pz.HIT, fell)
        actor("P2", f, (B0[0] - 0.22 * fell, 0, ground(B0[0], 0)), by, bpose)
        hold = hand(pz.HAND_OUT, "R", B0, -86) + Vector((-0.12, 0, 0.08))
        sea = Vector((17.6, 0.1, 1.5))
        face = Vector((B0[0] + 0.5, -0.02, 1.08))
        if v < kick_t:
            phone = hold
            spin = 0
        elif v < hit_t:
            q = ph(v, kick_t, hit_t)
            phone = hold.lerp(sea, q) + Vector((0, 0, 2.2 * q * (1 - q)))
            spin = q * 720
        elif v < back_t:
            q = ph(v, hit_t, back_t)
            phone = sea.lerp(face, q) + Vector((0, 0, 1.7 * q * (1 - q)))
            spin = 720 + q * 720
        else:
            q = v - back_t
            phone = face + Vector((0.5 * q, -0.1, 0.9 * q - 3.0 * q * q))
            spin = 1500 + q * 900
        free("celular_gag", f, tuple(phone), rad(spin, 0, spin * 0.3), 0.72 if v < kick_t else 1.1)
        up_a, up_b = hit_t - 0.3, hit_t + 0.34
        if up_a <= v < up_b:
            q = ph(v, up_a, up_b)
            z = -1.3 + 3.6 * 4 * q * (1 - q) * 0.52
            # Nose towards the phone on the way up, tail flip on the way down
            free("golfinho_gag", f, (sea.x + 1.0 * (0.6 - q), sea.y, z), rad(0, 0, 90), 1.0)
        if hit_t <= v < hit_t + 0.14:
            free("estrela", f, tuple(sea + Vector((0, -0.2, 0))), rad(0, 0, 0), 1 + (v - hit_t) * 6)
        if back_t <= v < back_t + 0.16:
            free("estrela", f, tuple(face + Vector((0, -0.25, 0))), rad(0, 0, 0), 0.8 + (v - back_t) * 5)
        follow = pz.ease(ph(v, kick_t - 0.02, hit_t - 0.24)) - pz.ease(ph(v, hit_t + 0.06, back_t - 0.04))
        cx = 10.9 + 6.2 * follow
        put_cam(f, (cx - 0.2, -4.2 - 2.4 * follow, 1.2 + 1.0 * follow), (cx, 0, 0.9 + 0.3 * follow), 26 - 3 * follow)
    elif name == "aero":
        K(log, "rotation_euler", (rot_for(AERO), 0, 0), f)
        up = smooth_ph(v, a, a + 0.18)
        pose = pz.mix(pz.PROUD, pz.ORB_UP, up)
        actor("P1", f, (0, 0, 0), -6, pose)
        h = hand(pose, "R", (0, 0, 0), -6) + Vector((0.06, -0.05, 0.3))
        free("orbe", f, tuple(h), None, 0.85 * up + 0.08 * math.sin(v * 12) * up)
        wave_t, wave_at = v - a, tuple(h)
        aurora_k = smooth_ph(v, a, a + 0.6)
        for i in range(7):
            t = u * 1.15 + i * 0.12 - 0.05
            xo = -9 + i * 3 + 9 * t * (1 if i % 2 else -1)
            free(f"koi_gag.{i}", f, (xo, 4.5 + i * 0.8, 1.0 + i * 0.55 + 3.4 * t + 0.4 * math.sin(v * 6 + i)), rad(0, -28 + 12 * math.sin(v * 5 + i), (0 if i % 2 else 180) + 10 * math.sin(v * 7 + i)), 1.1)
        for i in range(2):
            free(f"aero_gag.{i}", f, ((-1) ** i * (2.6 + u), 2.6, 2.6 + 0.3 * math.sin(v * 4 + i) + i * 0.6), rad(0, 0, (-1) ** i * 20), 1.2 * up)
        K(OB["ilha_aero"], "location", (-34, 66, -40 + 62 * smooth_ph(v, a, a + 0.8)), f)
        K(OB["balao_aero"], "location", (30, 58, -40 + 62 * smooth_ph(v, a, a + 0.8)), f)
        put_cam(f, (0.9 - 1.0 * u, -3.1, 0.72), (0, 1.1, 1.18), 22)
    else:  # choque
        K(log, "rotation_euler", (rot_for(CHOQUE), 0, 0), f)
        p, bt = beat_phase(v)
        blend = 0.5 + 0.5 * math.cos(math.pi * ((v - BEAT0) / BEAT))
        dance = pz.mix(pz.DANCE_A, pz.DANCE_B, blend)
        hop = 0.16 * abs(math.sin(math.pi * p))
        actor("P1", f, (0, -0.95, ground(0, -0.95) + hop), 0, dance)
        bx = (-1.55, -0.55, 0.55, 1.55)
        for i, pp in enumerate(("P2", "B1", "B2", "B3")):
            jit = random.Random(f * 7 + i)
            pose = pz.SHOCK_A if (f + i) % 4 < 2 else pz.SHOCK_B
            y = 1.05 - abs(bx[i]) * 0.15
            actor(pp, f, (bx[i] + jit.uniform(-0.03, 0.03), y, ground(bx[i], y) + jit.uniform(0, 0.08)), -bx[i] * 7, pose)
        tie_rot = -170 + 12 * math.sin(v * 40)
        nose_glow = 3.5 + 2.5 * math.sin(v * 35)
        arcs_on = True
        aurora_k = 1.0
        K(OB["ilha_aero"], "location", (-34, 66, 22), f)
        K(OB["balao_aero"], "location", (30, 58, 22), f)
        put_cam(f, (0.45 - 0.9 * u, -3.75, 1.1), (0, 0.3, 1.18), 25, shake=0.008)

    # ---- Things shared by every shot
    mouth(f, v, mouth_level)
    K(OB["P1_inchaco"], "scale", tuple(s * lump_on for s in OB["P1_inchaco"]["rest_scale"]), f)
    K(OB["P1_polegar"], "scale", tuple(s * thumb_on for s in OB["P1_polegar"]["rest_scale"]), f)
    K(ARMS["P1"].pose.bones[BONES["head"]], "scale", (head_scale,) * 3, f)
    K(door, "rotation_euler", rad(0, 0, door_a), f)
    for p in ("P2", "B1", "B2", "B3"):
        tie = OB[f"{p}_gravata"]
        r0 = Euler(tuple(tie["rest_rot"]), "XYZ").to_matrix()
        K(tie, "rotation_euler", (r0 @ Matrix.Rotation(math.radians(tie_rot), 3, "X")).to_euler("XYZ"), f)
        for j in range(4):
            on = arcs_on and random.Random(f * 13 + j * 5 + ord(p[1]) * 31).random() < 0.42
            K(OB[f"arco_{p}.{j}"], "scale", (1, 1, 1) if on else (0, 0, 0), f)
    K(NOSE.inputs["Emission Strength"], "default_value", nose_glow, f)
    K(aurora_glow.outputs[0], "default_value", aurora_k * 0.75, f)
    bubbles(f, v, level, cue_c, wave_t, wave_at, spread)

    # ---- Stash anything this shot didn't use
    if name not in ("aero", "choque"):
        K(OB["ilha_aero"], "location", (-34, 66, -80), f)
        K(OB["balao_aero"], "location", (30, 58, -80), f)
    for p in ALL_ACTORS:
        if p not in used:
            K(OB[p], "location", STASH, f)
    for n in ALL_V:
        if n not in used:
            K(OB[n], "location", STASH, f)
    for n in ALL_FREE:
        if n not in used and not n.startswith("bolha"):
            K(OB[n], "location", STASH, f)

prefs.keyframe_new_interpolation_type = "BEZIER"
# The preference above isn't reliably honoured, and a gliding key sends actors flying between shots. Every frame is computed above, so all keys simply hold.
held = 0
for act in bpy.data.actions:
    for layer in act.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for fc in bag.fcurves:
                    for kp in fc.keyframe_points:
                        kp.interpolation = "CONSTANT"
                        held += 1
print("constant keys", held)
sc.frame_set(1)
set_lib.save()
print("shots ok,", len(bpy.data.actions), "actions")
