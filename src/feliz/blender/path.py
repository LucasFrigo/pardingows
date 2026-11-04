# The curved world's geometry, shared by the world and shot scripts. The ground is a log lying along X, its top at z = 0.
# A place on it has a side position x and an arc distance s along the walk. Rotating the log by -s/R brings that place to the top.
# The pardo faces -Y, so ground ahead of him (larger s) sits on the -Y side.
import math

R = 22.0
FLAT = 13.0  # half width of the grass
BEACH = 19.0  # where the sand reaches the water
DROP = 1.3  # how far the sand falls from grass to its end
WATER = 0.6  # water level below the grass


def radius(x):
    """Log radius at side position x."""
    a = abs(x)
    if a <= FLAT:
        return R
    u = min((a - FLAT) / (BEACH - FLAT), 1.0)
    r = R - DROP * u * u * (3 - 2 * u)
    return r - max(a - BEACH, 0) * 0.5


def local(x, s, lift=0.0):
    """Position on the log in the log's own space, and the rotation that stands something upright there."""
    t = s / R
    r = radius(x) + lift
    return (x, -r * math.sin(t), r * math.cos(t)), (t, 0.0, 0.0)


def ground(x, y, roll=0.0):
    """World height of the ground at (x, y). The log's axis is at z = -R, so this doesn't depend on its rotation."""
    r = radius(x)
    return math.sqrt(max(r * r - y * y, 0.0)) - R


def rot_for(s):
    """Log rotation that brings arc distance s to the top."""
    return -s / R


# Where each scene happens along the walk. The walk itself runs from HOME to the nest, the rest are stops the log rolls to between cuts.
HOME = 0.0
NEST = 9.2
PIT = 13.5
CARTA = 18.0
REPITA = 27.0
PRACA = 42.0
CLOSE = 56.0
BERG = 66.0
CREW = 78.0
CELULAR = 90.0
AERO = 102.0
CHOQUE = 116.0
