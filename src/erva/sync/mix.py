# Builds the video's audio: the song from START to END, with the vocals taken out at both edges by switching to the
# Demucs instrumental (the previous verse's "estar" holds until 47.64; the next verse starts at 99.04), then a fade-out
# over the FIM bar's last second.
#   uv run --no-project --python 3.11 --with soundfile --with "numpy<2" python src/erva/sync/mix.py
# Writes blender/erva/sync/mix.wav, which starts at START (timeline mix_t0).
import json
import pathlib

import numpy as np
import soundfile as sf

ROOT = pathlib.Path(__file__).resolve().parents[3]
SYNC = ROOT / "blender" / "erva" / "sync"
TL = json.loads((ROOT / "src" / "erva" / "timeline.json").read_text(encoding="utf-8"))
START = TL["start"]
END = START + TL["frames"] / TL["fps"]
VOX_IN = (47.645, 47.680)   # instrumental -> song
VOX_OUT = (99.100, 99.200)  # song -> instrumental
FADE = (END - 1.0, END)

song, sr = sf.read(SYNC / "song.wav", dtype="float32", always_2d=True)
inst, sr2 = sf.read(SYNC / "htdemucs" / "no_vocals.wav", dtype="float32", always_2d=True)
assert sr == sr2
i0, i1 = int(round(START * sr)), int(round(END * sr))
t = (np.arange(i0, i1) / sr)[:, None]


def ramp(t, a, z):
    """0 before a, 1 after z, raised-cosine between."""
    x = np.clip((t - a) / (z - a), 0, 1)
    return 0.5 - 0.5 * np.cos(np.pi * x)


g = ramp(t, *VOX_IN) * (1 - ramp(t, *VOX_OUT))  # 1 where the full song plays
out = song[i0:i1] * g + inst[i0:i1] * (1 - g)
out *= 1 - ramp(t, *FADE)
peak = float(np.abs(out).max())
sf.write(SYNC / "mix.wav", out, sr, subtype="PCM_24")
print(f"mix.wav {START}-{END:.3f} s, {len(out) / sr:.3f} s, peak {20 * np.log10(peak):.1f} dBFS")
