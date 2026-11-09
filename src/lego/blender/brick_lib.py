# The brick kit. Every world is built from these, so walls, floors and furniture share one plastic and one grid.
# Positions are in studs (x, y) and plates (z): a brick is 3 plates tall. A Bricks object collects many pieces into one mesh, coloured per piece,
# so a whole set costs one object and one material.
import bpy, math, random
from mathutils import Vector
from set_lib import BRICK, P, PLATE, srgb

GAP = 0.0007  # the hairline between neighbouring pieces that makes them read as separate bricks
BEVEL = 0.0022
_box_faces = None


def _box_template():
    """A bevelled box: 24 corners, 6 faces, 12 edge strips and 8 corner triangles, wound outwards."""
    global _box_faces
    if _box_faces:
        return _box_faces
    keys = [(sx, sy, sz, ax) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1) for ax in (0, 1, 2)]
    idx = {k: i for i, k in enumerate(keys)}
    pos = []
    for sx, sy, sz, ax in keys:
        pos.append((sx * (1.0 if ax == 0 else 0.9), sy * (1.0 if ax == 1 else 0.9), sz * (1.0 if ax == 2 else 0.9)))
    faces = []
    for s in (-1, 1):
        faces.append([idx[(a, b, s, 2)] for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
        faces.append([idx[(a, s, b, 1)] for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
        faces.append([idx[(s, a, b, 0)] for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
    for a in (-1, 1):
        for b in (-1, 1):
            faces.append([idx[(-1, a, b, 1)], idx[(1, a, b, 1)], idx[(1, a, b, 2)], idx[(-1, a, b, 2)]])
            faces.append([idx[(a, -1, b, 0)], idx[(a, 1, b, 0)], idx[(a, 1, b, 2)], idx[(a, -1, b, 2)]])
            faces.append([idx[(a, b, -1, 0)], idx[(a, b, 1, 0)], idx[(a, b, 1, 1)], idx[(a, b, -1, 1)]])
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                faces.append([idx[(sx, sy, sz, 0)], idx[(sx, sy, sz, 1)], idx[(sx, sy, sz, 2)]])
    out = []
    for f in faces:
        c = [sum(pos[i][k] for i in f) / len(f) for k in range(3)]
        a, b, d = (Vector(pos[i]) for i in f[:3])
        n = (b - a).cross(d - a)
        out.append(tuple(f) if n.dot(Vector(c)) > 0 else tuple(reversed(f)))
    _box_faces = (keys, out)
    return _box_faces


def linear(hexcol, jitter=0.0, rng=None):
    c = srgb(hexcol)
    if jitter:
        k = 1 + rng.uniform(-jitter, jitter)
        c = [min(x * k, 1.0) for x in c]
    return (*c, 1.0)


def vc_material():
    """Moulded ABS plastic, coloured per piece from the mesh, with a fine scuff in its roughness."""
    m = bpy.data.materials.get("abs brick")
    if m:
        return m
    m = bpy.data.materials.new("abs brick")
    m.use_nodes = True
    t = m.node_tree
    t.nodes.clear()
    out = t.nodes.new("ShaderNodeOutputMaterial")
    b = t.nodes.new("ShaderNodeBsdfPrincipled")
    col = t.nodes.new("ShaderNodeVertexColor")
    col.layer_name = "Col"
    b.inputs["Specular IOR Level"].default_value = 0.5
    tc = t.nodes.new("ShaderNodeTexCoord")
    nz = t.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 70.0
    nz.inputs["Detail"].default_value = 4.0
    mr = t.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.35
    mr.inputs["From Max"].default_value = 0.7
    mr.inputs["To Min"].default_value = 0.17
    mr.inputs["To Max"].default_value = 0.3
    t.links.new(col.outputs[0], b.inputs["Base Color"])
    t.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    t.links.new(nz.outputs[0], mr.inputs["Value"])
    t.links.new(mr.outputs[0], b.inputs["Roughness"])
    t.links.new(b.outputs[0], out.inputs[0])
    return m


class Bricks:
    def __init__(self, name, coll, origin=(0, 0, 0), seed=1):
        self.name, self.coll = name, coll
        self.o = origin
        self.v, self.f, self.c, self.sm = [], [], [], []
        self.rng = random.Random(seed)
        self.pieces = 0

    # ---- Raw pieces, in Blender units relative to the set's origin
    def box(self, cx, cy, cz, hx, hy, hz, col):
        """A bevelled box from its centre and half sizes. col is a linear rgba."""
        keys, faces = _box_template()
        i = len(self.v)
        ox, oy, oz = self.o
        bx, by, bz = max(hx - BEVEL, hx * 0.5), max(hy - BEVEL, hy * 0.5), max(hz - BEVEL, hz * 0.5)
        for sx, sy, sz, ax in keys:
            self.v.append((ox + cx + sx * (hx if ax == 0 else bx), oy + cy + sy * (hy if ax == 1 else by), oz + cz + sz * (hz if ax == 2 else bz)))
        self.c += [col] * 24
        for q in faces:
            self.f.append(tuple(i + k for k in q))
            self.sm.append(False)
        self.pieces += 1

    def stud(self, cx, cy, z, col, r=0.0245, h=0.017, n=12):
        """A stud standing on z. Far studs use fewer sides and no chamfer."""
        i = len(self.v)
        ox, oy, oz = self.o
        rings = ((r, 0.0), (r, h - 0.003), (r - 0.003, h)) if n > 8 else ((r, 0.0), (r, h))
        for rr, zz in rings:
            for k in range(n):
                t = 2 * math.pi * k / n
                self.v.append((ox + cx + rr * math.cos(t), oy + cy + rr * math.sin(t), oz + z + zz))
        self.c += [col] * (n * len(rings))
        for ring in range(len(rings) - 1):
            for k in range(n):
                a, b = i + ring * n + k, i + ring * n + (k + 1) % n
                self.f.append((a, b, b + n, a + n))
                self.sm.append(n > 8)
        top = i + (len(rings) - 1) * n
        self.f.append(tuple(top + k for k in range(n)))
        self.sm.append(False)

    # ---- Pieces on the grid. x, y are the lowest stud corner, z the lowest plate.
    def brick(self, x, y, z, nx, ny, nz, col, studs=False, stud_n=12, jitter=0.03):
        """nx by ny studs, nz plates tall. col is a hex string."""
        c = linear(col, jitter, self.rng) if isinstance(col, str) else col
        cx, cy = (x + nx / 2) * P, (y + ny / 2) * P
        hz = nz * PLATE / 2
        self.box(cx, cy, z * PLATE + hz, nx * P / 2 - GAP, ny * P / 2 - GAP, hz - GAP * 0.4, c)
        if studs:
            top = (z + nz) * PLATE - GAP
            for i in range(nx):
                for j in range(ny):
                    self.stud((x + i + 0.5) * P, (y + j + 0.5) * P, top, c, n=stud_n)

    def wall(self, x, y, z, length, axis, courses, cols, openings=(), lengths=(2, 3, 4, 6), thick=2, studs_top=True):
        """Staggered courses along x or y. openings are (from, to, first course, last course) along the wall."""
        rng = self.rng
        cols = [cols] if isinstance(cols, str) else cols
        for c in range(courses):
            u = 0
            first = (c % 2) * 1
            while u < length:
                n = rng.choice(lengths)
                if u == 0 and first:
                    n = max(1, rng.choice((1, 3)))
                # A brick stops at the next opening edge and the wall's end
                for a, b, c0, c1 in openings:
                    if c0 <= c <= c1:
                        if a <= u < b:
                            n = b - u
                            u = b
                            n = 0
                            break
                        if u < a < u + n:
                            n = a - u
                if n == 0:
                    continue
                n = min(n, length - u)
                col = rng.choice(cols)
                top = studs_top and c == courses - 1
                if axis == "x":
                    self.brick(x + u, y, z + c * 3, n, thick, 3, col, studs=top, stud_n=8)
                else:
                    self.brick(x, y + u, z + c * 3, thick, n, 3, col, studs=top, stud_n=8)
                u += n

    def floor(self, x, y, nx, ny, z, cols, tiles=(4, 6, 8), near=None, nz=1, studs=True):
        """A floor of plates, top at z + nz plates. Studs inside near=(x0, y0, x1, y1) get full detail, the rest are cheap."""
        rng = self.rng
        cols = [cols] if isinstance(cols, str) else cols
        j = 0
        while j < ny:
            th = min(rng.choice(tiles), ny - j)
            i = 0
            while i < nx:
                tw = min(rng.choice(tiles), nx - i)
                c = linear(rng.choice(cols), 0.025, rng)
                cx, cy = (x + i + tw / 2) * P, (y + j + th / 2) * P
                hz = nz * PLATE / 2
                self.box(cx, cy, z * PLATE + hz, tw * P / 2 - GAP, th * P / 2 - GAP, hz - GAP * 0.4, c)
                if studs:
                    top = (z + nz) * PLATE - GAP
                    for a in range(tw):
                        for b in range(th):
                            sx, sy = x + i + a, y + j + b
                            full = near and near[0] <= sx < near[2] and near[1] <= sy < near[3]
                            self.stud((sx + 0.5) * P, (sy + 0.5) * P, top, c, n=12 if full else 6)
                i += tw
            j += th

    def build(self):
        me = bpy.data.meshes.new(self.name)
        me.from_pydata(self.v, [], self.f)
        ca = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
        ca.data.foreach_set("color", [x for c in self.c for x in c])
        me.polygons.foreach_set("use_smooth", self.sm)
        me.materials.append(vc_material())
        me.update()
        ob = bpy.data.objects.new(self.name, me)
        self.coll.objects.link(ob)
        print(f"  {self.name}: {self.pieces} pieces, {len(self.f)} faces", flush=True)
        return ob
