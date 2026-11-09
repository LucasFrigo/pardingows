# Second, independent word timer: CTC forced alignment (torchaudio MMS_FA) of the known lyrics onto the vocal stem.
# Each line is aligned inside its own window, so an error in one line can't drift into the next.
# Spellings are phonetic for a romanised acoustic model; '-' marks syllable breaks (stripped before aligning), and each
# syllable's onset is the start of its first character's CTC span. The bouncing ball lands on those onsets.
# Keys with a letter suffix are spelling variants of a line, aligned only to compare scores.
#   uv run --no-project --python 3.11 --with "torch==2.5.1" --with "torchaudio==2.5.1" --with soundfile --with "numpy<2" \
#     --index https://download.pytorch.org/whl/cu124 --index-strategy unsafe-best-match python src/erva/sync/align.py
# Writes blender/erva/sync/align.json with song seconds.
import json
import pathlib
import sys

import soundfile as sf
import torch
import torchaudio

ROOT = pathlib.Path(__file__).resolve().parents[3]
SYNC = ROOT / "blender" / "erva" / "sync"
T0 = 0.0  # the stem covers the whole song
sys.stdout.reconfigure(encoding="utf-8")

# (window start, window end, phonetic text). Windows sit in the dip before each line.
LINES = json.loads((pathlib.Path(__file__).parent / "lines.json").read_text(encoding="utf-8"))

device = "cuda" if torch.cuda.is_available() else "cpu"
print("device", device)
bundle = torchaudio.pipelines.MMS_FA
model = bundle.get_model().to(device)
tok = bundle.get_tokenizer()
aligner = bundle.get_aligner()

raw, sr = sf.read(SYNC / "htdemucs" / "vocals.wav", dtype="float32", always_2d=True)
wav = torchaudio.functional.resample(torch.from_numpy(raw.T).mean(0, keepdim=True), sr, bundle.sample_rate)

out = {}
for key, (a, z, text) in LINES.items():
    i0, i1 = int((a - T0) * bundle.sample_rate), int((z - T0) * bundle.sample_rate)
    with torch.inference_mode():
        emission, _ = model(wav[:, i0:i1].to(device))
    marked = text.split()
    words = [w.replace("-", "") for w in marked]
    spans = aligner(emission[0], tok(words))
    ratio = (i1 - i0) / emission.size(1) / bundle.sample_rate
    rows = []
    for w, m, sp in zip(words, marked, spans):
        # character index where each syllable starts
        starts, k = [0], 0
        for ch in m:
            if ch == "-":
                starts.append(k)
            else:
                k += 1
        rows.append({"w": w, "t0": round(a + sp[0].start * ratio, 3), "t1": round(a + sp[-1].end * ratio, 3),
                     "score": round(sum(s.score * (s.end - s.start) for s in sp) / sum(s.end - s.start for s in sp), 3),
                     "syl": [round(a + sp[s].start * ratio, 3) for s in starts],
                     "chars": [[round(a + s.start * ratio, 3), round(a + s.end * ratio, 3)] for s in sp]})
    mean = sum(r["score"] * (r["t1"] - r["t0"]) for r in rows) / sum(r["t1"] - r["t0"] for r in rows)
    out[key] = {"score": round(mean, 3), "words": rows}
    print(f"[{key:>3}] score {mean:.3f}  " + "  ".join(f"{r['w']} {r['t0']:.2f}-{r['t1']:.2f}({r['score']:.2f})" for r in rows))

(SYNC / "align.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
