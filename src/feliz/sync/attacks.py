# Snaps each word to the nearest real vocal attack within 80 ms, and writes the per-frame vocal loudness.
#   uv run --no-project --python 3.11 --with librosa --with soundfile --with matplotlib python src/feliz/sync/attacks.py
# In:  blender/feliz/sync/align.json (forced aligner), the Whisper times below, the Demucs stem
# Out: blender/feliz/sync/attacks.json (candidates and the snap table), src/feliz/vocal_env.json,
#      blender/feliz/review/01-vocais-zoom.png (spectrogram strips with the words marked)
import json
import pathlib
import sys

import librosa
import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parents[3]
SYNC = ROOT / "blender" / "feliz" / "sync"
STEMS = SYNC / "htdemucs" / "window_12_41"
REVIEW = ROOT / "blender" / "feliz" / "review"
T0 = 12.0
SR = 22050
HOP = 110  # 5 ms
MAX_SNAP = 0.080
sys.stdout.reconfigure(encoding="utf-8")

# Whisper's plain pass on the stem and the forced aligner (align.json) are two independent timers. The aligner wins as
# the seed: it repeats line 1 onto line 5 within a couple of frames. Each entry is (caption word, Whisper time).
WORDS = [
    ("1", [("hoje", 14.84), ("eu", 15.20), ("sou", 15.36), ("um", 15.54), ("pardo", 15.74), ("feliz", 16.00)]),
    ("2", [("tenho", 16.78), ("a", 17.20), ("pardo", 17.40), ("energia", 17.70)]),
    ("3", [("nada", 18.66), ("vai", 19.12), ("abalar", 19.56), ("o", 20.00), ("pardo", 20.28)]),
    ("4", [("comigo", 20.58), ("pardo", 21.48), ("repita", 21.80)]),
    ("5", [("hoje", 22.58), ("eu", 22.84), ("sou", 23.02), ("um", 23.20), ("pardo", 23.36), ("feliz", 23.68)]),
    ("6", [("pardo", 24.66), ("só", 24.86), ("quer", 25.20), ("ser", 25.38), ("feliz", 25.70)]),
    ("7", [("berg", 26.40), ("o", 26.78), ("que", 26.96), ("o", 27.14), ("pardo", 27.40), ("quer", 27.82)]),
    ("8", [("o", 28.14), ("pardo", 28.54), ("quer", 28.98), ("ser", 29.24), ("feliz", 29.52)]),
    ("9", [("beat", 30.44), ("plic", 31.18), ("ploc", 31.82)]),
    ("10", [("não", 32.28), ("f*do", 32.46), ("com", 32.84), ("tik", 33.16), ("tok", 33.58)]),
    ("11", [("frutiger", 33.98), ("aero", 35.04), ("neles", 35.50)]),
    ("12", [("deixando", 35.98), ("os", 36.74), ("berg", 37.02), ("em", 37.52), ("choque", 37.54)]),
]
ALIGN = json.loads((SYNC / "align.json").read_text(encoding="utf-8"))
SEEDS = []
for key, words in WORDS:
    al = ALIGN[key]["words"]
    assert len(al) == len(words), key
    SEEDS.append([(w, r["t0"], wt, r["score"]) for (w, wt), r in zip(words, al)])

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
    for word, seed, wt, ascore in line:
        near = [c for c in CANDS if abs(c[0] - seed) <= MAX_SNAP]
        row = dict(line=li + 1, word=word, aligner=seed, whisper=wt, ascore=ascore, disagree=abs(seed - wt) > 0.12)
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

print(f"{'ln':>2} {'word':10} {'align':>6} {'score':>5} {'whisp':>6} {'snap':>6}  evidence")
last = 0
for r in rows:
    if r["line"] != last:
        print()
        last = r["line"]
    print(f"{r['line']:>2} {r['word']:10} {r['aligner']:6.2f} {r['ascore']:5.2f} {r['whisper']:6.2f} {r['t']:6.2f}  {r['status']}{'  DISAGREE' if r['disagree'] else ''}")
print("\nMANUAL:", [f"{r['line']}:{r['word']}" for r in rows if r["status"] == "MANUAL"])
print("DISAGREE:", [f"{r['line']}:{r['word']}" for r in rows if r["disagree"]])

# The same melody comes back 4 bars later, so line 5 minus line 1 should be 7.68 s for every word
l1, l5 = [r for r in rows if r["line"] == 1], [r for r in rows if r["line"] == 5]
print("line5 - line1:", " ".join(f"{a['word']} {b['t'] - a['t']:.2f}" for a, b in zip(l1, l5)))

# Exact drum hit at the cut points
bd, bsr = librosa.load(STEMS / "no_vocals.wav", sr=None, mono=True)
for g in (14.895, 37.935):
    a0, z0 = int((g - 0.06 - T0) * bsr), int((g + 0.06 - T0) * bsr)
    w = np.abs(bd[a0:z0])
    e = np.convolve(w, np.ones(44) / 44, mode="same")
    i = int(np.argmax(np.gradient(e)))
    print(f"band transient near {g}: steepest at {g - 0.06 + i / bsr:.4f}, peak level {e.max():.3f}, level just before {e[max(0, i - 200):max(1, i - 100)].mean():.3f}")

(SYNC / "attacks.json").write_text(json.dumps({"rows": rows, "candidates": CANDS}, ensure_ascii=False), encoding="utf-8")

# Mouth loudness: per-video-frame peak of the short-time level, normalised against the window's 98th percentile
TL = json.loads((ROOT / "src" / "feliz" / "timeline.json").read_text(encoding="utf-8"))
START, FRAMES, FPS = TL["start"], TL["frames"], TL["fps"]
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
(ROOT / "src" / "feliz" / "vocal_env.json").write_text(
    json.dumps({"_": "Vocal loudness per video frame, 0 to 1, drives the mouth. Index 0 is frame 1. Made by src/feliz/sync/attacks.py.",
                "fps": FPS, "start": START, "env": [round(float(x), 3) for x in norm]}), encoding="utf-8")

# Pitch, for telling a held note from a new sung syllable
f0, voiced, _ = librosa.pyin(v, fmin=80, fmax=800, sr=sr, frame_length=1024, hop_length=220)
f0t = T0 + np.arange(len(f0)) * 220 / sr

# Review strips: spectrogram, loudness and pitch with words and beats, zoomed on the spots where the timers disagree
REVIEW.mkdir(parents=True, exist_ok=True)
words = [(r["t"], r["word"], r["status"]) for r in rows]
strips = [(16.7, 18.7), (19.4, 21.0), (26.3, 28.7), (33.8, 35.7), (36.7, 37.9)]
fig, axes = plt.subplots(len(strips) * 2, 1, figsize=(18, 18), gridspec_kw={"height_ratios": [3, 1] * len(strips)})
for k, (a, z) in enumerate(strips):
    ax, ax2 = axes[k * 2], axes[k * 2 + 1]
    i0, i1 = int((a - T0) * sr / HOP), int((z - T0) * sr / HOP)
    ax.imshow(mel[:, i0:i1], origin="lower", aspect="auto", extent=[a, z, 0, 64], cmap="magma", vmin=-70, vmax=0)
    ax2.plot(T[i0:i1], db[i0:i1], lw=0.8, color="k")
    ax2.set_xlim(a, z)
    ax2.set_ylim(-60, -5)
    ax3 = ax2.twinx()
    m = (f0t >= a) & (f0t < z)
    ax3.plot(f0t[m], f0[m], lw=1.2, color="tab:green")
    ax3.set_yscale("log")
    ax3.set_ylim(90, 700)
    for g in np.arange(14.895, 39, 0.48):
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
