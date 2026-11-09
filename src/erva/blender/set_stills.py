# Step 4 review: one test still per set at the real 9:16 framing (half size), cast placed in it.
#   node src/thps/bl.mjs run src/erva/blender/set_stills.py
# Out: blender/erva/review/04-set-<name>.png. Everyone goes back to the lineup afterwards.
import importlib
import json
import math
import os
import sys
import time

import bpy
from mathutils import Vector

try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    HERE = os.path.join(os.environ.get("ERVA_ROOT", r"E:\Projetos\pardingows"), "src", "erva", "blender")
sys.path.insert(0, HERE)
import set_lib, shots  # noqa: E402
for mod in (set_lib, shots):
    importlib.reload(mod)
from set_lib import REVIEW  # noqa: E402

sc = bpy.context.scene
sc.render.resolution_percentage = 50
times = {}
for name in ("sala", "trevas", "selva", "assombrada"):
    shots.still(name)
    sc.render.filepath = os.path.join(REVIEW, f"04-set-{name}.png")
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    times[name] = round(time.time() - t0, 2)
    set_lib.redraw()
sc.render.resolution_percentage = 100
shots.reset()
print("render seconds at half size:", times)
