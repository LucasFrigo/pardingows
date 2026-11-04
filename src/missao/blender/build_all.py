# Rebuilds the whole scene from the imports, in order, in a Blender with no window:
#   blender.exe -b blender/missao/missao.blend -P src/missao/blender/build_all.py
# Always build this way. The scripts delete and recreate hundreds of objects, which can crash an open viewport mid-redraw.
# An open Blender keeps showing the old file until it's reloaded, and saving from it would overwrite this build.
import os, traceback

HERE = r"C:\Users\lukeg\Projetos\pardingows\src\missao\blender"
STEPS = ("s02_import_assets", "s03_cast", "s04_props", "s05_street", "s07_story_sets", "s06_look", "s08_shots")

for step in STEPS:
    path = os.path.join(HERE, step + ".py")
    print("=== BUILD", step, flush=True)
    try:
        exec(compile(open(path, encoding="utf8").read(), path, "exec"), {"__name__": "__main__", "__file__": path})
    except Exception:
        traceback.print_exc()
        print("=== BUILD FAILED", step, flush=True)
        os._exit(1)
print("=== BUILD DONE", flush=True)
