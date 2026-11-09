# Shots for PARDÃO E A ERVA. apply(f) rebuilds the whole scene for video frame f (1-based) from timeline.json and
# cues.json: no keyframes. Poses step on twos (12 a second) like the old cartoons; cuts and gag hits land on their frame.
# Characters face -Y at rz = 0 (towards the camera side); rz = 90 faces +X.
import importlib
import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    HERE = os.path.join(os.environ.get("ERVA_ROOT", r"E:\Projetos\pardingows"), "src", "erva", "blender")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "shared"))  # blender_qa: measured seat fits
import set_lib, hose, snake, poses_toon as PT  # noqa: E402
for _m in (set_lib, hose, snake, PT):
    importlib.reload(_m)

ROOT = set_lib.ROOT
TL = json.load(open(os.path.join(ROOT, "src", "erva", "timeline.json"), encoding="utf8"))
STAGE = json.load(open(os.path.join(set_lib.WORK, "stage.json"), encoding="utf8"))
CAST = json.load(open(os.path.join(set_lib.WORK, "cast.json"), encoding="utf8"))
_cues = os.path.join(ROOT, "src", "erva", "cues.json")
CUE = json.load(open(_cues, encoding="utf8")) if os.path.exists(_cues) else {}
START, FPS, FRAMES = TL["start"], TL["fps"], TL["frames"]
BEAT, BEAT0 = 60 / TL["bpm"], TL["beat0"]
G, Y0, SP = CAST["pardo_ground_body_z"], CAST["lineup_y"], CAST["spacing"]
RIGS = ["P1", "VOVO", "EVA", "P2", "P3", "P4", "ALMA"]
OB = bpy.data.objects
SPOT = {k: Vector(v) for k, v in STAGE["spots"].items()}
SALA, TREVAS, SELVA = Vector(STAGE["sala"]), Vector(STAGE["trevas"]), Vector(STAGE["selva"])
SET_COLLS = {"sala": ["set_sala"], "trevas": ["set_trevas"], "selva": ["set_selva", "prop_flowers"],
             "assombrada": ["set_selva", "set_assombrada"]}
ALL_SETS = ["set_sala", "set_trevas", "set_selva", "prop_flowers", "set_assombrada"]
CUTS = [s["t"] for s in TL["shots"]]
MOMENT_NAMES = [s["moment"] for s in TL["shots"]]
BASE_SCALE = OB["P1"].scale.x
HOME = {p: Vector((i * SP, Y0, 0.035)) for i, p in enumerate(RIGS)}
PROPS = ["book_back", "pipe", "cigarette", "cigarette2", "joint", "sign", "register", "soul_jar", "trap", "hood", "spiral"] + \
        [o.name for o in OB if o.name.startswith(("smoke_ring", "smoke_puff"))]
PARK = {n: OB[n].location.copy() for n in PROPS if n in OB}


# ---------------------------------------------------------------- small maths
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def lerp(a, b, x):
    return a + (b - a) * x


def vlerp(a, b, x):
    return Vector(a).lerp(Vector(b), x)


def back_out(x, k=1.70158):
    """Overshoots then settles: the cartoon 'pop'."""
    x = clamp(x) - 1
    return x * x * ((k + 1) * x + k) + 1


def song_t(f):
    return START + (f - 1) / FPS


def twos(t):
    """Poses and moves hold for two frames, like 1930s animation on twos."""
    n = math.floor((t - START) * FPS / 2 + 1e-6) * 2
    return START + n / FPS


def beat(t):
    b = (t - BEAT0) / BEAT
    return b, b - math.floor(b)


def bounce(t, amp=1.0):
    """0..1..0 on every beat, peaking at the beat: the whole world bobs to the music."""
    _, ph = beat(t)
    return amp * (1 - abs(math.sin(math.pi * ph)) ** 0.6) if ph < 0.5 else amp * (1 - abs(math.sin(math.pi * ph)) ** 0.6)


def moment_at(t):
    i = 0
    for k, c in enumerate(CUTS):
        if t >= c - 1e-6:
            i = k
    return i, MOMENT_NAMES[i], t - CUTS[i]


def syl(card, row, word, k=0):
    """Song time of a syllable: card index (0-based), row, word, syllable."""
    return TL["cards"][card]["rows"][row][word][2][k]


# ---------------------------------------------------------------- scene state
def show(*names):
    want = {c for n in names for c in SET_COLLS[n]}
    for c in ALL_SETS:
        coll = bpy.data.collections[c]
        coll.hide_render = coll.hide_viewport = c not in want
    garden = "assombrada" not in names
    for o in bpy.data.collections["set_selva"].objects:
        if o.get("garden"):
            o.hide_render = o.hide_viewport = not garden


def world(v):
    """The sky's grey as it shows on screen (0 black .. 1 white), converted to the linear value Blender wants."""
    lin = max(0.0, v) ** 2.2
    bg = bpy.context.scene.world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (lin, lin, lin, 1)


def haze(v, amount=0.55, near=7.0, far=30.0):
    """Distance haze on the sets (never the cast): far things fade towards grey v (on screen) by up to 'amount'."""
    g = bpy.data.node_groups.get("erva_haze")
    if not g:
        return
    lin = max(0.0, v) ** 2.2
    g.nodes["haze_color"].outputs[0].default_value = (lin, lin, lin, 1)
    g.nodes["haze_amount"].outputs[0].default_value = amount
    mr = g.nodes["haze_range"]
    mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = near, far


def reset():
    """Everyone back to the lineup, standing; props parked; soul layer off."""
    for p in RIGS:
        r = OB[p]
        r.location = HOME[p]
        r.rotation_euler = (0, 0, 0)
        r.scale = (BASE_SCALE,) * 3
        PT.pose_pardo(p, PT.STAND, G)
    for n, loc in PARK.items():
        o = OB[n]
        o.location = loc
        o.rotation_euler = (0, 0, 0)
        o.scale = (1, 1, 1)
        o.hide_render = o.hide_viewport = False
    for n in ("book_cover", "book_page_left"):
        OB[n].rotation_euler = (0, 0, 0)
    # set pieces the moments squash, sway, pop or move go back to how they were built
    for c in ("set_sala", "set_selva", "set_assombrada", "prop_flowers"):
        for o in bpy.data.collections[c].objects:
            if "s0" in o:
                o.scale = (o["s0"],) * 3
                o.rotation_euler.y = 0.0
            if o.name.startswith("flower") and "_" not in o.name:
                o.rotation_euler = (0, 0, 0)
    OB["COBRA_hat"].location = (0.015, -0.005, 0.128)
    OB["COBRA_hat"].rotation_euler = (math.radians(22), math.radians(12), 0)
    OB["jar_cork"].location = (0, 0, 0)
    OB["register_tab"].location = (0, -0.1, 0.62)
    OB["trap_crate"].location = (0, 0, 0)
    OB["trap_crate"].rotation_euler = (0, 0, 0)
    OB["trap_stick"].location = (0, 0, 0)
    OB["trap_stick"].rotation_euler = (0, 0, 0)
    OB["spooky_moon"].scale = (1, 1, 1)
    snake.pose(**snake.stand((len(RIGS) * SP, Y0, 0), (0, -1, 0)))
    OB["COBRA_hat"].hide_render = OB["COBRA_hat"].hide_viewport = False
    OB["joint"].hide_render = OB["joint"].hide_viewport = False
    globals().get("SEAT_SHIN", {}).clear()
    soul(False)
    finish(RIGS)  # the hose limbs are world-space curves: they have to follow their rigs home


def soul(on):
    vl = bpy.context.scene.view_layers.get("soul")
    if vl:
        vl.use = on


def rig(p, at, rz=0.0, pose=None, scale=1.0, lift=0.0):
    if pose is not None and p in globals().get("SEAT_SHIN", {}):
        pose = {**pose, "shinR": (SEAT_SHIN[p], 0, 0), "shinL": (SEAT_SHIN[p], 0, 0)}
    r = OB[p]
    base = at[2] if len(at) > 2 else 0.0  # a raised point (a jar, a seat) lifts the rig by its height
    r.location = (at[0], at[1], base + 0.035 + lift)
    r.rotation_euler = (0, 0, math.radians(rz))
    r.scale = (BASE_SCALE * scale,) * 3
    PT.pose_pardo(p, pose or PT.STAND, G)


def finish(used):
    """After posing: evaluate, then re-shape the rubber-hose limbs of the rigs in the shot."""
    bpy.context.view_layer.update()
    soul_vl = bpy.context.scene.view_layers.get("soul")
    for p in used:
        if p == "ALMA" and soul_vl is not None:  # excluded from the main layer: evaluate it in its own
            soul_vl.update()
            hose.update(p, soul_vl.depsgraph)
        else:
            hose.update(p)


def cam(pos, target, lens=35.0, roll=0.0):
    c = OB["CAM"]
    c.location = pos
    d = Vector(target) - Vector(pos)
    q = d.to_track_quat("-Z", "Y")
    c.rotation_euler = (q @ Matrix.Rotation(math.radians(roll), 4, "Z").to_quaternion()).to_euler()
    c.data.lens = lens
    c.data.shift_y = -0.12  # characters ride high in the frame: the bottom is the captions' ground


def hand(p, side="R", along=0.62):
    """World point in the palm of a rig's glove (along the hand bone, glove scale included)."""
    arm = OB[p + "_arm"]
    pb = arm.pose.bones["Bone.004" if side == "R" else "Bone.011"]
    return arm.matrix_world @ pb.matrix @ Vector((0, along * 1.35, 0))


def facing(p):
    return (OB[p].matrix_world.to_3x3() @ Vector((0, -1, 0))).normalized()


def mouth(p):
    """The mouth: on the face's surface just under the nose, found by a ray from in front of the face."""
    n = OB[p + "_nose"]
    pts = [n.matrix_world @ Vector(v) for v in n.bound_box]
    c = sum(pts, Vector()) / 8
    up = (OB[p].matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()
    f = facing(p)
    low = min(pts, key=lambda q: q.dot(up))
    at = c + up * ((low - c).dot(up) - 0.015 * (OB[p].scale.x / BASE_SCALE))
    head = OB[p + "_head"]
    inv = head.matrix_world.inverted()
    o = at + f * 1.0
    hit, loc, _n, _i = head.ray_cast(inv @ o, (inv.to_3x3() @ -f).normalized())
    return head.matrix_world @ loc if hit else at


def head_top(p):
    h = OB[p + "_hat"]
    pts = [h.matrix_world @ Vector(v) for v in h.bound_box]
    return Vector((sum(q.x for q in pts) / 8, sum(q.y for q in pts) / 8, max(q.z for q in pts)))


def place(name, loc, rot=(0, 0, 0), s=1.0):
    o = OB[name]
    o.location = loc
    o.rotation_euler = [math.radians(a) for a in rot]
    o.scale = (s, s, s) if isinstance(s, (int, float)) else s


def in_hand(name, p, side="R", s=1.0, along=0.62, aim=None):
    """A prop held in a glove, pointing along aim (world) or out of the hand."""
    o = OB[name]
    at = hand(p, side, along)
    arm = OB[p + "_arm"]
    pb = arm.pose.bones["Bone.004" if side == "R" else "Bone.011"]
    d = Vector(aim) if aim is not None else (arm.matrix_world.to_3x3() @ pb.matrix.to_3x3() @ Vector((0, 1, 0)))
    q = d.normalized().to_track_quat("Y", "Z")
    o.matrix_world = Matrix.Translation(at) @ q.to_matrix().to_4x4() @ Matrix.Scale(s, 4)


def smoke(prefix, items, t):
    """Smoke puffs or rings: items are (birth time, start point, drift, size, ring?) and age over 1.4 s."""
    rings = [n for n in PARK if n.startswith("smoke_ring")]
    puffs = [n for n in PARK if n.startswith("smoke_puff")]
    ri = pi = 0
    for born, at, drift, size, ring in items:
        age = t - born
        if age < 0 or age > 1.4:
            continue
        k = age / 1.4
        pos = Vector(at) + Vector(drift) * age + Vector((0, 0, 0.35 * age))
        sc = size * (0.35 + 1.2 * k) * (1 - 0.35 * k * k)
        if ring and ri < len(rings):
            place(rings[ri], pos, (90, 0, 0), sc)
            ri += 1
        elif pi < len(puffs):
            place(puffs[pi], pos, (0, 0, age * 40), (sc, sc * 0.8, sc * 0.85))
            pi += 1


def sway(o, t, amp=4.0, squash=0.04, phase=0.0, base_s=None):
    """Set dressing bobbing to the beat: a side sway and a squash on every beat."""
    b, ph = beat(t)
    s0 = base_s if base_s is not None else o.get("s0", o.scale.z)
    o["s0"] = s0
    o.rotation_euler.y = math.radians(amp * math.sin(math.pi * (b + phase)))
    q = squash * math.cos(math.pi * 2 * ph) * 0.5 + squash * 0.5
    o.scale = (s0 * (1 + q * 0.5), s0 * (1 + q * 0.5), s0 * (1 - q))


def dance_world(t, spooky=False):
    """Every tree, flower and stick of furniture keeps the beat (the 1930s 'everything dances' look)."""
    if spooky:
        for o in bpy.data.collections["set_assombrada"].objects:
            if o.name.startswith("spooky_tree"):
                sway(o, t, 6.0, 0.05, o.get("sway", 0.0))
            elif o.name.startswith("spooky_skeletons"):
                b, ph = beat(t)
                o.location.z = 0.12 * abs(math.sin(math.pi * b))
        return
    for o in bpy.data.collections["set_selva"].objects:
        if o.name.startswith("selva_tree"):
            sway(o, t, 3.0, 0.035, o.get("sway", 0.0))
        elif o.name.startswith(("selva_dress", "selva_front")):
            sway(o, t, 2.0, 0.04, o.get("sway", hash(o.name) % 7 * 0.3))
        elif o.name == "selva_apple":
            sway(o, t, 2.5, 0.03, 0.4)
    for k in range(3):
        root = OB[f"flower{k}"]
        b, ph = beat(t)
        root.rotation_euler = (0, math.radians(9 * math.sin(math.pi * b + k)), 0)
        OB[f"flower{k}_head"].rotation_euler = (math.radians(6 * math.sin(math.pi * 2 * b)), 0, 0)


# ---------------------------------------------------------------- the test stills (step 4)
def still(name):
    reset()
    if name == "sala":
        show("sala")
        world(0.4)
        rig("VOVO", SPOT["sala_vovo_seat"], rz=-12, pose={**PT.SIT, "glove": ("hold", "open")}, lift=0.36)
        rig("EVA", SPOT["sala_eva_seat"], rz=14, pose={**PT.SIT, "armR": (-40, -10, 0), "foreR": (-60, 0, 0)}, lift=0.36)
        finish(["VOVO", "EVA"])
        cam(SALA + Vector((0, -6.2, 1.7)), SALA + Vector((0, 0.8, 1.45)), lens=34)
    elif name == "trevas":
        show("trevas")
        world(0.0)
        rig("P1", TREVAS, rz=0, pose=PT.WALK[0])
        finish(["P1"])
        cam(TREVAS + Vector((0, -6.0, 1.3)), TREVAS + Vector((0, 0, 1.1)), lens=30)
    elif name == "selva":
        show("selva")
        world(0.82)
        haze(0.82)
        dance_world(START)
        rig("P1", SELVA + Vector((-0.4, -0.2, 0)), rz=-20, pose=PT.STAND)
        snake.pose(**snake.stand(SELVA + Vector((0.55, 0.0, 0)), (-1, -0.6, 0)))
        finish(["P1"])
        cam(SELVA + Vector((0.1, -6.8, 1.45)), SELVA + Vector((0.1, 1.5, 1.35)), lens=30)
    elif name == "assombrada":
        show("assombrada")
        world(0.08)
        haze(0.1, amount=0.5, near=5)
        dance_world(START, spooky=True)
        rig("P1", SELVA + Vector((-0.6, -0.3, 0)), rz=-15, pose=PT.SCARED)
        snake.pose(**snake.giant(SELVA + Vector((0.6, 1.0, 0)), (-0.5, -1, 0)))
        finish(["P1"])
        cam(SELVA + Vector((0.0, -8.0, 2.0)), SELVA + Vector((0.0, 2.0, 3.2)), lens=26)


# ================================================================ staging helpers: measured, never guessed
# Facing comes from where the other character is (face_rz), hands go where they must by solving the arm (ik.reach),
# sitting comes from the chair's measured seat and backrest (seat), props in mouths use the mouth found on the face
# (mouth), and two-shots are spaced by the characters' real widths (a Pardo is ~1 m ear to ear).
import ik  # noqa: E402
importlib.reload(ik)

UP = Vector((0, 0, 1))
PARDO_HALF_W = 0.5   # half the ear-to-ear width, metres
COBRA_GAP = 1.35     # Pardo centre to cobra base in a two-shot


def flat(v):
    v = Vector(v).copy()
    v.z = 0
    return v.normalized() if v.length > 1e-9 else Vector((0, -1, 0))


def face_rz(frm, to, bias=0.0, cam_at=None):
    """rz in degrees for a rig at 'frm' to face 'to'. A rig faces -Y at rz 0 and +X at rz +90. bias turns it that
    fraction of the ANGLE towards the camera (blending the vectors barely turns it). A Pardo in profile hides his face
    behind his own ear, so two-shots use ~0.5: a three-quarter view that still reads as facing the other."""
    d = flat(Vector(to) - Vector(frm))
    a = math.atan2(d.x, -d.y)
    if cam_at is not None and bias:
        c = flat(Vector(cam_at) - Vector(frm))
        b = math.atan2(c.x, -c.y)
        a += math.atan2(math.sin(b - a), math.cos(b - a)) * bias
    return math.degrees(a)


def right_of(p):
    """The rig's own +X ('R' side) in world space."""
    return (OB[p].matrix_world.to_3x3().normalized() @ Vector((1, 0, 0))).normalized()


def side_towards(p, point):
    return "R" if (Vector(point) - OB[p].matrix_world.translation).dot(right_of(p)) > 0 else "L"


def other(side):
    return "L" if side == "R" else "R"


def reach(p, side, target, pose, keep_up=0.0):
    out, _err = ik.reach(p, side, target, pose, keep_up)
    return out


def apply_pose(p, pose):
    if p in SEAT_SHIN:  # a seated rig keeps the shins its seat fit chose
        pose = {**pose, "shinR": (SEAT_SHIN[p], 0, 0), "shinL": (SEAT_SHIN[p], 0, 0)}
    PT.pose_pardo(p, pose, G)


def torso_centre(p):
    t = OB[p + "_torso"]
    pts = [t.matrix_world @ v.co for v in t.data.vertices]
    return sum(pts, Vector()) / len(pts)


def cam_pos():
    return OB["CAM"].location.copy()  # the value just set: matrix_world only updates on the next evaluation


# ---------------------------------------------------------------- chairs: measured seat and backrest
_CHAIRS = {}


def chair_frame(name):
    """Seat height, which way the chair faces and where its backrest is, measured from the model's vertices."""
    if name not in _CHAIRS:
        m = set_lib.chair_measure(OB[name])
        _CHAIRS[name] = {"c": m["centre"], "front": -m["back"], "seat": m["seat"], "back": m["back_d"]}
    return _CHAIRS[name]


SEAT_SHIN = {}  # rigs seated this frame -> the shin angle the fit chose (apply_pose keeps it)
_SEATS = {}
HARD = ("torso", "pelvis", "head", "hat", "ears", "nose", "beard", "shades", "chain", "medallion", "eyes", "pearls")


def _chair_solid(chair):
    import blender_qa as Q  # noqa: E402
    key = ("solid", chair)
    if key not in _SEATS:
        _SEATS[key] = Q.Solid([OB[chair]], bpy.context.evaluated_depsgraph_get())
    return _SEATS[key]


def _crossing(p, chair, parts):
    import blender_qa as Q  # noqa: E402
    bpy.context.view_layer.update()
    objs = [o for o in Q.group([p]) if o.name[len(p) + 1:].split(".")[0].startswith(parts)]
    return Q.crossing(Q.Solid(objs, bpy.context.evaluated_depsgraph_get()), _chair_solid(chair))[0]


def _fit_seat(p, chair, rz, pose):
    """Hips on the measured seat, then slid forward until no hard part (body, head, hat) crosses the chair, then the
    shins swung forward until the shoes clear the chair's front. Measured with the QA's surface crossings."""
    F = chair_frame(chair)
    push, lift, shin = 0.0, 0.3, pose.get("shinR", (82, 0, 0))[0]
    for _ in range(3):
        rig(p, F["c"] + F["front"] * push, rz=rz, pose=pose, lift=lift)
        bpy.context.view_layer.update()
        arm = OB[p + "_arm"]
        hips = [(arm.matrix_world @ arm.pose.bones[b].head).z for b in ("Bone.005", "Bone.012")]
        lift += (F["seat"] + hose.LEG_R + 0.015) - sum(hips) / 2
    while push < 0.45 and _crossing(p, chair, HARD) > 0.03:
        push += 0.025
        rig(p, F["c"] + F["front"] * push, rz=rz, pose=pose, lift=lift)
    for shin in (shin, 70, 60, 50, 40, 30):
        q = {**pose, "shinR": (shin, 0, 0), "shinL": (shin, 0, 0)}
        rig(p, F["c"] + F["front"] * push, rz=rz, pose=q, lift=lift)
        if _crossing(p, chair, ("shoe",)) < 0.03:
            break
    return push, lift, shin


def seat(p, chair, pose, turn=0.0):
    """Sits a rig in a chair (fit measured once per rig and chair, then reused). Returns its rz."""
    F = chair_frame(chair)
    rz = math.degrees(math.atan2(F["front"].x, -F["front"].y)) + turn
    key = (p, chair, round(turn, 1))
    if key not in _SEATS:
        SEAT_SHIN.pop(p, None)
        _SEATS[key] = _fit_seat(p, chair, rz, {**PT.SIT, "glove": ("open", "open")})
    push, lift, shin = _SEATS[key]
    SEAT_SHIN[p] = shin
    rig(p, F["c"] + F["front"] * push, rz=rz, pose=pose, lift=lift)
    bpy.context.view_layer.update()
    return rz


# ---------------------------------------------------------------- props held and smoked
def frame_from(y_axis, origin, scale=1.0):
    """A matrix whose +Y runs along y_axis, X kept level."""
    y = Vector(y_axis).normalized()
    x = y.cross(UP)
    if x.length < 1e-6:
        x = Vector((1, 0, 0))
    x.normalize()
    z = x.cross(y).normalized()
    return Matrix.Translation(origin) @ Matrix((x, y, z)).transposed().to_4x4() @ Matrix.Scale(scale, 4)


JOINT_S, CIG_S = 1.6, 1.6
JOINT_LEN = 0.155 * JOINT_S  # ember at its origin, the twisted end at +Y
CIG_LEN = 0.12 * CIG_S       # mouth end at its origin, the ember at +Y


def joint_at(mouth_pt, out_dir):
    """The joint between the lips: twisted end at the mouth, ember out along out_dir."""
    out_dir = Vector(out_dir).normalized()
    OB["joint"].matrix_world = frame_from(-out_dir, mouth_pt + out_dir * JOINT_LEN, JOINT_S)
    OB["joint"].hide_render = OB["joint"].hide_viewport = False


def joint_mid():
    return OB["joint"].matrix_world @ Vector((0, 0.0775, 0))


def cig_at(name, mouth_pt, out_dir):
    OB[name].matrix_world = frame_from(out_dir, mouth_pt, CIG_S)


def smoke_dir(p, away_from=None, down=0.15):
    """Out of the side of the mouth that the camera sees, away from whoever is next to him."""
    f = facing(p)
    to_cam = flat(cam_pos() - OB[p].matrix_world.translation)
    d = f * 0.45 + to_cam * 0.7
    if away_from is not None:
        d += flat(OB[p].matrix_world.translation - Vector(away_from)) * 0.35
    d.z -= down
    return d.normalized()


_PIPE = None


def pipe_geom():
    """The pipe's mouthpiece and bowl in its root's space (measured from the model)."""
    global _PIPE
    if _PIPE:
        return _PIPE
    objs = [o for o in bpy.data.collections["AS_cachimbo"].all_objects if o.type == "MESH"]
    vs = [o.matrix_world @ v.co for o in objs for v in o.data.vertices]
    x0, x1 = min(v.x for v in vs), max(v.x for v in vs)
    w = (x1 - x0) * 0.1
    top = lambda xe: max(v.z for v in vs if abs(v.x - xe) < w)
    bowl_x, mouth_x = (x0, x1) if top(x0) > top(x1) else (x1, x0)
    near_m = [v for v in vs if abs(v.x - mouth_x) < w]
    mz = sum(v.z for v in near_m) / len(near_m)
    near_b = [v for v in vs if abs(v.x - bowl_x) < w * 1.5]
    bz = sum(v.z for v in near_b) / len(near_b)
    m = OB["pipe_model"].matrix_basis
    _PIPE = (m @ Vector((mouth_x, 0, mz)), m @ Vector((bowl_x, 0, bz)))
    return _PIPE


PIPE_S = 1.1


def pipe_at(mouth_pt, out_dir):
    """The pipe's mouthpiece at mouth_pt, its bowl out along out_dir (kept upright). Returns the grip point by the bowl."""
    ml, bl = pipe_geom()
    u = (bl - ml).normalized()
    e3 = (Vector((0, 0, 1)) - u * u.z).normalized()
    e2 = e3.cross(u)
    d = Vector(out_dir).normalized()
    E3 = (UP - d * d.z).normalized()
    E2 = E3.cross(d)
    R = Matrix((d, E2, E3)).transposed() @ Matrix((u, e2, e3))
    root = OB["pipe"]
    root.matrix_world = Matrix.Translation(mouth_pt) @ R.to_4x4() @ Matrix.Scale(PIPE_S, 4) @ Matrix.Translation(-ml)
    return root.matrix_world @ (ml + (bl - ml) * 0.72)


def pipe_held(grip_pt, out_dir):
    """The pipe in a hand: the grip at grip_pt, mouthpiece pointing back along -out_dir."""
    ml, bl = pipe_geom()
    L = (bl - ml).length * PIPE_S * 0.72
    return pipe_at(Vector(grip_pt) - Vector(out_dir).normalized() * L, out_dir)


# ---------------------------------------------------------------- the cobra
def cobra_mouth():
    return OB["COBRA_head"].matrix_world @ Vector((0, 0.3, -0.01))


def cobra_head_pt():
    return OB["COBRA_head"].matrix_world @ Vector((0, 0.12, 0.08))


def snake_two_shot(base, towards, t, height=1.12, bias=0.35):
    """The cobra up on its coil at base, looking at 'towards' (a point), turned a little to the camera."""
    f = flat(Vector(towards) - Vector(base)) * (1 - bias) + flat(cam_pos() - Vector(base)) * bias
    st = snake.stand(base, flat(f), height=height, sway=0.4 * math.sin(t * 3))
    return st


def lean_path(base, head, look_at, tail_tip=None, k_tail=0.0):
    """The cobra coiled at base with its neck arched up to 'head'; the tail lies on the ground, or rises to tail_tip."""
    base, head = Vector(base), Vector(head)
    d = flat(head - base)
    lat = UP.cross(d).normalized()
    pts = [head]
    for k in range(1, 7):  # neck: a smooth arch from the head down to the coil
        u = k / 6
        p = head.lerp(base + Vector((0, 0, 0.07)), u)
        p += Vector((0, 0, 0.18 * math.sin(math.pi * u))) - d * (0.12 * math.sin(math.pi * u))
        pts.append(p)
    for k in range(1, 7):  # the coil round the base
        a = k / 6 * math.pi * 1.4
        pts.append(base + lat * (0.22 * math.cos(a)) - d * (0.22 * math.sin(a)) + Vector((0, 0, 0.07)))
    end = pts[-1]
    lie = end + lat * 0.25 + d * 0.15
    if tail_tip is not None and k_tail > 0:
        tip = Vector(tail_tip)
        mid = end.lerp(tip, 0.5) + Vector((0, 0, 0.12))
        pts += [end.lerp(mid, k_tail * 0.9 + 0.1).lerp(lie, 1 - k_tail), lie.lerp(tip, k_tail)]
    else:
        pts.append(lie)
    look = flat(Vector(look_at) - head) - Vector((0, 0, 0.12))
    return dict(path=pts, look=look)


# ================================================================ the 16 moments
def path_y(x):
    """The garden path's centre line (s05_sets.path_strip)."""
    return SELVA.y + 0.6 * math.sin((x - SELVA.x) * 0.45) - 0.2


def on_path(x, dy=0.0):
    return Vector((x, path_y(x) + dy, 0))


def syl_times(card, row=None):
    c = TL["cards"][card]
    rows = c["rows"] if row is None else [c["rows"][row]]
    return [s for r in rows for w in r for s in w[2]]


def adlib_times(card):
    return [s for w in TL["cards"][card].get("adlib", []) for s in w[2]]


def nod(t, times, amp=10.0):
    """Head nods on sung syllables: a quick dip that eases back."""
    v = 0.0
    for s in times:
        a = t - s
        if 0 <= a < 0.18:
            v = max(v, math.sin(a / 0.18 * math.pi))
    return amp * v


def walk_key(t, period=0.8):
    """Which of the four walk keys is up: a stride takes two beats, a key every half beat."""
    k = int(math.floor((t - BEAT0) / (period / 4))) % 4
    return PT.WALK[k]


def pop(o, t0, t, dur=0.35, base=None):
    """Scales a thing up out of nowhere with an overshoot (the pop-up book)."""
    s0 = base if base is not None else o.get("s0", o.scale.z)
    o["s0"] = s0
    k = back_out((t - t0) / dur) if t >= t0 else 0.0
    if k <= 0.001:
        o.scale = (0.0001, 0.0001, 0.0001)
    else:
        cur = o.scale.copy()
        f = k * s0 / max(cur.z, 1e-6) if cur.z > 0 else k
        o.scale = (cur.x * f, cur.y * f, cur.z * f)
    return k


def hide(name, on=True):
    OB[name].hide_render = OB[name].hide_viewport = on


def garden(t, light=0.82):
    show("selva")
    world(light)
    haze(light)
    dance_world(t)


def spooky(t):
    show("assombrada")
    world(0.06)
    haze(0.12, amount=0.5, near=5)
    dance_world(t, spooky=True)


def room(t):
    show("sala")
    world(0.3)
    haze(0.5, amount=0.0)
    b, ph = beat(t)
    for k in range(3):  # the flames dance
        o = OB[f"sala_flame{k}"]
        s = 1 + 0.18 * math.sin(math.pi * 2 * (b + k * 0.33))
        o.scale = (1 / s ** 0.5, 1, s)
    for n, amp in (("sala_clock", 0.04), ("sala_gramophone", 0.08), ("sala_clock_face", 0.04)):
        o = OB[n]
        q = amp * (1 - abs(math.sin(math.pi * ph)))
        s0 = o.get("s0", o.scale.z)
        o["s0"] = s0
        o.scale = (s0 * (1 + q * 0.5), s0 * (1 + q * 0.5), s0 * (1 - q))


TALK = -12


def book_frame(p, lift=0.0):
    """Where the book sits for a seated rig: in front of its tummy, cover facing out and up to the camera."""
    c = torso_centre(p)
    f = facing(p)
    n = (f + UP * 0.45).normalized()
    y = right_of(p)
    y = (y - n * y.dot(n)).normalized()
    x = y.cross(n)
    centre = c + f * 0.36 - UP * (0.1 - lift)
    m = Matrix((x, y, n)).transposed().to_4x4()
    return centre, x, y, n, Matrix.Translation(centre - x * 0.125 - n * 0.025) @ m


def place_book(p, open_k, hands=("R", "L"), pose=None, lift=0.0):
    """Puts the book in the rig's hands (both, or one holding its edge) and opens its cover by open_k (0..1)."""
    centre, x, y, n, m = book_frame(p, lift)
    OB["book_back"].matrix_world = m
    OB["book_cover"].rotation_euler = (0, math.radians(-175 * min(open_k, 1.05)), 0)
    pose = dict(pose)
    for s in hands:
        edge = centre + (y if s == "R" else -y) * 0.19 - n * 0.02
        pose = reach(p, s, edge, pose)
    return pose


def book_page():
    return OB["book_back"].matrix_world @ Vector((0.125, 0.0, 0.05))


def eva_seat_pose(t, extra=None):
    pose = {**PT.SIT, "head": (-6, 0, -22)}
    if extra:
        pose.update(extra)
    return pose


def m_conto(t, dt):
    room(t)
    t_open = syl(0, 1, 1)  # "par-dão": the book opens
    k = smooth(dt / 3.6)
    cam(SALA + vlerp((0.05, -5.5, 1.05), (-0.3, -4.4, 1.0), k), SALA + vlerp((0.05, 0.6, 1.0), (-0.4, 0.5, 0.85), k), lens=32)
    pose = {**PT.SIT, "head": (TALK + nod(t, syl_times(0)), 0, 0)}
    seat("VOVO", "sala_rocking", pose)
    pose = place_book("VOVO", back_out((t - t_open) / 0.45, 1.2) if t >= t_open else 0.0, pose=pose)
    apply_pose("VOVO", pose)
    seat("EVA", "sala_wingchair", eva_seat_pose(t), turn=-8)
    finish(["VOVO", "EVA"])
    return ["VOVO", "EVA"]


def m_cachimbo(t, dt):
    room(t)
    puff = syl(1, 0, 5)       # "pu-xe": Vovô draws on the pipe
    hand_over = syl(1, 1, 1)  # "ca-chim-bo": passes it to Eva
    eva_puff = syl(1, 1, 4)   # "E-va"
    mnham = adlib_times(1)
    dive = smooth((t - (CUTS[2] - 0.45)) / 0.45)
    base_pos, base_tgt = SALA + Vector((0.05, -5.4, 1.05)), SALA + Vector((0.05, 0.5, 0.9))
    cam(base_pos, base_tgt, lens=36)  # set now for the props' camera side; the dive is applied at the end
    vpose = {**PT.SIT, "head": (TALK + nod(t, syl_times(1)), 0, 0)}
    vrz = seat("VOVO", "sala_rocking", vpose)
    erz = seat("EVA", "sala_wingchair", eva_seat_pose(t), turn=-8)
    # Vovô keeps the open book in his left hand all through, held out to us
    vpose = place_book("VOVO", 1.0, hands=("L",), pose=vpose)
    epose = eva_seat_pose(t)
    hand_k = smooth((t - (hand_over - 0.35)) / 0.35)  # the pipe travels from his hand to hers
    if t < hand_over - 0.35:
        holder = "VOVO"
        mp = mouth("VOVO")
        if t >= puff - 0.2:   # drawing on it
            grip = pipe_at(mp, smoke_dir("VOVO", away_from=OB["EVA"].location, down=0.35))
        else:                 # holding it by his chest
            grip = pipe_held(mp + facing("VOVO") * 0.25 - UP * 0.32 + right_of("VOVO") * 0.12,
                             facing("VOVO") * 0.6 + UP * 0.8)
        vpose = reach("VOVO", "R", grip, vpose)
    else:
        mid = (mouth("VOVO") + mouth("EVA")) / 2 - UP * 0.12 + facing("VOVO") * 0.1  # above her knees
        if hand_k < 1:
            across = flat(OB["EVA"].matrix_world.translation - OB["VOVO"].matrix_world.translation)
            grip = pipe_held(mid, across + UP * 0.6)
            if hand_k < 0.5:   # held out at arm's length...
                vpose = reach("VOVO", "R", grip, vpose)
            else:              # ...and taken from the air
                epose = reach("EVA", "L", grip, epose)
        else:
            me = mouth("EVA")
            puffing = any(0 <= t - m < 0.3 for m in [eva_puff] + mnham)
            if puffing:
                grip = pipe_at(me, smoke_dir("EVA", away_from=OB["VOVO"].location, down=0.35))
            else:
                grip = pipe_held(me + facing("EVA") * 0.25 - UP * 0.3 - right_of("EVA") * 0.1,
                                 facing("EVA") * 0.6 + UP * 0.8)
            epose = reach("EVA", "L", grip, epose)
            epose["head"] = (-10 - 6 * float(puffing), 0, -10)
    apply_pose("VOVO", vpose)
    apply_pose("EVA", epose)
    finish(["VOVO", "EVA"])
    rings = [(puff + 0.25, mouth("VOVO"), (0.05, 0, 0), 0.09, True)]
    rings += [(m + 0.05, mouth("EVA") + Vector((-0.1, 0, 0.05)), (-0.06, 0.02, 0), 0.08, True) for m in [eva_puff] + mnham]
    smoke("sala", rings, t)
    # the last half second: the camera dives into the open book's page
    pg = book_page()
    nrm = (OB["book_back"].matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()
    cam(vlerp(base_pos, pg + nrm * 0.12, dive ** 1.6), vlerp(base_tgt, pg, dive), lens=lerp(36, 30, dive))
    return ["VOVO", "EVA"]


def spotlight(x):
    OB["trevas_spot"].location = (x - TREVAS.x, 0, 0)
    OB["trevas_beam"].location = (x - TREVAS.x, 0, 0)


def eyes_blink(t):
    for o in bpy.data.collections["set_trevas"].objects:
        if o.name.startswith("trevas_eyes"):
            ph = (t * 0.7 + o["blink"]) % 2.3
            o.scale = (1, 1, 0.08 if ph < 0.12 else 1)


def m_trevas(t, dt):
    show("trevas")
    world(0.0)
    eyes_blink(t)
    x = TREVAS.x - 1.3 + 0.8 * dt
    stop = syl(2, 1, 2, 0)  # "me-re-tre-vaz": he stops and looks round
    if t < stop:
        pose = dict(walk_key(t))
        rz = 60
    else:
        look = math.sin((t - stop) * 7) * 35
        pose = {**PT.SCARED, "body": (0, 0, 0, 0, 0, 0), "armR": (-60, -30, 0), "foreR": (-90, 0, 0), "armL": (-60, 30, 0),
                "foreL": (-90, 0, 0), "head": (-6, 0, look), "glove": ("open", "open")}
        x = TREVAS.x - 1.3 + 0.8 * (stop - CUTS[2])
        rz = 20
    cam(Vector((x + 0.25, TREVAS.y - 6.2, 1.35)), Vector((x + 0.1, TREVAS.y, 1.0)), lens=30)
    rig("P1", (x, TREVAS.y), rz=rz, pose=pose)
    finish(["P1"])
    spotlight(x)
    return ["P1"]


def m_selva(t, dt):
    step1, step2 = syl(3, 0, 2, 0), syl(3, 0, 4, 0)  # "pas-so", "fren-te": two giant steps
    jungle = step2 + 0.05
    x0 = SELVA.x - 0.6
    x = x0 + 0.45 * smooth((t - step1 + 0.15) / 0.3) + 0.45 * smooth((t - step2 + 0.15) / 0.3)
    big = {"body": (0, 0, 0.9, 0, 0, 0), "spine": (-10, 0, 0), "head": (-8, 0, 0), "armR": (40, -40, 0), "foreR": (-40, 0, 0),
           "armL": (-80, 40, 0), "foreL": (-40, 0, 0), "thighR": (-95, 0, 0), "shinR": (110, 0, 0), "thighL": (25, 0, 0),
           "shinL": (20, 0, 0), "glove": ("open", "open")}
    big2 = {**big, "armR": big["armL"], "armL": big["armR"], "thighR": big["thighL"], "shinR": big["shinL"],
            "thighL": big["thighR"], "shinL": big["shinR"]}
    if t < jungle:
        show("trevas")
        world(0.0)
        eyes_blink(t)
        pose = big if (step1 - 0.2 <= t < step1 + 0.1) else big2 if (step2 - 0.2 <= t < step2 + 0.1) else PT.STAND
        tx = TREVAS.x + (x - x0) - 0.4
        cam(TREVAS + Vector((0.0, -5.6, 1.3)), TREVAS + Vector((0.0, 0, 1.0)), lens=32)
        rig("P1", (tx, TREVAS.y), rz=10, pose=pose)
        finish(["P1"])
        spotlight(tx)
        return ["P1"]
    garden(t)
    for o in bpy.data.collections["set_selva"].objects:  # the pop-up book: everything springs up, nearest first
        if o.get("garden") and o.instance_type == "COLLECTION":
            d = abs(o.location.x - x) * 0.06 + max(0.0, o.location.y) * 0.02
            pop(o, jungle + d, t)
    for k in range(3):
        pop(OB[f"flower{k}"], jungle + 0.1 + 0.07 * k, t, base=1.0)
    k = smooth((t - jungle) / 1.2)
    cam(vlerp((x + 0.1, -5.6, 1.3), (x + 0.2, -7.0, 1.6), k), vlerp((x, 0.5, 1.0), (x + 0.2, 1.5, 1.5), k), lens=lerp(32, 28, k))
    amazed = {**PT.SHRUG, "head": (-10, 0, 25 * math.sin((t - jungle) * 4))}
    rig("P1", on_path(x), rz=0, pose=amazed if t > jungle + 0.3 else big2)
    finish(["P1"])
    return ["P1"]


def m_jardim(t, dt):
    garden(t)
    x = SELVA.x - 2.6 + 0.85 * dt
    look_back = syl(4, 1, 4, 0)  # "fi-nin": he glances back, the cobra freezes
    if t >= look_back:
        x = SELVA.x - 2.6 + 0.85 * (look_back - CUTS[4])
    enter = syl(4, 1, 1, 0)  # "co-bra"
    sx = x - 2.8 + 1.6 * smooth((t - enter) / 1.2)
    cam(Vector((x - 0.9, -6.7, 1.3)), Vector((x - 0.9, 1.0, 1.05)), lens=28)
    P = on_path(x, -0.3 * clamp((t - CUTS[4]) / 3.2))  # the walk cheats a little towards the camera
    if t < look_back:
        rig("P1", P, rz=58, pose=dict(walk_key(t)))  # three-quarter: in profile his ear hides his face
    else:
        rig("P1", P, rz=face_rz(P, on_path(sx, 0.4), 0.45, cam_pos()), pose={**PT.STAND, "head": (-4, 0, 0)})
    finish(["P1"])
    if t < look_back:
        snake.pose(**snake.sneak(on_path(sx, 0.4), (1, 0, 0), lift=0.55 + 0.05 * math.sin(t * 9)))
    else:  # frozen bolt upright, pretending to be a sapling
        st = snake.stand(on_path(sx, 0.4), (0, -1, 0), height=1.25)
        top = st["path"][0]
        st["path"] = [Vector((top.x, top.y, p.z)) if i < 9 else p for i, p in enumerate(st["path"])]
        snake.pose(**st)
    return ["P1"]


PX = SELVA.x - 0.9  # where Pardão stands for the conversation on the garden path


def two_shot_cam(px, gap=COBRA_GAP, dist=7.0, lens=32.0, h=1.15, tgt_h=1.0, lead=0.0):
    cx = px + gap * 0.45 + lead
    cam(Vector((cx, -dist, h)), Vector((cx, 0.8, tgt_h)), lens=lens)


def p1_and_cobra(t, pose, gap=COBRA_GAP, bias=0.5, height=1.12, sdy=0.3):
    """Pardão on the path facing the cobra, the cobra up on its coil facing him; both turned a little to the camera."""
    P = on_path(PX)
    S = on_path(PX + gap, sdy)
    rig("P1", P, rz=face_rz(P, S, bias, cam_pos()), pose=pose)
    bpy.context.view_layer.update()
    snake.pose(**snake_two_shot(S, mouth("P1"), t, height=height))
    return P, S


def joint_in_cobra_mouth():
    m = cobra_mouth()
    to_p1 = flat(OB["P1"].matrix_world.translation - m)
    joint_at(m, -to_p1 * 0.2 + flat(cam_pos() - m) * 0.9 - UP * 0.1)


def m_basiadin(t, dt):
    garden(t)
    two_shot_cam(PX)
    offer = syl(5, 1, 0, 0)  # "o-fe-re-ceu"
    sniff = adlib_times(5)
    P, S = p1_and_cobra(t, {**PT.STAND, "head": (-8, 0, 0)})
    tipk = math.sin(clamp((t - CUTS[5]) / 0.5) * math.pi)  # tips its hat as it arrives
    OB["COBRA_hat"].location = (0.015, -0.005 + 0.02 * tipk, 0.128 + 0.12 * tipk)
    OB["COBRA_hat"].rotation_euler = (math.radians(22 - 40 * tipk), math.radians(12), 0)
    finish(["P1"])
    bpy.context.view_layer.update()
    if t >= offer:  # the joint comes out from under the bowler and drops into its mouth
        k = smooth((t - offer) / 0.5)
        hd = OB["COBRA_head"].matrix_world
        top = hd @ Vector((0.0, 0.05, 0.3))
        if k < 1:
            OB["joint"].matrix_world = frame_from(Vector((1, 0, 0)), top.lerp(cobra_mouth(), k), JOINT_S)
        else:
            joint_in_cobra_mouth()
    for k in range(3):  # the flowers lean in to sniff on each mnham
        root = OB[f"flower{k}"]
        lean = max(math.sin(clamp((t - m) / 0.25) * math.pi) for m in sniff)
        root.rotation_euler = (math.radians(-18 * lean), math.radians((PX - root.location.x) * 12 * lean), 0)
    return ["P1"]


def m_caminho(t, dt):
    garden(t)
    two_shot_cam(PX)
    take = syl(6, 0, 0, 0)      # "par-dão": he takes it from the cobra's mouth
    drag = syl(6, 0, 2, 0)      # "pen-sar": first drag
    sign_t = syl(6, 1, 0, 0)    # "a-cei-tou": the signpost springs up
    spiral_t = syl(6, 1, 3, 0)  # "ca-mi-nho": the path curls into a spiral
    woozy = math.sin(t * 5) * 6 * smooth((t - drag) / 0.6)
    pose = {**PT.STAND, "body": (0, 0, 0, 0, woozy, 0), "head": (-8, 0, 0)}
    P, S = p1_and_cobra(t, pose)
    finish(["P1"])
    bpy.context.view_layer.update()
    near = side_towards("P1", S)
    if t < take:
        joint_in_cobra_mouth()
    else:
        to_mouth = smooth((t - (drag - 0.3)) / 0.3)
        mp = mouth("P1")
        out = smoke_dir("P1", away_from=S, down=0.35)
        if to_mouth < 1:  # in his hand, on its way to his mouth
            short = cobra_mouth() + flat(OB["P1"].matrix_world.translation - cobra_mouth()) * 0.24
            held = short.lerp(mp + out * 0.2, to_mouth)
            OB["joint"].matrix_world = frame_from(out, held - out * 0.5 * JOINT_LEN, JOINT_S)
            pose = reach("P1", near, held, pose)
        else:             # between his lips; the hand comes up to it on each drag
            joint_at(mp, out)
            drags = [drag + 0.7 * i for i in range(4)]
            if any(0 <= t - d < 0.3 for d in drags):
                pose = reach("P1", near, mp + out * (JOINT_LEN + 0.17) - UP * 0.08, pose)
        apply_pose("P1", pose)
        finish(["P1"])
    smoke("caminho", [(drag + 0.15 + 0.35 * i, mouth("P1") + smoke_dir("P1", away_from=S) * (JOINT_LEN + 0.05),
                       (0.1, -0.05, 0), 0.13, i % 2 == 0) for i in range(6)], t)
    OB["sign"].location = on_path(PX + 0.6, 1.05)
    pop(OB["sign"], sign_t, t, base=1.0)
    OB["sign"].rotation_euler = (0, 0, math.radians(360 * (1 - smooth((t - sign_t) / 0.7)) + 15))
    OB["spiral"].location = on_path(PX + 0.7, -0.75) + Vector((0, 0, 0.01))
    pop(OB["spiral"], spiral_t, t, dur=0.5, base=1.0)
    OB["spiral"].rotation_euler = (0, 0, t * 2.5)
    return ["P1"]


def m_da_boa(t, dt):
    garden(t)
    gap = 1.25
    two_shot_cam(PX, gap=gap, dist=5.6, lens=34, h=1.1, tgt_h=1.05)
    pose = {**PT.STAND, "head": (-6, 0, 0)}
    P = on_path(PX)
    S = on_path(PX + gap, 0.25)
    rig("P1", P, rz=face_rz(P, S, 0.5, cam_pos()), pose=pose)
    finish(["P1"])
    mp = mouth("P1")
    joint_at(mp, smoke_dir("P1", away_from=S, down=0.35))
    # the salesman: the neck arched over so its head is beside his face, close but not touching
    to_p = flat(mp - S)
    head = mp - to_p * 0.72 - UP * 0.02 + flat(cam_pos() - mp) * 0.18  # below the floppy hat tip, which hangs forward
    mic_k = smooth((t - (syl(7, 1, 2, 0) - 0.25)) / 0.3)  # "fa-la pra mim": its tail tip becomes a microphone
    mic = mp - to_p * 0.38 - UP * 0.12 + flat(cam_pos() - mp) * 0.14
    lp = lean_path(S, head, mp, mic, mic_k)
    talking = syl(7, 0, 0, 0) <= t <= syl(7, 1, 4, 0) + 0.2
    lp["jaw"] = 12 * max(0.0, math.sin(t * 18)) if talking else 0
    snake.pose(**lp)
    return ["P1"]


def m_compensa(t, dt):
    garden(t)
    two_shot_cam(PX)
    shrug_t = syl(8, 1, 0, 0)  # "a-cho"
    reg_t = syl(8, 1, 3, 0)    # "com-pen-sa": ka-ching
    back_t = reg_t + 0.45      # he hands it back
    woozy = math.sin(t * 4.5) * 5
    if shrug_t <= t < back_t:
        pose = {**PT.SHRUG, "body": (0, 0, 0.1, 0, woozy, 0)}
    else:
        pose = {**PT.STAND, "body": (0, 0, 0, 0, woozy, 0), "head": (6, 0, 0)}
    P, S = p1_and_cobra(t, pose)
    bpy.context.view_layer.update()
    if shrug_t <= t < back_t:  # palms up, out to the sides at shoulder height: solved, so the hands stay clear
        c, r, f = torso_centre("P1"), right_of("P1"), facing("P1")
        pose = reach("P1", "R", c + r * 0.6 + UP * 0.28 + f * 0.18, pose)
        pose = reach("P1", "L", c - r * 0.6 + UP * 0.28 + f * 0.18, pose)
        apply_pose("P1", pose)
    finish(["P1"])
    bpy.context.view_layer.update()
    near = side_towards("P1", S)
    if t < back_t:
        joint_at(mouth("P1"), smoke_dir("P1", away_from=S, down=0.35))
    else:  # held out to the cobra, which takes it back in its mouth
        k = smooth((t - back_t) / 0.35)
        short = cobra_mouth() + flat(P - cobra_mouth()) * 0.24
        held = (mouth("P1") + smoke_dir("P1", away_from=S) * 0.38).lerp(short, k)
        OB["joint"].matrix_world = frame_from(flat(S - P), held, JOINT_S)
        pose = reach("P1", near, held, pose)
        apply_pose("P1", pose)
        finish(["P1"])
    OB["register"].location = on_path(PX + 0.78, -0.95)
    OB["register"].rotation_euler = (0, 0, math.radians(-10))
    pop(OB["register"], reg_t - 0.2, t, base=0.75)
    OB["register_tab"].location = (0, -0.1, 0.62 + 0.2 * back_out((t - reg_t) / 0.25))
    return ["P1"]


SCARED_WIDE = {"body": (0, 0.1, 0.25, -4, 0, 0), "spine": (-10, 0, 0), "head": (-6, 0, 0),
               "thighR": (-30, 0, 0), "shinR": (40, 0, 0), "glove": ("open", "open")}


def startled(p, pose):
    """Hands flung out wide at head height, well apart (not clapped together over the head)."""
    c = torso_centre(p)
    r, f = right_of(p), facing(p)
    pose = reach(p, "R", c + r * 0.72 + UP * 0.55 + f * 0.12, pose)
    return reach(p, "L", c - r * 0.72 + UP * 0.55 + f * 0.12, pose)


def m_tarde(t, dt):
    dark = syl(9, 0, 0, 0)  # "tar-de": the sky snaps black
    garden(t, light=0.82 if t < dark else 0.08)
    if t >= dark:
        haze(0.12, amount=0.45, near=5)
    two_shot_cam(PX, dist=7.2)
    pull = syl(9, 1, 1, 0)  # "rou-bei": the soul is tugged out
    out = smooth((t - pull) / 0.8)
    slumped = t >= pull + 0.25
    P = on_path(PX)
    S = on_path(PX + COBRA_GAP, 0.3)
    rig("P1", P, rz=face_rz(P, S, 0.5, cam_pos()), pose=PT.SLUMP if slumped else SCARED_WIDE)
    bpy.context.view_layer.update()
    if not slumped:
        apply_pose("P1", startled("P1", SCARED_WIDE))
    used = ["P1"]
    if t >= pull - 0.05:
        soul(True)
        rig("ALMA", P + Vector((0.3 * out, 0.05, 0)), rz=face_rz(P, S, 0.5, cam_pos()), lift=0.95 * out,
            pose={**SCARED_WIDE, "body": (0, 0, 0, 0, 0, 8 * math.sin(t * 6))})
        bpy.context.view_layer.update()
        apply_pose("ALMA", startled("ALMA", SCARED_WIDE))
        used.append("ALMA")
    finish(used)
    st = snake_two_shot(S, mouth("P1"), t, height=1.25)
    st["jaw"] = 18 * smooth((t - dark) / 0.3)
    if t >= pull - 0.1:  # its head down at the soul's cap, pulling
        top = head_top("ALMA") if t >= pull else head_top("P1")
        st["path"][0] = top + Vector((0.12, 0, 0.05))
        st["look"] = Vector((-1, 0, -0.5))
    snake.pose(**st)
    return used


def jar_in_tail(st, base, face, sc):
    """Adds the tail curling up to hold the jar beside the cobra; returns where the jar's base goes."""
    f = flat(face)
    lat = f.cross(UP).normalized()
    jar = Vector(base) + lat * (0.55 * sc) + f * (0.2 * sc) + UP * (0.55 * sc)
    end = st["path"][-1]
    neck = jar + UP * 0.66  # just under the cork; the jar (scale 1.2) is 0.26 m in radius, its neck narrower
    st["path"] = st["path"] + [end + UP * (0.25 * sc) - lat * (0.1 * sc), neck - lat * 0.36, neck + f * 0.36, neck + lat * 0.34]
    return jar


def jar_with_soul(at, t, s=1.0):
    place("soul_jar", at, (0, 0, -10), 1.2 * s)
    soul(True)
    rig("ALMA", at + Vector((0, 0, 0.05 * s)), rz=-10, pose={**PT.SCARED, "body": (0, 0, 0, 0, 0, 10 * math.sin(t * 9))},
        scale=0.24 * s)


def m_alma(t, dt):
    to_spooky = CUTS[10] + 0.05
    spooky(t)
    for o in bpy.data.collections["set_assombrada"].objects:  # the skeleton trees spring up
        if o.instance_type == "COLLECTION":
            pop(o, to_spooky + abs(o.location.x) * 0.03, t)
    px = PX
    cork_t = syl(10, 0, 4, 2)  # "a-go-RA": corked
    grow_t = syl(10, 1, 1, 0)  # "ve-nha": the cobra swells
    k = smooth((t - grow_t + 0.25) / 0.9)
    cam(vlerp((px + 0.5, -6.0, 1.0), (px + 0.6, -8.4, 1.7), k), vlerp((px + 0.5, 0.8, 1.1), (px + 0.8, 2.0, 2.9), k),
        lens=lerp(33, 26, k))
    rig("P1", on_path(px), rz=-15, pose=PT.SLUMP)
    g = back_out((t - grow_t) / 0.9, 1.3) if t >= grow_t else 0.0
    sc = 1 + 2 * g
    base = on_path(px + 1.3, 0.5)
    st = snake.stand(base, (-0.6, -1, 0), height=1.2)
    st["path"] = [base + (p - base) * sc for p in st["path"]]
    jar = jar_in_tail(st, base, (-0.6, -1, 0), sc)
    st.update(scale=sc, horns=t >= grow_t + 0.5, jaw=14)
    snake.pose(**st)
    jar_with_soul(jar, t)
    finish(["P1", "ALMA"])
    OB["jar_cork"].location = (0, 0, 0.45 * (1 - smooth((t - cork_t) / 0.15)))
    return ["P1", "ALMA"]


def laugh_syllables():
    return [s for r in TL["cards"][11]["rows"] for w in r for s in w[2]]


def m_risada(t, dt):
    spooky(t)
    px = PX
    cam(Vector((px + 0.6, -8.2, 1.2)), Vector((px + 0.9, 2.0, 3.6)), lens=24)
    rig("P1", on_path(px), rz=-15, pose=PT.SLUMP)
    snap = max([math.sin(clamp((t - s) / 0.16) * math.pi) for s in laugh_syllables()] + [0.0])
    base = on_path(px + 1.3, 0.5)
    st = snake.laugh(base, (-0.6, -1, 0))
    st["path"] = [base + (p - base) * 3.0 for p in st["path"]]
    jar = jar_in_tail(st, base, (-0.6, -1, 0), 3.0)
    st.update(scale=3.0, horns=True, jaw=18 + 22 * snap)
    snake.pose(**st)
    jar_with_soul(jar, t)
    finish(["P1", "ALMA"])
    OB["jar_cork"].location = (0, 0, 0)
    OB["spooky_moon"].scale = (1 + 0.06 * snap, 1, 1 - 0.06 * snap)
    return ["P1", "ALMA"]


def m_mole(t, dt):
    garden(t)
    gap = 1.05
    two_shot_cam(PX, gap=gap, dist=6.6)
    back_t = syl(12, 0, 0, 0)  # "vai": the soul snaps back
    grab_t = syl(12, 0, 4, 0)  # "co-bra": grabs its neck
    limp_t = syl(12, 0, 5, 0)  # "mo-le": it goes limp
    used = ["P1"]
    P = on_path(PX)
    S = on_path(PX + gap, 0.3)
    k = smooth((t - back_t) / 0.3)
    rz = face_rz(P, S, 0.5, cam_pos())
    pose = {**PT.POINT, "glove": ("point", "fist")} if k >= 1 else PT.SLUMP
    rig("P1", P, rz=rz, pose=pose)
    shrink = smooth((t - back_t) / 0.6)
    sc = lerp(3.0, 1.0, shrink)
    st = snake_two_shot(S, P + UP * 1.0, t, height=1.15)
    st["path"] = [S + (p - S) * sc for p in st["path"]]
    jar_face = flat(P - S) * 0.65 + flat(cam_pos() - S) * 0.35
    jar_at = jar_in_tail(st, S, jar_face, sc) if t < grab_t else None
    if k < 1:
        soul(True)
        place("soul_jar", jar_at, (0, 0, -10), 1.2)
        OB["jar_cork"].location = (0, 0, 0.45 + 0.6 * k)
        rig("ALMA", vlerp(jar_at + Vector((0, 0, 0.05)), P, k), rz=rz, pose=PT.SCARED, scale=lerp(0.24, 1.0, k))
        used.append("ALMA")
    bpy.context.view_layer.update()
    near = side_towards("P1", S)
    if t < grab_t:
        if jar_at is not None and k >= 1:
            place("soul_jar", jar_at, (0, 0, -10), 1.2)
            OB["jar_cork"].location = (0, 0, 1.05)
        st.update(scale=sc, horns=shrink < 0.5, jaw=10)
        snake.pose(**st)
        if k >= 1:  # points at it with the hand on its side
            c = torso_centre("P1")
            pose = reach("P1", near, c + flat(S - c) * 0.75 + UP * 0.35, {**pose, "glove": ("point", "fist") if near == "R" else ("fist", "point")})
    else:
        # grabbed by the neck, held up in the near hand, hanging limp
        c = torso_centre("P1")
        grip = c + flat(S - c) * 0.62 + UP * 0.55
        pose = reach("P1", near, grip, {**PT.STAND, "head": (-10, 0, 0), "glove": ("hold", "fist") if near == "R" else ("fist", "hold")})
        held = grip
        lp = snake.limp(held, flat(S - c), held=held)
        if t < limp_t:  # still stiff for an instant, then droops
            lp["path"] = [held + (p - held) * 0.6 for p in lp["path"]]
        snake.pose(**lp)
    apply_pose("P1", pose)
    finish(used)
    return used


# The crew: a back row behind Pardão, never between him and the cobra
CREW = [("P2", -1.0, 0.9), ("P3", -1.8, 1.6), ("P4", 0.85, 1.5)]  # P4 far back between him and the cobra


def akimbo(p, pose):
    """Fists on hips, elbows out: the tough stance, without arms passing through the body."""
    c = torso_centre(p)
    r, f = right_of(p), facing(p)
    pose = reach(p, "R", c + r * 0.36 - UP * 0.12 + f * 0.04, {**pose, "glove": ("fist", "fist")})
    return reach(p, "L", c - r * 0.36 - UP * 0.12 + f * 0.04, pose)


def crew_up(t, t0s, look_at):
    used = []
    for (p, dx, dy), t0 in zip(CREW, t0s):
        k = back_out((t - t0) / 0.35) if t >= t0 else 0.0
        at = on_path(PX + dx, dy)
        rig(p, at, rz=face_rz(at, look_at, 0.5, cam_pos()), pose=PT.STAND, lift=-1.6 * (1 - k))
        used.append(p)
    bpy.context.view_layer.update()
    for p in used:
        apply_pose(p, akimbo(p, PT.STAND))
    return used


def m_crew(t, dt):
    garden(t)
    cam(Vector((PX - 0.15, -8.6, 1.3)), Vector((PX - 0.15, 0.8, 1.05)), lens=32)
    ups = [syl(13, 0, 1, k) for k in range(3)]  # "fe-cha-do": one pops up per syllable
    hood_t = syl(13, 1, 3, 0)                    # "ca-ra-pu-ça": the hood drops on the cobra from above
    P = on_path(PX)
    S = on_path(PX + COBRA_GAP, 0.3)
    rig("P1", P, rz=face_rz(P, S, 0.5, cam_pos()), pose=PT.STAND)
    bpy.context.view_layer.update()
    apply_pose("P1", akimbo("P1", PT.STAND))
    used = ["P1"] + crew_up(t, ups, S)
    finish(used)
    snake.pose(**snake_two_shot(S, mouth("P1"), t, height=0.95))
    bpy.context.view_layer.update()
    k = smooth((t - (hood_t - 0.35)) / 0.35)
    top = OB["COBRA_head"].matrix_world @ Vector((0, 0.08, 0.17))
    if t >= hood_t - 0.35:
        place("hood", top + UP * 2.2 * (1 - k), (-10, 0, 0), 1.0)
        OB["COBRA_hat"].hide_render = OB["COBRA_hat"].hide_viewport = k > 0.95
    return used


def m_cigarros(t, dt):
    garden(t)
    two_shot_cam(PX, gap=1.55, dist=6.6, lens=33)
    lit = syl(14, 0, 0, 0)   # "fu-mei"
    blow = syl(14, 0, 2, 1)  # "ci-GAR-ro"
    rap = syl(14, 1, 0, 0)   # "ou-ve"
    lean = smooth((t - rap) / 0.3)
    P = on_path(PX)
    S = on_path(PX + 1.55, 0.3)
    pose = {**PT.STAND, "head": (-10 + nod(t, syl_times(14, 1), 12), 0, 0), "spine": (6 * lean, 0, 0)}
    rig("P1", P, rz=face_rz(P, S, 0.5, cam_pos()), pose=pose)
    bpy.context.view_layer.update()
    pose = akimbo("P1", pose)
    if t >= rap:  # points at it while he raps
        c = torso_centre("P1")
        near = side_towards("P1", S)
        pose = reach("P1", near, c + flat(S - c) * 0.72 + UP * 0.32,
                     {**pose, "glove": ("point", "fist") if near == "R" else ("fist", "point")})
    apply_pose("P1", pose)
    used = ["P1"] + crew_up(t, [CUTS[14] - 5] * 3, S)
    finish(used)
    shrinkage = lerp(1.0, 0.6, smooth((t - rap) / 1.6))
    st = snake_two_shot(S, mouth("P1"), t, height=0.85)
    st["path"] = [S + (p - S) * shrinkage for p in st["path"]]
    st.update(scale=shrinkage, jaw=6)
    snake.pose(**st)
    bpy.context.view_layer.update()
    place("hood", OB["COBRA_head"].matrix_world @ Vector((0, 0.08, 0.17)), (-10, 0, 0), shrinkage)
    OB["COBRA_hat"].hide_render = OB["COBRA_hat"].hide_viewport = True
    m = mouth("P1")
    if t >= lit:  # two cigarettes at once, one out of each corner of the mouth, angled so both show
        base = smoke_dir("P1", down=0.2)
        r = right_of("P1")
        cig_at("cigarette", m + r * 0.035, (base + r * 0.35).normalized())
        cig_at("cigarette2", m - r * 0.035, (base - r * 0.35).normalized())
    toward = cobra_head_pt() - m
    smoke("cig", [(blow + 0.06 * i, m + facing("P1") * 0.15, toward * 1.1 + Vector((0, 0, -0.3)), 0.22 + 0.02 * i, False)
                  for i in range(8)], t)
    return used


TRAP_LIFT = math.radians(37.7)  # the crate's front edge propped 0.55 m up on the stick (before TRAP_S)
TRAP_S = 0.78


def crate(fall):
    """The crate tipped up on its back edge (towards +Y), its front edge on the stick; fall 0..1 drops it flat."""
    ang = TRAP_LIFT * (1 - fall)
    m = Matrix.Translation((0, 0.45, 0)) @ Matrix.Rotation(-ang, 4, "X") @ Matrix.Translation((0, -0.45, 0))
    OB["trap_crate"].matrix_basis = m
    stick = OB["trap_stick"]
    if fall <= 0:
        stick.matrix_basis = Matrix.Translation((0, 0.45 - 0.9 * math.cos(TRAP_LIFT), 0))
    else:  # knocked flat, rolling out in front
        stick.matrix_basis = Matrix.Translation((0.15 * fall, -0.55 - 0.25 * fall, 0.02)) @ Matrix.Rotation(math.radians(-90 * fall), 4, "X")


def crawl_path(head, d, t, n=12, step=0.12, lift=0.18):
    """Slithering along the ground: head up a little, the body in S-waves trailing behind (towards -d)."""
    d = flat(d)
    lat = UP.cross(d).normalized()
    pts = []
    for k in range(n):
        u = k * step
        w = 0.09 * math.sin(u * 9 - t * 14) * min(1.0, k / 3)
        pts.append(Vector(head) - d * u + lat * w + Vector((0, 0, max(0.07, lift * (1 - k / 3)))))
    return dict(path=pts, look=d - Vector((0, 0, 0.1)))


def m_arapuca(t, dt):
    garden(t)
    trap_x = SELVA.x + 0.7
    C = on_path(trap_x, -1.0)   # the trap sits in the foreground
    cam(C + Vector((0.1, -4.4, 1.45)), C + Vector((0.05, 0.8, 0.4)), lens=30)
    go_t = syl(15, 1, 1, 0)     # "cai-o": the cobra goes for the bait
    drop_t = syl(15, 1, 4, 3)   # "a-ra-pu-CA": the box drops
    front = flat(cam_pos() - C)
    right = UP.cross(front).normalized()  # screen right, as the camera sees it
    used = []
    x = SELVA.x - 0.8 + 2.4 * dt  # the gang struts past BEHIND the trap in single file, left to right
    for i, p in enumerate(["P1", "P2", "P3", "P4"]):
        at = on_path(x - 1.35 * i, 0.95)  # a Pardo is ~1.2 m long side-on: floppy hat forward, tail behind
        rig(p, at, rz=80, pose=dict(walk_key(t + 0.2 * i)))
        used.append(p)
    finish(used)
    OB["trap"].location = C
    # the crate's propped edge is its local -Y: turned so that side faces the camera (rz so that R(rz) @ -Y = front)
    OB["trap"].rotation_euler = (0, 0, math.atan2(front.x, -front.y))
    OB["trap"].scale = (TRAP_S,) * 3
    fall = smooth((t - drop_t) / 0.08)
    crate(fall)
    bait = C + Vector((0, 0, 0.02))
    OB["joint"].matrix_world = frame_from(right, bait, JOINT_S)
    S = 0.8
    if t < drop_t:  # in from the right, low along the ground, dizzy in its hood, straight for the bait
        k = smooth((t - go_t) / max(0.2, drop_t - go_t - 0.05))
        head = (C + right * 0.85 + front * 0.2).lerp(bait - right * 0.1, k)
        cp = crawl_path(head, -right, t)
        cp["path"] = [head + (p - head) * S for p in cp["path"]]
        cp.update(scale=S, jaw=4)
        snake.pose(**cp)
    else:  # caught: tail sticking out at the front right, head peeking out at the front left
        k = TRAP_S
        tip = C + front * 0.7 * k + right * 0.32 * k + Vector((0, 0, 0.06))
        u = [tip, C + front * 0.3 * k + right * 0.28 * k, C + right * 0.18 * k, C - front * 0.15 * k, C - right * 0.18 * k,
             C + front * 0.3 * k - right * 0.28 * k, C + front * 0.62 * k - right * 0.3 * k]
        pts = [p + Vector((0, 0, 0.06)) for p in reversed(u)]
        pts[0] += Vector((0, 0, 0.08 + 0.03 * math.sin(t * 10)))
        snake.pose(path=pts, look=front + Vector((0, 0, 0.25)), scale=S, jaw=6)
    bpy.context.view_layer.update()
    place("hood", OB["COBRA_head"].matrix_world @ Vector((0, 0.08, 0.17)), (-10, 0, 0), S)
    OB["COBRA_hat"].hide_render = OB["COBRA_hat"].hide_viewport = True
    return used


MOMENTS = {"conto": m_conto, "cachimbo": m_cachimbo, "trevas": m_trevas, "selva": m_selva, "jardim": m_jardim,
           "basiadin": m_basiadin, "caminho": m_caminho, "da_boa": m_da_boa, "compensa": m_compensa, "tarde": m_tarde,
           "alma": m_alma, "risada": m_risada, "mole": m_mole, "crew": m_crew, "cigarros": m_cigarros,
           "arapuca": m_arapuca, "fim": m_arapuca}


def apply(f):
    """Rebuilds the scene for video frame f (1-based). Returns the moment's name."""
    t_exact = song_t(f)
    i, name, _ = moment_at(t_exact)  # the shot comes from the exact time, so a cut lands on its own frame
    t = max(twos(t_exact), CUTS[i])  # the animation steps on twos within it
    reset()
    MOMENTS[name](t, t - CUTS[i])
    bpy.context.view_layer.update()
    return name


def anchors():
    """World points the 2D effects pin to (their screen positions go to frames.json)."""
    hd = OB["COBRA_head"].matrix_world
    return {"cobra_head": hd @ Vector((0, 0.12, 0.12)), "cobra_mouth": hd @ Vector((0, 0.3, -0.02)),
            "p1_head": head_top("P1"), "p1_mouth": mouth("P1"),
            "register": OB["register"].matrix_world @ Vector((0, 0, 0.8)),
            "trap": OB["trap"].matrix_world.translation + Vector((0, 0, 0.35)), "iris": hd @ Vector((0, 0.15, 0.05)),
            "jar": OB["soul_jar"].matrix_world @ Vector((0, 0, 0.3)),
            "book": OB["book_back"].matrix_world @ Vector((0.125, 0, 0.05)), "moon": SPOT["moon"].copy(),
            "p1_feet": OB["P1"].matrix_world.translation.copy(), "vovo_mouth": mouth("VOVO"), "eva_mouth": mouth("EVA"),
            "gramophone": OB["sala_gramophone"].matrix_world @ Vector((0.1, -0.1, 0.7))}
