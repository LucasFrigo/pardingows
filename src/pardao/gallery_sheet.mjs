// Tiles the per-model renders from src/pardao/blender/gallery.py into labelled contact sheets, one per gallery row.
//   node src/pardao/gallery_sheet.mjs
// Out: blender/pardao/review/02-kit-{characters,favela,objects}.png. Labels: sheet number, name, real size in metres, polys, rig.
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { createCanvas, loadImage, GlobalFonts } from '@napi-rs/canvas';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..', '..');
const REVIEW = path.join(ROOT, 'blender/pardao/review');
GlobalFonts.registerFromPath(path.join(HERE, 'fonts', 'VT323-Regular.ttf'), 'VT323');

const rep = JSON.parse(fs.readFileSync(path.join(REVIEW, '02-import.json'), 'utf8'));
const sheetNo = Object.fromEntries(JSON.parse(fs.readFileSync(path.join(REVIEW, '00-assets.json'), 'utf8')).map(a => [a.uid, a.n]));
const fetchSrc = fs.readFileSync(path.join(HERE, 'blender/fetch_assets.py'), 'utf8');
const uidOf = name => fetchSrc.match(new RegExp(`"${name}": "([0-9a-f]{32})"`))?.[1];

const COLS = 6, T = 300, CAP = 64, GAP = 6;
for (const row of ['characters', 'favela', 'objects']) {
  const names = Object.keys(rep).filter(n => rep[n].row === row);
  const rows = Math.ceil(names.length / COLS);
  const c = createCanvas(COLS * (T + GAP) + GAP, rows * (T + CAP + GAP) + GAP);
  const ctx = c.getContext('2d');
  ctx.fillStyle = '#14151c';
  ctx.fillRect(0, 0, c.width, c.height);
  for (const [i, name] of names.entries()) {
    const x = GAP + (i % COLS) * (T + GAP), y = GAP + Math.floor(i / COLS) * (T + CAP + GAP);
    const img = await loadImage(path.join(REVIEW, 'gallery', `${name}.png`));
    ctx.drawImage(img, x, y, T, T);
    const r = rep[name];
    const n = sheetNo[uidOf(name)];
    ctx.font = '24px VT323';
    ctx.fillStyle = '#ffd23f';
    ctx.fillText(`${n ?? '-'} ${name}`, x + 2, y + T + 20);
    ctx.fillStyle = '#ffffff';
    ctx.fillText(`${r.metres.map(v => v.toFixed(2)).join(' x ')} m`, x + 2, y + T + 40);
    ctx.fillStyle = r.armatures.length ? '#7dff8a' : '#bbbbbb';
    ctx.fillText(`${r.polys}p ${r.armatures.length ? 'RIG ' + r.armatures[0].bones + ' bones' : 'no rig'}`, x + 2, y + T + 60);
  }
  const out = path.join(REVIEW, `02-kit-${row}.png`);
  fs.writeFileSync(out, c.toBuffer('image/png'));
  console.log('wrote', out);
}
