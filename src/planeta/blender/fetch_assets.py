# Downloads the Sketchfab models into blender/planeta/assets/<name>/ with the API key held by the addon.
# Run inside Blender so the key stays in its preferences. It is never printed or written to disk.
# Safe to re-run: models already on disk are skipped.
#   node src/thps/bl.mjs run src/planeta/blender/fetch_assets.py
import bpy, os, zipfile, requests

ASSETS = r"C:\Users\lukeg\Projetos\pardingows\blender\planeta\assets"
MODELS = {
    "cesar": "c69010aa3f954c7c8886de9dff38c307",
    "chimp": "c6d7980561064358ba2d122cbda877de",
    "sky": "a4a10124f767413892e6ff5340b5daf4",
    "asteroids": "994740be63754d76ad4988f05f9cd6f1",
    "lander": "bc9a0f58bd35480eb0cbf39167789042",
    "module": "5906dfa74d3242989350970240510702",
    "moonbase": "6924b0add16841c4b94f699494a758aa",
    "poles": "05dd24f8d3db4f7f8e61a660197f3030",
    "pistol": "aba9ad7845fe4b4f9c8b67805a6c1eda",
    "boxes": "a2b900c7598440ed875cc1413039acad",
}
key = bpy.context.preferences.addons["blender_mcp"].preferences.sketchfab_api_key
if not key:
    raise RuntimeError("no Sketchfab key in the addon preferences")

for name, uid in MODELS.items():
    folder = os.path.join(ASSETS, name)
    gltf = os.path.join(folder, "gltf")
    if os.path.exists(os.path.join(gltf, "scene.gltf")):
        print(name, "already here")
        continue
    os.makedirs(folder, exist_ok=True)
    r = requests.get(f"https://api.sketchfab.com/v3/models/{uid}/download", headers={"Authorization": f"Token {key}"}, timeout=30)
    if r.status_code != 200:
        print(name, "download request failed:", r.status_code)
        continue
    # The signed file URL takes no auth header
    z = requests.get(r.json()["gltf"]["url"], timeout=120)
    path = os.path.join(folder, name + ".zip")
    with open(path, "wb") as f:
        f.write(z.content)
    with zipfile.ZipFile(path) as zf:
        root = os.path.abspath(gltf)
        bad = [n for n in zf.namelist() if not os.path.abspath(os.path.join(root, n)).startswith(root + os.sep)]
        if bad:
            print(name, "unsafe paths in zip, not extracted:", bad[:3])
            continue
        zf.extractall(gltf)
    kinds = sorted({os.path.splitext(n)[1].lower() for n in zf.namelist()})
    print(name, f"{len(z.content) // 1024} KB", kinds)
