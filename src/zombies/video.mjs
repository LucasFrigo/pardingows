// renderFrame(dir, f, v): one video frame. Everything is built on a 270x480 canvas, as the console would, through the PS1 colour pass and scaled x4 nearest.
// The RE1 screens are drawn here, so their timing and wording need no Blender re-render. Then the judging zombie's corner window and the captions go on top.
import fs from 'fs';
import path from 'path';
import { createCanvas, loadImage } from '@napi-rs/canvas';
import { ps1Colour } from '../shared/ps1.mjs';
import { TL, W, H, FPS, drawUI } from './ui.mjs';

export const IW = 270, IH = 480;

const full = createCanvas(W, H);
const ctx = full.getContext('2d', { alpha: false });
const small = createCanvas(IW, IH);
const g = small.getContext('2d', { alpha: false });
const tmp = createCanvas(IW, IH);
const tg = tmp.getContext('2d', { alpha: false });
g.imageSmoothingEnabled = false;
ctx.imageSmoothingEnabled = false;
tg.imageSmoothingEnabled = false;

const START = TL.start;
const SHOTS = TL.lines.map((l, i) => ({ name: l.shot, t: i === 0 ? START : l.words[0][1], words: l.words }));
const shotAt = song => SHOTS.reduce((cur, s) => (Math.round((s.t - START) * FPS) <= Math.round((song - START) * FPS) ? s : cur), SHOTS[0]);
const word = (name, i) => SHOTS.find(s => s.name === name).words[i][1];

function text(c, str, x, y, px, colour, align = 'left') {
  c.font = `${px}px VT323`;
  c.textAlign = align;
  c.textBaseline = 'alphabetic';
  c.fillStyle = colour;
  c.fillText(str, x, y);
}

// A repeatable scatter
function rng(seed) {
  let x = seed;
  return () => (x = (x * 1664525 + 1013904223) >>> 0) / 4294967296;
}

// ---- Title: a frozen, drained character card, then the logo slams in dripping
function drain(c) {
  const id = c.getImageData(0, 0, IW, IH), p = id.data;
  for (let i = 0; i < p.length; i += 4) {
    const y = p[i] * 0.3 + p[i + 1] * 0.59 + p[i + 2] * 0.11;
    p[i] = Math.min(255, y * 1.12 + 10);
    p[i + 1] = y * 0.98 + 4;
    p[i + 2] = y * 0.82;
  }
  c.putImageData(id, 0, 0);
}

function card(song) {
  drain(g);
  if (song >= word('title', 2) - 0.1) {
    g.fillStyle = 'rgba(0,0,0,.55)';
    g.fillRect(0, 248, IW, 44);
    text(g, 'PARDO', 12, 272, 28, '#f2f2ea');
    text(g, 'P.A.R.D.O.S. - EQUIPE ALFA', 12, 286, 16, '#c9a227');
  }
}

function drips(c, x0, x1, top, len, seed, colour) {
  const r = rng(seed);
  c.fillStyle = colour;
  for (let x = x0; x < x1; x += 4) {
    const k = r();
    if (k > 0.5) continue;
    c.fillRect(x, top, 3, Math.max(0, len * (0.25 + r())));
  }
}

function logo(song) {
  const age = song - TL.title_logo;
  g.fillStyle = '#050304';
  g.fillRect(0, 0, IW, IH);
  const pop = age < 0.1 ? 1.5 - 5 * age : 1;
  g.save();
  g.translate(IW / 2, 150);
  g.scale(pop, pop);
  text(g, 'RESIDENT', 0, 0, 58, '#a81410', 'center');
  text(g, 'PARDO', 0, 62, 86, '#d81c14', 'center');
  g.restore();
  if (age >= 0.1) {
    const len = Math.min(70, (age - 0.1) * 130);
    drips(g, 28, 244, 152, len * 0.55, 3, '#a81410');
    drips(g, 62, 212, 214, len, 8, '#a81410');
  }
}

// ---- The diary: a parody of RE1's file screen, typed as the words are sung
const paper = createCanvas(IW, IH);
{
  const p = paper.getContext('2d');
  p.fillStyle = '#b4a684';
  p.fillRect(0, 0, IW, IH);
  const r = rng(77);
  for (let i = 0; i < 2400; i++) {
    p.fillStyle = r() > 0.5 ? 'rgba(70,50,30,.10)' : 'rgba(255,240,200,.08)';
    p.fillRect((r() * IW) | 0, (r() * IH) | 0, 2, 2);
  }
  p.fillStyle = 'rgba(90,10,10,.55)';
  for (let i = 0; i < 26; i++) p.fillRect((206 + r() * 44) | 0, (34 + r() * 44) | 0, 3 + (r() * 7 | 0), 3 + (r() * 7 | 0));
}

function file(song) {
  g.drawImage(paper, 0, 0);
  const a = word('file', 0), b = word('file', 1);
  const INK = '#241a12';
  text(g, 'DIÁRIO DO PARDO', 20, 44, 22, INK);
  g.fillStyle = INK;
  g.fillRect(20, 50, 190, 2);
  const lines = [[a, 'N*CROFILIA', 106, 36], [a + 0.42, 'coça.', 136, 26], [b, 'Z*MBIFILIA', 204, 36], [b + 0.42, 'fome.', 234, 26]];
  for (const [t, str, y, px] of lines) {
    if (song < t) continue;
    const typed = Math.min(str.length, Math.floor((song - t) * 34) + 1);
    text(g, str.slice(0, typed), 20, y, px, INK);
  }
  if (song >= b + 0.75) text(g, 'coça... fome...', 20, 286, 22, '#5a0a0a');
}

// ---- The select screen. Same zombie for careca and cabeluda: the wig is the joke.
let mugs = null;
const MUG = 120, CROP = 210;
function select(song) {
  g.fillStyle = '#07070a';
  g.fillRect(0, 0, IW, IH);
  text(g, 'SELECIONE O ZUMBI', IW / 2, 26, 22, '#c8c4b0', 'center');
  const slots = [
    ['CARECA', word('select_a', 0), 10, 38], ['CABELUDA', word('select_a', 2), 140, 38],
    ['CAOLHA', word('select_b', 0), 10, 180], ['BANGUELA', word('select_b', 2), 140, 180],
  ];
  let current = -1;
  slots.forEach(([, t], i) => { if (song >= t) current = i; });
  slots.forEach(([label, t, x, y], i) => {
    g.fillStyle = '#16161c';
    g.fillRect(x, y, MUG, MUG);
    if (song >= t && mugs?.[i]) {
      const age = song - t;
      const k = age < 0.07 ? 1.25 : 1;
      const w = MUG * k, d = (w - MUG) / 2;
      g.drawImage(mugs[i], (IW - CROP) / 2, (IH - CROP) / 2, CROP, CROP, x - d, y - d, w, w);
      text(g, label, x + MUG / 2, y + MUG + 15, 18, i === current ? '#f2f2ea' : '#8a867a', 'center');
    }
    if (i === current) {
      g.strokeStyle = '#d81c14';
      g.lineWidth = 3;
      g.strokeRect(x - 2, y - 2, MUG + 4, MUG + 4);
    }
  });
}

// ---- The status ECG: he's fine, until he isn't
function ecg(song) {
  const flip = word('shiver', 1);
  const bad = song >= flip;
  const col = bad ? '#e8c020' : '#30d060';
  const x0 = 158, y0 = 18, w = 100, h = 36;
  g.fillStyle = 'rgba(0,0,0,.72)';
  g.fillRect(x0, y0, w, h);
  g.strokeStyle = col;
  g.lineWidth = 1;
  g.strokeRect(x0 + 0.5, y0 + 0.5, w - 1, h - 1);
  const rate = bad ? 7 : 3.5;
  g.fillStyle = col;
  let py = y0 + 18;
  for (let i = 0; i < w - 8; i++) {
    const u = ((i / 40) + song * rate * 0.25) % 1;
    const y = y0 + 18 + (u < 0.1 ? -13 * Math.sin(u * 31.4) : u < 0.16 ? 8 * Math.sin((u - 0.1) * 52) : 0);
    g.fillRect(x0 + 4 + i, Math.min(py, y) | 0, 1, Math.max(1, Math.abs(y - py)) | 0);
    py = y;
  }
  text(g, bad ? 'CAUTION' : 'FINE', x0 + 5, y0 + 33, 14, col);
}

// ---- Game over: the picture goes to black and the words seep down
function gameOver(song) {
  const age = song - TL.game_over;
  if (age < 0) return;
  g.fillStyle = `rgba(0,0,0,${Math.min(1, age / 0.22)})`;
  g.fillRect(0, 0, IW, IH);
  const reveal = Math.min(1, age / 0.5);
  g.save();
  g.beginPath();
  g.rect(0, 96, IW, 88 * reveal + 4);
  g.clip();
  text(g, 'VOCÊ', IW / 2, 144, 40, '#c8100c', 'center');
  text(g, 'MORREU', IW / 2, 178, 48, '#c8100c', 'center');
  g.restore();
  if (age > 0.2) drips(g, 50, 222, 180, Math.min(90, (age - 0.2) * 95), 21, '#8a0c08');
}

// ---- Frames from Blender. An animatic with gaps holds the nearest frame.
const frameCache = new Map();
function listing(dir) {
  if (!frameCache.has(dir)) {
    const nums = fs.existsSync(dir) ? fs.readdirSync(dir).filter(n => /^f_\d+\.png$/.test(n)).map(n => Number(n.match(/\d+/)[0])).sort((a, b) => a - b) : [];
    frameCache.set(dir, nums);
  }
  return frameCache.get(dir);
}

const imgCache = new Map();
async function frameImage(dir, f) {
  const nums = listing(dir);
  if (!nums.length) return null;
  let best = nums[0];
  for (const n of nums) {
    if (Math.abs(n - f) < Math.abs(best - f)) best = n;
    if (n > f) break;
  }
  const key = `${dir}/${best}`;
  if (!imgCache.has(key)) {
    if (imgCache.size > 6) imgCache.delete(imgCache.keys().next().value);
    imgCache.set(key, await loadImage(path.join(dir, `f_${String(best).padStart(4, '0')}.png`)));
  }
  return imgCache.get(key);
}

// The judging zombie's close-up through the PS1 pass, on its own canvas
async function judge(dir, k) {
  const f = TL.judge_first + Math.max(0, Math.min(TL.judge_frames - 1, k));
  const img = await frameImage(path.join(dir, 'judge'), f);
  if (!img) return null;
  tg.drawImage(img, 0, 0, IW, IH);
  const id = tg.getImageData(0, 0, IW, IH);
  ps1Colour(id.data, IW, IH);
  tg.putImageData(id, 0, 0);
  return tmp;
}

export async function renderFrame(dir, f, v, { ui = true } = {}) {
  const song = v + START;
  const n = f - 1;
  if (!mugs) {
    mugs = [];
    for (let i = 0; i < TL.mugs.length; i++) mugs.push(await frameImage(path.join(dir, 'mug'), TL.mug_first + i));
  }
  const shot = shotAt(song);
  g.imageSmoothingEnabled = false;
  const fullGag = TL.gags.find(x => x.full && song >= x.full[0] && song < x.full[1]);
  if (n >= TL.song_frames) {
    g.fillStyle = '#000';
    g.fillRect(0, 0, IW, IH);
  } else if (shot.name === 'file') {
    file(song);
  } else if (shot.name === 'select_a' || shot.name === 'select_b') {
    select(song);
  } else if (shot.name === 'judge_full' || fullGag) {
    const im = await judge(dir, Math.round((song - fullGag.full[0]) * FPS));
    if (im) g.drawImage(im, 0, 0);
  } else {
    const img = await frameImage(path.join(dir, 'main'), f);
    if (img) g.drawImage(img, 0, 0, IW, IH);
  }
  // The judge frame already went through the colour pass, and doing it twice only darkens the dither
  const raw = !(shot.name === 'judge_full' || fullGag);
  if (shot.name === 'title') {
    if (song >= TL.title_logo) logo(song);
    else card(song);
  }
  if (shot.name === 'shiver') ecg(song);
  gameOver(song);
  if (raw) {
    const id = g.getImageData(0, 0, IW, IH);
    ps1Colour(id.data, IW, IH);
    g.putImageData(id, 0, 0);
  }
  ctx.drawImage(small, 0, 0, W, H);

  // The corner window snaps in on the word and snaps out again
  for (const gag of TL.gags) {
    const dt = song - gag.t;
    if (gag.window && dt >= 0 && dt < gag.window) {
      const im = await judge(dir, Math.round(dt * FPS));
      if (im) {
        const side = 150, sx = (IW - side) / 2, sy = (IH - side) / 2;
        const out = 336;
        const x = gag.corner === 'right' ? W - out - 40 : 40, y = 232;
        ctx.fillStyle = '#000';
        ctx.fillRect(x - 12, y - 12, out + 24, out + 24);
        ctx.fillStyle = '#c8100c';
        ctx.fillRect(x - 6, y - 6, out + 12, out + 12);
        ctx.drawImage(im, sx, sy, side, side, x, y, out, out);
      }
    }
  }
  if (ui) drawUI(ctx, v);
  return ctx.getImageData(0, 0, W, H).data;
}

// For the look stills: a raw Blender image through the same pass
export function compose(img, v, { ui = true } = {}) {
  g.drawImage(img, 0, 0, IW, IH);
  const id = g.getImageData(0, 0, IW, IH);
  ps1Colour(id.data, IW, IH);
  g.putImageData(id, 0, 0);
  ctx.drawImage(small, 0, 0, W, H);
  if (ui) drawUI(ctx, v);
  return full;
}
