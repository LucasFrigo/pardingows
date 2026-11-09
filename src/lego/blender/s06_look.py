# Step 6: render settings and the sky. Each world's sky is set when its shot comes up, see world_data.SKY and look_lib.
import bpy, os, sys, importlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import set_lib, look_lib, world_data
importlib.reload(set_lib); importlib.reload(look_lib); importlib.reload(world_data)
from set_lib import save

look_lib.world("rua")
look_lib.engine("CYCLES")
save()
print("look ok", flush=True)
