// Dialog UI: cream bubble, tilted name tag, word-by-word text, bouncing arrow and the PARDO ENERGIA meter.
// Everything is a pure function of video time, so a late sync fix needs no Blender re-render.
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { GlobalFonts } from '@napi-rs/canvas';

const HERE = path.dirname(fileURLToPath(import.meta.url));
export const TL = JSON.parse(fs.readFileSync(path.join(HERE, 'timeline.json'), 'utf8'));
export const W = 1080, H = 1920;
export const FPS = TL.fps;

GlobalFonts.registerFromPath(path.join(HERE, 'fonts', 'Fredoka-SemiBold.ttf'), 'Fredoka');

// Clear of TikTok's right-hand icons and bottom caption area
const BOX = { x: 44, y: 1236, w: 892, h: 276 };
const TEXT_PX = 66, LINE_PX = 84, TEXT_W = 780;
const INK = '#5b4630', CREAM = '#fff7dc', ARROW = '#f0a23c';
const TAGS = { PARDO: '#f4b740', TODOS: '#7fd1ae' };

// Index of the video frame a song time lands on: 0 is the first frame. A word shows on the frame nearest its time.
export const frameOf = t => Math.round((t - TL.start) * FPS);

// Gloss level from 0 to 5 at video time v, easing up as each line arrives. Same formula as aero_level in blender/s08_shots.py.
export function aeroLevel(v) {
  let lvl = 0;
  for (const line of TL.lines) {
    const t = line.words[0][1] - TL.start;
    const u = Math.min(1, Math.max(0, (v - (t - 0.2)) / 0.35));
    lvl += (line.aero - lvl) * u * u * (3 - 2 * u);
  }
  return lvl;
}

// Word positions are fixed per line, so words never shift as they appear
function layout(ctx, line) {
  ctx.font = `${TEXT_PX}px Fredoka`;
  const space = ctx.measureText(' ').width * 1.15;
  const place = words => {
    let x = 0;
    return words.map(([word, t, tag]) => {
      const w = ctx.measureText(word).width;
      const gap = tag === 'join' || x === 0 ? 0 : space;
      const cell = { word, t, x: x + gap, w };
      x += gap + w;
      return cell;
    });
  };
  const widthOf = row => row.at(-1).x + row.at(-1).w;
  let rows = [place(line.words)];
  // Too long for one row: split it into two rows of the most even width
  if (widthOf(rows[0]) > TEXT_W) {
    let best = Infinity;
    for (let k = 1; k < line.words.length; k++) {
      const a = place(line.words.slice(0, k)), b = place(line.words.slice(k));
      const worst = Math.max(widthOf(a), widthOf(b));
      if (worst < best) { best = worst; rows = [a, b]; }
    }
  }
  const top = BOX.y + BOX.h / 2 + 8 - ((rows.length - 1) * LINE_PX) / 2;
  const out = [];
  rows.forEach((row, r) => {
    const rowW = row.at(-1).x + row.at(-1).w;
    const left = BOX.x + (BOX.w - rowW) / 2;
    for (const c of row) out.push({ ...c, cx: left + c.x + c.w / 2, cy: top + r * LINE_PX });
  });
  return out;
}

// The line on screen at frame index n: frame 0 already shows the first line's bubble, empty
const activeLine = n => {
  let i = 0;
  TL.lines.forEach((l, k) => { if (frameOf(l.words[0][1]) <= n) i = k; });
  return i;
};

// A soft, slightly blobby rounded rectangle, like the game's speech bubble
function blob(ctx, x, y, w, h) {
  const b = 18, r = h * 0.46;
  ctx.beginPath();
  ctx.moveTo(x + r, y + b * 0.4);
  ctx.bezierCurveTo(x + w * 0.3, y - b, x + w * 0.7, y - b, x + w - r, y + b * 0.4);
  ctx.bezierCurveTo(x + w + b * 0.5, y + b, x + w + b * 0.5, y + h - b, x + w - r, y + h - b * 0.4);
  ctx.bezierCurveTo(x + w * 0.7, y + h + b, x + w * 0.3, y + h + b, x + r, y + h - b * 0.4);
  ctx.bezierCurveTo(x - b * 0.5, y + h - b, x - b * 0.5, y + b, x + r, y + b * 0.4);
  ctx.closePath();
}

function drawTag(ctx, who, pop) {
  const label = who;
  ctx.save();
  ctx.font = '50px Fredoka';
  const w = ctx.measureText(label).width + 68, h = 78;
  ctx.translate(BOX.x + 40 + w / 2, BOX.y - 6);
  ctx.rotate(-0.07);
  ctx.scale(pop, pop);
  ctx.fillStyle = TAGS[who] || TAGS.PARDO;
  ctx.beginPath();
  ctx.roundRect(-w / 2, -h / 2, w, h, h / 2);
  ctx.fill();
  ctx.fillStyle = INK;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(label, 0, 3);
  ctx.restore();
}

function drawMeter(ctx, v) {
  const song = v + TL.start;
  const [a, z] = TL.shots.energia;
  if (song < a || song >= z) return;
  const fill = 0.14 + 0.86 * Math.min(1, Math.max(0, (song - TL.cues.energia) / 0.55)) ** 0.7;
  const x = BOX.x + 40, y = 1040, w = BOX.w - 80, h = 44;
  ctx.save();
  ctx.font = '42px Fredoka';
  ctx.fillStyle = '#fff';
  ctx.shadowColor = 'rgba(70,50,30,.7)';
  ctx.shadowBlur = 10;
  ctx.fillText('PARDO ENERGIA', x + 6, y - 18);
  ctx.shadowBlur = 0;
  ctx.fillStyle = CREAM;
  ctx.beginPath();
  ctx.roundRect(x - 8, y - 8, w + 16, h + 16, (h + 16) / 2);
  ctx.fill();
  const g = ctx.createLinearGradient(x, 0, x + w, 0);
  g.addColorStop(0, '#6fd45a');
  g.addColorStop(1, '#ffd23c');
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.roundRect(x, y, Math.max(h, w * fill), h, h / 2);
  ctx.fill();
  ctx.restore();
}

export function drawUI(ctx, v) {
  const n = Math.round(v * FPS);
  const lineIdx = activeLine(n);
  const line = TL.lines[lineIdx];
  const cells = layout(ctx, line);
  const lineAge = n - (lineIdx === 0 ? 0 : frameOf(line.words[0][1]));

  drawMeter(ctx, v);

  ctx.save();
  ctx.shadowColor = 'rgba(70,50,30,.28)';
  ctx.shadowBlur = 22;
  ctx.shadowOffsetY = 8;
  ctx.fillStyle = CREAM;
  blob(ctx, BOX.x, BOX.y, BOX.w, BOX.h);
  ctx.fill();
  ctx.restore();

  const tagPop = lineAge < 4 ? [0.8, 1.1, 1.04, 1][lineAge] : 1;
  drawTag(ctx, line.who, tagPop);

  ctx.save();
  ctx.font = `${TEXT_PX}px Fredoka`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillStyle = INK;
  for (const c of cells) {
    const age = n - frameOf(c.t);
    if (age < 0) continue;
    const s = age < 4 ? [0.82, 1.1, 1.04, 1][age] : 1;
    ctx.save();
    ctx.translate(c.cx, c.cy);
    ctx.scale(s, s);
    ctx.fillText(c.word, 0, 0);
    ctx.restore();
  }
  ctx.restore();

  // Arrow appears once the whole line is out, and bounces with the beat
  if (n >= frameOf(line.words.at(-1)[1])) {
    const beats = (v + TL.start - TL.beat0) / (60 / TL.bpm);
    const bounce = Math.abs(Math.sin(beats * Math.PI)) * 10;
    const ax = BOX.x + BOX.w / 2, ay = BOX.y + BOX.h - 22 + bounce;
    ctx.fillStyle = ARROW;
    ctx.beginPath();
    ctx.moveTo(ax - 22, ay - 12);
    ctx.lineTo(ax + 22, ay - 12);
    ctx.lineTo(ax, ay + 12);
    ctx.closePath();
    ctx.fill();
  }
}

// Word boxes per line, for the check on the finished MP4 (sync/check.py)
export function wordBoxes(ctx) {
  return TL.lines.map((line, l) => layout(ctx, line).map(c => ({
    line: l + 1, word: c.word, t: c.t,
    x: Math.round(c.cx - c.w / 2), y: Math.round(c.cy - TEXT_PX / 2), w: Math.round(c.w), h: TEXT_PX,
  }))).flat();
}
