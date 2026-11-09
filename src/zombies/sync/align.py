# Second, independent word timer: CTC forced alignment (torchaudio MMS_FA) of the known lyrics onto the vocal stem.
# Each line is aligned inside its own window, so an error in one line can't drift into the next.
# Letter spans are kept: the bleep sits on the stressed vowel of each censored word.
# Lines 12 and 18 are aligned with and without the extra word Whisper hears, and the scores compared.
#   uv run --no-project --python 3.11 --with "torch==2.5.1" --with "torchaudio==2.5.1" --with soundfile --with "numpy<2" python src/zombies/sync/align.py
# Writes blender/zombies/sync/align.json with song seconds.
import json
import pathlib
import sys

import soundfile as sf
import torch
import torchaudio
import torchaudio.functional as F

ROOT = pathlib.Path(__file__).resolve().parents[3]
SYNC = ROOT / "blender" / "zombies" / "sync"
T0 = 60.0
sys.stdout.reconfigure(encoding="utf-8")

# Windows come from the draft Whisper pass and start in the dip before each line. Spellings are phonetic-ish for a romanised model.
LINES = {
    "1": (62.90, 64.74, "pardo apocalipse"),
    "2": (64.70, 66.36, "com muita canalice"),
    "3": (66.30, 68.06, "meu pau ja ta assado"),
    "4": (68.00, 69.76, "isso e resident pardo"),
    "5": (69.70, 71.32, "pardolipse na cidade"),
    "6": (71.26, 73.12, "pardos num fogem da maldade"),
    "7": (73.08, 74.76, "muita promiscuidade"),
    "8": (74.70, 76.50, "tome pica a vontade"),
    "9": (76.44, 78.22, "uma zombi me mordendo"),
    "10": (78.18, 80.14, "me deixou arrepiado"),
    "11": (80.10, 81.92, "puxei pelos cabelo"),
    "12": (81.88, 83.58, "ficou com o cu raspado"),
    "12n": (81.88, 83.58, "ficou com cu raspado"),
    "13": (83.54, 85.22, "necrofilia zombifilia"),
    "14": (85.16, 86.96, "fodo ate a sua filha"),
    "15": (86.92, 88.72, "careca ou cabeluda"),
    "16": (88.66, 90.36, "caolha ou banguela"),
    "17": (90.30, 92.02, "sodoma e gomorra"),
    "18": (91.96, 93.82, "cheira cola e chupa rola"),
    "18a": (91.96, 93.82, "cheira cola e chupa a rola"),
    "19": (93.78, 95.60, "baba ovo na masmorra"),
    "20": (95.54, 96.96, "se engasga ate que morra"),
}

device = "cuda" if torch.cuda.is_available() else "cpu"
print("device", device)
bundle = torchaudio.pipelines.MMS_FA
model = bundle.get_model().to(device)
tok = bundle.get_tokenizer()
aligner = bundle.get_aligner()

raw, sr = sf.read(SYNC / "htdemucs" / "window_60_100" / "vocals.wav", dtype="float32", always_2d=True)
wav = F.resample(torch.from_numpy(raw.T).mean(0, keepdim=True), sr, bundle.sample_rate)

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
