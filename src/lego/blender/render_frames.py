# Renders the frames listed in blender/lego/frames.json, switching on each frame's world. Run headless:
#   "$BLENDER" -b blender/lego/lego.blend -P src/lego/blender/render_frames.py -- [engine] [res] [samples] [dir] [frame,frame,...]
# Finished frames are skipped unless a frame list is given, so a retry after a crash resumes. Frames are f_0001.png ... f_0922.png.
import bpy, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import look_lib
from set_lib import WORK

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
engine = args[0] if len(args) > 0 and args[0] else "CYCLES"
res = float(args[1]) if len(args) > 1 and args[1] else 1.0
samples = int(args[2]) if len(args) > 2 and args[2] else None
out = os.path.abspath(args[3]) if len(args) > 3 and args[3] not in ("", "-") else os.path.join(WORK, "frames")  # Blender's render path doesn't follow the shell's working folder
only = {int(x) for x in args[4].split(",")} if len(args) > 4 else None

plan = json.load(open(os.path.join(WORK, "frames.json")))
os.makedirs(out, exist_ok=True)
sc = bpy.context.scene
print("engine", engine, look_lib.engine(engine, samples, res), flush=True)
t0 = time.time()
done = 0
current = None
for f in plan["frames"]:
    if only is not None and f not in only:
        continue
    path = os.path.join(out, f"f_{f:04d}.png")
    if only is None and os.path.exists(path):
        continue
    world = plan["world"][str(f)]
    if world != current:
        look_lib.activate(world)
        current = world
    sc.frame_set(f)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    done += 1
    if done % 20 == 0:
        print(f"progress {done} frames, {(time.time() - t0) / done:.2f}s each, at f{f}", flush=True)
print(f"done {done} frames in {time.time() - t0:.0f}s", flush=True)
sys.stdout.flush()
os._exit(0)
