// One finished frame: the Blender picture (or a card) with the gate weave, the 2D gags, the irises, the film wear and
// sepia print, then the bouncing-ball captions on top (crisp, so they read at phone size).
//   renderFrame(img, v, { ui, pts, frame })  v = video seconds, frame = 0-based index; returns RGBA pixels
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { createCanvas } from '@napi-rs/canvas';
import { TL, FPS, drawUI } from './ui.mjs';
import { W, H, weave, wear, filmFrame } from './film.mjs';
import { drawFX } from './fx.mjs';
import { titleCard, fimCard, iris } from './cards.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const CARDS = JSON.parse(fs.readFileSync(path.join(HERE, 'cards.json'), 'utf8'));
const END = TL.start + TL.frames / FPS;
const canvas = createCanvas(W, H);
const ctx = canvas.getContext('2d');
const DIAG = Math.hypot(W, H) / 2 + 40;
const ease = x => { x = Math.max(0, Math.min(1, x)); return x * x * (3 - 2 * x); };

function irises(song, pts) {
  const [o0, o1] = CARDS.iris_open;
  if (song >= o0 && song < o1) iris(ctx, DIAG * ease((song - o0) / (o1 - o0)));
  const [d0, d1] = CARDS.dive_close;
  if (song >= d0 && song < d1) iris(ctx, DIAG * (1 - ease((song - d0) / (d1 - d0))));
  const [t0, t1] = CARDS.trevas_open;
  if (song >= t0 && song < t1) iris(ctx, DIAG * ease((song - t0) / (t1 - t0)));
  const [c0, c1] = CARDS.iris_close;
  if (song >= c0 && song < c1) {
    const p = pts && pts.trap ? [pts.trap[0] * W, pts.trap[1] * H] : [W / 2, H / 2];
    // closes most of the way fast, holds a moment on the trap, then shuts
    const k = (song - c0) / (c1 - c0);
    const r = k < 0.6 ? lerpR(DIAG, 170, ease(k / 0.6)) : lerpR(170, 0, ease((k - 0.6) / 0.4));
    iris(ctx, r, p[0], p[1]);
  }
}
const lerpR = (a, b, k) => a + (b - a) * k;

export function renderFrame(img, v, { ui = true, pts = {}, frame = 0 } = {}) {
  const song = TL.start + v;
  ctx.fillStyle = '#000';
  ctx.fillRect(0, 0, W, H);
  const wv = weave(frame);
  ctx.save();
  ctx.translate(W / 2 + wv.dx, H / 2 + wv.dy);
  ctx.rotate(wv.rot);
  ctx.scale(1.012, 1.012);
  ctx.translate(-W / 2, -H / 2);
  if (song < CARDS.title_until) titleCard(ctx, song - TL.start);
  else if (song >= CARDS.fim_from) fimCard(ctx, song - CARDS.fim_from, END - CARDS.fim_from);
  else {
    if (img) ctx.drawImage(img, 0, 0, W, H);
    drawFX(ctx, song, pts, frame);
  }
  ctx.restore();
  if (song >= CARDS.title_until && song < CARDS.fim_from) irises(song, pts);
  if (song >= CARDS.title_until - 0.0001 && song < CARDS.iris_open[0]) {
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, W, H);
  }
  wear(ctx, frame);
  const im = ctx.getImageData(0, 0, W, H);
  filmFrame(im.data, frame);
  ctx.putImageData(im, 0, 0);
  if (ui) drawUI(ctx, v);
  return ctx.getImageData(0, 0, W, H).data;
}
