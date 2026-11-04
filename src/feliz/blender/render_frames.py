# Renders frames from the saved file. Run headless, so Blender's window stays free:
#   "$BLENDER" -b blender/feliz/feliz.blend -P src/feliz/blender/render_frames.py -- [step] [frame,frame,...] [dir] [samples]
# Finished frames are skipped unless a frame list is given, so a retry after a crash resumes. Frames are f_0001.png to f_0691.png.
import bpy, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import set_lib
from set_lib import TL, WORK

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
step = int(args[0]) if len(args) > 0 and args[0] else 1
only = {int(x) for x in args[1].split(",")} if len(args) > 1 and args[1] not in ("", "-") else None
out = args[2] if len(args) > 2 and args[2] not in ("", "-") else os.path.join(WORK, "frames")
samples = int(args[3]) if len(args) > 3 else None

os.makedirs(out, exist_ok=True)
sc = bpy.context.scene
r = sc.render
if samples:
    sc.eevee.taa_render_samples = samples
r.image_settings.file_format = "PNG"
r.image_settings.color_mode = "RGB"
t0 = time.time()
done = 0
for f in range(1, TL["frames"] + 1):
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
    bpy.ops.render.render(write_still=True)
    done += 1
    if done % 20 == 0:
        print(f"progress {done} frames, {(time.time() - t0) / done:.2f}s each, at f{f}", flush=True)
print(f"done {done} frames in {time.time() - t0:.0f}s", flush=True)
