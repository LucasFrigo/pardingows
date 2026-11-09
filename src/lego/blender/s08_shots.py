# Step 8: keys the whole video from the timeline. Poses and the camera change on every second frame (15 fps inside 30), like stop motion,
# and every cut also gets a key so a shot can start on any frame. Writes blender/lego/frames.json: the frames to render and which world each is in.
import bpy, json, math, os, random, sys, importlib
from mathutils import Matrix, Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import set_lib, poses_lego as PL, world_data
importlib.reload(set_lib); importlib.reload(PL); importlib.reload(world_data)
from set_lib import FAR, PLATE, ROOT, TL, WORK, save
from world_data import origin

OB = bpy.data.objects
sc = bpy.context.scene
FPS, START, FRAMES = TL["fps"], TL["start"], TL["frames"]
BEAT, BEAT0 = 60 / TL["bpm"], TL["beat0"]
sc.frame_start, sc.frame_end = 1, FRAMES
sc.render.fps = FPS
bpy.context.preferences.edit.keyframe_new_interpolation_type = "CONSTANT"
ENV = json.load(open(os.path.join(ROOT, "src", "lego", "vocal_env.json")))["env"]

HEROES = ["pardo", "israel", "robber1", "robber2", "robber3", "pardo_rob", "father", "child"]
CROWD = ["crook", "escapee", "policeman", "banker", "pepper", "brickster", "henchman", "sky", "dewey"]
PIECES = ["pardo_shades", "pardo_rob_shades", "pardo_rob_nose", "pardo_rob_mask", "father_shades", "father_chain", "child_shades", "child_chain"]
MOVERS = ["calendar", "joint_gag", "interrog_lamp", "thought_bubble", "puff_0", "puff_1"] + [f"sad_{i}" for i in range(6)]
FACEFIG = {"pardo": 2, "pardo_rob": 1, "israel": 2, "father": 1, "child": 1}

for ob in OB:
    if ob.animation_data:
        ob.animation_data_clear()
for fig in FACEFIG:
    nt = bpy.data.materials[f"{fig}_Face"].node_tree
    if nt.animation_data:
        nt.animation_data_clear()

cam = OB.get("lego_cam") or OB.new("lego_cam", bpy.data.cameras.new("lego_cam"))
if cam.name not in sc.collection.objects:
    sc.collection.objects.link(cam)
sc.camera = cam
cam.data.sensor_fit = "VERTICAL"
cam.data.sensor_height = 36
cam.data.clip_start, cam.data.clip_end = 0.02, 400
cam.data.dof.use_dof = True


# ---- Timing helpers
def fr(t):
    return round((t - START) * FPS) + 1


def word(line, i):
    return TL["lines"][line]["words"][i][1]


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def seg(t, a, b):
    return clamp((t - a) / (b - a))


def ease(x):
    return x * x * (3 - 2 * x)


def lerp(a, b, u):
    return tuple(p + (q - p) * u for p, q in zip(a, b))


SHOTS = [(s["sketch"], s["t"]) for s in TL["shots"]]


def shot_at(t):
    cur = SHOTS[0]
    for s in SHOTS:
        if fr(s[1]) <= fr(t):
            cur = s
    return cur


# ---- Keying: only changes are keyed, so a held pose costs nothing
last = {}


def K(owner, prop, value, f, idx=None):
    key = (owner.as_pointer(), prop)
    val = tuple(round(float(x), 5) for x in value) if hasattr(value, "__len__") else round(float(value), 5)
    if last.get(key) == val:
        return
    setattr(owner, prop, value)
    owner.keyframe_insert(prop, frame=f)
    last[key] = val


def key_arm(arm, f):
    for pb in arm.pose.bones:
        K(pb, "location", tuple(pb.location), f)
        K(pb, "rotation_quaternion", tuple(pb.rotation_quaternion), f)
        K(pb, "scale", tuple(pb.scale), f)


# ---- The state of the world at song time t, set from scratch each step
STATE = {}


def reset():
    for n in HEROES:
        r = OB["CH_" + n]
        r.location, r.rotation_euler = FAR, (0, 0, 0)
        PL.clear(OB[n + "_arm"])
    for n in CROWD:
        PL.clear(OB[n + "_arm"])
    for p in PIECES:
        OB[p].delta_location = (0, 0, 0)
        OB[p].hide_render = p in ("pardo_rob_shades", "pardo_rob_nose", "father_shades", "father_chain", "child_shades", "child_chain")
    OB["joint_gag"].location = FAR
    OB["joint_gag"].scale = (1, 1, 1)
    cal = OB["calendar"]
    o = origin("calendario")
    cal.location = (o[0] - 0.42, o[1] + 1.56, o[2] + 0.34)
    cal.rotation_euler = (0, 0, 0)
    OB["interrog_lamp"].rotation_euler = (0, 0, 0)
    for n in ("thought_bubble", "puff_0", "puff_1") + tuple(f"sad_{i}" for i in range(6)):
        ob = OB[n]
        ob.location = ob["home"]
        ob.scale = (0.5, 0.5, 0.5) if n.startswith("sad_") else (1, 1, 1)
        if "home_rot" in ob:
            ob.rotation_euler = ob["home_rot"]
    STATE.clear()
    STATE["faces"] = {fig: 0 for fig in FACEFIG}


def bounce(t):
    """0 on the beat, 1 halfway between: the shape of a head nod or a little hop."""
    return abs(math.sin(math.pi * (t - BEAT0) / BEAT))


def groove(arm, pose, t, k=1.0):
    """Moves a figure that would otherwise stand still to the beat: a nod, a sway of the shoulders and arms swinging on alternate beats."""
    b = bounce(t) * k
    side = 1 if int(math.floor((t - BEAT0) / BEAT)) % 2 == 0 else -1
    PL.adjust(arm, pose, "head", (10 * b, 0, 5 * side * k))
    PL.adjust(arm, pose, "spine03", (4 * b, 0, 4 * side * k))
    PL.adjust(arm, pose, "armUp_L", (-8 * side * k, 0, 0))
    PL.adjust(arm, pose, "armUp_R", (8 * side * k, 0, 0))
    return pose


def put(n, o, x, y, z=0.0, rz=0.0, rx=0.0, pose=None, action=None, u=0.0, t=None, gk=1.0):
    """t switches the beat groove on (static figures only), gk sets how strong it is."""
    r = OB["CH_" + n]
    arm = OB[n + "_arm"]
    hop = 0.0
    if action:
        PL.apply(arm, PL.sample(action, u))
    elif pose is not None:
        p = pose(arm) if callable(pose) else dict(pose)
        if t is not None:
            groove(arm, p, t, gk)
            hop = 0.008 * bounce(t) * gk
        PL.apply(arm, p)
    r.location = (o[0] + x, o[1] + y, o[2] + r["z0"] + z + hop + (PL.ground(action) if action else 0.0))
    r.rotation_euler = (math.radians(rx), 0, math.radians(rz))


def pose_on(n, pose, t=None, gk=1.0):
    arm = OB[n + "_arm"]
    p = pose(arm) if callable(pose) else dict(pose)
    if t is not None:
        groove(arm, p, t, gk)
    PL.apply(arm, p)


def offset(piece, world):
    """Moves a piece on its bone by a world-space offset, measured with the rig at rest."""
    m = OB[piece]["w2l"]
    M = Matrix(((m[0], m[1], m[2]), (m[3], m[4], m[5]), (m[6], m[7], m[8])))
    OB[piece].delta_location = M @ Vector(world)


def face(fig, i):
    STATE["faces"][fig] = i


def sing(fig, f, alt=1):
    """Mouth open when the vocal is loud, on the step's own frame."""
    if ENV[min(f - 1, len(ENV) - 1)] > 0.55:
        face(fig, alt)


def camera(o, pos, tgt, lens=38.0, fstop=4.0, f=0, shake=0.0012):
    r = random.Random(f)
    j = Vector((r.uniform(-1, 1), r.uniform(-1, 1), r.uniform(-1, 1))) * shake
    p, q = Vector(pos) + Vector(o) + j, Vector(tgt) + Vector(o)
    STATE["cam"] = (p, (q - p).to_track_quat("-Z", "Y").to_euler(), lens, fstop, (q - p).length)


def act_u(name, t, t0, phase=0.0):
    return (t - t0) / PL.duration(name) + phase


# ---- Poses used in several shots
def arms(dl, dr, head=(0, 0, 0)):
    def make(arm):
        p = {}
        PL.adjust(arm, p, "armUp_L", dl)
        PL.adjust(arm, p, "armUp_R", dr)
        PL.adjust(arm, p, "head", head)
        return p
    return make


RANTS = [arms((-62, 0, 18), (-20, 0, -14), (8, 0, -14)), arms((-30, 0, 30), (-85, 0, -10), (4, 0, -6)), arms((-95, 0, 8), (-60, 0, -22), (10, 0, -18)), arms((-40, 0, 36), (-40, 0, -36), (12, 0, 0))]
ASKS = [arms((-30, 0, 34), (-30, 0, -34)), arms((-70, 0, 10), (-10, 0, -8), (0, 0, 8)), arms((-10, 0, 8), (-70, 0, -10), (0, 0, -8))]


def beat_index(t, per=1.0):
    return int(math.floor((t - BEAT0) / (BEAT * per)))


# ---- The eight sketches
def rua(t, f, o):
    t0 = SHOTS[0][1]
    fod, isr = word(0, 5), word(0, 6)
    # Israel rants on every beat, mouth flapping on the half-beat, until fodase pops it. Then he just stands there.
    if t < fod:
        put("israel", o, -0.2, -0.05, rz=24, pose=RANTS[beat_index(t) % len(RANTS)])
        face("israel", 1 if beat_index(t, 0.5) % 2 == 0 else 0)
    else:
        put("israel", o, -0.2, -0.05, rz=24, pose=arms((8, 0, 4), (8, 0, -4)), t=t, gk=0.6)
        face("israel", 2)
    put("pardo", o, 0.2, 0.05, rz=-14, action="Idle_Light", u=act_u("Idle_Light", t, t0))
    sing("pardo", f)
    # Shades sit pushed up on the cap, then slide down over the last beat before fodase
    u = ease(seg(t, word(0, 4), fod))
    offset("pardo_shades", (0, 0.004 * (1 - u), 0.05 * (1 - u)))
    if t < fod:
        camera(o, lerp((0.0, -1.72, 0.22), (0.0, -1.55, 0.22), seg(t, t0, fod)), (0, 0, 0.2), f=f)
    elif t < isr:
        camera(o, (0.2, -0.95, 0.3), (0.2, 0, 0.3), f=f)
    else:
        camera(o, (-0.2, -0.95, 0.31), (-0.2, 0, 0.31), f=f)


def calendario(t, f, o):
    t0 = SHOTS[1][1]
    data, vou, nam = word(1, 5), word(1, 6), word(1, 8)
    fall_end = data + 0.26
    cal = OB["calendar"]
    # It tips forward off the wall and drops to the floor as it turns, landing flat
    k = ease(seg(t, data, fall_end)) ** 1.6
    cal.rotation_euler = (math.radians(90 * k), 0, 0)
    cal.location.z = origin("calendario")[2] + 0.34 * (1 - k) + 0.004 * k
    if t < fall_end:
        put("pardo", o, -0.42, 0.75, rz=0, action="LookingUp", u=0.5)
        sing("pardo", f)
    elif t >= vou:
        # On top of the fallen calendar, kicking back
        relax = lambda a: dict(PL.sit(a), **PL.adjust(a, PL.adjust(a, {}, "armUp_L", (-150, 0, 40)), "armUp_R", (-150, 0, -40)))
        put("pardo", o, -0.42, 0.95, z=0.004 - 0.12, rz=-18, pose=relax, t=t, gk=0.7)
        sing("pardo", f)
    if t < word(1, 2):
        # Read the page first, then tilt down to Pardo
        camera(o, (-0.42, -0.6, 0.95), (-0.42, 1.56, 0.95), f=f)
    elif t < data:
        camera(o, lerp((-0.1, -1.4, 0.4), (-0.15, -1.25, 0.36), seg(t, word(1, 2), data)), (-0.35, 0.6, 0.3), f=f)
    else:
        camera(o, lerp((0.15, -1.6, 0.55), (0.05, -1.25, 0.45), ease(seg(t, vou, nam + 0.6))), (-0.38, 0.9, 0.15), f=f)


def cofre(t, f, o):
    t0 = SHOTS[2][1]
    # Paused: the crew is frozen mid-move, only Pardo can still move
    put("robber1", o, -0.42, 0.15, rz=18, action="Flexing", u=0.5)
    put("robber2", o, 0.42, 0.15, rz=-18, action="AirGuitar", u=0.3)
    put("robber3", o, 0.15, 0.5, rz=-6, action="Dance", u=0.42)
    look = word(2, 1)
    lift_a, lift_b = word(2, 4), word(2, 5)
    walk_a = word(2, 5)
    head = (0, 0, 0)
    if look <= t < lift_a:
        head = (0, 0, 35 if beat_index(t, 0.5) % 2 == 0 else -35)
    if t < walk_a:
        put("pardo_rob", o, 0.0, -0.1, pose=arms((10, 0, 6), (-90 if lift_a <= t else 10, 0, -18 if lift_a <= t else -6), head), t=t if t >= lift_b else None, gk=0.8)
    else:
        w = seg(t, walk_a, walk_a + 1.6)
        put("pardo_rob", o, 0.0 + 0.55 * w, -0.1 - 0.5 * w, rz=-40, pose=lambda a: PL.walk(a, (t - walk_a) / 0.6))
    # The mask goes up over the cap, showing his shades and nose
    m = ease(seg(t, lift_a, lift_b))
    offset("pardo_rob_mask", (0, 0.025 * m, 0.075 * m))
    if m > 0.6:
        OB["pardo_rob_shades"].hide_render = False
        OB["pardo_rob_nose"].hide_render = False
        sing("pardo_rob", f)
    if t < walk_a:
        camera(o, lerp((0.0, -1.5, 0.22), (0.0, -1.15, 0.24), seg(t, t0, walk_a)), (0, 0, 0.22), f=f)
    else:
        camera(o, (0.15, -1.25, 0.24), (0.35, -0.4, 0.22), f=f)


def parque(t, f, o):
    t0 = SHOTS[3][1]
    breathe = 4 * math.sin((t - BEAT0) / BEAT * math.pi)
    calm = lambda a: dict(PL.sit(a), **PL.adjust(a, PL.adjust(a, PL.adjust(a, {}, "armUp_L", (-35, 0, 30)), "armUp_R", (-35, 0, -30)), "spine03", (breathe, 0, 0)))
    put("pardo", o, 0.0, 0.26, z=7 * PLATE - 0.17, pose=calm, t=t, gk=0.6)
    sing("pardo", f)
    # One sad brick leaves per word, spinning off up and away. On "mal" the empty bubble swells and pops.
    words = TL["lines"][3]["words"]
    for i in range(6):
        at = words[i][1]
        if t >= at:
            ob = OB[f"sad_{i}"]
            u = seg(t, at, at + 0.55)
            h = Vector(ob["home"])
            ob.location = h + Vector((0.35 + 0.1 * i, -0.15, 0.9)) * ease(u) + Vector((0, 0, 0.12 * math.sin(u * math.pi)))
            ob.rotation_euler = (ob["home_rot"][0] + 4 * u, ob["home_rot"][1] + 3 * u * (1 if i % 2 else -1), ob["home_rot"][2] + 2 * u)
    mal = words[6][1]
    if t >= mal:
        k = [1.25, 0.6, 0.0][min(int((t - mal) * 15), 2)]
        for n in ("thought_bubble", "puff_0", "puff_1"):
            OB[n].scale = (k, k, k)
    camera(o, lerp((0.14, -1.35, 0.4), (0.1, -1.05, 0.42), ease(seg(t, t0, t0 + 3.4))), (0.06, 0.2, 0.45), f=f)


def corrida(t, f, o):
    t0 = SHOTS[4][1]
    rmx, dos, prd = word(4, 6), word(4, 7), word(4, 8)
    # Scratch: on remix, time rubs back and forth like a record, then picks up where it was
    if rmx <= t < dos:
        tau = rmx - 0.09 * abs(math.sin((t - rmx) / 0.18 * math.pi))
    elif t >= dos:
        tau = t - (dos - rmx)
    else:
        tau = t
    y = 0.42 - 1.0 * (tau - t0)  # starts in front of the bus, which stands across the street at y 0.58 to 1.32
    put("father", o, 0.1, y, action="Run", u=act_u("Run", tau, t0))
    put("child", o, -0.16, y, action="Run", u=act_u("Run", tau, t0, 0.5))
    face("father", 1)
    face("child", 1)
    for fig in ("father", "child"):
        for piece, at in (("shades", dos), ("chain", prd)):
            if t >= at:
                OB[f"{fig}_{piece}"].hide_render = False
                offset(f"{fig}_{piece}", (0, 0, 0.3 * (1 - ease(seg(t, at, at + 0.17)))))
    if t >= prd + 0.2:
        face("father", 0)
        face("child", 0)
    camera(o, (-0.03, y - 1.7, 0.22), (-0.03, y, 0.26), fstop=3.2, f=f)


def praca(t, f, o):
    t0 = SHOTS[5][1]
    on, crane = word(5, 0), word(5, 5)
    u = (t - BEAT0) / BEAT
    six = (lambda a: PL.six_seven(a, u)) if t >= on else None
    put("pardo", o, 0.0, -0.45, pose=six or {}, t=None if six else t)
    sing("pardo", f)
    if six:
        for n in CROWD:
            pose_on(n, six)
    c = ease(seg(t, crane, crane + 1.0))
    camera(o, lerp((0.05, -1.75, 0.34), (0.0, -1.2, 3.4), c), lerp((0, 0, 0.22), (0, 1.3, 0.0), c), lens=38 - 6 * c, fstop=5.6 + 6 * c, f=f)


def interrogatorio(t, f, o):
    t0 = SHOTS[6][1]
    que, vai, bolar, bas = word(6, 5), word(6, 6), word(6, 7), word(6, 10)
    quem = word(6, 3)
    # Pardo sits on the stool behind the table under the lamp, asking with his hands
    seated = lambda a: dict(PL.sit(a), **ASKS[beat_index(t) % len(ASKS)](a))
    put("pardo", o, 0.0, 0.66, z=7 * PLATE - 0.15, pose=seated)
    sing("pardo", f)
    # The lamp swings on the beat
    s = math.pi * (t - BEAT0) / BEAT
    OB["interrog_lamp"].rotation_euler = (math.radians(7 * math.sin(s / 2)), math.radians(3 * math.cos(s / 2)), 0)
    # The interrogators lean in on the beat, glance at each other on "que", then the banker raises the joint over his head
    look = 45 if que <= t < vai else 0
    pose_on("policeman", arms((-30, 0, 10), (8, 0, -4), (0, 0, -look)), t=t, gk=0.7)
    pose_on("banker", arms((8, 0, 4), (-120 if t >= bolar else -30, 0, -12), (0, 0, look)), t=t, gk=0.7)
    if t >= bas:
        inst = OB["interrogator banker"]
        arm = OB["banker_arm"]
        bpy.context.view_layer.update()
        hand = arm.matrix_world @ arm.pose.bones[set_lib.bones_of(arm)["hand_R"]].tail
        pop = [0.4, 1.4, 1.0][min(int((t - bas) * 15), 2)]
        OB["joint_gag"].location = inst.matrix_world @ hand + Vector((0, 0, 0.015))
        OB["joint_gag"].scale = (pop, pop, pop)
        OB["joint_gag"].rotation_euler = (0, math.radians(20), math.radians(70))
    # Over the shoulders, then cut-ins on each face and the joint
    if t < quem:
        camera(o, lerp((0.0, -1.05, 0.5), (0.0, -0.9, 0.47), seg(t, t0, quem)), (0, 0.5, 0.34), lens=32, fstop=2.8, f=f)
    elif t < que:
        camera(o, (-0.6, 0.2, 0.44), (-0.36, -0.32, 0.2), lens=34, fstop=6.0, f=f)  # three-quarter front: a LEGO face is printed on the front only
    elif t < vai:
        camera(o, (0.6, 0.22, 0.44), (0.36, -0.3, 0.2), lens=34, fstop=6.0, f=f)
    elif t < bolar:
        camera(o, (0.04, -0.25, 0.43), (0, 0.66, 0.36), lens=40, fstop=2.8, f=f)
    elif t < bas:
        camera(o, (0.1, -1.0, 0.3), (0.08, 0.3, 0.45), lens=30, fstop=2.8, f=f)
    else:
        # Low from the side, up at the banker holding the joint into the lamp's light
        camera(o, (0.62, 0.32, 0.36), (0.36, -0.3, 0.32), lens=30, fstop=5.0, f=f)


def quarto(t, f, o):
    t0 = SHOTS[7][1]
    turn, fall, bem = word(7, 5), word(7, 6), word(7, 7)
    land = fall + 0.24
    # He walks in along the foot of the bed, turns to face it on "e", and falls face down onto it on "dormir"
    x = -0.9 + 0.9 * seg(t, t0, turn)
    if t < turn:
        put("pardo", o, x, -0.06, rz=90, pose=lambda a: PL.walk(a, (t - t0) / 0.55))
        sing("pardo", f)
    else:
        k = ease(seg(t, fall, land))
        bump = 0.025 * math.sin(seg(t, land, bem + 0.15) * math.pi) if t >= land else 0.0
        put("pardo", o, 0.0, -0.04, z=0.23 * k + bump, rz=180, rx=90 * k ** 1.4, pose={} if t >= fall else arms((10, 0, 4), (10, 0, -4)), t=t if t < fall else None)
        if t < fall:
            sing("pardo", f)
    if t < land:
        camera(o, (0.8, -1.05, 0.48), (x * 0.6, 0.1, 0.2), lens=34, f=f)
    else:
        camera(o, lerp((0.8, -1.05, 0.48), (0.48, -0.62, 0.42), ease(seg(t, land, land + 0.8))), (0.0, 0.2, 0.22), lens=34, f=f)


FN = dict(rua=rua, calendario=calendario, cofre=cofre, parque=parque, corrida=corrida, praca=praca, interrogatorio=interrogatorio, quarto=quarto)

# ---- Walk the video. Each step sets the world from scratch, then only what changed gets keyed.
cuts = {fr(s[1]) for s in SHOTS}
frames = sorted(set(range(1, FRAMES + 1, 2)) | cuts)
which = {}
tracks = {}
from bpy_extras.object_utils import world_to_camera_view
for f in frames:
    t = START + (f - 1) / FPS
    reset()
    name, _ = shot_at(t)
    which[f] = name
    FN[name](t, f, origin(name))
    for n in HEROES:
        r = OB["CH_" + n]
        K(r, "location", tuple(r.location), f)
        K(r, "rotation_euler", tuple(r.rotation_euler), f)
        key_arm(OB[n + "_arm"], f)
    for n in CROWD:
        key_arm(OB[n + "_arm"], f)
    for p in PIECES:
        K(OB[p], "delta_location", tuple(OB[p].delta_location), f)
        K(OB[p], "hide_render", OB[p].hide_render, f)
    for m in MOVERS:
        K(OB[m], "location", tuple(OB[m].location), f)
        K(OB[m], "rotation_euler", tuple(OB[m].rotation_euler), f)
        K(OB[m], "scale", tuple(OB[m].scale), f)
    for fig, i in STATE["faces"].items():
        nt = bpy.data.materials[f"{fig}_Face"].node_tree
        for k in range(1, len([n for n in nt.nodes if n.name.startswith("face")]) + 1):
            K(nt.nodes[f"face{k}"].outputs[0], "default_value", 1.0 if i == k else 0.0, f)
    p, rot, lens, fstop, dist = STATE["cam"]
    K(cam, "location", tuple(p), f)
    K(cam, "rotation_euler", tuple(rot), f)
    K(cam.data, "lens", lens, f)
    K(cam.data.dof, "aperture_fstop", fstop, f)
    K(cam.data.dof, "focus_distance", dist, f)
    # Where the overlays should sit: a few points projected into the frame, 0 to 1 from the top left
    bpy.context.view_layer.update()
    pts = {}

    def track(key, co):
        q = world_to_camera_view(sc, cam, co)
        if q.z > 0:
            pts[key] = [round(q.x, 4), round(1 - q.y, 4)]

    for n in ("pardo", "israel", "pardo_rob"):
        arm = OB[n + "_arm"]
        if OB["CH_" + n].location.z > -40:
            track(n, arm.matrix_world @ arm.pose.bones[set_lib.bones_of(arm)["head"]].tail)
    if OB["joint_gag"].location.z > -40:
        track("joint", OB["joint_gag"].location)
    if name == "parque":
        track("bubble", OB["thought_bubble"].location)
    tracks[f] = pts
    if f % 60 == 1:
        print("keyed to frame", f, name, flush=True)

# Every key holds until the next one: that is the stop-motion look, and it keeps a parked figure from drifting in between keys.
# The preference for new keys isn't honoured in a headless build, so it's set on the keys themselves.
held = 0
for a in bpy.data.actions:
    if a.name.startswith("U_"):
        continue
    for layer in a.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for fc in bag.fcurves:
                    for kp in fc.keyframe_points:
                        kp.interpolation = "CONSTANT"
                        held += 1
print("keys set to hold:", held, flush=True)
json.dump({"frames": frames, "world": {str(f): which[f] for f in frames}}, open(os.path.join(WORK, "frames.json"), "w"))
json.dump({"_": "Screen positions of figures and props per keyed frame, 0 to 1 from the top left. Made by blender s08_shots.py, read by fx.mjs.",
           "frames": {str(f): tracks[f] for f in frames}}, open(os.path.join(ROOT, "src", "lego", "track.json"), "w"))
save()
print(f"=== SHOTS DONE: {len(frames)} frames to render", flush=True)
