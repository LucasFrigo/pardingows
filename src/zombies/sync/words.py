# Word times from faster-whisper-medium on the Demucs vocal stem. Two passes, with and without the lyrics as a prompt.
#   uvx --python 3.11 --from faster-whisper python src/zombies/sync/words.py
# Writes blender/zombies/sync/whisper.json with times in song seconds.
import json
import pathlib
import sys

from faster_whisper import WhisperModel

ROOT = pathlib.Path(__file__).resolve().parents[3]
SYNC = ROOT / "blender" / "zombies" / "sync"
STEM = SYNC / "htdemucs" / "window_60_100" / "vocals.wav"
STEM_START = 60.0  # song second where the stem begins

LYRICS = (
    "pardo apocalipse, com muita canalhisse, meu pau já tá assado, isso é resident pardo, "
    "pardolipse na cidade, pardos não fogem da maldade, muita promiscuidade, tome pica a vontade, "
    "uma zombie me mordendo, me deixou arrepiado, puxei pelos cabelo, ficou com o cu raspado, "
    "necrofilia, zombifilia, fodo até a sua filha, careca ou cabeluda, caolha ou banguela, "
    "sodoma e gomorra, cheira cola e chupa rola, baba ovo na masmorra, se engasga até que morra"
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
