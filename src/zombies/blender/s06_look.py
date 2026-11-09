# Step 6: render settings, a dim bluish ambient and the distance fade. Run again after adding materials: the fade is removed before being added again.
import bpy, importlib, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "thps", "blender"))
sys.path.insert(0, HERE)
import lib, set_lib
importlib.reload(lib); importlib.reload(set_lib)
from lib import srgb

FOG_NEAR, FOG_FAR = 16.0, 62.0
FOG = "0a0a12"  # far things melt into a dark night
sc = bpy.context.scene
r = sc.render
r.engine = "BLENDER_EEVEE"
r.resolution_x, r.resolution_y = set_lib.RENDER_W, set_lib.RENDER_H
r.resolution_percentage = 100
r.fps = 30
r.filter_size = 0.01  # no anti-aliasing: hard pixels
r.film_transparent = False
r.image_settings.file_format = "PNG"
r.image_settings.color_mode = "RGB"
sc.eevee.taa_render_samples = 4
sc.view_settings.view_transform = "Standard"
sc.view_settings.look = "None"

w = bpy.data.worlds.get("noite") or bpy.data.worlds.new("noite")
w.use_nodes = True
n = w.node_tree.nodes
n.clear()
out = n.new("ShaderNodeOutputWorld")
amb = n.new("ShaderNodeBackground")
amb.inputs[0].default_value = (0.30, 0.36, 0.5, 1)
amb.inputs[1].default_value = 0.3
sky = n.new("ShaderNodeBackground")
sky.inputs[0].default_value = (*srgb(FOG), 1)
sky.inputs[1].default_value = 1.0
lp = n.new("ShaderNodeLightPath")
mix = n.new("ShaderNodeMixShader")
w.node_tree.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
w.node_tree.links.new(amb.outputs[0], mix.inputs[1])
w.node_tree.links.new(sky.outputs[0], mix.inputs[2])
w.node_tree.links.new(mix.outputs[0], out.inputs[0])
sc.world = w


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
set_lib.save()
print("=== LOOK DONE; fade on", count, "materials", flush=True)
