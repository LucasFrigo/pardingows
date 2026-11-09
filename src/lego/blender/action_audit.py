# Shows every one of the base rig's actions at two points on one figure, so the broken ones can be left out of the shots.
#   "$BLENDER" -b blender/lego/lego.blend -P src/lego/blender/action_audit.py
# Out: blender/lego/review/03-acoes/<action>_<u>.png, montaged by the caller. Doesn't save the scene.
import bpy, json, math, os, sys
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import set_lib, poses_lego as PL
from set_lib import REVIEW, WORK, srgb

sc = bpy.context.scene
OB = bpy.data.objects
OUT = os.path.join(REVIEW, "03-acoes")
os.makedirs(OUT, exist_ok=True)
NAMES = json.load(open(os.path.join(WORK, "cast.json")))["names"]
for n in NAMES:
    OB["CH_" + n].location = (500, 500, -50)

w = bpy.data.worlds.new("audit")
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (*srgb("b9c6d2"), 1)
sc.world = w
sun = OB.new("audit sun", bpy.data.lights.new("audit sun", "SUN"))
sc.collection.objects.link(sun)
sun.data.energy = 3
sun.rotation_euler = [math.radians(a) for a in (50, 8, 30)]
cam = OB.new("audit cam", bpy.data.cameras.new("audit cam"))
sc.collection.objects.link(cam)
sc.camera = cam
pos, tgt = Vector((0.5, -1.7, 0.5)), Vector((0, 0, 0.22))
cam.location = pos
cam.rotation_euler = (tgt - pos).to_track_quat("-Z", "Y").to_euler()
cam.data.lens = 50
sc.render.engine = "BLENDER_EEVEE"
sc.eevee.taa_render_samples = 8
sc.render.resolution_x, sc.render.resolution_y = 230, 300
sc.view_settings.view_transform = "Standard"
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGB"

root = OB["CH_israel"]
arm = OB["israel_arm"]
for a in sorted(x.name[2:] for x in bpy.data.actions if x.name.startswith("U_")):
    for u in (0.25, 0.6):
        PL.apply(arm, PL.sample(a, u))
        root.location = (0, 0, root["z0"] + PL.ground(a))
        bpy.context.view_layer.update()
        sc.render.filepath = os.path.join(OUT, f"{a}_{int(u * 100):02d}.png")
        bpy.ops.render.render(write_still=True)
print("=== AUDIT DONE", flush=True)
sys.stdout.flush()
os._exit(0)
