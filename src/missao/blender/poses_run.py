# Poses for this video, all in degrees in the rest axes (see lib.set_bone_rot). +X bends forward, so -X swings a hanging limb out in front.
# The smurf is off the board throughout, so every pose also carries its legs. Everyone faces -Y, and "R" is always the +X side.
STAND = {"spine": (2, 0, 0), "armR": (0, -8, 0), "foreR": (5, 0, 0), "armL": (0, 8, 0), "foreL": (5, 0, 0)}

# Run cycle: two contacts and two passing poses, stepped on the 15 fps pose grid
RUN = [
    {"body": (0, 0, 0.0, 12, 0, -5), "spine": (8, 0, 6), "head": (-10, 0, -4),
     "armR": (42, -18, 0), "foreR": (-50, 0, 0), "armL": (-48, 18, 0), "foreL": (-65, 0, 0),
     "thighR": (-48, 0, 0), "shinR": (24, 0, 0), "thighL": (34, 0, 0), "shinL": (58, 0, 0)},
    {"body": (0, 0, 0.14, 12, 0, 0), "spine": (8, 0, 0), "head": (-10, 0, 0),
     "armR": (8, -18, 0), "foreR": (-60, 0, 0), "armL": (-8, 18, 0), "foreL": (-60, 0, 0),
     "thighR": (-8, 0, 0), "shinR": (46, 0, 0), "thighL": (-26, 0, 0), "shinL": (82, 0, 0)},
    {"body": (0, 0, 0.0, 12, 0, 5), "spine": (8, 0, -6), "head": (-10, 0, 4),
     "armR": (-48, -18, 0), "foreR": (-65, 0, 0), "armL": (42, 18, 0), "foreL": (-50, 0, 0),
     "thighR": (34, 0, 0), "shinR": (58, 0, 0), "thighL": (-48, 0, 0), "shinL": (24, 0, 0)},
    {"body": (0, 0, 0.14, 12, 0, 0), "spine": (8, 0, 0), "head": (-10, 0, 0),
     "armR": (-8, -18, 0), "foreR": (-60, 0, 0), "armL": (8, 18, 0), "foreL": (-60, 0, 0),
     "thighR": (-26, 0, 0), "shinR": (82, 0, 0), "thighL": (-8, 0, 0), "shinL": (46, 0, 0)},
]
JUMP = {"body": (0, 0, 0, 4, 0, 0), "spine": (4, 0, 0), "head": (-8, 0, 0),
        "armR": (-20, -70, 0), "foreR": (-30, 0, 0), "armL": (-20, 70, 0), "foreL": (-30, 0, 0),
        "thighR": (-62, 0, 0), "shinR": (70, 0, 0), "thighL": (18, 0, 0), "shinL": (60, 0, 0)}
ROLL = {"body": (0, 0, -0.4, 34, 0, 0), "spine": (26, 0, 0), "head": (8, 0, 0),
        "armR": (-30, -14, 0), "foreR": (-80, 0, 0), "armL": (-30, 14, 0), "foreL": (-80, 0, 0),
        "thighR": (-86, 0, 0), "shinR": (100, 0, 0), "thighL": (-86, 0, 0), "shinL": (100, 0, 0)}
STUMBLE = {"body": (0, 0, -0.1, 24, 0, 8), "spine": (18, 0, 8), "head": (-16, 0, 0),
           "armR": (-70, -50, 0), "foreR": (-20, 0, 0), "armL": (30, 10, 0), "foreL": (-30, 0, 0),
           "thighR": (-30, 0, 0), "shinR": (30, 0, 0), "thighL": (20, 0, 0), "shinL": (40, 0, 0)}
HELD = {"body": (0, 0, 0, 16, 0, 0), "spine": (16, 0, 10), "head": (-20, 0, -18),
        "armR": (0, -86, 0), "foreR": (-4, 0, 0), "armL": (-40, 26, 0), "foreL": (-70, 0, 0),
        "thighR": (-22, 0, 0), "shinR": (20, 0, 0), "thighL": (26, 0, 0), "shinL": (22, 0, 0)}

# Story poses for the hero
ASLEEP = {"body": (0, 0, 0, 0, 0, 0), "spine": (0, 0, 0), "head": (0, 0, 16), "armR": (0, -22, 0), "armL": (0, 22, 0),
          "thighR": (-6, 0, 0), "shinR": (10, 0, 0), "thighL": (8, 0, 0), "shinL": (14, 0, 0)}
SIT_UP = {"spine": (2, 0, 0), "head": (-14, 0, 0), "armR": (-30, -60, 0), "foreR": (-90, 0, 0), "armL": (-30, 60, 0), "foreL": (-90, 0, 0),
          "thighR": (-84, 0, 0), "shinR": (6, 0, 0), "thighL": (-84, 0, 0), "shinL": (6, 0, 0)}
PANIC = {"spine": (-8, 0, 0), "head": (-12, 0, 0), "armR": (-20, -120, 0), "foreR": (-70, 0, 0), "armL": (-20, 120, 0), "foreL": (-70, 0, 0),
         "thighR": (-84, 0, 0), "shinR": (6, 0, 0), "thighL": (-84, 0, 0), "shinL": (6, 0, 0)}
THINK = {"spine": (-2, 0, 0), "head": (-22, 0, 8), "armR": (-100, -10, 0), "foreR": (-96, 0, 0), "armL": (0, 10, 0), "foreL": (5, 0, 0)}
LIFT = {"body": (0, 0, -0.5, 36, 0, 0), "spine": (32, 0, 0), "head": (-28, 0, 0), "armR": (-92, -6, 0), "foreR": (-14, 0, 0), "armL": (-92, 6, 0), "foreL": (-14, 0, 0),
        "thighR": (-52, 0, 0), "shinR": (72, 0, 0), "thighL": (-52, 0, 0), "shinL": (72, 0, 0)}
GOT_IT = {"spine": (-4, 0, 0), "head": (-8, 0, 0), "armR": (-20, -130, 0), "foreR": (-10, 0, 0), "armL": (0, 10, 0), "foreL": (5, 0, 0)}
RECOIL = {"body": (0, 0, 0, -10, 0, 0), "spine": (-14, 0, 0), "head": (-14, 0, -16), "armR": (-80, -10, 0), "foreR": (-115, 0, 0), "armL": (0, 44, 0), "foreL": (-20, 0, 0),
          "thighR": (-10, 0, 0), "shinR": (10, 0, 0), "thighL": (12, 0, 0), "shinL": (10, 0, 0)}
SHOUT = {"body": (0, 0, 0, -4, 0, 0), "spine": (-14, 0, 0), "head": (-18, 0, 0), "armR": (-10, -110, 0), "foreR": (-20, 0, 0), "armL": (-10, 110, 0), "foreL": (-20, 0, 0),
         "thighR": (-20, -14, 0), "thighL": (-20, 14, 0)}
BITE = {"spine": (4, 0, 0), "head": (8, 0, 0), "armR": (-92, -30, 0), "foreR": (-82, 0, 0), "armL": (-92, 30, 0), "foreL": (-82, 0, 0)}

REACH_UP = {"body": (0, 0, 0, -4, 0, 0), "spine": (-4, 0, 0), "head": (-6, 0, 0), "armR": (-120, -6, 0), "foreR": (-6, 0, 0), "armL": (0, 44, 0), "foreL": (-30, 0, 0),
            "thighR": (-22, 0, 0), "shinR": (20, 0, 0), "thighL": (26, 0, 0), "shinL": (22, 0, 0)}

# Humans start in their own rest pose, T for the Mixamo pair and A for the base man. "R" is the +X side.
# Rotating +Y drops the R arm, rotating -Z swings it forward, as on the Planeta chimps.
H_STAND = {"armR": (0, 72, 0), "foreR": (0, 8, 0), "armL": (0, -72, 0), "foreL": (0, -8, 0)}
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
H_REACH = {"spine": (12, 0, 0), "head": (-12, 0, 0), "armR": (0, 8, -80), "foreR": (0, 0, -8), "armL": (0, -8, 80), "foreL": (0, 0, 8)}
H_BEG = {"spine": (22, 0, 0), "head": (-20, 0, 0), "armR": (0, 4, -66), "foreR": (0, -8, -12), "armL": (0, -4, 66), "foreL": (0, 8, 12)}
H_GRAB = {"spine": (14, 0, 0), "head": (-14, 0, 0), "armR": (0, 40, -74), "foreR": (0, 0, -4), "armL": (0, -70, 0), "foreL": (0, -10, 0)}
H_SIT = {"spine": (10, 0, 0), "head": (-6, 0, 0), "armR": (0, 58, -22), "foreR": (0, 0, -48), "armL": (0, -58, 22), "foreL": (0, 0, 48),
         "thighR": (-86, 0, 0), "shinR": (78, 0, 0), "thighL": (-86, 0, 0), "shinL": (78, 0, 0)}
H_PEE = {"spine": (-6, 0, 0), "head": (14, 0, 0), "armR": (0, 62, -30), "foreR": (0, 0, -40), "armL": (0, -62, 30), "foreL": (0, 0, 40), "thighR": (-4, -6, 0), "thighL": (-4, 6, 0)}
H_POINT = {"spine": (2, 0, 0), "head": (-4, 0, 0), "armR": (0, 2, -88), "foreR": (0, 0, -4), "armL": (0, -30, 40), "foreL": (0, 0, 60)}
