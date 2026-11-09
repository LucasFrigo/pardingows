# Staging checks for the Blender videos, run on the evaluated scene of a frame BEFORE rendering, so alignment problems
# are caught at development time instead of in review. Pure measurement: nothing in the scene is changed.
#   group(names_or_prefixes)                the visible mesh/curve objects of an actor (a rig prefix, "COBRA", a prop)
#   penetration(A, B)                       how deep (m) any vertex of A sits inside B's solid surface, and where
#   facing_error(root, target)              degrees between an actor's facing (its -Y) and the direction to a target
#   visible(objs, cam, ...)                 fraction of an actor's sample points that are in frame, not in the caption
#                                           band, and not hidden behind something else
#   gap(p, q)                               distance between two points (contact checks: prop to hand, joint to mouth)
#   lowest(objs)                            the lowest world z of an actor (feet on the ground, seats)
# Ink outlines (inverted-hull shells, material "ink" or "*ink*") are ignored: they're 1 cm skins, not volume.
import math

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def _is_ink(mat):
    return mat is not None and "ink" in mat.name.lower()


def _evaluated(objs, dg):
    """World vertices and solid (non-ink) triangles of the objects, plus instanced collections' meshes."""
    verts, tris = [], []
    for ob in objs:
        ev = ob.evaluated_get(dg)
        try:
            me = ev.to_mesh()
        except RuntimeError:
            continue
        if me is None:
            continue
        mats = list(ev.material_slots)
        mw = ev.matrix_world
        base = len(verts)
        verts += [mw @ v.co for v in me.vertices]
        me.calc_loop_triangles()
        for lt in me.loop_triangles:
            m = mats[lt.material_index].material if lt.material_index < len(mats) else None
            if not _is_ink(m):
                tris.append(tuple(base + i for i in lt.vertices))
        ev.to_mesh_clear()
    return verts, tris


def _instances(empty_names, dg):
    verts, tris = [], []
    for inst in dg.object_instances:
        if not inst.is_instance or inst.parent is None or inst.parent.original.name not in empty_names:
            continue
        ob = inst.object
        if ob.type != "MESH":
            continue
        me = ob.data
        mats = list(ob.material_slots)
        mw = inst.matrix_world
        base = len(verts)
        verts += [mw @ v.co for v in me.vertices]
        me.calc_loop_triangles()
        for lt in me.loop_triangles:
            m = mats[lt.material_index].material if lt.material_index < len(mats) else None
            if not _is_ink(m):
                tris.append(tuple(base + i for i in lt.vertices))
    return verts, tris


def group(names, exclude=()):
    """Visible mesh/curve objects whose name equals or starts with '<name>_' for any of names (and collection-instance
    empties named exactly). Hidden pieces (hide_render) and names in exclude are left out."""
    out = []
    for ob in bpy.data.objects:
        if ob.hide_render or ob.name in exclude:
            continue
        hit = any(ob.name == n or ob.name.startswith(n + "_") for n in names)
        if not hit:
            continue
        if ob.type in ("MESH", "CURVE") or (ob.type == "EMPTY" and ob.instance_type == "COLLECTION"):
            if all(not c.hide_render for c in ob.users_collection):
                out.append(ob)
    return out


class Solid:
    """An actor's surface for the inside/outside tests."""

    def __init__(self, objs, dg=None):
        dg = dg or bpy.context.evaluated_depsgraph_get()
        empties = {o.name for o in objs if o.type == "EMPTY"}
        v1, t1 = _evaluated([o for o in objs if o.type != "EMPTY"], dg)
        v2, t2 = _instances(empties, dg) if empties else ([], [])
        off = len(v1)
        self.verts = v1 + v2
        self.tris = t1 + [tuple(i + off for i in t) for t in t2]
        self.bvh = BVHTree.FromPolygons(self.verts, self.tris, all_triangles=True) if self.tris else None

    def depth(self, p, reach=0.25):
        """How far p is inside the surface (> 0 inside), judged by the nearest face's normal."""
        if not self.bvh:
            return 0.0
        loc, n, _i, d = self.bvh.find_nearest(p, reach)
        if loc is None:
            return 0.0
        s = (p - loc).dot(n)
        return -s if s < 0 else 0.0


def crossing(A, B):
    """Where two surfaces pass through each other: (size of the crossing region in metres, its centre). This is what
    shows on screen as clipping. Resting contact gives a tiny region; open or badly-normalled imported models don't fool
    it (an inside test by face normals does)."""
    if not A.bvh or not B.bvh:
        return 0.0, None
    pairs = A.bvh.overlap(B.bvh)
    if not pairs:
        return 0.0, None
    pts = []
    for i, _j in pairs:
        t = A.tris[i]
        pts.append((A.verts[t[0]] + A.verts[t[1]] + A.verts[t[2]]) / 3)
    c = sum(pts, Vector()) / len(pts)
    return 2 * max((p - c).length for p in pts), c


def penetration(a_objs, b_objs, dg=None, sample=900, reach=0.25):
    """Deepest point of A inside B: (depth in metres, the point). Uses up to 'sample' of A's vertices."""
    dg = dg or bpy.context.evaluated_depsgraph_get()
    A = Solid(a_objs, dg)
    B = Solid(b_objs, dg)
    if not A.verts or not B.bvh:
        return 0.0, None
    step = max(1, len(A.verts) // sample)
    worst, where = 0.0, None
    for v in A.verts[::step]:
        d = B.depth(v, reach)
        if d > worst:
            worst, where = d, v
    return worst, where


def centre(objs):
    """World centre of the objects' bounding boxes (an object's origin can be anywhere, e.g. at the world origin)."""
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    return sum(pts, Vector()) / len(pts) if pts else Vector()


def facing_error(root, target, near=0.5):
    """Degrees between the actor's facing (its -Y, flattened) and the flat direction to the target. A target closer
    than 'near' horizontally (right on top of the actor) has no meaningful direction: 0."""
    f = root.matrix_world.to_3x3() @ Vector((0, -1, 0))
    f.z = 0
    d = Vector(target) - root.matrix_world.translation
    d.z = 0
    if f.length < 1e-6 or d.length < near:
        return 0.0
    return math.degrees(f.angle(d))


def gap(p, q):
    return (Vector(p) - Vector(q)).length


def lowest(objs, dg=None):
    dg = dg or bpy.context.evaluated_depsgraph_get()
    v, _t = _evaluated([o for o in objs if o.type != "EMPTY"], dg)
    return min((p.z for p in v), default=0.0)


def _see_through(ob):
    m = ob.active_material
    return m is not None and (_is_ink(m) or getattr(m, "surface_render_method", "") == "BLENDED")


def visible(objs, cam=None, dg=None, samples=60, caption_top=0.64, margin=0.02, ignore=()):
    """(fraction on screen and above the caption band, fraction of those not hidden behind something else).
    caption_top: screen height (0 top .. 1 bottom) where the caption band begins. ignore: names that don't count as
    blocking (the actor's own other parts: a head is allowed to be behind its own nose). See-through surfaces
    (blended materials, ink shells) never block."""
    sc = bpy.context.scene
    cam = cam or sc.camera
    dg = dg or bpy.context.evaluated_depsgraph_get()
    v, _t = _evaluated([o for o in objs if o.type != "EMPTY"], dg)
    if not v:
        return 0.0, 0.0
    step = max(1, len(v) // samples)
    pts = v[::step]
    own = {o.name for o in objs} | set(ignore)
    cam_at = cam.matrix_world.translation
    on, clear = 0, 0
    for p in pts:
        s = world_to_camera_view(sc, cam, p)
        if s.z <= 0 or not (margin < s.x < 1 - margin and margin < 1 - s.y < caption_top):
            continue
        on += 1
        start, left = cam_at.copy(), (p - cam_at).length - 0.03
        d = (p - cam_at).normalized()
        blocked = False
        for _k in range(6):
            hit, loc, _n, _i, ob, _m = sc.ray_cast(dg, start, d, distance=left)
            if not hit:
                break
            if ob.original.name in own or _see_through(ob):
                step = (loc - start).length + 0.002
                start, left = loc + d * 0.002, left - step
                continue
            blocked = True
            break
        if not blocked:
            clear += 1
    return on / len(pts), (clear / on if on else 0.0)
