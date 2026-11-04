# Step 1: saves the open blank project as missao.blend and appends both smurf rigs from solucao.blend.
# solucao.blend is only read. Refuses to run on any file other than a blank project or missao.blend.
# P1 runs in the RUN scene, P2 is the same hero acting in the STORY scene, since one object can only hold one pose per frame.
#   node src/thps/bl.mjs run src/missao/blender/s01_setup.py
import bpy, os

ROOT = r"C:\Users\lukeg\Projetos\pardingows"
WORK = os.path.join(ROOT, "blender", "missao")
BLEND = os.path.join(WORK, "missao.blend")
SRC = os.path.join(ROOT, "blender", "solucao", "solucao.blend")
for d in ("textures", "assets", "frames", "review"):
    os.makedirs(os.path.join(WORK, d), exist_ok=True)

if bpy.data.filepath and os.path.normcase(bpy.data.filepath) != os.path.normcase(BLEND):
    raise RuntimeError("open file is " + bpy.data.filepath + ", expected a blank project or missao.blend")
if not bpy.data.filepath and bpy.data.is_dirty:
    raise RuntimeError("the open blank project has unsaved changes")
if not bpy.data.filepath and {o.name for o in bpy.data.objects} - {"Camera", "Cube", "Light"}:
    raise RuntimeError("blank project has objects of its own: " + str([o.name for o in bpy.data.objects]))
if "P1" in bpy.data.objects:
    raise RuntimeError("rigs already appended")

for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)
for c in list(bpy.context.scene.collection.children):
    bpy.context.scene.collection.children.unlink(c)
    bpy.data.collections.remove(c)
bpy.ops.wm.save_as_mainfile(filepath=BLEND, relative_remap=True)

with bpy.data.libraries.load(SRC, link=False) as (src, dst):
    dst.collections = [c for c in src.collections if c in ("Collection", "rigs")]
    dst.objects = ["shades", "chain", "medallion"]  # these sit directly in the scene there, outside any collection
for c in dst.collections:
    bpy.context.scene.collection.children.link(c)
bpy.data.collections["Collection"].name = "smurf"
for ob in dst.objects:
    bpy.data.collections["rigs"].objects.link(ob)

# He keeps the hat here. Boards, phones and the stray camera and lights go.
DROP = ("phone", "P1_board", "P2_board", "Camera", "Sun", "Empty", "P2_marker")
for ob in list(bpy.data.objects):
    if ob.name.startswith(DROP):
        bpy.data.objects.remove(ob, do_unlink=True)

for ob in bpy.data.objects:
    if ob.animation_data:
        ob.animation_data_clear()
    if ob.type == "ARMATURE":
        ob.data.pose_position = "POSE"
        for pb in ob.pose.bones:
            pb.matrix_basis.identity()
            for c in pb.constraints:
                if c.name == "foot":
                    c.influence = 0.0
bpy.data.orphans_purge(do_recursive=True)

missing = [i.name for i in bpy.data.images if i.source == "FILE" and not i.packed_file and not os.path.exists(bpy.path.abspath(i.filepath))]
bpy.ops.wm.save_mainfile()
print("saved", bpy.data.filepath)
print("collections", [c.name for c in bpy.context.scene.collection.children])
print("objects", len(bpy.data.objects), sorted(o.name for o in bpy.data.objects if not o.parent))
print("all", sorted(o.name for o in bpy.data.objects))
print("images", len(bpy.data.images), "missing", missing)
print("materials", sorted(m.name for m in bpy.data.materials))
