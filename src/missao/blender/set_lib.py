# Set-building helpers shared by the street and story set scripts.
import bpy, math, os, time

TEXTURES = r"C:\Users\lukeg\Projetos\pardingows\blender\missao\textures"
_small = {}


def tex_mat(name, path_, emit=0.0):
    """Hard-texel material from an image file."""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    n = m.node_tree.nodes
    n.clear()
    out = n.new("ShaderNodeOutputMaterial")
    bsdf = n.new("ShaderNodeBsdfDiffuse")
    t = n.new("ShaderNodeTexImage")
    t.image = bpy.data.images.load(path_, check_existing=True)
    t.interpolation = "Closest"
    links = m.node_tree.links
    links.new(t.outputs[0], bsdf.inputs["Color"])
    if emit:
        add = n.new("ShaderNodeAddShader")
        e = n.new("ShaderNodeEmission")
        e.inputs["Strength"].default_value = emit
        links.new(t.outputs[0], e.inputs[0])
        links.new(bsdf.outputs[0], add.inputs[0])
        links.new(e.outputs[0], add.inputs[1])
        links.new(add.outputs[0], out.inputs[0])
    else:
        links.new(bsdf.outputs[0], out.inputs[0])
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
    for p in me.polygons:
        p.use_smooth = False
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def place(name, coll, loc, rz=0.0, s=1.0):
    """A copy of a flattened prefab, sharing its mesh."""
    src = bpy.data.objects[name + "_mesh"]
    ob = src.copy()
    ob.name = f"{name}.{len(coll.objects)}"
    ob.parent = None
    ob.location = loc
    ob.rotation_euler = (0, 0, math.radians(rz))
    ob.scale = (s, s, s)
    coll.objects.link(ob)
    return ob


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
    """Hard texels, no shine, opaque. Normal, gloss and metal maps have no place on a PS1 model, so they go."""
    if not m or not m.use_nodes:
        return
    t = m.node_tree
    for n in list(t.nodes):
        if n.type == "TEX_IMAGE":
            sockets = [l.to_socket.name for o in n.outputs for l in o.links]
            if sockets and not any(s in ("Base Color", "Color", "Color1", "Alpha", "Fac") for s in sockets):
                t.nodes.remove(n)
                continue
            n.interpolation = "Closest"
        if n.type == "BSDF_PRINCIPLED":
            n.inputs["Roughness"].default_value = 1.0
            n.inputs["Specular IOR Level"].default_value = 0.0
            n.inputs["Metallic"].default_value = 0.0
            for name in ("Normal", "Roughness", "Metallic"):
                for l in list(n.inputs[name].links):
                    t.links.remove(l)


def shrink(m, size):
    """Swaps a material's texture for a small PNG next to the project. A copied image still carries its original
    full-size file inside it, so the copy is thrown away and the PNG is loaded fresh. Shared images shrink once."""
    if not m or not m.use_nodes:
        return
    for n in m.node_tree.nodes:
        if n.type != "TEX_IMAGE" or not n.image or max(n.image.size) <= size:
            continue
        key = (n.image.name, size)
        if key not in _small or not _small[key].name in bpy.data.images:
            w, h = n.image.size
            k = size / max(w, h)
            tmp = n.image.copy()
            tmp.scale(max(int(w * k), 1), max(int(h * k), 1))
            name = "small " + n.image.name.replace(":", "_").replace("/", "_")
            path = os.path.join(TEXTURES, name + ".png")
            tmp.filepath_raw = path
            tmp.file_format = "PNG"
            tmp.save()
            bpy.data.images.remove(tmp)
            _small[key] = bpy.data.images.load(path, check_existing=False)
        n.image = _small[key]
