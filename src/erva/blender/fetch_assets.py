# Downloads the approved Sketchfab models into blender/erva/assets/<name>/ with the API key held by the addon, and writes CREDITS.txt.
# Run inside the open Blender so the key stays in its preferences. It is never printed or written to disk.
# Safe to re-run: models already on disk are skipped. It stops after a time budget so a long download can't hold Blender
# past bl.mjs's timeout: run it again while it prints a non-empty "left:" list.
#   node src/thps/bl.mjs run src/erva/blender/fetch_assets.py
# bl.mjs executes this text without __file__, so the repo root comes from ERVA_ROOT or the path below.
import os
import time
import zipfile

import bpy
import requests

ROOT = os.environ.get("ERVA_ROOT", r"E:\Projetos\pardingows")
ASSETS = os.path.join(ROOT, "blender", "erva", "assets")
os.makedirs(ASSETS, exist_ok=True)
BUDGET_S = 420

# Numbers are the ones on the review sheets (blender/erva/review/00-assets-*.png), approved by the user on 2026-11-06
MODELS = {
    # storyteller room
    "cadeira_balanco": "d5e784aa92464572af37264c3b3d2fa6",  # 1
    "poltrona": "49e21ea4c0bf469387471934dd8bf0fa",  # 3
    "relogio": "5dfff9d9c87f44cba61fb83179b0e3e2",  # 6
    "gramofone": "5e892fc786db4ca1b36738ab5e40e64d",  # 8
    "radio": "c744a35e88ae4f0f9d71483623412808",  # 10
    "livro": "cc887c88fe954dc2a4be11fcfb83fec6",  # 13
    "livro_aberto": "b30b6a9018f842e7b12622387979b0fa",  # 15
    "cachimbo": "f8a626bec4984fd083758dc07bcf057a",  # 18
    # jungle / Eden
    "palmeira": "95cd1a77789241ee82a960bad5dfe809",  # 22
    "bananeira": "3856533f350b4d33b47d5d434b9ac911",  # 24
    "costela_adao": "28bb9cca91e6479cadcd9c55242f43c1",  # 25
    "orelha_elefante": "75882b72d1374270aeac76c96db2aa4e",  # 29
    "arbusto": "9d9ce79d3ae040619e96d5b22c7de1a6",  # 30
    "arvores_pack": "6cfabc6732bf40fea7090cb6557ee0d8",  # 31
    "arvores_toon": "d631da94d5c14b85b44d9a737fef883f",  # 32
    "arvore": "e319ba8a4572485087b779db7b8bdb20",  # 33
    "macieira": "0fa93c551d8449808cc1f85c4238bf93",  # 34
    "tronco_caido": "85be5e12759d460cb5f1f0d7a4c109b6",  # 36
    "toco": "04d51f5c2fb643aab3b93b451d1b77c9",  # 37
    "cogumelos": "9d22e02ce2a548959b1c4c4c1d546842",  # 38
    "pedras": "480403c4689a425db3748baa88ad52c4",  # 40
    "flor": "7d8acfb0b38d4e4b9ef2c6e336473049",  # 43
    "margarida": "54045596253e478993ca96572cb1bf6b",  # 44
    "flores": "bffdeb9b066c43ac9456d9899e37d509",  # 45
    "nuvem": "f31be54812a348df86d94171098dae19",  # 47
    # spooky jungle
    "arvore_assombrada": "134a1f03b97d453d8ba63752f9c3b28d",  # 49
    "arvore_morta": "addc2aef9e534a93a8798320fea440ef",  # 53
    "arvore_retorcida": "7bdf7f23455e4298b77d3982461888a7",  # 54
    "esqueletos": "f07fa9b47c8c4d468b3f5a2124d53a15",  # 55
    # props
    "cigarro": "08ec2ff5d829436c955f4b5e8e0e47a7",  # 57
    "baseados": "00b86fecb88f4e5aa9a3f492dfae8448",  # 59
    "pe_erva": "73637ede37884a56bcb0f7e5d75b2ff8",  # 62
    "chapeu_coco": "3c3f5bfb98284924a70cf410ab532bc9",  # 64
    "caixa_registradora": "87562962d47e48b28cc1b874fa46a47f",  # 66
    "placa": "0d2fbde1a0a446a1b3bb808664a7e08a",  # 67
    "pote": "a9709a4cae864de4a1738519376621f6",  # 69
    "perolas": "badddc19523f4dc08344e8da5b143dae",  # 70
    "microfone": "a5986b39102f47c5b32b212365dd7276",  # 71
}
addons = bpy.context.preferences.addons
addon = next((a for k, a in addons.items() if k.endswith("blender_mcp")), None)  # an extension registers as bl_ext.<repo>.blender_mcp
key = addon.preferences.sketchfab_api_key if addon else None
if not key:
    raise RuntimeError("no Sketchfab key in the addon preferences")

# Downloaded but not seen in the video, so not credited: replaced by pieces built in code (the bowler, pearls,
# cigarettes, joints, books, jar) or never placed (banana plant, microphone, the lone tree)
NOT_SHOWN = {"chapeu_coco", "perolas", "cigarro", "baseados", "livro", "livro_aberto", "pote", "bananeira", "microfone", "arvore"}
credits = ["Modelos 3D do video PARDÃO E A ERVA. Licence and author from the public Sketchfab API, so the credit must appear wherever the video is shared.", "",
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
    # The signed file URL takes no auth header. Retried on network errors; the URL itself is never printed.
    z = None
    for attempt in range(3):
        try:
            z = requests.get(r.json()["gltf"]["url"], timeout=180)
            if z.status_code == 200:
                break
        except requests.exceptions.RequestException as e:
            print(name, f"attempt {attempt + 1}: {type(e).__name__}")
            time.sleep(3)
            z = None
    if z is None or z.status_code != 200:
        failed.append(name)
        continue
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
            "Look: an original 1930s-style rubber-hose cartoon. No studio's characters, logos or fonts are used.",
            "Fonts: Alfa Slab One, Limelight, Abril Fatface (and candidates Rye, Bevan, Fascinate), SIL Open Font License, src/erva/fonts/OFL-*.txt."]
with open(os.path.join(ASSETS, "CREDITS.txt"), "w", encoding="utf8") as f:
    f.write("\n".join(credits) + "\n")
print("failed:", failed)
print("left:", left)
