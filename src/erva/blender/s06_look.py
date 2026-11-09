# Step 4c: render settings and the look. EEVEE at 1080x1920 with the Standard view transform (the cel tones are exact
# greys; the sepia and film wear are added in Node). A shot camera "CAM". A world whose colour the shots set per frame.
# The soul: its own view layer holding only the "soul" collection (everything else a holdout), laid over the main
# picture at 55% by the compositor, so the see-through soul is one clean shape. Re-runnable.
#   node src/thps/bl.mjs run src/erva/blender/s06_look.py
import importlib
import math
import os
import sys

import bpy

try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    HERE = os.path.join(os.environ.get("ERVA_ROOT", r"E:\Projetos\pardingows"), "src", "erva", "blender")
sys.path.insert(0, HERE)
import set_lib  # noqa: E402
importlib.reload(set_lib)
from set_lib import save  # noqa: E402

SOUL_ALPHA = 0.55
sc = bpy.context.scene
r = sc.render
r.engine = "BLENDER_EEVEE"
r.resolution_x, r.resolution_y, r.resolution_percentage = 1080, 1920, 100
r.fps = 24
r.image_settings.file_format = "PNG"
r.image_settings.color_mode = "RGBA"
r.film_transparent = False
sc.view_settings.view_transform = "Standard"
sc.view_settings.look = "None"
sc.view_settings.exposure = 0.0
sc.view_settings.gamma = 1.0
ee = sc.eevee
ee.taa_render_samples = 16
ee.taa_samples = 8
for attr, val in (("use_shadows", True), ("use_raytracing", False), ("use_bloom", False)):
    if hasattr(ee, attr):
        setattr(ee, attr, val)
r.filter_size = 1.2

# The shot camera: lens set per shot; the frame's height is the sensor's reference for a vertical picture
cam = bpy.data.objects.get("CAM")
if not cam:
    cam = bpy.data.objects.new("CAM", bpy.data.cameras.new("CAM"))
    sc.collection.objects.link(cam)
cam.data.sensor_fit = "VERTICAL"
cam.data.sensor_height = 24.0
cam.data.lens = 35
cam.data.clip_start, cam.data.clip_end = 0.05, 200
sc.camera = cam

# World: a flat colour the shots change (paper sky in the garden, black in the dark and the spooky jungle)
w = sc.world or bpy.data.worlds.new("World")
sc.world = w
w.use_nodes = True
bg = w.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.8, 0.8, 0.8, 1)
bg.inputs[1].default_value = 1.0

# Key light: a sun from front-left so the cel shadow falls on the faces' far side
sun = bpy.data.objects["key_sun"]
sun.data.energy = 3.0
sun.data.angle = math.radians(3)
sun.rotation_euler = (math.radians(52), 0, math.radians(-32))

# The soul's view layer
main = sc.view_layers[0]
main.name = "main"
soul_vl = sc.view_layers.get("soul") or sc.view_layers.new("soul")
for vl, soul_only in ((main, False), (soul_vl, True)):
    for lc in vl.layer_collection.children:
        if lc.name == "library":
            lc.exclude = True
            continue
        if lc.name == "soul":
            lc.exclude = not soul_only
            lc.holdout = False
        else:
            lc.exclude = False
            lc.holdout = soul_only
soul_vl.use = False  # the shots switch it on only while the soul is out

# Compositor: main, then the soul over it at SOUL_ALPHA. Blender 5 keeps the compositor in a node group.
sc.use_nodes = True
tree = getattr(sc, "compositing_node_group", None)
if hasattr(sc, "compositing_node_group"):
    if tree is None:
        tree = bpy.data.node_groups.new("erva comp", "CompositorNodeTree")
        sc.compositing_node_group = tree
else:
    tree = sc.node_tree
tree.nodes.clear()
rl_main = tree.nodes.new("CompositorNodeRLayers")
rl_main.layer = "main"
rl_soul = tree.nodes.new("CompositorNodeRLayers")
rl_soul.layer = "soul"
mul = tree.nodes.new("CompositorNodeMath") if hasattr(bpy.types, "CompositorNodeMath") else None
over = tree.nodes.new("CompositorNodeAlphaOver")
over.inputs[0].default_value = SOUL_ALPHA if over.inputs[0].type == "VALUE" else over.inputs[0].default_value
if mul:
    tree.nodes.remove(mul)
out_node = None
for kind in ("NodeGroupOutput", "CompositorNodeComposite"):
    try:
        out_node = tree.nodes.new(kind)
        break
    except RuntimeError:
        continue
if out_node.bl_idname == "NodeGroupOutput" and not any(s.in_out == "OUTPUT" for s in tree.interface.items_tree):
    tree.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
L = tree.links
# Alpha Over: Fac, Background (main), Foreground (soul)
ins = [i for i in over.inputs]
fac = next(i for i in ins if i.name in ("Fac", "Factor"))
bgin = [i for i in ins if i.type == "RGBA"][0]
fgin = [i for i in ins if i.type == "RGBA"][1]
fac.default_value = SOUL_ALPHA
L.new(rl_main.outputs["Image"], bgin)
L.new(rl_soul.outputs["Image"], fgin)
L.new(over.outputs[0], out_node.inputs[0])
# Distance haze on the sets: one node group shared by every set and library material, so a shot retunes it once
# (shots.haze). Inserted just before each material's Emission colour. The cast's materials are left crisp.
hz = bpy.data.node_groups.get("erva_haze")
if not hz:
    hz = bpy.data.node_groups.new("erva_haze", "ShaderNodeTree")
    hz.interface.new_socket("Color", in_out="INPUT", socket_type="NodeSocketColor")
    hz.interface.new_socket("Color", in_out="OUTPUT", socket_type="NodeSocketColor")
    gi = hz.nodes.new("NodeGroupInput")
    go = hz.nodes.new("NodeGroupOutput")
    camd = hz.nodes.new("ShaderNodeCameraData")
    mr = hz.nodes.new("ShaderNodeMapRange")
    mr.name = "haze_range"
    mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 7.0, 30.0
    amt = hz.nodes.new("ShaderNodeValue")
    amt.name = "haze_amount"
    amt.outputs[0].default_value = 0.55
    col = hz.nodes.new("ShaderNodeRGB")
    col.name = "haze_color"
    col.outputs[0].default_value = (0.65, 0.65, 0.65, 1)
    mulf = hz.nodes.new("ShaderNodeMath")
    mulf.operation = "MULTIPLY"
    mix = hz.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    hz.links.new(camd.outputs["View Z Depth"], mr.inputs["Value"])
    hz.links.new(mr.outputs["Result"], mulf.inputs[0])
    hz.links.new(amt.outputs[0], mulf.inputs[1])
    hz.links.new(mulf.outputs[0], mix.inputs["Factor"])
    hz.links.new(gi.outputs[0], mix.inputs["A"])
    hz.links.new(col.outputs[0], mix.inputs["B"])
    hz.links.new(mix.outputs["Result"], go.inputs[0])
cast_mats = {m for c in ("cast", "soul") for o in bpy.data.collections[c].all_objects
             for m in getattr(o.data, "materials", []) if m}
set_colls = ["library", "set_sala", "set_trevas", "set_selva", "prop_flowers", "set_assombrada", "props", "prop_book", "prop_pipe"]
hazed = 0
for c in set_colls:
    for o in bpy.data.collections[c].all_objects:
        for m in getattr(o.data, "materials", []) or []:
            if not m or m in cast_mats or m.name == "ink" or not m.use_nodes:
                continue
            t = m.node_tree
            if any(n.type == "GROUP" and n.node_tree == hz for n in t.nodes):  # rebuilt materials lose it: check the node
                continue
            em = next((n for n in t.nodes if n.type == "EMISSION"), None)
            if not em or not em.inputs["Color"].links:
                continue
            src = em.inputs["Color"].links[0].from_socket
            gn = t.nodes.new("ShaderNodeGroup")
            gn.node_tree = hz
            t.links.new(src, gn.inputs[0])
            t.links.new(gn.outputs[0], em.inputs["Color"])
            m["hazed"] = 1
            hazed += 1
print("haze added to", hazed, "materials")
print("compositor:", tree.name, [n.bl_idname for n in tree.nodes], "inputs:", [i.name for i in over.inputs])
save()
print("look set")
