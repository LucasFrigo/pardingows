# Renders the cast review. Works on the saved scene without saving over it.
#   "$BLENDER" -b blender/lego/lego.blend -P src/lego/blender/cast_sheet.py
# Out: blender/lego/review/03-*.png
import bpy, json, math, os, sys
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import set_lib, poses_lego as PL
from set_lib import REVIEW, WORK, srgb

sc = bpy.context.scene
OB = bpy.data.objects
NAMES = json.load(open(os.path.join(WORK, "cast.json")))["names"]

w = bpy.data.worlds.get("studio") or bpy.data.worlds.new("studio")
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (*srgb("b9c6d2"), 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 0.7
sc.world = w
for name, en, rot, col in (("key", 2.6, (50, 8, 30), "fff4e4"), ("fill", 0.6, (65, 0, -60), "dcebff"), ("rim", 1.4, (70, 0, 170), "ffffff")):
    ob = OB.get(name)
    if not ob:
        ob = OB.new(name, bpy.data.lights.new(name, "SUN"))
        sc.collection.objects.link(ob)
    ob.data.energy = en
    ob.data.color = srgb(col)
    ob.data.angle = math.radians(14)
    ob.rotation_euler = [math.radians(a) for a in rot]
cam = OB.get("sheet_cam")
if not cam:
    cam = OB.new("sheet_cam", bpy.data.cameras.new("sheet_cam"))
    sc.collection.objects.link(cam)
sc.camera = cam
sc.render.engine = "BLENDER_EEVEE"
sc.eevee.taa_render_samples = 32
sc.view_settings.view_transform = "Standard"
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGB"
floor = OB.get("sheet_floor")
if not floor:
    me = bpy.data.meshes.new("sheet_floor")
    me.from_pydata([(-40, -40, 0), (40, -40, 0), (40, 40, 0), (-40, 40, 0)], [], [(0, 1, 2, 3)])
    floor = OB.new("sheet_floor", me)
    sc.collection.objects.link(floor)
    me.materials.append(set_lib.abs_mat("sheet floor", "8fa0ae", 0.5))


def stand(name, x, y=0.0, rz=0.0, action=None):
    r = OB["CH_" + name]
    r.location = (x, y, r["z0"] + (PL.ground(action) if action else 0.0))
    r.rotation_euler = (0, 0, math.radians(rz))


def park():
    for n in NAMES:
        OB["CH_" + n].location = (500, 500, -50)
        OB["CH_" + n].rotation_euler = (0, 0, 0)
        PL.clear(OB[n + "_arm"])


def shoot(path, pos, tgt, lens, res):
    pos, tgt = Vector(pos), Vector(tgt)
    cam.location = pos
    cam.rotation_euler = (tgt - pos).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = lens
    cam.data.clip_start, cam.data.clip_end = 0.02, 200
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.filepath = os.path.join(REVIEW, path)
    bpy.context.view_layer.update()
    bpy.ops.render.render(write_still=True)


# Under the mask, Pardo's shades and nose only appear when he lifts it in the shot
for piece_name in ("pardo_rob_shades", "pardo_rob_nose"):
    OB[piece_name].hide_render = True

HEROES = ["pardo", "israel", "robber1", "pardo_rob", "father", "child"]
CROWD = [n for n in NAMES if n not in HEROES and not n.startswith("robber")]
GAP = 0.46

# Heroes, front and back
park()
xs = [(i - (len(HEROES) - 1) / 2) * GAP for i in range(len(HEROES))]
for n, x in zip(HEROES, xs):
    stand(n, x)
shoot("03-heroes-frente.png", (0.5, -3.7, 0.5), (0, 0, 0.24), 50, (1500, 620))
shoot("03-heroes-costas.png", (-0.5, 3.7, 0.5), (0, 0, 0.24), 50, (1500, 620))

# Faces up close
for n, nm in (("pardo", "pardo"), ("israel", "israel"), ("robber1", "robber"), ("pardo_rob", "pardo-rob"), ("father", "father"), ("child", "child")):
    park()
    stand(n, 0, 0, 22)
    z = OB["CH_" + n]["z0"] + 0.35
    shoot(f"03-close-{nm}.png", (0.12, -0.95, z + 0.06), (0, 0, z + 0.015), 70, (420, 420))

# The crowd models
park()
xs = [(i - (len(CROWD) - 1) / 2) * 0.44 for i in range(len(CROWD))]
for n, x in zip(CROWD, xs):
    stand(n, x)
shoot("03-crowd.png", (0.4, -4.4, 0.45), (0, 0, 0.22), 50, (1500, 420))

# Which wrist twist turns the palms up? One figure, four twists.
for tw in (0, 90, 180, -90):
    park()
    stand("pardo", 0, 0, 12)
    PL.apply(OB["pardo_arm"], PL.six_seven(OB["pardo_arm"], 0.0, tw))
    shoot(f"03-twist-{tw}.png", (0.05, -0.85, 0.5), (0, -0.1, 0.22), 60, (420, 420))

# Six-seven: both extremes on Pardo, with others behind him to show it fits every figure
for tag, u in (("a", 0.0), ("b", 0.5)):
    park()
    stand("pardo", 0, 0)
    PL.apply(OB["pardo_arm"], PL.six_seven(OB["pardo_arm"], u))
    for i, n in enumerate(("crook", "policeman", "sky", "israel")):
        stand(n, (i - 1.5) * 0.5, 0.45)
        PL.apply(OB[n + "_arm"], PL.six_seven(OB[n + "_arm"], u))
    shoot(f"03-seven-{tag}.png", (0.25, -1.9, 0.5), (0, 0.1, 0.24), 50, (620, 620))

# Motion check from the rig's own actions, lifted onto the floor
park()
for n, x, act, u in (("pardo", -0.85, "Dance", 0.3), ("father", -0.3, "Run", 0.25), ("child", 0.12, "Run", 0.25)):
    stand(n, x, action=act)
    PL.apply(OB[n + "_arm"], PL.sample(act, u))
# And the hand-keyed ones, which stay on the rig's clean rest pose
stand("israel", 0.55)
PL.apply(OB["israel_arm"], PL.wave(OB["israel_arm"], 0.25))
stand("robber2", 1.0)
PL.apply(OB["robber2_arm"], PL.walk(OB["robber2_arm"], 0.25))
shoot("03-motion.png", (0.1, -3.1, 0.5), (0.05, 0, 0.22), 50, (1300, 520))
print("=== SHEET DONE", flush=True)
sys.stdout.flush()
os._exit(0)
