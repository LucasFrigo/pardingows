// Contact sheet of frames for review: node src/riso/stills.mjs [out.png] [t1 t2 ...] [--no-subs]
// With no times, samples the key moments of the video.
import fs from 'fs';
import path from 'path';
import { W, H } from './engine.mjs';
import { renderFrame } from './video.mjs';
import { encodePNG } from '../shared/png.mjs';

const KEY = [0, 0.7, 1.4, 2.2, 2.9, 3.5, 4.2, 5.0, 5.6, 6.7, 7.5, 8.3, 8.95, 9.6, 10.1, 10.25,
  11.0, 12.1, 13.1, 13.9, 15.1, 15.8, 16.8, 18.3, 19.5, 20.0, 20.6, 21.3, 21.6, 21.9, 22.1, 22.6, 23.4, 23.85, 24.1, 24.7];
const argv = process.argv.slice(2), subs = !argv.includes('--no-subs');
const [out = 'out/vida-de-pardo/vida-sheet.png', ...ts] = argv.filter(a => a !== '--no-subs');
const times = ts.length ? ts.map(Number) : KEY;
const Z = 0.5, COLS = Math.min(6, times.length), GAP = 6;
const tw = W * Z, th = H * Z;
const rows = Math.ceil(times.length / COLS);
const sw = COLS * (tw + GAP), sh = rows * (th + GAP);
const sheet = Buffer.alloc(sw * sh * 4, 30);

times.forEach((t, i) => {
  const f = renderFrame(t, { subs });
  const ox = (i % COLS) * (tw + GAP), oy = Math.floor(i / COLS) * (th + GAP);
  // 2x2 box filter down to half size
  for (let y = 0; y < th; y++)
    for (let x = 0; x < tw; x++) {
      const d = ((oy + y) * sw + ox + x) * 4;
      for (let c = 0; c < 3; c++) {
        const s = (yy, xx) => f[((y * 2 + yy) * W + x * 2 + xx) * 4 + c];
        sheet[d + c] = (s(0, 0) + s(0, 1) + s(1, 0) + s(1, 1)) >> 2;
      }
      sheet[d + 3] = 255;
    }
});
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, encodePNG(sw, sh, sheet));
console.log(`${out}: ${times.map(t => t.toFixed(2)).join(' ')}`);
