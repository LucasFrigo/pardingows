# Helpers shared by the zombies scene scripts: hard-texel PS1 materials, small textures, flat quads, placing prefabs.
import bpy, math, os, time

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
WORK = os.path.join(ROOT, "blender", "zombies")
ASSETS = os.path.join(WORK, "assets")
TEXTURES = os.path.join(WORK, "textures")
FAR = (500, 500, -50)
RENDER_W, RENDER_H = 270, 480
# The four locations sit far apart in one scene, so their lights don't reach each other
CORRIDOR, STREET, HALL, DUNGEON, DOOR, MUGS = (0, 0, 0), (200, 0, 0), (400, 0, 0), (600, 0, 0), (800, 0, 0), (1000, 0, 0)
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


def ps1_material(m):
    """Hard texels, no shine. Normal, gloss and metal maps have no place on a PS1 model, so they go."""
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
            n.interpolation = "Closest"
        if n.type == "BSDF_PRINCIPLED":
            n.inputs["Roughness"].default_value = 1.0
            n.inputs["Specular IOR Level"].default_value = 0.0
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


def fresh(name, *scenes):
    """An empty collection linked to the given scenes."""
    c = bpy.data.collections.get(name)
    if c:
        for o in list(c.objects):
            bpy.data.objects.remove(o, do_unlink=True)
    else:
        c = bpy.data.collections.new(name)
    for sc in scenes:
        if c.name not in sc.collection.children:
            sc.collection.children.link(c)
    return c


def parts(asset, kind="MESH"):
    return [o for o in bpy.data.objects if o.get("asset") == asset and o.type == kind]


def tex_mat(name, file, alpha=False, emit=0.0):
    """Hard-texel material from a texture file in the project's textures folder. Flat and matte, optionally cut out or glowing."""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    n = m.node_tree.nodes
    n.clear()
    out = n.new("ShaderNodeOutputMaterial")
    bsdf = n.new("ShaderNodeBsdfDiffuse")
    t = n.new("ShaderNodeTexImage")
    t.image = bpy.data.images.load(os.path.join(TEXTURES, file), check_existing=True)
    t.interpolation = "Closest"
    links = m.node_tree.links
    links.new(t.outputs[0], bsdf.inputs["Color"])
    last = bsdf.outputs[0]
    if emit:
        add = n.new("ShaderNodeAddShader")
        e = n.new("ShaderNodeEmission")
        e.inputs["Strength"].default_value = emit
        links.new(t.outputs[0], e.inputs[0])
        links.new(last, add.inputs[0])
        links.new(e.outputs[0], add.inputs[1])
        last = add.outputs[0]
    if alpha:
        mix = n.new("ShaderNodeMixShader")
        tr = n.new("ShaderNodeBsdfTransparent")
        links.new(t.outputs["Alpha"], mix.inputs[0])
        links.new(tr.outputs[0], mix.inputs[1])
        links.new(last, mix.inputs[2])
        last = mix.outputs[0]
        m.surface_render_method = "DITHERED"
    links.new(last, out.inputs[0])
    return m


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
