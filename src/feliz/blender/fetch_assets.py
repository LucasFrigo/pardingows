# Downloads the Sketchfab models into blender/feliz/assets/<name>/ with the API key held by the addon, and writes CREDITS.txt.
# Run inside the open Blender so the key stays in its preferences. It is never printed or written to disk.
# Safe to re-run: models already on disk are skipped.
#   node src/thps/bl.mjs run src/feliz/blender/fetch_assets.py
# bl.mjs executes this text without __file__, so the repo root comes from the REPO path below or FELIZ_ROOT.
import bpy, json, os, zipfile, requests

ROOT = os.environ.get("FELIZ_ROOT", r"E:\Projetos\pardingows")
ASSETS = os.path.join(ROOT, "blender", "feliz", "assets")
os.makedirs(ASSETS, exist_ok=True)

MODELS = {
    "arvore": "2ed2a55eebbb4b4fb60484390f611d20",
    "arvore2": "dde49eebec874267b52e53404655f9ca",
    "coqueiro": "d141941578044b0f861ca83b36d4c411",
    "casa": "68fd7b3b59d8441e82e64960620ac0e2",
    "casa2": "45a28a49e57e496e8b91d6de5c0ac88a",
    "casa3": "745f09c22e8943b3bcc5fa47e0aea6ec",
    "flor": "58ce34c65642408cb92eab784af2bd6c",
    "bambu": "d0d5eb345ff7420bb7f5c5239fcec637",
    "lirio": "04dd636204cd4b0db45a4fc82efa4385",
    "lotus": "12768caa111f446b8796e70f9cc53a23",
    "cerca": "9d8ce953d9414a07b974af8629dda93a",
    "poste": "6f257cdc33e6470a836892cb7fa6a47f",
    "banco": "e53ad46c604c44e59a98bad27041cb19",
    "mesa": "fe35acda3a5245da8459d1a062e28190",
    "correio": "52cd14f6b8f54bb6bb26d728c02fd9e2",
    "maca": "0176be079c2449e7aaebfb652910a854",
    "gato": "b2bd1ee7858444bda366110a2d960386",
    "pato": "613776d688764d0aaa615d1c84379733",
    "cachorro": "5be9012283c340de8d48a59bcfa0a39b",
    "guaxinim": "2b3b6a5abe784dfe816fec5bf62542c2",
    "abelha": "76801d3aea024063bc5d91e4ee355508",
    "celular": "4ff99cf17b164e7b9790638c5d2ef4ce",
    "aero": "23ad9c70727c4edeabbf7208b7c3511c",
    "koi": "236859b809984f52b70c94fd040b9c59",
    "golfinho": "f4abb460956240f98b7a6f19cc3037a1",
    "borboleta": "0f24b085e8654e4db09c2fe681a79e3f",
    "ilha": "b9a708aa70424f0699e9c4e3b5b5700a",
    "balao": "a420e9196b744919806ae532b3a11bf7",
}
addons = bpy.context.preferences.addons
addon = next((a for k, a in addons.items() if k.endswith("blender_mcp")), None)  # an extension registers as bl_ext.<repo>.blender_mcp
key = addon.preferences.sketchfab_api_key if addon else None
if not key:
    raise RuntimeError("no Sketchfab key in the addon preferences")

NOT_SHOWN = {"bambu", "maca", "borboleta"}  # downloaded but never placed in the video, so they aren't credited
credits = ["PARDOS FELIZ: third-party models. Licence and author from the public Sketchfab API.", ""]
failed = []
for name, uid in MODELS.items():
    meta = requests.get(f"https://api.sketchfab.com/v3/models/{uid}", timeout=30).json()
    if name not in NOT_SHOWN:
        credits.append(f"{name}: \"{meta.get('name')}\" by {meta.get('user', {}).get('username')}, {meta.get('license', {}).get('label')}, https://sketchfab.com/3d-models/{uid}")
    folder = os.path.join(ASSETS, name)
    gltf = os.path.join(folder, "gltf")
    if os.path.exists(os.path.join(gltf, "scene.gltf")):
        print(name, "already here")
        continue
    os.makedirs(folder, exist_ok=True)
    r = requests.get(f"https://api.sketchfab.com/v3/models/{uid}/download", headers={"Authorization": f"Token {key}"}, timeout=30)
    if r.status_code != 200:
        print(name, "download request failed:", r.status_code)
        failed.append(name)
        continue
    # The signed file URL takes no auth header
    z = requests.get(r.json()["gltf"]["url"], timeout=180)
    path = os.path.join(folder, name + ".zip")
    with open(path, "wb") as f:
        f.write(z.content)
    with zipfile.ZipFile(path) as zf:
        root = os.path.abspath(gltf)
        bad = [n for n in zf.namelist() if not os.path.abspath(os.path.join(root, n)).startswith(root + os.sep)]
        if bad:
            print(name, "unsafe paths in zip, not extracted:", bad[:3])
            failed.append(name)
            continue
        zf.extractall(gltf)
    print(name, f"{len(z.content) // 1024} KB")

credits += ["", "The pardo and Berg bodies are the rigged smurf from blender/solucao (see that folder's CREDITS.txt: the smurf model's licence is unverified).",
            "Font: Fredoka, SIL Open Font License, src/feliz/fonts/OFL.txt."]
with open(os.path.join(ASSETS, "CREDITS.txt"), "w", encoding="utf8") as f:
    f.write("\n".join(credits) + "\n")
print("failed:", failed)
