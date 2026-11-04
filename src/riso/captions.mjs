// Screen-space typography: the POV hook -> VIDA DE PARDO title, and the burned-in PT-BR
// lyrics, slapped on word by word as cut-out scraps. Everything stays inside TikTok's safe
// area: x 24..459 (right 15% is buttons), y 96..768 (top 10%, bottom 20%).
import { clamp, lerp, easeOut, easeIn, backOut, between, hash } from './engine.mjs';
import { drawText, measure, scrap, tape, stamp, layout } from './type.mjs';
import { scissors, INK } from './props.mjs';
import { LINES, CUT, CA_CUT, SIGNOFF, DURATION, S16, at } from './timeline.mjs';

export const SAFE = { x0: 24, x1: 459, y0: 96, y1: 768 };
export const CX = (SAFE.x0 + SAFE.x1) / 2;
const MAXW = SAFE.x1 - SAFE.x0 - 6;
const SLAP = 0.13;

const SIZE = { n: 34, key: 50, stamp: 44, cut: 62, shake: 44, cagar: 92 };
const PAD = { n: 9, key: 12, stamp: 18, cut: 12, shake: 6, cagar: 0 };

// ---------------------------------------------------------------- one word
// (x, y) = centre of the word's scrap. t = time since the word was sung.
function slapIn(g, t, seed, k = 1) {
  const s = t < SLAP ? 1 + 0.55 * k * (1 - backOut(t / SLAP, 3)) : 1;
  const r = (hash(seed, 1) - 0.5) * 0.07 + (t < SLAP ? (1 - t / SLAP) * 0.22 * (hash(seed, 2) > 0.5 ? 1 : -1) * k : 0);
  g.rotate(r); g.scale(s);
}

function plainWord(g, text, size, pad, seed, paint, ink, knock = false) {
  const tw = measure(text, size), pw = tw + pad * 2, ph = size + pad * 1.7;
  scrap(g, -pw / 2, -ph / 2, pw, ph, seed, paint);
  drawText(g, text, -tw / 2, -size / 2, size, { paint: knock ? {} : ink, mode: knock ? 'knock' : 'ink', weight: 1.45, seed, jitter: 0.6 });
  return [pw, ph];
}

// Per-letter ransom scraps (MILKSHAKE / VIDA DE PARDO). shown(i) -> time since letter i landed (or <0).
const RANSOM = [[{ Y: 1 }, INK.dark], [{ P: 1 }, null], [{}, INK.dark], [{ B: 1 }, null], [{ Y: 0.4 }, INK.dark]];
function ransom(g, text, size, seed, shown, { gap = 3, boil = 0.5 } = {}) {
  const letters = [...text];
  const ws = letters.map(ch => (ch === ' ' ? size * 0.35 : measure(ch, size) + size * 0.34));
  const total = ws.reduce((a, b) => a + b, 0) + gap * (letters.length - 1);
  let x = -total / 2;
  letters.forEach((ch, i) => {
    const t = shown(i), w = ws[i];
    if (ch !== ' ' && t >= 0) {
      const [paint, ink] = RANSOM[(i + seed) % RANSOM.length];
      const h = size * (1.32 + hash(seed, i, 3) * 0.2);
      g.save(); g.translate(x + w / 2, (hash(seed, i, 4) - 0.5) * size * 0.14);
      slapIn(g, t, seed * 13 + i, 0.8);
      scrap(g, -w / 2, -h / 2, w, h, seed * 7 + i, paint, { jag: 1.6, boil });
      const lw = measure(ch, size);
      drawText(g, ch, -lw / 2, -size / 2, size, { paint: ink || {}, mode: ink ? 'ink' : 'knock', weight: 1.5, seed: seed + i, jitter: 0.9 });
      g.restore();
    }
    x += w + gap;
  });
  return total;
}

// ---------------------------------------------------------------- header: POV hook -> title
const POV = ['POV:', 'VOCÊ', 'É', 'INTOLERANTE', 'À', 'LACTOSE', 'E', 'NÃO', 'APRENDE', 'NUNCA'];
const POV_ROWS = layout(POV.map(t => ({ text: t, size: 25, pad: 7 })), MAXW, 8);
const POV_IN = at('56.2.3');   // loop-in: the hook re-lands before the seam

export function povHook(g, v) {
  // frame 1 shows the full hook; it dissolves to halftone, then re-lands at the end for the loop
  let alpha = 1 - between(v, 2.45, 2.85);
  const loopIn = v > DURATION - 0.6;
  if (!loopIn && alpha <= 0) return;
  if (loopIn) alpha = 1;
  g.save(); g.alpha = alpha;
  let y = SAFE.y0 + 12, i = 0;
  for (const row of POV_ROWS) {
    for (const it of row.items) {
      const t = loopIn ? v - (POV_IN + i * 0.034) : 1;
      if (t >= 0) {
        g.save(); g.translate(CX + it.x + it.w / 2, y + row.h / 2);
        slapIn(g, t, 40 + i, 0.7);
        const txt = it.word.text;
        if (txt === 'POV:') plainWord(g, txt, 25, 7, 40 + i, { P: 1 }, null, true);
        else if (txt === 'LACTOSE') plainWord(g, txt, 25, 7, 40 + i, { B: 1 }, null, true);
        else plainWord(g, txt, 25, 7, 40 + i, i % 4 === 2 ? { Y: 0.4 } : {}, INK.dark);
        g.restore();
      }
      i++;
    }
    y += row.h * 0.92;
  }
  if (!loopIn) tape(g, CX - 190, SAFE.y0 + 18, -0.6, 38, 4);
  g.restore();
}

const TITLE_IN = at('41.4.3');
export function title(g, v) {
  if (v < TITLE_IN) return;
  const t = v - TITLE_IN;
  g.save(); g.translate(CX, SAFE.y0 + 34);
  slapIn(g, t, 77, 1.2);
  ransom(g, 'VIDA DE PARDO', 31, 3, i => t - i * 0.012);
  g.restore();
  // the band credit, one smaller line underneath
  const tc = t - 0.09;
  if (tc < 0) return;
  g.save(); g.translate(CX, SAFE.y0 + 78);
  slapIn(g, tc, 78, 0.8);
  plainWord(g, 'PARDINGOWS', 15, 6, 78, {}, INK.dark);
  g.restore();
}

export function header(g, v) {
  povHook(g, v);
  title(g, v);
}

// ---------------------------------------------------------------- lyrics
const LAYOUTS = LINES.map(line => {
  const words = line.words.filter(w => w.style !== 'cagar').map(w => ({
    ...w, size: line.mode === 'stop' && w.style === 'n' ? 44 : SIZE[w.style], pad: PAD[w.style],
  }));
  const rows = line.mode === 'stop'
    ? [...layout(words.slice(0, 1), MAXW), ...layout(words.slice(1), MAXW)]
    : layout(words, MAXW);
  const total = rows.reduce((a, r) => a + r.h, 0);
  return { line, rows, total };
});

// Where the "CA-!" scrap sits (so the scissors know where to cut).
const CUT_LINE = LAYOUTS.find(l => l.line.words.some(w => w.style === 'cut'));
const STOP_Y = 628;
function blockTop(L) { return L.line.mode === 'stop' ? STOP_Y - L.total / 2 : SAFE.y1 - 22 - L.total; }

function drawWord(g, w, t, seed) {
  slapIn(g, t, seed, w.style === 'n' ? 1 : 1.4);
  if (w.style === 'n') plainWord(g, w.text, w.size, w.pad, seed, seed % 5 === 3 ? { Y: 0.35 } : {}, INK.dark);
  else if (w.style === 'key') {
    const [pw, ph] = plainWord(g, w.text, w.size, w.pad, seed, w.text === 'LACTOSE' ? { P: 1 } : { B: 1 }, null, true);
    tape(g, pw / 2 - 6, -ph / 2 + 2, 0.7, 30, seed);
  } else if (w.style === 'stamp') {
    const tw = measure(w.text, w.size);
    scrap(g, -tw / 2 - 20, -w.size / 2 - 16, tw + 40, w.size + 32, seed, { Y: 1 });
    stamp(g, w.text, 0, 0, w.size, { paint: INK.dark, rot: -0.05, seed, weight: 1.6 });
  } else if (w.style === 'shake') {
    ransom(g, w.text, w.size, 5, i => t - [0, 0, 0, 0.27, 0.45, 0.45, 0.45, 0.64, 0.64][i]);
  }
}

// The "CA-!" gag: one scrap that the scissors snip at CA_CUT; the "-!" half falls away.
function cutWord(g, w, t, v, seed) {
  const size = w.size, a = measure('CA', size), b = measure('-!', size), pad = w.pad;
  const ph = size + pad * 1.7, wa = a + pad * 1.5, wb = b + pad * 1.5;
  slapIn(g, t, seed, 1.5);
  g.save(); g.translate(-wb / 2, 0);
  scrap(g, -wa / 2, -ph / 2, wa, ph, seed, { P: 1 });
  drawText(g, 'CA', -a / 2, -size / 2, size, { paint: {}, mode: 'knock', weight: 1.6, seed });
  g.restore();
  const fall = Math.max(0, v - CA_CUT);
  g.save(); g.translate(wa / 2 + fall * 120, fall * fall * 2600); g.rotate(fall * 9);
  scrap(g, -wb / 2, -ph / 2, wb, ph, seed + 1, { P: 1 });
  drawText(g, '-!', -b / 2, -size / 2, size, { paint: {}, mode: 'knock', weight: 1.6, seed: seed + 1 });
  g.restore();
  return wa / 2 - wb / 2;   // x of the cut, relative to the word centre
}

// Scissors hover over the stop lines and snip (stop 1) or get blasted away (stop 2).
function scissorGag(g, v, x, y, line) {
  const first = line === CUT_LINE.line;
  const enter = first ? at(67.9) : at(79.65);   // they show up in the silent pause
  if (v < enter) return;
  const hit = first ? CA_CUT : CUT.cagar;
  const k = easeOut(between(v, enter, enter + 0.25));
  let sx = lerp(x + 360, x + 92, k), sy = y - 70, rot = -0.25, open = 0.55 + Math.sin(v * 9) * 0.18;
  if (first && v >= hit - 0.05) {
    const c = between(v, hit - 0.05, hit);
    open = lerp(open, 0.02, c); sx = lerp(sx, x + 84, c); sy = lerp(sy, y - 6, c); rot = lerp(rot, -0.05, c);
  }
  if (!first && v >= hit) {
    const f = v - hit;
    sx += f * 1300; sy -= f * 900 - f * f * 1800; rot += f * 18;
  }
  g.save(); g.translate(sx, sy); g.rotate(rot); g.scale(1.05);
  scissors(g, open, 560);
  g.restore();
}

// CAGAR!!!: full-screen letters that sag as the vocal pitch falls.
const CAGAR_T = CUT.cagar;
function cagar(g, v) {
  const t = v - CAGAR_T;
  if (t < 0) return;
  const letters = [...'CAGAR!!!'];
  const size = 92, rows = [letters.slice(0, 5), letters.slice(5)];
  rows.forEach((row, r) => {
    const ws = row.map(ch => measure(ch, size) + 26);
    const total = ws.reduce((a, b) => a + b, 0);
    let x = CX - total / 2;
    row.forEach((ch, i) => {
      const li = r * 5 + i, lt = t - li * 0.018;
      if (lt < 0) { x += ws[i]; return; }
      const sag = easeIn(between(v, CAGAR_T + 0.12 + li * 0.04, CAGAR_T + 0.55)) * (34 + li * 6);
      const wob = Math.sin(v * 31 + li * 1.7) * 0.09;
      const h = size * 1.3;
      g.save(); g.translate(x + ws[i] / 2, 470 + r * 150 + sag);
      g.rotate(wob + (hash(li, 9) - 0.5) * 0.3); g.scale(1 + 0.8 * (1 - backOut(clamp(lt / 0.1), 3)));
      scrap(g, -ws[i] / 2, -h / 2, ws[i], h, 900 + li, li % 2 ? { Y: 1 } : {}, { boil: 1.4 });
      const lw = measure(ch, size);
      drawText(g, ch, -lw / 2, -size / 2, size, { paint: INK.red, weight: 1.9, seed: li, jitter: 1, boil: 1.2 });
      drawText(g, ch, -lw / 2, -size / 2, size, { paint: INK.dark, weight: 0.5, seed: li, jitter: 1, boil: 1.2 });
      g.restore();
      x += ws[i];
    });
  });
}

// "(PARDJHONSON)": the sign-off, rubber-stamped on the bathroom door above the CAGAR!!! letters.
function pardjhonson(g, v) {
  const t = v - SIGNOFF;
  if (t < 0) return;
  g.save(); g.translate(CX, 330);
  const s = 1 + 1.2 * (1 - easeOut(clamp(t / 0.08)));
  g.scale(s); g.rotate(-0.14);
  scrap(g, -205, -36, 410, 72, 23, {});
  stamp(g, '(PARDJHONSON)', 0, 0, 30, { paint: INK.red, rot: 0, seed: 21, weight: 1.6 });
  g.restore();
}

export function captions(g, v) {
  for (const L of LAYOUTS) {
    const { line, rows } = L;
    if (v < line.v || v >= line.end) continue;
    const top = blockTop(L);
    const cagarOn = line.mode === 'stop' && v >= CAGAR_T && line.words.some(w => w.style === 'cagar');
    let y = top, wi = 0, cutX = null, cutY = null;
    for (const row of rows) {
      for (const it of row.items) {
        const w = it.word, t = v - w.v, seed = Math.round(w.v * 100);
        // the payoff blasts the rest of the line off the page within half a second
        if (t >= 0 && !(cagarOn && v - CAGAR_T > 0.5)) {
          g.save();
          let x = CX + it.x + it.w / 2, yy = y + row.h / 2;
          if (cagarOn) {
            const f = v - CAGAR_T;
            x += (x - CX + (wi % 2 ? 90 : -90)) * f * 12; yy -= 1500 * f * (0.6 + wi * 0.2);
          }
          g.translate(x, yy);
          if (cagarOn) g.rotate((wi % 2 ? 1 : -1) * (v - CAGAR_T) * 6);
          if (w.style === 'cut') { cutX = x + cutWord(g, w, t, v, seed); cutY = yy; }
          else drawWord(g, w, t, seed);
          g.restore();
        }
        wi++;
      }
      y += row.h;
    }
    if (line.mode === 'stop') {
      const r2 = rows[rows.length - 1];
      const ref = cutX ?? CX + r2.w / 2;
      scissorGag(g, v, ref, cutY ?? top + rows[0].h + r2.h / 2, line);
    }
  }
  cagar(g, v);
  pardjhonson(g, v);
}

export { MAXW };
