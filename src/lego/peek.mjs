// Composites a folder of rendered spot frames (f_NNNN.png) with the overlays and captions, as the final video would, and tiles them.
//   node src/lego/peek.mjs blender/lego/frames_test [out.png]
import fs from 'fs';
import path from 'path';
import { createCanvas, loadImage, ImageData } from '@napi-rs/canvas';
import { W, H, FPS } from './ui.mjs';
import { renderFrame } from './video.mjs';

const dir = path.resolve(process.argv[2]);
const out = path.resolve(process.argv[3] || 'blender/lego/review/06-espia.png');
const files = fs.readdirSync(dir).filter(n => /^f_\d+\.png$/.test(n)).sort();
const TW = 270, TH = 480, C = Math.min(files.length, 9);
const sheet = createCanvas(C * TW, Math.ceil(files.length / C) * TH);
const s = sheet.getContext('2d');
const frame = createCanvas(W, H);
const fctx = frame.getContext('2d');
for (const [i, name] of files.entries()) {
  const f = Number(name.match(/\d+/)[0]);
  const data = renderFrame(await loadImage(path.join(dir, name)), (f - 1) / FPS);
  fctx.putImageData(new ImageData(new Uint8ClampedArray(data), W, H), 0, 0);
  s.drawImage(frame, (i % C) * TW, Math.floor(i / C) * TH, TW, TH);
  s.fillStyle = '#ff0';
  s.font = '20px sans-serif';
  s.fillText(String(f), (i % C) * TW + 6, Math.floor(i / C) * TH + 22);
}
fs.writeFileSync(out, sheet.toBuffer('image/png'));
console.log('wrote', out);
