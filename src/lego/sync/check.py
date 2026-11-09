# Measures sync on a finished MP4. Target: every word within 1 frame.
#   uv run --no-project --python 3.11 --with numpy --with soundfile python src/lego/sync/check.py out/pardos-lego/pardos-lego-proof.mp4
# Audio: for each word, a slice of the censored mix around its attack is located in the MP4's decoded audio by cross-correlation,
#   so AAC delay or any other shift is measured on the real file rather than assumed.
# Video: the frame each word really appears on is read from the MP4's pixels, inside that word's caption box.
# Bleep: compares the MP4 to the uncensored and censored mixes inside the span, and confirms the audio outside it matches.
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
SYNC = ROOT / "blender" / "lego" / "sync"
sys.stdout.reconfigure(encoding="utf-8")

mp4 = pathlib.Path(sys.argv[1]).resolve()
meta = json.loads(mp4.with_suffix(".boxes.json").read_text(encoding="utf-8"))
START, FPS, FRAMES, BOXES, SRC_T0, BLEEPS = meta["start"], meta["fps"], meta["frames"], meta["boxes"], meta["mix_t0"], meta["bleeps"]
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
    src = mono(SYNC / "mix_censored.wav", tmp, "s.wav")
    raw = mono(SYNC / "window_214_253.wav", tmp, "r.wav")
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

print(f"\n{'ln':>2} {'word':14} {'song':>7} {'attack in mp4':>13} {'shift ms':>8} {'shows on':>8} {'off frames':>10}")
worst = 0.0
bad = []
shifts = []
for i, b in enumerate(BOXES):
    exp = round((b["t"] - START) * FPS)
    first_word = exp == line_start[b["line"]]
    lo = max(1, exp - 6) if first_word else max(line_start[b["line"]] + 1, exp - 6)
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

# Bleep: inside the span the file must follow the censored mix, not the original vocal. Lag is the measured median shift.
lag = int(round(float(np.median(shifts)) * sr))
rms = lambda x: float(np.sqrt(np.mean(x**2)) + 1e-9)
db = lambda x: 20 * np.log10(x)
if not BLEEPS:
    n = min(len(dec) - lag, int((FRAMES / FPS) * sr))
    s0 = int((START - SRC_T0) * sr)
    print("\n" + f"no bleeps: whole file against the original mix {db(rms(dec[lag:lag + n] - raw[s0:s0 + n])):.1f} dB (AAC noise only), level {db(rms(raw[s0:s0 + n])):.1f} dB")
for g in BLEEPS:
    a, z = g["span"]
    i0, i1 = int((a - START) * sr) + lag, int((z - START) * sr) + lag
    s0, s1 = int((a - SRC_T0) * sr), int((z - SRC_T0) * sr)
    n = min(i1 - i0, s1 - s0, len(dec) - i0)
    d, cen, ori = dec[i0:i0 + n], src[s0:s0 + n], raw[s0:s0 + n]
    print(f"\nbleep {g['word']} {a}-{z}: error against censored mix {db(rms(d - cen)):.1f} dB, against the original {db(rms(d - ori)):.1f} dB (lower is closer)")
if BLEEPS:
  ci = int((BLEEPS[0]["span"][0] - 0.5 - START) * sr) + lag
  cs = int((BLEEPS[0]["span"][0] - 0.5 - SRC_T0) * sr)
  print(f"outside the bleep, 0.4 s before it: error against the original {db(rms(dec[ci:ci + int(0.4 * sr)] - raw[cs:cs + int(0.4 * sr)])):.1f} dB, level {db(rms(raw[cs:cs + int(0.4 * sr)])):.1f} dB")

# Loop: nothing of the neighbouring words may leak in.
edge = int(0.05 * sr)
print(f"\nloop: first 50 ms level {db(rms(dec[:edge])):.1f} dB, last 50 ms level {db(rms(dec[-edge:])):.1f} dB, audio length {len(dec) / sr:.3f} s, video {FRAMES / FPS:.3f} s")
