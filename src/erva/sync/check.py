# Measures sync on a finished MP4. Target: every syllable lights within 1 frame of its sung onset.
#   uv run --no-project --python 3.11 --with numpy --with soundfile python src/erva/sync/check.py out/pardao-erva/pardao-e-a-erva-proof.mp4
# Audio: for each syllable, a slice of mix.wav around its onset is located in the MP4's decoded audio by cross-correlation,
#   so AAC delay or any other shift is measured on the real file rather than assumed.
# Video: the frame each syllable really lights (dim -> white) is read from the MP4's pixels, in the lower half of that
#   syllable's letters, where the bouncing ball never passes.
# Needs <video>.boxes.json, which render.mjs writes next to the video.
import json
import pathlib
import re
import subprocess
import sys
import tempfile

import numpy as np
import soundfile as sf

ROOT = pathlib.Path(__file__).resolve().parents[3]
FFMPEG = str(ROOT / "node_modules" / "ffmpeg-static" / "ffmpeg.exe")
SYNC = ROOT / "blender" / "erva" / "sync"
sys.stdout.reconfigure(encoding="utf-8")

mp4 = pathlib.Path(sys.argv[1]).resolve()
meta = json.loads(mp4.with_suffix(".boxes.json").read_text(encoding="utf-8"))
START, FPS, FRAMES, BOXES, SRC_T0 = meta["start"], meta["fps"], meta["frames"], meta["boxes"], meta["mix_t0"]
W, H = 1080, 1920

info = subprocess.run([FFMPEG, "-hide_banner", "-i", str(mp4)], capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
print("\n".join(l.strip() for l in info.splitlines() if re.search(r"Duration|Stream", l)))


def mono(path, tmp, name):
    wav = pathlib.Path(tmp) / name
    subprocess.run([FFMPEG, "-y", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", "44100", str(wav)], check=True)
    return sf.read(wav, dtype="float32")[0]


with tempfile.TemporaryDirectory() as tmp:
    dec = mono(mp4, tmp, "a.wav")
    src = mono(SYNC / "mix.wav", tmp, "s.wav")
sr = 44100


def locate(t):
    """Where the mix around song time t really is in the MP4, in seconds of MP4 time."""
    half, reach = int(0.15 * sr), int(0.1 * sr)
    anchor = min(max(t, START + (half + reach) / sr), START + FRAMES / FPS - (half + reach) / sr)
    c = int((anchor - SRC_T0) * sr)
    ref = src[c - half:c + half]
    exp = int((anchor - START) * sr)
    i0 = exp - half - reach
    seg = dec[i0:exp + half + reach]
    if len(seg) < len(ref) or len(ref) < 2 * half:
        return None
    n = len(seg) + len(ref)
    corr = np.fft.irfft(np.fft.rfft(seg, n) * np.conj(np.fft.rfft(ref, n)), n)[: len(seg) - len(ref) + 1]
    return (i0 + int(np.argmax(corr)) + half) / sr - (anchor - t)


# Syllable regions, then one pass over the video keeping each region's mean brightness per frame
regions = []
for b in BOXES:
    for k, (t, (x0, x1)) in enumerate(zip(b["syl"], b["sx"])):
        regions.append(dict(card=b["card"], card_t=b["card_t"], word=b["word"], k=k, t=t, x0=x0 + 2, x1=max(x0 + 4, x1 - 2), y0=b["y0"], y1=b["y1"]))
level = np.zeros((len(regions), FRAMES + 1))
proc = subprocess.Popen([FFMPEG, "-v", "error", "-i", str(mp4), "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1"], stdout=subprocess.PIPE)
count = 0
while True:
    buf = proc.stdout.read(W * H)
    if len(buf) < W * H:
        break
    fr = np.frombuffer(buf, np.uint8).reshape(H, W)
    for i, r in enumerate(regions):
        level[i][count] = fr[r["y0"]:r["y1"], r["x0"]:r["x1"]].mean()
    count += 1
proc.wait()
print(f"decoded {count} video frames (expected {FRAMES})")

print(f"\n{'cd':>2} {'syllable':16} {'song':>7} {'in mp4':>8} {'shift ms':>8} {'lights on':>9} {'off frames':>10}")
worst, bad, shifts, skipped = 0.0, [], [], 0
for i, r in enumerate(regions):
    exp = round((r["t"] - START) * FPS)
    opens = round((r["card_t"] - START) * FPS)
    name = f"{r['word']}[{r['k']}]"
    if exp - opens < 3:
        skipped += 1
        print(f"{r['card']:>2} {name:16} {r['t']:7.2f}  due {exp - opens} frames into the card's fade-in: set by code, not measured")
        continue
    lo, hi = max(opens + 3, exp - 6), min(FRAMES - 1, exp + 7)
    rise = np.diff(level[i][lo - 1:hi + 1])
    shown = lo + int(np.argmax(rise)) if rise.size and rise.max() > 8 else None
    at = locate(r["t"])
    if at is None or shown is None:
        print(f"{r['card']:>2} {name:16} {r['t']:7.2f}  not measured")
        continue
    shift = at - (r["t"] - START)
    shifts.append(shift)
    off = shown - at * FPS
    worst = max(worst, abs(off))
    if abs(off) > 1:
        bad.append(f"{r['card']}:{name}")
    print(f"{r['card']:>2} {name:16} {r['t']:7.2f} {at:8.3f} {shift * 1000:8.1f} {shown + 1:9d} {off:+10.2f}")

print(f"\nmeasured audio shift: median {np.median(shifts) * 1000:.1f} ms, range {min(shifts) * 1000:.1f} to {max(shifts) * 1000:.1f} ms")
print(f"{len(shifts)} syllables measured, {skipped} set by code. Worst: {worst:.2f} frames. Over 1 frame: {bad or 'none'}")
rms = lambda x: float(np.sqrt(np.mean(x**2)) + 1e-9)
db = lambda x: 20 * np.log10(x)
lag = int(round(float(np.median(shifts)) * sr))
n = min(len(dec) - lag, len(src))
print(f"whole file against mix.wav: {db(rms(dec[lag:lag + n] - src[:n])):.1f} dB difference (AAC noise only), level {db(rms(src[:n])):.1f} dB")
print(f"audio length {len(dec) / sr:.3f} s, video {FRAMES / FPS:.3f} s")
