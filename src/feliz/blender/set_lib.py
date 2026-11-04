# Paths and set-building helpers shared by the feliz scripts. Started from Missão's set_lib, with glossy smooth materials instead of ps1_material.
import bpy, json, math, os, sys, time
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
WORK = os.path.join(ROOT, "blender", "feliz")
ASSETS = os.path.join(WORK, "assets")
TEXTURES = os.path.join(WORK, "textures")
REVIEW = os.path.join(WORK, "review")
for p in (os.path.join(ROOT, "src", "thps", "blender"), os.path.join(ROOT, "src", "planeta", "blender"), HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

TL = json.load(open(os.path.join(ROOT, "src", "feliz", "timeline.json"), encoding="utf8"))

# Internal render size, one setting for the whole pipeline. The look is Wii-era soft: small render, smooth upscale, bloom.
RENDER_W, RENDER_H = 480, 854

TEX_MAX = 1024  # textures above this are shrunk; the 512 limit of the old laptop isn't needed on the RTX 4060
_small = {}


def srgb(hexstr):
    v = [int(hexstr[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in v]


def fresh(name, scene=None):
    """An empty collection linked to the scene."""
    scene = scene or bpy.context.scene
    c = bpy.data.collections.get(name)
    if c:
        for o in list(c.objects):
            bpy.data.objects.remove(o, do_unlink=True)
    else:
        c = bpy.data.collections.new(name)
    if c.name not in scene.collection.children:
        scene.collection.children.link(c)
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


def gloss(name, rgb=None, image=None, rough=0.3, coat=0.5, spec=0.5, emit=0.0, metal=0.0, alpha=None):
    """Glossy plastic, the vinyl-toy look. Takes a flat colour or an image with soft filtering. Re-running rewrites it."""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    t = m.node_tree
    t.nodes.clear()
    out = t.nodes.new("ShaderNodeOutputMaterial")
    b = t.nodes.new("ShaderNodeBsdfPrincipled")
    b.name = "bsdf"
    if rgb:
        b.inputs["Base Color"].default_value = (*srgb(rgb), 1)
    if image:
        tx = t.nodes.new("ShaderNodeTexImage")
        tx.image = image
        tx.interpolation = "Linear"
        t.links.new(tx.outputs[0], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Specular IOR Level"].default_value = spec
    b.inputs["Coat Weight"].default_value = coat
    b.inputs["Coat Roughness"].default_value = 0.12
    if emit:
        b.inputs["Emission Color"].default_value = (*srgb(rgb or "ffffff"), 1)
        b.inputs["Emission Strength"].default_value = emit
    if alpha is not None:
        b.inputs["Alpha"].default_value = alpha
        m.surface_render_method = "BLENDED"
    t.links.new(b.outputs[0], out.inputs[0])
    return m


def soften_asset_material(m):
    """Keeps a model's own colours and normals but gives it smooth filtering and a little shine, so it sits in the same world."""
    if not m or not m.use_nodes:
        return
    for n in m.node_tree.nodes:
        if n.type == "TEX_IMAGE":
            n.interpolation = "Linear"
        if n.type == "UVMAP":
            n.uv_map = "UVMap"  # flatten() writes one UV layer under this name
        if n.type == "BSDF_PRINCIPLED":
            for name in ("Roughness", "Metallic"):
                sock = n.inputs[name]
                for l in list(sock.links):
                    m.node_tree.links.remove(l)
            n.inputs["Roughness"].default_value = 0.5
            n.inputs["Metallic"].default_value = 0.0
    if m.surface_render_method == "BLENDED":
        m.surface_render_method = "DITHERED"


def shrink(m, size=TEX_MAX):
    """Swaps a material's textures for smaller PNGs next to the project. Shared images shrink once."""
    if not m or not m.use_nodes:
        return
    os.makedirs(TEXTURES, exist_ok=True)
    for n in m.node_tree.nodes:
        if n.type != "TEX_IMAGE" or not n.image or max(n.image.size) <= size:
            continue
        key = (n.image.name, size)
        if key not in _small or _small[key].name not in bpy.data.images:
            w, h = n.image.size
            k = size / max(w, h)
            tmp = n.image.copy()
            tmp.scale(max(int(w * k), 1), max(int(h * k), 1))
            name = "small " + n.image.name.replace(":", "_").replace("/", "_").replace("\\", "_")
            path = os.path.join(TEXTURES, name + ".png")
            tmp.filepath_raw = path
            tmp.file_format = "PNG"
            tmp.save()
            bpy.data.images.remove(tmp)
            _small[key] = bpy.data.images.load(path, check_existing=False)
        n.image = _small[key]


def smooth(ob, levels=1, angle=None):
    """Smooth shading, optionally with subdivision."""
    me = ob.data
    if me.users > 1:
        pass
    for p in me.polygons:
        p.use_smooth = True
    me.update()
    if levels:
        s = ob.modifiers.get("sub") or ob.modifiers.new("sub", "SUBSURF")
        s.levels = levels
        s.render_levels = levels
    return ob


def flatten(name, target_h=None, face_yaw=0.0, max_faces=6000, rest_pose=True, coll=None):
    """Joins one imported model into a single mesh object "<name>_mesh", with its origin at the feet and optionally a set height.
    Skinned models are frozen in their rest pose. Decimates anything over max_faces. The originals stay in "assets"."""
    src_coll = bpy.data.collections["assets"]
    parts = [o for o in src_coll.objects if o.get("asset") == name and o.type == "MESH"]
    if not parts:
        raise RuntimeError("no meshes for " + name)
    dg = bpy.context.evaluated_depsgraph_get()
    verts, faces, uvs, fmat = [], [], [], []
    mats = []
    for ob in parts:
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        mw = ob.matrix_world
        base = len(verts)
        verts += [tuple(mw @ v.co) for v in me.vertices]
        slot = []
        for m in (ob.data.materials or [None]):  # an evaluated mesh has empty material slots, the original holds them
            if m not in mats:
                mats.append(m)
            slot.append(mats.index(m))
        uv = me.uv_layers.active
        for p in me.polygons:
            faces.append([base + i for i in p.vertices])
            fmat.append(slot[p.material_index] if p.material_index < len(slot) else 0)
            uvs.append([tuple(uv.data[li].uv) if uv else (0, 0) for li in p.loop_indices])
        ev.to_mesh_clear()
    new = bpy.data.meshes.new(name + "_mesh")
    new.from_pydata(verts, [], faces)
    layer = new.uv_layers.new(name="UVMap")
    li = 0
    for p, us in zip(new.polygons, uvs):
        for u in us:
            layer.data[li].uv = u
            li += 1
    for m in mats:
        new.materials.append(m)
    for p, i in zip(new.polygons, fmat):
        p.material_index = i
        p.use_smooth = True
    new.update()
    # Origin at the feet, centred, optional yaw and height
    xs, ys, zs = zip(*verts)
    c = Vector(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, min(zs)))
    k = (target_h / (max(zs) - min(zs))) if target_h else 1.0
    cy, sy = math.cos(math.radians(face_yaw)), math.sin(math.radians(face_yaw))
    for v in new.vertices:
        d = (v.co - c) * k
        v.co = (d.x * cy - d.y * sy, d.x * sy + d.y * cy, d.z)
    new.update()
    ob = bpy.data.objects.new(name + "_mesh", new)
    (coll or bpy.data.collections["prefabs"]).objects.link(ob)
    if len(new.polygons) > max_faces:
        d = ob.modifiers.new("dec", "DECIMATE")
        d.ratio = max_faces / len(new.polygons)
    return ob


def place(name, coll, loc=(0, 0, 0), rot=(0, 0, 0), s=1.0, parent=None, label=None):
    """A copy of a flattened prefab, sharing its mesh."""
    src = bpy.data.objects[name + "_mesh"]
    ob = src.copy()
    ob.name = label or f"{name}.{len(coll.objects)}"
    ob.parent = parent
    ob.location = loc
    ob.rotation_euler = rot
    ob.scale = (s, s, s) if not hasattr(s, "__len__") else s
    coll.objects.link(ob)
    return ob


def blobs(name, parts, mats, coll, parent=None, levels=0):
    """One smooth mesh from ellipsoids and cones. A part is (kind, centre, radii, material index, euler degrees or None),
    kind "ball" or "cone" (radii rx, ry, height; the cone points along local +Z)."""
    import bmesh
    from mathutils import Euler, Matrix
    bm = bmesh.new()
    for kind, c, r, mi, rot in parts:
        before = set(bm.faces)
        M = Matrix.Translation(c)
        if rot:
            M = M @ Euler([math.radians(a) for a in rot], "XYZ").to_matrix().to_4x4()
        if kind == "ball":
            M = M @ Matrix.Diagonal((r[0], r[1], r[2], 1))
            bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=16, radius=1.0, matrix=M)
        else:
            M = M @ Matrix.Diagonal((r[0], r[1], r[2], 1)) @ Matrix.Translation((0, 0, 0.5))
            bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=1.0, radius2=0.04, depth=1.0, matrix=M)
        for f in set(bm.faces) - before:
            f.material_index = mi
            f.smooth = True
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    ob.parent = parent
    if levels:
        smooth(ob, levels)
    return ob


def recentre(ob, c):
    """Moves a mesh so that the point c of its own space becomes its origin."""
    for v in ob.data.vertices:
        v.co -= Vector(c)
    ob.data.update()
