# Renders the video's frames headless: for each frame, shots.apply(f) rebuilds the scene, EEVEE renders it to
# blender/erva/frames/f_NNNN.png, and the screen positions of the 2D-effect anchors go to frames.json.
# Animation is on twos, so only every other frame renders, plus each cut's own frame. Frames wholly under the title
# card or the FIM card are skipped: Node draws those.
#   "$BLENDER" -b blender/erva/erva.blend -P src/erva/blender/render_frames.py -- [first last] [--step k] [--res pct]
#                                                                                   [--only f,f] [--out dir]
import json
import os
import sys
import time

import bpy
from bpy_extras.object_utils import world_to_camera_view

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import set_lib, shots  # noqa: E402
from set_lib import WORK  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def opt(name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default


out = opt("--out", os.path.join(WORK, "frames"))
os.makedirs(out, exist_ok=True)
nums = [int(a) for i, a in enumerate(argv) if a.isdigit() and (i == 0 or not argv[i - 1].startswith("--"))]
first, last = (nums[0], nums[1]) if len(nums) >= 2 else (1, shots.FRAMES)
step = int(opt("--step", "2"))
CARDS = json.load(open(os.path.join(shots.ROOT, "src", "erva", "cards.json"), encoding="utf8"))


def frame_of(t):
    return int(round((t - shots.START) * shots.FPS)) + 1


wanted = set(range(1, shots.FRAMES + 1, step))
wanted |= {frame_of(c) for c in shots.CUTS}
covered = set(range(1, frame_of(CARDS["title_until"]))) | set(range(frame_of(CARDS["fim_from"]) + 1, shots.FRAMES + 1))
wanted -= covered
if "--only" in argv:
    wanted = {int(x) for x in opt("--only").split(",")}
todo = sorted(f for f in wanted if first <= f <= last)

sc = bpy.context.scene
sc.render.resolution_percentage = int(opt("--res", "100"))
meta_path = os.path.join(out, "frames.json")
meta = json.load(open(meta_path, encoding="utf8")) if os.path.exists(meta_path) else {}
t0 = time.time()
for n, f in enumerate(todo):
    m = shots.apply(f)
    sc.render.filepath = os.path.join(out, f"f_{f:04d}.png")
    bpy.ops.render.render(write_still=True)
    pts = {}
    for name, co in shots.anchors().items():
        v = world_to_camera_view(sc, sc.camera, co)
        if v.z > 0:
            pts[name] = [round(v.x, 4), round(1 - v.y, 4), round(v.z, 2)]
    meta[str(f)] = {"moment": m, "pts": pts}
    if n % 20 == 0 or n == len(todo) - 1:
        json.dump(meta, open(meta_path, "w", encoding="utf8"))
        el = time.time() - t0
        print(f"frame {f} ({n + 1}/{len(todo)}) {m} {el:.0f}s, {el / (n + 1):.2f}s/frame", flush=True)
json.dump(meta, open(meta_path, "w", encoding="utf8"))
print("done", len(todo), "frames")
