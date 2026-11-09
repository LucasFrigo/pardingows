// Runs Blender stills through the same PS1 pass and captions as the video, side by side on one sheet.
//   node src/zombies/stills.mjs [in_dir] [out.png]
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { createCanvas, loadImage } from '@napi-rs/canvas';
import { compose } from './video.mjs';
import { W, H, TL } from './ui.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const dir = path.resolve(process.argv[2] || path.join(ROOT, 'blender/zombies/frames/stills'));
const out = path.resolve(process.argv[3] || path.join(ROOT, 'blender/zombies/review/04-look.png'));
const files = fs.readdirSync(dir).filter(n => n.endsWith('.png')).sort();
const SCALE = 0.5, CW = W * SCALE, CH = H * SCALE;
const sheet = createCanvas(CW * files.length, CH);
const g = sheet.getContext('2d');
g.imageSmoothingEnabled = false;

// A caption from the matching part of the song, so the text strip is judged against the picture
const LINES = [1, 5, 7, 18];
for (const [i, name] of files.entries()) {
  const img = await loadImage(path.join(dir, name));
  const line = TL.lines[LINES[i] ?? 0];
  const v = line.words.at(-1)[1] - TL.start + 0.05;
  g.drawImage(compose(img, v), i * CW, 0, CW, CH);
}
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, sheet.toBuffer('image/png'));
console.log('wrote', out, `${sheet.width}x${sheet.height}`);
