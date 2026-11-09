# Step 1: an empty scene saved as blender/lego/lego.blend. Never touches another video's .blend.
#   "$BLENDER" -b --factory-startup -P src/lego/blender/s01_setup.py
import bpy, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from set_lib import BLEND, WORK

os.makedirs(WORK, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.save_as_mainfile(filepath=BLEND)
print("saved", BLEND, flush=True)
os._exit(0)
