# Step 3e: turns the raw imports into clean actors with a root empty at ground level.
# Cop: root COP, faces -Y, Z up, metres. Car: root CAR, long axis Y.
# Needs a fresh import (run s07 first); re-running s07 + s08 together is safe.
import bpy, bmesh, sys, importlib, math
import numpy as np
from mathutils import Matrix
sys.path.insert(0, r"C:\Users\lukeg\Projetos\pardingows\src\thps\blender")
import lib; importlib.reload(lib)
from lib import Mesh, empty, make_mat

coll = bpy.data.collections["assets"]

def wipe(*names):
    for n in names:
        ob = bpy.data.objects.get(n)
        if ob:
            bpy.data.objects.remove(ob, do_unlink=True)

# Keep one cop out of the three variants, and drop the stray material-less spheres
wipe("Object_48", "Object_89", "Object_47", "Object_88", "Object_45", "Object_86", "metarig.001", "metarig.002",
     "Icosphere", "Icosphere.001", "Icosphere.002")

for name in ("COP", "CAR", "cop_mouth", "cop_plug", "cop_cap"):
    wipe(name)

# The FBX inside the cop's glTF is double-rotated, so the character arrives Y-up.
cop_top = bpy.data.objects["Sketchfab_model"]
cop_root = empty("COP", None, coll=coll, size=0.5)
bpy.context.view_layer.update()
cop_top.parent = cop_root
cop_top.matrix_parent_inverse = Matrix.Identity(4)
cop_top.matrix_basis = Matrix.Rotation(math.radians(90), 4, "X") @ cop_top.matrix_basis

car_top = bpy.data.objects["Sketchfab_model.001"]
car_root = empty("CAR", None, coll=coll, size=1.0)
car_top.parent = car_root
car_top.matrix_parent_inverse = Matrix.Identity(4)
car_top.location.z += 0.25  # tyres on the ground

# PS1 pass: hard texels, no specular
for mat_name in ("cop_mat", "car_PS1_BaseColor_512_v2"):
    m = bpy.data.materials[mat_name]
    for n in m.node_tree.nodes:
        if n.type == "TEX_IMAGE":
            n.interpolation = "Closest"
        if n.type == "BSDF_PRINCIPLED":
            n.inputs["Roughness"].default_value = 1.0
            n.inputs["Specular IOR Level"].default_value = 0.0
            n.inputs["Metallic"].default_value = 0.0

# The import leaves a 90-degree pose on the hips; the rest pose is the upright one
cop_arm = bpy.data.objects["Object_4"]
for pb in cop_arm.pose.bones:
    pb.matrix_basis = Matrix.Identity(4)

# Repaint the car: scrub the source badge and lettering so all markings are fictional.
# Coordinates are in a 256 px texture, top-left origin, measured from the texture itself.
img = bpy.data.images[[n.image.name for n in bpy.data.materials["car_PS1_BaseColor_512_v2"].node_tree.nodes if n.type == "TEX_IMAGE"][0]]
w, h = img.size
k = w / 256
px = np.empty(w * h * 4, np.float32)
img.pixels.foreach_get(px)
px = px.reshape(h, w, 4)

def fill(x0, y0, x1, y1, sample):
    """Paints a rectangle with the colour found at a reference point."""
    col = px[h - 1 - int(sample[1] * k), int(sample[0] * k), :3].copy()
    px[h - int(y1 * k):h - int(y0 * k), int(x0 * k):int(x1 * k), :3] = col

fill(6, 97, 30, 120, (12, 125))    # shield and small door text -> door white
fill(10, 203, 16, 246, (8, 225))   # rear quarter lettering -> panel black
scrubbed = bpy.data.images.new("car_pardo", w, h, alpha=True)
scrubbed.pixels.foreach_set(px.ravel())
scrubbed.filepath_raw = r"C:\Users\lukeg\Projetos\pardingows\blender\solucao\textures\car_pardo.png"
scrubbed.file_format = "PNG"
scrubbed.save()
for n in bpy.data.materials["car_PS1_BaseColor_512_v2"].node_tree.nodes:
    if n.type == "TEX_IMAGE":
        n.image = scrubbed

# Fictional door lettering, as real geometry so it reads correctly on both sides
letter = make_mat("car letter", "16181f")
accent = make_mat("car accent", "d42020")
for side, name in ((1, "car letter r"), (-1, "car letter l")):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = "POLÍCIA"
    cu.size = 0.26
    cu.align_x = "CENTER"
    cu.resolution_u = 1
    cu.materials.append(letter)
    ob = bpy.data.objects.new(name, cu)
    coll.objects.link(ob)
    ob.parent = car_root
    ob.location = (side * 0.875, -0.15, 0.56)
    ob.rotation_euler = (math.radians(90), 0, math.radians(90 if side > 0 else -90))
    Mesh().box((side * 0.865, -0.15, 0.47), (0.01, 1.05, 0.035)).build(name + " stripe", [accent], car_root, coll)

# Roof flashers: alternate on the beat in the shots script
for name, x, col in (("flash red", 0.2, "ff2a20"), ("flash blue", -0.2, "2a60ff")):
    Mesh().box((x, 0.15, 1.28), (0.2, 0.1, 0.05)).build(name, [make_mat(name, col, emit=4.0)], car_root, coll)

# Split the cap off the skinned mesh so it can pop off in the shock gag.
# It keeps its armature modifier, so it follows the head until its object location is animated.
bpy.context.view_layer.update()
cop_mesh = bpy.data.objects["Object_7"]
CAP_Z = 1.665
cap = cop_mesh.copy()
cap.data = cop_mesh.data.copy()
cap.name = "cop_cap"
coll.objects.link(cap)
cap.parent = cop_mesh.parent
for ob, keep_cap in ((cop_mesh, False), (cap, True)):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.faces.ensure_lookup_table()
    # verts are in rest pose, same axes as the armature
    drop = [f for f in bm.faces if (min(v.co.z for v in f.verts) > CAP_Z) != keep_cap]
    bmesh.ops.delete(bm, geom=drop, context="FACES")
    bm.to_mesh(ob.data)
    bm.free()
print("cap faces", len(cap.data.polygons), "body faces", len(cop_mesh.data.polygons))

# Close the hole the cap leaves: a dark hair plug on the head bone
hair = make_mat("cop hair", "3a2412")
plug = Mesh().prism([(0.09 * math.cos(k * math.pi / 3), 0.09 * math.sin(k * math.pi / 3)) for k in range(6)], 1.64, 1.685).build("cop_plug", [hair], None, coll)
world = Matrix.Translation((0, 0.03, 0))
plug.parent = cop_arm
plug.parent_type = "BONE"
plug.parent_bone = "head_05"
bpy.context.view_layer.update()
plug.matrix_world = cop_root.matrix_world @ world
# The shocked mouth: a dark octagon on the face, hidden until the gag
mouth = Mesh().prism([(0.024 * math.cos(k * math.pi / 4), 0.036 * math.sin(k * math.pi / 4)) for k in range(8)], 0, 0.006).build("cop_mouth", [make_mat("cop mouth", "1a0606")], None, coll)
mouth.parent = cop_arm
mouth.parent_type = "BONE"
mouth.parent_bone = "head_05"
bpy.context.view_layer.update()
mouth.matrix_world = cop_root.matrix_world @ Matrix.Translation((0, -0.098, 1.525)) @ Matrix.Rotation(math.radians(90), 4, "X")

# Parked out of frame until the shots place them
cop_root.location = (30, 3, 0)
car_root.location = (24, -2, 0)
bpy.context.view_layer.update()
me = bpy.data.objects["Object_7"]
pts = [me.matrix_world @ v.co for v in me.data.vertices]
print("cop box", [round(min(p[i] for p in pts), 2) for i in range(3)], [round(max(p[i] for p in pts), 2) for i in range(3)])
pts = [o.matrix_world @ v.co for o in car_root.children_recursive if o.type == "MESH" for v in o.data.vertices]
print("car box", [round(min(p[i] for p in pts), 2) for i in range(3)], [round(max(p[i] for p in pts), 2) for i in range(3)])
print("armature", bpy.data.objects["Object_4"].name, [o.name for o in bpy.data.objects["Object_4"].children])
bpy.ops.wm.save_mainfile()
