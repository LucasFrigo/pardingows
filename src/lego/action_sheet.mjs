// Labels and tiles the action audit into one review sheet.
//   node src/lego/action_sheet.mjs
// In: blender/lego/review/03-acoes/*.png  Out: blender/lego/review/03-acoes.png
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { createCanvas, loadImage, GlobalFonts } from '@napi-rs/canvas';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REVIEW = path.resolve(HERE, '..', '..', 'blender/lego/review');
GlobalFonts.registerFromPath(path.join(HERE, 'fonts', 'Fredoka-SemiBold.ttf'), 'Fredoka');
const DIR = path.join(REVIEW, '03-acoes');
const files = fs.readdirSync(DIR).filter(n => n.endsWith('_25.png')).sort();
const COLS = 12, TW = 160, TH = 208, CAP = 24;
const canvas = createCanvas(COLS * TW, Math.ceil(files.length / COLS) * (TH + CAP));
const ctx = canvas.getContext('2d');
ctx.fillStyle = '#14151c';
ctx.fillRect(0, 0, canvas.width, canvas.height);
ctx.font = '15px Fredoka';
for (const [i, f] of files.entries()) {
  const x = (i % COLS) * TW, y = Math.floor(i / COLS) * (TH + CAP);
  ctx.drawImage(await loadImage(path.join(DIR, f)), x, y, TW, TH);
  ctx.fillStyle = '#ffd23f';
  ctx.fillText(f.replace('_25.png', '').slice(0, 20), x + 3, y + TH + 17);
}
fs.writeFileSync(path.join(REVIEW, '03-acoes.png'), canvas.toBuffer('image/png'));
console.log(files.length, 'actions');
