# Where the runner is at any moment. The street runs along -Y, and everything in a lane is placed from these numbers,
# so a prop placed at dist(word time) reaches him exactly on that word.
LANES = (-2.0, 0.0, 2.0)
ROAD = 3.8      # half width of the asphalt
FRONT = 6.4     # house fronts stand this far from the middle of the road
SPEED = 11.0    # m/s until the dingow grabs him
SLOW = 2.2      # m/s while he drags the dingow along


def dist(v, grab):
    """Metres run by video time v. Eases from SPEED down to SLOW over half a second after the grab."""
    if v <= grab:
        return SPEED * v
    u = min((v - grab) / 0.5, 1.0)
    eased = SPEED * (v - grab) - (SPEED - SLOW) * (0.5 * u * u * 0.5 if u < 1 else 0.25 + (v - grab - 0.5))
    return SPEED * grab + eased


def run_y(v, grab):
    return -dist(v, grab)
