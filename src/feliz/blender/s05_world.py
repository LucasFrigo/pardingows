# Step 5: the world. A rolling log of grass and sand, a curved sea, trees and houses along the walk, clouds, a town square and bushes.
# Grass, sand and water each read a keyed "aero" value that takes them from cozy to Frutiger Aero.
import bpy, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib, set_lib, path; importlib.reload(set_lib); importlib.reload(path)
from set_lib import blobs, fresh, gloss, place, srgb
from path import AERO, BERG, BEACH, CARTA, CELULAR, CHOQUE, CLOSE, CREW, FLAT, HOME, NEST, PIT, PRACA, R, REPITA, WATER, local, radius

OB = bpy.data.objects
world = fresh("mundo")
rng = random.Random(11)


def mix_rgb(t, fac, a, b):
    n = t.nodes.new("ShaderNodeMix")
    n.data_type = "RGBA"
    if isinstance(fac, (int, float)):
        n.inputs[0].default_value = fac
    else:
        t.links.new(fac, n.inputs[0])
    for sock, v in (("A", a), ("B", b)):
        if isinstance(v, str):
            n.inputs[sock].default_value = (*srgb(v), 1)
        else:
            t.links.new(v, n.inputs[sock])
    return n.outputs["Result"]


def ground_material():
    m = bpy.data.materials.get("chao") or bpy.data.materials.new("chao")
    m.use_nodes = True
    t = m.node_tree
    t.nodes.clear()
    out = t.nodes.new("ShaderNodeOutputMaterial")
    b = t.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Specular IOR Level"].default_value = 0.25
    tc = t.nodes.new("ShaderNodeTexCoord")
    sep = t.nodes.new("ShaderNodeSeparateXYZ")
    t.links.new(tc.outputs["Object"], sep.inputs[0])
    aero = t.nodes.new("ShaderNodeValue")
    aero.name = "aero"
    # Patches of two greens, in big soft cells like mown grass
    vor = t.nodes.new("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = 0.85
    noise = t.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 0.6
    noise.inputs["Detail"].default_value = 3
    t.links.new(tc.outputs["Object"], vor.inputs["Vector"])
    t.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    cells = t.nodes.new("ShaderNodeMath")
    cells.operation = "GREATER_THAN"
    cells.inputs[1].default_value = 0.5
    t.links.new(vor.outputs["Color"], cells.inputs[0])
    cozy = mix_rgb(t, cells.outputs[0], "7fcf6a", "8fd978")
    vivid = mix_rgb(t, cells.outputs[0], "3cd42c", "52e23a")
    grass = mix_rgb(t, aero.outputs[0], cozy, vivid)
    # Path down the middle, wobbling, soft edged
    wob = t.nodes.new("ShaderNodeMath")
    wob.operation = "MULTIPLY_ADD"
    t.links.new(noise.outputs[0], wob.inputs[0])
    wob.inputs[1].default_value = 2.4
    wob.inputs[2].default_value = -1.2
    plus = t.nodes.new("ShaderNodeMath")
    plus.operation = "ADD"
    t.links.new(sep.outputs["X"], plus.inputs[0])
    t.links.new(wob.outputs[0], plus.inputs[1])
    ab = t.nodes.new("ShaderNodeMath")
    ab.operation = "ABSOLUTE"
    t.links.new(plus.outputs[0], ab.inputs[0])
    edge = t.nodes.new("ShaderNodeMapRange")
    edge.inputs["From Min"].default_value = 0.72
    edge.inputs["From Max"].default_value = 0.92
    edge.interpolation_type = "SMOOTHSTEP"
    t.links.new(ab.outputs[0], edge.inputs["Value"])
    path_col = mix_rgb(t, aero.outputs[0], "e4cf9b", vivid)
    with_path = mix_rgb(t, edge.outputs[0], path_col, grass)
    # Sand from the edge of the grass outward, with a wobbly border
    absx = t.nodes.new("ShaderNodeMath")
    absx.operation = "ABSOLUTE"
    t.links.new(sep.outputs["X"], absx.inputs[0])
    plus2 = t.nodes.new("ShaderNodeMath")
    plus2.operation = "ADD"
    t.links.new(absx.outputs[0], plus2.inputs[0])
    t.links.new(wob.outputs[0], plus2.inputs[1])
    band = t.nodes.new("ShaderNodeMapRange")
    band.inputs["From Min"].default_value = FLAT - 0.2
    band.inputs["From Max"].default_value = FLAT + 0.3
    band.interpolation_type = "SMOOTHSTEP"
    t.links.new(plus2.outputs[0], band.inputs["Value"])
    surface = mix_rgb(t, band.outputs[0], with_path, "f7e6b5")
    t.links.new(surface, b.inputs["Base Color"])
    rough = t.nodes.new("ShaderNodeMapRange")
    rough.inputs["To Min"].default_value = 0.85
    rough.inputs["To Max"].default_value = 0.42
    t.links.new(aero.outputs[0], rough.inputs["Value"])
    t.links.new(rough.outputs[0], b.inputs["Roughness"])
    t.links.new(b.outputs[0], out.inputs[0])
    return m


def water_material():
    m = bpy.data.materials.get("agua") or bpy.data.materials.new("agua")
    m.use_nodes = True
    t = m.node_tree
    t.nodes.clear()
    out = t.nodes.new("ShaderNodeOutputMaterial")
    b = t.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Specular IOR Level"].default_value = 0.8
    aero = t.nodes.new("ShaderNodeValue")
    aero.name = "aero"
    wave = t.nodes.new("ShaderNodeValue")
    wave.name = "onda"
    tc = t.nodes.new("ShaderNodeTexCoord")
    noise = t.nodes.new("ShaderNodeTexNoise")
    noise.noise_dimensions = "4D"
    noise.inputs["Scale"].default_value = 1.1
    noise.inputs["Detail"].default_value = 3
    t.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    t.links.new(wave.outputs[0], noise.inputs["W"])
    bump = t.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.35
    bump.inputs["Distance"].default_value = 0.2
    t.links.new(noise.outputs[0], bump.inputs["Height"])
    t.links.new(bump.outputs[0], b.inputs["Normal"])
    ramp = t.nodes.new("ShaderNodeMapRange")
    ramp.inputs["From Min"].default_value = 0.4
    ramp.inputs["From Max"].default_value = 0.65
    t.links.new(noise.outputs[0], ramp.inputs["Value"])
    cozy = mix_rgb(t, ramp.outputs[0], "57c7d6", "85dfe2")
    vivid = mix_rgb(t, ramp.outputs[0], "0a90e8", "2fd4f2")
    t.links.new(mix_rgb(t, aero.outputs[0], cozy, vivid), b.inputs["Base Color"])
    rough = t.nodes.new("ShaderNodeMapRange")
    rough.inputs["To Min"].default_value = 0.34
    rough.inputs["To Max"].default_value = 0.05
    t.links.new(aero.outputs[0], rough.inputs["Value"])
    t.links.new(rough.outputs[0], b.inputs["Roughness"])
    b.inputs["Coat Weight"].default_value = 0.8
    b.inputs["Coat Roughness"].default_value = 0.06
    t.links.new(b.outputs[0], out.inputs[0])
    return m


def tube(name, rad_fn, xs, segs, mat, coll):
    """A surface of revolution round the X axis, one radius per x sample."""
    verts, faces = [], []
    for x in xs:
        r = rad_fn(x)
        for k in range(segs):
            t = 2 * math.pi * k / segs
            verts.append((x, -r * math.sin(t), r * math.cos(t)))
    n = len(xs)
    for i in range(n - 1):
        for k in range(segs):
            a, b = i * segs + k, i * segs + (k + 1) % segs
            faces.append((a, a + segs, b + segs, b))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    for p in me.polygons:
        p.use_smooth = True
    me.update()
    me.materials.append(mat)
    ob = OB.new(name, me)
    coll.objects.link(ob)
    return ob


xs = [-24 + 48 * i / 96 for i in range(97)]
log = tube("tronco", radius, xs, 512, ground_material(), world)
log.location = (0, 0, -R)
sea_xs = [-400 + 800 * i / 80 for i in range(81)]
sea = tube("mar", lambda x: R - WATER, sea_xs, 256, water_material(), world)
sea.location = (0, 0, -R)


def on_log(name, x, s, yaw=0.0, k=1.0, lift=0.0, label=None):
    """A prefab standing on the log. yaw turns it about its own up axis, with 0 facing along the walk direction."""
    loc, rot = local(x, s, lift)
    ob = place(name, world, loc, rot, k, log, label)
    ob.rotation_mode = "ZYX"  # yaw about its own up axis first, then the tilt that stands it on the log
    ob.rotation_euler = (rot[0], 0, math.radians(yaw))
    return ob


# ---- Prefabs built here
leaf = gloss("moita", rgb="4fb85a", rough=0.4, coat=0.5)
leaf2 = gloss("moita2", rgb="6fce63", rough=0.4, coat=0.5)
prefabs = bpy.data.collections["prefabs"]
parts = [("ball", (0, 0, 0.42), (0.72, 0.62, 0.52), 0, None), ("ball", (-0.46, 0.05, 0.3), (0.46, 0.46, 0.38), 1, None), ("ball", (0.48, -0.05, 0.28), (0.48, 0.46, 0.36), 1, None),
         ("ball", (0.05, -0.2, 0.68), (0.4, 0.36, 0.3), 1, None)]
blobs("moita_mesh", parts, [leaf, leaf2], prefabs)

stone = gloss("pedra", rgb="d7d2c6", rough=0.55, coat=0.2)
fw = gloss("fonte agua", rgb="6fd6ef", rough=0.08, coat=1.0, spec=0.9)
parts = [("ball", (0, 0, 0.2), (2.0, 2.0, 0.34), 0, None), ("ball", (0, 0, 0.42), (1.72, 1.72, 0.12), 1, None), ("ball", (0, 0, 0.9), (0.3, 0.3, 0.72), 0, None),
         ("ball", (0, 0, 1.55), (0.92, 0.92, 0.17), 0, None), ("ball", (0, 0, 1.68), (0.76, 0.76, 0.06), 1, None), ("ball", (0, 0, 2.2), (0.12, 0.12, 0.62), 1, None),
         ("ball", (0, 0, 2.78), (0.26, 0.26, 0.16), 1, None)]
blobs("fonte_mesh", parts, [stone, fw], prefabs)

# ---- Along the walk. Home first, then trees framing the path.
HOUSE_YAW = -90.0  # the model's door faces +X, this turns it to face the walk
on_log("casa", 0.0, HOME - 5.2, yaw=HOUSE_YAW, label="casa_heroi")
on_log("casa3", -7.5, HOME - 3.5, yaw=20, k=0.9)
on_log("casa2", 8.0, HOME - 1.5, yaw=-25, k=0.8)
for i, (x, s, name, k) in enumerate(((3.6, 1.5, "arvore", 1.0), (-3.2, 3.5, "arvore2", 1.0), (4.2, 6.3, "arvore2", 1.1), (-4.4, 7.5, "arvore", 1.05), (-3.2, 13, "arvore", 1.0),
                                    (4.5, 16.8, "arvore2", 1.0), (-4.2, 20.0, "arvore", 1.0), (4.0, 23.0, "coqueiro", 1.0), (-8.5, 24.5, "arvore", 1.1))):
    on_log(name, x, s, yaw=rng.uniform(0, 360) if name != "arvore" else 0, k=k)
on_log("arvore", 2.9, NEST - 1.2, label="arvore_ninho", k=1.05)
on_log("correio", -1.4, 1.2, yaw=90)
for i in range(6):
    on_log("cerca", -2.2, -1.5 + 1.75 * i, yaw=90)

# Bushes the villagers pop out of
BUSHES = [(-1.55, REPITA - 1.75), (-0.82, REPITA - 2.5), (0.82, REPITA - 2.5), (1.55, REPITA - 1.75)]
for x, s in BUSHES:
    on_log("moita", x, s, k=1.0)
on_log("casa3", -7.5, REPITA - 7, yaw=-20)
on_log("arvore", 7.0, REPITA - 6, k=1.1)

# Town square
on_log("fonte", 0, PRACA - 3.2, k=1.2, label="fonte")
on_log("poste", -5.0, PRACA - 1.0, yaw=0)
on_log("poste", 5.0, PRACA - 1.0, yaw=180)
on_log("banco", -5.6, PRACA - 4.0, yaw=75)
on_log("banco", 5.6, PRACA - 4.0, yaw=-75)
on_log("mesa", 7.2, PRACA + 1.0)
on_log("casa2", -9.5, PRACA - 8.0, yaw=15)
on_log("casa", 9.5, PRACA - 8.0, yaw=-15)
on_log("arvore", 0, PRACA - 11.0, k=1.2)

# Beach stops: palms and shore plants at the sea end
for s, side in ((CLOSE, 1), (CELULAR, 1)):
    for k, (x, ds) in enumerate(((11.2, -5.0), (11.8, 5.5), (9.5, 8.0))):
        on_log("coqueiro", x * side, s - ds, yaw=rng.uniform(0, 360), k=1.1)

for s in (BERG, CREW):
    on_log("arvore", -6.5, s - 4.5, k=1.05)
    on_log("arvore2", 6.5, s - 5.0, k=1.05)
    on_log("casa3", -11, s - 7, yaw=30)
on_log("poste", -3.5, CARTA - 1.5)
on_log("casa2", -9.0, CARTA - 4.0, yaw=20)
on_log("arvore", 5.0, CARTA - 3.0)
on_log("arvore", 8, CHOQUE - 5, k=1.1)
on_log("arvore2", -8, CHOQUE - 6, k=1.1)
for s in (AERO,):
    for x, ds, k in ((-9, 7, 0.9), (9, 8, 1.0)):
        on_log("arvore2", x, s - ds, k=k)

# Flowers scattered over the whole log, clear of the path and of the spots where people stand
rng2 = random.Random(5)
for i in range(240):
    x = rng2.uniform(-FLAT + 0.5, FLAT - 0.5)
    if abs(x) < 1.6:
        continue
    on_log("flor", x, rng2.uniform(-10, 128), yaw=rng2.uniform(0, 360), k=rng2.uniform(0.9, 1.5))
for i in range(36):
    x = rng2.uniform(2.2, 12.0) * rng2.choice((-1, 1))
    s = rng2.uniform(-10, 128)
    if (abs(s - CELULAR) < 6 or abs(s - CLOSE) < 6) and x > 4:
        continue  # the beach scenes need that side clear
    on_log("moita", x, s, yaw=rng2.uniform(0, 360), k=rng2.uniform(0.5, 1.0))

# Water plants off the shore, sitting on the sea rather than the log
sea_plants = fresh("plantas_mar")
for i in range(26):
    x = rng2.uniform(BEACH + 1, BEACH + 22)
    y = rng2.uniform(-12, 12)
    ob = place(rng2.choice(("lirio", "lotus")), sea_plants, (x, y, -WATER - y * y / (2 * R) + 0.02), (0, 0, rng2.uniform(0, 6)), rng2.uniform(0.9, 1.5))

# Clouds, soft and white, in a ring far out. They don't turn with the log.
cloud = gloss("nuvem", rgb="ffffff", rough=0.75, coat=0, emit=0.28)
sky = fresh("ceu_props")
rng3 = random.Random(3)
parts = []
for k in range(7):
    parts.append(("ball", (rng3.uniform(-5, 5), rng3.uniform(-2, 2), rng3.uniform(0, 1.6)), (rng3.uniform(2.2, 3.6), rng3.uniform(2.0, 3.0), rng3.uniform(1.3, 2.2)), 0, None))
blobs("nuvem_mesh", parts, [cloud], prefabs)
for i in range(24):
    a = 2 * math.pi * i / 24 + rng3.uniform(-0.1, 0.1)
    d = rng3.uniform(70, 130)
    place("nuvem", sky, (d * math.cos(a), d * math.sin(a), rng3.uniform(10, 44)), (0, 0, rng3.uniform(0, 6)), rng3.uniform(1.0, 2.4), label=f"nuvem.{i}")

# Floating island and a balloon wait in the sky and show up when the Aero comes in
place("ilha", sky, (-34, 66, -80), (0, 0, 0.5), 2.2, label="ilha_aero")
place("balao", sky, (30, 58, -80), (0, 0, 0.2), 1.0, label="balao_aero")
set_lib.save()
print("world ok", len(world.objects), "objects")
