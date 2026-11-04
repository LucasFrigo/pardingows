# Renders one frame sequence from the saved file. Run headless, so Blender's window stays free:
#   blender.exe -b blender/missao/missao.blend -P src/missao/blender/render_frames.py -- story|run|end [step] [frame,frame,...]
# A frame list renders just those frames, replacing any already on disk, for checking a few shots.
# story and run are 270x240 up to the merge frame. end is 270x480 from the frame after it, using the STORY scene.
import bpy, json, os, sys

args = sys.argv[sys.argv.index("--") + 1:]
kind = args[0]
step = int(args[1]) if len(args) > 1 else 1
only = {int(x) for x in args[2].split(",")} if len(args) > 2 else None
ROOT = r"C:\Users\lukeg\Projetos\pardingows"
TL = json.load(open(os.path.join(ROOT, "src", "missao", "timeline.json"), encoding="utf8"))

sc = bpy.data.scenes["RUN" if kind == "run" else "STORY"]
bpy.context.window.scene = sc
r = sc.render
if kind == "end":
    r.resolution_x, r.resolution_y = 270, 480
    start, stop = TL["merge_frame"] + 1, TL["frames"]
else:
    r.resolution_x, r.resolution_y = 270, 240
    start, stop = 1, TL["merge_frame"]
out = os.path.join(ROOT, "blender", "missao", "frames", kind)
os.makedirs(out, exist_ok=True)
r.image_settings.file_format = "PNG"
r.image_settings.color_mode = "RGB"
for f in range(start, stop + 1):
    if only is not None:
        if f not in only:
            continue
    elif step > 1 and (f - 1) % step:
        continue
    path = os.path.join(out, f"f_{f:04d}.png")
    if only is None and os.path.exists(path):
        continue
    sc.frame_set(f)
    r.filepath = path
    bpy.ops.render.render(write_still=True, scene=sc.name)
print("done", kind)
