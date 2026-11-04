# Poses for this video, all in degrees in the rest axes (see lib.set_bone_rot). +X bends forward, so -X swings a hanging limb out in front.
# Smurfs are off the board throughout, so every pose is "free" and also carries its legs.
STAND = {"spine": (2, 0, 0), "armR": (0, -8, 0), "foreR": (5, 0, 0), "armL": (0, 8, 0), "foreL": (5, 0, 0)}
HOP_A = {"body": (0, 0, 0, 6, 0, 0), "spine": (6, 0, 0), "head": (-4, 0, 0),
         "armR": (28, -24, 0), "foreR": (-18, 0, 0), "armL": (-30, 24, 0), "foreL": (-18, 0, 0),
         "thighR": (-30, 0, 0), "shinR": (18, 0, 0), "thighL": (24, 0, 0), "shinL": (24, 0, 0)}
HOP_B = {"body": (0, 0, 0, 6, 0, 0), "spine": (6, 0, 0), "head": (-4, 0, 0),
         "armR": (-30, -24, 0), "foreR": (-18, 0, 0), "armL": (28, 24, 0), "foreL": (-18, 0, 0),
         "thighR": (24, 0, 0), "shinR": (24, 0, 0), "thighL": (-30, 0, 0), "shinL": (18, 0, 0)}
LAND = {"body": (0, 0, -0.18, 12, 0, 0), "spine": (10, 0, 0), "head": (-8, 0, 0),
        "armR": (0, -50, 0), "foreR": (-10, 0, 0), "armL": (0, 50, 0), "foreL": (-10, 0, 0)}
INSULTED = {"body": (0, 0, 0, -6, 0, 0), "spine": (-6, 0, 0), "head": (2, 0, 0),
            "armR": (0, -95, 0), "foreR": (0, -80, 0), "armL": (0, 95, 0), "foreL": (0, 80, 0)}
SUNBATHE = {"body": (0, 0, 0, -8, 0, 0), "spine": (-10, 0, 0), "head": (-16, 0, 0),
            "armR": (-10, -100, 0), "foreR": (-6, 0, 0), "armL": (-10, 100, 0), "foreL": (-6, 0, 0)}
CRUSHED = {"spine": (20, 0, 0), "head": (24, 0, 0), "armR": (0, -80, 0), "armL": (0, 80, 0),
           "thighR": (0, -25, 0), "thighL": (0, 25, 0)}
POINT = {"spine": (0, 0, 0), "head": (-4, 0, 0), "armR": (-98, -12, 0), "foreR": (-6, 0, 0), "armL": (0, 10, 0), "foreL": (5, 0, 0)}
DENY = {"body": (0, 0, 0, 8, 0, 0), "spine": (10, 0, 0), "head": (6, 0, 0),
        "armR": (-20, -112, 0), "foreR": (-8, 0, 0), "armL": (-20, 112, 0), "foreL": (-8, 0, 0)}
FACE = {"spine": (0, 0, 0), "head": (5, 0, 0), "armR": (0, -8, 0), "foreR": (5, 0, 0), "armL": (0, 8, 0), "foreL": (5, 0, 0)}
AIM = {"spine": (2, 0, 0), "head": (0, 0, 0), "armR": (-86, -8, 0), "foreR": (-4, 0, 0), "armL": (-10, 14, 0), "foreL": (-12, 0, 0),
       "thighR": (-8, 0, 0), "thighL": (8, 0, 0)}

# Chimps stand in a T as built. +X is their R side. Rotating +Y drops the R arm, rotating -Z swings it forward.
CH_STAND = {"armR": (0, 68, 0), "foreR": (0, 12, 0), "armL": (0, -68, 0), "foreL": (0, -12, 0)}
CH_HOP_A = {"spine": (5, 0, 0), "armR": (20, 52, 0), "foreR": (0, 16, 0), "armL": (-20, -52, 0), "foreL": (0, -16, 0),
            "thighR": (-26, 0, 0), "shinR": (14, 0, 0), "thighL": (20, 0, 0), "shinL": (20, 0, 0)}
CH_HOP_B = {"spine": (5, 0, 0), "armR": (-20, 52, 0), "foreR": (0, 16, 0), "armL": (20, -52, 0), "foreL": (0, -16, 0),
            "thighR": (20, 0, 0), "shinR": (20, 0, 0), "thighL": (-26, 0, 0), "shinL": (14, 0, 0)}
CH_POINT = {"spine": (-6, 0, 0), "head": (-6, 0, 0), "armR": (0, 0, -86), "armL": (0, -62, 0), "foreL": (0, -60, 0)}
CH_JEER = {"spine": (-10, 0, 0), "head": (-12, 0, 0), "armR": (0, -48, 0), "foreR": (0, -20, 0), "armL": (0, 48, 0), "foreL": (0, 20, 0)}
CH_AIM = {"spine": (2, 0, 0), "head": (0, 0, 0), "armR": (0, 0, -88), "armL": (0, -68, 0), "foreL": (0, -12, 0),
          "thighR": (-8, 0, 0), "thighL": (8, 0, 0)}

# César's Mixamo bones. His left arm is on the +X side and rotating it +Y drops it.
CESAR_BONES = {"spine": "mixamorig:Spine1_03", "chest": "mixamorig:Spine2_04", "neck": "mixamorig:Neck_05", "head": "mixamorig:Head_06",
               "armL": "mixamorig:LeftArm_08", "foreL": "mixamorig:LeftForeArm_09", "armR": "mixamorig:RightArm_027", "foreR": "mixamorig:RightForeArm_028"}
C_STAND = {"armL": (0, 66, 0), "foreL": (0, 10, 0), "armR": (0, -66, 0), "foreR": (0, -10, 0)}
C_AWAY = {**C_STAND, "head": (14, 0, 34), "neck": (0, 0, 10)}
C_GLARE = {**C_STAND, "chest": (6, 0, 0), "head": (20, 0, 0)}
C_SHOUT = {"spine": (8, 0, 0), "chest": (12, 0, 0), "head": (16, 0, 0), "armL": (-18, 44, 0), "foreL": (-30, 30, 0), "armR": (-18, -44, 0), "foreR": (-30, -30, 0)}
C_ROAR = {"spine": (-4, 0, 0), "chest": (2, 0, 0), "neck": (10, 0, 0), "head": (22, 0, 0), "armL": (0, -38, 0), "foreL": (0, -28, 0), "armR": (0, 38, 0), "foreR": (0, 28, 0)}
