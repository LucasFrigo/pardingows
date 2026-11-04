# Step 8: keys the whole video from timeline.json. Safe to re-run: clears its own animation first.
# RUN is the runner game for the bottom panel. STORY is the top panel and, from NÃO! on, the full-screen ending.
# Roots and cameras move at 30 fps; bone poses step at 15 fps for the PS1 feel. No easing between keys.
# Also writes src/missao/run_plan.json, so the HUD's coin counter matches the coins he actually picks up.
import bpy, json, math, os, random, sys, importlib
from mathutils import Euler, Vector
sys.path.insert(0, r"C:\Users\lukeg\Projetos\pardingows\src\thps\blender")
sys.path.insert(0, r"C:\Users\lukeg\Projetos\pardingows\src\missao\blender")
import lib, path, poses_run, set_lib
importlib.reload(lib); importlib.reload(path); importlib.reload(poses_run); importlib.reload(set_lib)
from lib import BONES, SCALE, make_mat
from path import LANES, ROAD, run_y
from poses_run import (STAND, RUN, JUMP, STUMBLE, HELD, REACH_UP, ASLEEP, SIT_UP, PANIC, THINK, LIFT, GOT_IT, RECOIL, SHOUT, BITE,
                       H_STAND, H_RUN, H_REACH, H_BEG, H_GRAB, H_SIT, H_PEE, H_POINT)
from set_lib import place, quads, tex_mat

ROOT = r"C:\Users\lukeg\Projetos\pardingows"
TL = json.load(open(os.path.join(ROOT, "src", "missao", "timeline.json"), encoding="utf8"))
NAMES = json.load(open(os.path.join(ROOT, "blender", "missao", "cast_bones.json")))
TEX = set_lib.TEXTURES
START, FRAMES, MERGE = TL["start"], TL["frames"], TL["merge_frame"]
BEAT = 60 / TL["bpm"]
S = {k: (a - START, b - START) for k, (a, b) in TL["shots"].items()}
C = {k: t - START for k, t in TL["cues"].items()}
FAR = (500, 500, -50)
GRAB = C["grab"]

OB = bpy.data.objects
run_scene, story_scene = bpy.data.scenes["RUN"], bpy.data.scenes["STORY"]
run_cast, story_cast = bpy.data.collections["run_cast"], bpy.data.collections["story_cast"]
street = bpy.data.collections["street"]


def song(t):
    return t - START


# ---- Clear previous animation
for ob in list(OB):
    if ob.animation_data:
        ob.animation_data_clear()
    if ob.type == "LIGHT" and ob.data.animation_data:
        ob.data.animation_data_clear()
    if ob.type == "CAMERA" and ob.data.animation_data:
        ob.data.animation_data_clear()
for a in list(bpy.data.actions):
    bpy.data.actions.remove(a)
for arm in [OB["Armature"], OB["P2_arm"]] + [OB[n + "_arm"] for n in ("PY1", "PY2", "PY3", "PY4", "PY5", "PY6", "DG1", "DG2", "DG3", "DG4", "DG5", "DH1", "DH2", "DH3", "DH4", "DH5")]:
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.matrix_basis.identity()

prefs = bpy.context.preferences.edit
prev_interp = prefs.keyframe_new_interpolation_type
prefs.keyframe_new_interpolation_type = "CONSTANT"

last = {}
def K(owner, prop, value, f):
    """Sets a property and keys it only if it changed. With constant keys that is all we need."""
    key = (owner.as_pointer(), prop)
    val = tuple(round(float(x), 4) for x in value) if hasattr(value, "__len__") else value
    if last.get(key) == val:
        return
    setattr(owner, prop, value)
    owner.keyframe_insert(prop, frame=f)
    last[key] = val


def rad(*d):
    return tuple(math.radians(x) for x in d)


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def phase(v, a, b):
    return clamp((v - a) / (b - a))


def rest_q(arm, bone_name, deg):
    rest = arm.data.bones[bone_name].matrix_local.to_quaternion()
    q = Euler(rad(*deg), "XYZ").to_quaternion()
    return rest.inverted() @ q @ rest


def cycle(v, poses):
    """Run cycle locked to the song: one full stride every beat."""
    return poses[int(v / (BEAT / 4)) % 4]


# ---- Blob shadows, since no light here casts a real one
BLOB = make_mat("sombra", "04040a", alpha=0.45)
def blob(name, coll, size):
    sh = OB.get(name + "_shadow")
    if sh:
        return sh
    n = 10
    me = bpy.data.meshes.new(name + "_shadow")
    me.from_pydata([(size * math.cos(2 * math.pi * k / n), size * math.sin(2 * math.pi * k / n), 0) for k in range(n)], [], [tuple(range(n))])
    me.materials.append(BLOB)
    sh = bpy.data.objects.new(name + "_shadow", me)
    coll.objects.link(sh)
    return sh


ACTORS = {"P1": (run_cast, 0.42), "P2": (story_cast, 0.42)}
for n in ("PY1", "PY2", "PY3", "DG1", "DG2", "DG3", "DH1", "DH2"):
    ACTORS[n] = (run_cast, 0.36)
for n in ("PY4", "PY5", "PY6", "DG4", "DG5", "DH3", "DH4", "DH5"):
    ACTORS[n] = (story_cast, 0.36)
for n, (coll, size) in ACTORS.items():
    blob(n, coll, size)


def shadow_at(name, f, pos):
    h = max(pos[2], 0)
    k = clamp(1.0 - h * 0.35, 0.4, 1.0)
    K(OB[name + "_shadow"], "location", (pos[0], pos[1], 0.03 if pos[2] > -10 else -50), f)
    K(OB[name + "_shadow"], "scale", (k, k, 1), f)


SMURF_BONES = ("spine", "head", "armR", "foreR", "armL", "foreL", "thighR", "shinR", "thighL", "shinL")
SMURF_ARMS = {"P1": OB["Armature"], "P2": OB["P2_arm"]}
def smurf(prefix, f, pos, yaw=0, pose=None, rot=None, size=1.0):
    root = OB[prefix]
    K(root, "location", pos, f)
    K(root, "rotation_euler", rad(*(rot or (0, 0, yaw))), f)
    K(root, "scale", (SCALE * size, SCALE * size, SCALE * size), f)
    shadow_at(prefix, f, pos)
    if pose is not None and (f - 1) % 2 == 0:
        arm = SMURF_ARMS[prefix]
        dx, dy, dz, rx, ry, rz = pose.get("body", (0,) * 6)
        K(OB[prefix + "_body"], "location", (dx, dy, dz), f)
        K(OB[prefix + "_body"], "rotation_euler", rad(rx, ry, rz), f)
        for alias in SMURF_BONES:
            pb = arm.pose.bones[BONES[alias]]
            K(pb, "rotation_quaternion", rest_q(arm, BONES[alias], pose.get(alias, (0, 0, 0))), f)


HUMAN_BONES = ("spine", "head", "armR", "foreR", "armL", "foreL", "thighR", "shinR", "thighL", "shinL")
def human(name, f, pos, yaw=0, pose=None):
    K(OB[name], "location", pos, f)
    K(OB[name], "rotation_euler", rad(0, 0, yaw), f)
    shadow_at(name, f, pos)
    if pose is not None and (f - 1) % 2 == 0:
        arm = OB[name + "_arm"]
        bones = NAMES[name[:2]]
        for alias in HUMAN_BONES:
            K(arm.pose.bones[bones[alias]], "rotation_quaternion", rest_q(arm, bones[alias], pose.get(alias, (0, 0, 0))), f)


def camera(scene, name):
    cam = OB.get(name)
    if not cam:
        cam = bpy.data.objects.new(name, bpy.data.cameras.new(name))
        scene.collection.objects.link(cam)
    cam.data.clip_start = 0.05
    cam.data.clip_end = 900
    scene.camera = cam
    return cam


def put_cam(cam, f, pos, tgt, lens=24.0, shake=0.0, roll=0.0):
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


cam_run = camera(run_scene, "CAM_RUN")
cam_story = camera(story_scene, "CAM_STORY")
run_scene.frame_start, run_scene.frame_end = 1, MERGE
story_scene.frame_start, story_scene.frame_end = 1, FRAMES

# ---- The runner's plan, in video time
LANE_PLAN = [(6.11, 1), (8.82, 2), (10.34, 0), (11.52, 1), (12.38, 2), (15.22, 1), (16.10, 0), (17.42, 1), (18.50, 2), (20.10, 1), (22.22, 2), (23.30, 1)]
LANE_PLAN = [(song(t), LANES[i]) for t, i in LANE_PLAN]
JUMPS = [(C["dumpster"], 0.32, 1.75), (C["poop"], 0.26, 1.1)]  # (peak time, half length, height)


def lane_x(v):
    x = LANE_PLAN[0][1]
    for t, target in LANE_PLAN[1:]:
        x += (target - x) * phase(v, t - 0.08, t + 0.1) if v >= t - 0.08 else 0
    return x


def lift(v):
    for t, half, height in JUMPS:
        if abs(v - t) < half:
            u = (v - t + half) / (2 * half)
            return height * 4 * u * (1 - u)
    return 0.0


def hero_at(v):
    return (lane_x(v), run_y(v, GRAB), lift(v))


# ---- Everything in the lanes. Placed once, from the same functions that move him, so each reaches him on its word.
props = bpy.data.collections.get("run_props")
if props:
    for o in list(props.objects):
        OB.remove(o, do_unlink=True)
else:
    props = bpy.data.collections.new("run_props")
if props.name not in run_scene.collection.children:
    run_scene.collection.children.link(props)

OBSTACLES = [(7.4, 2, "BARREIRA", 1.0), (7.4, 0, "LATA", 1.0), (9.6, 1, "BARREIRA", 1.0), (9.6, 0, "SACOS", 1.2), (11.0, 1, "VAN", 1.0), (12.0, 2, "SACOS", 1.2),
             (13.0, 1, "BARREIRA", 1.0), (14.3, 0, "VAN", 1.0), (14.3, 1, "LATA", 1.0), (15.7, 2, "BARREIRA", 1.0), (17.04, 1, "SACOS", 1.2),
             (19.9, 2, "SACOS", 1.2), (20.7, 0, "BARREIRA", 1.0), (22.6, 0, "BARREIRA", 1.0)]
for t, lane, name, s in OBSTACLES:
    rz = 90 if name == "VAN" else 0
    place(name, props, (LANES[lane], run_y(song(t), GRAB), 0), rz, s)
place("LIXEIRA", props, (hero_at(C["dumpster"])[0], run_y(C["dumpster"], GRAB), 0), 0, 0.62)
place("BOSTA", props, (hero_at(C["poop"])[0], run_y(C["poop"], GRAB), 0), 0, 1.0)
place("POCA", props, (hero_at(C["puddle"])[0], run_y(C["puddle"], GRAB), 0.02), 0, 0.72)

cash_y = run_y(C["dinheiro"], GRAB)
cash_x = lane_x(C["dinheiro"])
cash = place("GRANA", props, (cash_x, cash_y, 0.75), 90, 1.6)
cash.name = "run_grana"
note = OB["GRANA_NOTA_mesh"].copy()
note.name = "run_grana_nota"
note.parent = cash
note.location = (0, 0, 0)
props.objects.link(note)

# The banner over the road, promising the salgado
ban_y = run_y(song(13.05), GRAB)
quads("run_banner", [([(3.6, ban_y, 4.1), (-3.6, ban_y, 4.1), (-3.6, ban_y, 7.7), (3.6, ban_y, 7.7)], (1, 1))], tex_mat("banner", os.path.join(TEX, "sign_salgado.png"), emit=1.0), props)

# Coins: little runs of three on his path, with a few he misses in the other lanes
rng = random.Random(4)
coin_plan = []
coins = []
t = song(6.5)
coin_mesh = OB["MOEDA_mesh"]
while t < GRAB - 0.3:
    for k in range(3):
        ct = t + k * 0.13
        x, y, z = hero_at(ct)
        ob = coin_mesh.copy()
        ob.name = f"coin.{len(coins)}"
        ob.parent = None
        ob.location = (x, y, z + 0.85)
        props.objects.link(ob)
        coins.append((ob, ct))
        coin_plan.append(round(ct, 3))
    if rng.random() < 0.5:
        other = rng.choice([l for l in LANES if abs(l - lane_x(t)) > 0.5])
        for k in range(3):
            ct = t + k * 0.13
            ob = coin_mesh.copy()
            ob.name = f"coin.{len(coins)}"
            ob.parent = None
            ob.location = (other, run_y(ct, GRAB), 0.85)
            props.objects.link(ob)
    t += BEAT * 2
# They all spin from one driver expression, which costs no keys
for ob in props.objects:
    if ob.name.startswith("coin."):
        d = ob.driver_add("rotation_euler", 2).driver
        d.type = "SCRIPTED"
        d.expression = "floor(frame / 2) * 0.55"
for ob, ct in coins:
    K(ob, "hide_render", False, 1)
    K(ob, "hide_render", True, max(int(ct * 30) + 1, 2))
K(cash, "hide_render", False, 1)
K(cash, "hide_render", True, int(C["dinheiro"] * 30) + 1)
K(note, "hide_render", False, 1)
K(note, "hide_render", True, int(C["dinheiro"] * 30) + 1)

with open(os.path.join(ROOT, "src", "missao", "run_plan.json"), "w") as fp:
    json.dump({"coins": coin_plan, "cash": round(C["dinheiro"], 3)}, fp)

# The passed-out guy lies in the street both scenes share
morto = OB["MORTO"]
for o in [morto] + list(morto.children):
    for c in list(o.users_collection):
        c.objects.unlink(o)
    street.objects.link(o)
morto.location = (-(ROAD + 1.3), -158.0, 0.17)

# Loose trash near the story's street shots would block the camera. The street is shared, so it just comes off the render.
for ob in street.objects:
    if ob.name.startswith(("LATA", "SACOS", "LIXO_RUA", "BARREIRA")) and any(abs(ob.location.y - y) < 6 and abs(ob.location.x - x) < 7 for x, y in ((3.5, -189), (0, -170), (0, -210))):
        ob.hide_render = True

# ---- Small particles, which are just dark or bright cubes moved by hand
def pool(prefix, count, mat, coll, size):
    out = []
    for i in range(count):
        name = f"{prefix}{i}"
        ob = OB.get(name)
        if ob:
            OB.remove(ob, do_unlink=True)
        me = bpy.data.meshes.new(name)
        s = size
        me.from_pydata([(a * s, b * s, c * s) for a in (-1, 1) for b in (-1, 1) for c in (-1, 1)], [], [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)])
        me.materials.append(mat)
        ob = bpy.data.objects.new(name, me)
        coll.objects.link(ob)
        out.append(ob)
    return out


FUMO = make_mat("fumo", "5a8a2a", emit=0.25)
XIXI = make_mat("xixi gota", "e8d020", emit=0.8)
run_fumo = pool("r_fumo", 14, FUMO, props, 0.12)
run_gota = pool("r_gota", 10, XIXI, props, 0.07)
story_fumo = pool("s_fumo", 14, FUMO, story_cast, 0.05)
story_gota = pool("s_gota", 16, XIXI, story_cast, 0.022)


def stink(cubes, f, centre, age, spread, rise, life=0.9):
    """Green puffs drifting up in a wobble. Each piece keeps its own path, so it travels instead of flickering."""
    for i, ob in enumerate(cubes):
        r = random.Random(i * 7 + 3)
        a, s, late = r.uniform(0, 6.28), r.uniform(0.2, 1), r.uniform(0, 0.35)
        u = (age - late) / life
        on = 0 <= u < 1
        if on:
            K(ob, "location", (centre[0] + math.cos(a) * s * spread + math.sin(u * 7 + i) * spread * 0.25, centre[1] + math.sin(a) * s * spread * 0.6, centre[2] + u * rise), f)
        K(ob, "hide_render", not on, f)


def hide_pool(cubes, f):
    for ob in cubes:
        K(ob, "hide_render", True, f)


def stream(cubes, f, a, b, age, arc=0.1):
    """A comic arc of droplets from a to b, moving along it."""
    a, b = Vector(a), Vector(b)
    for i, ob in enumerate(cubes):
        u = (i / len(cubes) + age * 2.2) % 1
        p = a.lerp(b, u)
        p.z += arc * 4 * u * (1 - u)
        K(ob, "location", p, f)
        K(ob, "hide_render", False, f)


# ---- Story props and lights
colchao, grana_story, nota_story = OB["story_colchao"], OB["story_grana"], OB["story_grana_nota"]
coxinha, mordida = OB["story_coxinha"], OB["story_coxinha_mord"]
abajur = OB["q_abajur"]
rato = OB["story_rato"]
pensa = OB.get("story_pensa") or coxinha.copy()
pensa.name = "story_pensa"
if pensa.name not in story_cast.objects:
    story_cast.objects.link(pensa)
bosta_s = OB.get("story_bosta") or place("BOSTA", story_cast, (0, -170, 0.0), 0, 1.0)
bosta_s.name = "story_bosta"
poca_s = OB.get("story_poca") or place("POCA", story_cast, (5.3, -190, 0.175), 0, 0.5)
poca_s.name = "story_poca"
y_pivot = 601.9
half = OB["COLCHAO"]["size"][1] / 2


def mattress(f, angle):
    a = math.radians(angle)
    K(colchao, "location", (0.25, y_pivot - half * math.cos(a), half * math.sin(a)), f)
    K(colchao, "rotation_euler", (-a, 0, 0), f)


# ---- Key every frame
RUN_OTHERS = ("PY1", "PY2", "PY3", "DG1", "DG2", "DG3", "DH1", "DH2")
for f in range(1, FRAMES + 1):
    v = (f - 1) / 30
    in_shot = lambda name: S[name][0] <= v < S[name][1]

    # ===== Bottom panel
    if f <= MERGE:
        hx, hy, hz = hero_at(v)
        if v >= C["nao"] - 0.05:
            pose = HELD
        elif v >= GRAB:
            pose = HELD if v >= GRAB + 0.3 else STUMBLE
        elif hz > 0:
            pose = JUMP
        else:
            pose = cycle(v, RUN)
        smurf("P1", f, (hx, hy, hz), 0, pose)
        trail = 7.4 if v < GRAB else 7.4 - 1.5 * phase(v, GRAB, GRAB + 0.8)
        put_cam(cam_run, f, (hx * 0.55, hy + trail, 3.7), (hx * 0.6, hy - 7.5, 0.9), 36, shake=0.03 if hz == 0 and v < GRAB else 0.05 if v >= GRAB else 0)

        # The jerseys come in from behind the camera and stay on his heels
        offs = ((-1.75, 2.4, 0.0), (1.75, 2.0, 0.1), (-0.55, 3.2, 0.2))
        for name, (ox, oy, late) in zip(("PY1", "PY2", "PY3"), offs):
            t0 = C["chasers_in"] + late
            if v < t0:
                human(name, f, FAR, 0, H_STAND)
            else:
                close = 1.0 - phase(v, GRAB, GRAB + 1.2) * 0.55
                gap = oy * close + 7.0 * (1 - phase(v, t0, t0 + 0.7))
                human(name, f, (hx * 0.4 + ox, hy + gap, 0), 0, cycle(v + late, H_RUN))

        # Dingows take shifts: first in the lanes, then watching from the sides, then blocking the road
        slots = {n: dict(pos=FAR, yaw=0, pose=H_STAND) for n in ("DG1", "DG2", "DG3", "DH1", "DH2")}
        first = song(17.6)
        if first <= v < song(19.6):
            slots["DG2"] = dict(pos=(LANES[0], run_y(C["dingow"], GRAB), 0), yaw=180 if v < C["dingow"] else 0, pose=H_REACH)
            slots["DH1"] = dict(pos=(LANES[2], run_y(C["dingow"], GRAB), 0), yaw=180 if v < C["dingow"] else 0, pose=H_REACH)
            slots["DG3"] = dict(pos=(LANES[1], run_y(song(19.0), GRAB), 0), yaw=180, pose=H_BEG)
        if song(20.4) <= v < song(21.9):
            # The guy at the wall, seen in passing
            pee_y = run_y(C["mijando"] + 0.25, GRAB)
            slots["DH2"] = dict(pos=(ROAD + 1.9, pee_y, 0.16), yaw=90, pose=H_PEE)
        if song(21.5) <= v < C["real1"]:
            watch = run_y(song(22.5), GRAB)
            for name, x, dy in (("DG2", -3.2, 1), ("DG3", 3.4, -2), ("DH1", -3.4, -7)):
                p = (x, watch + dy, 0)
                slots[name] = dict(pos=p, yaw=math.degrees(math.atan2(hx - p[0], -(hy - p[1]))), pose=H_STAND)
        # The one who grabs him waits in the road, then gets dragged along
        if song(22.9) <= v < GRAB:
            slots["DG1"] = dict(pos=(LANES[1] + 0.95, run_y(GRAB, GRAB) + 0.4, 0), yaw=180, pose=H_REACH)
        elif v >= GRAB:
            slots["DG1"] = dict(pos=(hx + 0.95, hy + 0.35, 0), yaw=225, pose=H_GRAB)
        walls = (("DG2", C["real1"], LANES[1], 3.0), ("DG3", C["real2"], LANES[0], 2.8), ("DH1", C["real2"], LANES[2], 2.8), ("DH2", C["real3"], LANES[1] + 0.8, 1.9))
        for name, t0, x, ahead in walls:
            if v >= t0 - 0.1:
                u = phase(v, t0 - 0.1, t0 + 0.05)
                squeeze = phase(v, C["real3"], C["nao"]) * 0.7
                side = -6 if x < 0 else 6
                slots[name] = dict(pos=(side + (x - side) * u, hy - ahead + squeeze, 0), yaw=180, pose=H_BEG)
        for name, s in slots.items():
            human(name, f, s["pos"], s["yaw"], s["pose"])

        # Gross stuff on the bottom panel
        if C["cheirao"] <= v < C["cheirao"] + 1.25:
            hxx, hyy, _ = hero_at(C["cheirao"] + 0.1)
            stink(run_fumo, f, (hxx, hy - 0.8, 0.7), v - C["cheirao"], 1.1, 1.8)
        else:
            hide_pool(run_fumo, f)
        if C["puddle"] <= v < C["puddle"] + 0.5:
            age = v - C["puddle"]
            for i, ob in enumerate(run_gota):
                r = random.Random(i + 40)
                a, s = r.uniform(0, 6.28), r.uniform(0.6, 1.5)
                K(ob, "location", (hx + math.cos(a) * s * age * 2.0, run_y(C["puddle"], GRAB) + math.sin(a) * s * age * 2.0, 0.06 + 3.2 * age - 7.5 * age * age), f)
                K(ob, "hide_render", 3.2 * age - 7.5 * age * age < -0.02, f)
        else:
            hide_pool(run_gota, f)

    # ===== Top panel, and the ending
    p2 = dict(pos=FAR, yaw=0, pose=STAND, rot=None, size=1.0)
    extras = {n: dict(pos=FAR, yaw=0, pose=H_STAND) for n in ("PY4", "PY5", "PY6", "DG4", "DG5", "DH3", "DH4", "DH5")}
    grana_at, grana_on, grana_size = (0.55, 601.45, 0.005), False, 1.0
    mat_angle = 0.0
    lamp = 0.0
    pensa_scale = 0.0
    bosta_on = poca_on = False
    fumo_at = gota = None
    rat_at = (-0.9, 699.5, 0.02)
    cox_on, mord_on = True, False
    shot = None

    if in_shot("dorme"):
        u = phase(v, *S["dorme"])
        p2.update(pos=(0.1, 601.45, 0.34), rot=(-90, 0, 90), pose=ASLEEP)
        shot = ((1.5 - u * 0.5, 598.9 + u * 0.5, 1.55 - u * 0.2), (0.0, 601.35, 0.35), 24)

    elif in_shot("acorda"):
        lamp = 45 if v >= C["afflicao"] else 0
        if v < song(9.56):
            # DUAS DA MANHÃ on the clock
            shot = ((-1.1, 601.75, 0.62), (-1.1, 602.25, 0.6), 34)
        else:
            pose = PANIC if v >= C["afflicao"] else SIT_UP
            jump = 0.1 if C["afflicao"] <= v < C["afflicao"] + 0.12 else 0
            p2.update(pos=(0.15, 601.3, 0.08 + jump), yaw=0, pose=pose)
            shot = ((0.15, 598.9, 0.95), (0.15, 601.3, 0.72), 28, 0.03 if v >= C["afflicao"] else 0)

    elif in_shot("objetivo"):
        lamp = 45
        p2.update(pos=(-0.5, 600.5, 0.0), yaw=0, pose=THINK if v >= song(11.9) else STAND)
        pensa_scale = 0.0 if v < song(11.9) else 1.0 if v >= C["salgado"] else 0.55
        shot = ((-0.2, 598.1, 0.95), (-0.2, 600.5, 1.05), 28)

    elif in_shot("colchao"):
        lamp = 45
        d = C["dinheiro"]
        mat_angle = 62 * phase(v, S["colchao"][0] + 0.25, song(13.55))
        grana_on = v >= S["colchao"][0] + 0.25
        if v < d:
            p2.update(pos=(0.25, 600.9, 0.0), yaw=180, pose=LIFT)
            shot = ((2.1, 599.6, 1.15), (0.25, 601.3, 0.5), 26)
        elif v < C["colchao"]:
            # The cash, close, and blue because it's reais
            shot = ((0.95, 600.65, 0.5), (0.55, 601.45, 0.1), 30)
            p2.update(pos=(0.25, 600.9, 0.0), yaw=180, pose=LIFT)
        else:
            mat_angle = 0.0
            p2.update(pos=(0.1, 600.4, 0.0), yaw=0, pose=GOT_IT)
            grana_at = (0.52, 600.35, 1.08)
            grana_size = 0.6
            shot = ((0.15, 598.3, 0.9), (0.2, 600.4, 0.85), 28)

    elif in_shot("paraguaios"):
        # Three jerseys pile into the street behind him and come at the camera
        a = S["paraguaios"][0]
        y = -113 + (v - a) * 7.5
        for name, x, off in (("PY4", -1.9, 0.0), ("PY5", 1.8, 0.8), ("PY6", 0.0, -1.2)):
            extras[name] = dict(pos=(x, y + off, 0), yaw=180, pose=cycle(v + off, H_RUN))
        shot = ((0.3, -100.5, 0.8), (0, -112, 1.5), 34)

    elif in_shot("lixao"):
        # He's what gets thrown on the pile
        a, land = S["lixao"][0], C["dumpster"]
        if v < land:
            u = phase(v, a, land)
            p2.update(pos=(-7 + 7.2 * u, 699.0 + 5.5 * u, 2.4 + 2.6 * 4 * u * (1 - u)), rot=(u * 500, 0, u * 240), pose=SHOUT)
        else:
            p2.update(pos=(0.2, 704.5, 1.9), rot=(170, 0, 20), pose=PANIC)
        rat_at = (-0.9 + (v - a) * 4.2, 699.5, 0.02)
        shot = ((0, 693.6, 1.9), (0, 702, 2.3), 24, 0.1 * (1 - phase(v, land, land + 0.3)) if v >= land else 0)

    elif in_shot("caminho"):
        # Dingows along both curbs, turning their heads as the camera walks past
        a = S["caminho"][0]
        cy = -150 - (v - a) * 2.4
        for name, x, y in (("DG4", -3.95, -156.5), ("DH3", 3.95, -157.5), ("DH4", -3.95, -159.5), ("DG5", 3.95, -160.5)):
            # They sit on the curb looking across the road, then all turn to the camera on DINGOW
            yaw = (-90 if x < 0 else 90) if v < C["dingow"] else (-155 if x < 0 else 155)
            extras[name] = dict(pos=(x, y, -0.45), yaw=yaw, pose=H_SIT)
        shot = ((0, cy, 1.2), (0, cy - 9, 0.75), 30, 0.015)

    elif in_shot("chao"):
        bosta_on = True
        if v < song(19.66):
            # CAGARAM NO CHÃO, from the ground
            shot = ((0.55, -168.3, 0.22), (0, -170, 0.32), 28, 0.04 if v >= C["poop"] else 0)
        else:
            p2.update(pos=(0, -168.7, 0), yaw=180, pose=RECOIL)
            fumo_at = ((0, -170, 0.45), v - song(19.66))
            shot = ((-1.6, -170.2, 0.75), (0, -169.3, 0.85), 26, 0.05 if v >= C["bosta"] else 0)

    elif in_shot("mijando"):
        # From behind, against the wall
        poca_on = True
        extras["DH5"] = dict(pos=(5.0, -190, 0.16), yaw=90, pose=H_PEE)
        gota = ((5.32, -190, 1.0), (6.25, -190, 0.42), v)
        shot = ((3.0, -187.9, 1.25), (5.25, -190, 0.95), 28)

    elif in_shot("olhando"):
        # Three quick tilted faces, one per stress in the line
        stares = (("DG4", (0, 0), C["olhando"], 14), ("DH3", (3, 0), C["olhando"] + 0.4, -16), ("DG5", (-3, 0), S["olhando"][1], 10))
        for name, (dx, _), until, roll in stares:
            if v < until:
                extras[name] = dict(pos=(dx, -210, 0), yaw=0, pose=H_STAND)
                shot = ((dx, -210.62, 1.55), (dx, -210, 1.53), 30, 0, roll)
                break

    elif in_shot("mao"):
        # The hand comes in and doesn't let go
        grabbed = v >= GRAB
        reach = phase(v, song(23.3), GRAB)
        p2.update(pos=(-0.55, -210, 0), yaw=90, pose=REACH_UP if v >= song(23.3) else cycle(v * 0.6, RUN))
        extras["DG4"] = dict(pos=(1.25 - 0.28 * reach, -210, 0), yaw=-90, pose=H_GRAB if reach > 0 else H_STAND)
        shot = ((0.12, -211.9, 0.95), (0.12, -210, 0.98), 30, 0.03 if grabbed else 0)

    elif in_shot("dois_real"):
        # One more leans in on each line, right at the camera
        p = phase(v, C["real1"], C["real3"])
        extras["DG4"] = dict(pos=(0, -210, 0), yaw=180, pose=H_BEG)
        p2.update(pos=FAR)
        if v >= C["real2"] - 0.1:
            extras["DH3"] = dict(pos=(-0.85, -209.7, 0), yaw=180, pose=H_BEG)
        if v >= C["real3"] - 0.1:
            extras["DH4"] = dict(pos=(0.85, -209.6, 0), yaw=180, pose=H_BEG)
            extras["DG5"] = dict(pos=(1.5, -209.9, 0), yaw=195, pose=H_REACH)
        shot = ((0, -207.9 - p * 0.4, 1.32), (0, -210, 1.3), 26, 0.012 + p * 0.03)

    elif in_shot("nao"):
        # Full screen from here on. He throws everyone off.
        age = v - C["nao"]
        p2.update(pos=(0, -210, 0), yaw=180, pose=SHOUT)
        for name, x in (("DG4", -1.2), ("DH3", 1.3), ("DH4", -2.1), ("DG5", 2.2)):
            extras[name] = dict(pos=(x * (1 + age * 3), -211.5 - age * 2.5, 0), yaw=0 if x < 0 else 0, pose=H_BEG)
        shot = ((0, -207.9, 0.55), (0, -210, 0.9), 22, 0.05)

    else:
        # The silence, the snack bar and the bite
        a = S["coxinha"][0]
        bite = a + 0.72
        mord_on = v >= bite
        cox_on = not mord_on
        p2.update(pos=(-0.72, 800.0, 0.58), yaw=68, pose=BITE if v >= bite - 0.18 else STAND)
        u = phase(v, a, a + 0.5)
        shot = ((-0.12, 796.2 + 0.5 * u, 1.3), (-0.12, 800.4, 1.72), 25)

    if shot:
        pos, tgt, lens = shot[0], shot[1], shot[2]
        put_cam(cam_story, f, pos, tgt, lens, shot[3] if len(shot) > 3 else 0.0, shot[4] if len(shot) > 4 else 0.0)

    smurf("P2", f, p2["pos"], p2["yaw"], p2["pose"], p2["rot"], p2["size"])
    for name, s in extras.items():
        human(name, f, s["pos"], s["yaw"], s["pose"])

    mattress(f, mat_angle)
    K(grana_story, "location", grana_at, f)
    K(grana_story, "scale", (grana_size, grana_size, grana_size), f)
    K(grana_story, "hide_render", not grana_on, f)
    K(nota_story, "hide_render", not grana_on, f)
    K(abajur.data, "energy", lamp, f)
    K(pensa, "location", (0.55, 600.5, 0.75), f)
    K(pensa, "scale", (0.5 * pensa_scale, 0.5 * pensa_scale, 0.6 * pensa_scale), f)
    K(pensa, "hide_render", pensa_scale == 0, f)
    K(bosta_s, "hide_render", not bosta_on, f)
    K(poca_s, "hide_render", not poca_on, f)
    K(rato, "location", rat_at, f)
    K(coxinha, "hide_render", not cox_on, f)
    K(mordida, "hide_render", not mord_on, f)
    if fumo_at:
        stink(story_fumo, f, fumo_at[0], fumo_at[1], 0.3, 0.9, life=0.8)
    else:
        hide_pool(story_fumo, f)
    if gota:
        stream(story_gota, f, gota[0], gota[1], gota[2])
    else:
        hide_pool(story_gota, f)

prefs.keyframe_new_interpolation_type = prev_interp
# The preference above isn't reliably honoured here, and a gliding key sends actors and cameras flying between sets, so every key is made constant by hand
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
run_scene.frame_set(1)
story_scene.frame_set(1)
bpy.data.orphans_purge(do_recursive=True)
set_lib.save()
print("keyed", FRAMES, "frames; coins", len(coins), "collected plan", len(coin_plan), "actions", len(bpy.data.actions))
