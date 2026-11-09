# Measures sync and censoring on a finished MP4. Target: every word within 1 frame, a bleep on all 5 gags, nothing leaking at the cuts.
#   uv run --no-project --python 3.11 --with numpy --with soundfile python src/zombies/sync/check.py out/pardos-vs-zombies/pardos-vs-zombies-proof.mp4
# Audio: for each word, a slice of the censored mix around its attack is located in the MP4's decoded audio by cross-correlation,
#   so AAC delay or any other shift is measured on the real file rather than assumed.
# Video: the frame each word really appears on is read from the MP4's pixels, inside that word's caption box.
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
sys.stdout.reconfigure(encoding="utf-8")

mp4 = pathlib.Path(sys.argv[1]).resolve()
meta = json.loads(mp4.with_suffix(".boxes.json").read_text(encoding="utf-8"))
START, FPS, FRAMES, BOXES, GAGS, SONG_FRAMES, MIX_T0 = (meta[k] for k in ("start", "fps", "frames", "boxes", "gags", "song_frames", "mix_t0"))
W, H = 1080, 1920

info = subprocess.run([FFMPEG, "-hide_banner", "-i", str(mp4)], capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
print("\n".join(l.strip() for l in info.splitlines() if re.search(r"Duration|Stream", l)))

with tempfile.TemporaryDirectory() as tmp:
    wav = pathlib.Path(tmp) / "a.wav"
    subprocess.run([FFMPEG, "-y", "-v", "error", "-i", str(mp4), "-vn", "-ac", "1", "-ar", "44100", str(wav)], check=True)
    dec, sr = sf.read(wav, dtype="float32")
    src_wav = pathlib.Path(tmp) / "s.wav"
    subprocess.run([FFMPEG, "-y", "-v", "error", "-i", str(ROOT / "blender" / "zombies" / "sync" / "mix_censored.wav"), "-ac", "1", "-ar", "44100", str(src_wav)], check=True)
    src, _ = sf.read(src_wav, dtype="float32")


def locate(t):
    """Where the source audio around song time t really is in the MP4, in seconds of MP4 time."""
    half = int(0.15 * sr)
    reach = int(0.1 * sr)
    # A word near a file edge has too little audio to compare, so its slice moves inward and only the shift is used
    lo = START + (half + reach) / sr
    hi = START + SONG_FRAMES / FPS - (half + reach) / sr
    anchor = min(max(t, lo), hi)
    c = int((anchor - MIX_T0) * sr)
    ref = src[c - half:c + half]
    exp = int((anchor - START) * sr)
    i0 = exp - half - reach
    seg = dec[i0:exp + half + reach]
    if len(seg) < len(ref):
        return None
    n = len(seg) + len(ref)
    corr = np.fft.irfft(np.fft.rfft(seg, n) * np.conj(np.fft.rfft(ref, n)), n)[: len(seg) - len(ref) + 1]
    return (i0 + int(np.argmax(corr)) + half) / sr - (anchor - t)


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

print(f"\n{'ln':>2} {'word':14} {'song':>6} {'attack in mp4':>13} {'shift ms':>8} {'shows on':>8} {'off frames':>10}")
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
        print(f"{b['line']:>2} {b['word']:14} {b['t']:6.2f}  not measured (at the edge of the file or no pixel change)")
        continue
    shift = at - (b["t"] - START)
    shifts.append(shift)
    off = shown - at * FPS
    worst = max(worst, abs(off))
    if abs(off) > 1:
        bad.append(f"{b['line']}:{b['word']}")
    print(f"{b['line']:>2} {b['word']:14} {b['t']:6.2f} {at:13.3f} {shift * 1000:8.1f} {shown + 1:8d} {off:+10.2f}")

median_shift = float(np.median(shifts))
print(f"\nmeasured audio shift: median {median_shift * 1000:.1f} ms, range {min(shifts) * 1000:.1f} to {max(shifts) * 1000:.1f} ms")
print(f"worst word: {worst:.2f} frames. Over 1 frame: {bad or 'none'}")


def tone_db(a, z):
    """Level of the 1 kHz bleep inside a slice of the MP4's audio."""
    i0, i1 = int(a * sr), int(z * sr)
    x = dec[i0:i1] * np.hanning(i1 - i0)
    spec = np.abs(np.fft.rfft(x)) / (i1 - i0) * 4
    f = np.fft.rfftfreq(i1 - i0, 1 / sr)
    return 20 * np.log10(spec[(f > 950) & (f < 1050)].max() + 1e-9)


print(f"\n{'gag':6} {'bleep song':>15} {'1 kHz inside':>13} {'just before':>12} {'rise':>8}")
missing = []
for g in GAGS:
    a, z = g["bleep"]
    va, vz = a - START + median_shift, z - START + median_shift
    inside = tone_db(va + 0.01, vz - 0.01)
    before = tone_db(va - 0.13, va - 0.03)
    if inside - before < 12:
        missing.append(g["word"])
    print(f"{g['word']:6} {a:7.2f}-{z:7.2f} {inside:10.1f} dB {before:9.1f} dB {inside - before:5.1f} dB")
print(f"bleeps missing: {missing or 'none'}")

edge = int(0.05 * sr)
rms = lambda x: float(np.sqrt(np.mean(x**2)) + 1e-9)
dbs = lambda x: 20 * np.log10(rms(x))
song_end = int(SONG_FRAMES / FPS * sr)
print(f"\ncuts: first 50 ms {dbs(dec[:edge]):.1f} dB, last 50 ms of song {dbs(dec[song_end - edge:song_end]):.1f} dB, silent tail {dbs(dec[song_end + int(0.1 * sr):]):.1f} dB")
print(f"audio length {len(dec) / sr:.3f} s, video {FRAMES / FPS:.3f} s")

# Nothing of the source around the cuts may remain beyond them: the song's level just outside each cut, for comparison
print(f"source just before the cut in {dbs(src[int((START - 0.05 - MIX_T0) * sr):int((START - MIX_T0) * sr)]):.1f} dB (not in the file)")
