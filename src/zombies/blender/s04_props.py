# Step 4: flattens each import into one prefab mesh at real-world size, feet on z = 0 and centred, named PF_<name>, kept out of the render.
# Sets and shots place shared copies with set_lib.place. Kits are split into the parts actually used.
import bpy, importlib, os, re, sys
from mathutils import Matrix, Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import set_lib; importlib.reload(set_lib)
from set_lib import FAR, fresh, parts

OB = bpy.data.objects
pf = fresh("prefabs", bpy.context.scene)
pf.hide_render = True


def flatten(name, asset, match=None, height=None, length=None, scale=None, keep_xy=False, keep_z=False, rz=0.0, frame=None):
    """Merges an asset's meshes (or those whose name matches) as they stand now into PF_<name>.
    height or length (the longest horizontal side) gives the final size in metres, or scale a plain factor."""
    if frame is not None:
        bpy.context.scene.frame_set(frame)
    meshes = [o for o in parts(asset) if not o.name.startswith("Icosphere") and (match is None or re.search(match, o.name))]
    assert meshes, f"{name}: nothing matches {match} in {asset}"
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    v, f, fm, uvs, mats = [], [], [], [], []
    for ob in meshes:
        ev = ob.evaluated_get(dg)
        me = bpy.data.meshes.new_from_object(ev)
        me.transform(ev.matrix_world)
        off, base = len(v), len(mats)
        mats += list(me.materials) or [None]
        v += [tuple(x.co) for x in me.vertices]
        uv = me.uv_layers.active
        for p in me.polygons:
            f.append(tuple(off + i for i in p.vertices))
            fm.append(base + p.material_index)
            uvs.append([tuple(uv.data[l].uv) if uv else (0, 0) for l in p.loop_indices])
        bpy.data.meshes.remove(me)
    me = bpy.data.meshes.new("PF_" + name)
    me.from_pydata(v, [], f)
    for mt in mats:
        me.materials.append(mt)
    layer = me.uv_layers.new(name="UVMap")
    for p, q, mi in zip(me.polygons, uvs, fm):
        p.material_index = mi
        p.use_smooth = False
        for l, uv in zip(p.loop_indices, q):
            layer.data[l].uv = uv
    pts = [x.co for x in me.vertices]
    lo = Vector(min(p[i] for p in pts) for i in range(3))
    hi = Vector(max(p[i] for p in pts) for i in range(3))
    size = hi - lo
    k = scale if scale else height / size.z if height else length / max(size.x, size.y) if length else 1.0
    tx = 0 if keep_xy else -(lo.x + hi.x) / 2
    ty = 0 if keep_xy else -(lo.y + hi.y) / 2
    tz = 0 if keep_z else -lo.z
    me.transform(Matrix.Rotation(rz, 4, "Z") @ Matrix.Scale(k, 4) @ Matrix.Translation(Vector((tx, ty, tz))))
    ob = OB.new("PF_" + name, me)
    pf.objects.link(ob)
    ob.location = FAR
    ob.hide_render = True
    print(f"PF_{name}: {len(f)} polys, size {size.x * k:.2f} {size.y * k:.2f} {size.z * k:.2f}", flush=True)
    return ob


# ---- Rooms keep their own coordinates: both are already in metres with the floor at z = 0
flatten("corredor", "corredor", keep_xy=True, keep_z=True)
flatten("hall", "hall", keep_xy=True, keep_z=True)

# ---- Mansion
flatten("janela", "janela", height=2.6)
flatten("lustre", "lustre", height=1.5)
flatten("estante", "estante", height=2.5)
flatten("relogio", "relogio", height=2.2)
flatten("vela", "vela", height=0.28)
flatten("candelabro", "candelabro", height=1.5)
flatten("retrato", "retrato", height=1.1)
flatten("caixa", "caixa", height=0.7)
flatten("parede", "parede", length=3.0)
flatten("piano", "moveis", r"^piano(?!Stool)", scale=0.8)
flatten("banqueta", "moveis", r"^pianoStool", scale=0.8)
flatten("poltrona", "moveis", r"^chair_", scale=0.65)
flatten("cadeira", "moveis", r"^DinnerChair", scale=0.55)
flatten("mesa", "moveis", r"^LargeTable", scale=0.75)
flatten("armario", "moveis", r"^TallCabinet", scale=0.75)
flatten("tapete", "moveis", r"^Plane_rugtex", scale=0.8)
flatten("mesinha", "moveis", r"^sidetable", scale=0.6)
flatten("quadro_cao", "moveis", r"^PortraitDog", scale=0.8)
flatten("teias", "teias", scale=0.012)

# ---- Dungeon
flatten("parede_tocha", "tocha", height=2.6)
flatten("grades", "grades", height=2.3)
flatten("esqueleto", "esqueleto", height=1.65)
flatten("barata", "barata", length=0.5)

# ---- Street
flatten("ruina", "ruina")
flatten("ruina2", "ruina2")
flatten("viatura", "viatura")
flatten("semaforo", "semaforo", height=6.0)
flatten("poste", "poste", height=6.4)
flatten("barreira", "barreira", length=2.2)
flatten("helicoptero", "helicoptero", length=11.0)
flatten("fita", "fita", r"^CrimeTape", scale=0.8)
flatten("giz", "fita", r"^Body1", scale=0.9)
flatten("cones", "rua", r"^barriers1", length=1.8)
flatten("lixeira", "rua", r"^(Tank|Cap)\.001", height=0.9)
flatten("soda", "rua", r"^SodaMachine\.004", height=1.9)
flatten("cabine", "rua", r"^(Body|Door|Glass_Side)\.?\d*_|^Glass_Side_", length=2.0)

# ---- Gag props
flatten("seringa", "seringa", length=1.0)
flatten("cola", "cola", height=0.9)
flatten("pomba", "pomba", length=0.34)
flatten("pistola", "pistola", r"^(main|side|trigger)_", length=0.42)
flatten("porta", "portas", r"^Worn Door_001", height=2.3)

# ---- The imports are spent. Everything is read from here on through the prefabs.
for ob in list(OB):
    if ob.get("asset") or ob.name.endswith("_import"):
        OB.remove(ob, do_unlink=True)
bpy.data.orphans_purge(do_recursive=True)
set_lib.save()
print("=== PROPS DONE", flush=True)
