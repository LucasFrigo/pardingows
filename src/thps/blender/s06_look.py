# Step 3c: render settings, lights, sky and the PS1 distance fog on every material.
# Safe to re-run: the fog is removed before being added again.
import bpy, math, sys, importlib
sys.path.insert(0, r"C:\Users\lukeg\Projetos\pardingows\src\thps\blender")
import lib; importlib.reload(lib)
from lib import srgb

FOG_NEAR, FOG_FAR = 28.0, 150.0
FOG = "c9d4d8"  # smoggy Sao Paulo haze, also the sky at the horizon
SKY_TOP = "7fa8c9"

sc = bpy.context.scene
r = sc.render
r.engine = "BLENDER_EEVEE"
r.resolution_x, r.resolution_y = 270, 480
r.resolution_percentage = 100
r.fps = 30
r.filter_size = 0.01
r.film_transparent = False
r.image_settings.file_format = "PNG"
r.image_settings.color_mode = "RGB"
sc.eevee.taa_render_samples = 1
sc.eevee.use_shadows = False if hasattr(sc.eevee, "use_shadows") else False
sc.view_settings.view_transform = "Standard"
sc.view_settings.look = "None"

# World: gradient for camera rays, flat ambient for everything else
w = sc.world
w.use_nodes = True
n = w.node_tree.nodes
n.clear()
out = n.new("ShaderNodeOutputWorld")
amb = n.new("ShaderNodeBackground")
amb.inputs[0].default_value = (0.62, 0.64, 0.7, 1)
amb.inputs[1].default_value = 0.9
sky = n.new("ShaderNodeBackground")
sky.inputs[1].default_value = 1.0
tc = n.new("ShaderNodeTexCoord")
sep = n.new("ShaderNodeSeparateXYZ")
ramp = n.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].position = 0.0
ramp.color_ramp.elements[0].color = (*srgb(FOG), 1)
ramp.color_ramp.elements[1].position = 0.45
ramp.color_ramp.elements[1].color = (*srgb(SKY_TOP), 1)
lp = n.new("ShaderNodeLightPath")
mix = n.new("ShaderNodeMixShader")
t = w.node_tree
t.links.new(tc.outputs["Generated"], sep.inputs[0])
t.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
t.links.new(ramp.outputs[0], sky.inputs[0])
t.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
t.links.new(amb.outputs[0], mix.inputs[1])
t.links.new(sky.outputs[0], mix.inputs[2])
t.links.new(mix.outputs[0], out.inputs[0])

# Lights: one warm unshadowed sun plus a cool fill so nothing goes flat on the far side
for name, energy, rot, col in (("LV_sun", 2.2, (50, 12, -35), "fff1d8"), ("LV_fill", 0.7, (65, 0, 150), "c9d8ff")):
    ob = bpy.data.objects.get(name)
    if not ob:
        ob = bpy.data.objects.new(name, bpy.data.lights.new(name, "SUN"))
        sc.collection.objects.link(ob)
    ob.data.energy = energy
    ob.data.color = srgb(col)
    ob.data.use_shadow = False
    ob.rotation_euler = [math.radians(a) for a in rot]


def add_fog(m):
    tree = m.node_tree
    nodes = tree.nodes
    out = next((nd for nd in nodes if nd.type == "OUTPUT_MATERIAL" and nd.is_active_output), None)
    if not out:
        return False
    old = nodes.get("fog_mix")
    src = old.inputs[1].links[0].from_socket if old and old.inputs[1].links else None
    for node in list(nodes):
        if node.name.startswith("fog_"):
            nodes.remove(node)
    if src is None and out.inputs["Surface"].links:
        src = out.inputs["Surface"].links[0].from_socket
    if src is None:
        # output left dangling: reconnect the shader nothing else consumes
        src = next((nd.outputs[0] for nd in nodes if nd.outputs and nd.outputs[0].type == "SHADER" and not nd.outputs[0].links), None)
    if src is None:
        return False
    cam = nodes.new("ShaderNodeCameraData"); cam.name = "fog_cam"
    rng = nodes.new("ShaderNodeMapRange"); rng.name = "fog_range"
    rng.inputs["From Min"].default_value = FOG_NEAR
    rng.inputs["From Max"].default_value = FOG_FAR
    rng.clamp = True
    glow = nodes.new("ShaderNodeEmission"); glow.name = "fog_col"
    glow.inputs[0].default_value = (*srgb(FOG), 1)
    mix = nodes.new("ShaderNodeMixShader"); mix.name = "fog_mix"
    tree.links.new(cam.outputs["View Distance"], rng.inputs["Value"])
    tree.links.new(rng.outputs[0], mix.inputs[0])
    tree.links.new(src, mix.inputs[1])
    tree.links.new(glow.outputs[0], mix.inputs[2])
    tree.links.new(mix.outputs[0], out.inputs["Surface"])
    return True


count = sum(add_fog(m) for m in bpy.data.materials if m.use_nodes)
bpy.ops.wm.save_mainfile()
print("look ok; fog on", count, "materials")
