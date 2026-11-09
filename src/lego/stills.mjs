// Contact sheet of the world stills with their real captions on top, as a viewer sees them.
//   node src/lego/stills.mjs
// In: blender/lego/review/04-<set>.png  Out: blender/lego/review/04-mundos.png
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { createCanvas, loadImage } from '@napi-rs/canvas';
import { TL, W, H, frameOf } from './ui.mjs';
import { renderFrame } from './video.mjs';

const REVIEW = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', 'blender/lego/review');
const COLS = 4, TW = 405, TH = 720, GAP = 8;
const sheet = createCanvas(COLS * (TW + GAP) + GAP, 2 * (TH + GAP) + GAP);
const ctx = sheet.getContext('2d');
ctx.fillStyle = '#14151c';
ctx.fillRect(0, 0, sheet.width, sheet.height);
const frame = createCanvas(W, H);
const fctx = frame.getContext('2d');
for (const [i, line] of TL.lines.entries()) {
  const file = path.join(REVIEW, `04-${line.sketch}.png`);
  if (!fs.existsSync(file)) continue;
  // The line's last word is up, so the longest caption shows
  const v = (frameOf(line.words.at(-1)[1]) + 2) / TL.fps;
  const data = renderFrame(await loadImage(file), v);
  fctx.putImageData(new (globalThis.ImageData || (await import('@napi-rs/canvas')).ImageData)(new Uint8ClampedArray(data), W, H), 0, 0);
  ctx.drawImage(frame, GAP + (i % COLS) * (TW + GAP), GAP + Math.floor(i / COLS) * (TH + GAP), TW, TH);
}
fs.writeFileSync(path.join(REVIEW, '04-mundos.png'), sheet.toBuffer('image/png'));
console.log('wrote 04-mundos.png');
