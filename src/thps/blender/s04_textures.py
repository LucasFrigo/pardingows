# Procedural PS1-sized textures for the plaza. Written once to blender/solucao/textures/.
import bpy, os
import numpy as np

OUT = r"C:\Users\lukeg\Projetos\pardingows\blender\solucao\textures"
rng = np.random.default_rng(1987)


def save(name, rgb):
    h, w, _ = rgb.shape
    img = bpy.data.images.get(name) or bpy.data.images.new(name, w, h, alpha=True)
    if tuple(img.size) != (w, h):
        img.scale(w, h)
    rgba = np.dstack([np.clip(rgb, 0, 1), np.ones((h, w))]).astype(np.float32)
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = os.path.join(OUT, name + ".png")
    img.file_format = "PNG"
    img.save()


def noise(h, w, amp, cell=1):
    n = rng.normal(0, amp, (h // cell + 1, w // cell + 1))
    return np.kron(n, np.ones((cell, cell)))[:h, :w]


def tone(base, n):
    return np.dstack([np.full(n.shape, c) + n for c in base])


def lines(img, pts, color, thick=2):
    """Draws a polyline by stamping squares. Enough for tags."""
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        steps = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for t in np.linspace(0, 1, steps):
            x, y = int(x0 + (x1 - x0) * t), int(y0 + (y1 - y0) * t)
            img[max(y - thick, 0):y + thick, max(x - thick, 0):x + thick] = color


# Concrete: grey with slab joints
c = tone((0.58, 0.57, 0.54), noise(64, 64, 0.035, 2))
c[0:1, :] -= 0.16
c[:, 0:1] -= 0.16
save("tx_concrete", c)

# Ledge top: paler with a dark waxed streak
l = tone((0.72, 0.70, 0.66), noise(64, 64, 0.025, 2))
l[26:38, :] -= 0.18
save("tx_ledge", l)

# Asphalt: dark with speckle
save("tx_asphalt", tone((0.20, 0.20, 0.22), noise(128, 128, 0.03)))

# Pedra portuguesa: small stones in a bold black-and-white wave, like the Sao Paulo pavement
H = 128
yy, xx = np.mgrid[0:H, 0:H]
wave = np.sin((xx + yy) * 2 * np.pi / H) + np.sin((xx - yy) * 4 * np.pi / H) * 0.5
stones = np.where(wave > 0.25, 0.14, 0.82)
cell = rng.normal(0, 0.05, (H // 4 + 1, H // 4 + 1))
stones = stones + np.kron(cell, np.ones((4, 4)))[:H, :H]
stones[::4, :] = stones[::4, :] * 0.72
stones[:, ::4] = stones[:, ::4] * 0.72
save("tx_pedra", np.dstack([stones, stones * 0.98, stones * 0.94]))

# Tower facade: dirty concrete, window grid, some lit
W = 128
f = tone((0.46, 0.44, 0.42), noise(W, W, 0.03, 2))
for iy in range(4):
    for ix in range(4):
        x, y = 4 + ix * 31, 5 + iy * 31
        lit = rng.random()
        col = (0.95, 0.82, 0.45) if lit < 0.2 else (0.12, 0.17, 0.26) if lit < 0.8 else (0.28, 0.34, 0.42)
        f[y:y + 20, x:x + 24] = col
        f[y + 20:y + 22, x - 1:x + 25] = (0.66, 0.64, 0.6)
        f[y + 22:y + 30, x + 2:x + 22] -= 0.05  # rain streaks
save("tx_tower", f)

# Copan-style facade: horizontal concrete louvres
g = np.zeros((64, 64, 3))
g[:] = (0.86, 0.84, 0.78)
for y in range(0, 64, 8):
    g[y + 4:y + 8, :] = (0.16, 0.19, 0.25)
save("tx_louvre", g + tone((0, 0, 0), noise(64, 64, 0.015, 2)))

# Picha\u00e7\u00e3o: tall angular runes across a stained wall
S = 256
t = tone((0.62, 0.60, 0.56), noise(S, S, 0.03, 2))
t[150:, :] -= np.linspace(0, 0.12, S - 150)[:, None, None]
for row, (y0, y1) in enumerate(((12, 74), (92, 150), (172, 240))):
    x = 6 + row * 7
    while x < S - 18:
        w = int(rng.integers(8, 15))
        k = rng.integers(0, 4)
        top, bot = y0 + int(rng.integers(0, 6)), y1 - int(rng.integers(0, 6))
        if k == 0:
            pts = [(x, bot), (x, top), (x + w, top), (x + w, bot)]
        elif k == 1:
            pts = [(x, top), (x + w, top), (x, bot), (x + w, bot)]
        elif k == 2:
            pts = [(x, bot), (x + w // 2, top), (x + w, bot)]
        else:
            pts = [(x + w, top), (x, top), (x, bot), (x + w, bot)]
        lines(t, pts, (0.03, 0.03, 0.04), 1)
        x += w + int(rng.integers(5, 10))
save("tx_pichacao", t)
print("textures ok")
