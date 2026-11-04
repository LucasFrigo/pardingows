# Step 1: Save As the working copy, then repaint the smurf pardo.
# The source .blend and textures are never written to.
#   node src/thps/bl.mjs run src/thps/blender/s01_setup_repaint.py
import bpy, os
import numpy as np

ROOT = r"C:\Users\lukeg\Projetos\pardingows"
WORK = os.path.join(ROOT, "blender", "solucao")
SRC_TEX = os.path.join(ROOT, "smurf-low-poly", "source",
                       "smurf_low_poly_model__download__by_grishamanimation1_dhzbe7v",
                       "smurf_low_poly", "textures")
OUT_TEX = os.path.join(WORK, "textures")
for d in ("textures", "assets", "frames"):
    os.makedirs(os.path.join(WORK, d), exist_ok=True)

BLEND = os.path.join(WORK, "solucao.blend")
if os.path.normcase(bpy.data.filepath) != os.path.normcase(BLEND):
    bpy.ops.wm.save_as_mainfile(filepath=BLEND, relative_remap=True)

SKIN = np.array([0xa0, 0x62, 0x3a]) / 255  # C.skin in src/surupardo/art.mjs

def repaint(rgba):
    """Swap the model's blue for SKIN, keeping white/black and anti-aliased edges."""
    rgb = rgba[..., :3]
    blueness = rgb[..., 2] - rgb[..., 0]
    solid = blueness > 0.5
    if not solid.any():
        return rgba.copy(), 0
    ref = np.median(rgb[solid], axis=0)
    t = np.clip(blueness / (ref[2] - ref[0]), 0, 1)[..., None]
    out = rgba.copy()
    out[..., :3] = np.clip(rgb + t * (SKIN - ref), 0, 1)
    return out, int(solid.sum())

done = {}
for mat in bpy.data.materials:
    if not mat.use_nodes:
        continue
    for node in mat.node_tree.nodes:
        if node.type != "TEX_IMAGE" or not node.image:
            continue
        base = os.path.basename(node.image.filepath.replace("\\", "/"))
        if base not in done:
            src = bpy.data.images.load(os.path.join(SRC_TEX, base), check_existing=False)
            w, h = src.size
            px = np.empty(w * h * 4, np.float32)
            src.pixels.foreach_get(px)
            out, solid = repaint(px.reshape(h, w, 4))
            bpy.data.images.remove(src)
            img = bpy.data.images.new("pardo " + base, w, h, alpha=True)
            img.pixels.foreach_set(out.ravel())
            img.filepath_raw = os.path.join(OUT_TEX, "pardo " + base)
            img.file_format = "PNG"
            img.save()
            done[base] = img
            left = int(((out[..., 2] - out[..., 0]) > 0.08).sum())
            print(f"{base}: {w}x{h}, {solid} blue px repainted, {left} still blue")
        node.image = done[base]
        node.interpolation = "Closest"

bpy.ops.wm.save_mainfile()
head = bpy.data.objects["head"]
from mathutils import Vector
pts = [head.matrix_world @ Vector(c) for c in head.bound_box]
print("head bbox", [round(min(p[i] for p in pts), 2) for i in range(3)], [round(max(p[i] for p in pts), 2) for i in range(3)])
body = bpy.data.objects["body"]
pts = [body.matrix_world @ Vector(c) for c in body.bound_box]
print("body bbox", [round(min(p[i] for p in pts), 2) for i in range(3)], [round(max(p[i] for p in pts), 2) for i in range(3)])
print("saved", bpy.data.filepath)
