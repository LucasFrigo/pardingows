# Writes the censored mix: each bleep swaps to the Demucs band stem, ducks it and adds a sharp 1 kHz tone, then a quiet neck creak.
#   out = (mix * (1 - gate) + band * gate) * duck + tone * gate + creak
# Gate times come from src/zombies/timeline.json. Re-run after changing a bleep.
#   uv run --no-project --python 3.11 --with numpy --with soundfile python src/zombies/sync/bleep.py
# Out: blender/zombies/sync/mix_censored.wav, starting at song second 60. Prints how well the stem cancels under each bleep.
import json
import pathlib
import sys

import numpy as np
import soundfile as sf

ROOT = pathlib.Path(__file__).resolve().parents[3]
SYNC = ROOT / "blender" / "zombies" / "sync"
TL = json.loads((ROOT / "src" / "zombies" / "timeline.json").read_text(encoding="utf-8"))
T0 = TL["mix_t0"]
RAMP = 0.005  # s, keeps the edges sharp without a click
TONE_HZ = 1000.0
DUCK = 0.35  # the band under the tone, so the tone cuts through a loud master without clipping
CREAK_DB = -16.0  # against the local mix level
sys.stdout.reconfigure(encoding="utf-8")

mix, sr = sf.read(SYNC / "window_60_100.wav", dtype="float64", always_2d=True)
voc, sr2 = sf.read(SYNC / "htdemucs" / "window_60_100" / "vocals.wav", dtype="float64", always_2d=True)
assert sr == sr2
n = min(len(mix), len(voc))
band, _ = sf.read(SYNC / "htdemucs" / "window_60_100" / "no_vocals.wav", dtype="float64", always_2d=True)
n = min(n, len(band))
mix, voc, band = mix[:n], voc[:n], band[:n]
out = mix.copy()
touched = np.zeros(n, bool)
rng = np.random.default_rng(1996)


def rms(x):
    return float(np.sqrt(np.mean(x**2)) + 1e-12)


def db(x):
    return 20 * np.log10(x + 1e-12)


def creak(length):
    """A dry neck creak: irregular clicks that speed up, through a rough resonance. Synthesized, so no sample licence."""
    m = int(length * sr)
    x = np.zeros(m)
    t = 0.0
    while t < length:
        i = int(t * sr)
        if i < m:
            x[i] = rng.uniform(0.6, 1.0) * rng.choice([-1, 1])
        rate = 38 + 70 * (t / length) ** 1.4
        t += (1 / rate) * rng.uniform(0.75, 1.25)
    # Two-pole resonators around a wood-like 1.1 and 2.3 kHz
    y = np.zeros(m)
    for fc, q, w in ((1100, 7, 1.0), (2300, 9, 0.6)):
        r = np.exp(-np.pi * fc / q / sr)
        a1, a2 = 2 * r * np.cos(2 * np.pi * fc / sr), -r * r
        z1 = z2 = 0.0
        for i in range(m):
            z = x[i] + a1 * z1 + a2 * z2
            y[i] += w * z
            z2, z1 = z1, z
    env = np.minimum(1, np.arange(m) / (0.01 * sr)) * np.minimum(1, (m - np.arange(m)) / (0.06 * sr))
    y *= env
    return y / (np.abs(y).max() + 1e-12)


print(f"{'word':6} {'bleep':>15} {'ms':>4} {'voice out':>12} {'mismatch':>12} {'margin':>9} {'tone':>9} {'peak':>6} {'over band':>10}")
for g in TL["gags"]:
    a, z = g["bleep"]
    i0, i1 = int((a - T0) * sr), int((z - T0) * sr)
    r = int(RAMP * sr)
    i00, i11 = i0 - r, i1 + r
    gate = np.ones(i11 - i00)
    ramp = 0.5 - 0.5 * np.cos(np.pi * np.arange(r) / r)
    gate[:r] = ramp
    gate[-r:] = ramp[::-1]
    gate2 = gate[:, None]

    seg = mix[i00:i11]
    # The band stem, not mix minus vocals: what Demucs leaves unassigned can still hold some of the word
    clean = seg * (1 - gate2) + band[i00:i11] * gate2

    t = np.arange(i11 - i00) / sr
    level = rms(mix[i00 - sr // 10:i11 + sr // 10])
    # Square-ish tones sound harsher, but a plain sine is the classic broadcast bleep
    amp = min(level * 1.6 * np.sqrt(2), 0.55)
    tone = amp * np.sin(2 * np.pi * TONE_HZ * t)
    duck = 1 - (1 - DUCK) * gate2
    out[i00:i11] = clean * duck + (tone * gate)[:, None]
    touched[i00:i11] = True
    # Cancellation: how far the voice-free signal sits from Demucs's own band stem, against the voice that came out
    miss = rms(mix[i0:i1] - voc[i0:i1] - band[i0:i1])
    took = rms(voc[i0:i1])

    # Creak right after the bleep, longer on the full-screen gag
    length = 0.70 if g.get("full") else 0.42
    c = creak(length)
    ci = i11 + int(0.02 * sr)
    ce = ci + len(c)
    gain = level * 10 ** (CREAK_DB / 20) * np.sqrt(2)
    out[ci:ce] += (c * gain)[:, None]
    touched[ci:ce] = True

    print(f"{g['word']:6} {a:7.2f}-{z:7.2f} {(z - a) * 1000:4.0f} {db(took):9.1f} dB {db(miss):9.1f} dB {db(took) - db(miss):6.1f} dB {db(rms(tone)):6.1f} dB {np.abs(out[i00:i11]).max():6.3f} {db(rms(tone)) - db(rms(clean * duck)):7.1f} dB")

peak = float(np.abs(out[touched]).max())
print(f"\npeak in the changed parts {peak:.3f} (source peak {np.abs(mix).max():.3f})")
# Only the changed samples can be limited, so the rest of the song stays exactly as mastered
over = touched[:, None] & (np.abs(out) > 0.97)
out[over] = (np.sign(out) * (0.97 + 0.03 * np.tanh((np.abs(out) - 0.97) / 0.03)))[over]
same = np.array_equal(out[~touched], mix[~touched])
print(f"limited {int(over.sum())} samples. Unchanged parts identical to the source: {same}. Changed: {touched.mean() * 100:.2f}% of the window")
sf.write(SYNC / "mix_censored.wav", out, sr, subtype="PCM_24")
print("wrote", SYNC / "mix_censored.wav")
