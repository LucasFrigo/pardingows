# Measures sync on a finished MP4. Target: every word within 1 frame.
#   uv run --no-project --python 3.11 --with numpy --with soundfile python src/pardao/sync/check.py out/pardao-2000/pardao-2000-proof.mp4
# Audio: for each word, a slice of the censored mix around its attack is located in the MP4's decoded audio by cross-correlation,
#   so AAC delay or any other shift is measured on the real file rather than assumed.
# Video: the frame each word really appears on is read from the MP4's pixels, inside that word's caption box.
# Also compares the whole file to the song (AAC noise only) and reports the loop edges. This video has no bleeps.
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
SYNC = ROOT / "blender" / "pardao" / "sync"
sys.stdout.reconfigure(encoding="utf-8")

mp4 = pathlib.Path(sys.argv[1]).resolve()
meta = json.loads(mp4.with_suffix(".boxes.json").read_text(encoding="utf-8"))
START, FPS, FRAMES, BOXES, SRC_T0 = meta["start"], meta["fps"], meta["frames"], meta["boxes"], meta["mix_t0"]
BLEEPS = []
W, H = 1080, 1920

# Format
info = subprocess.run([FFMPEG, "-hide_banner", "-i", str(mp4)], capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
print("\n".join(l.strip() for l in info.splitlines() if re.search(r"Duration|Stream", l)))


def mono(path, tmp, name, extra=()):
    wav = pathlib.Path(tmp) / name
    subprocess.run([FFMPEG, "-y", "-v", "error", *extra, "-i", str(path), "-vn", "-ac", "1", "-ar", "44100", str(wav)], check=True)
    return sf.read(wav, dtype="float32")[0]


with tempfile.TemporaryDirectory() as tmp:
    dec = mono(mp4, tmp, "a.wav")
    src = raw = mono(SYNC / "song.wav", tmp, "s.wav")
sr = 44100


def locate(t):
    """Where the source audio around song time t really is in the MP4, in seconds of MP4 time."""
    half = int(0.15 * sr)
    reach = int(0.1 * sr)
    # A word near the start of the file has no audio before it to compare, so its slice moves right and only the shift is used
    anchor = max(t, START + (half + reach) / sr)
    c = int((anchor - SRC_T0) * sr)
    ref = src[c - half:c + half]
    exp = int((anchor - START) * sr)
    i0 = exp - half - reach
    seg = dec[i0:exp + half + reach]
    if len(seg) < len(ref):
        return None
    n = len(seg) + len(ref)
    corr = np.fft.irfft(np.fft.rfft(seg, n) * np.conj(np.fft.rfft(ref, n)), n)[: len(seg) - len(ref) + 1]
    best = int(np.argmax(corr))
    return (i0 + best + half) / sr - (anchor - t)


# Video: walk the file once, keep each frame's pixels only inside the word boxes
proc = subprocess.Popen([FFMPEG, "-v", "error", "-i", str(mp4), "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1"], stdout=subprocess.PIPE)
diffs = {i: np.zeros(FRAMES + 1) for i in range(len(BOXES))}
prev = None
count = 0
while True:
    buf = proc.stdout.read(W * H)
    if len(buf) < W * H:
        break
    fr = np.frombuffer(buf, np.uint8).reshape(H, W).astype(np.int16)
    if prev is not None:
        for i, b in enumerate(BOXES):
            y0, y1, x0, x1 = b["y"], b["y"] + b["h"], b["x"], b["x"] + b["w"]
            diffs[i][count] = np.abs(fr[y0:y1, x0:x1] - prev[y0:y1, x0:x1]).mean()
    prev = fr
    count += 1
proc.wait()
print(f"decoded {count} video frames (expected {FRAMES})")

line_start = {}
for b in BOXES:
    line_start.setdefault(b["line"], round((b["t"] - START) * FPS))
# The dialogue box opens over the first 3 frames of each line (ui.mjs), which changes every pixel in it. A word due inside that
# opening can't be told apart from it, so it is reported as set by code instead of measured.
TL = json.loads((ROOT / "src" / "pardao" / "timeline.json").read_text(encoding="utf-8"))
cut = {i + 1: round((s["t"] - START) * FPS) for i, s in enumerate(TL["shots"])}

print(f"\n{'ln':>2} {'word':14} {'song':>7} {'attack in mp4':>13} {'shift ms':>8} {'shows on':>8} {'off frames':>10}")
worst = 0.0
bad = []
shifts = []
for i, b in enumerate(BOXES):
    exp = round((b["t"] - START) * FPS)
    first_word = exp == line_start[b["line"]]
    if exp - cut[b["line"]] < 3:
        print(f"{b['line']:>2} {b['word']:14} {b['t']:7.2f}  due {exp - cut[b['line']]} frames into the box opening: set by code, not measured")
        continue
    lo = max(cut[b["line"]] + 3, exp - 6) if first_word else max(line_start[b["line"]] + 1, exp - 6, cut[b["line"]] + 3)
    win = diffs[i][lo:min(FRAMES, exp + 7)]
    if win.size == 0 or win.max() == 0:
        shown = exp if exp == 0 else None
    else:
        shown = lo + int(np.argmax(win > win.max() * 0.5))
    at = locate(b["t"])
    if at is None or shown is None:
        print(f"{b['line']:>2} {b['word']:14} {b['t']:7.2f}  not measured (at the edge of the file or no pixel change)")
        continue
    shift = at - (b["t"] - START)
    shifts.append(shift)
    off = shown - at * FPS
    worst = max(worst, abs(off))
    if abs(off) > 1:
        bad.append(f"{b['line']}:{b['word']}")
    print(f"{b['line']:>2} {b['word']:14} {b['t']:7.2f} {at:13.3f} {shift * 1000:8.1f} {shown + 1:8d} {off:+10.2f}")

print(f"\nmeasured audio shift: median {np.median(shifts) * 1000:.1f} ms, range {min(shifts) * 1000:.1f} to {max(shifts) * 1000:.1f} ms")
print(f"worst word: {worst:.2f} frames. Over 1 frame: {bad or 'none'}")

# Whole-file match against the song. Lag is the measured median shift.
lag = int(round(float(np.median(shifts)) * sr))
rms = lambda x: float(np.sqrt(np.mean(x**2)) + 1e-9)
db = lambda x: 20 * np.log10(x)
if not BLEEPS:
    n = min(len(dec) - lag, int((FRAMES / FPS) * sr))
    s0 = int((START - SRC_T0) * sr)
    print("\n" + f"no bleeps: whole file against the original mix {db(rms(dec[lag:lag + n] - raw[s0:s0 + n])):.1f} dB (AAC noise only), level {db(rms(raw[s0:s0 + n])):.1f} dB")
# Loop: nothing of the neighbouring words may leak in.
edge = int(0.05 * sr)
print(f"\nloop: first 50 ms level {db(rms(dec[:edge])):.1f} dB, last 50 ms level {db(rms(dec[-edge:])):.1f} dB, audio length {len(dec) / sr:.3f} s, video {FRAMES / FPS:.3f} s")
