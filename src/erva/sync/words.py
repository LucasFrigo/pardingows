# Word times from faster-whisper-medium on the Demucs vocal stem, two passes (plain, and with the lyrics as a prompt).
#   uvx --python 3.11 --from faster-whisper --with soundfile python src/erva/sync/words.py
# Only CLIP_A..CLIP_Z of the stem is transcribed. Writes blender/erva/sync/whisper.json with times in song seconds.
import json
import pathlib
import sys

import numpy as np
from faster_whisper import WhisperModel
from faster_whisper.audio import decode_audio

ROOT = pathlib.Path(__file__).resolve().parents[3]
SYNC = ROOT / "blender" / "erva" / "sync"
STEM = SYNC / "htdemucs" / "vocals.wav"
CLIP_A, CLIP_Z = 40.0, 105.0

LYRICS = (
    "vou te contar a história do pardão e da erva, só espera eu dar um puxe no cachimbo com a eva, mnham mnham mnham. "
    "pardão estava andando sozinho no meretrevaz, deu dois passo pra frente e tava no meio da selva. "
    "andando no jardim uma cobra veio de fininho, chegou na menisquência, ofereceu um baseadinho, mnham mnham mnham. "
    "pardão sem pensar aceitou esse novo caminho. essa é da boa pardão, o que achou, fala pra mim. "
    "essa flor é boa mas acho que não compensa. tarde demais pardão, já roubei sua vicência. "
    "sua alma é minha agora, não venha com menisquência. hahaha hohoho hohoho hahaha. "
    "vai se foder sua cobra mole, você não me assusta, sou fechado com os pardo, já veste a carapuça. "
    "fumei dois cigarro, ouve minha barra sua puta, cê tá fechado com os cara, não caio na sua arapuca."
)

sys.stdout.reconfigure(encoding="utf-8")
audio = decode_audio(str(STEM), sampling_rate=16000)[int(CLIP_A * 16000):int(CLIP_Z * 16000)].astype(np.float32)
model = WhisperModel("medium", device="cpu", compute_type="int8")
result = {}
for name, prompt in (("plain", None), ("prompted", LYRICS)):
    segs, _ = model.transcribe(
        audio, language="pt", word_timestamps=True, condition_on_previous_text=False,
        vad_filter=False, beam_size=5, initial_prompt=prompt,
    )
    words = []
    for s in segs:
        line = []
        for w in s.words:
            words.append({"w": w.word.strip(), "t0": round(w.start + CLIP_A, 3),
                          "t1": round(w.end + CLIP_A, 3), "p": round(w.probability, 3)})
            line.append(f"{w.word.strip()}@{w.start + CLIP_A:.2f}")
        print(f"[{name}] " + " ".join(line))
    result[name] = words

(SYNC / "whisper.json").write_text(json.dumps(result, ensure_ascii=False, indent=0), encoding="utf-8")
