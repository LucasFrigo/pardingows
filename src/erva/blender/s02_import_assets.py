# Step 4a: imports the Sketchfab models into a "library" collection (excluded from the view layer: sets use instances of
# it), one "AS_<name>" collection each, scaled to a real-world size with the base at the origin. Materials become the
# cartoon look: a texture keeps its light and dark, posterised to four greys (a painted background), a plain colour
# becomes a flat cel tone; leaves keep their cut-out alpha. Solid models get the ink outline, alpha-cut ones don't.
# Resumable: models already in the library are skipped, and it stops after a time budget so bl.mjs doesn't time out.
#   node src/thps/bl.mjs run src/erva/blender/s02_import_assets.py
import importlib
import json
import os
import sys
import time

import bpy
from mathutils import Vector

try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    HERE = os.path.join(os.environ.get("ERVA_ROOT", r"E:\Projetos\pardingows"), "src", "erva", "blender")
sys.path.insert(0, HERE)
import set_lib, hose  # noqa: E402
for mod in (set_lib, hose):
    importlib.reload(mod)
from set_lib import ASSETS, WORK, cel, lum, redraw, save  # noqa: E402

BUDGET_S = 400
TEX_CAP = 1024
# Real-world size per model: (axis, metres) for its bounding box (axis 2 is height). Cartoon props run a little big.
SIZE = {
    "cadeira_balanco": (2, 1.05), "poltrona": (2, 1.15), "relogio": (2, 2.1), "gramofone": (2, 0.75), "radio": (2, 0.6),
    "livro": (0, 0.42), "livro_aberto": (0, 0.6), "cachimbo": (0, 0.55),
    "palmeira": (2, 4.6), "bananeira": (2, 3.0), "costela_adao": (2, 1.2), "orelha_elefante": (2, 1.0), "arbusto": (2, 0.9),
    "arvores_pack": (2, 4.0), "arvores_toon": (2, 3.6), "arvore": (2, 3.8), "macieira": (2, 3.6), "tronco_caido": (0, 2.6),
    "toco": (2, 0.6), "cogumelos": (2, 0.7), "pedras": (0, 4.0), "flor": (2, 0.75), "margarida": (2, 0.6), "flores": (0, 1.8),
    "nuvem": (0, 2.6), "arvore_assombrada": (2, 3.8), "arvore_morta": (2, 3.6), "arvore_retorcida": (2, 3.2),
    "esqueletos": (2, 1.1), "cigarro": (0, 0.14), "baseados": (0, 0.16), "pe_erva": (2, 0.7),
    "caixa_registradora": (2, 0.5), "placa": (2, 1.7), "pote": (2, 0.3), "microfone": (2, 0.4),
}
SKIP = {"chapeu_coco", "perolas"}  # the cobra's bowler and Eva's pearls are built in code
TONE_STEPS = [0.12, 0.38, 0.62, 0.86]

sc = bpy.context.scene
lib = bpy.data.collections.get("library")
if not lib:
    lib = bpy.data.collections.new("library")
    sc.collection.children.link(lib)
REPORT = os.path.join(WORK, "review", "02-import.json")
report = json.load(open(REPORT, encoding="utf8")) if os.path.exists(REPORT) else {}


def cap_image(img):
    if img and max(img.size) > TEX_CAP:
        k = TEX_CAP / max(img.size)
        img.scale(max(1, int(img.size[0] * k)), max(1, int(img.size[1] * k)))


def toon(m, tag):
    """Rebuilds an imported material as the cartoon look; returns True if it is alpha-cut (no ink outline then)."""
    if not m or not m.use_nodes:
        return False
    t = m.node_tree
    bsdf = next((n for n in t.nodes if n.type == "BSDF_PRINCIPLED"), None)
    tex = alpha_tex = None
    base = (0.6, 0.6, 0.6)
    if bsdf:
        bc = bsdf.inputs["Base Color"]
        base = tuple(bc.default_value[:3])
        if bc.links:
            n = bc.links[0].from_node
            while n.type not in ("TEX_IMAGE",) and n.inputs and any(i.links for i in n.inputs):
                n = next(i.links[0].from_node for i in n.inputs if i.links)
            tex = n if n.type == "TEX_IMAGE" else None
        al = bsdf.inputs["Alpha"]
        if al.links and al.links[0].from_node.type == "TEX_IMAGE":
            alpha_tex = al.links[0].from_node
    img = tex.image if tex else None
    a_img = alpha_tex.image if alpha_tex else None
    for im in (img, a_img):
        cap_image(im)
    t.nodes.clear()
    out = t.nodes.new("ShaderNodeOutputMaterial")
    em = t.nodes.new("ShaderNodeEmission")
    # light: two cel steps (shadow side 0.62 of the lit side)
    dif = t.nodes.new("ShaderNodeBsdfDiffuse")
    s2r = t.nodes.new("ShaderNodeShaderToRGB")
    light = t.nodes.new("ShaderNodeValToRGB")
    light.color_ramp.interpolation = "CONSTANT"
    light.color_ramp.elements[0].color = (0.62, 0.62, 0.62, 1)
    light.color_ramp.elements[1].position = 0.18
    t.links.new(dif.outputs[0], s2r.inputs[0])
    t.links.new(s2r.outputs[0], light.inputs[0])
    mul = t.nodes.new("ShaderNodeMix")
    mul.data_type = "RGBA"
    mul.blend_type = "MULTIPLY"
    mul.inputs["Factor"].default_value = 1.0
    t.links.new(light.outputs[0], mul.inputs["B"])
    if img:
        ti = t.nodes.new("ShaderNodeTexImage")
        ti.image = img
        bw = t.nodes.new("ShaderNodeRGBToBW")
        post = t.nodes.new("ShaderNodeValToRGB")  # the texture's luminance posterised to four painted greys
        post.color_ramp.interpolation = "CONSTANT"
        els = post.color_ramp.elements
        els[0].position, els[0].color = 0.0, (TONE_STEPS[0],) * 3 + (1,)
        els[1].position, els[1].color = 0.16, (TONE_STEPS[1],) * 3 + (1,)
        for pos, tone in ((0.32, TONE_STEPS[2]), (0.55, TONE_STEPS[3])):
            e = els.new(pos)
            e.color = (tone,) * 3 + (1,)
        t.links.new(ti.outputs["Color"], bw.inputs[0])
        t.links.new(bw.outputs[0], post.inputs[0])
        t.links.new(post.outputs[0], mul.inputs["A"])
    else:
        l = lum(base) ** (1 / 2.2)  # display brightness of the flat colour
        tone = min(TONE_STEPS, key=lambda v: abs(v - l))
        mul.inputs["A"].default_value = (tone, tone, tone, 1)
    t.links.new(mul.outputs["Result"], em.inputs["Color"])
    cut = False
    if img or a_img:
        src = a_img or img
        if a_img or (src and src.depth == 32 and m.blend_method != "OPAQUE"):
            ta = t.nodes.new("ShaderNodeTexImage")
            ta.image = src
            gt = t.nodes.new("ShaderNodeMath")
            gt.operation = "GREATER_THAN"
            gt.inputs[1].default_value = 0.5
            tr = t.nodes.new("ShaderNodeBsdfTransparent")
            mix = t.nodes.new("ShaderNodeMixShader")
            t.links.new(ta.outputs["Alpha"], gt.inputs[0])
            t.links.new(gt.outputs[0], mix.inputs[0])
            t.links.new(tr.outputs[0], mix.inputs[1])
            t.links.new(em.outputs[0], mix.inputs[2])
            t.links.new(mix.outputs[0], out.inputs[0])
            cut = True
    if not cut:
        t.links.new(em.outputs[0], out.inputs[0])
    m.surface_render_method = "DITHERED"
    m["toon"] = tag
    return cut


def bbox(objs):
    mins, maxs = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for ob in objs:
        if ob.type != "MESH":
            continue
        for c in ob.bound_box:
            p = ob.matrix_world @ Vector(c)
            mins = Vector(map(min, mins, p))
            maxs = Vector(map(max, maxs, p))
    return mins, maxs


t0 = time.time()
left = []
names = sorted(n for n in os.listdir(ASSETS) if os.path.isdir(os.path.join(ASSETS, n)) and n not in SKIP)
for name in names:
    if bpy.data.collections.get("AS_" + name):
        continue
    if time.time() - t0 > BUDGET_S:
        left.append(name)
        continue
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(ASSETS, name, "gltf", "scene.gltf"))
    new = [o for o in bpy.data.objects if o not in before]
    coll = bpy.data.collections.new("AS_" + name)
    lib.children.link(coll)
    for o in new:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        coll.objects.link(o)
    root = bpy.data.objects.new(name + "_root", None)
    coll.objects.link(root)
    for o in new:
        if o.parent is None:
            o.parent = root
    bpy.context.view_layer.update()
    mins, maxs = bbox(new)
    axis, metres = SIZE.get(name, (2, 1.0))
    k = metres / max((maxs - mins)[axis], 1e-6)
    root.scale = (k, k, k)
    bpy.context.view_layer.update()
    mins, maxs = bbox(new)
    root.location = (-(mins.x + maxs.x) / 2, -(mins.y + maxs.y) / 2, -mins.z)
    bpy.context.view_layer.update()
    mins, maxs = bbox(new)
    cut_any, done = False, set()
    for o in new:
        if o.type != "MESH":
            continue
        cut = False
        for m in o.data.materials:
            if m and m.name not in done:
                done.add(m.name)
                m["cut"] = toon(m, name)
            cut = cut or bool(m and m.get("cut"))
        cut_any = cut_any or cut
        if not cut:
            hose.outline(o, 0.012)
        o["asset"] = name
    report[name] = {"objects": len(new), "meshes": sum(o.type == "MESH" for o in new),
                    "verts": sum(len(o.data.vertices) for o in new if o.type == "MESH"),
                    "size": [round(v, 2) for v in (maxs - mins)], "alpha_cut": cut_any,
                    "parts": [o.name for o in new if o.type == "MESH" and o.parent == root][:12]}
    print(name, report[name]["size"], "meshes", report[name]["meshes"], "alpha" if cut_any else "", flush=True)
    redraw()

# The library itself never renders: sets place instances of its collections
lc = bpy.context.view_layer.layer_collection.children.get("library")
if lc:
    lc.exclude = True
os.makedirs(os.path.dirname(REPORT), exist_ok=True)
json.dump(report, open(REPORT, "w", encoding="utf8"), indent=1)
save()
print("left:", left)
