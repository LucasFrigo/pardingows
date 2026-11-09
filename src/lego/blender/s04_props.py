# Step 4: flattens each import into one prefab mesh at the video's scale (a minifig is about 0.4 tall), base on z = 0 and centred, named PF_<name>, kept out of the render.
# Sets and shots place shared copies with set_lib.place.
import bpy, importlib, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import set_lib; importlib.reload(set_lib)
from set_lib import flatten, fresh, parts, save

OB = bpy.data.objects
pf = fresh("prefabs", bpy.context.scene)
pf.hide_render = True

for name, asset, kw in (
    ("cash", "cash", dict(length=0.2)),
    ("gold", "gold", dict(length=0.18)),
    ("briefcase", "briefcase", dict(length=0.17)),
    ("dj", "dj", dict(length=0.72)),
    ("joint", "joint", dict(length=0.16)),
    ("clock", "clock", dict(height=0.17)),
    ("vault", "vault", dict(height=1.7, decimate=0.2)),
    ("house_red", "house_red", dict(height=1.15)),
    ("house_tall", "house_tall", dict(height=2.5)),
    ("bus", "bus", dict(length=2.5)),
    ("car_red", "car_red", dict(length=0.95)),
    ("cars", "cars", dict(length=2.9)),
    ("bike", "bike", dict(length=0.55)),
    ("lamp", "lamp", dict(height=0.95)),
    ("tree", "tree", dict(height=1.9)),
    ("stump", "stump", dict(length=0.95)),
    ("plants", "plants", dict(length=2.6)),
    ("bush", "bush", dict(length=0.55)),
    ("flowers", "flowers", dict(length=0.5)),
    ("sofa", "sofa", dict(length=1.05)),
    ("table", "table", dict(length=0.8)),
):
    ob = flatten(name, asset, pf, **kw)
    # Models keep their colours, but all get the same moulded-plastic finish
    for m in ob.data.materials:
        if not m or not m.node_tree:
            continue
        b = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if b and not b.inputs["Roughness"].is_linked:
            b.inputs["Roughness"].default_value = min(max(b.inputs["Roughness"].default_value, 0.18), 0.42)

# The imports are spent. Everything is read from here on through the prefabs and the cast.
for ob in list(OB):
    if ob.get("asset") or ob.name.endswith("_import"):
        OB.remove(ob, do_unlink=True)
bpy.data.orphans_purge(do_recursive=True)
save()
print("=== PROPS DONE", flush=True)
