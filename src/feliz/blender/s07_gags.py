# Step 7: everything the gags need, built in code unless noted. All of it starts stashed inside the log and s08 keys it into place.
# Nest, pit, debt letter, confetti, water droplets and ripples, butterflies, glass orb, bubbles, aurora, electric arcs, crowd copies.
import bpy, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib, set_lib, path, build; importlib.reload(set_lib); importlib.reload(path); importlib.reload(build)
from set_lib import TEXTURES, blobs, fresh, gloss, place, srgb
from build import ring
import lib; importlib.reload(lib)
from lib import BONES, Mesh
from mathutils import Matrix, Vector

OB = bpy.data.objects
if "P1_inchaco" in OB:
    OB.remove(OB["P1_inchaco"], do_unlink=True)
g = fresh("gags")
STASH = (0, 0, -12)
rng = random.Random(21)


def stash(ob):
    ob.location = STASH
    return ob


# ---- Wasp nest: stacked papery rings
paper = gloss("ninho", rgb="b9a07a", rough=0.6, coat=0.1)
paper2 = gloss("ninho2", rgb="8f7a5a", rough=0.7, coat=0.05)
parts = []
for k, (z, r) in enumerate(((0.0, 0.2), (0.14, 0.32), (0.3, 0.4), (0.47, 0.42), (0.63, 0.34), (0.76, 0.2))):
    parts.append(("ball", (0, 0, z), (r, r, 0.11), k % 2, None))
parts.append(("ball", (0, -0.34, 0.24), (0.1, 0.05, 0.1), 1, None))
stash(blobs("ninho", parts, [paper, paper2], g))

# Swollen lumps for the pardo's face, on his head bone so they follow it
ARM = OB["Armature"]
lump = gloss("inchaco", rgb="e8795f", rough=0.3, coat=0.6)
head_c = Vector((0, -0.693, 2.774))
parts = [("ball", head_c + Vector((-1.12, -0.62, -0.18)), (0.36, 0.32, 0.34), 0, None), ("ball", head_c + Vector((1.14, -0.56, -0.08)), (0.42, 0.36, 0.4), 0, None),
         ("ball", head_c + Vector((-0.86, -1.0, 0.42)), (0.2, 0.18, 0.18), 0, None), ("ball", head_c + Vector((0.92, -1.02, -0.6)), (0.2, 0.18, 0.18), 0, None)]
lumps = blobs("P1_inchaco", parts, [lump], bpy.data.collections["rigs"])
set_lib.recentre(lumps, head_c)
lumps.parent = ARM
lumps.parent_type = "BONE"
lumps.parent_bone = BONES["head"]
bpy.context.view_layer.update()
lumps.matrix_world = ARM.matrix_world @ Matrix.Translation(head_c)
bpy.context.view_layer.update()
lumps["rest_scale"] = list(lumps.scale)

# ---- The pit: a dark disc with a raised rim of earth
pit_dark, pit_rim = gloss("buraco", rgb="1c130c", rough=0.9, coat=0), gloss("buraco borda", rgb="7a5a36", rough=0.8, coat=0)
parts = [("ball", (0, 0, 0.0), (1.0, 1.0, 0.05), 0, None)]
for k in range(12):
    a = 2 * math.pi * k / 12
    parts.append(("ball", (math.cos(a) * 1.02, math.sin(a) * 1.02, 0.02), (0.26, 0.26, 0.11), 1, None))
stash(blobs("buraco", parts, [pit_dark, pit_rim], g))

# ---- Debt letter: two halves with a jagged tear, sharing one drawn texture
img = bpy.data.images.load(os.path.join(TEXTURES, "carta.png"), check_existing=True)
letter_m = gloss("carta", image=img, rough=0.55, coat=0.1)
LW, LH = 1.7, 1.2
TEAR = [(0.02, 0.5), (-0.05, 0.36), (0.05, 0.22), (-0.04, 0.08), (0.05, -0.08), (-0.05, -0.22), (0.04, -0.36), (-0.02, -0.5)]


def half(name, sign):
    edge = [(x * LW * 0.5, z * LH) for x, z in TEAR]
    outer = [(sign * LW / 2, -LH / 2), (sign * LW / 2, LH / 2)]
    pts = edge + outer if sign > 0 else edge + outer
    # Fan from the middle of the half
    mid = (sign * LW / 4, 0)
    verts = [(mid[0], 0, mid[1])] + [(x, 0, z) for x, z in edge] + [(outer[0][0], 0, outer[0][1]), (outer[1][0], 0, outer[1][1])]
    n = len(verts) - 1
    faces = [(0, 1 + k, 1 + (k + 1) % n) for k in range(n)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    uv = me.uv_layers.new(name="UVMap")
    for p in me.polygons:
        for li in p.loop_indices:
            v = me.loops[li].vertex_index
            uv.data[li].uv = (verts[v][0] / LW + 0.5, verts[v][2] / LH + 0.5)
    me.materials.append(letter_m)
    me.update()
    ob = OB.new(name, me)
    g.objects.link(ob)
    return stash(ob)


half("carta_a", -1)
half("carta_b", 1)

# ---- Confetti: paper scraps, some with the letter's red and cream
scrap_m = [gloss("confete" + str(i), rgb=c, rough=0.5, coat=0.3) for i, c in enumerate(("fbf6e6", "d62f33", "fbf6e6", "ffd23c", "4fd0ff"))]
for i in range(70):
    me = bpy.data.meshes.new(f"confete.{i}")
    s = rng.uniform(0.05, 0.11)
    me.from_pydata([(-s, 0, -s * 0.7), (s, 0, -s * 0.7), (s, 0, s * 0.7), (-s, 0, s * 0.7)], [], [(0, 1, 2, 3)])
    me.materials.append(scrap_m[i % 5])
    ob = OB.new(f"confete.{i}", me)
    g.objects.link(ob)
    stash(ob)

# ---- Giant droplets and ripples
drop = gloss("gota", rgb="9fe6ff", rough=0.02, coat=1.0, spec=1.0, alpha=0.72)
for i in range(3):
    parts = [("ball", (0, 0, 0.55), (0.55, 0.55, 0.55), 0, None), ("cone", (0, 0, 0.82), (0.47, 0.47, 0.92), 0, None)]
    stash(blobs(f"gota.{i}", parts, [drop], g)).visible_shadow = False
rip = gloss("onda anel", rgb="ffffff", rough=0.1, coat=1.0, emit=0.6)
for i in range(6):
    m = Mesh()
    n = 48
    for k in range(n):
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        ring(m, (math.cos(a0), math.sin(a0), 0), (math.cos(a1), math.sin(a1), 0), 0.016, 0, n=5)
    ob = m.build(f"anel.{i}", [rip], None, g)
    for p in ob.data.polygons:
        p.use_smooth = True
    stash(ob)

# ---- Butterflies: two wing quads on a body point, flapped by s08
for i, col in enumerate(("ffcf3c", "ff8fc0", "7fd0ff", "ffffff", "ffa24f", "c79bff")):
    wm = gloss(f"asa{i}", rgb=col, rough=0.3, coat=0.6, emit=0.15)
    root = OB.new(f"borboleta.{i}", None)
    g.objects.link(root)
    stash(root)
    for sign in (-1, 1):
        me = bpy.data.meshes.new(f"asa.{i}.{sign}")
        w = 0.15
        me.from_pydata([(0, -0.03, 0), (0, 0.12, 0), (sign * w, 0.16, 0.0), (sign * w * 1.15, -0.1, 0)], [], [(0, 1, 2, 3) if sign > 0 else (3, 2, 1, 0)])
        me.materials.append(wm)
        wing = OB.new(f"asa.{i}.{'r' if sign > 0 else 'l'}", me)
        g.objects.link(wing)
        wing.parent = root

# ---- The glass orb, with a glowing core
orb_core = gloss("orbe nucleo", rgb="6fe8ff", rough=0.2, emit=3.0)
orb_glass = gloss("orbe vidro", rgb="dff8ff", rough=0.02, coat=1.0, spec=1.0, alpha=0.4)
stash(blobs("orbe", [("ball", (0, 0, 0), (0.2, 0.2, 0.2), 0, None), ("ball", (0, 0, 0), (0.46, 0.46, 0.46), 1, None)], [orb_core, orb_glass], g))

# ---- Bubbles: a shared soapy material, see-through with a bright rainbow rim
bm = bpy.data.materials.get("bolha") or bpy.data.materials.new("bolha")
bm.use_nodes = True
t = bm.node_tree
t.nodes.clear()
out = t.nodes.new("ShaderNodeOutputMaterial")
tr = t.nodes.new("ShaderNodeBsdfTransparent")
gl = t.nodes.new("ShaderNodeBsdfGlossy")
gl.inputs["Roughness"].default_value = 0.04
em = t.nodes.new("ShaderNodeEmission")
em.inputs["Strength"].default_value = 1.3
lw = t.nodes.new("ShaderNodeLayerWeight")
lw.inputs["Blend"].default_value = 0.22
hue = t.nodes.new("ShaderNodeValToRGB")
cr = hue.color_ramp
for e, (p, c) in zip(cr.elements, ((0.0, "bff4ff"), (1.0, "ffc6f2"))):
    e.position = p
    e.color = (*srgb(c), 1)
t.links.new(lw.outputs["Fresnel"], hue.inputs[0])
t.links.new(hue.outputs[0], em.inputs[0])
add = t.nodes.new("ShaderNodeAddShader")
t.links.new(gl.outputs[0], add.inputs[0])
t.links.new(em.outputs[0], add.inputs[1])
mixs = t.nodes.new("ShaderNodeMixShader")
rim = t.nodes.new("ShaderNodeMapRange")
rim.inputs["From Min"].default_value = 0.1
rim.inputs["From Max"].default_value = 0.8
rim.inputs["To Min"].default_value = 0.05
t.links.new(lw.outputs["Facing"], rim.inputs["Value"])
t.links.new(rim.outputs[0], mixs.inputs[0])
t.links.new(tr.outputs[0], mixs.inputs[1])
t.links.new(add.outputs[0], mixs.inputs[2])
t.links.new(mixs.outputs[0], out.inputs[0])
bm.surface_render_method = "BLENDED"
bubble_mesh = blobs("bolha_src", [("ball", (0, 0, 0), (1, 1, 1), 0, None)], [bm], g).data
OB.remove(OB["bolha_src"], do_unlink=True)
for i in range(130):
    ob = OB.new(f"bolha.{i}", bubble_mesh)
    g.objects.link(ob)
    ob.visible_shadow = False  # soap film casts no dark blob on the grass
    stash(ob)

# ---- Aurora ribbons: tall curved strips, additive glow with a soft top and bottom. Their brightness is one keyed value.
am = bpy.data.materials.get("aurora") or bpy.data.materials.new("aurora")
am.use_nodes = True
t = am.node_tree
t.nodes.clear()
out = t.nodes.new("ShaderNodeOutputMaterial")
tc = t.nodes.new("ShaderNodeTexCoord")
sp = t.nodes.new("ShaderNodeSeparateXYZ")
t.links.new(tc.outputs["UV"], sp.inputs[0])
col = t.nodes.new("ShaderNodeValToRGB")
for e, (p, c) in zip(col.color_ramp.elements, ((0.15, "2dffa8"), (0.95, "c66bff"))):
    e.position = p
    e.color = (*srgb(c), 1)
t.links.new(sp.outputs["Y"], col.inputs[0])
env = t.nodes.new("ShaderNodeMapRange")
env.inputs["From Min"].default_value = 0.0
env.inputs["From Max"].default_value = 1.0
env.interpolation_type = "LINEAR"
pw = t.nodes.new("ShaderNodeMath")
pw.operation = "SINE"
mul = t.nodes.new("ShaderNodeMath")
mul.operation = "MULTIPLY"
mul.inputs[1].default_value = math.pi
t.links.new(sp.outputs["Y"], mul.inputs[0])
t.links.new(mul.outputs[0], pw.inputs[0])
noise = t.nodes.new("ShaderNodeTexNoise")
noise.noise_dimensions = "4D"
noise.inputs["Scale"].default_value = 9.0
wv = t.nodes.new("ShaderNodeValue")
wv.name = "onda"
t.links.new(tc.outputs["UV"], noise.inputs["Vector"])
t.links.new(wv.outputs[0], noise.inputs["W"])
mul2 = t.nodes.new("ShaderNodeMath")
mul2.operation = "MULTIPLY"
t.links.new(pw.outputs[0], mul2.inputs[0])
t.links.new(noise.outputs[0], mul2.inputs[1])
fade = t.nodes.new("ShaderNodeValue")
fade.name = "brilho"
fade.outputs[0].default_value = 0.0
mul3 = t.nodes.new("ShaderNodeMath")
mul3.operation = "MULTIPLY"
t.links.new(mul2.outputs[0], mul3.inputs[0])
t.links.new(fade.outputs[0], mul3.inputs[1])
em2 = t.nodes.new("ShaderNodeEmission")
t.links.new(col.outputs[0], em2.inputs[0])
t.links.new(mul3.outputs[0], em2.inputs[1])
tr2 = t.nodes.new("ShaderNodeBsdfTransparent")
add2 = t.nodes.new("ShaderNodeAddShader")
t.links.new(em2.outputs[0], add2.inputs[0])
t.links.new(tr2.outputs[0], add2.inputs[1])
t.links.new(add2.outputs[0], out.inputs[0])
am.surface_render_method = "BLENDED"
for i, (base, wob, z0, h) in enumerate(((58, 8, 10, 34), (72, 12, 16, 40), (86, 10, 8, 44))):
    verts, faces, uvs = [], [], []
    N = 60
    for k in range(N + 1):
        u = k / N
        x = -90 + 180 * u
        y = base + wob * math.sin(u * 7 + i * 1.7)
        verts += [(x, y, z0), (x, y + 3, z0 + h)]
    for k in range(N):
        faces.append((2 * k, 2 * k + 2, 2 * k + 3, 2 * k + 1))
    me = bpy.data.meshes.new(f"aurora.{i}")
    me.from_pydata(verts, [], faces)
    uv = me.uv_layers.new(name="UVMap")
    for p in me.polygons:
        for li in p.loop_indices:
            v = me.loops[li].vertex_index
            uv.data[li].uv = ((v // 2) / N * 3 + i, v % 2)
    me.materials.append(am)
    ob = OB.new(f"aurora.{i}", me)
    g.objects.link(ob)

# ---- Electric arcs: zigzag tubes, three shapes each, flickered by s08. They hang on each Berg's root, in smurf units.
arc_m = gloss("arco", rgb="9fe9ff", emit=7.0, rough=0.5, coat=0)
ANCHORS = (((0, 0, 7.4), (2.8, -0.5, 6.0)), ((0, 0, 7.4), (-2.8, -0.5, 6.2)), ((1.4, -0.4, 3.6), (3.2, -0.6, 1.2)), ((-1.4, -0.4, 3.6), (-3.2, -0.6, 1.2)), ((0.6, -0.8, 3.0), (-0.6, -1.2, 0.5)))
arc_meshes = []
for k in range(4):
    m = Mesh()
    for a, b in ANCHORS:
        a, b = Vector(a), Vector(b)
        pts = [a]
        n = 7
        for j in range(1, n):
            pts.append(a + (b - a) * (j / n) + Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))) * 0.5)
        pts.append(b)
        for p0, p1 in zip(pts, pts[1:]):
            ring(m, p0, p1, 0.075, 0, n=5)
    me = m.build(f"arco_src.{k}", [arc_m], None, g).data
    OB.remove(OB[f"arco_src.{k}"], do_unlink=True)
    arc_meshes.append(me)
for p in ("P2", "B1", "B2", "B3"):
    for k, me in enumerate(arc_meshes):
        ob = OB.new(f"arco_{p}.{k}", me)
        g.objects.link(ob)
        ob.parent = OB[p]
        ob.scale = (0, 0, 0)

# ---- Steam puffs for the fuming Berg, and a hit star
puff = gloss("vapor", rgb="ffffff", rough=0.7, coat=0, emit=0.25)
for i in range(8):
    stash(blobs(f"vapor.{i}", [("ball", (0, 0, 0), (0.14, 0.14, 0.14), 0, None), ("ball", (0.1, 0.03, 0.06), (0.1, 0.1, 0.1), 0, None)], [puff], g))
star_m = gloss("estrela", rgb="fff06a", rough=0.3, emit=2.0)
parts = [("cone", (0, 0, 0), (0.1, 0.1, 0.8), 0, (0, a, 0)) for a in range(0, 360, 45)]
stash(blobs("estrela", parts, [star_m], g))

# ---- The hero door: a dark gap over the model's door, and a panel that swings. In the house's own space, its front faces +X.
house = OB["casa_heroi"]
DOOR_X, DOOR_Y, DOOR_W, DOOR_H = 2.32, -0.08, 1.16, 2.12
gap = gloss("vao", rgb="120c08", rough=1, coat=0)
door_m = gloss("porta", rgb="c9353a", rough=0.32, coat=0.6)
me = bpy.data.meshes.new("vao")
me.from_pydata([(DOOR_X, DOOR_Y - DOOR_W / 2, 0.08), (DOOR_X, DOOR_Y + DOOR_W / 2, 0.08), (DOOR_X, DOOR_Y + DOOR_W / 2, 0.08 + DOOR_H), (DOOR_X, DOOR_Y - DOOR_W / 2, 0.08 + DOOR_H)], [], [(0, 1, 2, 3)])
me.materials.append(gap)
ob = OB.new("vao", me)
g.objects.link(ob)
ob.parent = house
m = Mesh()
m.box((0.03, DOOR_W / 2, DOOR_H / 2), (0.03, DOOR_W / 2, DOOR_H / 2))
door = m.build("porta", [door_m], house, g)
door.location = (DOOR_X + 0.012, DOOR_Y - DOOR_W / 2, 0.08)

# ---- Crowd: copies of the four villagers with their outfits
crowd = fresh("multidao")
NAMES = ("gato", "pato", "cachorro", "guaxinim")
for i in range(16):
    src = OB["V_" + NAMES[i % 4]]
    c = src.copy()
    c.name = f"C_{i}"
    crowd.objects.link(c)
    c.location = STASH
    for piece in ("shades", "chain"):
        a0 = OB[f"V_{NAMES[i % 4]}_{piece}"]
        a = a0.copy()
        a.name = f"C_{i}_{piece}"
        crowd.objects.link(a)
        a.parent = c
for v in OB:
    if v.name in ("V_gato", "V_pato", "V_cachorro", "V_guaxinim"):
        v.location = STASH
for name in ("ilha_aero", "balao_aero"):
    OB[name].location.z = -80
set_lib.save()
print("gags ok", len(g.objects), "objects")
