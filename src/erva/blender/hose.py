# Rubber-hose limbs, cartoon gloves and shoes for the Pardo rigs, plus the ink outline used by every cast member.
#
# The rig's arm and leg pieces are rigid, so they're hidden and each limb becomes a bevelled Bezier tube from the shoulder
# (hip) to the wrist (ankle). Its handles pull towards the elbow (knee): a quadratic arc, so the limb bends in one smooth
# curve with no joint, the 1930s way. update(prefix) re-shapes the tubes from the current pose; call it after posing.
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

LIMBS = {  # tube: (upper bone, lower bone, end bone)
    "armR": ("Bone.002", "Bone.003", "Bone.004"), "armL": ("Bone.009", "Bone.010", "Bone.011"),
    "legR": ("Bone.005", "Bone.006", "Bone.007"), "legL": ("Bone.012", "Bone.013", "Bone.014"),
}
ARM_R, LEG_R = 0.042, 0.06  # tube radius, metres
SHOE_ANCHOR = Vector((0, -0.22, 0.42))  # where a leg ends, in the shoe mesh's own units: inside the heel, above the sole
INK_W = 0.011  # outline width, metres


def ink_material():
    m = bpy.data.materials.get("ink")
    if m:
        return m
    m = bpy.data.materials.new("ink")
    m.use_nodes = True
    t = m.node_tree
    t.nodes.clear()
    em = t.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (0.012, 0.01, 0.008, 1)
    out = t.nodes.new("ShaderNodeOutputMaterial")
    t.links.new(em.outputs[0], out.inputs[0])
    m.use_backface_culling = True
    m.diffuse_color = (0, 0, 0, 1)
    return m


def outline(ob, width=INK_W):
    """Inverted-hull ink line: a flipped, culled shell around the object, in the ink material."""
    if ob.type not in ("MESH", "CURVE") or "ink" in ob.modifiers:
        return
    data = ob.data
    ink = ink_material()
    if ink.name not in [m.name for m in data.materials if m]:
        data.materials.append(ink)
    idx = [m.name if m else "" for m in data.materials].index(ink.name)
    sc = max(ob.matrix_world.to_scale())
    mod = ob.modifiers.new("ink", "SOLIDIFY")
    mod.thickness = -width / max(sc, 1e-6)
    mod.offset = 1.0
    mod.use_flip_normals = True
    mod.use_rim = False
    mod.material_offset = idx
    mod.material_offset_rim = idx
    ob["ink"] = width


def tube(name, radius, mat, coll):
    cu = bpy.data.curves.get(name) or bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_mode = "ROUND"
    cu.bevel_depth = radius
    cu.bevel_resolution = 4
    cu.resolution_u = 14
    cu.use_fill_caps = True
    cu.splines.clear()
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(1)
    for p in sp.bezier_points:
        p.handle_left_type = p.handle_right_type = "FREE"
    cu.materials.clear()
    cu.materials.append(mat)
    ob = bpy.data.objects.get(name) or bpy.data.objects.new(name, cu)
    if ob.name not in coll.objects:
        coll.objects.link(ob)
    return ob


def update(prefix, depsgraph=None):
    """Re-shapes a rig's four tubes from its current pose (world space). Pass the depsgraph of the view layer the rig
    lives in when that isn't the active one (the soul is excluded from the main layer, so it's stale there)."""
    OB = bpy.data.objects
    arm = OB[prefix + "_arm"]
    if depsgraph is not None:
        arm = arm.evaluated_get(depsgraph)
    M = arm.matrix_world
    for limb, (a, b, c) in LIMBS.items():
        ob = OB.get(f"{prefix}_{limb}")
        if not ob:
            continue
        s = M @ arm.pose.bones[a].head
        e = M @ arm.pose.bones[b].head
        pc = arm.pose.bones[c]
        w = M @ pc.head
        if limb.startswith("leg"):
            # the leg ends inside the shoe's upper (the shoe rides the foot bone), so the two always join
            shoe = OB.get(f"{prefix}_shoe{limb[-1]}")
            if shoe is not None and depsgraph is not None:
                shoe = shoe.evaluated_get(depsgraph)
            if shoe and not shoe.hide_viewport:
                w = shoe.matrix_world @ SHOE_ANCHOR
        p0, p1 = ob.data.splines[0].bezier_points
        # quadratic arc with the elbow as its control point, written as a cubic
        p0.co, p0.handle_right, p0.handle_left = s, s + (e - s) * (2 / 3), s - (e - s) * 0.05
        p1.co, p1.handle_left, p1.handle_right = w, w + (e - w) * (2 / 3), w - (e - w) * 0.05
        ob.matrix_world = Matrix.Identity(4)


def lengthen_arms(arm, k):
    """Stretches both arm chains in the rest pose by k from the shoulder (edit mode)."""
    vl = bpy.context.view_layer
    vl.objects.active = arm
    with bpy.context.temp_override(active_object=arm, object=arm, selected_objects=[arm], selected_editable_objects=[arm]):
        bpy.ops.object.mode_set(mode="EDIT")
        eb = arm.data.edit_bones
        for chain in (("Bone.002", "Bone.003", "Bone.004"), ("Bone.009", "Bone.010", "Bone.011")):
            s = eb[chain[0]].head.copy()
            for n in chain:
                b = eb[n]
                b.head = s + (b.head - s) * k
                b.tail = s + (b.tail - s) * k
        bpy.ops.object.mode_set(mode="OBJECT")


# ---------------------------------------------------------------- gloves and shoes, built in bone space (rig units)

def _blob(bm, centre, radii, along=None):
    """An ellipsoid; 'along' points its local Y axis (the third radius stays across)."""
    rot = Matrix.Identity(4)
    if along is not None:
        rot = Vector((0, 1, 0)).rotation_difference(Vector(along).normalized()).to_matrix().to_4x4()
    m = Matrix.Translation(Vector(centre)) @ rot @ Matrix.Diagonal(Vector((*radii, 1)))
    bmesh.ops.create_uvsphere(bm, u_segments=18, v_segments=12, radius=1.0, matrix=m)


def _mesh(name, build, mats):
    bm = bmesh.new()
    build(bm)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    for m in mats:
        me.materials.append(m)
    return me


def glove_meshes(u, w, white, shade):
    """The five glove shapes. u is the bone-space axis the fingers fan along, w the palm's thickness axis.
    The wrist is at the origin and the hand points along +Y. Units are rig units (x 0.23 for metres)."""
    U, Wv, Y = Vector(u), Vector(w), Vector((0, 1, 0))

    def at(du, dy, dw=0.0):
        return U * du + Y * dy + Wv * dw

    def cuff(bm):
        # a flared cuff: two rings of blobs read as a rolled cuff in silhouette
        _blob(bm, at(0, 0.08), (0.32, 0.12, 0.32), along=Y)
        _blob(bm, at(0, 0.0), (0.27, 0.09, 0.27), along=Y)

    def palm(bm, big=1.0):
        _blob(bm, at(0, 0.5), (0.42 * big, 0.4 * big, 0.3 * big), along=Y)

    def finger(bm, du, dirn, length=0.5, r=0.13, base=0.72):
        d = (U * dirn[0] + Y * dirn[1] + Wv * dirn[2]).normalized()
        c = at(du, base) + d * (length / 2)
        _blob(bm, c, (r, length / 2 + r * 0.6, r), along=d)

    def knuckles(bm):
        for du in (-0.24, 0, 0.24):
            _blob(bm, at(du, 0.8, 0.08), (0.15, 0.15, 0.17))

    def thumb(bm, dirn=(1, 0.8, 0), length=0.36):
        d = (U * dirn[0] + Y * dirn[1] + Wv * dirn[2]).normalized()
        _blob(bm, at(0.34, 0.42) + d * (length / 2), (0.12, length / 2 + 0.08, 0.12), along=d)

    shapes = {
        "open": lambda bm: (cuff(bm), palm(bm), finger(bm, -0.26, (-0.25, 1, 0)), finger(bm, 0, (0, 1, 0), 0.56),
                            finger(bm, 0.26, (0.25, 1, 0)), thumb(bm)),
        "fist": lambda bm: (cuff(bm), palm(bm, 1.08), knuckles(bm), thumb(bm, (0.2, 0.6, 0.8), 0.3)),
        "point": lambda bm: (cuff(bm), palm(bm, 1.05), knuckles(bm), finger(bm, 0, (0, 1, 0), 0.62, base=0.82),
                             thumb(bm, (0.2, 0.6, 0.8), 0.3)),
        "thumb": lambda bm: (cuff(bm), palm(bm, 1.08), knuckles(bm), thumb(bm, (0, 0, 1), 0.42)),
        "hold": lambda bm: (cuff(bm), palm(bm, 1.05), knuckles(bm), thumb(bm, (0.3, 0.7, 0.6), 0.32)),
    }
    return {k: _mesh(f"glove_{k}", f, [white]) for k, f in shapes.items()}


def bone_axes(arm, bone):
    """Which of the bone's local X/Z axes points along the rig's X (the fan axis for a hanging hand), signed."""
    m = arm.data.bones[bone].matrix_local.to_3x3()
    x, z = m.col[0], m.col[2]
    fan = Vector((1, 0, 0))
    if abs(x.dot(fan)) >= abs(z.dot(fan)):
        return (math.copysign(1, x.dot(fan)), 0, 0), (0, 0, 1)
    return (0, 0, math.copysign(1, z.dot(fan))), (1, 0, 0)


def attach(ob, arm, bone, local=Matrix.Identity(4)):
    """Parents ob to a bone so that 'local' is its transform in that bone's space with the origin at the bone's head."""
    ob.parent = arm
    ob.parent_type = "BONE"
    ob.parent_bone = bone
    ob.matrix_parent_inverse = Matrix.Identity(4)
    ob.matrix_basis = Matrix.Translation((0, -arm.data.bones[bone].length, 0)) @ local


def shoe_mesh(black, shine):
    """A big round cartoon shoe in world-like axes: toe towards -Y, sole at z = 0, heel at the origin."""
    def build(bm):
        _blob(bm, (0, -0.55, 0.3), (0.5, 0.78, 0.32))   # toe box
        _blob(bm, (0, -0.05, 0.3), (0.36, 0.4, 0.34))   # heel
        bmesh.ops.scale(bm, vec=(1, 1, 1), verts=bm.verts)
        for v in bm.verts:  # flat sole
            v.co.z = max(v.co.z, 0.02)
    return _mesh("shoe", build, [black])
