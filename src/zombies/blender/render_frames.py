# Renders frames from the saved file. Run headless, so Blender's window stays free:
#   "$BLENDER" -b blender/zombies/zombies.blend -P src/zombies/blender/render_frames.py -- main|judge|mug [step] [frame,frame,...] [dir]
# Frames Node draws by itself are skipped. Finished frames are skipped unless a frame list is given, so a retry after a crash resumes.
import bpy, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from set_lib import ROOT, WORK

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
kind = args[0] if args else "main"
step = int(args[1]) if len(args) > 1 and args[1] else 1
only = {int(x) for x in args[2].split(",")} if len(args) > 2 and args[2] not in ("", "-") else None
out = args[3] if len(args) > 3 and args[3] not in ("", "-") else os.path.join(WORK, "frames", kind)
TL = json.load(open(os.path.join(ROOT, "src", "zombies", "timeline.json"), encoding="utf8"))
FPS = TL["fps"]

if kind == "main":
    starts = [(max(0, round((l["words"][0][1] - TL["start"]) * FPS)), l["shot"]) for l in TL["lines"]]
    skip = set()
    for i, (a, name) in enumerate(starts):
        z = starts[i + 1][0] if i + 1 < len(starts) else TL["song_frames"]
        if name in TL["node_only"]:
            skip |= set(range(a + 1, z + 1))
    frames = [f for f in range(1, TL["song_frames"] + 1) if f not in skip]
elif kind == "judge":
    frames = list(range(TL["judge_first"], TL["judge_first"] + TL["judge_frames"]))
else:
    frames = list(range(TL["mug_first"], TL["mug_first"] + len(TL["mugs"])))

os.makedirs(out, exist_ok=True)
sc = bpy.context.scene
r = sc.render
r.image_settings.file_format = "PNG"
r.image_settings.color_mode = "RGB"
t0 = time.time()
done = 0
for k, f in enumerate(frames):
    if only is not None:
        if f not in only:
            continue
    elif step > 1 and k % step:
        continue
    path = os.path.join(out, f"f_{f:04d}.png")
    if only is None and os.path.exists(path):
        continue
    sc.frame_set(f)
    r.filepath = path
    bpy.ops.render.render(write_still=True)
    done += 1
    if done % 20 == 0:
        print(f"progress {done} frames, {(time.time() - t0) / done:.2f}s each, at f{f}", flush=True)
print(f"done {done} frames in {time.time() - t0:.0f}s", flush=True)
sys.stdout.flush()
os._exit(0)
