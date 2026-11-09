// Contact sheet of the finished look: frames through the whole Node pipeline (film pass, gags, cards, captions).
//   node src/erva/stills.mjs [out.png] [--frames dir] [--no-ui] [f1 f2 ...]
// Default: three frames per moment (start, middle, end of each cut) from blender/erva/frames.
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { createCanvas, loadImage, ImageData } from '@napi-rs/canvas';
import { TL, FPS, W, H } from './ui.mjs';
import { renderFrame } from './video.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const args = process.argv.slice(2);
const fi = args.indexOf('--frames');
const DIR = fi >= 0 ? path.resolve(args[fi + 1]) : path.join(ROOT, 'blender/erva/frames');
const ui = !args.includes('--no-ui');
const pos = args.filter((a, i) => !a.startsWith('--') && !(fi >= 0 && i === fi + 1));
const out = pos.find(a => a.endsWith('.png')) || path.join(ROOT, 'blender/erva/review/05-contato.png');
let wanted = pos.filter(a => /^\d+$/.test(a)).map(Number);
const onDisk = fs.readdirSync(DIR).filter(n => /^f_\d+\.png$/.test(n)).map(n => Number(n.match(/\d+/)[0])).sort((a, b) => a - b);
const META = fs.existsSync(path.join(DIR, 'frames.json')) ? JSON.parse(fs.readFileSync(path.join(DIR, 'frames.json'), 'utf8')) : {};
if (!wanted.length) {
  const cuts = TL.shots.map(s => s.t).concat([TL.start + TL.frames / FPS]);
  for (let i = 0; i < cuts.length - 1; i++) {
    for (const k of [0.15, 0.5, 0.88]) wanted.push(Math.round((cuts[i] + (cuts[i + 1] - cuts[i]) * k - TL.start) * FPS) + 1);
  }
  wanted.push(Math.round((TL.shots[TL.shots.length - 1].t + 1 - TL.start) * FPS) + 1);
}
const latest = f => onDisk.filter(n => n <= f).pop() ?? onDisk[0];
const TW = 270, TH = 480, COLS = 12;
const rows = Math.ceil(wanted.length / COLS);
const sheet = createCanvas(COLS * TW, rows * (TH + 30));
const sctx = sheet.getContext('2d');
sctx.fillStyle = '#111';
sctx.fillRect(0, 0, sheet.width, sheet.height);
const frameCanvas = createCanvas(W, H);
const fctx = frameCanvas.getContext('2d');
for (const [k, f] of wanted.entries()) {
  const n = latest(f);
  const img = n ? await loadImage(path.join(DIR, `f_${String(n).padStart(4, '0')}.png`)) : null;
  const data = renderFrame(img, (f - 1) / FPS, { ui, pts: META[n]?.pts || {}, frame: f - 1 });
  fctx.putImageData(new ImageData(new Uint8ClampedArray(data), W, H), 0, 0);
  const x = (k % COLS) * TW, y = Math.floor(k / COLS) * (TH + 30);
  sctx.drawImage(frameCanvas, x, y, TW, TH);
  sctx.fillStyle = '#ddd';
  sctx.font = '20px sans-serif';
  sctx.fillText(`${f} ${META[n]?.moment || ''} ${(TL.start + (f - 1) / FPS).toFixed(2)}`, x + 6, y + TH + 22);
}
fs.writeFileSync(out, sheet.toBuffer('image/png'));
console.log('wrote', out, wanted.length, 'frames');
