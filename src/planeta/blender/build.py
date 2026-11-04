# Geometry helpers shared by the planeta scripts. Everything appends to a lib.Mesh or works in world space.
import bpy, math, random
from mathutils import Vector


def attach(ob, arm, bone):
    """Hangs a rigid piece on a bone without moving it. The armature must be in its rest pose."""
    ob.parent = arm
    ob.parent_type = "BONE"
    ob.parent_bone = bone
    bpy.context.view_layer.update()
    ob.matrix_world = arm.matrix_world
    return ob


def ring(m, a, b, r, mi=0, n=8):
    """Short n-sided tube from point a to point b."""
    a, b = Vector(a), Vector(b)
    z = (b - a).normalized()
    x = z.cross(Vector((0, 1, 0))) if abs(z.y) < 0.9 else z.cross(Vector((1, 0, 0)))
    x.normalize()
    y = z.cross(x)
    i = len(m.v)
    for c in (a, b):
        for k in range(n):
            t = 2 * math.pi * (k + 0.5) / n
            m.v.append(tuple(c + (x * math.cos(t) + y * math.sin(t)) * r))
    m.f.append(tuple(i + n - 1 - k for k in range(n)))
    m.f.append(tuple(i + n + k for k in range(n)))
    m.fm += [mi, mi]
    for k in range(n):
        p, q = k, (k + 1) % n
        m.f.append((i + p, i + q, i + n + q, i + n + p))
        m.fm.append(mi)


def on_ball(c, r, azim, elev):
    """Point on a ball. azim 0 is the face (-Y), positive towards +X."""
    a, e = math.radians(azim), math.radians(elev)
    return Vector(c) + Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))) * r


def disc(m, c, r, azim, elev, rx, rz, mi, n=8, lift=0.0):
    """Flat oval lying on a ball, facing outwards."""
    centre = on_ball(c, r + lift, azim, elev)
    out = (centre - Vector(c)).normalized()
    x = Vector((0, 0, 1)).cross(out).normalized()
    z = out.cross(x)
    i = len(m.v)
    for k in range(n):
        t = 2 * math.pi * k / n
        m.v.append(tuple(centre + x * rx * math.cos(t) + z * rz * math.sin(t)))
    m.f.append(tuple(i + k for k in range(n)))
    m.fm.append(mi)


def shell(m, c, r, keep, paint, lats=10, lons=12, rim_mi=None, rim=0.07):
    """Faceted ball. keep(lat, lon) drops bands and windows; paint(lat, lon) picks the material.
    lat runs -5..4 bottom to top, lon -6..5 with the seam at the back, so 0 is just right of the face."""
    grid = {}
    for la in range(lats + 1):
        e = -90 + 180 * la / lats
        for lo in range(lons):
            grid[(la, lo)] = len(m.v)
            m.v.append(tuple(on_ball(c, r, -180 + 360 * lo / lons, e)))
    edges = {}
    for la in range(lats):
        for lo in range(lons):
            lat, lon = la - lats // 2, lo - lons // 2
            if not keep(lat, lon):
                continue
            q = (grid[(la, lo)], grid[(la, (lo + 1) % lons)], grid[(la + 1, (lo + 1) % lons)], grid[(la + 1, lo)])
            m.f.append(q)
            m.fm.append(paint(lat, lon))
            for u, v in zip(q, q[1:] + q[:1]):
                edges[frozenset((u, v))] = edges.get(frozenset((u, v)), 0) + 1
    if rim_mi is None:
        return
    # Every open edge gets a thick lip, which also hides the jagged inside of the shell
    for e, count in edges.items():
        if count == 1:
            u, v = tuple(e)
            cv = Vector(c)
            a, b = Vector(m.v[u]), Vector(m.v[v])
            j = len(m.v)
            m.v.append(tuple(cv + (a - cv) * (1 + rim)))
            m.v.append(tuple(cv + (b - cv) * (1 + rim)))
            m.f.append((u, v, j + 1, j))
            m.fm.append(rim_mi)


ROAD = 3.2  # half width of the flat, dead straight road along X. Characters on it stand at z = 0.
_rng = random.Random(7)
CRATERS = [(_rng.uniform(-190, 190), _rng.choice((-1, 1)) * _rng.uniform(13, 110), _rng.uniform(3, 15)) for _ in range(46)]
CRATERS += [(9, 24, 11), (-26, -21, 8), (38, -15, 7), (58, 22, 9)]  # placed where the shots look


def height(x, y):
    """Ground height. Dead flat on the road, rolling and cratered away from it, sinking towards a close horizon."""
    away = max(abs(y) - ROAD, 0)
    blend = min(away / 7, 1) ** 2
    z = 0.8 * math.sin(x * 0.11 + 1.3) * math.cos(y * 0.13) + 0.45 * math.sin(x * 0.27 - y * 0.21) + 0.25 * math.cos(x * 0.53 + y * 0.47)
    for cx, cy, r in CRATERS:
        d = math.hypot(x - cx, y - cy) / r
        if d < 1.6:
            bowl = -0.3 * r * (1 - d * d) if d < 1 else 0
            lip = 0.09 * r * math.exp(-((d - 1) / 0.22) ** 2)
            z += bowl + lip
    return blend * (z - away * away / 900)
