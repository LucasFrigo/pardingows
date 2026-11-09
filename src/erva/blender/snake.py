# The cobra: a noodle snake built in code. Its body is a bevelled Bezier curve whose points are set every frame, so
# slithering, sneaking, coiling, going limp and laughing are all just point paths. The head is a separate rigid object
# (with a hinged jaw) that sits on the first point and looks along the body's direction or wherever it's told.
#   build(coll)            makes COBRA_body, COBRA_head (+ jaw, eyes, grin, tongue, bowler hat, horns)
#   pose(path, look, ...)  path: world points head-first; look: where the snout points
#   POSES[name](base, face) returns pose() arguments for the stock poses (stand, sneak, laugh, limp, giant)
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

N = 12  # body points
RADIUS = 0.075  # body radius at its thickest, metres
# radius along the body, neck first: thick behind the head, thinning to the tail tip
TAPER = [0.7, 0.95, 1.0, 1.0, 0.97, 0.92, 0.85, 0.75, 0.62, 0.46, 0.3, 0.12]


def _blob(bm, c, r, along=None):
    rot = Matrix.Identity(4)
    if along is not None:
        rot = Vector((0, 1, 0)).rotation_difference(Vector(along).normalized()).to_matrix().to_4x4()
    bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=14, radius=1.0,
                              matrix=Matrix.Translation(Vector(c)) @ rot @ Matrix.Diagonal(Vector((*r, 1))))


def _mesh(name, parts, mats):
    """parts: list of (material index, builder)"""
    bm = bmesh.new()
    for mi, f in parts:
        before = set(bm.faces)
        f(bm)
        for fa in set(bm.faces) - before:
            fa.material_index = mi
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    for m in mats:
        me.materials.append(m)
    return me


def _ob(name, data, coll, parent=None):
    ob = bpy.data.objects.get(name)
    if ob:
        bpy.data.objects.remove(ob, do_unlink=True)
    ob = bpy.data.objects.new(name, data)
    coll.objects.link(ob)
    if parent:
        ob.parent = parent
    return ob


def build(coll, cel, outline):
    """cel(name, tone, ...) and outline(ob) come from set_lib and hose, so the snake matches the cast."""
    skin, belly, ink = cel("cobra skin", 0.3), cel("cobra belly", 0.7), cel("cobra ink", 0.012)
    white, mouth, tongue_m = cel("cobra eye", 0.97), cel("cobra mouth", 0.05), cel("cobra tongue", 0.55)
    hat_m, band_m, horn_m = cel("cobra hat", 0.1), cel("cobra hat band", 0.5), cel("cobra horn", 0.85)

    cu = bpy.data.curves.new("COBRA_body", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_mode = "ROUND"
    cu.bevel_depth = RADIUS
    cu.bevel_resolution = 5
    cu.resolution_u = 10
    cu.use_fill_caps = True
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(N - 1)
    for p, r in zip(sp.bezier_points, TAPER):
        p.handle_left_type = p.handle_right_type = "AUTO"
        p.radius = r
    cu.materials.append(skin)
    body = _ob("COBRA_body", cu, coll)
    outline(body)

    # Head, in its own frame: snout towards +Y, top towards +Z, origin at the neck joint
    head = _ob("COBRA_head", _mesh("COBRA_head", [
        (0, lambda bm: _blob(bm, (0, 0.11, 0.05), (0.135, 0.16, 0.115))),         # cranium
        (0, lambda bm: _blob(bm, (0, 0.23, 0.02), (0.115, 0.13, 0.075))),         # snout
        (1, lambda bm: _blob(bm, (0, 0.22, -0.01), (0.095, 0.115, 0.04))),         # pale upper lip line
        (2, lambda bm: [_blob(bm, (s * 0.04, 0.345, 0.045), (0.012, 0.01, 0.01)) for s in (-1, 1)]),  # nostrils
    ], [skin, belly, ink]), coll, body)
    jaw = _ob("COBRA_jaw", _mesh("COBRA_jaw", [
        (0, lambda bm: _blob(bm, (0, 0.15, -0.035), (0.105, 0.15, 0.045))),
        (1, lambda bm: _blob(bm, (0, 0.13, -0.02), (0.09, 0.13, 0.03))),        # mouth inside, dark
    ], [belly, mouth]), coll, head)
    jaw.location = (0, 0.04, -0.01)  # hinge
    eyes = _ob("COBRA_eyes", _mesh("COBRA_eyes", [
        (0, lambda bm: [_blob(bm, (s * 0.058, 0.17, 0.135), (0.052, 0.045, 0.075)) for s in (-1, 1)]),
        (1, lambda bm: [_blob(bm, (s * 0.052, 0.208, 0.14), (0.024, 0.016, 0.042)) for s in (-1, 1)]),
        (0, lambda bm: [_blob(bm, (s * 0.046, 0.222, 0.158), (0.007, 0.004, 0.011)) for s in (-1, 1)]),  # pie-cut glint
    ], [white, ink]), coll, head)
    # The sly grin: a black line along the jaw, corners curling up
    gc = bpy.data.curves.new("COBRA_grin", "CURVE")
    gc.dimensions = "3D"
    gc.bevel_depth = 0.009
    gc.bevel_resolution = 2
    g = gc.splines.new("BEZIER")
    pts = [(-0.105, 0.12, 0.05), (-0.1, 0.22, 0.0), (0, 0.33, -0.005), (0.1, 0.22, 0.0), (0.105, 0.12, 0.05)]
    g.bezier_points.add(len(pts) - 1)
    for p, c in zip(g.bezier_points, pts):
        p.co = c
        p.handle_left_type = p.handle_right_type = "AUTO"
    gc.materials.append(ink)
    _ob("COBRA_grin", gc, coll, head)
    # Forked tongue, hidden unless asked for
    def fork(bm):
        _blob(bm, (0, 0.42, -0.01), (0.018, 0.09, 0.006))
        for s in (-1, 1):
            _blob(bm, (s * 0.022, 0.53, -0.01), (0.012, 0.045, 0.005), along=(s * 0.45, 1, 0))
    tongue = _ob("COBRA_tongue", _mesh("COBRA_tongue", [(0, fork)], [tongue_m]), coll, head)
    tongue.hide_viewport = tongue.hide_render = True

    # The bowler: low round crown, a band, a curled brim
    def crown(bm):
        _blob(bm, (0, 0, 0.065), (0.09, 0.098, 0.075))
        for v in bm.verts:
            v.co.z = max(v.co.z, 0.0)
    def brim(bm):
        _blob(bm, (0, 0, 0.004), (0.14, 0.15, 0.014))
    def band(bm):
        _blob(bm, (0, 0, 0.02), (0.093, 0.101, 0.021))
    hat = _ob("COBRA_hat", _mesh("COBRA_hat", [(0, crown), (0, brim), (1, band)], [hat_m, band_m]), coll, head)
    hat.location = (0.015, -0.005, 0.128)
    hat.rotation_euler = (math.radians(22), math.radians(12), 0)
    def two_horns(bm):
        for s in (-1, 1):
            bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.028, radius2=0.002, depth=0.11,
                                  matrix=Matrix.Translation((s * 0.075, 0.0, 0.14)) @ Matrix.Rotation(s * -0.45, 4, "Y"))
    horns = _ob("COBRA_horns", _mesh("COBRA_horns", [(0, two_horns)], [horn_m]), coll, hat)
    horns.hide_viewport = horns.hide_render = True

    for o in (head, jaw, eyes, hat, horns):
        outline(o, 0.008)
    return body


def pose(path, look, up=(0, 0, 1), jaw=0.0, scale=1.0, tongue=False, horns=False):
    """path: N world points from the neck to the tail tip (any count, resampled). look: the snout's direction."""
    OB = bpy.data.objects
    body = OB["COBRA_body"]
    pts = _resample([Vector(p) for p in path], N)
    sp = body.data.splines[0]
    for p, c in zip(sp.bezier_points, pts):
        p.co = c
    body.data.bevel_depth = RADIUS * scale
    body.matrix_world = Matrix.Identity(4)
    f = Vector(look).normalized()
    u = Vector(up)
    x = f.cross(u).normalized()
    u = x.cross(f).normalized()
    rot = Matrix((x, f, u)).transposed().to_4x4()
    head = OB["COBRA_head"]
    head.matrix_world = Matrix.Translation(pts[0]) @ rot @ Matrix.Scale(scale, 4)
    OB["COBRA_jaw"].rotation_euler = (math.radians(-jaw), 0, 0)
    for name, on in (("COBRA_tongue", tongue), ("COBRA_horns", horns)):
        OB[name].hide_viewport = OB[name].hide_render = not on


def _resample(pts, n):
    """n points evenly spaced along the polyline pts."""
    d = [0.0]
    for a, b in zip(pts, pts[1:]):
        d.append(d[-1] + (b - a).length)
    out = []
    for k in range(n):
        s = d[-1] * k / (n - 1)
        i = max(0, min(len(pts) - 2, next((j for j in range(len(d) - 1) if d[j + 1] >= s), len(d) - 2)))
        t = (s - d[i]) / max(d[i + 1] - d[i], 1e-9)
        out.append(pts[i].lerp(pts[i + 1], t))
    return out


# ---------------------------------------------------------------- stock poses, around a base point on the ground, facing 'face'

def _frame(base, face):
    f = Vector(face).normalized()
    x = f.cross(Vector((0, 0, 1))).normalized()
    return Vector(base), f, x


def stand(base, face, height=1.15, sway=0.0):
    """Up on a coil of tail, an S-curve neck, head forward."""
    b, f, x = _frame(base, face)
    pts = []
    for k in range(10):  # neck down to the coil
        t = k / 9
        z = height * (1 - t) + 0.07 * t
        side = math.sin(t * math.pi * 1.6 + sway) * 0.16 * (1 - t * 0.5)
        pts.append(b + f * (0.18 * (1 - t)) + x * side + Vector((0, 0, z)))
    for k in range(1, 9):  # the coil on the floor
        a = k / 8 * math.pi * 1.6
        pts.append(b + x * (0.24 * math.cos(a)) - f * (0.24 * math.sin(a)) + Vector((0, 0, 0.07)))
    return dict(path=pts, look=f - Vector((0, 0, 0.15)))


def sneak(base, face, lift=0.6):
    """On the tip of the tail, arched like a question mark, head low and forward."""
    b, f, x = _frame(base, face)
    pts = [b + f * 0.35 + Vector((0, 0, lift + 0.15))]
    for k in range(1, 14):
        a = k / 13 * math.pi * 1.25
        pts.append(b + f * (0.35 * math.cos(a)) + Vector((0, 0, lift + 0.15 + 0.32 * math.sin(a) - k / 13 * 0.15)))
    pts.append(b + Vector((0, 0, 0.02)))
    return dict(path=pts[:1] + pts[1:], look=f - Vector((0, 0, 0.35)))


def laugh(base, face):
    p = stand(base, face, height=1.2)
    p.update(look=Vector(face).normalized() * 0.4 + Vector((0, 0, 1)), jaw=34)
    return p


def limp(base, face, held=(0, 0, 1.0)):
    """Hanging limp from a grip at 'held' (world), head flopped forward, body drooping to the floor."""
    h = Vector(held)
    b, f, x = _frame(base, face)
    pts = [h + f * 0.06 + Vector((0, 0, -0.04))]
    for k in range(1, 14):
        t = k / 13
        pts.append(h + f * (0.05 * math.sin(t * 6)) + x * (0.08 * t) + Vector((0, 0, -t * (h.z - 0.08))))
    pts += [Vector((pts[-1].x, pts[-1].y, 0.06)) + f * 0.25, Vector((pts[-1].x, pts[-1].y, 0.06)) + f * 0.5]
    return dict(path=pts, look=Vector((0, 0, -1)) + f * 0.3, up=f)


def giant(base, face):
    p = stand(base, face, height=1.25)
    p.update(scale=3.0, horns=True, jaw=12)
    p["path"] = [Vector(base) + (Vector(q) - Vector(base)) * 3.0 for q in p["path"]]
    return p


POSES = {"stand": stand, "sneak": sneak, "laugh": laugh, "limp": limp, "giant": giant}
