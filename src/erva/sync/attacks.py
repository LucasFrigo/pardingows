# Snaps every syllable onset to the nearest real vocal attack (80 ms for a word's first syllable, 60 ms for the others),
# checks the band against the 150 BPM grid, writes the per-frame vocal loudness and a review sheet.
#   uv run --no-project --python 3.11 --with librosa --with soundfile --with matplotlib python src/erva/sync/attacks.py
# In:  blender/erva/sync/align.json (forced aligner, with syllable onsets), whisper.json (cross-check), the Demucs stems
# Out: blender/erva/sync/attacks.json, src/erva/vocal_env.json, blender/erva/review/01-vocais.png
import json
import pathlib
import sys

import librosa
import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parents[3]
SYNC = ROOT / "blender" / "erva" / "sync"
STEMS = SYNC / "htdemucs"
REVIEW = ROOT / "blender" / "erva" / "review"
SR, HOP = 22050, 110  # 5 ms
SNAP_WORD, SNAP_SYL = 0.080, 0.060
BEAT = 0.4  # 150 BPM from 0 s (FL Studio grid): grid.py's fit was 16 ms early, the band's earliest hits land on it
BAR0 = 48.0  # couplet bars are 3.2 s (8 beats, the half-time feel)
START, END, FPS = 47.6, 101.6, 24
FRAMES = round((END - START) * FPS)
sys.stdout.reconfigure(encoding="utf-8")

ALIGN = json.loads((SYNC / "align.json").read_text(encoding="utf-8"))
WHISPER = json.loads((SYNC / "whisper.json").read_text(encoding="utf-8"))
WH = sorted({round(w["t0"], 2) for k in WHISPER for w in WHISPER[k]})

# Lines in sung order: (line id, aligner key) for aligned lines, (line id, manual) with syllable seeds per word for the rest.
# Lines 8 and 14 use the spellings the singer seems to sing (8s, 14L); see the step-1 notes.
ORDER = ["1", "2", "3", "4", ("4m", [[53.84], [53.98], [54.06]]), "5", "6", "7", "8s", "9", "10", "11", "12",
         ("12m", [[66.70], [66.88], [67.06]]), "13", "14L", "15", "16", "17", "18", "19", "20", "21", "22",
         ("23", [[82.81, 82.97, 83.17], [83.61, 83.77, 84.01], [84.39, 84.57, 84.79], [85.23, 85.39, 85.61]]),
         "24", "25", "26", "27", "28", "29", "30", "31"]

v, sr = librosa.load(STEMS / "vocals.wav", sr=SR, mono=True)
smooth = lambda x, n: np.convolve(x, np.ones(n) / n, mode="same")

# Evidence 1: spectral flux in the voice band (consonants, and syllables starting over a held note)
S = np.abs(librosa.stft(v, n_fft=512, hop_length=HOP))
mel = librosa.power_to_db(librosa.feature.melspectrogram(S=S**2, sr=sr, n_mels=64, fmin=120, fmax=9000), ref=np.max)
flux = np.maximum(0, mel[:, 2:] - mel[:, :-2]).mean(axis=0)
flux_s = smooth(np.concatenate(([0, 0], flux)), 3)
# Evidence 2: loudness rising out of a dip of at least 4 dB
rms = librosa.feature.rms(y=v, frame_length=441, hop_length=HOP, center=True)[0]
db = 20 * np.log10(smooth(rms, 3) + 1e-5)
slope = np.gradient(db)
n = min(len(flux_s), len(db))
flux_s, db, slope = flux_s[:n], db[:n], slope[:n]
T = np.arange(n) * HOP / sr
floor = np.median(flux_s[int(START * sr / HOP):int(END * sr / HOP)])

cands = []
lo, hi = int((START - 0.5) * sr / HOP), int((END + 0.5) * sr / HOP)
for i in range(max(8, lo), min(n - 12, hi)):
    if db[i + 6] <= -35:
        continue
    if flux_s[i] == flux_s[i - 8:i + 9].max() and flux_s[i] > 1.6 * max(floor, flux_s[max(0, i - 40):i + 40].mean() * 0.8):
        cands.append((float(T[i]), float(flux_s[i]), "flux"))
    if slope[i] == slope[i - 8:i + 9].max() and slope[i] > 0.5 and db[i + 8] - db[max(0, i - 12):i + 1].min() >= 4:
        cands.append((float(T[i]), float(slope[i]), "rise"))
cands.sort()


def snap(seed, reach):
    near = [c for c in cands if abs(c[0] - seed) <= reach]
    if not near:
        return seed, "MANUAL"
    agree = lambda c: any(o[2] != c[2] and abs(o[0] - c[0]) <= 0.02 for o in near)
    pick = min(near, key=lambda c: (0 if agree(c) else 1, abs(c[0] - seed)))
    return round(pick[0], 3), "both" if agree(pick) else pick[2]


lines = []
for item in ORDER:
    if isinstance(item, tuple):
        lid, seeds = item
        words = [{"w": f"#{k}", "syl": s, "t1": s[-1] + 0.12, "score": None} for k, s in enumerate(seeds)]
    else:
        lid = item.rstrip("sLxmr") if item not in ("4m", "12m") else item
        words = ALIGN[item]["words"]
    out = []
    prev = -1.0  # the last syllable placed, across word boundaries
    for w in words:
        syl, st = [], []
        for k, s in enumerate(w["syl"]):
            t, how = snap(s, SNAP_WORD if k == 0 else SNAP_SYL)
            # a syllable lands at least 70 ms after the previous one, also across words (two words can't share an attack)
            if t < prev + 0.07:
                t, how = round(max(s, prev + 0.07), 3), "seed"
            prev = t
            syl.append(t)
            st.append(how)
        wh = min(WH, key=lambda x: abs(x - syl[0]))
        out.append({"w": w["w"], "syl": syl, "seed": w["syl"], "how": st, "end": w["t1"], "score": w["score"],
                    "whisper": wh if abs(wh - syl[0]) < 0.3 else None})
    lines.append({"line": lid, "key": item if isinstance(item, str) else lid, "words": out})

print(f"{'line':>4} {'word':14} {'aligner':>7} {'snap':>7} {'whisper':>7}  syllables")
for L in lines:
    print()
    for w in L["words"]:
        wh = f"{w['whisper']:7.2f}" if w["whisper"] else "      -"
        flag = "  DISAGREE" if w["whisper"] and abs(w["whisper"] - w["syl"][0]) > 0.12 else ""
        print(f"{L['line']:>4} {w['w']:14} {w['seed'][0]:7.2f} {w['syl'][0]:7.2f} {wh}  " +
              " ".join(f"{t:.2f}/{h[0]}" for t, h in zip(w["syl"], w["how"])) + flag)
manual = [f"{L['line']}:{w['w']}" for L in lines for w in L["words"] if "MANUAL" in w["how"]]
print("\nMANUAL (no attack near):", manual)

# The band against the grid: one measured hit per beat at every bar line in the window
bd, bsr = librosa.load(STEMS / "no_vocals.wav", sr=None, mono=True)


def band_hit(g, reach=0.06):
    a0, z0 = int((g - reach) * bsr), int((g + reach) * bsr)
    e = np.convolve(np.abs(bd[a0:z0]), np.ones(44) / 44, mode="same")
    i = int(np.argmax(np.gradient(e)))
    return g - reach + i / bsr


offs = []
for k in range(17):
    g = BAR0 + k * 3.2
    t = band_hit(g)
    offs.append(t - g)
    print(f"bar {k:2d} grid {g:7.3f} hit {t:8.4f} off {1000 * (t - g):+6.1f} ms")
print(f"grid offset median {1000 * np.median(offs):+.1f} ms, spread {1000 * (max(offs) - min(offs)):.1f} ms")

(SYNC / "attacks.json").write_text(json.dumps({"lines": lines, "grid_offset_ms": float(1000 * np.median(offs))},
                                              ensure_ascii=False), encoding="utf-8")

# Mouth loudness per video frame, 0 to 1 (0 at 30 dB under the window's 98th percentile)
hop_env = sr // 300
env = librosa.feature.rms(y=v, frame_length=hop_env * 3, hop_length=hop_env, center=True)[0]
vals = []
for f in range(FRAMES):
    a = START + f / FPS
    i0, i1 = int(a * sr / hop_env), int((a + 1 / FPS) * sr / hop_env)
    vals.append(float(env[i0:max(i1, i0 + 1)].max()))
vals = np.array(vals)
norm = np.clip(20 * np.log10(vals / np.percentile(vals, 98) + 1e-5) / 30 + 1, 0, 1)
(ROOT / "src" / "erva" / "vocal_env.json").write_text(json.dumps(
    {"_": "Vocal loudness per video frame, 0 to 1, drives the mouths. Index 0 is frame 1. Made by src/erva/sync/attacks.py.",
     "fps": FPS, "start": START, "env": [round(float(x), 3) for x in norm]}), encoding="utf-8")

# Review: spectrogram strips of the whole block, syllables marked, beats in cyan
REVIEW.mkdir(parents=True, exist_ok=True)
syls = [(t, w["w"] if k == 0 else "", h) for L in lines for w in L["words"] for k, (t, h) in enumerate(zip(w["syl"], w["how"]))]
strips = [(START + k * 6.75, START + (k + 1) * 6.75) for k in range(8)]
fig, axes = plt.subplots(len(strips), 1, figsize=(22, 30))
for ax, (a, z) in zip(axes, strips):
    i0, i1 = int(a * sr / HOP), int(z * sr / HOP)
    ax.imshow(mel[:, i0:i1], origin="lower", aspect="auto", extent=[a, z, 0, 64], cmap="magma", vmin=-70, vmax=0)
    for g in np.arange(BAR0 - 2 * BEAT, END, BEAT):
        if a <= g <= z:
            ax.axvline(g, color="cyan", lw=1.4 if abs((g - BAR0) / 3.2 - round((g - BAR0) / 3.2)) < 1e-6 else 0.5, alpha=0.7)
    for t, w, h in syls:
        if a <= t <= z:
            c = "red" if "MANUAL" in h else ("yellow" if h == "seed" else "w")
            ax.axvline(t, color=c, lw=0.9, ymax=0.85)
            if w:
                ax.text(t + 0.01, 58, w, color=c, fontsize=9, weight="bold")
    ax.set_xlim(a, z)
    ax.set_xticks(np.arange(np.ceil(a * 5) / 5, z, 0.2))
    ax.tick_params(labelsize=7)
plt.tight_layout()
plt.savefig(REVIEW / "01-vocais.png", dpi=60)
print("saved review/01-vocais.png")
