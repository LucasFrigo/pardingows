# Snaps each word to the nearest real vocal attack within 80 ms, measures the band's bar hits and writes the per-frame vocal loudness.
#   uv run --no-project --python 3.11 --with librosa --with soundfile --with matplotlib python src/lego/sync/attacks.py
# In:  blender/lego/sync/align.json (forced aligner), the Whisper times below, the Demucs stems
# Out: blender/lego/sync/attacks.json (candidates and the snap table), src/lego/vocal_env.json,
#      blender/lego/review/01-vocais-zoom.png (spectrogram strips with the words marked)
import json
import pathlib
import sys

import librosa
import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parents[3]
SYNC = ROOT / "blender" / "lego" / "sync"
STEMS = SYNC / "htdemucs"
REVIEW = ROOT / "blender" / "lego" / "review"
T0 = 214.0
SR = 22050
HOP = 110  # 5 ms
MAX_SNAP = 0.080
BAR = 1.92
START, END, FPS = 218.40, 249.12, 30
FRAMES = round((END - START) * FPS)
sys.stdout.reconfigure(encoding="utf-8")

# Each entry is (caption word, Whisper time on the stem). The aligner (align.json) is the seed, Whisper the cross-check.
WORDS = [
    ("1", [("hoje", 218.54), ("eu", 218.98), ("não", 219.14), ("fico", 219.36), ("puto", 219.84), ("fodase", 220.40), ("israel", 221.08)]),
    ("2", [("terça", 221.86), ("dos", 222.52), ("pardos", 222.78), ("é", 223.24), ("a", 223.62), ("data", 223.80), ("vou", 224.08), ("ficar", 224.40), ("na", 224.86), ("moral", 225.22)]),
    ("3", [("pausar", 225.66), ("os", 226.30), ("planos", 226.60), ("de", 227.10), ("roubar", 227.38), ("a", 227.86), ("La", 228.16), ("Casa", 228.44), ("de", 228.72), ("Papel", 229.08)]),
    ("4", [("sem", 229.88), ("menisquencia", 230.42), ("triste", 231.38), ("sem", 231.74), ("pensar", 232.06), ("nada", 232.56), ("mal", 233.04)]),
    ("5", [("Em", 233.38), ("Busca", 233.78), ("da", 234.18), ("Felicidade", 234.62), ("é", 235.66), ("o", 235.90), ("remix", 236.04), ("dos", 236.52), ("pardos", 236.90)]),
    ("6", [("sessenta", 237.40), ("e", 238.14), ("sete", 238.16), ("ponto", 238.66), ("nove", 238.98), ("noia", 239.48), ("por", 240.02), ("metro", 240.30), ("quadrado", 240.66)]),
    ("7", [("eu", 241.18), ("quero", 241.42), ("saber", 241.86), ("quem", 242.38), ("é", 242.70), ("que", 243.02), ("vai", 243.40), ("bolar", 243.80), ("mais", 244.38), ("um", 244.62), ("baseado", 244.86)]),
    ("8", [("pra", 245.70), ("eu", 246.02), ("chegar", 246.30), ("em", 246.60), ("casa", 246.84), ("e", 247.16), ("dormir", 247.48), ("bem", 247.88), ("r3t#ard$do", 248.22)]),
]
ALIGN = json.loads((SYNC / "align.json").read_text(encoding="utf-8"))
SEEDS = []
for key, words in WORDS:
    al = ALIGN[key]["words"]
    assert len(al) == len(words), key
    SEEDS.append([(w, r["t0"], wt, r["score"], r["t1"]) for (w, wt), r in zip(words, al)])

v, sr = librosa.load(STEMS / "vocals.wav", sr=SR, mono=True)
times = lambda n: T0 + np.arange(n) * HOP / sr


def smooth(x, n):
    return np.convolve(x, np.ones(n) / n, mode="same")


# Evidence 1: spectral flux in the voice band, which catches consonants and syllables that start over a held note.
S = np.abs(librosa.stft(v, n_fft=512, hop_length=HOP))
mel = librosa.power_to_db(librosa.feature.melspectrogram(S=S**2, sr=sr, n_mels=64, fmin=120, fmax=9000), ref=np.max)
flux = np.maximum(0, mel[:, 2:] - mel[:, :-2]).mean(axis=0)
flux = np.concatenate(([0, 0], flux))
flux_s = smooth(flux, 3)

# Evidence 2: loudness rising out of a dip of at least 4 dB.
rms = librosa.feature.rms(y=v, frame_length=441, hop_length=HOP, center=True)[0]
db = 20 * np.log10(smooth(rms, 3) + 1e-5)
slope = np.gradient(db)

n = min(len(flux_s), len(db))
flux_s, db, slope = flux_s[:n], db[:n], slope[:n]
T = times(n)
floor = np.median(flux_s)


def candidates():
    out = []
    # Flux peaks, 40 ms apart, clearly over the local average. Both kinds need real singing just after them.
    for i in range(8, n - 8):
        if flux_s[i] == flux_s[i - 8:i + 9].max() and flux_s[i] > 1.6 * max(floor, flux_s[max(0, i - 40):i + 40].mean() * 0.8):
            if db[min(i + 6, n - 1)] > -35:
                out.append((float(T[i]), float(flux_s[i]), "flux"))
    # Steepest rise after a dip
    for i in range(10, n - 10):
        if slope[i] == slope[i - 8:i + 9].max() and slope[i] > 0.5 and db[i + 8] - db[max(0, i - 12):i + 1].min() >= 4:
            if db[min(i + 6, n - 1)] > -35:
                out.append((float(T[i]), float(slope[i]), "rise"))
    return sorted(out)


CANDS = candidates()
rows = []
for li, line in enumerate(SEEDS):
    for word, seed, wt, ascore, t1 in line:
        near = [c for c in CANDS if abs(c[0] - seed) <= MAX_SNAP]
        row = dict(line=li + 1, word=word, aligner=seed, whisper=wt, ascore=ascore, end=t1, disagree=abs(seed - wt) > 0.12)
        if near:
            # Prefer where both kinds of evidence agree, then the closest to the seed
            def score(c):
                agree = any(o[2] != c[2] and abs(o[0] - c[0]) <= 0.02 for o in near)
                return (0 if agree else 1, abs(c[0] - seed))
            pick = min(near, key=score)
            agree = any(o[2] != pick[2] and abs(o[0] - pick[0]) <= 0.02 for o in near)
            row.update(t=round(pick[0], 3), status="both" if agree else pick[2])
        else:
            row.update(t=seed, status="MANUAL")
        rows.append(row)

print(f"{'ln':>2} {'word':12} {'align':>7} {'score':>5} {'whisp':>7} {'snap':>7}  evidence")
last = 0
for r in rows:
    if r["line"] != last:
        print()
        last = r["line"]
    print(f"{r['line']:>2} {r['word']:12} {r['aligner']:7.2f} {r['ascore']:5.2f} {r['whisper']:7.2f} {r['t']:7.2f}  {r['status']}{'  DISAGREE' if r['disagree'] else ''}")
print("\nMANUAL:", [f"{r['line']}:{r['word']}" for r in rows if r["status"] == "MANUAL"])
print("DISAGREE:", [f"{r['line']}:{r['word']}" for r in rows if r["disagree"]])

# The band: is the 125 BPM grid still true this deep into the song? One bar hit measured per bar, plus each cut point.
bd, bsr = librosa.load(STEMS / "no_vocals.wav", sr=None, mono=True)


def band_hit(g, reach=0.06):
    a0, z0 = int((g - reach - T0) * bsr), int((g + reach - T0) * bsr)
    w = np.abs(bd[a0:z0])
    e = np.convolve(w, np.ones(44) / 44, mode="same")
    i = int(np.argmax(np.gradient(e)))
    return g - reach + i / bsr, float(e.max()), float(e[max(0, i - 200):max(1, i - 100)].mean())


offs = []
for k in range(0, 17):
    g = START + k * BAR
    t, peak, before = band_hit(g)
    offs.append(t - g)
    print(f"bar {k:2d} grid {g:7.2f} hit {t:8.4f} off {1000 * (t - g):+6.1f} ms  level {before:.3f} -> {peak:.3f}")
print(f"grid offset median {1000 * np.median(offs):+.1f} ms, spread {1000 * (max(offs) - min(offs)):.1f} ms")

# What is left of the voice either side of the cut points, and the bleep span
for label, a, z in (("before the start cut", START - 0.25, START), ("after the start cut", START, START + 0.15), ("last 150 ms", END - 0.15, END), ("after the end cut", END, END + 0.15)):
    i0, i1 = int((a - T0) * sr), int((z - T0) * sr)
    print(f"voice {label:22}: {20 * np.log10(np.sqrt(np.mean(v[i0:i1] ** 2)) + 1e-6):6.1f} dB")

(SYNC / "attacks.json").write_text(json.dumps({"rows": rows, "candidates": CANDS, "grid_offset_ms": float(1000 * np.median(offs))}, ensure_ascii=False), encoding="utf-8")

# Mouth loudness: per-video-frame peak of the short-time level, normalised against the window's 98th percentile
hop_env = sr // 300
env = librosa.feature.rms(y=v, frame_length=hop_env * 3, hop_length=hop_env, center=True)[0]
vals = []
for f in range(FRAMES):
    a = START + f / FPS - T0
    i0, i1 = int(a * sr / hop_env), int((a + 1 / FPS) * sr / hop_env)
    vals.append(float(env[i0:max(i1, i0 + 1)].max()))
vals = np.array(vals)
ref = np.percentile(vals, 98)
norm = np.clip(20 * np.log10(vals / ref + 1e-5) / 30 + 1, 0, 1)  # 0 at -30 dB under reference, 1 at the reference
(ROOT / "src" / "lego" / "vocal_env.json").write_text(
    json.dumps({"_": "Vocal loudness per video frame, 0 to 1, drives the mouth. Index 0 is frame 1. Made by src/lego/sync/attacks.py.",
                "fps": FPS, "start": START, "env": [round(float(x), 3) for x in norm]}), encoding="utf-8")

# Review strips: spectrogram and loudness with words and beats, zoomed on the spots that matter most or are least sure
REVIEW.mkdir(parents=True, exist_ok=True)
words = [(r["t"], r["word"], r["status"]) for r in rows]
strips = [(218.2, 219.6), (229.8, 231.5), (237.2, 239.6), (242.2, 243.6), (247.0, 249.4)]
fig, axes = plt.subplots(len(strips) * 2, 1, figsize=(18, 16), gridspec_kw={"height_ratios": [3, 1] * len(strips)})
for k, (a, z) in enumerate(strips):
    ax, ax2 = axes[k * 2], axes[k * 2 + 1]
    i0, i1 = int((a - T0) * sr / HOP), int((z - T0) * sr / HOP)
    ax.imshow(mel[:, i0:i1], origin="lower", aspect="auto", extent=[a, z, 0, 64], cmap="magma", vmin=-70, vmax=0)
    ax2.plot(T[i0:i1], db[i0:i1], lw=0.8, color="k")
    ax2.set_xlim(a, z)
    ax2.set_ylim(-60, -5)
    for g in np.arange(START, END + 1, 0.48):
        if a <= g <= z:
            ax.axvline(g, color="cyan", lw=0.6, alpha=0.6)
            ax2.axvline(g, color="tab:blue", lw=0.5, alpha=0.5)
    for t, w, st in words:
        if a <= t <= z:
            ax.axvline(t, color="w" if st != "MANUAL" else "red", lw=1)
            ax.text(t + 0.01, 58, w, color="w" if st != "MANUAL" else "red", fontsize=10, weight="bold")
    ax.set_xlim(a, z)
    ax.set_xticks(np.arange(np.ceil(a * 10) / 10, z, 0.1))
    ax.tick_params(labelsize=7)
    ax2.set_xticks(np.arange(np.ceil(a * 10) / 10, z, 0.1))
    ax2.tick_params(labelsize=7)
plt.tight_layout()
plt.savefig(REVIEW / "01-vocais-zoom.png", dpi=75)
print("saved")
