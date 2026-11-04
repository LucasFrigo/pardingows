# Step 3: skater rigs. Each player: root empty (world placement, +X = travel) ->
#   body empty (hip offset) -> armature, and root -> board -> foot targets the leg IK follows.
# Safe to re-run: rebuilds the "rigs" collection and the P2 copy.
import bpy, sys, math, importlib
from mathutils import Matrix, Vector
sys.path.insert(0, r"C:\Users\lukeg\Projetos\pardingows\src\thps\blender")
import lib; importlib.reload(lib)
from lib import BONES, SCALE, Mesh, collection, empty, make_mat

scene = bpy.context.scene
coll = collection("rigs")

def clear_bone_constraints(arm):
    for pb in arm.pose.bones:
        for c in list(pb.constraints):
            pb.constraints.remove(c)

def board_mesh(name, parent, grip, under, wheel, metal):
    # Deck in smurf units: top surface at z=0, long axis X, kicktails at both ends.
    L, W = 2.7, 1.15
    outline = [(-L, -W * 0.55), (-L + 0.7, -W), (L - 0.7, -W), (L, -W * 0.55), (L, W * 0.55), (L - 0.7, W), (-L + 0.7, W), (-L, W * 0.55)]
    m = Mesh()
    m.prism(outline, -0.16, 0.0, 0, 1)
    # the underside gets its own colour so kickflips read
    m.prism([(x * 0.98, y * 0.98) for x, y in outline], -0.2, -0.16, 1)
    for sx in (-1, 1):
        x = sx * 1.55
        m.box((x, 0, -0.32), (0.2, 0.6, 0.12), 3)
        for sy in (-1, 1):
            # wheels turn around Y; built along Y by swapping axes below
            i = len(m.v)
            for side in (-1, 1):
                for k in range(8):
                    a = 2 * math.pi * (k + 0.5) / 8
                    m.v.append((x + 0.42 * math.cos(a), sy * 0.8 + side * 0.2, -0.46 + 0.42 * math.sin(a)))
            m.f.append(tuple(i + k for k in range(8)))
            m.fm.append(2)
            m.f.append(tuple(i + 8 + 7 - k for k in range(8)))
            m.fm.append(2)
            for k in range(8):
                a, b = k, (k + 1) % 8
                m.f.append((i + b, i + a, i + 8 + a, i + 8 + b))
                m.fm.append(2)
    return m.build(name, [grip, under, wheel, metal], parent, coll)

grip = make_mat("board grip", "1c1b22")
under_a = make_mat("board under p1", "e0342b")
under_b = make_mat("board under p2", "2f6fe0")
wheel = make_mat("board wheel", "f2efe2")
metal = make_mat("board truck", "8a8f98")

def build_player(prefix, arm, under):
    root = empty(prefix, None, coll=coll, size=1.0)
    root.scale = (SCALE,) * 3
    board = board_mesh(prefix + "_board", root, grip, under, wheel, metal)
    # deck top sits on top of the wheels: wheel bottom at z=-0.88 -> ground
    board.location = (0, 0, 0.88)
    body = empty(prefix + "_body", root, loc=(0, 0, 0.88), coll=coll)
    arm.parent = body
    arm.matrix_parent_inverse = Matrix.Identity(4)
    arm.location = (0, 0, 1.87)  # the model's own offset: soles land on z=0 of the body empty
    arm.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()

    # The feet follow a stance empty, not the board, so the board can flip under them in a kickflip
    stance = empty(prefix + "_stance", root, loc=(0, 0, 0.88), coll=coll)
    clear_bone_constraints(arm)
    rest = {k: arm.data.bones[v] for k, v in BONES.items()}
    for side, stance_x, stance_y in (("R", 1.05, -0.05), ("L", -1.05, -0.05)):
        # ankle target: on the board, wider than the idle stance
        t = empty(f"{prefix}_ankle{side}", stance, loc=(stance_x, stance_y, 0.52), coll=coll, size=0.2)  # ankle height above the sole
        c = arm.pose.bones[BONES["shin" + side]].constraints.new("IK")
        c.name = "foot"
        c.target = t
        c.chain_count = 2
        for part in ("heel", "toe"):
            # Each foot bone copies an empty holding its rest orientation (yawed to sit square on the deck).
            mat = rest[part + side].matrix_local.to_quaternion()
            e = empty(f"{prefix}_{part}{side}", t, coll=coll, size=0.15)
            yaw = -17 if side == "R" else 17
            e.rotation_mode = "QUATERNION"
            e.rotation_quaternion = Matrix.Rotation(math.radians(yaw), 4, "Z").to_quaternion() @ mat
            pc = arm.pose.bones[BONES[part + side]].constraints.new("COPY_ROTATION")
            pc.name = "foot"
            pc.target = e
    return root

# P1 is the original armature; P2 duplicates it, sharing mesh data
arm1 = bpy.data.objects["Armature"]
for ob in list(bpy.data.objects):
    if ob.name.startswith("P2_"):
        bpy.data.objects.remove(ob, do_unlink=True)

arm1.parent = None
root1 = build_player("P1", arm1, under_a)

arm2 = arm1.copy()
arm2.name = "P2_arm"
coll.objects.link(arm2)
for child in list(arm1.children):
    if child.name.startswith("phone"):  # props on P1's hand aren't part of the body
        continue
    c2 = child.copy()
    c2.name = "P2_torso" if child.name == "body" else "P2_" + child.name  # "P2_body" is the hip empty
    coll.objects.link(c2)
    c2.parent = arm2
    c2.matrix_parent_inverse = child.matrix_parent_inverse  # setting .parent clears it
root2 = build_player("P2", arm2, under_b)
root2.location = (3, 0, 0)

# the "P2" floating marker: two chunky glowing blocks over the head
m = Mesh()
for box in (((-0.6, 0, 0), (0.12, 0.08, 0.5)), ((-0.25, 0, 0.3), (0.3, 0.08, 0.2)), ((0.3, 0, 0.4), (0.3, 0.08, 0.1)),
            ((0.5, 0, 0.1), (0.1, 0.08, 0.2)), ((0.3, 0, -0.05), (0.3, 0.08, 0.1)), ((0.1, 0, -0.3), (0.1, 0.08, 0.2)), ((0.3, 0, -0.45), (0.3, 0.08, 0.1))):
    m.box(*box)
marker = m.build("P2_marker", [make_mat("p2 marker", "2fd0ff", emit=1.5)], bpy.data.objects["P2_body"], coll)
marker.location = (0, 0, 8.6)

# Move the stray copies of the source camera/lights out of the way of later shots
for name in ("Camera", "Sun", "Sun.001", "Empty"):
    ob = bpy.data.objects.get(name)
    if ob:
        ob.hide_render = True
        ob.hide_viewport = True

bpy.ops.wm.save_mainfile()
print("rigs ok:", [o.name for o in coll.objects if o.type == "EMPTY" and "_" not in o.name], "P2 parts", sum(1 for o in bpy.data.objects if o.name.startswith("P2_")))
