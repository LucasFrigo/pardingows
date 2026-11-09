# Step 3 review renders: turnarounds (front, 3/4, side, back) of every cast member, and pose strips of P1 and M1 from poses_brawl.
# Tiles go to blender/pardao/review/cast/, then src/pardao/cast_sheet.mjs labels and tiles them into 03-*.png.
# Temporary camera, sun, floor and world are removed afterwards, and poses and visibility are put back.
#   node src/thps/bl.mjs run src/pardao/blender/cast_sheet.py
import bpy, json, math, os, sys
from mathutils import Vector, Euler
try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    HERE = os.path.join(os.environ.get("PARDAO_ROOT", r"E:\Projetos\pardingows"), "src", "pardao", "blender")
sys.path.insert(0, HERE)
import importlib, set_lib, poses_brawl as PB
importlib.reload(set_lib)
importlib.reload(PB)
from set_lib import WORK, REVIEW

OUT = os.path.join(REVIEW, "cast")
os.makedirs(OUT, exist_ok=True)
CAST = json.load(open(os.path.join(WORK, "cast.json"), encoding="utf8"))
G = CAST["pardo_ground_body_z"]
sc = bpy.context.scene
OB = bpy.data.objects


def tree(name):
    root = OB[name]
    return [root] + list(root.children_recursive)


def bbox(objs):
    """World box of the posed, evaluated vertices (bound_box can still hold the rest pose of a skinned mesh)."""
    dg = bpy.context.evaluated_depsgraph_get()
    mins, maxs = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for ob in objs:
        if ob.type != "MESH" or ob.hide_viewport:
            continue
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        for v in me.vertices:
            p = ev.matrix_world @ v.co
            mins = Vector(map(min, mins, p))
            maxs = Vector(map(max, maxs, p))
        ev.to_mesh_clear()
    return mins, maxs


cam_data = bpy.data.cameras.new("review_cam")
cam_data.type = "ORTHO"
cam_data.clip_end = 500
cam = OB.new("review_cam", cam_data)
sun_data = bpy.data.lights.new("review_sun", "SUN")
sun_data.energy = 3.2
sun_data.angle = math.radians(8)
sun = OB.new("review_sun", sun_data)
sun.rotation_euler = (math.radians(48), 0, math.radians(-38))
floor_me = bpy.data.meshes.new("review_floor")
floor_me.from_pydata([(-60, -80, 0), (60, -80, 0), (60, 40, 0), (-60, 40, 0)], [], [(0, 1, 2, 3)])
floor = OB.new("review_floor", floor_me)
fm = bpy.data.materials.new("review_floor")
fm.use_nodes = True
fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.2, 0.21, 0.24, 1)
floor_me.materials.append(fm)
temp = (cam, sun, floor)
for o in temp:
    sc.collection.objects.link(o)
old_world, old_cam = sc.world, sc.camera
world = bpy.data.worlds.new("review_world")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.32, 0.34, 0.4, 1)
sc.world, sc.camera = world, cam
r = sc.render
old = (r.engine, r.resolution_x, r.resolution_y, r.resolution_percentage, r.filepath, r.film_transparent)
r.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in {e.identifier for e in r.bl_rna.properties["engine"].enum_items} else "BLENDER_EEVEE"
r.resolution_percentage = 100

saved = {o.name: o.hide_render for o in OB}
for o in OB:
    if o not in temp:
        o.hide_render = True


def shoot(names, path, yaw, centre, scale, w=360, h=480, pitch=82):
    objs = [o for n in names for o in tree(n)]
    for o in objs:
        o.hide_render = o.hide_viewport  # hidden props (like P2's mic) stay hidden
    rot = Euler((math.radians(pitch), 0, math.radians(yaw)))
    cam.rotation_euler = rot
    cam.location = Vector(centre) + rot.to_matrix() @ Vector((0, 0, 30))
    cam_data.ortho_scale = scale
    r.resolution_x, r.resolution_y = w, h
    r.filepath = path
    bpy.ops.render.render(write_still=True)
    for o in objs:
        o.hide_render = True


def subject_frame(names):
    bpy.context.view_layer.update()
    mins, maxs = bbox([o for n in names for o in tree(n)])
    c = (mins + maxs) / 2
    size = max(maxs.z - mins.z, (maxs.x - mins.x) * 0.75, (maxs.y - mins.y) * 0.75) * 1.18  # ortho_scale spans the taller side (height) of a portrait render
    return c, size


PLAYERS = ["P1", "P2", "P3", "P4"]
HOBOS = ["M1", "M2", "M3"]
for p in PLAYERS:
    PB.pose_pardo(p, PB.P_STAND, G)
for m in HOBOS:
    PB.pose_hobo(m, PB.H_STAND)

listing = {"turn": [], "pardo": [], "hobo": []}
VIEWS = (("frente", 0), ("3/4", 35), ("lado", 90), ("costas", 180))
for name in PLAYERS + HOBOS + ["MB", "JUMENTO"]:
    c, size = subject_frame([name])
    row = []
    for label, yaw in VIEWS:
        path = os.path.join(OUT, f"turn_{name}_{yaw}.png")
        shoot([name], path, yaw, c, size)
        row.append([label, os.path.basename(path)])
    listing["turn"].append([name, row])
    print("turnaround", name)

# Pose strips at a fixed scale so the poses compare
c, _ = subject_frame(["P1"])
for pname in PB.PARDO_STRIP:
    PB.pose_pardo("P1", PB.get(pname), G)
    path = os.path.join(OUT, f"pose_{pname}.png")
    shoot(["P1"], path, 30, (c.x, c.y, 0.9), 2.6)
    listing["pardo"].append([pname, os.path.basename(path)])
c, _ = subject_frame(["M1"])
for pname in PB.H_STRIP:
    PB.pose_hobo("M1", PB.get(pname))
    path = os.path.join(OUT, f"pose_{pname}.png")
    shoot(["M1"], path, 30, (c.x, c.y, 1.0), 2.8)
    listing["hobo"].append([pname, os.path.basename(path)])
print("strips done")

# Put back: Pardos and Mildingows standing, visibility as it was
for p in PLAYERS:
    PB.pose_pardo(p, PB.P_STAND, G)
for m in HOBOS:
    PB.pose_hobo(m, PB.H_STAND)
for o in OB:
    if o.name in saved:
        o.hide_render = saved[o.name]
r.engine, r.resolution_x, r.resolution_y, r.resolution_percentage, r.filepath, r.film_transparent = old
sc.world, sc.camera = old_world, old_cam
for o in temp:
    bpy.data.objects.remove(o, do_unlink=True)
bpy.data.cameras.remove(cam_data)
bpy.data.lights.remove(sun_data)
bpy.data.meshes.remove(floor_me)
bpy.data.materials.remove(fm)
bpy.data.worlds.remove(world)
json.dump(listing, open(os.path.join(OUT, "listing.json"), "w", encoding="utf8"), indent=1)
set_lib.save()
print("done")
