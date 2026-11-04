# Step 7: places the set pieces on the moon and hangs the sky. Safe to re-run: pole copies are rebuilt, the rest just move.
import bpy, math, sys, importlib
sys.path.insert(0, r"C:\Users\lukeg\Projetos\pardingows\src\planeta\blender")
import build; importlib.reload(build)
from build import ROAD, height

OB = bpy.data.objects
coll = bpy.data.collections["assets"]


def place(name, x, y, yaw=0, tilt=(0, 0), sink=0.0, scale=1.0):
    ob = OB[name]
    ob.location = (x, y, height(x, y) - sink)
    ob.rotation_euler = (math.radians(tilt[0]), math.radians(tilt[1]), math.radians(yaw))
    ob.scale = (scale,) * 3


place("LANDER", -7.5, 9.0, yaw=20, sink=0.1)
place("MODULE", -21.0, 12.5, yaw=-35, tilt=(-14, 9), sink=0.5)  # came down hard
place("MOONBASE", 30.0, 26.0, yaw=15, sink=0.2)

# Brazilian poles marching along the far kerb, the way they would down any street
for ob in [o for o in OB if o.name.startswith("POLE.")]:
    OB.remove(ob, do_unlink=True)
for k in range(-2, 8):
    if k == 0:
        root = OB["POLE"]
    else:
        root = OB["POLE"].copy()
        coll.objects.link(root)
        for c in OB["POLE"].children:
            c2 = c.copy()
            coll.objects.link(c2)
            c2.parent = root
    x = 16.0 * k + 2.0
    root.location = (x, ROAD + 1.6, height(x, ROAD + 1.6))
    root.rotation_euler = (0, 0, 0)

# The sky doesn't move. The sun is keyed in the shots, so it rises on "SOL".
OB["EARTH"].location = (34, 280, 118)
OB["EARTH"].scale = (5.0,) * 3
OB["SUN"].location = (-30, 420, -30)
OB["SUN"].scale = (0.9,) * 3
OB["ASTEROIDS"].location = (-70, 300, 150)
OB["ASTEROIDS"].rotation_euler = (0.4, 0.2, 0.3)
OB["ASTEROIDS"].scale = (2.4,) * 3
# A lamp just for César. It has no shadow and falls off long before anyone else's mark.
key = OB.get("cesar key")
if not key:
    key = bpy.data.objects.new("cesar key", bpy.data.lights.new("cesar key", "POINT"))
    coll.objects.link(key)
key.data.energy = 55
key.data.color = (1.0, 0.93, 0.82)
key.data.use_shadow = False
key.location = (57.3, -1.3, 1.05)
bpy.context.view_layer.update()
bpy.ops.wm.save_mainfile()
print("set placed; poles", sum(1 for o in OB if o.name.startswith("POLE") and not o.parent))
