// RE1-style captions: white pixel text, word by word, in a black strip. Censor bars flash red as the word lands.
// Everything is a pure function of video time, so a late sync fix needs no Blender re-render.
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { GlobalFonts } from '@napi-rs/canvas';

const HERE = path.dirname(fileURLToPath(import.meta.url));
export const TL = JSON.parse(fs.readFileSync(path.join(HERE, 'timeline.json'), 'utf8'));
export const W = 1080, H = 1920;
export const FPS = TL.fps;

GlobalFonts.registerFromPath(path.join(HERE, 'fonts', 'VT323-Regular.ttf'), 'VT323');

// Clear of TikTok's right-hand icons and bottom caption area. VT323 is drawn on 4x its 16 px grid, to match the 4x picture.
export const STRIP = { x: 0, y: 1272, w: W, h: 136 };
const TEXT_LEFT = 44, TEXT_W = 892, TEXT_PX = 80;
const INK = '#f2f2ea', FLASH = '#e0261a';

// Index of the video frame a song time lands on: 0 is the first frame
export const frameOf = t => Math.round((t - TL.start) * FPS);

// Censored words are written with # in the timeline, and their bar length comes from the gags list in order
const barOf = new Map();
{
  let g = 0;
  TL.lines.forEach((line, l) => line.words.forEach((w, k) => {
    if (w[2] === 'gag') barOf.set(`${l}:${k}`, TL.gags[g++].bar);
  }));
}

function layout(ctx, line, l) {
  ctx.font = `${TEXT_PX}px VT323`;
  const charW = ctx.measureText('m').width, space = ctx.measureText(' ').width;
  let x = 0;
  const cells = line.words.map(([word, t, tag], k) => {
    const gap = x === 0 ? 0 : space;
    const head = tag === 'gag' ? word.replace('#', '') : word;
    const w = ctx.measureText(head).width + (tag === 'gag' ? barOf.get(`${l}:${k}`) * charW : 0);
    const cell = { word, head, tag, t, x: x + gap, w, bar: tag === 'gag' ? barOf.get(`${l}:${k}`) * charW : 0 };
    x += gap + w;
    return cell;
  });
  // Left-aligned on the line's own centre, so words never shift as they appear
  const left = TEXT_LEFT + Math.max(0, (TEXT_W - x) / 2);
  const cy = STRIP.y + STRIP.h / 2 + 2;
  return cells.map(c => ({ ...c, cx: left + c.x, cy }));
}

const activeLine = n => {
  let i = 0;
  TL.lines.forEach((l, k) => { if (frameOf(l.words[0][1]) <= n) i = k; });
  return i;
};

export function drawUI(ctx, v) {
  const n = Math.round(v * FPS);
  if (n >= TL.song_frames) return;  // the silent VOCÊ MORREU tail has no caption
  const l = activeLine(n);
  const cells = layout(ctx, TL.lines[l], l);

  ctx.fillStyle = '#000';
  ctx.fillRect(STRIP.x, STRIP.y, STRIP.w, STRIP.h);

  ctx.save();
  ctx.font = `${TEXT_PX}px VT323`;
  ctx.textAlign = 'left';
  ctx.textBaseline = 'middle';
  for (const c of cells) {
    const age = n - frameOf(c.t);
    if (age < 0) continue;
    ctx.fillStyle = INK;
    ctx.fillText(c.head, c.cx, c.cy);
    if (c.tag === 'gag') {
      const hw = c.w - c.bar;
      ctx.fillStyle = age < 12 && (age >> 1) % 2 === 0 ? FLASH : INK;
      ctx.fillRect(c.cx + hw + 4, c.cy - TEXT_PX * 0.3, c.bar - 8, TEXT_PX * 0.6);
    }
  }
  ctx.restore();
}

// Word boxes per line, for the check on the finished MP4 (sync/check.py)
export function wordBoxes(ctx) {
  return TL.lines.map((line, l) => layout(ctx, line, l).map(c => ({
    line: l + 1, word: c.word, t: c.t, gag: c.tag === 'gag',
    x: Math.round(c.cx), y: Math.round(c.cy - TEXT_PX / 2), w: Math.round(c.w), h: TEXT_PX,
  }))).flat();
}
