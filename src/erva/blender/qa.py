# Staging QA for every moment, run headless BEFORE rendering: builds sampled frames with shots.apply() and measures
# clipping, hands inside bodies, facing, key subjects on screen (above the captions, not hidden) and feet on the floor.
#   "$BLENDER" -b blender/erva/erva.blend -P src/erva/blender/qa.py -- [--step 4] [--only moment,moment] [--frames f,f]
# Out: blender/erva/review/qa.json and a summary per moment. The rules for what to declare are in CLAUDE.md.
import json
import os
import sys
import time

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "shared"))
import blender_qa as Q  # noqa: E402
import shots  # noqa: E402
from set_lib import REVIEW  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def opt(name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default


OB = bpy.data.objects
RIGS = ["P1", "VOVO", "EVA", "P2", "P3", "P4"]
PROPS = {"joint": ["joint"], "cigarette": ["cigarette"], "cigarette2": ["cigarette2"], "hood": ["hood"],
         "book": ["book_back", "book_cover"], "pipe": ["pipe_model"], "trap": ["trap_crate", "trap_stick"],
         "register": ["register_model", "register_tab"], "jar": ["jar_glass", "jar_cork"]}
CHAIRS = {"rocking": ["sala_rocking"], "wingchair": ["sala_wingchair"]}
BODY = ("torso", "head", "hat", "nose", "ears", "pelvis", "beard")  # soft parts (hair, dress) may overlap hands

# What each moment must show and may touch. facing: (who, target actor) within FACING_MAX degrees.
# visible: objects that must be on screen above the caption band and mostly unhidden. allow: intended contact.
# floor: rigs standing on the ground. seated: rigs whose chair contact is allowed (deeper).
SPEC = {
    "conto": dict(face=["VOVO", "EVA"], visible=["VOVO_head", "EVA_head", "book_back"], allow=[("VOVO", "book")],
                  seated={"VOVO": "rocking", "EVA": "wingchair"}),
    "cachimbo": dict(face=["VOVO", "EVA"], visible=["VOVO_head", "EVA_head"], allow=[("VOVO", "book"), ("VOVO", "pipe"), ("EVA", "pipe")],
                     seated={"VOVO": "rocking", "EVA": "wingchair"}),
    "trevas": dict(visible=["P1_head"], floor=["P1"]),
    "selva": dict(visible=["P1_head"]),
    "jardim": dict(face=["P1"], visible=["P1_head", "COBRA_head"], floor=["P1"]),
    "basiadin": dict(face=["P1"], visible=["P1_head", "COBRA_head", "joint"], facing=[("P1", "COBRA")], allow=[("COBRA", "joint")],
                     floor=["P1"]),
    "caminho": dict(face=["P1"], visible=["P1_head", "COBRA_head", "joint"], facing=[("P1", "COBRA")],
                    allow=[("COBRA", "joint"), ("P1", "joint")], floor=["P1"]),
    "da_boa": dict(face=["P1"], visible=["P1_head", "COBRA_head", "joint"], facing=[("P1", "COBRA")], allow=[("P1", "joint")],
                   floor=["P1"]),
    "compensa": dict(face=["P1"], visible=["P1_head", "COBRA_head", "register_tab"], facing=[("P1", "COBRA")],
                     allow=[("P1", "joint"), ("COBRA", "joint")], floor=["P1"]),
    "tarde": dict(face=["P1"], visible=["P1_head", "COBRA_head"], facing=[("P1", "COBRA")], allow=[("P1", "COBRA")], floor=["P1"]),
    "alma": dict(visible=["COBRA_head", "jar_glass"], allow=[("COBRA", "jar")]),
    "risada": dict(visible=["COBRA_head", "jar_glass"], allow=[("COBRA", "jar")]),
    "mole": dict(face=["P1"], visible=["P1_head", "COBRA_head"], facing=[("P1", "COBRA")], allow=[("P1", "COBRA"), ("COBRA", "jar")]),
    "crew": dict(face=["P1", "P2", "P3", "P4"], visible=["P1_head", "COBRA_head"], facing=[("P1", "COBRA")],
                 allow=[("COBRA", "hood")]),
    "cigarros": dict(face=["P1"], visible=["P1_head", "COBRA_head", "cigarette", "cigarette2"], facing=[("P1", "COBRA")],
                     allow=[("COBRA", "hood"), ("P1", "cigarette"), ("P1", "cigarette2")], floor=["P1"]),
    "arapuca": dict(visible=["COBRA_head", "trap_crate"], allow=[("COBRA", "trap"), ("COBRA", "hood"), ("COBRA", "joint"),
                                                                ("trap", "joint")]),
}
# The size (m) a crossing region may reach before it reads as clipping
DEPTH_MAX = {"rig-rig": 0.06, "rig-cobra": 0.06, "rig-prop": 0.08, "cobra-prop": 0.08, "rig-chair": 0.22, "self": 0.09}
FACING_MAX = 70.0
FACE_MAX = 62.0  # a lead's face must turn at least this far towards the camera: in profile a Pardo's ear hides it
VIS_ON, VIS_CLEAR = 0.6, 0.55
VIS_CLEAR_PROP = 0.4  # a prop in a mouth or a hand is partly covered by them by design
SOFT = ("dress", "hair", "tail", "leg", "shoe")  # parts allowed to rest on or sink into a chair


def actors():
    out = {p: Q.group([p]) for p in RIGS}
    out["COBRA"] = Q.group(["COBRA"])
    for k, names in PROPS.items():
        out[k] = Q.group(names)
    for k, names in CHAIRS.items():
        out[k] = Q.group(names)
    return {k: v for k, v in out.items() if v}


def kind(name):
    return "rig" if name in RIGS else "cobra" if name == "COBRA" else "chair" if name in CHAIRS else "prop"


def in_view(objs):
    sc = bpy.context.scene
    c = Q.centre(objs)
    if (c - sc.camera.matrix_world.translation).length > 25:  # parked off stage
        return False
    s = world_to_camera_view(sc, sc.camera, c)
    return s.z > 0 and -0.3 < s.x < 1.3 and -0.3 < s.y < 1.3


_SOLIDS = {}


def solid(name, objs, dg):
    if name not in _SOLIDS:
        _SOLIDS[name] = Q.Solid(objs, dg)
    return _SOLIDS[name]


def pen(a, b, acts, dg, sample=900):
    """Deepest point of a inside b (cached surfaces per frame)."""
    A, B = solid(a, acts[a], dg), solid(b, acts[b], dg)
    if not A.verts or not B.bvh:
        return 0.0, None
    worst, where = 0.0, None
    for v in A.verts[::max(1, len(A.verts) // sample)]:
        d = B.depth(v)
        if d > worst:
            worst, where = d, v
    return worst, where


def check_frame(f):
    m = shots.apply(f)
    _SOLIDS.clear()
    spec = SPEC.get(m, {})
    dg = bpy.context.evaluated_depsgraph_get()
    acts = {k: v for k, v in actors().items() if in_view(v)}
    allow = {tuple(sorted(p)) for p in spec.get("allow", [])}
    seated = spec.get("seated", {})
    issues = []
    names = sorted(acts)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            ka, kb = kind(a), kind(b)
            pair = "-".join(sorted((ka, kb)))
            if tuple(sorted((a, b))) in allow or pair in ("prop-prop", "chair-prop", "chair-chair", "chair-cobra"):
                continue
            if pair == "chair-rig":
                rig, chair = (a, b) if ka == "rig" else (b, a)
                if seated.get(rig) != chair:
                    continue
            lim = DEPTH_MAX.get(pair, DEPTH_MAX["rig-prop"])
            if pair == "chair-rig":  # sitting: only hard parts count (a skirt or hair resting on the chair is fine)
                rig = a if ka == "rig" else b
                hard = [o for o in acts[rig] if not o.name[len(rig) + 1:].startswith(SOFT)]
                d, w = Q.crossing(solid(rig + "_hard", hard, dg), solid(chair, acts[chair], dg))
            else:
                d, w = Q.crossing(solid(a, acts[a], dg), solid(b, acts[b], dg))
            if d > lim:
                issues.append({"type": "clip", "what": f"{a} x {b}", "depth": round(d, 3), "at": [round(x, 2) for x in w]})
    # hands and arms inside their own body
    for p in [r for r in RIGS if r in acts]:
        body = [o for o in acts[p] if o.name[len(p) + 1:].split(".")[0] in BODY]
        hands = [o for o in acts[p] if "_glove" in o.name and not o.hide_render]
        tubes = [o for o in acts[p] if o.name in (f"{p}_armR", f"{p}_armL")]
        if not body:
            continue
        B = Q.Solid(body, dg)
        worst = 0.0
        for o in hands:
            worst = max(worst, Q.crossing(Q.Solid([o], dg), B)[0])
        for o in tubes:  # past the shoulder, where the tube starts inside the body anyway
            T = Q.Solid([o], dg)
            far = [i for i, t in enumerate(T.tris) if min(t) > len(T.verts) * 0.45]
            if far and T.bvh:
                pairs = [(i, j) for i, j in T.bvh.overlap(B.bvh) if i in set(far)] if B.bvh else []
                if pairs:
                    pts = [sum((T.verts[k] for k in T.tris[i]), Vector()) / 3 for i, _ in pairs]
                    c = sum(pts, Vector()) / len(pts)
                    worst = max(worst, 2 * max((p - c).length for p in pts))
        if worst > DEPTH_MAX["self"]:
            issues.append({"type": "hand-in-body", "what": p, "depth": round(worst, 3)})
    for who, target in spec.get("facing", []):
        if who in acts and target in acts:
            tgt = shots.cobra_head_pt() if target == "COBRA" else OB[target].matrix_world.translation
            e = Q.facing_error(OB[who], tgt)
            if e > FACING_MAX:
                issues.append({"type": "facing", "what": f"{who} -> {target}", "deg": round(e)})
    sc = bpy.context.scene
    for who in spec.get("face", []):
        if who in acts:
            e = Q.facing_error(OB[who], sc.camera.matrix_world.translation)
            if e > FACE_MAX:
                issues.append({"type": "face", "what": who, "deg": round(e)})
    for name in spec.get("visible", []):
        objs = [o for o in Q.group([name]) if not o.hide_render] or ([OB[name]] if name in OB and not OB[name].hide_render else [])
        if not objs or not in_view(objs) and (Q.centre(objs) - bpy.context.scene.camera.matrix_world.translation).length > 25:
            continue  # parked off stage: not in this shot
        owner = name.split("_")[0]
        own = [o.name for o in Q.group([owner])] if owner in RIGS + ["COBRA"] else []
        on, clear = Q.visible(objs, dg=dg, ignore=own)
        if on < VIS_ON or clear < (VIS_CLEAR if owner in RIGS + ["COBRA"] else VIS_CLEAR_PROP):
            issues.append({"type": "hidden", "what": name, "on_screen": round(on, 2), "unblocked": round(clear, 2)})
    for p in spec.get("floor", []):
        if p in acts:
            z = Q.lowest(acts[p], dg)
            if z < -0.04 or z > 0.07:
                issues.append({"type": "floor", "what": p, "lowest": round(z, 3)})
    return m, issues


def main():
    step = int(opt("--step", "4"))
    only = set(opt("--only", "").split(",")) - {""}
    cards = json.load(open(os.path.join(shots.ROOT, "src", "erva", "cards.json"), encoding="utf8"))
    fr = lambda t: int(round((t - shots.START) * shots.FPS)) + 1
    frames = set(range(fr(cards["title_until"]), fr(cards["fim_from"]), step)) | {fr(c) + 1 for c in shots.CUTS[1:-1]}
    if opt("--frames"):
        frames = {int(x) for x in opt("--frames").split(",")}
    out, t0 = {}, time.time()
    for f in sorted(frames):
        m = shots.moment_at(shots.song_t(f))[1]
        if only and m not in only:
            continue
        m, issues = check_frame(f)
        if issues:
            out[str(f)] = {"moment": m, "issues": issues}
    json.dump(out, open(os.path.join(REVIEW, "qa.json"), "w", encoding="utf8"), indent=1)
    summary = {}
    for f, r in out.items():
        for it in r["issues"]:
            key = (r["moment"], it["type"], it["what"])
            s = summary.setdefault(key, {"frames": [], "worst": it})
            s["frames"].append(int(f))
            val = it.get("depth", it.get("deg", it.get("lowest", 0)))
            if val > s["worst"].get("depth", s["worst"].get("deg", s["worst"].get("lowest", 0))):
                s["worst"] = it
    print(f"QA: {len(frames)} frames in {time.time() - t0:.0f}s, {len(out)} with issues")
    for (m, ty, what), s in sorted(summary.items(), key=lambda kv: (shots.MOMENT_NAMES.index(kv[0][0]), kv[0][1])):
        fs = s["frames"]
        w = {k: v for k, v in s["worst"].items() if k not in ("type", "what")}
        print(f"  {m:9} {ty:12} {what:22} {len(fs):3} frames ({min(fs)}-{max(fs)})  worst {w}")
    if not summary:
        print("  clean")


main()
