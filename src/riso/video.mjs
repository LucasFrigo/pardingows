// The director: picks the scene for each moment, drives boil + misregistration from the audio,
// applies the print jam and the torn-paper loop wipe, then composites the riso print.
import { Print, composite, W, H, clamp, lerp, hash, vnoise, between, easeIn, tornRect } from './engine.mjs';
import { CUT, FPS, DURATION, STOP1, STOP2, CA_CUT, JAM_END, beatNum, pulse, s16Num, inStop } from './timeline.mjs';
import { loud, snare, kickHit } from './audio.mjs';
import * as S from './scenes.mjs';
import { header, captions, povHook, title } from './captions.mjs';

const g = new Print();
const out = Buffer.alloc(W * H * 4);
const CUTS = Object.values(CUT).filter(t => t > 0 && t < DURATION);

function drawScene(v, vt) {
  if (v < CUT.commute) S.padaria(g, v, vt);
  else if (v < CUT.office) S.commute(g, v, vt);
  else if (v < CUT.meeting) S.office(g, v, vt);
  else if (v < CUT.panic1) S.meeting(g, v, vt);
  else if (v < CUT.calendar) S.panic(g, v, vt, STOP1);
  else if (v < CUT.lactose) S.calendarScene(g, v, vt);
  else if (v < CUT.shrug) S.lactoseScene(g, v, vt);
  else if (v < CUT.milkshake) S.shrugScene(g, v, vt);
  else if (v < CUT.vegetal) S.milkshakeScene(g, v, vt);
  else if (v < CUT.panic2) S.vegetalScene(g, v, vt);
  else if (v < CUT.cagar) S.panic(g, v, vt, STOP2);
  else if (v < CUT.door) S.sprint(g, v, vt);
  else S.doorScene(g, v, vt);
}

// Plate offsets per ink: base offset + slow drift + a jolt on every beat, harder on snares and cuts.
// Near-perfect registration during the stops, chaos on the print jam and on "cagar".
function registration(v, f, stop, cagar) {
  const reg = { P: [1.5, -1, 0], B: [-1, 1.3, 0], Y: [1.3, 1.6, 0] };
  const b = beatNum(v);
  let jolt = pulse(v, 13) * (1.6 + snare(v) * 1.6);
  for (const c of CUTS) if (v >= c && v < c + 0.15) jolt += 6 * (1 - (v - c) / 0.15);
  ['P', 'B', 'Y'].forEach((k, i) => {
    const r = reg[k];
    r[0] += (vnoise(v * 0.8, i * 7) - 0.5) * 2.6 + (hash(b, i, 1) - 0.5) * 2 * jolt;
    r[1] += (vnoise(v * 0.8, i * 7 + 3) - 0.5) * 2.6 + (hash(b, i, 2) - 0.5) * 2 * jolt;
    if (stop) { r[0] *= 0.15; r[1] *= 0.15; }
  });
  if (v >= CA_CUT && v < JAM_END) {
    const k = between(v, CA_CUT, JAM_END);
    reg.P[1] += 46 * k; reg.B[1] -= 28 * k; reg.B[0] -= 12 * k; reg.Y[0] += 14 * k; reg.P[2] = 0.03 * k;
  }
  if (cagar || (v >= CUT.door && v < CUT.door + 0.2)) {
    const n = s16Num(v);
    ['P', 'B', 'Y'].forEach((k, i) => {
      reg[k][0] += (hash(n, i, 5) - 0.5) * 26; reg[k][1] += (hash(n, i, 6) - 0.5) * 26;
      reg[k][2] = (hash(n, i, 7) - 0.5) * 0.05;
    });
  }
  return reg;
}

// The door page gets torn off to reveal tomorrow morning: back to frame 1.
function tearWipe(v, vt, subs) {
  S.doorScene(g, v, vt);
  title(g, v);
  if (subs) captions(g, v);
  const door = g.snapshot();
  g.clear();
  g.save(); S.padaria(g, v - DURATION, vt - DURATION); g.restore();
  povHook(g, v);
  const k = easeIn(between(v, CUT.tear, CUT.tear + 0.45));
  const base = lerp(-60, H + 80, k);
  const edge = x => base + (vnoise(x / 26, 3.7) - 0.5) * 70 + (hash(x >> 2, 9) - 0.5) * 6;
  const ys = new Float32Array(W);
  for (let x = 0; x < W; x++) ys[x] = edge(x);
  g.mergeSnapshot(door, (x, y) => y > ys[x]);
  // the torn fibre edge and its shadow on the page below
  const strip = [], shadow = [];
  for (let x = -10; x <= W + 10; x += 6) { strip.push([x, edge(Math.max(0, Math.min(W - 1, x))) - 3]); shadow.push([x, edge(Math.max(0, Math.min(W - 1, x))) - 12]); }
  for (let x = W + 10; x >= -10; x -= 6) { strip.push([x, edge(Math.max(0, Math.min(W - 1, x))) + 9 + hash(x, 4) * 6]); shadow.push([x, edge(Math.max(0, Math.min(W - 1, x)))]); }
  g.fill(shadow, { B: 0.4 }, { mode: 'ink', boil: 0.4, id: 3 });
  g.fill(strip, {}, { mode: 'knock', boil: 0.6, id: 4 });
}

// subs = false renders the same video without the burned-in lyrics (hook + title stay).
export function renderFrame(v, { subs = true } = {}) {
  const f = Math.round(v * FPS);
  const vt = Math.floor(f / 2) * 2 / FPS;
  const cagar = v >= CUT.cagar && v < CUT.door;
  const stop = inStop(v) && !cagar && !(v >= CA_CUT && v < JAM_END);
  const step = cagar ? 1 : stop ? 3 : 2;
  g.clear();
  g.boilSeed = Math.floor(f / step);
  g.boilAmp = cagar ? 4.5 : stop ? 0.45 : Math.min(2.8, 0.85 + loud(v) * 0.55 + snare(v) * 1.1);

  if (v >= CUT.tear) tearWipe(v, vt, subs);
  else {
    g.save();
    const kz = stop ? 0 : kickHit(v) * 0.006;
    g.translate(W / 2, H / 2); g.scale(1 + kz); g.translate(-W / 2, -H / 2);
    drawScene(v, vt);
    g.restore();
    header(g, v);
    if (subs) captions(g, v);
  }
  if (v >= CA_CUT && v < JAM_END) g.smear(0.25 + between(v, CA_CUT, JAM_END) * 1.6, f);
  return composite(g, registration(v, f, stop, cagar), Math.floor(f / step), out);
}
