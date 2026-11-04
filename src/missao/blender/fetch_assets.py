# Downloads the Sketchfab models into blender/missao/assets/<name>/ with the API key held by the addon.
# Run inside Blender so the key stays in its preferences. It is never printed or written to disk.
# Safe to re-run: models already on disk are skipped.
#   node src/thps/bl.mjs run src/missao/blender/fetch_assets.py
import bpy, os, zipfile, requests

ASSETS = r"C:\Users\lukeg\Projetos\pardingows\blender\missao\assets"
MODELS = {
    "casas1": "b9797c38e4e645b39f0cda8c05bebd5f",
    "casas2": "c87942d7d3ba43648920c7f7cd451afc",
    "rua1": "be4a54f622a14f8b8bb8df70046f1dc1",
    "rua2": "789cd0b9c4644a01adc3ace61573baf1",
    "props": "381b65d98a5b4e3886ac2acace7e5c74",
    "cerca": "57d3e84f276d46c6b4bab1e502d9a4d5",
    "van": "1cac40905d494bae8108a556d870e23e",
    "male": "f9acca1dc1ec411699ffd6337889e058",
    "male2": "67368ece5a8d47e7aeffbe2253f6bdd5",
    "oldman": "dc42fa861cd645f489be5c9b3d2076fb",
    "deadman": "391f58976d4c484e85909d38561005af",
    "colchao": "e914df64a021484a91613b38c28ee538",
    "relogio": "23b2d0e81d414836877c555e5b5fc18d",
    "criado": "df9eb305734b412693c715f94e8878a0",
    "abajur": "17aab30248a34734ae3c64137444aeae",
    "grana": "632cf7dbc59a496283d1a6092dc6f9b0",
    "grana2": "4abdbd60b1cb41a88233d38f878798e3",
    "lixeira": "7d149495e5004301b518ce3bd4895484",
    "sacos": "9e769751ac3a4b6a893a5719349b78ca",
    "lata": "6b691a9cb47249809e52aab5346aa430",
    "bosta": "5b80e6a023fc4ca591f4a9f73eb09a93",
    "poca": "1b6132426e154eec994e3b59c65a2a07",
    "rato": "896e654c7fdc41a78cf554005e3bdfcd",
    "kiosk": "1a322d0c3eb543c3a5f9cea0937684d5",
    "caixa": "87562962d47e48b28cc1b874fa46a47f",
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
