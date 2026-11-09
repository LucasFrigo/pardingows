# The whole video as a function of the frame: apply(f) puts every actor, prop, light and the camera where frame f needs them.
# There are no keyframes: render_frames.py calls apply(f) and renders, so a frame is always rebuilt from scratch and any frame
# can be re-rendered alone. Timing comes from timeline.json (cuts) and cues.json (gag times derived from the sung words).
# Stage-local coordinates throughout (actors.world adds the stage origin). Yaw 0 faces -Y (the camera side), 90 faces +X.
import bpy, json, math, os, random
from mathutils import Vector, Euler, Matrix
import poses_brawl as PB
import actors as A
from set_lib import ROOT, WORK

OB = bpy.data.objects
TL = json.load(open(os.path.join(ROOT, "src", "pardao", "timeline.json"), encoding="utf8"))
CUE = json.load(open(os.path.join(ROOT, "src", "pardao", "cues.json"), encoding="utf8"))
GAGS = json.load(open(os.path.join(WORK, "gags.json"), encoding="utf8"))
START, FPS, FRAMES = TL["start"], TL["fps"], TL["frames"]
BEAT = 60 / TL["bpm"]
CUTS = CUE["cuts"]
PLAYERS = ["P1", "P2", "P3", "P4"]
HOBOS = ["M1", "M2", "M3"]
HORDE = GAGS["horde"]
ALL_HOBOS = HOBOS + HORDE
PARDO_ARM = {"P1": "Armature", "P2": "P2_arm", "P3": "P3_arm", "P4": "P4_arm"}

# Baselines captured once per Blender session, before any shot touches them
STAGE_LIGHTS = [o for o in bpy.data.collections["st_luzes"].objects if o.type == "LIGHT"]
LIGHT_BASE = {o.name: o.data.energy for o in STAGE_LIGHTS}
WIN_MATS = [m for m in bpy.data.materials if m.name.startswith(("st janela_luz", "st janela_tv", "st janela_fluor", "st lampada", "st led_", "st bandeira"))]
WIN_BASE = {m.name: m.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value for m in WIN_MATS}
FAR_MAT = bpy.data.materials.get("st morro longe")
FAR_BASE = FAR_MAT.node_tree.nodes["Emission"].inputs["Strength"].default_value if FAR_MAT else 0
WORLD = bpy.context.scene.world
WORLD_BG = WORLD.node_tree.nodes["Background"].inputs["Strength"]


def song(f):
    return START + (f - 1) / FPS


def moment_index(t):
    i = 0
    for k, c in enumerate(CUTS):
        if t >= c - 1e-6:
            i = k
    return i


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def lerp(a, b, k):
    return tuple(p + (q - p) * k for p, q in zip(a, b))


def beat_i(t, per=1.0):
    return int(math.floor((t - CUE["beat0"]) / (BEAT * per) + 1e-6))


def guard(t):
    return PB.P_GUARD_A if beat_i(t, 0.5) % 2 == 0 else PB.P_GUARD_B


def walk(t, rate=6.0, phase=0.0):
    return PB.H_WALK[int(math.floor(t * rate + phase)) % 4]


def yaw_to(src, dst):
    """Yaw that turns a -Y facing actor at src to face dst."""
    dx, dy = dst[0] - src[0], dst[1] - src[1]
    return math.degrees(math.atan2(dx, -dy))


def stair_z(x, xs, d, z0):
    """Height on a flight starting at xs going in direction d from z0 (20 steps of 0.3 x 0.15)."""
    k = (x - xs) * d / 0.3
    return z0 + max(0.0, min(20.0, k)) * 0.15


# ---------------------------------------------------------------- per-frame reset
def reset():
    for i, p in enumerate(PLAYERS):
        OB[p].location = (i * 1.3, -40, 0)
        OB[p].rotation_euler = (0, 0, 0)
        PB.pose_pardo(p, PB.P_STAND, A.G)
    for i, m in enumerate(ALL_HOBOS):
        OB[m].location = (5.6 + i * 1.2, -46 if m in HORDE else -40, 0)
        OB[m].rotation_euler = (0, 0, 0)
        PB.pose_hobo(m, PB.H_STAND)
    A.static("JUMENTO", (11.6, -40, 0), 0)
    OB["JUMENTO"].location = (11.6, -40, 0)
    OB["JUMENTO"].scale = (1, 1, 1)
    OB["MB"].location = (9.6, -40, 0)
    for n in ("P2_mic",):
        OB[n].hide_render = OB[n].hide_viewport = True
    for o in OB:
        if o.name.startswith(("arma_", "mao_")):
            o.hide_render = o.hide_viewport = True
    for n in ("ITEM_baseado", "ITEM_radio"):
        OB[n].location = (0, -60, -20)
    for o in STAGE_LIGHTS:
        o.data.energy = LIGHT_BASE[o.name]
    for m in WIN_MATS:
        m.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = WIN_BASE[m.name]
    if FAR_MAT:
        FAR_MAT.node_tree.nodes["Emission"].inputs["Strength"].default_value = FAR_BASE
    WORLD_BG.default_value = 1.0
    OB["luz_pardo"].data.energy = 0.0
    for m in HOBOS:
        OB[f"flash_{m}"].data.energy = 0.0


def cam(pos, target, lens=24.0, fill=250.0, shake=0.0, seed=0):
    if shake:
        r = random.Random(seed)
        pos = tuple(p + r.uniform(-shake, shake) for p in pos)
    c = A.camera("cam", pos, target, lens)
    A.fill_light(c, fill)
    bpy.context.scene.camera = c
    return c


def blackout(k=1.0):
    """k = 1: every light in the favela off. Windows, lamps, baile, far hill and sky all go dark."""
    for o in STAGE_LIGHTS:
        o.data.energy = LIGHT_BASE[o.name] * (1 - k)
    for m in WIN_MATS:
        m.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = WIN_BASE[m.name] * (1 - k)
    if FAR_MAT:
        FAR_MAT.node_tree.nodes["Emission"].inputs["Strength"].default_value = FAR_BASE * (1 - 0.85 * k)
    WORLD_BG.default_value = 1 - 0.8 * k


def street_pardos():
    pass


# ---------------------------------------------------------------- the moments
def m_card(t, u):
    pose = guard(t) if t < CUE["descobri"] else PB.P_POINT if t < CUE["pardo1"] else PB.P_VICTORY
    A.pardo("P1", (0.3, 2.0, 0), -12, pose)
    A.static("MB", (4.6, 5.0, 0), 200)
    k = ease(u / 2.6)
    cam(lerp((1.6, -7.0, 2.6), (0.7, -3.0, 1.5), k), (0.3, 2.0, 1.0), 24, 220)


def m_apagao(t, u):
    A.pardo("P1", (0.3, 2.0, 0), -12, guard(t))
    du = u / 1.65
    A.hobo("M1", (-3.4 + 0.7 * du, 1.0, 0), 75, walk(t, 4))
    A.hobo("M2", (3.9 - 0.6 * du, 3.2, 0), -105, walk(t, 4, 2))
    x3 = -5.6 + 0.8 * du
    A.hobo("M3", (x3, 5.0, stair_z(x3, -6.6, 1, 0.0)), 90, walk(t, 4, 1))
    A.static("MB", (4.6, 5.0, 0), 200)
    c = cam((2.2, -6.2, 2.4), (-0.2, 2.6, 1.1), 22, 200)
    if t >= CUE["escuro"]:
        blackout(1.0)
        OB["luz_pardo"].location = A.world((0.3, 1.2, 1.4))
        OB["luz_pardo"].data.energy = 140.0
        A.fill_light(c, 0.0)


def m_crew(t, u):
    A.pardo("P1", (0.0, 2.2, 0), -8, guard(t))
    spots = {"P2": ((1.5, 2.7), CUE["p2_land"]), "P3": ((-1.5, 2.7), CUE["p3_land"]), "P4": ((3.0, 3.2), CUE["p4_land"])}
    for p, ((x, y), tl) in spots.items():
        fall = 0.35
        if t < tl - fall:
            continue
        if t < tl:
            s = (t - (tl - fall)) / fall
            A.pardo(p, (x, y, 4.5 * (1 - s * s)), -10, PB.P_STRETCH_UP)
        elif t < tl + 0.3:
            A.pardo(p, (x, y, 0), -10, PB.P_LUNGE)
        else:
            A.pardo(p, (x, y, 0), -10, guard(t + 0.12 * PLAYERS.index(p)))
    A.hobo("M1", (-4.3, 1.2, 0), 70, PB.H_ALERT)
    A.hobo("M2", (4.7, 1.0, 0), -80, PB.H_ALERT)
    cam((1.0, -6.6, 2.4), (0.6, 2.6, 1.2), 24, 240)


def m_baseado(t, u):
    P = (4.7, 0.6, 0)
    if t < CUE["grab"]:
        A.pardo("P1", P, -10, PB.P_STAND)
        o = OB["ITEM_baseado"]
        o.location = A.world((4.75, -0.05, 1.0 + 0.08 * math.sin(t * 9)))
        o.rotation_euler = (0, 0, t * 9.0)
    elif t < CUE["turn"]:
        A.pardo("P1", P, -10, PB.P_SMOKE)
        A.hand_prop("mao_baseado", "baseado", "Armature", "Bone.004", loc=(0.0, 0.05, 0.0), rot=(0, 0, 90), scale=3.0)
    elif t < CUE["jab"]:
        A.pardo("P1", P, 42, guard(t))
    elif t < CUE["recoil"]:
        A.pardo("P1", P, 42, PB.P_JAB)
    else:
        wob = 14 * math.sin((t - CUE["recoil"]) * 11)
        A.pardo("P1", P, 42 + wob, PB.P_HIT if t < CUE["recoil"] + 0.25 else {**PB.P_STAND, "head": (8, wob, 0)})
    zoom = 26 + 8 * ease((t - CUE["recoil"]) / 0.4)
    cam((2.6, -3.6, 1.5), (4.9, 0.0, 1.0), zoom, 160, 0.03 if CUE["jab"] + 0.05 < t < CUE["jab"] + 0.3 else 0.0, int(t * 30))


def m_banger(t, u):
    BOX = (-0.4, 8.2, 3.0)
    land = CUE["radio_land"]
    o = OB["ITEM_radio"]
    if t < land:
        s = max(0.0, (t - CUTS[4]) / (land - CUTS[4]))
        o.location = A.world((BOX[0], BOX[1], BOX[2] + 5.0 * (1 - s * s)))
    else:
        squash = 1.0 - 0.18 * max(0.0, 1 - (t - land) / 0.15)
        o.location = A.world(BOX)
        o.scale = (4.0 / squash ** 0.5, 4.0 / squash ** 0.5, 4.0 * squash)
    o.rotation_euler = (0, 0, math.radians(180))
    for p, (x, y, yaw) in zip(PLAYERS, ((-1.7, 7.3, 20), (0.9, 7.1, -20), (-2.6, 8.7, 40), (1.6, 8.4, -40))):
        A.pardo(p, (x, y, 3.0), yaw, PB.P_DANCE_A if beat_i(t, 0.5) % 2 else PB.P_DANCE_B)
    beats = [CUE["beat0"] + BEAT * k for k in range(200) if land < CUE["beat0"] + BEAT * k < CUTS[5]]
    for m, p0 in zip(HOBOS, ((-5.2, 7.0), (5.0, 7.4), (4.6, 8.9))):
        d = (Vector((BOX[0], BOX[1])) - Vector(p0)).normalized()
        knock = sum(ease((t - b) / 0.15) * 1.1 for b in beats if t >= b)
        pos = Vector(p0) + d * (1.3 * u) - d * knock
        hit = any(0 <= t - b < 0.2 for b in beats)
        A.hobo(m, (pos.x, pos.y, 3.0), yaw_to(pos, BOX), PB.H_HIT if hit else walk(t, 5, HOBOS.index(m)))
    cam((1.6, 2.6, 6.2), (-0.2, 8.3, 3.8), 22, 280)


COMBO_HITS = [167.80, 168.04, 168.27, 168.51, CUE["absurdo"]] + [CUE["absurdo"] + 0.118 * k for k in range(1, 7)]


def m_combo(t, u):
    last = max([h for h in COMBO_HITS if h <= t], default=None)
    n = COMBO_HITS.index(last) if last is not None else -1
    if last is None or t - last > 0.16:
        pose = guard(t)
    elif last == COMBO_HITS[-1]:
        pose = PB.P_FLYKICK
    else:
        pose = (PB.P_JAB, PB.P_UPPER, PB.P_KICK)[n % 3]
    A.pardo("P1", (-0.6, 7.5, 3.0), 90, pose)
    if t < COMBO_HITS[0]:
        A.hobo("M1", (0.7, 7.5, 3.0), -90, PB.H_STAND)
    elif t < COMBO_HITS[-1]:
        air = 0.55 + 0.45 * abs(math.sin(math.pi * (t - COMBO_HITS[0]) / 0.236))
        A.hobo("M1", (0.75, 7.5, 3.0 + air), -90, PB.H_HIT)
        OB["M1"].rotation_euler = (math.radians(-25 + 18 * math.sin(t * 13)), 0, math.radians(-90))
    else:
        s = t - COMBO_HITS[-1]
        A.hobo("M1", (0.8 + 6.0 * s, 7.5, 3.0 + 1.2 + 3.0 * s - 9.0 * s * s), -90, PB.H_HIT)
        OB["M1"].rotation_euler = (math.radians(-40 - 400 * s), 0, math.radians(-90))
    A.pardo("P2", (-2.4, 8.6, 3.0), 80, guard(t + 0.1))
    A.hobo("M2", (3.4, 8.0, 3.0), -100, PB.H_ALERT)
    shake = 0.05 if last is not None and t - last < 0.06 else 0.0
    cam((3.2, 2.4, 5.0), (0.3, 7.6, 4.3), 24, 220, shake, int(t * 30))


HORDE_PATH = [(-3.0, 12.6, 6.0), (0.3, 10.0, 6.0), (6.6, 10.0, 3.0), (4.2, 8.0, 3.0)]


def along(path, s):
    """Point at distance s along a polyline; before the start it queues back along the first segment."""
    pts = [Vector(p) for p in path]
    if s <= 0:
        d = (pts[1] - pts[0]).normalized()
        return pts[0] + d * s, d
    for a, b in zip(pts, pts[1:]):
        L = (b - a).length
        if s <= L:
            return a + (b - a) * (s / L), (b - a).normalized()
        s -= L
    return pts[-1], (pts[-1] - pts[-2]).normalized()


MURO_P = [(0.9, 15.05), (2.2, 15.05), (3.5, 15.05), (4.8, 15.05)]
MURO_M = [(1.4, 12.6), (3.0, 12.6), (4.6, 12.6)]


def horde_rows(t, pose_a, pose_b, y0=11.7):
    for i, h in enumerate(HORDE[:10]):
        x = -1.2 + (i % 5) * 1.15 + (0.55 if i >= 5 else 0)
        y = y0 - (0.9 if i >= 5 else 0)
        A.hobo(h, (x, y, 6.0), 180 + (i % 3 - 1) * 8, pose_a if (i + beat_i(t)) % 2 else pose_b)


def m_horda(t, u):
    if t < CUE["enquadram"]:
        for i, (p, (x, y)) in enumerate(zip(PLAYERS, ((-2.3, 7.4), (-1.0, 7.0), (0.3, 7.7), (-3.3, 8.3)))):
            A.pardo(p, (x, y, 3.0), 175 + i * 6, guard(t + 0.1 * i))
        for k, h in enumerate(HOBOS + HORDE):
            if k < 8:
                # The front of the horde streams down the stairs towards the Pardos
                pos, d = along(HORDE_PATH, 2.3 * u + 6.5 - 0.95 * k)
                off = Vector((-d.y, d.x, 0)) * (((k * 37) % 7) / 7 - 0.5) * 0.8
                p = pos + off
                z = p.z
                if 0.3 < p.x < 6.6 and abs(p.y - 10.0) < 0.9:
                    z = 6.0 - (p.x - 0.6) * 0.5
                A.hobo(h, (p.x, p.y, z), yaw_to((0, 0), (d.x, d.y)), walk(t, 7, k))
            else:
                # The rest pour across landing 2 behind them
                j = k - 8
                p = (-5.0 + (j % 4) * 1.25 + 1.0 * u, 12.4 + (j // 4) * 0.95, 6.0)
                A.hobo(h, p, 70 + (j % 3) * 10, walk(t, 7, k))
        cam((-0.5, 4.2, 8.0), (2.4, 11.0, 6.0), 20, 300)
    else:
        for p, (x, y) in zip(PLAYERS, MURO_P):
            A.pardo(p, (x, y, 6.0), 0, PB.P_GUARD_B)
        k = ease((t - CUE["enquadram"]) / 0.35)
        for m, (x, y) in zip(HOBOS, MURO_M):
            A.hobo(m, (x, y + 0.8 * k, 6.0), 180, PB.H_GRAB)
        horde_rows(t, PB.H_SHOUT, PB.H_ALERT)
        cam((5.2, 9.4, 8.7), (2.8, 14.2, 6.9), 22, 300)


FIRES = [CUE[f"fire{i}"] for i in range(5)]


def m_muro(t, u):
    over = t >= CUE["gameover"]
    for i, (p, (x, y)) in enumerate(zip(PLAYERS, MURO_P)):
        jolt = any(0 <= t - f < 0.1 for f in FIRES)
        A.pardo(p, (x, y, 6.0), 0, PB.P_DOWN if over else PB.P_HIT if jolt and t > FIRES[0] else PB.P_HANDSUP)
    for m, (x, y), target in zip(HOBOS, MURO_M, (MURO_P[0], MURO_P[1:3][0], MURO_P[3])):
        tgt = MURO_P[min(3, HOBOS.index(m) + (1 if m == "M3" else 0))]
        yaw = yaw_to((x, y), tgt) if not over else 180
        A.hobo(m, (x, y, 6.0), yaw, PB.H_SHOUT if t >= CUE["lamento"] else PB.H_AIM)
        if t < CUE["lamento"]:
            A.gun_in_hand(f"arma_{m}", f"{m}_arm", "LeftHand")
        flash = any(0 <= t - f < 0.05 for f in FIRES)
        fl = OB[f"flash_{m}"]
        if flash and not over:
            arm = OB[f"{m}_arm"]
            fl.location = arm.matrix_world @ arm.pose.bones["LeftHand"].tail
            fl.data.energy = 900.0
    horde_rows(t, PB.H_ALERT, PB.H_SHOUT, 11.4)
    cam((6.4, 10.4, 8.0), (2.7, 14.6, 6.9), 22, 300, 0.04 if any(0 <= t - f < 0.05 for f in FIRES) else 0.0, int(t * 30))


def m_continue(t, u):
    up = t >= CUE["press"]
    for i, (p, (x, y)) in enumerate(zip(PLAYERS, MURO_P)):
        if not up:
            pose = PB.P_DOWN
        elif t < CUE["press"] + 0.25:
            pose = PB.P_LUNGE
        else:
            pose = PB.P_VICTORY if beat_i(t) % 2 else guard(t)
        A.pardo(p, (x, y, 6.0), 0, pose)
    # On the continue, the blast launches every Mildingow up out of the top of frame (never past the lens), and they're gone
    kb = (t - CUE["press"]) / 0.45 if up else 0.0
    group = list(zip(HOBOS, MURO_M)) + [(h, (-1.2 + (i % 5) * 1.15 + (0.55 if i >= 5 else 0), 11.4 - (0.9 if i >= 5 else 0))) for i, h in enumerate(HORDE[:10])]
    for k, (m, (x, y)) in enumerate(group):
        if kb >= 1.0:
            continue
        if not up:
            A.hobo(m, (x, y, 6.0), 180, PB.H_SHOUT if (k + beat_i(t)) % 2 else PB.H_ALERT)
            continue
        side = -1 if x < 2.8 else 1
        A.hobo(m, (x + side * 2.0 * kb, y + 0.6 * kb, 6.0 + 11.0 * kb * kb + 2.0 * kb), 180, PB.H_HIT)  # launched into the sky, out the top of frame
        OB[m].rotation_euler = (math.radians(-200 * kb), math.radians(side * 90 * kb), math.radians(180))
    k = ease(u / 1.65)
    cam(lerp((5.8, 10.2, 8.4), (5.0, 11.0, 7.8), k), (2.8, 14.8, 6.6), 22, 300)


PLAZA_ROW = [(-1.95, 20.4), (-0.65, 20.9), (0.65, 20.4), (1.95, 20.9)]


def m_aquecimento(t, u):
    seq = [PB.P_STRETCH_UP, PB.P_STRETCH_SIDE, PB.P_LUNGE, PB.P_STRETCH_UP]
    for i, (p, (x, y)) in enumerate(zip(PLAYERS, PLAZA_ROW)):
        if t < CUE["dance"]:
            pose = seq[(beat_i(t) - beat_i(CUTS[9])) % 4]
        else:
            pose = PB.P_DANCE_A if (beat_i(t, 0.5) + i) % 2 else PB.P_DANCE_B
        A.pardo(p, (x, y, 9.0), (i - 1.5) * 8, pose)
    A.hobo("M1", (-4.3, 22.6, 9.0), 30, PB.H_DRINK)
    A.static("MB", (-5.2, 19.2, 9.0), 120)
    k = ease(u / 1.9)
    cam(lerp((0.4, 12.6, 12.4), (0.2, 13.8, 11.8), k), (0.0, 21.0, 10.0), 22, 280)


def m_mapa(t, u):
    for i, (p, (x, y)) in enumerate(zip(PLAYERS, PLAZA_ROW)):
        A.pardo(p, (x, y, 9.0), 0, PB.P_DANCE_A if (beat_i(t, 0.5) + i) % 2 else PB.P_DANCE_B)
    k = ease(u / 1.9)
    cam(lerp((0.0, -16.0, 3.0), (0.0, -9.0, 19.0), k), (0.0, 16.0, 8.0), 20, 0)


def m_perdeu(t, u):
    arrive = CUTS[11] + 1.1
    if t < arrive:
        s = (t - CUTS[11]) / 1.1
        A.hobo("M3", lerp((-0.8, 16.8, 9.0), (0.2, 19.6, 9.0), s), 175, walk(t, 5))
    else:
        look = 30 * math.sin((t - arrive) * 4)
        A.hobo("M3", (0.2, 19.6, 9.0), 180 + look, {**PB.H_STAND, "head": (24, 0, 0), "neck": (14, 0, 0)})
    A.static("MB", (-5.2, 19.2, 9.0), 120)
    for n in ("baile_magenta", "baile_ciano", "baile_verde"):
        OB[n].data.energy = LIGHT_BASE[n] * 0.25
    cam((1.6, 13.2, 11.6), (0.0, 20.2, 10.1), 24, 220)


def m_golpes(t, u):
    A.pardo("P1", (0.0, 20.0, 9.0), -10, PB.P_POINT if beat_i(t) % 2 else PB.P_SMOKE)
    cam((0.8, 17.6, 10.6), (0.0, 20.0, 10.2), 30, 150)


def m_momento(t, u):
    P0 = Vector((-0.6, 20.0, 9.0))
    if t < CUE["qte_press"]:
        A.pardo("P1", tuple(P0), 90, guard(t))
        x = 5.0 - 4.6 * (t - CUTS[13]) / (CUE["qte_press"] - CUTS[13])
        A.hobo("M1", (x, 20.0, 9.0), -90, walk(t, 8))
    elif t < CUE["impact"]:
        s = (t - CUE["qte_press"]) / (CUE["impact"] - CUE["qte_press"])
        A.pardo("P1", (P0.x + 1.3 * s, P0.y, 9.0 + 0.9 * math.sin(s * math.pi * 0.6)), 90, PB.P_FLYKICK)
        A.hobo("M1", (2.4 - 0.3 * s, 20.0, 9.0), -90, PB.H_WALK[1])
    else:
        s = t - CUE["impact"]
        A.pardo("P1", (P0.x + 1.3, P0.y, 9.0 + max(0.0, 0.8 - 4 * s)), 90, PB.P_FLYKICK if s < 0.2 else PB.P_VICTORY)
        A.hobo("M1", (2.1 + 5.0 * s, 20.0 + 0.4 * s, 9.0 + max(0.0, 1.6 * s * (1.2 - s) * 3)), -90, PB.H_HIT)
        OB["M1"].rotation_euler = (math.radians(-60 * min(1, s * 3)), 0, math.radians(-90))
    # Camera orbits the clash, slowest in the bullet-time stretch
    k = ease((t - CUTS[13]) / (CUE["impact"] - CUTS[13] + 0.3))
    ang = math.radians(-70 + 100 * k)
    c = Vector((0.9, 20.0, 9.9))
    pos = c + Vector((math.sin(ang) * 4.2, -math.cos(ang) * 4.2, 0.5))
    cam(tuple(pos), tuple(c), 24, 240, 0.06 if 0 <= t - CUE["impact"] < 0.1 else 0.0, int(t * 30))


def m_sotaque(t, u):
    nod = 7 * math.sin(t * 17)
    talk = {**(PB.P_POINT if beat_i(t) % 2 else PB.P_STAND), "head": (nod, 0, 6 * math.sin(t * 5))}
    A.pardo("P1", (0.0, 20.0, 9.0), -18, talk)
    A.hobo("M1", (2.0, 21.6, 9.0), -140, {**PB.H_ALERT, "head": (0, 16, 0), "neck": (0, 10, 0)})
    cam((0.75, 18.2, 10.15), (0.05, 20.0, 10.05), 35, 120)


DONKEY_FROM, DONKEY_HIT = (-1.2, 16.6), (0.0, 24.85)  # it charges up the plaza and into the paredão


def donkey_down(s):
    """Knocked back off the speaker wall onto its back, s from 0 to 1."""
    A.static("JUMENTO", (DONKEY_HIT[0], DONKEY_HIT[1] - 0.7 * s, 9.0 + 0.35 * s), 180)
    OB["JUMENTO"].rotation_euler = (math.radians(-80 * s), 0, math.radians(180))


def m_jumento(t, u):
    x = 0.2 + 1.7 * ease((t - CUE["sidestep"]) / 0.15) if t >= CUE["sidestep"] else 0.2
    pose = guard(t) if t < CUE["sidestep"] else PB.P_LUNGE if t < CUE["crash"] else PB.P_VICTORY
    A.pardo("P1", (x, 22.6, 9.0), 0 if t < CUE["crash"] else -25, pose)
    j = OB["JUMENTO"]
    if t < CUE["charge"]:
        A.static("JUMENTO", (DONKEY_FROM[0], DONKEY_FROM[1] - 0.15 * abs(math.sin(t * 20)), 9.0), 180)
    elif t < CUE["crash"]:
        s = (t - CUE["charge"]) / (CUE["crash"] - CUE["charge"])
        p = lerp(DONKEY_FROM, DONKEY_HIT, s)
        A.static("JUMENTO", (p[0], p[1], 9.0 + 0.25 * abs(math.sin(math.pi * (t - CUE["charge"]) / 0.16))), 180)
    else:
        s = min(1.0, (t - CUE["crash"]) / 0.25)
        donkey_down(s)
        j.scale = (1.0, 1.0 - 0.3 * (1 - s), 1.0)
    shake = 0.12 if 0 <= t - CUE["crash"] < 0.15 else 0.0
    cam((5.2, 15.4, 11.6), (0.0, 21.8, 10.0), 22, 300, shake, int(t * 30))


def m_resultado(t, u):
    for i, (p, (x, y)) in enumerate(zip(PLAYERS, PLAZA_ROW)):
        if p == "P2":
            continue
        A.pardo(p, (x, y, 9.0), (i - 1.5) * 8, PB.P_VICTORY if p == "P1" else PB.P_DANCE_A if i % 2 else PB.P_DANCE_B)
    A.pardo("P2", (-0.1, 19.4, 9.0), 0, PB.P_VICTORY if t >= CUE["tag"] else guard(t))
    OB["P2_mic"].hide_render = OB["P2_mic"].hide_viewport = False
    donkey_down(1.0)
    k = ease(u / 1.18)
    cam(lerp((0.4, 14.2, 11.2), (0.3, 15.2, 10.8), k), (0.0, 20.4, 10.0), 22, 300)


MOMENTS = [m_card, m_apagao, m_crew, m_baseado, m_banger, m_combo, m_horda, m_muro, m_continue, m_aquecimento,
           m_mapa, m_perdeu, m_golpes, m_momento, m_sotaque, m_jumento, m_resultado]


def apply(f):
    t = song(f)
    i = moment_index(t)
    reset()
    MOMENTS[i](t, t - CUTS[i])
    bpy.context.view_layer.update()
    return i


# ---------------------------------------------------------------- anchors for the 2D effects
def anchors():
    """Named world points the HUD and effects track: heads, hands, chests, gun muzzles, items."""
    pts = {}
    for p in PLAYERS:
        if OB[p].location.y < -30:
            continue
        arm = OB[PARDO_ARM[p]]
        mw = arm.matrix_world
        pts[p + "_head"] = mw @ arm.pose.bones["Bone.001"].tail
        pts[p + "_chest"] = mw @ arm.pose.bones["Bone.016"].tail
        pts[p + "_hand"] = mw @ arm.pose.bones["Bone.004"].tail
    for m in ALL_HOBOS:
        if OB[m].location.y < -30:
            continue
        arm = OB[m + "_arm"]
        mw = arm.matrix_world
        pts[m + "_head"] = mw @ arm.pose.bones["Head"].tail
        pts[m + "_chest"] = mw @ arm.pose.bones["Spine1"].tail
        pts[m + "_hand"] = mw @ arm.pose.bones["LeftHand"].tail
    for m in HOBOS:
        g = OB.get(f"arma_{m}")
        if g and not g.hide_render:
            pts[m + "_muzzle"] = g.matrix_world @ Vector((0.12, -0.068, 0.11))
    for n in ("ITEM_radio", "ITEM_baseado"):
        if OB[n].location.z > -10:
            pts[n] = OB[n].matrix_world.translation.copy()
    j = OB["JUMENTO"]
    if j.location.y > -30:
        pts["JUMENTO_head"] = j.matrix_world @ Vector((0.0, -0.65, 1.15))
        pts["JUMENTO_body"] = j.matrix_world @ Vector((0.0, 0.0, 0.8))
    return pts
