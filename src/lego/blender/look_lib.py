# Render engine, sky and which world is on: shared by the stills and the frame renderer.
import bpy
from set_lib import RENDER_H, RENDER_W, srgb
from world_data import SETS, SKY

CYCLES_SAMPLES = 48
EEVEE_SAMPLES = 48


def engine(name, samples=None, res=1.0):
    sc = bpy.context.scene
    r = sc.render
    r.engine = "CYCLES" if name == "CYCLES" else "BLENDER_EEVEE"
    r.resolution_x, r.resolution_y, r.resolution_percentage = RENDER_W, RENDER_H, int(res * 100)
    r.fps = 30
    r.film_transparent = False
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGB"
    r.use_persistent_data = True
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    if name == "CYCLES":
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = d.type == "OPTIX"
        cy = sc.cycles
        cy.device = "GPU"
        cy.samples = samples or CYCLES_SAMPLES
        cy.use_adaptive_sampling = True
        cy.adaptive_threshold = 0.03
        cy.use_denoising = True
        cy.denoiser = "OPTIX"
        cy.max_bounces = 5
        cy.diffuse_bounces = 2
        cy.glossy_bounces = 2
        cy.transmission_bounces = 2
        cy.volume_bounces = 0
        cy.caustics_reflective = False
        cy.caustics_refractive = False
        cy.use_light_tree = True
        return [d.name for d in prefs.devices if d.use]
    ev = sc.eevee
    ev.taa_render_samples = samples or EEVEE_SAMPLES
    ev.use_shadows = True
    ev.shadow_ray_count = 2
    ev.shadow_step_count = 6
    ev.use_raytracing = True
    return []


def world(name):
    """Sets the one shared sky to this world's colours."""
    sc = bpy.context.scene
    w = bpy.data.worlds.get("ceu") or bpy.data.worlds.new("ceu")
    w.use_nodes = True
    t = w.node_tree
    if "ramp" not in t.nodes:
        t.nodes.clear()
        out = t.nodes.new("ShaderNodeOutputWorld")
        bg = t.nodes.new("ShaderNodeBackground")
        bg.name = "bg"
        tc = t.nodes.new("ShaderNodeTexCoord")
        nrm = t.nodes.new("ShaderNodeVectorMath")
        nrm.operation = "NORMALIZE"
        sep = t.nodes.new("ShaderNodeSeparateXYZ")
        rp = t.nodes.new("ShaderNodeValToRGB")
        rp.name = "ramp"
        rp.color_ramp.interpolation = "EASE"
        t.links.new(tc.outputs["Generated"], nrm.inputs[0])
        t.links.new(nrm.outputs[0], sep.inputs[0])
        t.links.new(sep.outputs["Z"], rp.inputs[0])
        t.links.new(rp.outputs[0], bg.inputs[0])
        t.links.new(bg.outputs[0], out.inputs[0])
    a, b, s = SKY[name]
    e = t.nodes["ramp"].color_ramp.elements
    e[0].position, e[1].position = 0.0, 0.55
    e[0].color = (*srgb(a), 1)
    e[1].color = (*srgb(b), 1)
    t.nodes["bg"].inputs[1].default_value = s
    sc.world = w


def activate(name):
    """Only this world's collection renders. Everything else stays out of the BVH."""
    for n in SETS:
        c = bpy.data.collections.get("set_" + n)
        if c:
            c.hide_render = n != name
    world(name)
