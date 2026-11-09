# Rebuilds the scene from the imports, in order, in a Blender with no window. A full build starts from the clean output of s01:
#   "$BLENDER" -b --factory-startup -P src/lego/blender/s01_setup.py
#   "$BLENDER" -b blender/lego/lego.blend -P src/lego/blender/build_all.py -- first_step [last_step]
# Always build this way: the scripts delete and recreate hundreds of objects, which can crash an open viewport mid-redraw.
import bpy, os, sys, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
STEPS = ["s02_import_assets", "s03_cast", "s04_props", "s05_sets", "s06_look", "s07_gags", "s08_shots"]
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
        os._exit(1)
print("=== BUILD DONE", flush=True)
os._exit(0)
