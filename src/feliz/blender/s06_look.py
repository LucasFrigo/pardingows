# Step 6: render settings, sky and lights. The sky mixes from a cozy pale morning to deep Aero blue with one keyed value, named "aero", 0 to 1.
import bpy, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib, set_lib; importlib.reload(set_lib)
from set_lib import RENDER_H, RENDER_W, srgb

sc = bpy.context.scene
r = sc.render
r.engine = "BLENDER_EEVEE"
r.resolution_x, r.resolution_y, r.resolution_percentage = RENDER_W, RENDER_H, 100
r.fps = 30
r.filter_size = 1.2
r.film_transparent = False
r.image_settings.file_format = "PNG"
r.image_settings.color_mode = "RGB"
sc.eevee.taa_render_samples = 24
sc.eevee.use_shadows = True
sc.eevee.shadow_ray_count = 1
sc.eevee.shadow_step_count = 4
sc.eevee.use_raytracing = False
sc.view_settings.view_transform = "Standard"
sc.view_settings.look = "None"
sc.view_settings.exposure = 0.0
sc.view_settings.gamma = 1.0

w = bpy.data.worlds.get("ceu") or bpy.data.worlds.new("ceu")
w.use_nodes = True
t = w.node_tree
t.nodes.clear()
out = t.nodes.new("ShaderNodeOutputWorld")
bg = t.nodes.new("ShaderNodeBackground")
bg.inputs[1].default_value = 1.0
tc = t.nodes.new("ShaderNodeTexCoord")
nrm = t.nodes.new("ShaderNodeVectorMath")
nrm.operation = "NORMALIZE"
sep = t.nodes.new("ShaderNodeSeparateXYZ")
t.links.new(tc.outputs["Generated"], nrm.inputs[0])
t.links.new(nrm.outputs[0], sep.inputs[0])


def ramp(stops):
    n = t.nodes.new("ShaderNodeValToRGB")
    cr = n.color_ramp
    cr.interpolation = "EASE"
    while len(cr.elements) < len(stops):
        cr.elements.new(0.5)
    for e, (pos, col) in zip(cr.elements, stops):
        e.position = pos
        e.color = (*srgb(col), 1)
    t.links.new(sep.outputs["Z"], n.inputs[0])
    return n


cozy = ramp([(0.0, "ffe9c9"), (0.12, "ffe6c4"), (0.45, "a9e0f2"), (1.0, "6cc4ec")])
aero = ramp([(0.0, "c9f4ff"), (0.10, "8fe2ff"), (0.42, "1d7cf0"), (1.0, "0636b8")])
mix = t.nodes.new("ShaderNodeMix")
mix.data_type = "RGBA"
mix.blend_type = "MIX"
val = t.nodes.new("ShaderNodeValue")
val.name = "aero"
val.outputs[0].default_value = 0.0
t.links.new(val.outputs[0], mix.inputs[0])
t.links.new(cozy.outputs[0], mix.inputs["A"])
t.links.new(aero.outputs[0], mix.inputs["B"])
t.links.new(mix.outputs["Result"], bg.inputs[0])
t.links.new(bg.outputs[0], out.inputs[0])
sc.world = w

for name, energy, rot, col, angle, shadow in (("sol", 3.2, (52, 6, 38), "fff1d8", 12, True), ("recorte", 1.1, (70, 0, 200), "dff2ff", 30, False)):
    ob = bpy.data.objects.get(name)
    if not ob:
        ob = bpy.data.objects.new(name, bpy.data.lights.new(name, "SUN"))
        sc.collection.objects.link(ob)
    ob.data.energy = energy
    ob.data.color = srgb(col)
    ob.data.angle = math.radians(angle)
    ob.data.use_shadow = shadow
    ob.rotation_euler = [math.radians(a) for a in rot]
set_lib.save()
print("look ok")
