# Writes the censored mix: each bleep swaps to the Demucs band stem, ducks it and adds a sharp 1 kHz tone.
#   out = (mix * (1 - gate) + band * gate) * duck + tone * gate
# Gate times come from src/lego/timeline.json. Re-run after changing a bleep.
#   uv run --no-project --python 3.11 --with numpy --with soundfile python src/lego/sync/bleep.py
# Out: blender/lego/sync/mix_censored.wav, starting at song second 214. Prints how well the stem cancels under each bleep.
import json
import pathlib
import sys

import numpy as np
import soundfile as sf

ROOT = pathlib.Path(__file__).resolve().parents[3]
SYNC = ROOT / "blender" / "lego" / "sync"
TL = json.loads((ROOT / "src" / "lego" / "timeline.json").read_text(encoding="utf-8"))
T0 = TL["mix_t0"]
RAMP = 0.005  # s, keeps the edges sharp without a click
TONE_HZ = 1000.0
DUCK = 0.35  # the band under the tone, so the tone cuts through a loud master without clipping
sys.stdout.reconfigure(encoding="utf-8")

mix, sr = sf.read(SYNC / "window_214_253.wav", dtype="float64", always_2d=True)
voc, sr2 = sf.read(SYNC / "htdemucs" / "vocals.wav", dtype="float64", always_2d=True)
band, _ = sf.read(SYNC / "htdemucs" / "no_vocals.wav", dtype="float64", always_2d=True)
assert sr == sr2
n = min(len(mix), len(voc), len(band))
mix, voc, band = mix[:n], voc[:n], band[:n]
out = mix.copy()
touched = np.zeros(n, bool)


def rms(x):
    return float(np.sqrt(np.mean(x**2)) + 1e-12)


def db(x):
    return 20 * np.log10(x + 1e-12)


print(f"{'word':10} {'bleep':>15} {'ms':>4} {'voice out':>12} {'mismatch':>12} {'margin':>9} {'tone':>9} {'peak':>6} {'over band':>10}")
for g in TL["bleeps"]:
    a, z = g["span"]
    i0, i1 = int((a - T0) * sr), int((z - T0) * sr)
    r = int(RAMP * sr)
    i00, i11 = i0 - r, i1 + r
    gate = np.ones(i11 - i00)
    ramp = 0.5 - 0.5 * np.cos(np.pi * np.arange(r) / r)
    gate[:r] = ramp
    gate[-r:] = ramp[::-1]
    gate2 = gate[:, None]

    # The band stem, not mix minus vocals: what Demucs leaves unassigned can still hold some of the word
    clean = mix[i00:i11] * (1 - gate2) + band[i00:i11] * gate2
    t = np.arange(i11 - i00) / sr
    level = rms(mix[i00 - sr // 10:i11 + sr // 10])
    amp = min(level * 1.6 * np.sqrt(2), 0.55)  # a plain sine is the classic broadcast bleep
    tone = amp * np.sin(2 * np.pi * TONE_HZ * t)
    duck = 1 - (1 - DUCK) * gate2
    out[i00:i11] = clean * duck + (tone * gate)[:, None]
    touched[i00:i11] = True

    # Cancellation: how far the voice-free signal sits from Demucs's own band stem, against the voice that came out
    miss = rms(mix[i0:i1] - voc[i0:i1] - band[i0:i1])
    took = rms(voc[i0:i1])
    print(f"{g['word']:10} {a:7.2f}-{z:7.2f} {(z - a) * 1000:4.0f} {db(took):9.1f} dB {db(miss):9.1f} dB {db(took) - db(miss):6.1f} dB {db(rms(tone)):6.1f} dB {np.abs(out[i00:i11]).max():6.3f} {db(rms(tone)) - db(rms(clean * duck)):7.1f} dB")

# Only the changed samples can be limited, so the rest of the song stays exactly as mastered
over = touched[:, None] & (np.abs(out) > 0.97)
out[over] = (np.sign(out) * (0.97 + 0.03 * np.tanh((np.abs(out) - 0.97) / 0.03)))[over]
same = np.array_equal(out[~touched], mix[~touched])
print(f"limited {int(over.sum())} samples. Unchanged parts identical to the source: {same}. Changed: {touched.mean() * 100:.2f}% of the window")
sf.write(SYNC / "mix_censored.wav", out, sr, subtype="PCM_24")
print("wrote", SYNC / "mix_censored.wav")
