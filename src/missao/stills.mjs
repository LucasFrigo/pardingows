// Contact sheet of finished frames, through the real panels, colour pass and HUD. Missing frames stay black.
//   node src/missao/stills.mjs out.png cols frame frame ...
import { spawnSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import ffmpeg from 'ffmpeg-static';
import { W, H, PANEL_BYTES, FULL_BYTES, renderFrame } from './video.mjs';
import { TL } from './hud.mjs';
import { encodePNG } from '../shared/png.mjs';

const [out, colsArg, ...list] = process.argv.slice(2);
const cols = Number(colsArg), frames = list.map(Number);
const DIR = 'blender/missao/frames';

function load(file, bytes) {
  if (!fs.existsSync(file)) return Buffer.alloc(bytes);
  const r = spawnSync(ffmpeg, ['-v', 'error', '-i', file, '-f', 'rawvideo', '-pix_fmt', 'rgba', 'pipe:1'], { maxBuffer: 1 << 24 });
  return r.stdout;
}

const rows = Math.ceil(frames.length / cols);
const sheetW = cols * W + (cols - 1) * 2, sheetH = rows * H + (rows - 1) * 2;
const sheet = Buffer.alloc(sheetW * sheetH * 4, 40);
frames.forEach((f, i) => {
  const name = `f_${String(f).padStart(4, '0')}.png`;
  const v = (f - 1) / TL.fps;
  const px = f <= TL.merge_frame
    ? renderFrame(load(`${DIR}/story/${name}`, PANEL_BYTES), load(`${DIR}/run/${name}`, PANEL_BYTES), v)
    : renderFrame(load(`${DIR}/end/${name}`, FULL_BYTES), null, v);
  const ox = (i % cols) * (W + 2), oy = Math.floor(i / cols) * (H + 2);
  for (let y = 0; y < H; y++) Buffer.from(px.buffer, px.byteOffset + y * W * 4, W * 4).copy(sheet, ((oy + y) * sheetW + ox) * 4);
});
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, encodePNG(sheetW, sheetH, sheet));
console.log('wrote', out, `${sheetW}x${sheetH}`);
