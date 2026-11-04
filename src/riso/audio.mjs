// Loudness + drum-hit envelopes of the video window, one value per frame, computed from the
// WAV itself (ffmpeg decode -> mono float). Drives boil and misregistration.
import { spawnSync } from 'child_process';
import ffmpeg from 'ffmpeg-static';
import { AUDIO_FILE, SONG_START, DURATION, FPS } from './timeline.mjs';

const SR = 22050;
const HOP = 256;

function decode() {
  const r = spawnSync(ffmpeg, ['-v', 'error', '-ss', String(SONG_START), '-t', String(DURATION + 0.2), '-i', AUDIO_FILE,
    '-ac', '1', '-ar', String(SR), '-f', 'f32le', 'pipe:1'], { maxBuffer: 1 << 28 });
  if (r.status) throw new Error(`ffmpeg decode failed: ${r.stderr}`);
  const b = r.stdout;
  return new Float32Array(b.buffer, b.byteOffset, b.length / 4);
}

// Positive log-energy flux per hop, normalised by its 95th percentile.
function flux(energy) {
  const f = new Float32Array(energy.length);
  for (let i = 1; i < energy.length; i++) f[i] = Math.max(0, Math.log(energy[i] + 1e-9) - Math.log(energy[i - 1] + 1e-9));
  const s = Array.from(f).sort((a, b) => a - b), p = s[Math.floor(s.length * 0.95)] || 1;
  return f.map(x => x / p);
}

function analyse() {
  const x = decode();
  const n = Math.floor(x.length / HOP);
  const eAll = new Float32Array(n), eHi = new Float32Array(n), eLo = new Float32Array(n);
  let lp = 0, prev = 0, prev2 = 0;
  const kLp = 1 - Math.exp(-2 * Math.PI * 140 / SR);
  for (let h = 0; h < n; h++) {
    let a = 0, hi = 0, lo = 0;
    for (let i = h * HOP; i < (h + 1) * HOP; i++) {
      const s = x[i];
      lp += (s - lp) * kLp;
      const d2 = s - 2 * prev + prev2;       // 2nd difference ~ high-pass
      prev2 = prev; prev = s;
      a += s * s; hi += d2 * d2; lo += lp * lp;
    }
    eAll[h] = a / HOP; eHi[h] = hi / HOP; eLo[h] = lo / HOP;
  }
  const fHi = flux(eHi), fLo = flux(eLo);
  const frames = Math.ceil(DURATION * FPS) + 2;
  const loud = new Float32Array(frames), snare = new Float32Array(frames), kick = new Float32Array(frames);
  const hopsPerFrame = SR / HOP / FPS;
  for (let f = 0; f < frames; f++) {
    const h0 = Math.floor(f * hopsPerFrame), h1 = Math.max(h0 + 1, Math.floor((f + 1) * hopsPerFrame));
    let e = 0, sh = 0, kl = 0;
    for (let h = h0; h < Math.min(h1, n); h++) { e += eAll[h]; sh = Math.max(sh, fHi[h]); kl = Math.max(kl, fLo[h]); }
    const db = 10 * Math.log10(e / Math.max(1, h1 - h0) + 1e-12);
    loud[f] = Math.max(0, Math.min(1, (db + 15) / 9));
    snare[f] = Math.min(1.5, sh); kick[f] = Math.min(1.5, kl);
  }
  // hits decay over ~4 frames so a hit is felt for more than one frame
  for (const env of [snare, kick]) for (let f = 1; f < frames; f++) env[f] = Math.max(env[f], env[f - 1] * 0.6);
  return { loud, snare, kick };
}

let ENV = null;
const get = () => (ENV ||= analyse());
const frameOf = v => Math.max(0, Math.min(get().loud.length - 1, Math.round(v * FPS)));
export const loud = v => get().loud[frameOf(v)];
export const snare = v => get().snare[frameOf(v)];
export const kickHit = v => get().kick[frameOf(v)];
