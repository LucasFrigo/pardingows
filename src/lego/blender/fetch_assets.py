# Downloads the Sketchfab models into blender/lego/assets/<name>/ with the API key held by the addon, and writes CREDITS.txt.
# Run inside the open Blender so the key stays in its preferences. It is never printed or written to disk.
# Safe to re-run: models already on disk are skipped. It stops after a time budget, so a long download can't hold Blender past bl.mjs's timeout:
# run it again while it prints a non-empty "left:" list.
#   node src/thps/bl.mjs run src/lego/blender/fetch_assets.py
# bl.mjs executes this text without __file__, so the repo root comes from LEGO_ROOT or the path below.
import bpy, os, time, zipfile, requests

ROOT = os.environ.get("LEGO_ROOT", r"E:\Projetos\pardingows")
ASSETS = os.path.join(ROOT, "blender", "lego", "assets")
os.makedirs(ASSETS, exist_ok=True)
BUDGET_S = 420

MODELS = {
    "rig_unity": "7e457f008932400d879504a8924fa3cf",
    "fig_crook": "d98f8361b4314af286e6ae3742401570",
    "fig_escapee": "65f5df1e7c9a4cfe8e6bbe63ef880922",
    "fig_policeman": "9c8fa7f144d747dab1a1602b13431f05",
    "fig_banker": "0393881e3e3a4883b6f572fff5149ecb",
    "fig_pepper": "cbd0649a27664f17bf88d125fded129a",
    "fig_brickster": "fcf25fb9770144e59d5f13d72db2d732",
    "fig_henchman": "ab23809108d5469883d1ae0e8ff29caf",
    "fig_sky": "f54e5da4640c47ae861cdf1f742ced6f",
    "fig_dewey": "32a249e14f27436780aff34f4b00b499",
    "fig_far": "e7bdf43f03d4412dbc6e98852f5b371a",
    "mask_dali": "85beed593d2c49259c15b56be68e1d5c",
    "hair": "42aa4810ed45460984183273c217654d",
    "cash": "c9a3b36cb53b48cbbb017e551840d724",
    "gold": "0d1ff6b3e6d045cba78889caf7f5bc6e",
    "briefcase": "0f5b865144074c52b1ed04777de980d5",
    "dj": "b7bb537521bd4fa9be15926c24bb4656",
    "joint": "5b7dcea4012d4843a4c2baac027c7e78",
    "clock": "19f68e57f79c40658b1c6bbe434a0386",
    "vault": "af389a721faa4ec49eaec7ec2a215371",
    "house_red": "cc0ac9132a3646da9ba884bf78060c73",
    "house_tall": "2f1fbbffe4f74330a0456b6434520bca",
    "bus": "9fef772cf9a74aeab238828b82d05b29",
    "car_red": "f55e4d6ed9354e3e933a28879153716b",
    "cars": "6b94e5aef92c484d8e55516457325c26",
    "bike": "b535a5a2173c49d592259dac7fc8b516",
    "lamp": "35e80fe8959049e3b7eaf4dcf8da6df8",
    "tree": "842efd6c8eb04449aca12cd599a27af3",
    "stump": "6df6061f989747e1b334276f66c71576",
    "plants": "78c18640757f4f16a316c76bc9ea8544",
    "bush": "f3e20f36aa0d4483a960e39cb33e0727",
    "flowers": "d9c5c3c9366f4de0adba13d3ed80de93",
    "sofa": "71f7a1b7b6ec44e7a3714cf3eb43d964",
    "table": "ce218d8147444a3c830e406e4bfb56b3",
}
NOT_SHOWN = {"cars", "house_red", "house_tall", "dj", "briefcase", "table", "hair", "fig_far"}  # downloaded but never placed in the video, so they aren't credited

addons = bpy.context.preferences.addons
addon = next((a for k, a in addons.items() if k.endswith("blender_mcp")), None)  # an extension registers as bl_ext.<repo>.blender_mcp
key = addon.preferences.sketchfab_api_key if addon else None
if not key:
    raise RuntimeError("no Sketchfab key in the addon preferences")

credits = ["3D models in the video PARDOS FELIZ (LEGO). Licence and author from the public Sketchfab API, so the credit must appear wherever the video is shared.", "",
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
            "LEGO is a trademark of the LEGO Group. This is an unofficial fan work: no LEGO logos are used, but a complaint can't be ruled out.",
            "Some minifigure models may be extracted from LEGO games despite their CC-BY label.",
            "La Casa de Papel and Em Busca da Felicidade are referenced by costume and scene only.",
            "Font: Fredoka, SIL Open Font License, src/lego/fonts/OFL.txt."]
with open(os.path.join(ASSETS, "CREDITS.txt"), "w", encoding="utf8") as f:
    f.write("\n".join(credits) + "\n")
print("failed:", failed)
print("left:", left)
