# Word times from faster-whisper-medium on the Demucs vocal stem. Two passes, with and without the lyrics as a prompt.
#   uvx --python 3.11 --from faster-whisper python src/pardao/sync/words.py
# Writes blender/pardao/sync/whisper.json with times in song seconds. The stem covers the whole song (STEM_START = 0).
import json
import pathlib
import sys

from faster_whisper import WhisperModel

ROOT = pathlib.Path(__file__).resolve().parents[3]
SYNC = ROOT / "blender" / "pardao" / "sync"
STEM = SYNC / "htdemucs" / "vocals.wav"
STEM_START = 0.0

LYRICS = (
    "descobri que eu sou pardo, eu não sumo no escuro, na presença dos pardos, eu fumo muito e fico burro, "
    "toda terça um banger novo, pardo isso é absurdo, os mildingows te enquadram, fuzilam você no muro, só lamento, "
    "então presta atenção nesse novo aquecimento, se você não cola terça perde os acontecimento, "
    "tenho mil ideias novas, aproveito o momento, com o sotaque carioca, mais malandro que esse jumento"
)

sys.stdout.reconfigure(encoding="utf-8")
model = WhisperModel("medium", device="cpu", compute_type="int8")
result = {}
for name, prompt in (("plain", None), ("prompted", LYRICS)):
    segs, _ = model.transcribe(
        str(STEM), language="pt", word_timestamps=True, condition_on_previous_text=False,
        vad_filter=False, beam_size=5, initial_prompt=prompt,
    )
    words = []
    for s in segs:
        line = []
        for w in s.words:
            words.append({"w": w.word.strip(), "t0": round(w.start + STEM_START, 3),
                          "t1": round(w.end + STEM_START, 3), "p": round(w.probability, 3)})
            line.append(f"{w.word.strip()}@{w.start + STEM_START:.2f}")
        print(f"[{name}] " + " ".join(line))
    result[name] = words

(SYNC / "whisper.json").write_text(json.dumps(result, ensure_ascii=False, indent=0), encoding="utf-8")
