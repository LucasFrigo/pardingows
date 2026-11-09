// Contact sheet of finished frames (PS2 pass, HUD and captions) for review, straight from Blender's PNGs:
//   node src/pardao/stills.mjs [out.png] [--frames dir] [--no-ui] [f1 f2 ...]
// With no frame numbers it takes three frames from every moment. Each tile is labelled with its frame, moment and song time.
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { createCanvas, loadImage, GlobalFonts } from '@napi-rs/canvas';
import { TL } from './ui.mjs';
import { renderFrame } from './video.mjs';
import { CUE } from './fx.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..', '..');
GlobalFonts.registerFromPath(path.join(HERE, 'fonts', 'VT323-Regular.ttf'), 'VT323');
const args = process.argv.slice(2);
const fi = args.indexOf('--frames');
const DIR = fi >= 0 ? path.resolve(args[fi + 1]) : path.join(ROOT, 'blender/pardao/frames');
const ui = !args.includes('--no-ui');
const rest = args.filter((a, i) => !a.startsWith('--') && !(fi >= 0 && i === fi + 1));
const out = rest.find(a => a.endsWith('.png')) || path.join(ROOT, 'blender/pardao/review/05-contato.png');
let want = rest.filter(a => /^\d+$/.test(a)).map(Number);
const frameOf = t => Math.round((t - TL.start) * TL.fps) + 1;
if (!want.length) {
  const cuts = CUE.cuts.concat([CUE.end]);
  for (let i = 0; i < CUE.cuts.length; i++) for (const k of [0.2, 0.55, 0.9]) want.push(frameOf(cuts[i] + (cuts[i + 1] - cuts[i]) * k));
}
const META = JSON.parse(fs.readFileSync(path.join(DIR, 'frames.json'), 'utf8'));
const onDisk = Object.keys(META).map(Number).sort((a, b) => a - b);
const held = f => onDisk.filter(n => n <= f).pop() ?? onDisk[0];

const TW = 270, TH = 480, COLS = 6;
const rows = Math.ceil(want.length / COLS);
const sheet = createCanvas(COLS * TW, rows * (TH + 24));
const sctx = sheet.getContext('2d');
sctx.fillStyle = '#111';
sctx.fillRect(0, 0, sheet.width, sheet.height);
const tile = createCanvas(1080, 1920);
const tctx = tile.getContext('2d');
for (const [i, f] of want.entries()) {
  const n = held(f);
  const img = await loadImage(path.join(DIR, `f_${String(n).padStart(4, '0')}.png`));
  const data = renderFrame(img, (f - 1) / TL.fps, { ui, pts: META[n]?.pts || {}, fresh: true });
  const id = tctx.createImageData(1080, 1920);
  id.data.set(data);
  tctx.putImageData(id, 0, 0);
  const x = (i % COLS) * TW, y = Math.floor(i / COLS) * (TH + 24);
  sctx.drawImage(tile, x, y, TW, TH);
  sctx.fillStyle = '#ffd23f';
  sctx.font = '20px VT323';
  const t = TL.start + (f - 1) / TL.fps;
  sctx.fillText(`${f} ${META[n]?.moment + 1}.${CUE.moments[META[n]?.moment]} ${t.toFixed(2)}`, x + 3, y + TH + 18);
}
fs.writeFileSync(out, sheet.toBuffer('image/png'));
console.log('wrote', out, `${want.length} frames`);
