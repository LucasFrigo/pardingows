# Step 3: the cast. Each figure is a copy of the base rig under a CH_<name> empty, or a crowd model made tidy the same way: Z up, facing -Y, soles on z = 0,
# at the video's scale. Hero figures get new colours, printed faces and torsos, and rigid pieces on their bones.
import bpy, json, math, os, sys, importlib
from mathutils import Matrix, Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import set_lib; importlib.reload(set_lib)
from set_lib import FIG, TEXTURES, WORK, abs_mat, flatten, fresh, mesh_ob, parts, piece, save, srgb

OB = bpy.data.objects
cast = fresh("cast", bpy.context.scene)
pf = fresh("cast_prefabs", bpy.context.scene)
pf.hide_render = True


# ---- Rig handling
def arm_of(asset):
    return next(o for o in parts(asset, "ARMATURE"))


def take(asset, name):
    """Moves one imported figure out of its export hierarchy and under a new CH_<name> root."""
    arm = arm_of(asset)
    root = OB.new("CH_" + name, None)
    cast.objects.link(root)
    root.scale = (FIG, FIG, FIG)
    bpy.context.view_layer.update()
    m0 = arm.matrix_world.copy()
    meshes = [o for o in parts(asset) if any(x.type == "ARMATURE" for x in o.modifiers)]
    rel = {o: m0.inverted() @ o.matrix_world for o in meshes}
    arm.parent = root
    arm.parent_type = "OBJECT"
    arm.matrix_parent_inverse = Matrix.Identity(4)
    arm.matrix_local = m0
    arm.name = f"{name}_arm"
    for ob in [arm] + meshes:
        for c in list(ob.users_collection):
            c.objects.unlink(ob)
        cast.objects.link(ob)
        ob.hide_set(False)
        ob.hide_render = False
        del ob["asset"]
    for i, ob in enumerate(meshes):
        ob.parent = arm
        ob.parent_type = "OBJECT"
        ob.matrix_parent_inverse = Matrix.Identity(4)
        ob.matrix_local = rel[ob]
        ob.name = f"{name}_{i}"
    root["figure"] = name
    return root, arm, meshes


def copy_fig(src, name):
    """A separate figure from an existing one: same armature data, its own pose and its own material slots."""
    sroot, sarm, smeshes = src
    root = OB.new("CH_" + name, None)
    cast.objects.link(root)
    root.scale = sroot.scale
    arm = sarm.copy()
    arm.name = f"{name}_arm"
    cast.objects.link(arm)
    arm.parent = root
    arm.matrix_parent_inverse = Matrix.Identity(4)
    arm.matrix_local = sarm.matrix_local
    meshes = []
    for i, s in enumerate(smeshes):
        ob = s.copy()
        ob.data = s.data.copy()
        ob.name = f"{name}_{i}"
        cast.objects.link(ob)
        ob.parent = arm
        ob.matrix_parent_inverse = Matrix.Identity(4)
        ob.matrix_local = s.matrix_local
        for md in ob.modifiers:
            if md.type == "ARMATURE":
                md.object = arm
        meshes.append(ob)
    root["figure"] = name
    return root, arm, meshes


SLOTS = ("Arm_Main_L", "Arm_Main_R", "Face", "Hand_L", "Hand_R", "Head", "Hip_Crotch", "Hip_Front", "Hip_Main", "Leg_L_Foot", "Leg_L_Front", "Leg_L_Main", "Leg_L_Side",
         "Leg_R_Foot", "Leg_R_Front", "Leg_R_Main", "Leg_R_Side", "Torso_Back", "Torso_Front", "Torso_Main")


def slot(ob):
    """Which part of the figure this is. Dressed figures' materials are called <figure>_<part>, and copies can end in .001."""
    m = ob.data.materials[0]
    name = m.name.split(".")[0] if m else ""
    return next((s for s in SLOTS if name == s or name.endswith("_" + s)), name)


def by_slot(fig, *names):
    return [o for o in fig[2] if slot(o) in names]


def bsdf(m):
    return next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def tune(m, rough=0.2):
    """The glTF roughness of 0.03 reads as wet glass. Moulded plastic is a touch softer."""
    b = bsdf(m)
    b.inputs["Roughness"].default_value = rough


def recolour(fig, name, slots, hexcol, rough=0.2):
    """Gives these parts one new colour. Each figure gets its own copies of the materials, keeping the moulded detail in their normal maps."""
    for ob in by_slot(fig, *slots):
        m = ob.data.materials[0].copy()
        m.name = f"{name}_{slot(ob)}"
        b = bsdf(m)
        for l in list(b.inputs["Base Color"].links):
            m.node_tree.links.remove(l)
        b.inputs["Base Color"].default_value = (*srgb(hexcol), 1)
        tune(m, rough)
        ob.data.materials[0] = m


def print_on(fig, name, sl, png, base_hex=None):
    """A decal part, like the torso front, shows this image."""
    img = bpy.data.images.load(os.path.join(TEXTURES, png + ".png"), check_existing=True)
    for ob in by_slot(fig, sl):
        m = ob.data.materials[0].copy()
        m.name = f"{name}_{sl}"
        t = m.node_tree
        b = bsdf(m)
        tex = next((n for n in t.nodes if n.type == "TEX_IMAGE" and any(l.to_socket == b.inputs["Base Color"] for l in n.outputs[0].links)), None)
        if not tex:
            tex = t.nodes.new("ShaderNodeTexImage")
            uv = next((n for n in t.nodes if n.type == "UVMAP"), None)
            t.links.new(tex.outputs[0], b.inputs["Base Color"])
        tex.image = img
        tune(m)
        ob.data.materials[0] = m


def dress(fig, name, skin, shirt, pants, face, torso, hand=None, sleeves=None, torso_flip=False, hips=None):
    recolour(fig, name, ("Head",), skin)
    recolour(fig, name, ("Hand_L", "Hand_R"), hand or skin)
    recolour(fig, name, ("Torso_Main", "Torso_Back"), shirt)
    recolour(fig, name, ("Arm_Main_L", "Arm_Main_R"), sleeves or shirt)
    recolour(fig, name, ("Hip_Crotch", "Hip_Front", "Hip_Main"), hips or pants)
    recolour(fig, name, ("Leg_L_Foot", "Leg_L_Front", "Leg_L_Main", "Leg_L_Side", "Leg_R_Foot", "Leg_R_Front", "Leg_R_Main", "Leg_R_Side"), pants)
    print_on(fig, name, "Face", face)
    print_on(fig, name, "Torso_Front", torso)


# ---- Measuring. The rig is at rest while the cast is built, so these world numbers hold for every copy at the origin.
def world_box(meshes):
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    lo, hi = [1e9] * 3, [-1e9] * 3
    for ob in meshes:
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        for v in me.vertices:
            p = ev.matrix_world @ v.co
            for i in range(3):
                lo[i], hi[i] = min(lo[i], p[i]), max(hi[i], p[i])
        ev.to_mesh_clear()
    return Vector(lo), Vector(hi)


base = take("rig_unity", "base")
bpy.context.view_layer.update()
for pb in base[1].pose.bones:
    pb.rotation_mode = "QUATERNION"
    pb.location = (0, 0, 0)
    pb.rotation_quaternion = (1, 0, 0, 0)
if base[1].animation_data:
    base[1].animation_data.action = None
lo, hi = world_box(base[2])
print("figure box", [round(x, 3) for x in lo], [round(x, 3) for x in hi], flush=True)
# Every figure stands with its soles on z = 0
base[0].location = (0, 0, -lo.z)
bpy.context.view_layer.update()
SOLE = -lo.z

h_lo, h_hi = world_box(by_slot(base, "Head"))
t_lo, t_hi = world_box(by_slot(base, "Torso_Main"))
f_lo, f_hi = world_box(by_slot(base, "Face"))
HC = (h_lo + h_hi) / 2
HW = h_hi.x - h_lo.x  # head width, including the slight moulding
HR = HW / 2
TOP = f_hi.z  # top of the head's body, under its stud
print("head", [round(x, 3) for x in h_lo], [round(x, 3) for x in h_hi], "face", [round(x, 3) for x in f_lo], [round(x, 3) for x in f_hi], "torso", [round(x, 3) for x in t_lo], [round(x, 3) for x in t_hi], flush=True)
FACE_Y = f_lo.y  # the frontmost point of the head's body

# ---- Pieces. Each one is built in world space around the resting head or torso, then hangs on a bone.
WHITE = abs_mat("cap white", "f3f3ef", 0.28)
NAVY = abs_mat("shades navy", "131848", 0.08)
GLINT = abs_mat("shades glint", "dfe8ff", 0.2, emit=0.2)
GOLD = abs_mat("chain gold", "e8b830", 0.2, metal=1.0)
SKIN_PARDO = abs_mat("pardo nose", "a8754a", 0.25)
SKIN_ISRAEL = abs_mat("israel nose", "f0cfae", 0.25)


def sweep(name, spine, radii, mats, n=24, flatten_y=1.0):
    """Rings of radius r around a spine of points, closed at the far end."""
    v, f = [], []
    rows = len(spine)
    for i, (c, r) in enumerate(zip(spine, radii)):
        ahead = spine[min(i + 1, rows - 1)] - spine[max(i - 1, 0)]
        z = ahead.normalized()
        x = Vector((1, 0, 0))
        y = z.cross(x).normalized()
        x = y.cross(z).normalized()
        for k in range(n):
            t = 2 * math.pi * k / n
            v.append(c + x * r * math.cos(t) + y * r * math.sin(t) * flatten_y)
    for i in range(rows - 1):
        for k in range(n):
            a, b = i * n + k, i * n + (k + 1) % n
            f.append((a, b, b + n, a + n))
    tip = len(v)
    v.append(spine[-1] + (spine[-1] - spine[-2]) * 0.4)
    for k in range(n):
        a, b = (rows - 1) * n + k, (rows - 1) * n + (k + 1) % n
        f.append((a, b, tip))
    f.append(tuple(reversed(range(n))))
    return mesh_ob(name, v, f, mats, cast)


def cap(name, fig):
    """The floppy Smurf cap: a low round dome whose soft tip folds over and hangs down in front, never a tall point."""
    bottom = HC.z + (TOP - HC.z) * 0.62
    # A Bezier spine: up from the brim, over the top, then hanging forward and a little to one side
    p0 = Vector((HC.x, HC.y, bottom))
    p1 = Vector((HC.x, HC.y + HW * 0.22, bottom + HW * 0.98))
    p2 = Vector((HC.x + HW * 0.22, HC.y - HW * 0.22, bottom + HW * 1.04))
    p3 = Vector((HC.x + HW * 0.72, HC.y - HW * 0.58, bottom + HW * 0.22))
    spine, radii = [], []
    N = 30
    for i in range(N):
        t = i / (N - 1)
        a, b = (1 - t), t
        spine.append(p0 * a ** 3 + p1 * 3 * a * a * b + p2 * 3 * a * b * b + p3 * b ** 3)
        bulge = 1.03 + 0.24 * math.sin(min(t / 0.34, 1) * math.pi)  # the brim hugs the head, then the dome swells
        radii.append(HR * bulge * (1 - t ** 1.7 * 0.93))
    ob = sweep(name + "_cap", spine, radii, [WHITE], n=32)
    return piece(ob, fig[1], "head")


def wrap_y(x, extra=0.0):
    """y of the round head's front surface at x, slightly proud of it."""
    x = x - HC.x
    r = HR * 1.0 + extra
    return HC.y - math.sqrt(max(r * r - x * x, 0.0))


def strip(name, outline, mat, extra=0.006, cols=10, thick=0.004):
    """A patch following the head's curve. outline(u) returns (x, z low, z high) for u from 0 to 1."""
    v, f = [], []
    for i in range(cols + 1):
        x, lo_z, hi_z = outline(i / cols)
        y = wrap_y(x, extra)
        y2 = wrap_y(x, extra - thick)
        v += [(x, y, lo_z), (x, y, hi_z), (x, y2, lo_z), (x, y2, hi_z)]
    for i in range(cols):
        a = i * 4
        f.append((a, a + 4, a + 5, a + 1))
        f.append((a + 2, a + 3, a + 7, a + 6))
        f.append((a + 1, a + 5, a + 7, a + 3))
        f.append((a, a + 2, a + 6, a + 4))
    f.append((0, 1, 3, 2))
    a = cols * 4
    f.append((a, a + 2, a + 3, a + 1))
    return mesh_ob(name, v, f, [mat], cast, smooth=False)


def shades(name, fig):
    """Navy shades that follow the head's curve, with diagonal white glints and thin temples, like the mascot's."""
    ez = HC.z + (TOP - HC.z) * 0.2  # just above eye level, clear of the nose
    w = HR * 0.86
    h = HW * 0.3
    gap = HR * 0.09

    def lens(side):
        def out(u):
            x = HC.x + side * (gap + (w - gap) * u)
            # Flat top with a rounded outer corner. The lower edge rises towards the bridge, so the nose sits under it
            low = h * (0.34 + 0.66 * math.sin(min(u / 0.62, 1) * math.pi / 2)) * (1 - 0.32 * max(u - 0.62, 0) / 0.38)
            top = h * 0.3 - h * 0.14 * max(u - 0.84, 0) / 0.16
            return x, ez - low, ez + top
        return out

    left = strip(name + "_L", lens(1), NAVY, cols=18)
    right = strip(name + "_R", lens(-1), NAVY, cols=18)
    bridge = strip(name + "_B", lambda u: (HC.x - gap * 1.1 + 2 * gap * 1.1 * u, ez + h * 0.1, ez + h * 0.3), NAVY, cols=3)
    pieces = [left, right, bridge]
    for side in (-1, 1):
        # Two thin slanted highlights in the middle of each lens
        for k, (off, tall) in enumerate(((0.42, 0.5), (0.6, 0.3))):
            def glint(u, s=side, o=off, l=tall):
                x = HC.x + s * (gap + (w - gap) * (o + 0.05 * u))
                centre = ez - h * 0.14 + s * h * 0.2 * (u - 0.5)
                return x, centre - h * 0.4 * l, centre + h * 0.4 * l
            pieces.append(strip(f"{name}_g{side}{k}", glint, GLINT, extra=0.0075, cols=2, thick=0.001))
    # Thin temples, flush with the head, from the lens ends back around it
    m_v, m_f = [], []
    start = math.degrees(math.asin(w / HR))
    for side in (-1, 1):
        for t in range(0, 9):
            a = math.radians(start + t * 12)
            x = HC.x + side * HR * 1.005 * math.sin(a)
            y = HC.y - HR * 1.005 * math.cos(a)
            for z in (ez + h * 0.12, ez + h * 0.24):
                m_v.append((x, y, z))
        base_i = len(m_v) - 18
        for t in range(8):
            a = base_i + t * 2
            m_f.append((a, a + 2, a + 3, a + 1))
    pieces.append(mesh_ob(name + "_temples", m_v, m_f, [NAVY], cast, smooth=False))
    # One object, so it can slide as a unit
    me_ob = pieces[0]
    ctx = {"selected_editable_objects": pieces, "active_object": me_ob}
    with bpy.context.temp_override(**ctx):
        bpy.ops.object.join()
    me_ob.name = name + "_shades"
    return piece(me_ob, fig[1], "head")


def nose(name, fig, mat, rad, drop=0.0, out=0.8, stretch=1.0):
    """A rounded nose in the middle of the face."""
    z = HC.z + (TOP - HC.z) * -0.18 + drop
    c = Vector((HC.x, wrap_y(HC.x) - rad * out, z))
    v, f = [], []
    rows, cols = 10, 14
    for i in range(rows + 1):
        a = math.pi * i / rows
        for k in range(cols):
            b = 2 * math.pi * k / cols
            v.append(c + Vector((math.sin(a) * math.cos(b) * rad, math.sin(a) * math.sin(b) * rad, math.cos(a) * rad * stretch)))
    for i in range(rows):
        for k in range(cols):
            p, q = i * cols + k, i * cols + (k + 1) % cols
            f.append((p, p + cols, q + cols, q))
    return piece(mesh_ob(name + "_nose", v, f, [mat], cast), fig[1], "head")


def chain(name, fig):
    """Gold links in a U across the chest and a big round medallion, as on the mascot."""
    # The front panel is flat but leans: y is read from the panel itself at the height of each link
    panel = by_slot(fig, "Torso_Front")[0]
    pts = [panel.matrix_world @ w.co for w in panel.data.vertices]
    bot = min(pts, key=lambda p: p.z)
    top_p = max(pts, key=lambda p: p.z)
    top, low = top_p.z, bot.z
    y_at = lambda z: bot.y + (top_p.y - bot.y) * (z - low) / max(top - low, 1e-6) - 0.003
    width = max(p.x for p in pts) - min(p.x for p in pts)
    v, f = [], []

    def bead(c, r):
        i = len(v)
        rows, cols = 5, 8
        for a in range(rows + 1):
            e = math.pi * a / rows
            for k in range(cols):
                t = 2 * math.pi * k / cols
                v.append((c[0] + r * math.sin(e) * math.cos(t), c[1] + r * 0.7 * math.sin(e) * math.sin(t), c[2] + r * math.cos(e)))
        for a in range(rows):
            for k in range(cols):
                p, q = i + a * cols + k, i + a * cols + (k + 1) % cols
                f.append((p, p + cols, q + cols, q))

    N = 15
    wide = width * 0.36
    z_top = top - HW * 0.03
    depth = (top - low) * 0.4
    for i in range(N):
        u = i / (N - 1) * 2 - 1
        z = z_top - depth * (1 - u * u)
        bead((HC.x + u * wide, y_at(z), z), HW * 0.05 if i % 2 else HW * 0.04)
    # Medallion: a disc with a raised centre
    cz = z_top - depth - HW * 0.14
    rm = HW * 0.17
    fy = y_at(cz)
    for ring_r, dy in ((rm, 0.0), (rm * 0.68, -0.005)):
        i = len(v)
        n = 24
        for k in range(n):
            t = 2 * math.pi * k / n
            v.append((HC.x + ring_r * math.cos(t), fy, cz + ring_r * math.sin(t)))
            v.append((HC.x + ring_r * math.cos(t), fy - 0.008 + dy, cz + ring_r * math.sin(t)))
        for k in range(n):
            a, b = i + k * 2, i + (k + 1) % n * 2
            f.append((a, b, b + 1, a + 1))
        f.append(tuple(i + k * 2 + 1 for k in range(n)))
    ob = mesh_ob(name + "_chain", v, f, [GOLD], cast, smooth=True, sharp_deg=45)
    return piece(ob, fig[1], "spine06")


def hood(name, fig, hexcol):
    """The jumpsuit's hood: a shell over the head's top, sides and back, open at the face, with a stud-free dome."""
    m = abs_mat(name + " hood", hexcol, 0.42)
    v, f = [], []
    rows, cols = 14, 28
    R = HR * 1.2
    cz = HC.z + (TOP - HC.z) * 0.12
    for i in range(rows + 1):
        a = math.pi * 0.86 * i / rows
        for k in range(cols + 1):
            b = math.radians(58 + (360 - 116) * k / cols)  # 0 faces the camera side (-Y); skips the opening
            r = R * math.sin(a) if i else 0.0
            x = math.sin(b) * r
            y = -math.cos(b) * r
            z = cz + math.cos(a) * R * 1.12
            v.append((HC.x + x, HC.y + y + HW * 0.03, z))
    for i in range(rows):
        for k in range(cols):
            p = i * (cols + 1) + k
            f.append((p, p + cols + 1, p + cols + 2, p + 1))
    ob = mesh_ob(name + "_hood", v, f, [m], cast)
    s = ob.modifiers.new("thick", "SOLIDIFY")
    s.thickness = HW * 0.05
    s.offset = -1
    return piece(ob, fig[1], "head")


MASK = flatten("mask", "mask_dali", pf, decimate=0.14, sharp_deg=70, rx=math.pi / 2)  # imported lying on its back, face up


def asset_piece(name, fig, src, width, z_at, y_off=0.0, mats=None, rz=0.0, bone="head", zk=1.0):
    """A copy of a prefab, scaled to a width and centred on the head, bottom at z_at. zk squashes it to fit a LEGO head's proportions."""
    me = src.data.copy()
    me.transform(Matrix.Rotation(rz, 4, "Z"))
    pts = [v.co for v in me.vertices]
    lo_ = Vector(min(p[i] for p in pts) for i in range(3))
    hi_ = Vector(max(p[i] for p in pts) for i in range(3))
    k = width / (hi_.x - lo_.x)
    me.transform(Matrix.Translation(Vector((HC.x, HC.y + y_off, z_at))) @ Matrix.Diagonal((k, k, k * zk, 1)) @ Matrix.Translation(Vector((-(lo_.x + hi_.x) / 2, -(lo_.y + hi_.y) / 2, -lo_.z))))
    if mats:
        me.materials.clear()
        for m in mats:
            me.materials.append(m)
    ob = OB.new(name, me)
    cast.objects.link(ob)
    return piece(ob, fig[1], bone)


# ---- Palette
PARDO_SKIN = "a8754a"
ISRAEL_SKIN = "f0cfae"
FATHER_SKIN = "7c4f2e"
CHILD_SKIN = "85552f"
RED_SUIT = "b5121b"

# ---- The figures. The base stays at the origin, untouched, until they've all been copied from it.
FIGS = {}


def hero(name, *a, **k):
    fig = copy_fig(base, name)
    dress(fig, name, *a, **k)
    # Everyone here wears something on their head, so the stud is pressed flat or it pokes through
    for ob in by_slot(fig, "Head"):
        mw, inv = ob.matrix_world, ob.matrix_world.inverted()
        for v in ob.data.vertices:
            p = mw @ v.co
            if p.z > TOP + 0.002:
                p.z = TOP + 0.002
                v.co = inv @ p
    FIGS[name] = fig
    return fig


def tint_hair(name, fig, hexcol, style):
    """A moulded LEGO hairpiece: one solid shell over the top, sides and back of the head, its front edge at the hairline and a thick rim,
    so nothing shows through. style "swept" lifts a quiff to one side; "curly" gives short tight curls."""
    mat = abs_mat(name + " hair", hexcol, 0.36)
    cols, side_rows, top_rows = 48, 8, 10
    R = HR * 1.07
    front_z = HC.z + (TOP - HC.z) * 0.62  # hairline above the brows
    back_z = HC.z - HR * 0.55  # down to the nape
    shoulder = TOP + HW * 0.04
    crown = shoulder + HW * 0.17

    def bump(theta, z):
        """Extra radius, giving the hair its sculpted shape."""
        if style == "curly":
            return HW * 0.035 * (0.5 + 0.5 * math.sin(theta * 11 + z * 260) * math.cos(theta * 7 - z * 190))
        # Swept: grooves running back, and a quiff at the front swept towards +X
        groove = HW * 0.012 * math.sin(theta * 16 + z * 90)
        d = math.atan2(math.sin(theta - 0.35), math.cos(theta - 0.35))
        quiff = HW * 0.22 * math.exp(-(d / 0.75) ** 2) * max(0.0, (z - front_z) / (crown - front_z)) ** 0.8
        return groove + quiff

    v, f = [], []
    for k in range(cols):
        th = 2 * math.pi * k / cols  # 0 faces the front (-Y)
        hl = front_z + (back_z - front_z) * (1 - math.cos(th)) / 2
        hl -= HR * 0.12 * math.sin(th) ** 2  # over the ears the line dips a little lower
        for r in range(side_rows):
            z = hl + (shoulder - hl) * r / (side_rows - 1)
            rr = R + bump(th, z)
            v.append((HC.x + rr * math.sin(th), HC.y - rr * math.cos(th), z))
        for r in range(1, top_rows):
            a = (math.pi / 2) * r / top_rows
            z = shoulder + (crown - shoulder) * math.sin(a)
            rr = (R + bump(th, z)) * math.cos(a)
            v.append((HC.x + rr * math.sin(th), HC.y - rr * math.cos(th), z))
    per = side_rows + top_rows - 1
    for k in range(cols):
        k2 = (k + 1) % cols
        for r in range(per - 1):
            f.append((k * per + r, k * per + r + 1, k2 * per + r + 1, k2 * per + r))
    pole = len(v)
    v.append((HC.x, HC.y, crown + (HW * 0.04 if style == "curly" else 0.0)))
    for k in range(cols):
        k2 = (k + 1) % cols
        f.append((k * per + per - 1, pole, k2 * per + per - 1))
    ob = mesh_ob(name + "_hair", v, f, [mat], cast)
    s = ob.modifiers.new("thick", "SOLIDIFY")
    s.thickness = HW * 0.07
    s.offset = -1
    s.use_rim = True
    s.use_even_offset = True
    return piece(ob, fig[1], "head")


pardo = hero("pardo", PARDO_SKIN, PARDO_SKIN, "f3f3ef", "face_pardo", "torso_pardo")
cap("pardo", pardo)
shades("pardo", pardo)
PARDO_NOSE = dict(drop=-HW * 0.09, out=0.75)
nose("pardo", pardo, SKIN_PARDO, HW * 0.12, **PARDO_NOSE)
chain("pardo", pardo)

israel = hero("israel", ISRAEL_SKIN, "f4f6f8", "1f62c4", "face_israel", "torso_israel", sleeves="1f62c4")
tint_hair("israel", israel, "e8c547", "swept")
nose("israel", israel, SKIN_ISRAEL, HW * 0.085, drop=-HW * 0.02, out=0.72, stretch=1.25)

MASK_W = HW * 1.32  # its face is concave, so it has to be wider than the head and sit well forward for its surface to clear the head's front
for nm in ("robber1", "robber2", "robber3", "pardo_rob"):
    skin = PARDO_SKIN if nm == "pardo_rob" else "e7bd94"
    fig = hero(nm, skin, RED_SUIT, RED_SUIT, "face_pardo", "torso_robber", hand="26211f")
    asset_piece(nm + "_mask", fig, MASK, MASK_W, h_lo.z - HW * 0.02, y_off=-HW * 0.62, zk=0.6)
    if nm == "pardo_rob":
        cap(nm, fig)
        shades(nm, fig)
        nose(nm, fig, SKIN_PARDO, HW * 0.12, **PARDO_NOSE)
    else:
        hood(nm, fig, RED_SUIT)

father = hero("father", FATHER_SKIN, "7c8691", "6b7480", "face_father", "torso_father")
tint_hair("father", father, "17110d", "curly")
child = hero("child", CHILD_SKIN, "c23a2a", "b7a27a", "face_child", "torso_child")
tint_hair("child", child, "17110d", "curly")

# Kid legs: the leg meshes squash up towards the hips. The bones stay put, so all the same poses work, and the figure just stands lower.
LEG = ("Leg_L_Foot", "Leg_L_Front", "Leg_L_Main", "Leg_L_Side", "Leg_R_Foot", "Leg_R_Front", "Leg_R_Main", "Leg_R_Side")
hip_z = world_box(by_slot(child, *LEG))[1].z  # the top of the legs. The hip's lower parts squash with them, or a post shows between the legs.
LEG_K = 0.52
for ob in by_slot(child, *LEG, "Hip_Crotch", "Hip_Front", "Hip_Main"):
    mw = ob.matrix_world
    inv = mw.inverted()
    for v in ob.data.vertices:
        p = mw @ v.co
        if p.z < hip_z:
            p.z = hip_z - (hip_z - p.z) * LEG_K
            v.co = inv @ p
# Forward-swinging kid feet come from the same bones, so nothing else changes
leg_bottom = world_box(by_slot(child, *LEG))[0].z
child[0]["z0"] = -leg_bottom

# ---- Crowd figures, each from its own import, on the same footing
for name in ("crook", "escapee", "policeman", "banker", "pepper", "brickster", "henchman", "sky", "dewey"):
    fig = take("fig_" + name, name)
    for m in {m for ob in fig[2] for m in ob.data.materials if m}:
        tune(m, 0.22)
    fig[1].animation_data_clear()
    for pb in fig[1].pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.location = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)
    fig[0].location = (0, 0, SOLE)
    FIGS[name] = fig

# The base stays parked for later copies, out of the render
base[0].location = (500, 500, -50)
for ob in [base[1]] + base[2]:
    ob.hide_render = True

for name, (root, arm, meshes) in FIGS.items():
    root.location = (0, 0, SOLE + root.get("z0", 0.0))
    root["z0"] = root.location.z

# The rig's actions came from Unity with the hips offset, so each one sinks the figure by its own amount. This is how much to lift it by:
# the action's lowest point across one pass, read on the base figure while it stands on z = 0.
base[0].location = (0, 0, SOLE)
ground = {}
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import poses_lego as PL; importlib.reload(PL)
for a in bpy.data.actions:
    if not a.name.startswith("U_"):
        continue
    nm = a.name[2:]
    low = 1e9
    for k in range(10):
        PL.apply(base[1], PL.sample(nm, k / 10))
        low = min(low, world_box(base[2])[0].z)
    ground[nm] = round(-low, 4)
PL.clear(base[1])
base[0].location = (500, 500, -50)
json.dump({"names": list(FIGS), "head_width": HW, "ground": ground}, open(os.path.join(WORK, "cast.json"), "w"), indent=0)
print("ground", {k: ground[k] for k in ("Run", "Walk", "Dance", "Wave", "Sleeping", "Laughing", "Idle_Light")}, flush=True)
save()
print("=== CAST DONE", list(FIGS), flush=True)
