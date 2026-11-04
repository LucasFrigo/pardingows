// Contact sheet of finished frames (colour pass + HUD):
//   node src/thps/stills.mjs out.png cols frame frame ...
import { spawnSync } from 'child_process';
import ffmpeg from 'ffmpeg-static';
import { W, H, renderFrame } from './video.mjs';
import { TL } from './hud.mjs';

const [out, colsArg, ...list] = process.argv.slice(2);
const cols = Number(colsArg), rows = Math.ceil(list.length / cols);
const sheet = Buffer.alloc(cols * W * rows * H * 4);
list.forEach((f, n) => {
  const r = spawnSync(ffmpeg, ['-v', 'error', '-i', `blender/solucao/frames/f_${String(f).padStart(4, '0')}.png`, '-f', 'rawvideo', '-pix_fmt', 'rgba', 'pipe:1'], { maxBuffer: 1 << 24 });
  if (r.status) throw new Error(`frame ${f}: ${r.stderr}`);
  const px = renderFrame(r.stdout, (f - 1) / TL.fps);
  const ox = (n % cols) * W, oy = Math.floor(n / cols) * H;
  for (let y = 0; y < H; y++) sheet.set(px.subarray(y * W * 4, (y + 1) * W * 4), ((oy + y) * cols * W + ox) * 4);
});
const enc = spawnSync(ffmpeg, ['-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', `${cols * W}x${rows * H}`, '-i', 'pipe:0', '-frames:v', '1', out], { input: sheet, maxBuffer: 1 << 28 });
if (enc.status) throw new Error(String(enc.stderr));
console.log(out);
