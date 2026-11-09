// Tiles the step-3 renders from src/pardao/blender/cast_sheet.py into labelled sheets.
//   node src/pardao/cast_sheet.mjs
// Out: blender/pardao/review/03-turnaround.png (one row per cast member) and 03-poses.png (P1 and M1 pose strips).
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { createCanvas, loadImage, GlobalFonts } from '@napi-rs/canvas';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REVIEW = path.resolve(HERE, '..', '..', 'blender/pardao/review');
const DIR = path.join(REVIEW, 'cast');
GlobalFonts.registerFromPath(path.join(HERE, 'fonts', 'VT323-Regular.ttf'), 'VT323');
const L = JSON.parse(fs.readFileSync(path.join(DIR, 'listing.json'), 'utf8'));
const NAMES = { P1: 'P1 PARDO', P2: 'P2 PARDJHONSON', P3: 'P3 PARDO AZUL', P4: 'P4 PARDO VERDE', M1: 'MILDINGOW 1', M2: 'MILDINGOW 2', M3: 'MILDINGOW 3', MB: 'MENDIGO (extra)', JUMENTO: 'JUMENTO (chefe)' };

const TW = 240, TH = 320, CAP = 30, GAP = 6, LEFT = 210;

// Turnarounds: two cast members per row, four views each
{
  const rows = Math.ceil(L.turn.length / 2);
  const c = createCanvas(2 * (LEFT + 4 * (TW + GAP)) + GAP, rows * (TH + CAP + GAP) + GAP);
  const ctx = c.getContext('2d');
  ctx.fillStyle = '#14151c';
  ctx.fillRect(0, 0, c.width, c.height);
  for (const [i, [name, views]] of L.turn.entries()) {
    const ox = (i % 2) * (LEFT + 4 * (TW + GAP)), y = GAP + Math.floor(i / 2) * (TH + CAP + GAP);
    ctx.font = '34px VT323';
    ctx.fillStyle = '#ffd23f';
    ctx.fillText(NAMES[name] || name, ox + 10, y + TH / 2);
    for (const [k, [label, file]] of views.entries()) {
      const x = ox + LEFT + k * (TW + GAP);
      ctx.drawImage(await loadImage(path.join(DIR, file)), x, y, TW, TH);
      ctx.font = '24px VT323';
      ctx.fillStyle = '#ffffff';
      ctx.fillText(label, x + 4, y + TH + 22);
    }
  }
  fs.writeFileSync(path.join(REVIEW, '03-turnaround.png'), c.toBuffer('image/png'));
}

// Pose strips: P1's row(s) then M1's
{
  const COLS = 7;
  const strips = [['PARDO', L.pardo], ['MILDINGOW', L.hobo]];
  const rowsOf = s => Math.ceil(s.length / COLS);
  const totalRows = strips.reduce((a, [, s]) => a + rowsOf(s), 0);
  const c = createCanvas(COLS * (TW + GAP) + GAP, totalRows * (TH + CAP + GAP) + GAP + strips.length * 40);
  const ctx = c.getContext('2d');
  ctx.fillStyle = '#14151c';
  ctx.fillRect(0, 0, c.width, c.height);
  let y = GAP;
  for (const [title, s] of strips) {
    ctx.font = '34px VT323';
    ctx.fillStyle = '#ffd23f';
    ctx.fillText(title, 10, y + 28);
    y += 40;
    for (const [i, [pname, file]] of s.entries()) {
      const x = GAP + (i % COLS) * (TW + GAP), yy = y + Math.floor(i / COLS) * (TH + CAP + GAP);
      ctx.drawImage(await loadImage(path.join(DIR, file)), x, yy, TW, TH);
      ctx.font = '24px VT323';
      ctx.fillStyle = '#ffffff';
      ctx.fillText(pname, x + 4, yy + TH + 22);
    }
    y += rowsOf(s) * (TH + CAP + GAP);
  }
  fs.writeFileSync(path.join(REVIEW, '03-poses.png'), c.toBuffer('image/png'));
}
console.log('wrote 03-turnaround.png and 03-poses.png');
