// Finds tempo and first-beat phase of the 0:39-1:04 window, then prints whole-bar windows near it.
//   node src/thps/beatgrid.mjs
import { spawnSync } from 'child_process';
import fs from 'fs';
import ffmpeg from 'ffmpeg-static';

const AUDIO = 'audio/' + fs.readdirSync('audio').find(n => n.startsWith('A SOLU') && n.endsWith('.wav'));
const SR = 22050, HOP = 128, T0 = 39, T1 = 64;
const r = spawnSync(ffmpeg, ['-v', 'error', '-ss', String(T0), '-t', String(T1 - T0), '-i', AUDIO,
  '-ac', '1', '-ar', String(SR), '-f', 'f32le', 'pipe:1'], { maxBuffer: 1 << 28 });
const b = r.stdout, x = new Float32Array(b.buffer, b.byteOffset, b.length / 4);

// log-energy flux, one value per hop
const n = Math.floor(x.length / HOP), flux = new Float64Array(n);
let prev = 0;
for (let i = 0; i < n; i++) {
  let e = 1e-9;
  for (let j = 0; j < HOP; j++) e += x[i * HOP + j] ** 2;
  const l = Math.log(e);
  flux[i] = Math.max(0, l - prev);
  prev = l;
}
const hopS = HOP / SR;

// Score every BPM + phase by summing flux on the implied 8th-note grid. Sampling on a fine comb
// avoids the low-tempo bias of plain autocorrelation.
const results = [];
for (let bpm = 80; bpm <= 200; bpm += 0.1) {
  const beat = 60 / bpm;
  let best = 0, bestPh = 0;
  for (let ph = 0; ph < beat; ph += 0.005) {
    let s = 0, c = 0;
    for (let t = ph; t < T1 - T0; t += beat) {
      s += flux[Math.round(t / hopS)] || 0;
      c++;
    }
    s /= c;
    if (s > best) { best = s; bestPh = ph; }
  }
  results.push({ bpm: +bpm.toFixed(1), score: best, phase: bestPh });
}
results.sort((a, c) => c.score - a.score);
const mean = flux.reduce((a, c) => a + c, 0) / n;
console.log('mean flux', mean.toFixed(3));
console.log('top', results.slice(0, 12).map(r => `${r.bpm}@${r.phase.toFixed(3)}:${r.score.toFixed(2)}`).join('  '));
const top = results[0];
const beat = 60 / top.bpm, bar = beat * 4;
console.log(`best ${top.bpm} BPM, a beat at ${(T0 + top.phase).toFixed(3)} s; bar = ${bar.toFixed(3)} s`);
console.log('bars in 25 s:', (25 / bar).toFixed(2));
