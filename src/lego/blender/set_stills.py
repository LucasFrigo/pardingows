# One finished still per world, with its figures in place, and the time each frame takes.
#   "$BLENDER" -b blender/lego/lego.blend -P src/lego/blender/set_stills.py -- [engine] [set,set] [outsuffix] [samples]
# Out: blender/lego/review/04-<set><suffix>.png. Doesn't save the scene.
import bpy, json, math, os, sys, time
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import set_lib, look_lib, poses_lego as PL
from set_lib import FAR, REVIEW, WORK
from world_data import SETS, origin

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ENGINE = args[0] if len(args) > 0 and args[0] else "CYCLES"
ONLY = args[1].split(",") if len(args) > 1 and args[1] not in ("", "-") else SETS
SUFFIX = args[2] if len(args) > 2 and args[2] != "-" else ""
SAMPLES = int(args[3]) if len(args) > 3 else None

sc = bpy.context.scene
OB = bpy.data.objects
HEROES = ["pardo", "israel", "robber1", "robber2", "robber3", "pardo_rob", "father", "child"]
print("engine", ENGINE, look_lib.engine(ENGINE, SAMPLES), flush=True)
cam = OB.get("lego_cam") or OB.new("lego_cam", bpy.data.cameras.new("lego_cam"))
if cam.name not in sc.collection.objects:
    sc.collection.objects.link(cam)
sc.camera = cam
cam.data.sensor_fit = "VERTICAL"
cam.data.sensor_height = 36
cam.data.clip_start, cam.data.clip_end = 0.02, 400
cam.data.dof.use_dof = True
for n in ("pardo_rob_shades", "pardo_rob_nose"):
    OB[n].hide_render = True


def park():
    for n in HEROES:
        OB["CH_" + n].location = FAR
        OB["CH_" + n].rotation_euler = (0, 0, 0)
        PL.clear(OB[n + "_arm"])
    for n in ("crook", "escapee", "policeman", "banker", "pepper", "brickster", "henchman", "sky", "dewey"):
        PL.clear(OB[n + "_arm"])


def put(n, o, x, y, rz=0.0, pose=None, action=None, u=0.3, rx=0.0, dz=0.0):
    r = OB["CH_" + n]
    arm = OB[n + "_arm"]
    if action:
        PL.apply(arm, PL.sample(action, u))
    elif pose:
        PL.apply(arm, pose(arm))
    r.location = (o[0] + x, o[1] + y, o[2] + r["z0"] + dz + (PL.ground(action) if action else 0.0))
    r.rotation_euler = (math.radians(rx), 0, math.radians(rz))


def shoot(name, o, pos, tgt, lens=38, fstop=4.0, focus=None):
    pos, tgt = Vector(pos), Vector(tgt)
    cam.location = pos + Vector(o)
    cam.rotation_euler = (tgt - pos).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = lens
    cam.data.dof.aperture_fstop = fstop
    cam.data.dof.focus_distance = focus or (tgt - pos).length
    sc.render.filepath = os.path.join(REVIEW, f"04-{name}{SUFFIX}.png")
    bpy.context.view_layer.update()
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"TIME {name} {time.time() - t0:.1f}s", flush=True)


def rant_pose(arm):
    pose = {}
    PL.adjust(arm, pose, "armUp_L", (-62, 0, 18))
    PL.adjust(arm, pose, "armUp_R", (-20, 0, -14))
    PL.adjust(arm, pose, "head", (8, 0, -14))
    return pose


def lift_pose(arm):
    pose = {}
    PL.adjust(arm, pose, "armUp_R", (-90, 0, -18))
    PL.adjust(arm, pose, "armUp_L", (10, 0, 6))
    return pose


def ask_pose(arm):
    pose = {}
    PL.adjust(arm, pose, "armUp_L", (-30, 0, 34))
    PL.adjust(arm, pose, "armUp_R", (-30, 0, -34))
    return pose


def scene_rua(o):
    put("israel", o, -0.2, -0.05, 24, rant_pose)
    put("pardo", o, 0.2, 0.05, -14, action="Idle_Impatient", u=0.2)
    shoot("rua", o, (0.0, -1.72, 0.22), (0.0, 0, 0.2))


def scene_calendario(o):
    put("pardo", o, -0.1, -0.2, 8, action="Stretching", u=0.45)
    shoot("calendario", o, (0.15, -1.5, 0.28), (-0.05, 0, 0.26))


def scene_cofre(o):
    put("pardo_rob", o, 0.0, -0.1, 0, lift_pose)
    put("robber1", o, -0.42, 0.15, 18, action="Flexing", u=0.5)
    put("robber2", o, 0.42, 0.15, -18, action="AirGuitar", u=0.3)
    put("robber3", o, 0.15, 0.5, -6, action="Idle_Impatient", u=0.6)
    shoot("cofre", o, (0.0, -1.5, 0.22), (0, 0, 0.2))


def scene_parque(o):
    put("pardo", o, 0.0, 0.26, 0, PL.sit, dz=7 * set_lib.PLATE - 0.17)
    shoot("parque", o, (0.12, -1.25, 0.27), (0, 0.15, 0.3))


def scene_corrida(o):
    put("father", o, 0.1, -0.3, 0, action="Run", u=0.25)
    put("child", o, -0.16, -0.3, 0, action="Run", u=0.7)
    shoot("corrida", o, (-0.03, -1.95, 0.2), (-0.03, -0.25, 0.26), lens=38, fstop=3.2)


def scene_praca(o):
    put("pardo", o, 0.0, -0.45, 0, lambda a: PL.six_seven(a, 0.0))
    for n in ("crook", "escapee", "policeman", "banker", "pepper", "brickster", "henchman", "sky", "dewey"):
        arm = OB[n + "_arm"]
        PL.apply(arm, PL.six_seven(arm, 0.0))
    shoot("praca", o, (0.05, -1.75, 0.34), (0, 0, 0.22), lens=38, fstop=5.6)


def scene_interrogatorio(o):
    put("pardo", o, 0.0, 0.86, 0, ask_pose)
    shoot("interrogatorio", o, (0.0, -0.85, 0.46), (0, 0.6, 0.36), lens=38)


def scene_quarto(o):
    # Face down on the bed, on top of the blanket
    put("pardo", o, -0.05, 0.25, 180, rx=90, dz=8 * set_lib.PLATE + 0.06)
    shoot("quarto", o, (0.72, -0.3, 0.6), (0.0, 0.45, 0.3), lens=38)


FN = dict(rua=scene_rua, calendario=scene_calendario, cofre=scene_cofre, parque=scene_parque, corrida=scene_corrida, praca=scene_praca, interrogatorio=scene_interrogatorio, quarto=scene_quarto)
for name in ONLY:
    park()
    look_lib.activate(name)
    FN[name](origin(name))
# The first frame of a world includes building it. A repeat with the same scene shows what each later frame costs.
t0 = time.time()
bpy.ops.render.render(write_still=True)
print(f"TIME repeat of {ONLY[-1]} {time.time() - t0:.1f}s", flush=True)
print("=== STILLS DONE", flush=True)
sys.stdout.flush()
os._exit(0)
