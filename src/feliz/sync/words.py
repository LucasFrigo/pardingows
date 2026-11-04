# Word times from faster-whisper-medium on the Demucs vocal stem. Two passes, with and without the lyrics as a prompt.
# Run through uv (python may not be on PATH):
#   uvx --python 3.11 --from faster-whisper python src/feliz/sync/words.py
# Writes blender/feliz/sync/whisper.json with times in song seconds.
import json
import pathlib
import sys

from faster_whisper import WhisperModel

ROOT = pathlib.Path(__file__).resolve().parents[3]
SYNC = ROOT / "blender" / "feliz" / "sync"
STEM = SYNC / "htdemucs" / "window_12_41" / "vocals.wav"
STEM_START = 12.0  # song second where the stem begins

LYRICS = (
    "hoje eu sou um pardo feliz, tenho a pardo energia, nada vai abalar o pardo, comigo, pardo repita, "
    "hoje eu sou um pardo feliz, pardo só quer ser feliz, berg, o que o pardo quer? o pardo quer ser feliz, "
    "beat plic ploc, não fodo com tiktok, frutiger aero neles, deixando os berg em choque"
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
