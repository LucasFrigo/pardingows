# Downloads the Sketchfab models into blender/zombies/assets/<name>/ with the API key held by the addon, and writes CREDITS.txt.
# Run inside the open Blender so the key stays in its preferences. It is never printed or written to disk.
# Safe to re-run: models already on disk are skipped. It stops after a time budget, so a long download can't hold Blender past bl.mjs's timeout:
# run it again while it prints a non-empty "left:" list.
#   node src/thps/bl.mjs run src/zombies/blender/fetch_assets.py
# bl.mjs executes this text without __file__, so the repo root comes from ZOMBIES_ROOT or the path below.
import bpy, os, time, zipfile, requests

ROOT = os.environ.get("ZOMBIES_ROOT", r"C:\Users\lukeg\Projetos\pardingows")
ASSETS = os.path.join(ROOT, "blender", "zombies", "assets")
os.makedirs(ASSETS, exist_ok=True)
BUDGET_S = 420

MODELS = {
    "zumbi_psx": "e5780c5c161c461783d978aee98a865b",
    "zumbi_cyber": "a972e941ea554773bf3b00b82c090f4f",
    "zumbi_real": "0541416bd635486f95cb3d44f8f676c1",
    "rastejante": "92e32f2303fa4a339590c243fd6c505a",
    "zumbi_f": "5990107ff5da4d2ab8a7024f2664f564",
    "cao": "a0570f82ac974a6bb3214364b0e2b16d",
    "barata": "4b19ed8851f74c278eef835250a82896",
    "esqueleto": "0559c4623da344df9755a2ded991e540",
    "corredor": "30f359fcea3d4b498b179cd8ba9201ea",
    "parede": "0aaf61c5dc5d4008befa851e7971cdee",
    "retrato": "d794819d83594c4eb069ca31d4f214b4",
    "hall": "9d57979efd8d43fc970388e50dc7adc0",
    "moveis": "452c8783fd96456387f9f84fe8d05b94",
    "lustre": "e7a99b9024904ce3ac60c8831acd0418",
    "janela": "b08907202ad54cc982cbc111da27f37c",
    "estante": "bf8be00f3d344ebdafd701fb90d65497",
    "relogio": "6ede129be11e43cea5c279e34a7eddaa",
    "vela": "9debe7915b8740bb83f4493c0d9a5f51",
    "candelabro": "89f71a03a338491c92ada680e6f51749",
    "teias": "2dd4798676d84bc7af5d2a8f5834563a",
    "mural": "92c8eed11d404a01b0ca2237919c79c6",
    "caixa": "2f0af73d6d734669b486b9d8a90cf23e",
    "plantas": "2c6fea8bd48944389ae6d1f22b391f3e",
    "portas": "16dd7631d2e145ffacfc374961d71cf1",
    "cela": "10838c04681e460183338685944a4bc0",
    "grades": "410e6acfc4c448d3835929e1b6d6df3a",
    "tocha": "156b8eca745549ee951abd8aa58f2d3f",
    "ruina": "9fdc8d1f23a249768c377db0dfcaf42c",
    "ruina2": "b6a7905251f54a419232ae44c5117517",
    "rua": "381b65d98a5b4e3886ac2acace7e5c74",
    "viatura": "3000906db39245ff8e519f85a50a8403",
    "semaforo": "1d7ac82702484f979b37bfa896983bbc",
    "poste": "81a8d1861bbd4cef8ab1aed2986bf873",
    "barreira": "89a79068de614a478aeaea49371cfef8",
    "helicoptero": "5bbed2de9baa4a13a7faa72653b78b64",
    "fita": "83351a4cd72346ccad6792dfde46d22e",
    "pistola": "6640a5fd40b4456c94578b015264e305",
    "seringa": "1de7893db91c4cf8822ff10ee999cd67",
    "cola": "39207e87ba90446fa0e3c40a93148efa",
    "pomba": "79de3c5b47f24376a5694029b1693088",
}
addons = bpy.context.preferences.addons
addon = next((a for k, a in addons.items() if k.endswith("blender_mcp")), None)  # an extension registers as bl_ext.<repo>.blender_mcp
key = addon.preferences.sketchfab_api_key if addon else None
if not key:
    raise RuntimeError("no Sketchfab key in the addon preferences")

NOT_SHOWN = {"rastejante", "candelabro", "vela", "parede", "mural", "plantas", "cela", "seringa"}  # downloaded but never placed in the video, so they aren't credited
credits = ["Modelos 3D do video PARDOS vs ZOMBIES. Licence and author from the public Sketchfab API, so the credit must appear wherever the video is shared.", "",
           "Paste into the video description:", ""]
t0 = time.time()
failed, left = [], []
for name, uid in MODELS.items():
    meta = requests.get(f"https://api.sketchfab.com/v3/models/{uid}", timeout=30).json()
    lic = meta.get("license", {})
    user = meta.get("user", {})
    if name not in NOT_SHOWN:
        credits.append(f"This work is based on \"{meta.get('name')}\" ({meta.get('viewerUrl')}) by {user.get('displayName') or user.get('username')} ({user.get('profileUrl')}) licensed under {lic.get('label')}")
    folder = os.path.join(ASSETS, name)
    gltf = os.path.join(folder, "gltf")
    if os.path.exists(os.path.join(gltf, "scene.gltf")):
        print(name, "already here")
        continue
    if time.time() - t0 > BUDGET_S:
        left.append(name)
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

credits += ["", "Not credit lines, but check before publishing:",
            "Smurf base model: by grishamanimation1, repainted, shades and chain added. Licence terms not verified (see blender/solucao).",
            "Resident Evil: only the style is referenced. No Capcom logos, characters or art are used, but a complaint can't be ruled out.",
            "Font: VT323, SIL Open Font License, src/zombies/fonts/OFL.txt."]
with open(os.path.join(ASSETS, "CREDITS.txt"), "w", encoding="utf8") as f:
    f.write("\n".join(credits) + "\n")
print("failed:", failed)
print("left:", left)
