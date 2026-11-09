import math

# Poses in degrees in the rest axes (see rest_q in s03_cast.py). Everyone faces -Y, and "R" is always the +X side.
# Zombies start in a T pose. +Y drops the R arm, -Y drops the L arm. -Z swings the R arm forward, +Z swings the L arm forward. On legs and spine, +X bends forward.
# The "drop" key is how far the root sinks, in metres.

# Arms hanging, shoulders slumped
Z_STAND = {"spine": (14, 0, 0), "neck": (8, 0, 0), "head": (6, 0, 4), "armR": (0, 70, -8), "foreR": (0, 6, -14), "armL": (0, -74, 6), "foreL": (0, -8, 16)}

# The classic reach
Z_REACH = {"spine": (16, 0, 0), "neck": (6, 0, 0), "head": (4, 0, -6), "armR": (0, 12, -72), "foreR": (0, 0, -10), "armL": (0, -18, 66), "foreL": (0, 0, 14)}

# Shamble: one leg drags. Stepped on the 15 fps pose grid.
Z_WALK = [
    {"spine": (16, 0, 6), "neck": (8, 0, 0), "head": (6, 0, -6), "armR": (0, 58, -20), "foreR": (0, 0, -20), "armL": (0, -70, 2), "foreL": (0, 0, 10),
     "thighR": (-26, 0, 0), "shinR": (10, 0, 0), "thighL": (16, 0, 0), "shinL": (18, 0, 0)},
    {"spine": (18, 0, 2), "neck": (8, 0, 0), "head": (8, 0, -2), "armR": (0, 62, -14), "foreR": (0, 0, -20), "armL": (0, -70, 6), "foreL": (0, 0, 10),
     "thighR": (-8, 0, 0), "shinR": (6, 0, 0), "thighL": (-4, 0, 0), "shinL": (36, 0, 0)},
    {"spine": (16, 0, -4), "neck": (8, 0, 0), "head": (6, 0, 4), "armR": (0, 66, -6), "foreR": (0, 0, -20), "armL": (0, -62, 16), "foreL": (0, 0, 10),
     "thighR": (12, 0, 0), "shinR": (14, 0, 0), "thighL": (-20, 0, 0), "shinL": (12, 0, 0)},
    {"spine": (18, 0, -1), "neck": (8, 0, 0), "head": (8, 0, 2), "armR": (0, 62, -10), "foreR": (0, 0, -20), "armL": (0, -66, 10), "foreL": (0, 0, 10),
     "thighR": (-2, 0, 0), "shinR": (30, 0, 0), "thighL": (-8, 0, 0), "shinL": (6, 0, 0)},
]

# Crouched over the body, back to the camera, feeding
_K = {"drop": 0.5, "spine": (40, 0, 0), "neck": (12, 0, 0), "head": (24, 0, 0),
      "armR": (0, 40, -60), "foreR": (0, 0, -55), "armL": (0, -40, 60), "foreL": (0, 0, 55),
      "thighR": (-64, 6, 0), "shinR": (128, 0, 0), "thighL": (-64, -6, 0), "shinL": (128, 0, 0)}


def kneel(**over):
    return {**_K, **over}


# The head turn over the shoulder, from feeding to staring into a camera behind him and off to the -X side.
# Turning around a bent spine tips the face upward, so the head keeps bowing forward the whole way round: that is what keeps the final stare level.
TURN = [
    kneel(),
    kneel(spine=(38, 0, -8), neck=(9, 0, -14), head=(24, 0, -20)),
    kneel(spine=(34, 0, -16), neck=(6, 0, -30), head=(24, 0, -42)),
    kneel(spine=(32, 0, -24), neck=(3, 0, -44), head=(20, 0, -62)),
    kneel(spine=(30, 0, -28), neck=(0, 0, -52), head=(12, 0, -75)),
]

# Same stand with her chin up: her exported pose already stoops
ZF_STAND = {**Z_STAND, "neck": (-10, 0, 0), "head": (-18, 0, 4)}


# The judging close-up shakes its head after staring
def judge_pose(frame):
    """frame is 0-based, 30 per second: turn for 12 frames, stare, then a slow disappointed shake."""
    if frame < 12:
        k = frame / 12 * (len(TURN) - 1)
        i = int(k)
        return mix(TURN[i], TURN[min(i + 1, len(TURN) - 1)], k - i)
    shake = 0.0 if frame < 22 else 15 * math.sin((frame - 22) * 0.42)
    return {**TURN[-1], "head": (TURN[-1]["head"][0], 0, TURN[-1]["head"][2] + shake)}


def mix(a, b, t):
    """Blends two poses. Anything missing counts as zero."""
    out = {}
    for k in set(a) | set(b):
        if k == "drop":
            out[k] = a.get(k, 0) * (1 - t) + b.get(k, 0) * t
        else:
            va, vb = a.get(k, (0, 0, 0)), b.get(k, (0, 0, 0))
            n = max(len(va), len(vb))
            va, vb = tuple(va) + (0,) * (n - len(va)), tuple(vb) + (0,) * (n - len(vb))
            out[k] = tuple(x * (1 - t) + y * t for x, y in zip(va, vb))
    return out


# Running away, from Missão's human cycle
H_RUN = [
    {"spine": (14, 0, 5), "head": (-10, 0, 0), "armR": (0, 62, 36), "foreR": (0, 0, -80), "armL": (0, -62, 36), "foreL": (0, 0, 80),
     "thighR": (-52, 0, 0), "shinR": (34, 0, 0), "thighL": (32, 0, 0), "shinL": (58, 0, 0)},
    {"spine": (14, 0, 0), "head": (-10, 0, 0), "armR": (0, 66, 0), "foreR": (0, 0, -80), "armL": (0, -66, 0), "foreL": (0, 0, 80),
     "thighR": (-8, 0, 0), "shinR": (46, 0, 0), "thighL": (-28, 0, 0), "shinL": (84, 0, 0)},
    {"spine": (14, 0, -5), "head": (-10, 0, 0), "armR": (0, 62, -36), "foreR": (0, 0, -80), "armL": (0, -62, -36), "foreL": (0, 0, 80),
     "thighR": (32, 0, 0), "shinR": (58, 0, 0), "thighL": (-52, 0, 0), "shinL": (34, 0, 0)},
    {"spine": (14, 0, 0), "head": (-10, 0, 0), "armR": (0, 66, 0), "foreR": (0, 0, -80), "armL": (0, -66, 0), "foreL": (0, 0, 80),
     "thighR": (-28, 0, 0), "shinR": (84, 0, 0), "thighL": (-8, 0, 0), "shinL": (46, 0, 0)},
]
# Scared: arms flung up, looking back over a shoulder
Z_SCARED = {"spine": (-6, 0, 0), "neck": (-8, 0, 0), "head": (-10, 0, 20), "armR": (0, -46, -6), "foreR": (0, -30, 0), "armL": (0, 46, 6), "foreL": (0, 30, 0)}

# The stiff line dance: four counts on the beat, claws out
Z_DANCE = [
    {"spine": (8, 0, 10), "neck": (0, 0, 0), "head": (0, 10, 0), "armR": (0, -18, -24), "foreR": (0, 0, -70), "armL": (0, 18, 24), "foreL": (0, 0, 70),
     "thighR": (-26, -8, 0), "shinR": (34, 0, 0)},
    {"spine": (8, 0, 0), "neck": (0, 0, 0), "head": (6, 0, 0), "armR": (0, 24, -40), "foreR": (0, 0, -30), "armL": (0, -24, 40), "foreL": (0, 0, 30)},
    {"spine": (8, 0, -10), "neck": (0, 0, 0), "head": (0, -10, 0), "armR": (0, -18, -24), "foreR": (0, 0, -70), "armL": (0, 18, 24), "foreL": (0, 0, 70),
     "thighL": (-26, 8, 0), "shinL": (34, 0, 0)},
    {"spine": (8, 0, 0), "neck": (0, 0, 0), "head": (6, 0, 0), "armR": (0, 24, -40), "foreR": (0, 0, -30), "armL": (0, -24, 40), "foreL": (0, 0, 30)},
]
Z_QUEUE = {"spine": (10, 0, 0), "neck": (6, 0, 0), "head": (4, 0, 0), "armR": (0, 60, -16), "foreR": (0, 0, -30), "armL": (0, -60, 16), "foreL": (0, 0, 30)}
Z_JABBED = {"spine": (-12, 0, 0), "neck": (-12, 0, 0), "head": (-16, 0, 0), "armR": (0, -40, 0), "foreR": (0, -40, 0), "armL": (0, 40, 0), "foreL": (0, 40, 0),
            "thighR": (-12, 0, 0), "shinR": (20, 0, 0), "thighL": (-12, 0, 0), "shinL": (20, 0, 0)}

# Her lunge and bite. She stoops down to his arm.
ZF_LUNGE = {"spine": (24, 0, 0), "neck": (-6, 0, 0), "head": (-14, 0, 0), "armR": (0, 20, -66), "foreR": (0, 0, -18), "armL": (0, -20, 66), "foreL": (0, 0, 18), "thighR": (-22, 0, 0), "shinR": (20, 0, 0), "thighL": (12, 0, 0), "shinL": (14, 0, 0)}
ZF_BITE = {"drop": 0.2, "spine": (52, 0, 0), "neck": (-4, 0, 0), "head": (-10, 0, 0), "armR": (0, 34, -60), "foreR": (0, 0, -50), "armL": (0, -34, 60), "foreL": (0, 0, 50), "thighR": (-34, 0, 0), "shinR": (40, 0, 0), "thighL": (-20, 0, 0), "shinL": (40, 0, 0)}
ZF_CHEW = {**ZF_BITE, "head": (6, 0, 0)}
ZF_YANKED = {"spine": (32, 0, 0), "neck": (-12, 0, 0), "head": (-20, 0, 0), "armR": (0, 56, -30), "foreR": (0, 0, -14), "armL": (0, -56, 30), "foreL": (0, 0, 14)}
ZF_STARE = {"spine": (10, 0, 0), "neck": (-14, 0, 0), "head": (-14, 0, -6), "armR": (0, 70, -8), "foreR": (0, 6, -14), "armL": (0, -74, 6), "foreL": (0, -8, 16)}
ZF_REACHED = {**ZF_LUNGE, "spine": (40, 0, 0), "neck": (-14, 0, 0), "head": (-16, 0, 0)}
ZF_DEADPAN = {**ZF_STARE, "neck": (-10, 0, -28), "head": (-8, 0, -46)}

# In the cell
Z_HUFF = {"spine": (6, 0, 4), "neck": (-4, 0, 0), "head": (-4, 0, 0), "armR": (0, 26, -62), "foreR": (0, -46, -60), "armL": (0, -70, 4), "foreL": (0, -8, 12)}
Z_WOOZY = [{**Z_HUFF, "spine": (6, 12, 6), "neck": (0, 10, 0), "head": (-4, 16, 0), "armR": (0, 58, -20), "foreR": (0, 0, -40)},
           {**Z_HUFF, "spine": (6, -12, 2), "neck": (0, -10, 0), "head": (-4, -16, 0), "armR": (0, 62, -20), "foreR": (0, 0, -36)}]
Z_DROOL = [kneel(spine=(28, 0, 0), neck=(6, 0, 0), head=(8, 0, 0), armR=(0, 30, -56), foreR=(0, 0, -44), armL=(0, -30, 56), foreL=(0, 0, 44)),
           kneel(spine=(34, 0, 0), neck=(10, 0, 0), head=(14, 0, 0), armR=(0, 30, -56), foreR=(0, 0, -44), armL=(0, -30, 56), foreL=(0, 0, 44))]
Z_CHOKE = kneel(spine=(4, 0, 0), neck=(-16, 0, 0), head=(-26, 0, 0), armR=(0, 12, -68), foreR=(0, 0, -124), armL=(0, -12, 68), foreL=(0, 0, 124))

# ---- Pardo. The smurf hangs its arms from the rest pose: -X swings a limb forward, -Y lifts the R arm sideways, +Y lifts the L arm.
P_STAND = {"spine": (2, 0, 0), "armR": (0, -8, 0), "foreR": (5, 0, 0), "armL": (0, 8, 0), "foreL": (5, 0, 0)}
P_WALK = [
    {"body": (0, 0, 0, 4, 0, -3), "spine": (4, 0, 3), "armR": (-92, -8, 0), "foreR": (-4, 0, 0), "armL": (14, 12, 0), "foreL": (-8, 0, 0), "thighR": (-26, 0, 0), "shinR": (10, 0, 0), "thighL": (18, 0, 0), "shinL": (16, 0, 0)},
    {"body": (0, 0, 0.05, 4, 0, 0), "spine": (4, 0, 0), "armR": (-92, -8, 0), "foreR": (-4, 0, 0), "armL": (0, 12, 0), "foreL": (-8, 0, 0), "thighR": (-6, 0, 0), "shinR": (20, 0, 0), "thighL": (-4, 0, 0), "shinL": (26, 0, 0)},
    {"body": (0, 0, 0, 4, 0, 3), "spine": (4, 0, -3), "armR": (-92, -8, 0), "foreR": (-4, 0, 0), "armL": (-14, 12, 0), "foreL": (-8, 0, 0), "thighR": (18, 0, 0), "shinR": (16, 0, 0), "thighL": (-26, 0, 0), "shinL": (10, 0, 0)},
    {"body": (0, 0, 0.05, 4, 0, 0), "spine": (4, 0, 0), "armR": (-92, -8, 0), "foreR": (-4, 0, 0), "armL": (0, 12, 0), "foreL": (-8, 0, 0), "thighR": (-4, 0, 0), "shinR": (26, 0, 0), "thighL": (-6, 0, 0), "shinL": (20, 0, 0)},
]
P_LEAN = {"body": (0, 0, 0, 0, -9, 0), "spine": (-2, 0, -8), "head": (-6, 0, 6), "armR": (-12, -20, 0), "foreR": (-70, 0, 0), "armL": (0, 34, 0), "foreL": (-64, 0, 0), "thighR": (-12, -6, 0), "shinR": (18, 0, 0)}
P_GUNS = {"body": (0, 0, 0, -3, 0, 0), "spine": (-4, 0, 0), "head": (-10, 0, 0), "armR": (-98, -14, 0), "foreR": (-6, 0, 0), "armL": (-98, 14, 0), "foreL": (-6, 0, 0), "thighR": (-12, -8, 0), "shinR": (14, 0, 0)}
P_ROAST = {"spine": (8, 0, 0), "head": (8, 0, 0), "armR": (-72, -18, 0), "foreR": (-14, 0, 0), "armL": (0, 10, 0), "foreL": (-20, 0, 0)}
P_PROUD = {"body": (0, 0, 0, -4, 0, 0), "spine": (-6, 0, 0), "head": (-14, 0, 0), "armR": (-130, -12, 0), "foreR": (-20, 0, 0), "armL": (0, 34, 0), "foreL": (-64, 0, 0)}
P_COOL = {"spine": (-2, 0, 0), "head": (-5, 0, 6), "armR": (-44, -8, 0), "foreR": (-88, 0, 0), "armL": (-44, 8, 0), "foreL": (-88, 0, 0)}
P_BITTEN = {"body": (0, 0, 0, -6, 0, 0), "spine": (-6, 0, 0), "head": (-4, 0, 26), "armR": (-92, -26, 0), "foreR": (-8, 0, 0), "armL": (-30, 80, 0), "foreL": (-30, 0, 0)}
P_SHIVER = [{"spine": (8, 0, 0), "head": (2, 0, 3), "armR": (-34, 32, 0), "foreR": (-104, 0, 0), "armL": (-34, -32, 0), "foreL": (-104, 0, 0), "thighR": (-6, 6, 0), "thighL": (-6, -6, 0)},
            {"spine": (8, 0, 0), "head": (2, 0, -3), "armR": (-30, 36, 0), "foreR": (-108, 0, 0), "armL": (-30, -36, 0), "foreL": (-108, 0, 0), "thighR": (-6, 6, 0), "thighL": (-6, -6, 0)}]
P_REACH = {"spine": (4, 0, 0), "head": (-14, 0, 0), "armR": (-128, -10, 0), "foreR": (-14, 0, 0), "armL": (-30, 26, 0), "foreL": (-40, 0, 0), "thighR": (-16, 0, 0), "shinR": (16, 0, 0)}
P_YANK = {"body": (0, 0, 0, -14, 0, 0), "spine": (-14, 0, 0), "head": (-10, 0, 0), "armR": (-60, -30, 0), "foreR": (-40, 0, 0), "armL": (10, 40, 0), "foreL": (-20, 0, 0), "thighL": (20, 0, 0), "shinL": (12, 0, 0), "thighR": (-22, 0, 0), "shinR": (18, 0, 0)}
P_SHOW = {"spine": (-2, 0, 0), "head": (-8, 0, 0), "armR": (-100, -18, 0), "foreR": (-10, 0, 0), "armL": (0, 10, 0), "foreL": (-10, 0, 0)}
P_AIM = {"spine": (6, 0, 0), "armR": (-78, -20, 0), "foreR": (-10, 0, 0), "armL": (-20, 10, 0), "foreL": (-30, 0, 0), "thighR": (-20, 0, 0), "shinR": (14, 0, 0)}
P_JAB = {"body": (0, 0, 0, 8, 0, 0), "spine": (12, 0, 0), "armR": (-96, -8, 0), "foreR": (0, 0, 0), "armL": (6, 18, 0), "foreL": (-16, 0, 0), "thighR": (-34, 0, 0), "shinR": (16, 0, 0), "thighL": (18, 0, 0), "shinL": (12, 0, 0)}
P_PANIC = {"body": (0, 0, 0, -8, 0, 0), "spine": (-10, 0, 0), "head": (-30, 0, 0), "armR": (-30, -130, 0), "foreR": (-40, 0, 0), "armL": (-30, 130, 0), "foreL": (-40, 0, 0), "thighR": (-16, -10, 0), "shinR": (24, 0, 0), "thighL": (-16, 10, 0), "shinL": (24, 0, 0)}
P_FALL = {"body": (0, 0, 0, -18, 0, 0), "spine": (-18, 0, 0), "head": (-24, 0, 0), "armR": (-10, -160, 0), "foreR": (-10, 0, 0), "armL": (-10, 160, 0), "foreL": (-10, 0, 0), "thighR": (-40, -14, 0), "shinR": (50, 0, 0), "thighL": (-30, 14, 0), "shinL": (60, 0, 0)}
