# Snaps each word to the nearest real vocal attack within 80 ms, measures the beat grid and the two cut points.
#   uv run --no-project --python 3.11 --with librosa --with soundfile --with matplotlib python src/zombies/sync/attacks.py
# In:  blender/zombies/sync/align.json (forced aligner), the Whisper times below, the Demucs stems
# Out: blender/zombies/sync/attacks.json (snap table, grid, letter spans of the censored words),
#      blender/zombies/review/01-vocais-zoom.png (spectrogram strips with the words marked)
import json
import pathlib
import sys

import librosa
import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parents[3]
SYNC = ROOT / "blender" / "zombies" / "sync"
STEMS = SYNC / "htdemucs" / "window_60_100"
REVIEW = ROOT / "blender" / "zombies" / "review"
T0 = 60.0
SR = 22050
HOP = 110  # 5 ms
MAX_SNAP = 0.080
BPM = 140.0
sys.stdout.reconfigure(encoding="utf-8")

# (caption word, Whisper time on the stem). Aligner keys pick the written lyric where a variant was tested.
WORDS = [
    ("1", [("pardo", 62.96), ("apocalipse", 63.66)]),
    ("2", [("com", 64.74), ("muita", 65.06), ("canalhisse", 65.40)]),
    ("3", [("meu", 66.52), ("pau", 66.72), ("já", 66.90), ("tá", 67.18), ("assado", 67.40)]),
    ("4", [("isso", 68.10), ("é", 68.38), ("resident", 68.54), ("pardo", 69.42)]),
    ("5", [("pardolipse", 69.88), ("na", 70.66), ("cidade", 70.80)]),
    ("6", [("pardos", 71.62), ("não", 71.74), ("fogem", 71.88), ("da", 72.26), ("maldade", 72.48)]),
    ("7", [("muita", 73.16), ("promiscuidade", 73.62)]),
    ("8", [("tome", 75.12), ("pica", 75.34), ("a", 75.90), ("vontade", 75.96)]),
    ("9", [("uma", 76.54), ("zombie", 77.00), ("me", 77.46), ("mordendo", 77.70)]),
    ("10", [("me", 78.26), ("deixou", 78.56), ("arrepiado", 79.14)]),
    ("11", [("puxei", 80.18), ("pelos", 80.68), ("cabelo", 81.10)]),
    ("12", [("ficou", 82.00), ("com", 82.34), ("o", 82.64), ("cu", 82.64), ("raspado", 82.88)]),
    ("13", [("necrofilia", 83.86), ("zombifilia", 84.68)]),
    ("14", [("fodo", 85.44), ("até", 85.62), ("a", 86.02), ("sua", 86.32), ("filha", 86.62)]),
    ("15", [("careca", 87.30), ("ou", 87.66), ("cabeluda", 87.80)]),
    ("16", [("caolha", 88.88), ("ou", 89.60), ("banguela", 89.70)]),
    ("17", [("sodoma", 90.66), ("e", 91.18), ("gomorra", 91.50)]),
    ("18", [("cheira", 92.02), ("cola", 92.56), ("e", 92.70), ("chupa", 92.96), ("rola", 93.54)]),
    ("19", [("baba", 93.92), ("ovo", 94.20), ("na", 94.58), ("masmorra", 94.88)]),
    ("20", [("se", 95.62), ("engasga", 95.86), ("até", 96.32), ("que", 96.50), ("morra", 96.84)]),
]
ALIGN = json.loads((SYNC / "align.json").read_text(encoding="utf-8"))
SEEDS = []
for key, words in WORDS:
    al = ALIGN[key]["words"]
    assert len(al) == len(words), key
    SEEDS.append([(w, r["t0"], wt, r["score"]) for (w, wt), r in zip(words, al)])

v, sr = librosa.load(STEMS / "vocals.wav", sr=SR, mono=True)


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
T = T0 + np.arange(n) * HOP / sr
floor = np.median(flux_s)


def candidates():
    out = []
    for i in range(8, n - 8):
        if flux_s[i] == flux_s[i - 8:i + 9].max() and flux_s[i] > 1.6 * max(floor, flux_s[max(0, i - 40):i + 40].mean() * 0.8):
            if db[min(i + 6, n - 1)] > -35:
                out.append((float(T[i]), float(flux_s[i]), "flux"))
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
            def score(c):
                agree = any(o[2] != c[2] and abs(o[0] - c[0]) <= 0.02 for o in near)
                return (0 if agree else 1, abs(c[0] - seed))
            pick = min(near, key=score)
            agree = any(o[2] != pick[2] and abs(o[0] - pick[0]) <= 0.02 for o in near)
            row.update(t=round(pick[0], 3), status="both" if agree else pick[2])
        else:
            row.update(t=seed, status="MANUAL")
        rows.append(row)

print(f"{'ln':>2} {'word':14} {'align':>6} {'score':>5} {'whisp':>6} {'snap':>6}  evidence")
last = 0
for r in rows:
    if r["line"] != last:
        print()
        last = r["line"]
    print(f"{r['line']:>2} {r['word']:14} {r['aligner']:6.2f} {r['ascore']:5.2f} {r['whisper']:6.2f} {r['t']:6.2f}  {r['status']}{'  DISAGREE' if r['disagree'] else ''}")
print("\nMANUAL:", [f"{r['line']}:{r['word']}" for r in rows if r["status"] == "MANUAL"])
print("DISAGREE:", [f"{r['line']}:{r['word']}" for r in rows if r["disagree"]])

# Beat grid measured on the band stem alone, with the drums free of the voice
bd, bsr = librosa.load(STEMS / "no_vocals.wav", sr=None, mono=True)
bhop = 128
bS = librosa.feature.rms(y=bd, frame_length=512, hop_length=bhop, center=True)[0]
bl = np.log(bS + 1e-6)
bflux = np.maximum(0, np.diff(bl, prepend=bl[0]))
beat = 60 / BPM
best = (0, 0)
for ph in np.arange(0, beat, 0.001):
    idx = ((ph + np.arange(0, len(bd) / bsr - 1.0, beat)) * bsr / bhop).astype(int)
    s = bflux[idx].mean()
    if s > best[0]:
        best = (s, ph)
beat0 = T0 + best[1]
print(f"\ngrid: {BPM} BPM, a beat at {beat0:.3f}, comb score {best[0]:.3f}, mean flux {bflux.mean():.3f}")

# Which of the four beats is the bar's first: band energy per beat position over the song window
pos = np.zeros(4)
for k in range(int((97 - beat0) / beat)):
    t = beat0 + k * beat
    if t >= 63:
        pos[k % 4] += bflux[int((t - T0) * bsr / bhop)]
print("flux per beat position:", np.round(pos, 2), "(position 0 is the beat at", f"{beat0:.3f})")

# The two cuts, on the voice alone: 10 ms loudness in dB around them
for a, z, name in ((62.3, 63.5, "start"), (96.4, 97.4, "end")):
    i0, i1 = int((a - T0) * sr / HOP), int((z - T0) * sr / HOP)
    print(f"\nvoice level around the {name} cut:")
    print(" ".join(f"{T[i]:.2f}:{db[i]:.0f}" for i in range(i0, i1, 4)))

for g in np.arange(beat0, 100, beat):
    if 62.5 < g < 63.5 or 96.5 < g < 97.5:
        a0, z0 = int((g - 0.05 - T0) * bsr), int((g + 0.05 - T0) * bsr)
        e = np.convolve(np.abs(bd[a0:z0]), np.ones(44) / 44, mode="same")
        i = int(np.argmax(np.gradient(e)))
        print(f"band near beat {g:.3f}: steepest at {g - 0.05 + i / bsr:.4f}, peak {e.max():.3f}")

# Letter spans of the censored words, for placing the bleep on the stressed vowel
KEYS = {"pau": ("3", 1), "pica": ("8", 1), "cu": ("12", 3), "fodo": ("14", 0), "rola": ("18", 4)}
spans = {}
for word, (key, idx) in KEYS.items():
    r = ALIGN[key]["words"][idx]
    spans[word] = {"letters": list(zip(r["w"], r["chars"])), "score": r["score"]}
    print(word, r["score"], " ".join(f"{ch}:{a:.2f}-{z:.2f}" for ch, (a, z) in zip(r["w"], r["chars"])))

(SYNC / "attacks.json").write_text(json.dumps({"rows": rows, "candidates": CANDS, "beat0": beat0, "spans": spans}, ensure_ascii=False), encoding="utf-8")

# Review strips: spectrogram and loudness with words and beats, on the disputed spots and the censored words
REVIEW.mkdir(parents=True, exist_ok=True)
words = [(r["t"], r["word"], r["status"]) for r in rows]
strips = [(62.4, 64.0), (66.4, 67.4), (68.0, 69.9), (75.0, 76.0), (82.2, 83.2), (85.1, 86.1), (93.0, 94.0), (95.5, 97.5)]
fig, axes = plt.subplots(len(strips) * 2, 1, figsize=(18, 22), gridspec_kw={"height_ratios": [3, 1] * len(strips)})
for k, (a, z) in enumerate(strips):
    ax, ax2 = axes[k * 2], axes[k * 2 + 1]
    i0, i1 = int((a - T0) * sr / HOP), int((z - T0) * sr / HOP)
    ax.imshow(mel[:, i0:i1], origin="lower", aspect="auto", extent=[a, z, 0, 64], cmap="magma", vmin=-70, vmax=0)
    ax2.plot(T[i0:i1], db[i0:i1], lw=0.8, color="k")
    ax2.set_xlim(a, z)
    ax2.set_ylim(-60, -5)
    for g in np.arange(beat0, 100, beat):
        if a <= g <= z:
            ax.axvline(g, color="cyan", lw=0.6, alpha=0.6)
            ax2.axvline(g, color="tab:blue", lw=0.5, alpha=0.5)
    for t, w, st in words:
        if a <= t <= z:
            ax.axvline(t, color="w" if st != "MANUAL" else "red", lw=1)
            ax.text(t + 0.01, 58, w, color="w" if st != "MANUAL" else "red", fontsize=10, weight="bold")
    ax.set_xlim(a, z)
    for x in (ax, ax2):
        x.set_xticks(np.arange(np.ceil(a * 10) / 10, z, 0.1))
        x.tick_params(labelsize=7)
plt.tight_layout()
plt.savefig(REVIEW / "01-vocais-zoom.png", dpi=75)
print("saved")
