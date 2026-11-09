# Step 1: saves the open blank project as blender/pardao/pardao.blend and appends the rigged pardo from solucao.blend. solucao.blend is only read.
# Refuses to run on any open file other than a blank project or pardao.blend. Meant for the open window, so the user sees the build:
#   node src/thps/bl.mjs run src/pardao/blender/s01_setup.py        (or headless: "$BLENDER" -b -P src/pardao/blender/s01_setup.py)
import bpy, os, shutil, sys
try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    HERE = os.path.join(os.environ.get("PARDAO_ROOT", r"E:\Projetos\pardingows"), "src", "pardao", "blender")
sys.path.insert(0, HERE)
import importlib, set_lib
importlib.reload(set_lib)
from set_lib import ROOT, WORK, BLEND, SOLUCAO

for d in ("textures", "assets", "frames", "review"):
    os.makedirs(os.path.join(WORK, d), exist_ok=True)

if bpy.data.filepath and os.path.normcase(bpy.data.filepath) != os.path.normcase(BLEND):
    raise RuntimeError("open file is " + bpy.data.filepath + ", expected a blank project or pardao.blend")
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

with bpy.data.libraries.load(SOLUCAO, link=False) as (src, dst):
    dst.collections = [c for c in src.collections if c in ("Collection", "rigs")]
    dst.objects = ["shades", "chain", "medallion"]  # these sit directly in the scene there, outside any collection
for c in dst.collections:
    bpy.context.scene.collection.children.link(c)
bpy.data.collections["Collection"].name = "smurf"
for ob in dst.objects:
    bpy.data.collections["rigs"].objects.link(ob)

# He keeps the hat. Boards, phones and the stray camera and lights go.
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

# The textures stay in solucao's tracked folder. Appending can leave paths relative to the wrong file, so they are pointed there outright.
TEX = os.path.join(ROOT, "blender", "solucao", "textures")
for im in bpy.data.images:
    if im.source == "FILE" and not im.packed_file:
        p = os.path.join(TEX, os.path.basename(bpy.path.abspath(im.filepath).replace("\\", "/")))
        if os.path.exists(p):
            im.filepath = bpy.path.relpath(p)
            im.reload()

# Frame the pair in the open window
if not bpy.app.background:
    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            for sp in area.spaces:
                if sp.type == "VIEW_3D":
                    sp.shading.type = "MATERIAL"
            with bpy.context.temp_override(area=area, region=next(r for r in area.regions if r.type == "WINDOW")):
                bpy.ops.view3d.view_all()
set_lib.save()
shutil.copyfile(BLEND, os.path.join(WORK, "pardao_base.blend"))  # build_all.py starts every full rebuild from this clean copy

missing = [i.name for i in bpy.data.images if i.source == "FILE" and not i.packed_file and not os.path.exists(bpy.path.abspath(i.filepath))]
print("saved", bpy.data.filepath)
print("collections", [c.name for c in bpy.context.scene.collection.children])
for ob in sorted(bpy.data.objects, key=lambda o: o.name):
    par = ob.parent.name if ob.parent else "-"
    extra = ""
    if ob.type == "MESH":
        extra = f"{len(ob.data.polygons)}p {ob.parent_type}:{ob.parent_bone} mats={[m.name for m in ob.data.materials if m]}"
    print(f"  {ob.name:18} {ob.type:9} parent={par:12} {extra}")
print("images", len(bpy.data.images), "missing", missing)
