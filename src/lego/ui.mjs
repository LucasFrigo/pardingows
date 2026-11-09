// Studded brick-plate captions: one coloured plate per sung line, words popping on as they're sung.
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
const BOX = { x: 44, y: 1250, w: 892, h: 236 };
const MAX_PX = 72, TEXT_W = 824;
const STUD_R = 24, STUD_H = 16, STUD_GAP = 74;
const PLATES = {
  red: { face: '#c8202a', top: '#e0363c', edge: '#8f1219', stud: '#d92c32', studTop: '#ef5552', ink: '#ffffff' },
  yellow: { face: '#f2c300', top: '#ffd929', edge: '#b58f00', stud: '#f9cf14', studTop: '#ffe65c', ink: '#25211a' },
  blue: { face: '#0d62b5', top: '#1f7ad1', edge: '#07427d', stud: '#146dc2', studTop: '#3f95e4', ink: '#ffffff' },
  green: { face: '#1f8f3f', top: '#2eaa50', edge: '#12602a', stud: '#26a048', studTop: '#4cc26c', ink: '#ffffff' },
};

// Index of the video frame a song time lands on: 0 is the first frame. A word shows on the frame nearest its time.
export const frameOf = t => Math.round((t - TL.start) * FPS);

// Word positions and text size are fixed per line, so words never shift as they appear.
function layout(ctx, line) {
  const words = line.words.map(([word, t]) => ({ word, t }));
  const rows = [words.slice(0, line.brk), words.slice(line.brk)].filter(r => r.length);
  const measure = px => {
    ctx.font = `${px}px Fredoka`;
    const space = ctx.measureText(' ').width * 1.12;
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
  const lineH = px * 1.26;
  const top = BOX.y + BOX.h / 2 + 4 - ((placed.length - 1) * lineH) / 2;
  const out = [];
  placed.forEach((row, r) => {
    const left = BOX.x + (BOX.w - row.width) / 2;
    for (const c of row.cells) out.push({ ...c, px, cx: left + c.x + c.w / 2, cy: top + r * lineH });
  });
  return out;
}

// The line on screen at frame index n: frame 0 already shows the first line's plate, empty
const activeLine = n => {
  let i = 0;
  TL.shots.forEach((s, k) => { if (frameOf(s.t) <= n) i = k; });
  return i;
};

// One stud seen from slightly above: side wall, lit round top and a soft shine
function stud(ctx, cx, cy, c) {
  ctx.fillStyle = c.edge;
  ctx.beginPath();
  ctx.ellipse(cx, cy + STUD_H, STUD_R, STUD_R * 0.42, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillRect(cx - STUD_R, cy, STUD_R * 2, STUD_H);
  ctx.fillStyle = c.stud;
  ctx.beginPath();
  ctx.ellipse(cx, cy, STUD_R, STUD_R * 0.42, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = c.studTop;
  ctx.beginPath();
  ctx.ellipse(cx - 4, cy - 2, STUD_R * 0.62, STUD_R * 0.22, 0, 0, Math.PI * 2);
  ctx.fill();
}

function plate(ctx, c, drop) {
  const { x, y, w, h } = BOX;
  const yy = y + drop;
  ctx.save();
  ctx.shadowColor = 'rgba(0,0,0,.42)';
  ctx.shadowBlur = 26;
  ctx.shadowOffsetY = 12;
  ctx.fillStyle = c.edge;
  ctx.beginPath();
  ctx.roundRect(x, yy, w, h + 12, 14);
  ctx.fill();
  ctx.restore();

  const count = Math.floor((w - 40) / STUD_GAP);
  const span = (count - 1) * STUD_GAP;
  for (let i = 0; i < count; i++) stud(ctx, x + w / 2 - span / 2 + i * STUD_GAP, yy - STUD_H + 6, c);

  ctx.fillStyle = c.face;
  ctx.beginPath();
  ctx.roundRect(x, yy, w, h, 14);
  ctx.fill();
  // Moulded plastic: bright top edge, tiny highlight line
  const g = ctx.createLinearGradient(0, yy, 0, yy + 34);
  g.addColorStop(0, c.top);
  g.addColorStop(1, c.face);
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.roundRect(x, yy, w, 34, [14, 14, 0, 0]);
  ctx.fill();
  ctx.fillStyle = 'rgba(255,255,255,.28)';
  ctx.fillRect(x + 16, yy + 5, w - 32, 3);
}

export function drawUI(ctx, v) {
  const n = Math.round(v * FPS);
  const idx = activeLine(n);
  const line = TL.lines[idx];
  const c = PLATES[line.plate];
  const age = n - (idx === 0 ? 0 : frameOf(TL.shots[idx].t));
  // The plate snaps down onto the picture like a brick clicking into place
  const drop = age < 4 ? [-30, 8, -3, 0][age] : 0;
  plate(ctx, c, drop);

  ctx.save();
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillStyle = c.ink;
  for (const cell of layout(ctx, line)) {
    const a = n - frameOf(cell.t);
    if (a < 0) continue;
    const s = a < 4 ? [0.8, 1.12, 1.04, 1][a] : 1;
    ctx.font = `${cell.px}px Fredoka`;
    ctx.save();
    ctx.translate(cell.cx, cell.cy + drop);
    ctx.scale(s, s);
    ctx.fillText(cell.word, 0, 0);
    ctx.restore();
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
