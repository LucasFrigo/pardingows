# Step 8: keys the whole video from timeline.json. Safe to re-run: clears its own animation first.
# Roots and camera move at 30 fps; bone poses step at 15 fps for the PS1 feel. No easing between keys.
import bpy, json, math, random, sys, importlib
from mathutils import Euler, Vector
sys.path.insert(0, r"C:\Users\lukeg\Projetos\pardingows\src\thps\blender")
sys.path.insert(0, r"C:\Users\lukeg\Projetos\pardingows\src\planeta\blender")
import lib, build, poses_moon
importlib.reload(lib); importlib.reload(build); importlib.reload(poses_moon)
from lib import BONES, SCALE
from build import height
from poses_moon import (STAND, HOP_A, HOP_B, LAND, INSULTED, SUNBATHE, CRUSHED, POINT, DENY, FACE, AIM, CH_STAND, CH_HOP_A, CH_HOP_B,
                        CH_POINT, CH_JEER, CH_AIM, CESAR_BONES, C_AWAY, C_GLARE, C_SHOUT, C_ROAR, C_STAND)

TL = json.load(open(r"C:\Users\lukeg\Projetos\pardingows\src\planeta\timeline.json", encoding="utf8"))
START, FRAMES = TL["start"], TL["frames"]
BEAT = 60 / TL["bpm"]
BAR1 = 36.571 - START  # "PLANETA" lands on this bar line, so every hop is on the beat
S = {k: (a - START, b - START) for k, (a, b) in TL["shots"].items()}
C = {k: t - START for k, t in TL["cues"].items()}
FAR = (500, 500, -50)

sc = bpy.context.scene
OB = bpy.data.objects
arm1, arm2 = OB["Armature"], OB["P2_arm"]
ARMS = {"P1": arm1, "P2": arm2}
CHIMPS = {n: OB[n + "_arm"] for n in ("CHIMP1", "CHIMP2", "CHIMP3")}
ces_arm, ces_skin = OB["CESAR_arm"], OB["CESAR_skin"]
jaw = ces_skin.data.shape_keys.key_blocks["open"]
lander, fardo, sun, flame = OB["LANDER"], OB["FARDO"], OB["SUN"], OB["lander flame"]
sun_lamp = OB["LV_sun"]
earth = next(c for c in OB["EARTH"].children if c.type == "MESH")
DUST = [OB[f"dust {i}"] for i in range(30)]
CARD = [OB[n] for n in ("card head", "card nose", "card stamp", "card tape")]
PLAIN = [OB["head"], OB["nose"]]
LANDER_X, LANDER_Y = lander.location.x, lander.location.y
GROUND = {"LANDER": height(LANDER_X, LANDER_Y) - 0.1}  # from the terrain, not the scene, which still holds the last run's keys

cam = OB.get("CAM")
if not cam:
    cam = bpy.data.objects.new("CAM", bpy.data.cameras.new("CAM"))
    sc.collection.objects.link(cam)
cam.data.clip_start = 0.05
cam.data.clip_end = 900
sc.camera = cam
sc.frame_start, sc.frame_end = 1, FRAMES
sc.render.filepath = "//frames/f_"

# ---- Clear previous animation
animated = [OB[n] for n in ("P1", "P2", "CHIMP1", "CHIMP2", "CHIMP3", "CESAR", "P1_body", "P2_body")] + [cam, cam.data, lander, fardo, sun, flame, earth, sun_lamp.data]
animated += list(CHIMPS.values()) + [arm1, arm2, ces_arm, ces_skin.data.shape_keys] + DUST + CARD + PLAIN
animated += [OB[n] for n in ("pistol hero", "pistol chimp", "cesar mouth", "P1_shadow", "P2_shadow", "CHIMP1_shadow", "CHIMP2_shadow", "CHIMP3_shadow", "CESAR_shadow")]
for ob in animated:
    if ob.animation_data:
        ob.animation_data_clear()
for a in [arm1, arm2, ces_arm] + list(CHIMPS.values()):
    for pb in a.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.matrix_basis.identity()
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

def rest_q(arm, bone_name, deg):
    rest = arm.data.bones[bone_name].matrix_local.to_quaternion()
    q = Euler(rad(*deg), "XYZ").to_quaternion()
    return rest.inverted() @ q @ rest

SMURF_BONES = ("spine", "head", "armR", "foreR", "armL", "foreL", "thighR", "shinR", "thighL", "shinL")
CHIMP_BONES = ("spine", "head", "armR", "foreR", "armL", "foreL", "thighR", "shinR", "thighL", "shinL")

def shadow_at(name, f, pos, size=1.0):
    K(OB[name + "_shadow"], "location", (pos[0], pos[1], 0.035), f)
    k = clamp(size * (1.0 - max(pos[2], 0) * 0.55), 0.35, 1.3)
    K(OB[name + "_shadow"], "scale", (k, k, 1), f)

def smurf(prefix, f, pos, yaw=0, pose=None, squash=(1, 1), pitch=0):
    root = OB[prefix]
    K(root, "location", pos, f)
    K(root, "rotation_euler", rad(0, pitch, yaw), f)
    K(root, "scale", (SCALE * squash[0], SCALE * squash[0], SCALE * squash[1]), f)
    shadow_at(prefix, f, pos, squash[0])
    if pose is not None and (f - 1) % 2 == 0:
        arm = ARMS[prefix]
        dx, dy, dz, rx, ry, rz = pose.get("body", (0,) * 6)
        K(OB[prefix + "_body"], "location", (dx, dy, dz), f)
        K(OB[prefix + "_body"], "rotation_euler", rad(rx, ry, rz), f)
        for alias in SMURF_BONES:
            pb = arm.pose.bones[BONES[alias]]
            K(pb, "rotation_quaternion", rest_q(arm, BONES[alias], pose.get(alias, (0, 0, 0))), f)

def chimp(name, f, pos, yaw=0, pose=None):
    K(OB[name], "location", pos, f)
    K(OB[name], "rotation_euler", rad(0, 0, yaw), f)
    shadow_at(name, f, pos)
    if pose is not None and (f - 1) % 2 == 0:
        arm = CHIMPS[name]
        for alias in CHIMP_BONES:
            K(arm.pose.bones[alias], "rotation_quaternion", rest_q(arm, alias, pose.get(alias, (0, 0, 0))), f)

def cesar(f, pos, pose=None):
    K(OB["CESAR"], "location", pos, f)
    shadow_at("CESAR", f, pos, 1.2)
    if pose is not None and (f - 1) % 2 == 0:
        for alias, bone in CESAR_BONES.items():
            K(ces_arm.pose.bones[bone], "rotation_quaternion", rest_q(ces_arm, bone, pose.get(alias, (0, 0, 0))), f)

def put_cam(f, pos, tgt, lens=24.0, shake=0.0):
    pos = Vector(pos)
    tgt = Vector(tgt)
    if shake:
        r = random.Random(f)
        pos = pos + Vector((r.uniform(-1, 1), r.uniform(-1, 1), r.uniform(-1, 1))) * shake
    K(cam, "location", pos, f)
    K(cam, "rotation_euler", (tgt - pos).to_track_quat("-Z", "Y").to_euler(), f)
    K(cam.data, "lens", lens, f)

def show(obs, on, f):
    for ob in obs:
        K(ob, "hide_render", not on, f)

def hop(v, a=None, height=0.42):
    """Low-gravity lope on the beat: height above ground and which leg leads."""
    t = (v - BAR1) / BEAT
    n = math.floor(t)
    u = t - n
    return height * 4 * u * (1 - u), n % 2 == 0

def puff(f, centre, age, spread=1.6, count=30):
    """Dust thrown out from a point. Re-rolled per piece, not per frame, so it travels instead of flickering."""
    for i, d in enumerate(DUST):
        r = random.Random(i * 13 + int(centre[0] * 7))
        a, s, up = r.uniform(0, 6.28), r.uniform(0.35, 1.0), r.uniform(0.15, 0.9)
        life = r.uniform(0.45, 0.95)
        u = age / life
        on = i < count and 0 <= u < 1
        if on:
            K(d, "location", (centre[0] + math.cos(a) * s * spread * (1 - (1 - u) ** 2), centre[1] + math.sin(a) * s * spread * (1 - (1 - u) ** 2) * 0.6, 0.05 + up * spread * 0.55 * u * (1.4 - u)), f)
        K(d, "hide_render", not on, f)

def hide_dust(f):
    for d in DUST:
        K(d, "hide_render", True, f)

for f in range(1, FRAMES + 1):
    v = (f - 1) / 30
    in_shot = lambda name: S[name][0] <= v < S[name][1]
    # ---- Defaults, overridden by the shots below
    p1 = dict(pos=FAR, pose=STAND)
    p2 = dict(pos=FAR, pose=STAND)
    apes = {n: dict(pos=FAR, pose=CH_STAND) for n in CHIMPS}
    ces = dict(pos=FAR, pose=C_STAND)
    jaw_open, gun_on, card_on = 0.0, False, False
    dust_at = None
    sun_z, lamp = -300.0, 3.2
    lander_z, flame_on = GROUND["LANDER"], False
    fardo_at = FAR
    fardo_squash = 1.0

    if in_shot("landing"):
        # Comes down hard on the first bar line of the chorus, flame out, dust everywhere
        td = C["touchdown"]
        if v < td:
            u = v / td
            lander_z = GROUND["LANDER"] + 42 * (1 - u) ** 2
        flame_on = v < td + 0.1
        if v >= td:
            dust_at = ((LANDER_X, LANDER_Y - 2.2), v - td, 5.5)
        h, lead = hop(v)
        if v >= td + 0.75:
            u = phase(v, td + 0.75, S["landing"][1])
            p1 = dict(pos=(LANDER_X + 2.2 + 2.2 * u, 6.4 - 4.4 * u, h), yaw=20, pose=HOP_A if lead else HOP_B)
        shake = 0.1 * (1 - phase(v, td, td + 0.45)) if v >= td else 0.0
        put_cam(f, (-5.4, -8.2, 0.65), (-5.0, 0, 3.3), 24, shake=shake)

    elif in_shot("rua1"):
        a = S["rua1"][0]
        x = 3.7 + 2.4 * (v - a)
        h, lead = hop(v)
        if v >= C["macaco"]:
            # Pulled up short. Hands go up and he stays put.
            x = 3.7 + 2.4 * (C["macaco"] - a)
            p1 = dict(pos=(x, 0, 0), yaw=90, pose=INSULTED)
        else:
            p1 = dict(pos=(x, 0, h), yaw=90, pose=HOP_A if lead else HOP_B)
        if v >= C["chimps_in"]:
            # Two chimps come bounding down the road straight at him
            u = phase(v, C["chimps_in"], C["macaco"])
            for name, dy, far in (("CHIMP1", 1.1, 7.0), ("CHIMP2", -0.9, 8.5)):
                ax = x + far + (2.5 - far) * u
                if v < C["macaco"]:
                    apes[name] = dict(pos=(ax, dy, h), yaw=-90 - dy * 6, pose=CH_HOP_A if lead else CH_HOP_B)
                else:
                    bob = 0.05 * abs(math.sin((v - C["macaco"]) * 9))
                    apes[name] = dict(pos=(ax, dy, bob), yaw=-90 - dy * 10, pose=CH_POINT if name == "CHIMP1" else CH_JEER)
        put_cam(f, (x - 2.5, -2.3, 1.0), (x + 2.2, 0.5, 1.05), 24, shake=0.03 * (1 - phase(v, C["macaco"], C["macaco"] + 0.25)) if v >= C["macaco"] else 0)

    elif in_shot("rua2"):
        # From in front, walking into the lens. The chimps keep pace behind, still pointing.
        a = S["rua2"][0]
        x = 12 + 2.4 * (v - a)
        h, lead = hop(v)
        p1 = dict(pos=(x, 0, h), yaw=90, pose=HOP_A if lead else HOP_B)
        for name, dy in (("CHIMP1", 1.2), ("CHIMP2", -1.1)):
            apes[name] = dict(pos=(x - 3.0, dy, h), yaw=90 + dy * 8, pose=CH_POINT if lead else CH_JEER)
        u = phase(v, C["scan"], C["pardo"])
        dist, cz, tz = 3.3 - 1.95 * u, 0.72 + 0.36 * u, 0.95 + 0.14 * u + h * 0.6
        put_cam(f, (x + dist, -0.7 + 0.5 * u, cz + h * 0.6), (x, -0.05, tz), 24)

    elif in_shot("sol"):
        # He stops and lets the sun come up on him. Then the bale arrives.
        x = 20.0
        land = C["fardo"]
        if v < land:
            p1 = dict(pos=(x, 0, 0), yaw=18, pose=SUNBATHE if v >= C["sun_rise"] else STAND)
            fall = phase(v, land - 0.34, land)
            if v >= land - 0.34:
                fardo_at = (x + 0.05, -0.15, 15 * (1 - fall * fall) + 0.44)
        else:
            k = phase(v, land, land + 0.2)
            sq = 1 - 0.28 * math.sin(k * math.pi) * (1 - k)
            fardo_at = (x + 0.05, -0.15, 0.44 * sq)
            fardo_squash = sq
            p1 = dict(pos=(x, -0.75, 0), yaw=8, pose=CRUSHED, squash=(1.35, 0.3 * sq))
            dust_at = ((x, -0.3), v - land, 3.2)
        rise = phase(v, C["sun_rise"], land + 0.2)
        sun_z = -175 + 265 * rise
        lamp = 3.2 + 1.8 * rise
        shake = 0.13 * (1 - phase(v, land, land + 0.5)) if v >= land else 0.0
        put_cam(f, (x, -2.9, 0.5), (x + 0.35, 2, 1.5), 24, shake=shake)

    elif in_shot("pardomon"):
        hx, px = 26.0, 28.3
        h, lead = hop(v)
        if v < C["nao"]:
            if v >= C["pardomon_in"]:
                u = phase(v, C["pardomon_in"], C["branco"] - 0.1)
                on_ground = u >= 1
                p2 = dict(pos=(px + 7 * (1 - u), 0, 0 if on_ground else h), yaw=-90,
                          pose=POINT if on_ground else (HOP_A if lead else HOP_B))
            p1 = dict(pos=(hx, 0, 0), yaw=90, pose=STAND)
            put_cam(f, (27.28, -3.7, 0.95), (27.28, 0, 1.4), 24)
        else:
            # Hard cut on NÃO: his face, full frame, head shaking
            s = 1 if int((v - C["nao"]) * 7) % 2 == 0 else -1
            pose = dict(DENY)
            pose["head"] = (4, 0, 15 * s)
            p1 = dict(pos=(hx, 0, 0), yaw=90, pose=pose)
            p2 = dict(pos=(px, 0, 0), yaw=-90, pose=POINT)
            put_cam(f, (hx + 1.6, -0.25, 0.9), (hx, -0.02, 1.16), 26, shake=0.03 * (1 - phase(v, C["nao"], C["nao"] + 0.3)))

    elif in_shot("papelao"):
        # Slowly into the visor, then the skin gives way on the word
        hx = 26.0
        p1 = dict(pos=(hx, 0, 0), yaw=0, pose=FACE)
        u = phase(v, S["papelao"][0], C["papelao"])
        card_on = C["papelao"] <= v < C["papelao_off"]
        d = -1.75 + 0.42 * u
        put_cam(f, (hx, d, 1.14), (hx, -0.16, 1.08), 24, shake=0.018 * (1 - phase(v, C["papelao"], C["papelao"] + 0.25)) if card_on else 0)

    elif in_shot("standoff"):
        # The camera circles two identical poses. Nobody fires.
        hx, cx = 40.3, 42.0
        a = S["standoff"][0]
        flt = 0.16 + 0.07 * math.sin(v * 3.1)
        drawn = v >= C["draw"]
        gun_on = drawn
        p1 = dict(pos=(hx, 0, flt), yaw=90, pose=AIM if drawn else STAND)
        apes["CHIMP1"] = dict(pos=(cx, 0, 0.16 + 0.07 * math.sin(v * 3.1 + 1.0)), yaw=-90, pose=CH_AIM if drawn else CH_STAND)
        ang = math.radians(-114 + (v - a) * 20)
        r = 3.5 - 0.5 * phase(v, C["pistola"], C["pistola"] + 0.15)
        put_cam(f, (41.15 + r * math.cos(ang), r * math.sin(ang), 0.72), (41.15, 0, 1.12), 24,
                shake=0.03 * (1 - phase(v, C["pistola"], C["pistola"] + 0.3)) if v >= C["pistola"] else 0)

    elif in_shot("cesar") or in_shot("report"):
        # From the ground, looking up at him. He only looks at us on his own name.
        cx = 58.0
        n1, n2 = C["nao1"], C["nao2"]
        if v < C["nao1"]:
            a = S["cesar"][0]
            ces = dict(pos=(cx, 0, 0), pose=C_AWAY if v < 53.38 - START else C_GLARE)
            d = -1.9 + 0.4 * phase(v, a, n1)
            put_cam(f, (cx, d, 0.78), (cx, -0.05, 1.7), 24)
        else:
            shout = n1 <= v < n2
            ces = dict(pos=(cx, 0, 0), pose=C_SHOUT if shout else C_ROAR)
            hit = n1 if shout else n2
            jaw_open = 1.0 if v < S["cesar"][1] + 0.1 else 0.0
            if shout and v >= hit + 0.34:
                jaw_open = 0.35
            k = 1 - phase(v, hit, hit + 0.3)
            d = -1.42 + (0.2 if v >= n2 else 0.0)
            put_cam(f, (cx, d, 0.82), (cx, -0.05, 1.74), 24, shake=(0.05 if shout else 0.075) * k)

    # ---- Apply the frame
    smurf("P1", f, **p1)
    smurf("P2", f, **p2)
    for name, spec in apes.items():
        chimp(name, f, **spec)
    cesar(f, **ces)
    K(jaw, "value", jaw_open, f)
    show([OB["cesar mouth"]], jaw_open > 0, f)
    show([OB["pistol hero"], OB["pistol chimp"]], gun_on, f)
    show(CARD, card_on, f)
    show(PLAIN, not card_on, f)
    K(lander, "location", (LANDER_X, LANDER_Y, lander_z), f)
    K(flame, "hide_render", not flame_on, f)
    r = random.Random(f)
    K(flame, "scale", (r.uniform(0.85, 1.1), r.uniform(0.85, 1.1), r.uniform(0.7, 1.25)), f)
    K(fardo, "location", fardo_at, f)
    K(fardo, "scale", (0.5 * (2 - fardo_squash), 0.5 * (2 - fardo_squash), 0.5 * fardo_squash), f)
    K(sun, "location", (34, 420, sun_z), f)
    K(sun, "scale", (3.0, 3.0, 3.0), f)
    K(sun_lamp.data, "energy", lamp, f)
    # Earth would sit right behind the top bar in the two tight face shots, and block the sun on the way up
    K(earth, "hide_render", in_shot("sol") or in_shot("papelao") or (in_shot("pardomon") and v >= C["nao"]), f)
    if dust_at:
        puff(f, dust_at[0], dust_at[1], dust_at[2])
    else:
        hide_dust(f)

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
