# Second, independent word timer: CTC forced alignment (torchaudio MMS_FA) of the known lyrics onto the vocal stem.
# Each line is aligned inside its own window, so an error in one line can't drift into the next.
# Keys with a letter suffix are spelling variants of a line, aligned only to compare scores.
#   uv run --no-project --python 3.11 --with "torch==2.5.1" --with "torchaudio==2.5.1" --with soundfile --with "numpy<2" \
#     --index https://download.pytorch.org/whl/cu124 --index-strategy unsafe-best-match python src/lego/sync/align.py
# Writes blender/lego/sync/align.json with song seconds.
import json
import pathlib
import sys

import soundfile as sf
import torch
import torchaudio
import torchaudio.functional as F

ROOT = pathlib.Path(__file__).resolve().parents[3]
SYNC = ROOT / "blender" / "lego" / "sync"
T0 = 214.0
sys.stdout.reconfigure(encoding="utf-8")

# Window starts sit in the dip before each line, spellings are phonetic-ish for a romanised acoustic model
LINES = {
    "1": (218.30, 221.86, "oje eu nao fico puto fodassi israel"),
    "2": (221.72, 225.62, "tersa dos pardos e a data vou ficar na moral"),
    "3": (225.56, 229.60, "pausar os planos de roubar a la casa de papel"),
    "3a": (225.56, 229.60, "pausa os planos de roubar a la casa de papel"),
    "4": (229.54, 233.30, "sem menisquencia tristi sem pensar nada mal"),
    "4a": (229.54, 233.30, "sem reminisquencia tristi sem pensar nada mal"),
    "4b": (229.54, 233.30, "sem menispuencia tristi sem pensar nada mal"),
    "5": (233.24, 237.34, "em busca da felicidadi e o remix dos pardos"),
    "6": (237.28, 241.14, "sessenta i seti ponto novi noia por metro quadrado"),
    "7": (241.08, 245.68, "eu quero saber quem e que vai bolar mais um baseado"),
    "8": (245.62, 249.14, "pra eu chegar em casa e dormir bem retardado"),
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
