# Step 5a: everything the gags need beyond the cast and the stage. Re-runnable (deletes what it made, tagged "gag_made").
#   H01-H14  the horde: extra Mildingows sharing M1-M3's rig, meshes and colours, each with its own armature object (own pose)
#   ITEM_baseado, ITEM_radio  power-up items (collection instances) for the pickup and the banger
#   luz_pardo  a light that rides with P1 so he never vanishes in the blackout ("eu não sumo no escuro")
#   flash_<M>  a short point light per shooter for the muzzle flashes
#   node src/thps/bl.mjs run src/pardao/blender/s07_gags.py
import bpy, json, os, sys
from mathutils import Matrix
try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    HERE = os.path.join(os.environ.get("PARDAO_ROOT", r"E:\Projetos\pardingows"), "src", "pardao", "blender")
sys.path.insert(0, HERE)
import importlib, set_lib
importlib.reload(set_lib)
from set_lib import WORK

OB = bpy.data.objects
for o in [o for o in OB if o.get("gag_made")]:
    OB.remove(o, do_unlink=True)
gags = bpy.data.collections.get("gags") or bpy.data.collections.new("gags")
if gags.name not in bpy.context.scene.collection.children:
    bpy.context.scene.collection.children.link(gags)


def new(name, data=None):
    o = OB.new(name, data)
    o["gag_made"] = True
    gags.objects.link(o)
    return o


# ---- the horde
HORDE = [f"H{i:02d}" for i in range(1, 15)]
for i, h in enumerate(HORDE):
    src = ("M1", "M2", "M3")[i % 3]
    root = new(h)
    root.empty_display_size = 0.3
    arm = new(h + "_arm", OB[src + "_arm"].data)
    arm.parent = root
    for part in ("skin", "jacket", "beard"):
        s = OB[f"{src}_{part}"]
        o = s.copy()
        o.name = f"{h}_{part}"
        o["gag_made"] = True
        gags.objects.link(o)
        o.parent = arm
        o.matrix_parent_inverse = Matrix.Identity(4)
        for md in o.modifiers:
            if md.type == "ARMATURE":
                md.object = arm
    root.location = (20 + i * 1.2, -46, 0)  # parked behind the lineup until a shot calls them
    root.scale = (1.0 + (i % 4 - 1.5) * 0.03,) * 3  # a little height variety in the crowd

# ---- power-up items
for name, prefab, s in (("ITEM_baseado", "baseado", 3.2), ("ITEM_radio", "radio", 4.0)):
    o = new(name)
    o.instance_type = "COLLECTION"
    o.instance_collection = bpy.data.collections["PF_" + prefab]
    o.scale = (s,) * 3
    o.location = (0, -60, -20)

# ---- lights
ld = bpy.data.lights.new("luz_pardo", "POINT")
ld.energy, ld.color, ld.shadow_soft_size, ld.use_shadow = 0.0, (1.0, 0.85, 0.7), 0.4, False
lp = new("luz_pardo", ld)
for m in ("M1", "M2", "M3"):
    fd = bpy.data.lights.new(f"flash_{m}", "POINT")
    fd.energy, fd.color, fd.shadow_soft_size = 0.0, (1.0, 0.75, 0.35), 0.05
    new(f"flash_{m}", fd)

json.dump({"horde": HORDE}, open(os.path.join(WORK, "gags.json"), "w", encoding="utf8"))
set_lib.save()
print("gags:", len(HORDE), "horde members, items and lights")
