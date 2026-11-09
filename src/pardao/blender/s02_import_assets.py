# Step 2: imports the Sketchfab models into the "assets" collection, each under its own "<name>_import" empty, laid out in rows
# (characters, favela, objects) so the open window shows the whole kit, and reports what each contains (meshes, armatures, actions).
# Textures are capped at 512 px on import: PS2-era textures were 256-512, and some of these kits ship 4K maps.
# Resumable: models already imported are skipped, and it stops after a time budget so bl.mjs doesn't time out. Run again while it prints "left".
# To start over, delete the "assets" collection first (or run from pardao_base.blend).
#   node src/thps/bl.mjs run src/pardao/blender/s02_import_assets.py
import bpy, os, sys, time, json
try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    HERE = os.path.join(os.environ.get("PARDAO_ROOT", r"E:\Projetos\pardingows"), "src", "pardao", "blender")
sys.path.insert(0, HERE)
import importlib, set_lib
importlib.reload(set_lib)
from set_lib import ASSETS, WORK, ps2_material, shrink, redraw
from mathutils import Vector

TEX_CAP = 512
BUDGET_S = 420
ROWS = {
    "characters": (["mendigo_capuz", "thug_lp", "homem_lp", "jumento", "pistola"], 0.0),
    "favela": (["slums", "casa1", "casa2", "casas_pack", "casas_pack2", "rua_favela", "casa_br", "favelas", "barraco", "morro",
                "escada", "escada2", "muro_concreto", "grafite", "zinco", "caixa_dagua", "poste_luz", "lampiao", "bandeirolas", "kombi", "moto"], 40.0),
    "objects": (["cadeira", "engradado", "saco_lixo", "lixeira", "cacamba", "tambor_fogo", "carrinho", "caixas", "radio", "caixa_som",
                 "dj", "microfone", "baseado", "calendario", "taco"], -14.0),
}
# Real-world size per model: (axis, metres) for its bounding box, chosen from the thumbnails. Many exports are in centimetres.
# Axis 2 is height, 0 or 1 the longest flat side. Models not listed keep their scale.
SIZE = {
    "mendigo_capuz": (2, 1.55), "thug_lp": (2, 1.78), "homem_lp": (2, 1.78), "jumento": (2, 1.35), "pistola": (0, 0.22),
    "casa1": (2, 8.5), "casa2": (2, 10.0), "casas_pack": (2, 8.0), "casas_pack2": (2, 8.5),
    "escada": (2, 3.0), "escada2": (2, 3.0), "muro_concreto": (2, 3.0), "zinco": (2, 2.2), "caixa_dagua": (2, 5.0),
    "lampiao": (2, 4.5), "kombi": (1, 4.3), "moto": (2, 1.1),
    "cadeira": (2, 0.85), "engradado": (2, 0.3), "saco_lixo": (2, 0.7), "lixeira": (2, 0.9), "cacamba": (2, 1.3),
    "tambor_fogo": (2, 0.9), "carrinho": (2, 1.0), "radio": (2, 0.35), "caixa_som": (2, 1.2), "dj": (2, 1.0),
    "microfone": (2, 1.6), "baseado": (0, 0.09), "calendario": (2, 0.45), "taco": (0, 0.85),
}
on_disk = {n for n in os.listdir(ASSETS) if os.path.isdir(os.path.join(ASSETS, n))}
listed = {n for names, _ in ROWS.values() for n in names}
assert on_disk == listed, f"on disk but not listed: {on_disk - listed}, listed but missing: {listed - on_disk}"

scene = bpy.context.scene
coll = bpy.data.collections.get("assets")
if not coll:
    coll = bpy.data.collections.new("assets")
    scene.collection.children.link(coll)
REPORT = os.path.join(WORK, "review", "02-import.json")
report = json.load(open(REPORT, encoding="utf8")) if os.path.exists(REPORT) and len(coll.objects) else {}


def bbox(objs):
    mins, maxs = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for ob in objs:
        if ob.type != "MESH":
            continue
        for c in ob.bound_box:
            p = ob.matrix_world @ Vector(c)
            mins = Vector(map(min, mins, p))
            maxs = Vector(map(max, maxs, p))
    return mins, maxs


t0 = time.time()
left = []
for row, (names, y) in ROWS.items():
    cursor = 6.0 if row == "characters" else 0.0
    for name in names:
        root = bpy.data.objects.get(name + "_import")
        if root:
            # Already imported: just advance the row cursor past it
            cursor += report.get(name, {}).get("width", 2.0) + 2.0
            continue
        if time.time() - t0 > BUDGET_S:
            left.append(name)
            continue
        before = set(bpy.data.objects)
        acts_before = set(bpy.data.actions)
        bpy.ops.import_scene.gltf(filepath=os.path.join(ASSETS, name, "gltf", "scene.gltf"))
        new = [o for o in bpy.data.objects if o not in before]
        root = bpy.data.objects.new(name + "_import", None)
        root.empty_display_size = 0.5
        coll.objects.link(root)
        for ob in new:
            for c in list(ob.users_collection):
                c.objects.unlink(ob)
            coll.objects.link(ob)
            ob["asset"] = name
            if not ob.parent:
                ob.parent = root
        bpy.context.view_layer.update()
        mins, maxs = bbox(new)
        size = maxs - mins
        polys, tex, arms, mats = 0, set(), [], set()
        for ob in new:
            if ob.type == "ARMATURE":
                arms.append({"name": ob.name, "bones": len(ob.data.bones), "names": [b.name for b in ob.data.bones][:80]})
            if ob.type != "MESH":
                continue
            polys += len(ob.data.polygons)
            for m in ob.data.materials:
                if m:
                    mats.add(m)
                    if m.use_nodes:
                        tex |= {f"{n.image.size[0]}x{n.image.size[1]}" for n in m.node_tree.nodes if n.type == "TEX_IMAGE" and n.image}
        for m in mats:
            ps2_material(m)
            shrink(m, TEX_CAP, name)
        # Gallery spot: sit it on the floor, left edge at the row cursor, centred on the row
        root.location = (cursor - mins.x, y - (mins.y + maxs.y) / 2, -mins.z)
        cursor += size.x + 2.0
        acts = [a.name for a in bpy.data.actions if a not in acts_before]
        meshes = [o for o in new if o.type == "MESH"]
        skinned = [o.name for o in meshes if any(md.type == "ARMATURE" for md in o.modifiers)]
        report[name] = {"row": row, "meshes": len(meshes), "polys": polys, "mats": len(mats), "tex": sorted(tex),
                        "size": [round(v, 2) for v in size], "width": round(size.x, 2), "armatures": arms, "skinned": skinned[:10], "actions": acts[:20]}
        print(f"== {name}: {len(meshes)} meshes, {polys} polys, {len(mats)} mats, tex {sorted(tex)}, size {[round(v, 2) for v in size]}")
        for a in arms:
            print(f"   armature {a['name']} {a['bones']} bones: {a['names'][:30]}")
        if acts:
            print("   actions", acts[:10])
        bpy.data.orphans_purge(do_recursive=True)
        json.dump(report, open(REPORT, "w", encoding="utf8"), indent=1)
        redraw()

# Scale pass and gallery layout, redone on every run so a SIZE change only needs a re-run. Raw sizes are in the report.
for row, (names, y) in ROWS.items():
    cursor = 6.0 if row == "characters" else 0.0
    for name in names:
        root = bpy.data.objects.get(name + "_import")
        if not root:
            continue
        kids = [o for o in root.children_recursive]
        axis, metres = SIZE.get(name, (None, None))
        raw = report[name]["size"]
        k = metres / raw[axis] if axis is not None and raw[axis] > 0 else 1.0
        root.scale = (k, k, k)
        root.location = (0, 0, 0)
        bpy.context.view_layer.update()
        mins, maxs = bbox(kids)
        root.location = (cursor - mins.x, y - (mins.y + maxs.y) / 2, -mins.z)
        report[name]["scale"] = round(k, 5)
        report[name]["metres"] = [round(v, 2) for v in (maxs - mins)]
        cursor += (maxs.x - mins.x) + 1.5
json.dump(report, open(REPORT, "w", encoding="utf8"), indent=1)
for name, r in report.items():
    print(f"{name:14} scale {r['scale']:<9} -> {r['metres']} m")

# Frame everything in the open window
if not bpy.app.background:
    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            with bpy.context.temp_override(area=area, region=next(r for r in area.regions if r.type == "WINDOW")):
                bpy.ops.view3d.view_all()
set_lib.save()
print("images", len(bpy.data.images), "materials", len(bpy.data.materials))
print("left:", left)
