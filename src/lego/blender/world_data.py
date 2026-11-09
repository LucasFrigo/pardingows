# Where each world sits and how it looks: origin, sky colours (horizon, zenith, strength), lens and default camera. Read by the sets, the look and the shots.
SPACING = 80.0
SETS = ["rua", "calendario", "cofre", "parque", "corrida", "praca", "interrogatorio", "quarto"]
SKY = {
    "rua": ("cfeaff", "4f9fe8", 1.0),
    "calendario": ("fff0d8", "d8c8a8", 0.5),
    "cofre": ("1c2230", "0c1018", 0.35),
    "parque": ("d9f1ff", "58ace8", 1.0),
    "corrida": ("ffd7a8", "c9796e", 0.85),
    "praca": ("dbeeff", "5ca5e6", 1.0),
    "interrogatorio": ("10141c", "080a0e", 0.2),
    "quarto": ("1c2548", "0a0f24", 0.35),
}


def origin(name):
    return (SETS.index(name) * SPACING, 0.0, 0.0)
