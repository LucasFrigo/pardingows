# Helpers shared by the LEGO scene scripts: paths, scale, ABS plastic materials, mesh building, prefabs and bone name lookups.
# Scale: 1 Blender unit is 10 cm of real LEGO. A minifig is about 0.39 tall, one stud pitch is 0.08.
import bpy, json, math, os, re, time
from mathutils import Matrix, Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
WORK = os.path.join(ROOT, "blender", "lego")
ASSETS = os.path.join(WORK, "assets")
TEXTURES = os.path.join(WORK, "textures")
REVIEW = os.path.join(WORK, "review")
TL = json.load(open(os.path.join(ROOT, "src", "lego", "timeline.json"), encoding="utf8"))
BLEND = os.path.join(WORK, "lego.blend")
FAR = (500, 500, -50)
RENDER_W, RENDER_H = 1080, 1920
FIG = 10.0  # the rig is modelled at real size, about 0.039 m
P, BRICK, PLATE = 0.08, 0.096, 0.032  # stud pitch, brick height, plate height
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


def srgb(hexstr):
    v = [int(hexstr[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in v]


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


def shrink(m, size, tag=""):
    """Swaps a material's texture for a small PNG next to the project. A copied image still carries its original
    full-size file inside it, so the copy is thrown away and the PNG is loaded fresh. Shared images shrink once."""
    if not m or not m.node_tree:
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
            cs = n.image.colorspace_settings.name
            bpy.data.images.remove(tmp)
            _small[key] = bpy.data.images.load(path, check_existing=False)
            _small[key].colorspace_settings.name = cs
        n.image = _small[key]


def abs_mat(name, rgb, rough=0.2, metal=0.0, emit=0.0, alpha=None):
    """Moulded ABS plastic: saturated, glossy, with a faint surface scuff so highlights don't look like wet glass."""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    t = m.node_tree
    t.nodes.clear()
    out = t.nodes.new("ShaderNodeOutputMaterial")
    b = t.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (*srgb(rgb), 1)
    b.inputs["Metallic"].default_value = metal
    b.inputs["Specular IOR Level"].default_value = 0.5
    if emit:
        b.inputs["Emission Color"].default_value = (*srgb(rgb), 1)
        b.inputs["Emission Strength"].default_value = emit
    if alpha is not None:
        b.inputs["Alpha"].default_value = alpha
        b.inputs["Transmission Weight"].default_value = 0.6
    # Scuffs: small noise on roughness only, so colour stays clean
    tc = t.nodes.new("ShaderNodeTexCoord")
    nz = t.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 90.0
    nz.inputs["Detail"].default_value = 4.0
    mr = t.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.35
    mr.inputs["From Max"].default_value = 0.7
    mr.inputs["To Min"].default_value = rough
    mr.inputs["To Max"].default_value = rough + 0.1
    t.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    t.links.new(nz.outputs[0], mr.inputs["Value"])
    t.links.new(mr.outputs[0], b.inputs["Roughness"])
    t.links.new(b.outputs[0], out.inputs[0])
    return m


def mesh_ob(name, v, f, mats, coll, fm=None, smooth=True, sharp_deg=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(x) for x in v], [], f)
    for m in mats:
        me.materials.append(m)
    if fm:
        for p, i in zip(me.polygons, fm):
            p.material_index = i
    if smooth:
        me.shade_smooth()
        if sharp_deg:
            me.set_sharp_from_angle(angle=math.radians(sharp_deg))
    me.update()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def flatten(name, asset, coll, match=None, height=None, length=None, scale=None, keep_xy=False, keep_z=False, rz=0.0, rx=0.0, decimate=None, sharp_deg=40):
    """Merges an asset's meshes (or those whose name matches) as they stand now into PF_<name>, centred with its base on z = 0.
    height or length (the longest horizontal side) gives the final size in Blender units, or scale a plain factor. decimate is a face ratio."""
    meshes = [o for o in parts(asset) if match is None or re.search(match, o.name)]
    assert meshes, f"{name}: nothing matches {match} in {asset}"
    if decimate:
        for o in meshes:
            if not o.modifiers.get("dec"):
                o.modifiers.new("dec", "DECIMATE").ratio = decimate
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    v, f, fm, uvs, mats = [], [], [], [], []
    colours = []
    for ob in meshes:
        ev = ob.evaluated_get(dg)
        me = bpy.data.meshes.new_from_object(ev)
        me.transform(ev.matrix_world)
        off, base = len(v), len(mats)
        mats += list(me.materials) or [None]
        v += [tuple(x.co) for x in me.vertices]
        uv = me.uv_layers.active
        col = me.color_attributes.active_color if me.color_attributes else None
        for p in me.polygons:
            f.append(tuple(off + i for i in p.vertices))
            fm.append(base + p.material_index)
            uvs.append([tuple(uv.data[l].uv) if uv else (0, 0) for l in p.loop_indices])
            if col is not None and col.domain == "CORNER":
                colours.append([tuple(col.data[l].color) for l in p.loop_indices])
            else:
                colours.append(None)
        bpy.data.meshes.remove(me)
    me = bpy.data.meshes.new("PF_" + name)
    me.from_pydata(v, [], f)
    for mt in mats:
        me.materials.append(mt)
    layer = me.uv_layers.new(name="UVMap")
    for p, q, mi in zip(me.polygons, uvs, fm):
        p.material_index = mi
        for l, uv in zip(p.loop_indices, q):
            layer.data[l].uv = uv
    if any(c is not None for c in colours):
        ca = me.color_attributes.new("Col", "BYTE_COLOR", "CORNER")
        for p, q in zip(me.polygons, colours):
            for l, c in zip(p.loop_indices, q or [(1, 1, 1, 1)] * p.loop_total):
                ca.data[l].color = c
    pts = [x.co for x in me.vertices]
    lo = Vector(min(p[i] for p in pts) for i in range(3))
    hi = Vector(max(p[i] for p in pts) for i in range(3))
    size = hi - lo
    k = scale if scale else height / size.z if height else length / max(size.x, size.y) if length else 1.0
    tx = 0 if keep_xy else -(lo.x + hi.x) / 2
    ty = 0 if keep_xy else -(lo.y + hi.y) / 2
    tz = 0 if keep_z else -lo.z
    me.transform(Matrix.Rotation(rz, 4, "Z") @ Matrix.Rotation(rx, 4, "X") @ Matrix.Scale(k, 4) @ Matrix.Translation(Vector((tx, ty, tz))))
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(sharp_deg))
    me.update()
    ob = bpy.data.objects.new("PF_" + name, me)
    coll.objects.link(ob)
    ob.location = FAR
    ob.hide_render = True
    print(f"PF_{name}: {len(f)} polys, size {size.x * k:.3f} {size.y * k:.3f} {size.z * k:.3f}", flush=True)
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


def bone_key(name):
    """A rig's bone name without its export number: shoulder_L_011 -> shoulder_L. The same across all the figures."""
    return re.sub(r"_\d+$", "", name)


def bones_of(arm):
    return {bone_key(b.name): b.name for b in arm.data.bones}


def piece(ob, arm, bone):
    """Hangs a rigid piece, built in world space with the rig at rest, on a bone without moving it. Key lookups use bone_key."""
    wm = ob.matrix_world.copy()
    ob.parent = arm
    ob.parent_type = "BONE"
    ob.parent_bone = bones_of(arm)[bone]
    bpy.context.view_layer.update()
    ob.matrix_parent_inverse = Matrix.Identity(4)
    ob.matrix_world = wm
    return ob
