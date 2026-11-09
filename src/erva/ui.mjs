// Bouncing-ball sing-along captions, after the 1930s song cartoons: the whole couplet is on screen from its cut, the words
// light up as they're sung, and a white ball hops along the text and lands on every syllable at its onset.
// Everything is a pure function of video time, so a sync fix needs no Blender re-render.
//
// timeline.json cards: { moment, speaker, rows: [[ [text, t, [syllable onsets]] ...], ...], adlib?: row }
// A word's text marks syllable breaks with '-' ("his-tó-ria"); the marks are not drawn.
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { GlobalFonts } from '@napi-rs/canvas';

const HERE = path.dirname(fileURLToPath(import.meta.url));
export const TL = JSON.parse(fs.readFileSync(path.join(HERE, 'timeline.json'), 'utf8'));
export const W = 1080, H = 1920;
export const FPS = TL.fps;

GlobalFonts.registerFromPath(path.join(HERE, 'fonts', 'AlfaSlabOne-Regular.ttf'), 'Alfa');
GlobalFonts.registerFromPath(path.join(HERE, 'fonts', 'Limelight-Regular.ttf'), 'Limelight');
GlobalFonts.registerFromPath(path.join(HERE, 'fonts', 'AbrilFatface-Regular.ttf'), 'Abril');
export const FONT = 'Alfa';

// Clear of TikTok's right-hand icons (x > 918) and its bottom caption area (y > 1536)
const BAND = { x: 40, w: 870, top: 1230, bottom: 1500 };
const MAX_PX = 72, MIN_PX = 40;
const BALL_R = 20;
const ROW = 2.0;

// Index of the video frame a song time lands on: 0 is the first frame. A word lights on the frame nearest its time.
export const frameOf = t => Math.round((t - TL.start) * FPS);
const timeOf = n => TL.start + n / FPS;

export const activeCard = n => {
  let i = 0;
  TL.cards.forEach((c, k) => { if (frameOf(c.t) <= n) i = k; });
  return i;
};

const plain = s => s.replace(/-/g, '');

// Fixed layout per card: font size, rows centred, and the x of every syllable's centre (where the ball lands)
const LAYOUT = new Map();
function layout(ctx, ci) {
  if (LAYOUT.has(ci)) return LAYOUT.get(ci);
  const card = TL.cards[ci];
  const rows = card.rows.map(r => r.map(([text, t, syl]) => ({ text, t, syl: syl || [t] })));
  if (card.adlib) rows.push(card.adlib.map(([text, t, syl]) => ({ text, t, syl: syl || [t], adlib: true })));
  const measure = px => rows.map(row => {
    const size = row[0]?.adlib ? Math.round(px * 0.78) : px;
    ctx.font = `${size}px ${FONT}`;
    const space = ctx.measureText(' ').width * 1.1;
    let x = 0;
    const cells = row.map((w, i) => {
      const txt = plain(w.text);
      const width = ctx.measureText(txt).width;
      const x0 = x + (i ? space : 0);
      // syllable centres from the widths of the text before and including each syllable
      const parts = w.text.split('-');
      let acc = '';
      const sylX = parts.map(p => {
        const a = ctx.measureText(acc).width;
        acc += p;
        const b = ctx.measureText(acc).width;
        return x0 + (a + b) / 2;
      });
      x = x0 + width;
      return { ...w, txt, x: x0, w: width, sylX, px: size };
    });
    return { cells, width: x, px: size };
  });
  let px = MAX_PX;
  while (px > MIN_PX && Math.max(...measure(px).map(r => r.width)) > BAND.w - 20) px -= 2;
  const placed = measure(px);
  // rows far enough apart that the ball fits between a row and the one above it
  const gap = px * ROW;
  const total = (placed.length - 1) * gap;
  const base = (BAND.top + BAND.bottom) / 2 + px * 0.35 - total / 2;
  const cells = [];
  let y = base;
  placed.forEach((row, r) => {
    if (r) y += gap;
    const left = BAND.x + (BAND.w - row.width) / 2;
    for (const c of row.cells) cells.push({ ...c, row: r, cx: left + c.x + c.w / 2, left: left + c.x, y, sylX: c.sylX.map(s => left + s) });
  });
  // The ball's landing points, in time order
  const hops = [];
  for (const c of cells) c.syl.forEach((t, k) => hops.push({ t, x: c.sylX[Math.min(k, c.sylX.length - 1)], y: c.y - c.px * 0.82 }));
  hops.sort((a, b) => a.t - b.t);
  const out = { cells, hops, px, gap };
  LAYOUT.set(ci, out);
  return out;
}

// Ball position at song time t: parabolic hops between landing points, squashed for a moment on each landing
function ball(hops, t, tIn, tOut) {
  if (!hops.length) return null;
  const first = hops[0], last = hops[hops.length - 1];
  const arc = (a, b, s) => {
    const dx = Math.abs(b.x - a.x), dt = Math.max(0.05, b.t - a.t);
    const h = Math.min(150, Math.max(26, 30 + dx * 0.35)) * Math.min(1, dt / 0.22);
    return { x: a.x + (b.x - a.x) * s, y: a.y + (b.y - a.y) * s - h * 4 * s * (1 - s), sq: 0 };
  };
  if (t < first.t) {
    // hops in from the left edge in the half second before the first syllable
    const start = { t: Math.max(tIn, first.t - 0.5), x: BAND.x - 40, y: first.y - 40 };
    if (t < start.t) return null;
    return arc(start, first, (t - start.t) / (first.t - start.t));
  }
  for (let i = 0; i + 1 < hops.length; i++) {
    const a = hops[i], b = hops[i + 1];
    if (t >= a.t && t < b.t) {
      const p = arc(a, b, (t - a.t) / (b.t - a.t));
      p.sq = Math.max(0, 1 - (t - a.t) / 0.07);
      return p;
    }
  }
  // after the last syllable: small rest bounces on the beat until the card ends
  const beat = 60 / TL.bpm;
  const k = ((t - last.t) % beat) / beat;
  return { x: last.x, y: last.y - 18 * 4 * k * (1 - k), sq: Math.max(0, 1 - (t - last.t) / 0.07) };
}

const INK = '#0b0906', PAPER = '#fbf5e6', DIM = '#8d8472';

function speakerBadge(ctx, name, x, y, px) {
  ctx.save();
  ctx.font = `${Math.round(px * 0.5)}px Limelight`;
  const tw = ctx.measureText(name).width;
  const w = tw + 44, h = px * 0.78;
  ctx.fillStyle = INK;
  ctx.beginPath();
  ctx.roundRect(x - w / 2, y - h / 2, w, h, h / 2);
  ctx.fill();
  ctx.strokeStyle = PAPER;
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.roundRect(x - w / 2 + 5, y - h / 2 + 5, w - 10, h - 10, (h - 10) / 2);
  ctx.stroke();
  ctx.fillStyle = PAPER;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(name, x, y + 2);
  ctx.restore();
}

export function drawUI(ctx, v) {
  const n = Math.round(v * FPS);
  const t = timeOf(n);
  const ci = activeCard(n);
  const card = TL.cards[ci];
  if (!card.rows.length) return;
  const L = layout(ctx, ci);
  const age = n - frameOf(card.t);
  // the card fades in over 3 frames, like a lap dissolve on film
  const alpha = Math.min(1, (age + 1) / 3);
  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.textAlign = 'left';
  ctx.textBaseline = 'alphabetic';
  ctx.lineJoin = 'round';
  if (card.speaker) {
    ctx.font = `${Math.round(L.px * 0.5)}px Limelight`;
    const bw = ctx.measureText(card.speaker).width + 44;
    speakerBadge(ctx, card.speaker, Math.max(BAND.x + bw / 2, L.cells[0].left + bw / 2 - 10), L.cells[0].y - L.px * 1.75, L.px);
  }
  for (const c of L.cells) {
    ctx.font = `${c.px}px ${FONT}`;
    ctx.lineWidth = Math.max(6, c.px * 0.14);
    ctx.strokeStyle = INK;
    ctx.strokeText(c.txt, c.left, c.y);
    // sung part of the word in white, the rest dim; a syllable lights at its onset
    const lit = c.syl.filter(s => frameOf(s) <= n).length;
    const parts = c.text.split('-');
    const litTxt = parts.slice(0, lit).join('');
    ctx.fillStyle = DIM;
    ctx.fillText(c.txt, c.left, c.y);
    if (lit) {
      ctx.fillStyle = PAPER;
      ctx.fillText(litTxt, c.left, c.y);
    }
  }
  const next = TL.cards[ci + 1];
  const tOut = next ? next.t : TL.start + TL.frames / FPS;
  const b = ball(L.hops, t, card.t, tOut);
  if (b) {
    const sx = 1 + 0.28 * b.sq, sy = 1 - 0.3 * b.sq;
    ctx.save();
    ctx.translate(b.x, b.y + BALL_R * (1 - sy));
    ctx.scale(sx, sy);
    ctx.fillStyle = PAPER;
    ctx.strokeStyle = INK;
    ctx.lineWidth = 5;
    ctx.beginPath();
    ctx.arc(0, -BALL_R, BALL_R, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = 'rgba(255,255,255,.9)';
    ctx.beginPath();
    ctx.arc(-BALL_R * 0.35, -BALL_R * 1.38, BALL_R * 0.28, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }
  ctx.restore();
}

// Word boxes per card, for the check on the finished MP4 (sync/check.py). t is the word's first syllable; each syllable
// gets its x range, and y0..y1 is the lower half of the letters, which the ball never touches.
export function wordBoxes(ctx) {
  return TL.cards.map((card, ci) => card.rows.length ? layout(ctx, ci).cells.map(c => {
    ctx.font = `${c.px}px ${FONT}`;
    const parts = c.text.split('-');
    let acc = '';
    const sx = parts.map(p => {
      const a = ctx.measureText(acc).width;
      acc += p;
      return [Math.round(c.left + a), Math.round(c.left + ctx.measureText(acc).width)];
    });
    return {
      card: ci + 1, card_t: card.t, word: c.txt, t: c.syl[0], syl: c.syl, sx,
      x: Math.round(c.left), y: Math.round(c.y - c.px * 0.8), w: Math.round(c.w), h: Math.round(c.px),
      y0: Math.round(c.y - c.px * 0.45), y1: Math.round(c.y - c.px * 0.05),
    };
  }) : []).flat();
}
