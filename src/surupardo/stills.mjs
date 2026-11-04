// Contact sheet of frames for review: node src/surupardo/stills.mjs [out.png] [t1 t2 ...]
// With no times, samples the whole video every 0.5s.
import fs from 'fs';
import path from 'path';
import { Surface, W, H } from '../shared/engine.mjs';
import { renderFrame } from './video.mjs';
import { DURATION } from './timeline.mjs';
import { encodePNG } from '../shared/png.mjs';

const [out = 'out/surupardo/sheet.png', ...ts] = process.argv.slice(2);
const times = ts.length ? ts.map(Number) : Array.from({ length: Math.ceil(DURATION / 0.5) }, (_, i) => i * 0.5);
const Z = 2, COLS = Math.min(6, times.length), GAP = 4;
const rows = Math.ceil(times.length / COLS);
const sheet = new Surface(COLS * (W * Z + GAP), rows * (H * Z + GAP));
sheet.clear(0xff202020);

times.forEach((t, i) => {
  const f = renderFrame(t);
  const ox = (i % COLS) * (W * Z + GAP), oy = Math.floor(i / COLS) * (H * Z + GAP);
  sheet.draw(f, ox, oy, { scale: Z });
});
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, encodePNG(sheet.w, sheet.h, Buffer.from(sheet.px.buffer)));
console.log(`${out}: ${times.map(t => t.toFixed(2)).join(' ')}`);
