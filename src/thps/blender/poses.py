# Pose library. Upper-body bones in degrees (see lib.set_bone_rot); legs follow the board through IK.
# "body" is the hip offset above the deck in smurf units: (dx, dy, dz, rx, ry, rz).
# Travel direction is +X, the character stands sideways facing -Y, so head +Z looks down the road.
REST = {}

RIDE = {
    "body": (0, 0, -0.35, 8, 0, 25),
    "spine": (8, 0, 5), "head": (0, 0, 40),
    "armR": (10, -35, 0), "foreR": (20, 0, 0), "armL": (-5, 35, 0), "foreL": (20, 0, 0),
}
PUSH = {
    "body": (0, 0, -0.55, 12, -4, 30),
    "spine": (8, 0, 6), "head": (-16, 0, 30),
    "armR": (35, -30, 0), "foreR": (25, 0, 0), "armL": (-35, 35, 0), "foreL": (25, 0, 0),
}
CROUCH = {
    "body": (0, 0, -0.95, 10, 0, 15),
    "spine": (10, 0, 5), "head": (-16, 0, 38),
    "armR": (30, -55, 0), "foreR": (30, 0, 0), "armL": (30, 55, 0), "foreL": (30, 0, 0),
}
OLLIE = {
    "body": (0, 0, -0.75, 6, 10, 15),
    "spine": (10, 8, 5), "head": (-8, -6, 40),
    "armR": (-10, -105, 0), "foreR": (15, 0, 0), "armL": (-10, 105, 0), "foreL": (15, 0, 0),
}
GRAB = {  # tucked, one hand on the board
    "body": (0, 0, -1.25, 12, 0, 10),
    "spine": (16, 0, 0), "head": (-24, 0, 42),
    "armR": (-25, -15, 0), "foreR": (-25, 0, 0), "armL": (-20, 120, 0), "foreL": (10, 0, 0),
}
GRIND = {
    "body": (0, 0, -0.6, 10, 16, 20),
    "spine": (12, 12, 5), "head": (-6, -8, 45),
    "armR": (10, -90, 0), "foreR": (10, 0, 0), "armL": (10, 75, 0), "foreL": (20, 0, 0),
}
STAND = {  # off the board, standing
    "body": (0, 0, 0, 0, 0, 0),
    "spine": (2, 0, 0), "head": (0, 0, 0),
    "armR": (0, -8, 0), "foreR": (5, 0, 0), "armL": (0, 8, 0), "foreL": (5, 0, 0),
}
HANDS_UP = {  # the head is huge, so the arms go out wide and bend up beside it
    "body": (0, 0, 0, -3, 0, 0),
    "spine": (-3, 0, 0), "head": (2, 0, 0),
    "armR": (0, -95, 0), "foreR": (0, -80, 0), "armL": (0, 95, 0), "foreL": (0, 80, 0),
}
HAND_OUT = {  # offering the phone: right forearm reaching towards camera
    "body": (0, 0, 0, 0, 0, 0),
    "spine": (4, 0, 0), "head": (6, 0, 0),
    "armL": (-68, 14, 0), "foreL": (-28, 0, 0), "armR": (0, -8, 0), "foreR": (5, 0, 0),
}
BAIL_A = {  # flailing in the air
    "body": (0, 0, 0, 0, 0, 0),
    "spine": (-25, 10, 15), "head": (-30, 15, 0),
    "armR": (-40, -130, 0), "foreR": (-30, 0, 0), "armL": (50, 140, 0), "foreL": (40, 0, 0),
}
SPECIAL = {  # the GOONAR pose: arms flung wide, head back
    "body": (0, 0, -0.5, -12, 0, 0),
    "spine": (-16, 0, 0), "head": (-26, 0, 0),
    "armR": (-14, -112, 0), "foreR": (-8, 0, 0), "armL": (-14, 112, 0), "foreL": (-8, 0, 0),
}

PLEAD = {  # begging for the board back, both hands forward
    "body": (0, 0, 0, 10, 0, 0),
    "spine": (10, 0, 0), "head": (-14, 0, 0),
    "armR": (-70, -8, 0), "foreR": (-25, 0, 0), "armL": (-70, 8, 0), "foreL": (-25, 0, 0),
}
for off_board in (STAND, HANDS_UP, HAND_OUT, BAIL_A, PLEAD):
    off_board["free"] = True

# Cop poses. Same axes; his left arm is on the +X side, and the rest pose is an A-pose.
COP_BONES = {
    "spine": "spine_02", "chest": "chest_03", "head": "head_05",
    "armL": "LeftArm_07", "foreL": "LeftElbow_08", "armR": "RightArm_014", "foreR": "RightElbow_015",
}
COP_STAND = {"armL": (0, 38, 0), "armR": (0, -38, 0), "foreL": (-8, 0, 0), "foreR": (-8, 0, 0)}
COP_DEMAND = {"chest": (6, 0, 0), "head": (6, 0, 0), "armL": (0, 38, 0), "armR": (-72, -32, 0), "foreL": (-8, 0, 0), "foreR": (-18, 0, 0)}
# "aim" gives arm directions in the cop's own axes, for poses where the hand must reach a place
COP_PHONE = {"spine": (5, 0, 0), "chest": (6, 0, 0), "head": (22, -8, -28), "armL": (0, 38, 0), "foreL": (-8, 0, 0),
             "aim": {"armR": (-0.2, -0.6, -0.75), "foreR": (0.25, -0.6, 0.75)}}  # hand out past the face, so the phone clears it
COP_SHOCK = {"spine": (-8, 0, 0), "chest": (-8, 0, 0), "head": (-10, 0, 0),
             "aim": {"armR": (-0.35, -0.5, -0.75), "foreR": (0.15, -0.55, 0.85), "armL": (0.7, -0.3, -0.45), "foreL": (-0.35, -0.55, 0.9)}}
COP_OVERHEAD = {"chest": (-6, 0, 0), "head": (-14, 0, 0), "armL": (0, -105, 0), "armR": (0, 105, 0), "foreL": (0, -25, 0), "foreR": (0, 25, 0)}
COP_FLAT = {"armL": (0, -40, 0), "armR": (0, 40, 0), "head": (-10, 0, 0)}

ALL = dict(RIDE=RIDE, PUSH=PUSH, CROUCH=CROUCH, OLLIE=OLLIE, GRAB=GRAB, GRIND=GRIND, STAND=STAND,
           HANDS_UP=HANDS_UP, HAND_OUT=HAND_OUT, BAIL_A=BAIL_A, SPECIAL=SPECIAL)
