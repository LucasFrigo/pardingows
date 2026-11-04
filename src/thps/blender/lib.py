# Shared helpers for the scene scripts. Imported by every sNN script.
import bpy, math
from mathutils import Euler, Quaternion, Vector

FPS = 30
SCALE = 0.23  # smurf units -> metres (about 1.6 m tall, cartoon proportions)

BONES = {
    "hips": "Bone", "spine": "Bone.016", "head": "Bone.001",
    "armR": "Bone.002", "foreR": "Bone.003", "handR": "Bone.004",   # +X side
    "armL": "Bone.009", "foreL": "Bone.010", "handL": "Bone.011",   # -X side
    "thighR": "Bone.005", "shinR": "Bone.006", "heelR": "Bone.007", "toeR": "Bone.008",
    "thighL": "Bone.012", "shinL": "Bone.013", "heelL": "Bone.014", "toeL": "Bone.015",
}


def srgb(hexstr):
    v = [int(hexstr[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in v]


def make_mat(name, rgb, emit=0.0, alpha=None):
    """Flat diffuse material, optionally glowing or see-through. Re-running rewrites it."""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    n = m.node_tree.nodes
    n.clear()
    out = n.new("ShaderNodeOutputMaterial")
    bsdf = n.new("ShaderNodeBsdfDiffuse")
    bsdf.inputs["Color"].default_value = (*srgb(rgb), 1)
    last = bsdf.outputs[0]
    if emit:
        add = n.new("ShaderNodeAddShader")
        e = n.new("ShaderNodeEmission")
        e.inputs["Color"].default_value = (*srgb(rgb), 1)
        e.inputs["Strength"].default_value = emit
        m.node_tree.links.new(last, add.inputs[0])
        m.node_tree.links.new(e.outputs[0], add.inputs[1])
        last = add.outputs[0]
    if alpha is not None:
        mix = n.new("ShaderNodeMixShader")
        tr = n.new("ShaderNodeBsdfTransparent")
        mix.inputs[0].default_value = alpha
        m.node_tree.links.new(tr.outputs[0], mix.inputs[1])
        m.node_tree.links.new(last, mix.inputs[2])
        last = mix.outputs[0]
        m.surface_render_method = "BLENDED"
    m.node_tree.links.new(last, out.inputs[0])
    return m


class Mesh:
    """Small polygon soup builder. Faces carry a material index."""

    def __init__(self):
        self.v, self.f, self.fm = [], [], []

    def box(self, c, s, mi=0):
        i = len(self.v)
        for sx in (-1, 1):
            for sy in (-1, 1):
                for sz in (-1, 1):
                    self.v.append((c[0] + sx * s[0], c[1] + sy * s[1], c[2] + sz * s[2]))
        for q in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
            self.f.append(tuple(i + k for k in q))
            self.fm.append(mi)
        return self

    def prism(self, outline, z0, z1, mi=0, mi_side=None):
        """Extrudes a counter-clockwise (x, y) outline from z0 to z1."""
        i, n = len(self.v), len(outline)
        self.v += [(x, y, z0) for x, y in outline] + [(x, y, z1) for x, y in outline]
        self.f.append(tuple(i + n - 1 - k for k in range(n)))
        self.fm.append(mi)
        self.f.append(tuple(i + n + k for k in range(n)))
        self.fm.append(mi)
        for k in range(n):
            a, b = k, (k + 1) % n
            self.f.append((i + a, i + b, i + n + b, i + n + a))
            self.fm.append(mi if mi_side is None else mi_side)
        return self

    def build(self, name, mats, parent=None, coll=None):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        for m in mats:
            me.materials.append(m)
        for p, i in zip(me.polygons, self.fm):
            p.material_index = i
            p.use_smooth = False
        me.update()
        ob = bpy.data.objects.new(name, me)
        (coll or bpy.context.scene.collection).objects.link(ob)
        ob.parent = parent
        return ob


def empty(name, parent=None, loc=(0, 0, 0), coll=None, size=0.3):
    ob = bpy.data.objects.new(name, None)
    ob.empty_display_size = size
    (coll or bpy.context.scene.collection).objects.link(ob)
    ob.parent = parent
    ob.location = loc
    return ob


def collection(name):
    """Fresh, empty collection linked to the scene."""
    c = bpy.data.collections.get(name)
    if c:
        for ob in list(c.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
    else:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c


def set_bone_rot(arm, alias, deg):
    """Rotates a bone by Euler degrees given in the armature's rest axes, not the bone's roll axes.
    +X bends forward (the character faces -Y), +Z turns towards +X, +Y leans towards +X."""
    pb = arm.pose.bones[BONES[alias]]
    rest = pb.bone.matrix_local.to_quaternion()
    q = Euler([math.radians(a) for a in deg], "XYZ").to_quaternion()
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = rest.inverted() @ q @ rest


UPPER = ("spine", "head", "armR", "foreR", "handR", "armL", "foreL", "handL")
DECK_Z = 0.88  # height of the deck above the ground, smurf units


def apply_pose(prefix, pose):
    """Puts a player in a library pose. pose["free"] means off the board: leg IK off, soles on the root."""
    arm = bpy.data.objects["Armature" if prefix == "P1" else prefix + "_arm"]
    body = bpy.data.objects[prefix + "_body"]
    free = pose.get("free", False)
    dx, dy, dz, rx, ry, rz = pose.get("body", (0, 0, 0, 0, 0, 0))
    body.location = (dx, dy, dz + (0 if free else DECK_Z))
    body.rotation_euler = [math.radians(a) for a in (rx, ry, rz)]
    for alias in UPPER:
        set_bone_rot(arm, alias, pose.get(alias, (0, 0, 0)))
    for pb in arm.pose.bones:
        for c in pb.constraints:
            if c.name == "foot":
                c.influence = 0.0 if free else 1.0
