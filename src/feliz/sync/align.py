# Second, independent word timer: CTC forced alignment (torchaudio MMS_FA) of the known lyrics onto the vocal stem.
# Each line is aligned inside its own window, so an error in one line can't drift into the next.
# Lines 4 and 6 are aligned with and without the extra "o" that Whisper hears, and the scores compared.
#   uv run --no-project --python 3.11 --with "torch==2.5.1" --with "torchaudio==2.5.1" --with soundfile --with "numpy<2" \
#     --index https://download.pytorch.org/whl/cu124 --index-strategy unsafe-best-match python src/feliz/sync/align.py
# Writes blender/feliz/sync/align.json with song seconds.
import json
import pathlib
import sys

import soundfile as sf
import torch
import torchaudio
import torchaudio.functional as F

ROOT = pathlib.Path(__file__).resolve().parents[3]
SYNC = ROOT / "blender" / "feliz" / "sync"
T0 = 12.0
sys.stdout.reconfigure(encoding="utf-8")

# Window starts sit in the dip before each line, spellings are phonetic-ish for a romanised acoustic model
LINES = {
    "1": (14.60, 16.72, "oje eu sou um pardo feliz"),
    "2": (16.72, 18.62, "tenho a pardo energia"),
    "3": (18.62, 20.46, "nada vai abalar o pardo"),
    "4": (20.40, 22.46, "comigo pardo repita"),
    "4o": (20.40, 22.46, "comigo o pardo repita"),
    "5": (22.42, 24.44, "oje eu sou um pardo feliz"),
    "6": (24.40, 26.40, "pardo so quer ser feliz"),
    "6o": (24.40, 26.40, "o pardo so quer ser feliz"),
    "7": (26.36, 28.10, "berg o que o pardo quer"),
    "8": (28.05, 30.70, "o pardo quer ser feliz"),
    "9": (30.68, 32.04, "biti pliqui ploqui"),
    "10": (32.04, 33.80, "num fodo com tiqui toqui"),
    "11": (33.70, 35.92, "frutiguer aero neles"),
    "12": (35.90, 37.86, "deixando os berg em choque"),
}

device = "cuda" if torch.cuda.is_available() else "cpu"
print("device", device)
bundle = torchaudio.pipelines.MMS_FA
model = bundle.get_model().to(device)
tok = bundle.get_tokenizer()
aligner = bundle.get_aligner()

raw, sr = sf.read(SYNC / "htdemucs" / "window_12_41" / "vocals.wav", dtype="float32", always_2d=True)
wav = torchaudio.functional.resample(torch.from_numpy(raw.T).mean(0, keepdim=True), sr, bundle.sample_rate)

out = {}
for key, (a, z, text) in LINES.items():
    i0, i1 = int((a - T0) * bundle.sample_rate), int((z - T0) * bundle.sample_rate)
    with torch.inference_mode():
        emission, _ = model(wav[:, i0:i1].to(device))
    words = text.split()
    spans = aligner(emission[0], tok(words))
    ratio = (i1 - i0) / emission.size(1) / bundle.sample_rate
    rows = []
    for w, sp in zip(words, spans):
        rows.append({"w": w, "t0": round(a + sp[0].start * ratio, 3), "t1": round(a + sp[-1].end * ratio, 3),
                     "score": round(sum(s.score * (s.end - s.start) for s in sp) / sum(s.end - s.start for s in sp), 3),
                     "chars": [[round(a + s.start * ratio, 3), round(a + s.end * ratio, 3)] for s in sp]})
    mean = sum(r["score"] * (r["t1"] - r["t0"]) for r in rows) / sum(r["t1"] - r["t0"] for r in rows)
    out[key] = {"score": round(mean, 3), "words": rows}
    print(f"[{key:>3}] score {mean:.3f}  " + "  ".join(f"{r['w']} {r['t0']:.2f}-{r['t1']:.2f}({r['score']:.2f})" for r in rows))

(SYNC / "align.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
