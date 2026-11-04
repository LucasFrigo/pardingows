// Contact sheet of rendered frames, with the frame number and the caption UI on top:
//   node src/feliz/stills.mjs [frames dir] [out.png] [columns] [--no-ui]
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { createCanvas, loadImage } from '@napi-rs/canvas';
import { TL, W, H, FPS, drawUI } from './ui.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const args = process.argv.slice(2);
const ui = !args.includes('--no-ui');
const pos = args.filter(a => !a.startsWith('--'));
const dir = pos[0] || path.join(ROOT, 'blender/feliz/frames');
const out = pos[1] || path.join(ROOT, 'blender/feliz/review/sheet.png');
const COLS = Number(pos[2] || 10);

const files = fs.readdirSync(dir).filter(n => /^f_\d+\.png$/.test(n)).sort();
const TW = 216, TH = 384;
const rows = Math.ceil(files.length / COLS);
const sheet = createCanvas(COLS * TW, rows * TH);
const s = sheet.getContext('2d');
const full = createCanvas(W, H);
const c = full.getContext('2d');
for (const [i, n] of files.entries()) {
  const f = Number(n.match(/\d+/)[0]);
  const img = await loadImage(path.join(dir, n));
  c.imageSmoothingQuality = 'high';
  c.drawImage(img, 0, 0, W, H);
  if (ui) drawUI(c, (f - 1) / FPS);
  const x = (i % COLS) * TW, y = Math.floor(i / COLS) * TH;
  s.drawImage(full, x, y, TW, TH);
  s.fillStyle = 'rgba(0,0,0,.65)';
  s.fillRect(x, y, 82, 24);
  s.fillStyle = '#fff';
  s.font = '18px Fredoka';
  s.fillText(`f${f} ${((f - 1) / FPS + TL.start).toFixed(1)}`, x + 4, y + 18);
}
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, sheet.toBuffer('image/png'));
console.log('wrote', out, `${sheet.width}x${sheet.height}, ${files.length} frames`);
