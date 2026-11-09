// Tiles the step-3 renders from src/erva/blender/cast_sheet.py into labelled sheets.
//   node src/erva/cast_sheet.mjs
// Out: blender/erva/review/03-turnaround.png (one row per cast member) and 03-poses.png (P1 and M1 pose strips).
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { createCanvas, loadImage, GlobalFonts } from '@napi-rs/canvas';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REVIEW = path.resolve(HERE, '..', '..', 'blender/erva/review');
const DIR = path.join(REVIEW, 'cast');
GlobalFonts.registerFromPath(path.join(HERE, 'fonts', 'AlfaSlabOne-Regular.ttf'), 'VT323');
const L = JSON.parse(fs.readFileSync(path.join(DIR, 'listing.json'), 'utf8'));
const NAMES = { P1: 'PARDÃO', VOVO: 'VOVÔ (narrador)', EVA: 'EVA', P2: 'P2 PARDJHONSON', P3: 'P3 (bolinhas)', P4: 'P4 (xadrez)', ALMA: 'ALMA (a alma)', COBRA: 'COBRA' };

const TW = 240, TH = 320, CAP = 30, GAP = 6, LEFT = 210;

// Turnarounds: two cast members per row, four views each
{
  const rows = Math.ceil(L.turn.length / 2);
  const c = createCanvas(2 * (LEFT + 4 * (TW + GAP)) + GAP, rows * (TH + CAP + GAP) + GAP);
  const ctx = c.getContext('2d');
  ctx.fillStyle = '#1c1812';
  ctx.fillRect(0, 0, c.width, c.height);
  for (const [i, [name, views]] of L.turn.entries()) {
    const ox = (i % 2) * (LEFT + 4 * (TW + GAP)), y = GAP + Math.floor(i / 2) * (TH + CAP + GAP);
    ctx.font = '30px VT323';
    ctx.fillStyle = '#f5c95a';
    ctx.fillText(NAMES[name] || name, ox + 10, y + TH / 2);
    for (const [k, [label, file]] of views.entries()) {
      const x = ox + LEFT + k * (TW + GAP);
      // the soul was shot alone on transparent film: it's faded as a whole onto the tile
      if (name === 'ALMA') {
        ctx.fillStyle = '#cdcdcd';
        ctx.fillRect(x, y, TW, TH);
        ctx.globalAlpha = 0.55;
      }
      ctx.drawImage(await loadImage(path.join(DIR, file)), x, y, TW, TH);
      ctx.globalAlpha = 1;
      ctx.font = '20px VT323';
      ctx.fillStyle = '#ffffff';
      ctx.fillText(label, x + 4, y + TH + 22);
    }
  }
  fs.writeFileSync(path.join(REVIEW, '03-turnaround.png'), c.toBuffer('image/png'));
}

// Pose strips: P1's row(s) then M1's
{
  const COLS = 7;
  const strips = [['PARDÃO', L.pardo], ['COBRA', L.cobra]];
  const rowsOf = s => Math.ceil(s.length / COLS);
  const totalRows = strips.reduce((a, [, s]) => a + rowsOf(s), 0);
  const c = createCanvas(COLS * (TW + GAP) + GAP, totalRows * (TH + CAP + GAP) + GAP + strips.length * 40);
  const ctx = c.getContext('2d');
  ctx.fillStyle = '#1c1812';
  ctx.fillRect(0, 0, c.width, c.height);
  let y = GAP;
  for (const [title, s] of strips) {
    ctx.font = '30px VT323';
    ctx.fillStyle = '#f5c95a';
    ctx.fillText(title, 10, y + 28);
    y += 40;
    for (const [i, [pname, file]] of s.entries()) {
      const x = GAP + (i % COLS) * (TW + GAP), yy = y + Math.floor(i / COLS) * (TH + CAP + GAP);
      ctx.drawImage(await loadImage(path.join(DIR, file)), x, yy, TW, TH);
      ctx.font = '20px VT323';
      ctx.fillStyle = '#ffffff';
      ctx.fillText(pname, x + 4, yy + TH + 22);
    }
    y += rowsOf(s) * (TH + CAP + GAP);
  }
  fs.writeFileSync(path.join(REVIEW, '03-poses.png'), c.toBuffer('image/png'));
}
console.log('wrote 03-turnaround.png and 03-poses.png');
