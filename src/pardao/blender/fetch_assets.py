# Downloads the approved Sketchfab models into blender/pardao/assets/<name>/ with the API key held by the addon, and writes CREDITS.txt.
# Run inside the open Blender so the key stays in its preferences. It is never printed or written to disk.
# Safe to re-run: models already on disk are skipped. It stops after a time budget, so a long download can't hold Blender past bl.mjs's timeout:
# run it again while it prints a non-empty "left:" list.
#   node src/thps/bl.mjs run src/pardao/blender/fetch_assets.py
# bl.mjs executes this text without __file__, so the repo root comes from PARDAO_ROOT or the path below.
import bpy, os, time, zipfile, requests

ROOT = os.environ.get("PARDAO_ROOT", r"E:\Projetos\pardingows")
ASSETS = os.path.join(ROOT, "blender", "pardao", "assets")
os.makedirs(ASSETS, exist_ok=True)
BUDGET_S = 420

# Numbers are the ones on the review sheets (blender/pardao/review/00-assets-*.png), approved by the user on 2026-11-06
MODELS = {
    # characters
    "mendigo_capuz": "f9182eda717247a7abcba196194678b4",  # 2
    "thug_lp": "6410256c1c41417bbc1de043983b3107",  # 4
    "homem_lp": "16522107ad84410dad419e2e3977e721",  # 8
    "jumento": "e46951f1f62b44f79657400d75e8fc8d",  # 13
    # favela
    "slums": "e2b6f532e1fe4f7280890971d78183f4",  # 15
    "casa1": "b9797c38e4e645b39f0cda8c05bebd5f",  # 16
    "casa2": "c87942d7d3ba43648920c7f7cd451afc",  # 17
    "casas_pack": "be4a54f622a14f8b8bb8df70046f1dc1",  # 18
    "casas_pack2": "789cd0b9c4644a01adc3ace61573baf1",  # 19
    "rua_favela": "9631e0bae22343db82c44fe243af7c15",  # 21
    "casa_br": "7164cfffd09743899278ab52f688e566",  # 23
    "favelas": "03a03568eb0d4c9cbae9b1ce4091b059",  # 24
    "barraco": "2473e58947004b3fadc5daa6fad6afeb",  # 25
    "morro": "2e238fa40a9844cb85374ea2d9715617",  # 26
    "escada": "b552862f1bff4a968fa65da90c6a9e6b",  # 27
    "escada2": "8bc4ce5657e548bbacada83f04e7f50d",  # 28
    "muro_concreto": "51c6567b2d524f179254667176f60a3a",  # 29
    "grafite": "2fdfb7253c4044aab30c933cce951bc2",  # 30
    "zinco": "ea06568a9e304ecc806cb7cb0552e269",  # 32
    "caixa_dagua": "aff4e9fd3f7042d5855fade7411df4df",  # 34
    "poste_luz": "55261fa6535e4d5ea8c7af390c478110",  # 35
    "lampiao": "e127bb7b1a154529b7d4fc4a1be4bc99",  # 37
    "bandeirolas": "64a08e45f72640659a590cc1ea805301",  # 38
    "kombi": "f6a7b54ec6d24d8e95992f68be6c930c",  # 39
    "moto": "9c486accf04f41389b8d5ca01968ec06",  # 40
    # objects
    "cadeira": "68089dce5fa1461981d690f1cfd657fa",  # 42
    "engradado": "24329e92a51b41f690fe4bfbd510c9f3",  # 44
    "saco_lixo": "9ef36ddf03bb4db99bc32a369cc2c871",  # 46
    "lixeira": "269cc79ce7ca4dcf88030e7b7151dc36",  # 48
    "cacamba": "7dca2f86161346a894f113cafb473e72",  # 49
    "tambor_fogo": "166e9eb26fd9406b961fa08722648093",  # 50
    "carrinho": "96534b56f0d9487db08f00f1f9301fa1",  # 52
    "caixas": "5d3d508061e544739e37c685af235684",  # 54
    "radio": "d9f19a9ddce04dac8586b34869d0c1ba",  # 56
    "caixa_som": "7c0d85ad0df04153a864a49e575b6416",  # 57
    "dj": "00615da2444f437da7efa342c05be7ff",  # 59
    "microfone": "16cfa90113ee43f4812d062d37d26462",  # 60
    "baseado": "fc5daec8fc7f4fbf9424736fd4bcbdf0",  # 61
    "calendario": "592f4833145442d2871b8f7c23a113b0",  # 62
    "taco": "2669cf86386747449611396c0409db47",  # 63
    "pistola": "6640a5fd40b4456c94578b015264e305",  # from PARDOS vs ZOMBIES, the Mildingows' guns at the muro
}
addons = bpy.context.preferences.addons
addon = next((a for k, a in addons.items() if k.endswith("blender_mcp")), None)  # an extension registers as bl_ext.<repo>.blender_mcp
key = addon.preferences.sketchfab_api_key if addon else None
if not key:
    raise RuntimeError("no Sketchfab key in the addon preferences")

# Downloaded but never seen in the video, so not credited. Models whose textures dress the procedural houses, stairs and
# graffiti walls (casa1, casa2, casas_pack, casas_pack2, favelas, escada, escada2, grafite) are credited even though their
# meshes aren't used.
NOT_SHOWN = {"homem_lp", "slums", "rua_favela", "casa_br", "barraco", "morro", "muro_concreto", "zinco", "caixa_dagua",
             "poste_luz", "lampiao", "bandeirolas", "taco", "calendario"}
credits = ["Modelos 3D do video PARDÃO 2000. Licence and author from the public Sketchfab API, so the credit must appear wherever the video is shared.", "",
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
    os.remove(path)
    print(name, f"{len(z.content) // 1024} KB")

credits += ["", "Not credit lines, but check before publishing:",
            "Smurf base model: by grishamanimation1, repainted, shades and chain added. Licence terms not verified (see blender/solucao).",
            "Game look: an original PS2-era brawler. No real game's logos, HUD or characters are used.",
            "Fonts: Russo One, Bungee and VT323, SIL Open Font License, src/pardao/fonts/OFL-*.txt."]
with open(os.path.join(ASSETS, "CREDITS.txt"), "w", encoding="utf8") as f:
    f.write("\n".join(credits) + "\n")
print("failed:", failed)
print("left:", left)
