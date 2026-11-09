# Renders the video's frames headless: for each frame, shots.apply(f) rebuilds the scene, EEVEE renders it to
# blender/pardao/frames/f_NNNN.png, and the screen positions of the shot's anchors go to frames.json for the 2D effects.
# Poses step at 15 fps, so only odd frames render, plus any frame where a cut or a one-frame gag (muzzle flash) lands.
#   "$BLENDER" -b blender/pardao/pardao.blend -P src/pardao/blender/render_frames.py -- [first last] [--all] [--only f,f,...] [--out dir]
import bpy, json, math, os, sys, time
from bpy_extras.object_utils import world_to_camera_view
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import set_lib, shots
from set_lib import WORK

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
out = os.path.join(WORK, "frames")
if "--out" in argv:
    out = argv[argv.index("--out") + 1]
os.makedirs(out, exist_ok=True)
nums = [int(a) for a in argv if a.isdigit()]
first, last = (nums[0], nums[1]) if len(nums) >= 2 else (1, shots.FRAMES)


def frame_of(t):
    return int(round((t - shots.START) * shots.FPS)) + 1


wanted = set(range(1, shots.FRAMES + 1, 2))
wanted |= {frame_of(c) for c in shots.CUTS}
for k, v in shots.CUE.items():
    if k.startswith(("fire", "impact", "crash", "escuro", "press", "jab", "gameover")) and isinstance(v, (int, float)):
        wanted |= {frame_of(v), frame_of(v) + 1}
if "--all" in argv:
    wanted = set(range(1, shots.FRAMES + 1))
if "--only" in argv:
    wanted = {int(x) for x in argv[argv.index("--only") + 1].split(",")}
todo = sorted(f for f in wanted if first <= f <= last and 1 <= f <= shots.FRAMES)

sc = bpy.context.scene
meta_path = os.path.join(out, "frames.json")
meta = json.load(open(meta_path, encoding="utf8")) if os.path.exists(meta_path) else {}
t0 = time.time()
for n, f in enumerate(todo):
    m = shots.apply(f)
    sc.render.filepath = os.path.join(out, f"f_{f:04d}.png")
    bpy.ops.render.render(write_still=True)
    cam = sc.camera
    pts = {}
    for name, co in shots.anchors().items():
        v = world_to_camera_view(sc, cam, co)
        if v.z > 0:
            pts[name] = [round(v.x, 4), round(1 - v.y, 4), round(v.z, 2)]
    meta[str(f)] = {"moment": m, "pts": pts}
    if n % 20 == 0 or n == len(todo) - 1:
        json.dump(meta, open(meta_path, "w", encoding="utf8"))
        el = time.time() - t0
        print(f"frame {f} ({n + 1}/{len(todo)}) {el:.0f}s elapsed, {el / (n + 1):.2f}s/frame", flush=True)
json.dump(meta, open(meta_path, "w", encoding="utf8"))
print("done", len(todo), "frames")
