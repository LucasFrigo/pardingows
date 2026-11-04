# Step 6: render settings, night sky, moonlight and the distance fade, for both scenes.
# Run again after adding materials. Safe to re-run: the fade is removed before being added again.
import bpy, math, sys, importlib
sys.path.insert(0, r"C:\Users\lukeg\Projetos\pardingows\src\thps\blender")
sys.path.insert(0, r"C:\Users\lukeg\Projetos\pardingows\src\missao\blender")
import lib, set_lib; importlib.reload(lib); importlib.reload(set_lib)
from lib import srgb

FOG_NEAR, FOG_FAR = 26.0, 92.0
FOG = "0a0d20"  # the far end of the street melts into a dark blue night
OB = bpy.data.objects


def world(name):
    w = bpy.data.worlds.get(name) or bpy.data.worlds.new(name)
    w.use_nodes = True
    n = w.node_tree.nodes
    n.clear()
    out = n.new("ShaderNodeOutputWorld")
    amb = n.new("ShaderNodeBackground")
    amb.inputs[0].default_value = (0.34, 0.40, 0.72, 1)
    amb.inputs[1].default_value = 0.34
    sky = n.new("ShaderNodeBackground")
    sky.inputs[0].default_value = (*srgb(FOG), 1)
    sky.inputs[1].default_value = 1.0
    lp = n.new("ShaderNodeLightPath")
    mix = n.new("ShaderNodeMixShader")
    t = w.node_tree
    t.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
    t.links.new(amb.outputs[0], mix.inputs[1])
    t.links.new(sky.outputs[0], mix.inputs[2])
    t.links.new(mix.outputs[0], out.inputs[0])
    return w


for sc, tag in ((bpy.data.scenes["RUN"], "run"), (bpy.data.scenes["STORY"], "story")):
    r = sc.render
    r.engine = "BLENDER_EEVEE"
    r.resolution_x, r.resolution_y = 270, 240
    r.resolution_percentage = 100
    r.fps = 30
    r.filter_size = 0.01
    r.film_transparent = False
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGB"
    sc.eevee.taa_render_samples = 1
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.world = world("noite " + tag)
    # Moonlight is the hard key. The run also gets a light from behind the runner, since the chase camera only ever sees his back.
    lights = [("lua_" + tag, 1.5, (52, 6, 148), "9fb4ff")]
    if tag == "run":
        lights.append(("costas_run", 1.5, (-68, 0, 0), "ffe2c0"))
    for name, energy, rot, col in lights:
        ob = OB.get(name)
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
set_lib.save()
print("look ok; fade on", count, "materials")
