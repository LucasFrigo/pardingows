# Fits a fixed beat grid (BPM and phase) to the kick onsets of the instrumental stem around the lyric block.
#   uv run --no-project --python 3.11 --with soundfile --with "numpy<2" python src/pardao/sync/grid.py
# Prints the best BPM, the first-beat phase, and the bar lines near the block edges.
import pathlib
import numpy as np
import soundfile as sf

ROOT = pathlib.Path(__file__).resolve().parents[3]
SYNC = ROOT / "blender" / "pardao" / "sync"
A, Z = 140.0, 200.0

m, sr = sf.read(SYNC / "htdemucs" / "no_vocals.wav", dtype="float32", always_2d=True)
m = m.mean(1)[int(A * sr):int(Z * sr)]
# low band (kick) energy flux at 2 ms resolution
spec_hop = 88
win = 1024
frames = np.lib.stride_tricks.sliding_window_view(m, win)[::spec_hop] * np.hanning(win)
S = np.abs(np.fft.rfft(frames, axis=1))
freqs = np.fft.rfftfreq(win, 1 / sr)
low = np.log1p(S[:, freqs < 150].sum(1))
full = np.log1p(S.sum(1))
def flux(x):
    return np.maximum(0, np.diff(x, prepend=x[0]))
onset = flux(low) + 0.5 * flux(full)
t = np.arange(len(onset)) * spec_hop / sr + A

best = None
for bpm in np.arange(123.0, 129.0, 0.01):
    p = 60 / bpm
    for ph in np.arange(0, p, 0.002):
        idx = ((np.arange(ph + A, Z, p) - A) * sr / spec_hop).astype(int)
        idx = idx[idx < len(onset)]
        sc = onset[idx].mean()
        if best is None or sc > best[0]:
            best = (sc, bpm, ph)
sc, bpm, ph = best
p = 60 / bpm
print(f"BPM {bpm:.2f}  beat {p:.4f}s  bar {4*p:.4f}s  first beat after {A}: {A+ph:.3f}  score {sc:.3f}")
beats = np.arange(A + ph, Z, p)
# which beat of the bar is the downbeat: the one with the strongest mean onset
idx = ((beats - A) * sr / spec_hop).astype(int)
strength = [onset[idx[k::4]].mean() for k in range(4)]
print("beat-in-bar strengths", np.round(strength, 3))
for k, b in enumerate(beats):
    if 150 < b < 196:
        print(f"{b:8.3f}{'  | bar' if k % 4 == int(np.argmax(strength)) else ''}")
