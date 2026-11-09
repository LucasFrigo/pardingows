// Tiles every PNG in a folder into one contact sheet, in name order.
//   node src/zombies/contact.mjs <dir> <out.png> [columns] [cell width]
import fs from 'fs';
import path from 'path';
import { createCanvas, loadImage } from '@napi-rs/canvas';

const [dir, out, colsArg, widthArg] = process.argv.slice(2);
const cols = Number(colsArg || 12), cw = Number(widthArg || 216);
const files = fs.readdirSync(dir).filter(n => n.endsWith('.png')).sort();
const first = await loadImage(path.join(dir, files[0]));
const ch = Math.round(cw * first.height / first.width);
const rows = Math.ceil(files.length / cols);
const sheet = createCanvas(cols * cw, rows * ch);
const g = sheet.getContext('2d');
g.imageSmoothingEnabled = false;
for (const [i, name] of files.entries()) {
  const img = await loadImage(path.join(dir, name));
  g.drawImage(img, (i % cols) * cw, Math.floor(i / cols) * ch, cw, ch);
  g.font = '14px sans-serif';
  g.fillStyle = '#ff0';
  g.fillText(name.replace(/\D/g, '').replace(/^0+/, ''), (i % cols) * cw + 3, Math.floor(i / cols) * ch + 14);
}
fs.writeFileSync(out, sheet.toBuffer('image/png'));
console.log('wrote', out, `${sheet.width}x${sheet.height}`);
