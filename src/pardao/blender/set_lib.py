# Helpers shared by the PARDÃO 2000 scene scripts: PS2-style materials, capped textures, flat quads, placing prefabs.
# Scripts run either headless (blender -b -P file) or inside the open window through bl.mjs, which has no __file__:
# then the repo root comes from PARDAO_ROOT or the default below.
import bpy, math, os, time

try:
    ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
except NameError:
    ROOT = os.environ.get("PARDAO_ROOT", r"E:\Projetos\pardingows")
WORK = os.path.join(ROOT, "blender", "pardao")
BLEND = os.path.join(WORK, "pardao.blend")
ASSETS = os.path.join(WORK, "assets")
TEXTURES = os.path.join(WORK, "textures")
REVIEW = os.path.join(WORK, "review")
SOLUCAO = os.path.join(ROOT, "blender", "solucao", "solucao.blend")
RENDER_W, RENDER_H = 540, 960
_small = {}


def save():
    """Saves, waiting out whatever on Windows briefly holds a just-written file while Blender swaps in its .blend1 backup."""
    for attempt in range(6):
        try:
            bpy.ops.wm.save_mainfile()
            return
        except RuntimeError:
            if attempt == 5:
                raise
            time.sleep(2)


def ps2_material(m):
    """PS2 look: bilinear textures, a soft sheen at most, no normal or metal maps (that hardware had none)."""
    if not m or not m.use_nodes:
        return
    t = m.node_tree
    for n in list(t.nodes):
        if n.type == "TEX_IMAGE":
            # Only the maps that shape the light go. A colour map can reach the shader through a Mix node, so it is kept by default.
            to = [(l.to_node.type, l.to_socket.name) for o in n.outputs for l in o.links]
            if to and all(k in ("NORMAL_MAP", "BUMP", "SEPARATE_COLOR", "SEPRGB") or s in ("Normal", "Roughness", "Metallic", "Emission Color", "Emission Strength") for k, s in to):
                t.nodes.remove(n)
                continue
            n.interpolation = "Linear"
        if n.type == "BSDF_PRINCIPLED":
            n.inputs["Roughness"].default_value = 0.8
            n.inputs["Specular IOR Level"].default_value = 0.15
            n.inputs["Metallic"].default_value = 0.0
            for name in ("Normal", "Roughness", "Metallic", "Emission Color", "Emission Strength"):
                for l in list(n.inputs[name].links):
                    t.links.remove(l)
            # With its map unlinked the emission colour falls back to white, so it has to be switched off or the model glows flat white
            n.inputs["Emission Strength"].default_value = 0.0


def shrink(m, size, tag=""):
    """Swaps a material's texture for a small PNG next to the project. A copied image still carries its original
    full-size file inside it, so the copy is thrown away and the PNG is loaded fresh. Shared images shrink once.
    tag is the asset's name: many exports call their map material_0_baseColor, and those must not share a small copy."""
    if not m or not m.use_nodes:
        return
    os.makedirs(TEXTURES, exist_ok=True)
    for n in m.node_tree.nodes:
        if n.type != "TEX_IMAGE" or not n.image or max(n.image.size) <= size:
            continue
        key = (tag, n.image.name, size)
        if key not in _small or _small[key].name not in bpy.data.images:
            w, h = n.image.size
            k = size / max(w, h)
            tmp = n.image.copy()
            tmp.scale(max(int(w * k), 1), max(int(h * k), 1))
            name = f"small {tag} " + n.image.name.replace(":", "_").replace("/", "_")
            path = os.path.join(TEXTURES, name + ".png")
            tmp.filepath_raw = path
            tmp.file_format = "PNG"
            tmp.save()
            bpy.data.images.remove(tmp)
            _small[key] = bpy.data.images.load(path, check_existing=False)
        n.image = _small[key]


def fresh(name, parent=None):
    """An empty collection under the scene (or under parent), cleared if it already exists."""
    c = bpy.data.collections.get(name)
    if c:
        for o in list(c.objects):
            bpy.data.objects.remove(o, do_unlink=True)
    else:
        c = bpy.data.collections.new(name)
    host = parent.children if parent else bpy.context.scene.collection.children
    if c.name not in host:
        host.link(c)
    return c


def parts(asset, kind="MESH"):
    return [o for o in bpy.data.objects if o.get("asset") == asset and o.type == kind]


def quads(name, items, mat, coll):
    """Flat textured quads: each item is four corners plus the UV repeat counts."""
    v, f, uvs = [], [], []
    for corners, (ru, rv) in items:
        i = len(v)
        v += corners
        f.append((i, i + 1, i + 2, i + 3))
        uvs += [(0, 0), (ru, 0), (ru, rv), (0, rv)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(v, [], f)
    layer = me.uv_layers.new(name="UVMap")
    for loop, uv in zip(layer.data, uvs):
        loop.uv = uv
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def place(name, coll, loc, rz=0.0, s=1.0, rx=0.0, ry=0.0):
    """A copy of a flattened prefab, sharing its mesh. s can be one number or three."""
    src = bpy.data.objects["PF_" + name]
    ob = src.copy()
    ob.name = f"{name}.{len(coll.objects)}"
    ob.parent = None
    ob.location = loc
    ob.rotation_euler = (math.radians(rx), math.radians(ry), math.radians(rz))
    ob.scale = (s, s, s) if isinstance(s, (int, float)) else s
    ob.hide_render = False
    coll.objects.link(ob)
    return ob


def redraw():
    """Lets the open window repaint between long steps, so progress shows while a script runs through bl.mjs."""
    if bpy.app.background:
        return
    try:
        bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=1)
    except Exception:
        pass
