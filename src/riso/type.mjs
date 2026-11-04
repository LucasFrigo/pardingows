// Cut-out collage typography. A monoline stroke font defined in code (cap height = 6 units,
// y down, baseline at 6), drawn as boiling marker strokes, pasted on torn paper scraps.
import { arc, hash, tornRect, clamp } from './engine.mjs';

const O = (cx, cy, rx, ry) => arc(cx, cy, rx, ry, 0, 360, 28);
const G = {
  A: [4, [[0, 6], [2, 0], [4, 6]], [[0.75, 3.9], [3.25, 3.9]]],
  B: [3.8, [[0, 6], [0, 0], [2.3, 0], ...arc(2.3, 1.45, 1.45, 1.45, -90, 90), [0, 2.9]], [[0, 2.9], [2.4, 2.9], ...arc(2.4, 4.45, 1.55, 1.55, -90, 90), [0, 6]]],
  C: [4.2, arc(2.3, 3, 2.3, 3, -42, -318, 22)],
  D: [4.2, [[0, 0], [0, 6], [1.6, 6], ...arc(1.6, 3, 2.6, 3, 90, -90, 16), [0, 0]]],
  E: [3.4, [[3.4, 0], [0, 0], [0, 6], [3.4, 6]], [[0, 3], [2.8, 3]]],
  F: [3.4, [[3.4, 0], [0, 0], [0, 6]], [[0, 3], [2.8, 3]]],
  G: [4.4, [...arc(2.3, 3, 2.3, 3, -42, -360, 22), [2.5, 3]]],
  H: [4, [[0, 0], [0, 6]], [[4, 0], [4, 6]], [[0, 3], [4, 3]]],
  I: [1.6, [[0, 0], [1.6, 0]], [[0.8, 0], [0.8, 6]], [[0, 6], [1.6, 6]]],
  J: [3.4, [[3.4, 0], [3.4, 4.3], ...arc(1.7, 4.3, 1.7, 1.7, 0, 180, 10)]],
  K: [3.9, [[0, 0], [0, 6]], [[3.8, 0], [0, 3.8]], [[1.3, 2.6], [3.9, 6]]],
  L: [3.2, [[0, 0], [0, 6], [3.2, 6]]],
  M: [5, [[0, 6], [0, 0], [2.5, 4.2], [5, 0], [5, 6]]],
  N: [4, [[0, 6], [0, 0], [4, 6], [4, 0]]],
  O: [4.6, O(2.3, 3, 2.3, 3)],
  P: [3.8, [[0, 6], [0, 0], [2.2, 0], ...arc(2.2, 1.6, 1.6, 1.6, -90, 90), [0, 3.2]]],
  Q: [4.6, O(2.3, 3, 2.3, 3), [[2.8, 4.4], [4.8, 6.4]]],
  R: [3.8, [[0, 6], [0, 0], [2.2, 0], ...arc(2.2, 1.6, 1.6, 1.6, -90, 90), [0, 3.2]], [[2.0, 3.2], [3.9, 6]]],
  S: [3.8, [...arc(1.9, 1.5, 1.9, 1.5, -15, -270, 12), ...arc(1.9, 4.5, 1.9, 1.5, -90, 165, 12)]],
  T: [4, [[0, 0], [4, 0]], [[2, 0], [2, 6]]],
  U: [4, [[0, 0], [0, 4], ...arc(2, 4, 2, 2, 180, 0, 10), [4, 0]]],
  V: [4.2, [[0, 0], [2.1, 6], [4.2, 0]]],
  W: [5.6, [[0, 0], [1.4, 6], [2.8, 1.6], [4.2, 6], [5.6, 0]]],
  X: [4, [[0, 0], [4, 6]], [[4, 0], [0, 6]]],
  Y: [4, [[0, 0], [2, 3.2], [4, 0]], [[2, 3.2], [2, 6]]],
  Z: [4, [[0, 0], [4, 0], [0, 6], [4, 6]]],
  0: [3.6, O(1.8, 3, 1.8, 3)],
  1: [3, [[0.2, 1.2], [1.6, 0], [1.6, 6]], [[0.2, 6], [3, 6]]],
  2: [3.6, [...arc(1.8, 1.8, 1.8, 1.8, -170, 10, 12), [0, 6], [3.6, 6]]],
  3: [3.6, [...arc(1.8, 1.5, 1.7, 1.5, -160, 90, 12), ...arc(1.8, 4.5, 1.8, 1.5, -90, 160, 12)]],
  4: [3.8, [[2.8, 6], [2.8, 0], [0, 4.2], [3.8, 4.2]]],
  5: [3.6, [[3.4, 0], [0.4, 0], [0.2, 2.6], ...arc(1.7, 4.1, 1.8, 1.9, -125, 150, 12)]],
  6: [3.6, O(1.8, 4.2, 1.8, 1.8), [[0.02, 4.0], [0.4, 2.0], [1.4, 0.5], [2.9, 0]]],
  7: [3.6, [[0, 0], [3.6, 0], [1.2, 6]]],
  8: [3.6, O(1.8, 1.45, 1.5, 1.45), O(1.8, 4.4, 1.8, 1.6)],
  9: [3.6, O(1.8, 1.8, 1.8, 1.8), [[3.58, 2.0], [3.2, 4.0], [2.2, 5.5], [0.7, 6]]],
  '.': [0.8, [[0.4, 5.7], [0.4, 5.7]]],
  ',': [0.9, [[0.5, 5.5], [0.1, 6.9]]],
  '!': [0.8, [[0.4, 0], [0.4, 4]], [[0.4, 5.7], [0.4, 5.7]]],
  '?': [3.4, [...arc(1.7, 1.6, 1.7, 1.6, -170, 60, 12), [1.7, 3.6], [1.7, 4.1]], [[1.7, 5.7], [1.7, 5.7]]],
  '-': [2.4, [[0, 3.4], [2.4, 3.4]]],
  ':': [0.8, [[0.4, 2.2], [0.4, 2.2]], [[0.4, 5.7], [0.4, 5.7]]],
  '#': [4, [[1.3, 0.4], [0.9, 5.6]], [[3.1, 0.4], [2.7, 5.6]], [[0.1, 2], [4, 2]], [[0, 4], [3.9, 4]]],
  '(': [1.6, arc(3.2, 3, 3, 3.8, -128, -232, 12)],
  ')': [1.6, arc(-1.6, 3, 3, 3.8, -52, 52, 12)],
  '/': [3, [[3, 0], [0, 6]]],
  "'": [0.8, [[0.4, 0], [0.3, 1.5]]],
};
const ACC = {
  acute: w => [[[w / 2 - 0.4, -0.7], [w / 2 + 0.7, -1.9]]],
  grave: w => [[[w / 2 - 0.7, -1.9], [w / 2 + 0.4, -0.7]]],
  circ: w => [[[w / 2 - 1, -0.7], [w / 2, -1.8], [w / 2 + 1, -0.7]]],
  tilde: w => [Array.from({ length: 9 }, (_, i) => [w / 2 - 1.2 + 2.4 * i / 8, -1.25 - 0.5 * Math.sin(Math.PI * 2 * i / 8)])],
  ced: w => [[[w / 2, 6], [w / 2 + 0.3, 6.7], [w / 2 - 0.5, 7.4]]],
};
const ACCENTED = {
  'Á': 'A acute', 'À': 'A grave', 'Â': 'A circ', 'Ã': 'A tilde', 'É': 'E acute', 'Ê': 'E circ', 'Í': 'I acute',
  'Ó': 'O acute', 'Ô': 'O circ', 'Õ': 'O tilde', 'Ú': 'U acute', 'Ç': 'C ced',
};

export function glyph(ch) {
  ch = ch.toUpperCase();
  if (ACCENTED[ch]) {
    const [base, acc] = ACCENTED[ch].split(' ');
    const [w, ...strokes] = G[base];
    return { w, strokes: [...strokes, ...ACC[acc](w)] };
  }
  const g = G[ch];
  return g ? { w: g[0], strokes: g.slice(1) } : null;
}

const GAP = 1.25, SPACE = 2.4;
// Width in px of a string at cap height `size`.
export function measure(str, size, track = 1) {
  let w = 0;
  for (const ch of str) {
    if (ch === ' ') { w += SPACE; continue; }
    const gl = glyph(ch);
    w += (gl ? gl.w : 2) + GAP * track;
  }
  return Math.max(0, w - GAP * track) * size / 6;
}

// Draw a string with its cap-top-left at (x, y). Letters jitter like hand-cut type.
// opts: paint, weight (units), seed, jitter (0..1), boil, mode, track
export function drawText(g, str, x, y, size, {
  paint = { P: 1, B: 1 }, weight = 1.05, seed = 1, jitter = 0.5, boil = 0.45, mode = 'ink', track = 1, letter = null,
} = {}) {
  const u = size / 6;
  let cx = x, i = 0;
  for (const ch of str) {
    if (ch === ' ') { cx += SPACE * u; i++; continue; }
    const gl = glyph(ch);
    if (!gl) { cx += 2 * u; i++; continue; }
    const r = k => hash(seed, i, k) - 0.5;
    const rot = r(1) * 0.14 * jitter, sc = 1 + r(2) * 0.16 * jitter, dy = r(3) * 0.12 * jitter * size;
    const lw = gl.w * u;
    g.save();
    g.translate(cx + lw / 2, y + size / 2 + dy);
    if (letter) letter(g, i, ch, lw, size);
    g.rotate(rot);
    g.scale(u * sc);
    g.translate(-gl.w / 2, -3);
    for (const s of gl.strokes) g.stroke(s, weight, paint, { mode, boil, id: seed * 31 + i });
    g.restore();
    cx += (gl.w + GAP * track) * u;
    i++;
  }
  return cx;
}

// A torn paper scrap. paint {} = bare paper (knockout). Optional halftone drop shadow.
export function scrap(g, x, y, w, h, seed, paint = {}, { shadow = true, jag = 2.2, boil = 0.6 } = {}) {
  const pts = tornRect(x, y, w, h, seed, jag);
  if (shadow) {
    g.save(); g.translate(4, 5);
    g.fill(pts, { B: 0.45 }, { mode: 'ink', boil, id: seed + 3 });
    g.restore();
  }
  g.fill(pts, paint, { mode: Object.keys(paint).length ? 'over' : 'knock', boil, id: seed });
}

// Masking tape strip across a corner.
export function tape(g, x, y, ang, len = 34, seed = 1) {
  g.save(); g.translate(x, y); g.rotate(ang);
  g.fill(tornRect(-len / 2, -7, len, 14, seed, 1.6, 5), { Y: 0.45 }, { mode: 'over', id: seed });
  g.restore();
}

// Rubber stamp: bordered word in one ink with voids where the stamp missed.
export function stamp(g, str, cx, cy, size, { paint = { P: 1, Y: 1 }, rot = -0.12, seed = 3, border = true, weight = 1.35 } = {}) {
  const w = measure(str, size, 1.2), h = size;
  g.save(); g.translate(cx, cy); g.rotate(rot);
  if (border) {
    const pad = size * 0.45;
    const box = [[-w / 2 - pad, -h / 2 - pad], [w / 2 + pad, -h / 2 - pad], [w / 2 + pad, h / 2 + pad], [-w / 2 - pad, h / 2 + pad]];
    g.stroke(box, size * 0.12, paint, { closed: true, id: seed + 1, boil: 0.8 });
    const p2 = pad * 0.55;
    g.stroke([[-w / 2 - p2, -h / 2 - p2], [w / 2 + p2, -h / 2 - p2], [w / 2 + p2, h / 2 + p2], [-w / 2 - p2, h / 2 + p2]], size * 0.05, paint, { closed: true, id: seed + 2, boil: 0.8 });
  }
  drawText(g, str, -w / 2, -h / 2, size, { paint, weight, seed, jitter: 0.25, boil: 0.6, track: 1.2 });
  // voids: bare spots where the rubber didn't take ink
  const sub = {};
  for (const k in paint) sub[k] = 0.9;
  for (let i = 0; i < 26; i++) {
    const vx = (hash(seed, i, 1) - 0.5) * (w + size), vy = (hash(seed, i, 2) - 0.5) * size * 1.6;
    const vr = 1 + hash(seed, i, 3) * size * 0.07;
    g.fill(arc(vx, vy, vr * 1.6, vr, 0, 360, 8).slice(0, -1), sub, { mode: 'sub', id: seed + i, boil: 0.3 });
  }
  g.restore();
}

// Lay out words into centred rows no wider than maxW. Each word: { text, size, pad }.
// Returns rows of { word, x, w } with x relative to the row centre, plus row heights.
export function layout(words, maxW, gap = 10) {
  const rows = [];
  let row = [], rw = 0;
  for (const w of words) {
    const ww = measure(w.text, w.size) + w.pad * 2;
    if (row.length && rw + gap + ww > maxW) { rows.push({ items: row, w: rw }); row = []; rw = 0; }
    row.push({ word: w, w: ww });
    rw += (row.length > 1 ? gap : 0) + ww;
  }
  if (row.length) rows.push({ items: row, w: rw });
  for (const r of rows) {
    let x = -r.w / 2;
    for (const it of r.items) { it.x = x; x += it.w + gap; }
    r.h = Math.max(...r.items.map(it => it.word.size)) * 1.75;
  }
  return rows;
}

export { clamp };
