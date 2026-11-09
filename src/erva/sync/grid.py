# Fits a fixed beat grid (BPM and phase) to the onsets of the instrumental stem around the lyric block.
#   uv run --no-project --python 3.11 --with soundfile --with "numpy<2" python src/erva/sync/grid.py
# The tempo is unknown, so an autocorrelation of the onset curve gives the candidates first, then each is fitted finely.
# Prints the best BPM, the beat phase, which beat of the bar is strongest, and the beats near the block edges.
import pathlib
import sys

import numpy as np
import soundfile as sf

ROOT = pathlib.Path(__file__).resolve().parents[3]
SYNC = ROOT / "blender" / "erva" / "sync"
A, Z = 40.0, 105.0
sys.stdout.reconfigure(encoding="utf-8")

m, sr = sf.read(SYNC / "htdemucs" / "no_vocals.wav", dtype="float32", always_2d=True)
m = m.mean(1)[int(A * sr):int(Z * sr)]
hop, win = 88, 1024  # 2 ms
frames = np.lib.stride_tricks.sliding_window_view(m, win)[::hop] * np.hanning(win)
S = np.abs(np.fft.rfft(frames, axis=1))
freqs = np.fft.rfftfreq(win, 1 / sr)
low = np.log1p(S[:, freqs < 150].sum(1))
full = np.log1p(S.sum(1))
flux = lambda x: np.maximum(0, np.diff(x, prepend=x[0]))
onset = flux(low) + 0.5 * flux(full)
dt = hop / sr

# Coarse: autocorrelation peaks between 60 and 200 BPM
o = onset - onset.mean()
ac = np.correlate(o, o, mode="full")[len(o) - 1:]
lags = np.arange(len(ac)) * dt
cands = []
for bpm in np.arange(60, 200, 0.25):
    lag = int(round(60 / bpm / dt))
    cands.append((ac[lag - 2:lag + 3].max(), bpm))
cands.sort(reverse=True)
seen = []
for sc, bpm in cands:
    if all(abs(bpm - b) > 3 for b in seen):
        seen.append(bpm)
    if len(seen) == 5:
        break
print("autocorrelation candidates (BPM):", [round(b, 2) for b in seen])


def fit(lo, hi, step):
    best = None
    for bpm in np.arange(lo, hi, step):
        p = 60 / bpm
        for ph in np.arange(0, p, 0.002):
            idx = (np.arange(ph, Z - A, p) / dt).astype(int)
            idx = idx[idx < len(onset)]
            sc = onset[idx].mean()
            if best is None or sc > best[0]:
                best = (sc, bpm, ph)
    return best


results = []
for b in seen:
    sc, bpm, ph = fit(b - 1.5, b + 1.5, 0.01)
    results.append((sc, bpm, ph))
    print(f"  fitted {bpm:7.2f} BPM  phase {A + ph:.3f}  score {sc:.3f}")
sc, bpm, ph = max(results)
p = 60 / bpm
print(f"\nBEST BPM {bpm:.2f}  beat {p:.4f}s  bar {4 * p:.4f}s  first beat after {A}: {A + ph:.3f}  score {sc:.3f}")
beats = np.arange(A + ph, Z, p)
idx = ((beats - A) / dt).astype(int)
idx = idx[idx < len(onset)]
strength = [onset[idx[k::4]].mean() for k in range(4)]
print("beat-in-bar strengths", np.round(strength, 3), "-> downbeat index", int(np.argmax(strength)))
down = int(np.argmax(strength))
for k, b in enumerate(beats):
    if 44 < b < 52 or 94 < b < 104:
        print(f"{b:8.3f}{'  | bar' if k % 4 == down else ''}")
