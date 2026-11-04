# Step 1b: gold chain and shades, plus the PS1 material pass on the smurf.
# Safe to re-run: removes its own objects first.
import bpy, bmesh, math
from mathutils import Vector

arm = bpy.data.objects["Armature"]
body = bpy.data.objects["body"]

def make_mat(name, rgb, emit=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    n = m.node_tree.nodes
    n.clear()
    out = n.new("ShaderNodeOutputMaterial")
    bsdf = n.new("ShaderNodeBsdfDiffuse")
    bsdf.inputs["Color"].default_value = (*srgb(rgb), 1)
    if emit:
        add = n.new("ShaderNodeAddShader")
        e = n.new("ShaderNodeEmission")
        e.inputs["Color"].default_value = (*srgb(rgb), 1)
        e.inputs["Strength"].default_value = emit
        m.node_tree.links.new(bsdf.outputs[0], add.inputs[0])
        m.node_tree.links.new(e.outputs[0], add.inputs[1])
        m.node_tree.links.new(add.outputs[0], out.inputs[0])
    else:
        m.node_tree.links.new(bsdf.outputs[0], out.inputs[0])
    return m

def srgb(hexstr):
    v = [int(hexstr[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in v]

def attach(ob, bone):
    world = ob.matrix_world.copy()
    ob.parent = arm
    ob.parent_type = "BONE"
    ob.parent_bone = bone
    bpy.context.view_layer.update()
    ob.matrix_world = world

def new_object(name, verts, faces, mats, face_mats=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    for m in mats:
        me.materials.append(m)
    if face_mats:
        for p, i in zip(me.polygons, face_mats):
            p.material_index = i
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob

def box(verts, faces, fm, mi, c, size):
    """Axis-aligned box appended to the arrays."""
    i = len(verts)
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                verts.append((c[0] + sx * size[0], c[1] + sy * size[1], c[2] + sz * size[2]))
    for f in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
        faces.append(tuple(i + k for k in f))
        fm.append(mi)

for name in ("shades", "chain", "medallion"):
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)

gold = make_mat("gold", "ffc62e", emit=0.25)
gold_d = make_mat("gold dark", "b5791a")
black = make_mat("shades black", "14122b")
shine = make_mat("shades shine", "e8f0ff", emit=0.5)

# Shades: two curved lenses hugging the head sphere (centre (0,-0.69,4.64), r 1.37).
C = Vector((0, -0.69, 4.64))
R = 1.43
def on_head(x, z, extra=0.0):
    dz = z - C.z
    r2 = max((R + extra) ** 2 - x * x - dz * dz, 0.01)
    return (x, C.y - math.sqrt(r2), z)

verts, faces, fm = [], [], []
Z = 4.98
for side in (-1, 1):
    # lens: a rounded hexagon, wider at the outside, in (x offset, z offset)
    outline = [(0.10, 0.30), (0.48, 0.36), (0.86, 0.26), (0.90, -0.04), (0.62, -0.26), (0.28, -0.25), (0.10, -0.06)]
    i = len(verts)
    for ox, oz in outline:
        verts.append(on_head(side * ox, Z + oz))
    for ox, oz in outline:
        verts.append(on_head(side * ox, Z + oz, extra=0.05))
    n = len(outline)
    faces.append(tuple(i + n + (k if side > 0 else n - 1 - k) for k in range(n)))
    fm.append(0)
    for k in range(n):
        a, b = k, (k + 1) % n
        faces.append((i + a, i + b, i + n + b, i + n + a) if side > 0 else (i + b, i + a, i + n + a, i + n + b))
        fm.append(0)
    # diagonal shine
    j = len(verts)
    for ox, oz in ((0.34, 0.27), (0.48, 0.28), (0.30, -0.15), (0.20, -0.14)):
        verts.append(on_head(side * ox, Z + oz, extra=0.07))
    faces.append((j, j + 1, j + 2, j + 3) if side > 0 else (j + 3, j + 2, j + 1, j))
    fm.append(1)
# bridge
a = on_head(0, Z + 0.06, extra=0.05)
box(verts, faces, fm, 0, a, (0.18, 0.04, 0.05))
# temples run back to the ears
for side in (-1, 1):
    # three short segments that follow the skull, so nothing sticks out past the ears
    for x0, x1 in ((0.88, 1.08), (1.08, 1.22), (1.22, 1.32)):
        a, b = on_head(side * x0, Z + 0.05, extra=0.02), on_head(side * x1, Z + 0.05, extra=0.02)
        box(verts, faces, fm, 0, ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, a[2]),
            (abs(a[0] - b[0]) / 2 + 0.02, abs(a[1] - b[1]) / 2 + 0.02, 0.04))
attach(new_object("shades", verts, faces, [black, shine], fm), "Bone.001")

# Chain: ring of beads fitted to the real torso surface with raycasts, front low, back high.
depsgraph = bpy.context.evaluated_depsgraph_get()
body_eval = body.evaluated_get(depsgraph)
inv = body.matrix_world.inverted()
axis = Vector((0, -0.42, 0))
pts = []
N = 22
for k in range(N):
    th = 2 * math.pi * k / N
    # th=0 is the chest (-Y); z rises to the nape
    z = 2.98 + (3.72 - 2.98) * (1 - math.cos(th)) / 2
    d = Vector((math.sin(th), -math.cos(th), 0))
    origin = Vector((axis.x, axis.y, z)) + d * 4
    hit, loc, nor, idx = body_eval.ray_cast(inv @ origin, (inv.to_3x3() @ -d).normalized())
    p = body.matrix_world @ loc if hit else Vector((axis.x, axis.y, z)) + d * 0.6
    pts.append(p + d * 0.07)

verts, faces, fm = [], [], []
for k, p in enumerate(pts):
    s = 0.075 if k % 2 == 0 else 0.055  # alternating links
    box(verts, faces, fm, 0, tuple(p), (s, s, s))
attach(new_object("chain", verts, faces, [gold]), "Bone.016")

# Medallion: octagonal disc hanging from the front of the chain
front = pts[0]
c = Vector((0, front.y - 0.05, front.z - 0.30))
verts, faces, fm = [], [], []
def disc(radius, y, mi):
    i = len(verts)
    for k in range(8):
        a = (k + 0.5) * math.pi / 4
        verts.append((c.x + radius * math.cos(a), y, c.z + radius * math.sin(a)))
    for k in range(8):
        a = (k + 0.5) * math.pi / 4
        verts.append((c.x + radius * math.cos(a), y + 0.09, c.z + radius * math.sin(a)))
    faces.append(tuple(i + k for k in range(8)))
    fm.append(mi)
    for k in range(8):
        a, b = k, (k + 1) % 8
        faces.append((i + 8 + a, i + 8 + b, i + b, i + a))
        fm.append(mi)
disc(0.32, c.y, 1)
disc(0.20, c.y - 0.03, 0)
attach(new_object("medallion", verts, faces, [gold, gold_d], fm), "Bone.016")

# PS1 pass on the textured parts: no specular, hard texels
for m in bpy.data.materials:
    if not m.use_nodes:
        continue
    for n in m.node_tree.nodes:
        if n.type == "BSDF_PRINCIPLED":
            n.inputs["Roughness"].default_value = 1.0
            n.inputs["Specular IOR Level"].default_value = 0.0
for ob in bpy.data.objects:
    if ob.type == "MESH":
        for p in ob.data.polygons:
            p.use_smooth = False
print("outfit ok; chain beads", len(pts), "front", tuple(round(v, 2) for v in pts[0]), "nape", tuple(round(v, 2) for v in pts[N // 2]))
bpy.ops.wm.save_mainfile()
