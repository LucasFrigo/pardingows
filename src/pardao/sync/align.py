# Second, independent word timer: CTC forced alignment (torchaudio MMS_FA) of the known lyrics onto the vocal stem.
# Each line is aligned inside its own window, so an error in one line can't drift into the next.
# Keys with a letter suffix are spelling variants of a line, aligned only to compare scores.
#   uv run --no-project --python 3.11 --with "torch==2.5.1" --with "torchaudio==2.5.1" --with soundfile --with "numpy<2" \
#     --index https://download.pytorch.org/whl/cu124 --index-strategy unsafe-best-match python src/pardao/sync/align.py
# Writes blender/pardao/sync/align.json with song seconds.
import json
import pathlib
import sys

import soundfile as sf
import torch
import torchaudio
import torchaudio.functional as F

ROOT = pathlib.Path(__file__).resolve().parents[3]
SYNC = ROOT / "blender" / "pardao" / "sync"
T0 = 0.0  # the stem covers the whole song
sys.stdout.reconfigure(encoding="utf-8")

# Window starts sit in the dip before each line, spellings are phonetic-ish for a romanised acoustic model
LINES = {
    "1": (157.40, 160.15, "descobri ki eu so pardo"),
    "2": (160.05, 162.05, "eu nao sumo no escuro"),
    "3": (162.00, 163.65, "na presensa dos pardos"),
    "4": (163.60, 165.90, "eu fumo muito i fico burro"),
    "5": (165.85, 167.75, "toda tersa um banger novo"),
    "5a": (165.85, 167.75, "toda tersa um benguer novo"),
    "6": (167.70, 169.55, "pardo isso e absurdo"),
    "7": (169.50, 171.65, "os mildingous ti enquadram"),
    "8": (171.60, 173.75, "fuzilam voce no muro so lamento"),
    "8a": (171.60, 173.75, "fuzilam voce no muro"),
    "9": (173.55, 175.00, "entao presta atensao"),
    "10": (174.95, 177.20, "nessi novo aquecimento"),
    "11": (177.15, 179.20, "si voce nao cola tersa"),
    "12": (179.15, 181.00, "perdi os acontecimento"),
    "13": (180.95, 182.95, "tenho mil ideias novas"),
    "14": (182.90, 184.70, "aproveito o momento"),
    "15": (184.65, 186.45, "com o sotaki carioca"),
    "16": (186.40, 188.40, "mais malandro quiessi jumento"),
    "17": (188.30, 189.65, "pardjonson"),
}

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
