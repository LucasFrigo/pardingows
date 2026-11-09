# Rebuilds the scene from the imports, in order, in a Blender with no window. A full build starts from the clean output of s01:
#   "$BLENDER" -b blender/zombies/zombies_base.blend -P src/zombies/blender/build_all.py
# or, to redo the later steps on the current build:
#   "$BLENDER" -b blender/zombies/zombies.blend -P src/zombies/blender/build_all.py -- first_step [last_step]
# Always build this way: the scripts delete and recreate hundreds of objects, which can crash an open viewport mid-redraw.
import bpy, os, sys, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(bpy.data.filepath) == "zombies_base.blend":
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.dirname(bpy.data.filepath), "zombies.blend"), relative_remap=True)
STEPS = [s[:-3] for s in sorted(os.listdir(HERE)) if s[0] == "s" and s[1:3].isdigit() and s.endswith(".py") and not s.startswith("s01")]
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
first = STEPS.index(args[0]) if args else 0
last = STEPS.index(args[1]) if len(args) > 1 else len(STEPS) - 1

for step in STEPS[first:last + 1]:
    path = os.path.join(HERE, step + ".py")
    print("=== BUILD", step, flush=True)
    try:
        exec(compile(open(path, encoding="utf8").read(), path, "exec"), {"__name__": "__main__", "__file__": path})
    except Exception:
        traceback.print_exc()
        print("=== BUILD FAILED", step, flush=True)
        sys.stdout.flush()
        os._exit(1)
print("=== BUILD DONE", flush=True)
sys.stdout.flush()
os._exit(0)
