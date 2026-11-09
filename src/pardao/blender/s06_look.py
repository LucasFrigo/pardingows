# Step 4b: render look. EEVEE at 540x960 (a PS2 frame was ~512x448: low resolution is part of the look; ps2.mjs upscales x2 and
# adds bloom, dither and interlace). Night sky world with stars and a faint violet horizon, thin volumetric haze so the street
# lights get halos, Standard view transform so emissive windows clip to white and feed the bloom.
#   node src/thps/bl.mjs run src/pardao/blender/s06_look.py
import bpy, os, sys
try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    HERE = os.path.join(os.environ.get("PARDAO_ROOT", r"E:\Projetos\pardingows"), "src", "pardao", "blender")
sys.path.insert(0, HERE)
import importlib, set_lib
importlib.reload(set_lib)
from set_lib import RENDER_W, RENDER_H

sc = bpy.context.scene
r = sc.render
r.engine = "BLENDER_EEVEE"
r.resolution_x, r.resolution_y, r.resolution_percentage = RENDER_W, RENDER_H, 100
r.fps = 30
r.film_transparent = False
r.image_settings.file_format = "PNG"
r.image_settings.color_mode = "RGB"
ee = sc.eevee
ee.taa_render_samples = 24
for attr, val in (("use_shadows", True), ("shadow_ray_count", 1), ("shadow_step_count", 4), ("use_volumetric_shadows", False),
                  ("volumetric_tile_size", "8"), ("volumetric_samples", 32), ("volumetric_start", 0.5), ("volumetric_end", 120.0),
                  ("use_raytracing", False), ("fast_gi_method", "GLOBAL_ILLUMINATION")):
    if hasattr(ee, attr):
        setattr(ee, attr, val)
vs = sc.view_settings
vs.view_transform = "Standard"
vs.look = "None"
vs.exposure = 0.0
vs.gamma = 1.0
sc.display_settings.display_device = "sRGB"

# World: gradient night sky with stars, plus a thin haze volume
w = bpy.data.worlds.get("noite") or bpy.data.worlds.new("noite")
w.use_nodes = True
nt = w.node_tree
nt.nodes.clear()
out = nt.nodes.new("ShaderNodeOutputWorld")
bg = nt.nodes.new("ShaderNodeBackground")
coord = nt.nodes.new("ShaderNodeTexCoord")
sep = nt.nodes.new("ShaderNodeSeparateXYZ")
nt.links.new(coord.outputs["Generated"], sep.inputs[0])
ramp = nt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].position = 0.45
ramp.color_ramp.elements[0].color = (0.05, 0.025, 0.07, 1)   # violet glow of the city at the horizon
ramp.color_ramp.elements[1].position = 0.75
ramp.color_ramp.elements[1].color = (0.004, 0.006, 0.02, 1)  # deep navy overhead
nt.links.new(sep.outputs["Z"], ramp.inputs[0])
stars = nt.nodes.new("ShaderNodeTexNoise")
stars.inputs["Scale"].default_value = 900.0
star_ramp = nt.nodes.new("ShaderNodeValToRGB")
star_ramp.color_ramp.elements[0].position = 0.74
star_ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
star_ramp.color_ramp.elements[1].position = 0.78
star_ramp.color_ramp.elements[1].color = (0.6, 0.65, 0.8, 1)
nt.links.new(coord.outputs["Generated"], stars.inputs["Vector"])
nt.links.new(stars.outputs["Fac"], star_ramp.inputs[0])
add = nt.nodes.new("ShaderNodeMix")
add.data_type, add.blend_type = "RGBA", "ADD"
add.inputs["Factor"].default_value = 1.0
nt.links.new(ramp.outputs[0], add.inputs[6])
nt.links.new(star_ramp.outputs[0], add.inputs[7])
nt.links.new(add.outputs[2], bg.inputs["Color"])
bg.inputs["Strength"].default_value = 1.0
nt.links.new(bg.outputs[0], out.inputs["Surface"])
vol = nt.nodes.new("ShaderNodeVolumePrincipled")
vol.inputs["Density"].default_value = 0.0035
vol.inputs["Color"].default_value = (0.4, 0.5, 0.95, 1)
vol.inputs["Anisotropy"].default_value = 0.35
nt.links.new(vol.outputs[0], out.inputs["Volume"])
sc.world = w

# The gallery and the cast lineup never render; only the stage and whoever a shot places
for name in ("assets",):
    c = bpy.data.collections.get(name)
    if c:
        c.hide_render = True
set_lib.save()
print("look set:", r.engine, r.resolution_x, "x", r.resolution_y, "samples", ee.taa_render_samples)
