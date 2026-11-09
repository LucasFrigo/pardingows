# Step 4 review: one finished still per location with the cast in action, rendered raw at 540x960 to review/04-raw-<name>.png.
# src/pardao/ps2.mjs then makes review/04-<name>.png. Prints the render time of each frame.
#   node src/thps/bl.mjs run src/pardao/blender/set_stills.py
import bpy, os, sys, time
try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    HERE = os.path.join(os.environ.get("PARDAO_ROOT", r"E:\Projetos\pardingows"), "src", "pardao", "blender")
sys.path.insert(0, HERE)
import importlib, set_lib, poses_brawl as PB, actors as A
for m in (set_lib, PB, A):
    importlib.reload(m)
from set_lib import REVIEW

sc = bpy.context.scene
OB = bpy.data.objects
PLAYERS = ["P1", "P2", "P3", "P4"]
HOBOS = ["M1", "M2", "M3"]


def park():
    """Everyone back to the lineup before each still, standing."""
    for i, p in enumerate(PLAYERS):
        A.OB[p].location = (i * 1.3, -40, 0)
        A.OB[p].rotation_euler = (0, 0, 0)
        PB.pose_pardo(p, PB.P_STAND, A.G)
    for i, m in enumerate(HOBOS):
        A.OB[m].location = (5.6 + i * 1.2, -40, 0)
        A.OB[m].rotation_euler = (0, 0, 0)
        PB.pose_hobo(m, PB.H_STAND)
    for t in [o for o in OB if o.name.startswith("arma_")]:
        t.hide_render = t.hide_viewport = True
    OB["P2_mic"].hide_render = OB["P2_mic"].hide_viewport = True


def gun(m):
    # The pistol rides on the raised right hand (Mixamo "LeftHand", the +X side): call after the aim pose is set
    return A.gun_in_hand(f"arma_{m}", f"{m}_arm", "LeftHand")


STILLS = {}


def still(fn):
    STILLS[fn.__name__] = fn
    return fn


@still
def escada():
    """Street level: P1 kicks a Mildingow off the foot of the stairs while more come down. P2 squares up behind."""
    A.pardo("P1", (0.6, 2.4, 0), -90, PB.P_KICK)
    A.hobo("M3", (-0.75, 2.55, 0), 90, PB.H_HIT)
    A.hobo("M2", (-2.4, 1.3, 0), 60, PB.H_WALK[0])
    A.hobo("M1", (-4.6, 5.0, 0.9 + 0.15), 90, PB.H_WALK[2])
    A.pardo("P2", (1.9, 3.5, 0), -110, PB.P_GUARD_A)
    A.static("MB", (4.6, 5.0, 0), 200)
    cam = A.camera("cam_still", (1.2, -4.4, 2.2), (-0.6, 3.6, 1.7), 22)
    A.fill_light(cam, 300)
    return cam


@still
def muro():
    """Landing 2: the four Pardos hands up against the graffiti wall, the Mildingows' guns on them. Seen past the shooters."""
    for i, p in enumerate(PLAYERS):
        A.pardo(p, (-1.95 + i * 1.3, 15.05, 6), 0, PB.P_HANDSUP)
    # Each shooter turns towards a different Pardo, so from the over-the-shoulder camera the gun arms read in profile
    for i, (m, yaw) in enumerate(zip(HOBOS, (162, 182, 205))):
        A.hobo(m, (-1.7 + i * 1.7, 12.6, 6), yaw, PB.H_AIM)
        gun(m)
    cam = A.camera("cam_still", (3.6, 8.4, 8.6), (-0.4, 14.4, 6.9), 22)
    A.fill_light(cam, 350)
    return cam


@still
def baile():
    """The top plaza: the four Pardos dance the passinho in front of the paredão, Pardjhonson on the mic. The boss waits behind."""
    for i, p in enumerate(PLAYERS):
        A.pardo(p, (-1.95 + i * 1.3, 20.4 + (i % 2) * 0.5, 9), (i - 1.5) * 8, PB.P_DANCE_A if i % 2 else PB.P_DANCE_B)
    OB["P2_mic"].hide_render = OB["P2_mic"].hide_viewport = False
    A.static("JUMENTO", (3.9, 23.0, 9), -30)
    A.hobo("M1", (-4.3, 22.6, 9), 30, PB.H_DRINK)
    A.static("MB", (-5.2, 19.2, 9), 120)
    cam = A.camera("cam_still", (0.4, 12.4, 12.6), (0.0, 21.4, 10.0), 22)
    A.fill_light(cam, 300)
    return cam


only = os.environ.get("PARDAO_STILL")
for name, fn in STILLS.items():
    if only and name != only:
        continue
    park()
    A.static("JUMENTO", (11.6, -40, 0), 0)
    A.static("MB", (9.6, -40, 0), 0)
    cam = fn()
    sc.camera = cam
    bpy.context.view_layer.update()
    sc.render.filepath = os.path.join(REVIEW, f"04-raw-{name}.png")
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"still {name}: {time.time() - t0:.2f} s")
set_lib.save()
