// PS2 game dialogue-box captions: one box per sung line with a speaker tag, words popping on as they're sung.
// Everything is a pure function of video time, so a sync fix needs no Blender re-render.
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { GlobalFonts } from '@napi-rs/canvas';

const HERE = path.dirname(fileURLToPath(import.meta.url));
export const TL = JSON.parse(fs.readFileSync(path.join(HERE, 'timeline.json'), 'utf8'));
export const W = 1080, H = 1920;
export const FPS = TL.fps;

GlobalFonts.registerFromPath(path.join(HERE, 'fonts', 'RussoOne-Regular.ttf'), 'Russo');
GlobalFonts.registerFromPath(path.join(HERE, 'fonts', 'Bungee-Regular.ttf'), 'Bungee');

// Clear of TikTok's right-hand icons (x > 918) and the bottom caption area (y > 1536)
const BOX = { x: 44, y: 1268, w: 862, h: 222 };
const MAX_PX = 74, TEXT_W = 790;

// Index of the video frame a song time lands on: 0 is the first frame. A word shows on the frame nearest its time.
export const frameOf = t => Math.round((t - TL.start) * FPS);

// Word positions and text size are fixed per line, so words never shift as they appear.
function layout(ctx, line) {
  const words = line.words.map(([word, t]) => ({ word, t }));
  const rows = (line.brk ? [words.slice(0, line.brk), words.slice(line.brk)] : [words]).filter(r => r.length);
  const measure = px => {
    ctx.font = `${px}px Russo`;
    const space = ctx.measureText(' ').width * 1.15;
    return rows.map(row => {
      let x = 0;
      const cells = row.map((w, i) => {
        const width = ctx.measureText(w.word).width;
        const cell = { ...w, x: x + (i ? space : 0), w: width };
        x = cell.x + width;
        return cell;
      });
      return { cells, width: x };
    });
  };
  let px = MAX_PX;
  while (px > 40 && Math.max(...measure(px).map(r => r.width)) > TEXT_W) px -= 2;
  const placed = measure(px);
  const lineH = px * 1.3;
  const top = BOX.y + BOX.h / 2 + 14 - ((placed.length - 1) * lineH) / 2;
  const out = [];
  placed.forEach((row, r) => {
    // Left-aligned like an RPG text box, centred only when the line is one short row
    const left = placed.length === 1 ? BOX.x + (BOX.w - row.width) / 2 : BOX.x + 36;
    for (const c of row.cells) out.push({ ...c, px, cx: left + c.x + c.w / 2, cy: top + r * lineH });
  });
  return out;
}

// The line on screen at frame index n: frame 0 already shows the first line's box, empty
export const activeLine = n => {
  let i = 0;
  TL.shots.forEach((s, k) => { if (frameOf(s.t) <= n) i = k; });
  return i;
};

// Translucent navy panel with a bevelled chrome rim, the stock look of a 2000s console text box
function panel(ctx, open) {
  const { x, w } = BOX;
  const h = BOX.h * open, y = BOX.y + (BOX.h - h) / 2;
  ctx.save();
  ctx.shadowColor = 'rgba(0,0,0,.5)';
  ctx.shadowBlur = 24;
  ctx.shadowOffsetY = 10;
  const g = ctx.createLinearGradient(0, y, 0, y + h);
  g.addColorStop(0, 'rgba(24,46,112,.88)');
  g.addColorStop(1, 'rgba(6,14,44,.92)');
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, 18);
  ctx.fill();
  ctx.restore();
  const rim = ctx.createLinearGradient(0, y, 0, y + h);
  rim.addColorStop(0, '#f4f8ff');
  rim.addColorStop(0.5, '#8aa2c8');
  rim.addColorStop(1, '#dfe8f8');
  ctx.strokeStyle = rim;
  ctx.lineWidth = 6;
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, 18);
  ctx.stroke();
  ctx.strokeStyle = 'rgba(120,200,255,.35)';
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.roundRect(x + 9, y + 9, w - 18, h - 18, 12);
  ctx.stroke();
  // Glassy top sheen
  ctx.fillStyle = 'rgba(255,255,255,.07)';
  ctx.beginPath();
  ctx.roundRect(x + 10, y + 10, w - 20, Math.max(0, h * 0.38), [12, 12, 4, 4]);
  ctx.fill();
}

function speakerTag(ctx, name) {
  ctx.font = '40px Bungee';
  const tw = ctx.measureText(name).width;
  const x = BOX.x + 30, y = BOX.y - 30, w = tw + 44, h = 60;
  const g = ctx.createLinearGradient(0, y, 0, y + h);
  g.addColorStop(0, '#ffe45a');
  g.addColorStop(1, '#f29a12');
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, 10);
  ctx.fill();
  ctx.strokeStyle = '#3a1d00';
  ctx.lineWidth = 4;
  ctx.stroke();
  ctx.fillStyle = '#2a1500';
  ctx.textBaseline = 'middle';
  ctx.textAlign = 'left';
  ctx.fillText(name, x + 22, y + h / 2 + 3);
}

export function drawUI(ctx, v) {
  const n = Math.round(v * FPS);
  const idx = activeLine(n);
  const line = TL.lines[idx];
  const age = n - (idx === 0 ? 0 : frameOf(TL.shots[idx].t));
  // The box snaps open vertically over 3 frames on every new line
  const open = age < 3 ? [0.35, 0.8, 1.04][age] : 1;
  ctx.save();
  panel(ctx, open);
  if (age >= 2) speakerTag(ctx, line.speaker);

  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  const cells = layout(ctx, line);
  for (const cell of cells) {
    const a = n - frameOf(cell.t);
    if (a < 0) continue;
    const s = a < 4 ? [1.35, 1.12, 1.03, 1][a] : 1;
    ctx.font = `${cell.px}px Russo`;
    ctx.save();
    ctx.translate(cell.cx, cell.cy);
    ctx.scale(s, s);
    ctx.lineJoin = 'round';
    ctx.lineWidth = 9;
    ctx.strokeStyle = '#050a1e';
    ctx.strokeText(cell.word, 0, 0);
    // A just-sung word flashes yellow for two frames, then settles to white
    ctx.fillStyle = a < 2 ? '#fff25a' : '#ffffff';
    ctx.fillText(cell.word, 0, 0);
    ctx.restore();
  }
  // Blinking "next" arrow once the whole line is out
  const last = cells[cells.length - 1];
  if (n - frameOf(last.t) > 6 && Math.floor(n / 8) % 2 === 0) {
    const ax = BOX.x + BOX.w - 46, ay = BOX.y + BOX.h - 40;
    ctx.fillStyle = '#ffe45a';
    ctx.beginPath();
    ctx.moveTo(ax - 16, ay - 10);
    ctx.lineTo(ax + 16, ay - 10);
    ctx.lineTo(ax, ay + 10);
    ctx.closePath();
    ctx.fill();
  }
  ctx.restore();
}

// Word boxes per line, for the check on the finished MP4 (sync/check.py)
export function wordBoxes(ctx) {
  return TL.lines.map((line, l) => layout(ctx, line).map(c => ({
    line: l + 1, word: c.word, t: c.t,
    x: Math.round(c.cx - c.w / 2), y: Math.round(c.cy - c.px / 2), w: Math.round(c.w), h: c.px,
  }))).flat();
}
