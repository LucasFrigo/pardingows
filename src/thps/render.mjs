// Reads the Blender PNG sequence, runs every frame through renderFrame and pipes it into ffmpeg
// with the song window:
//   node src/thps/render.mjs [out.mp4] [--no-hud]
// Internal 270x480 -> 1080x1920 (x4 nearest). Audio gets 8 ms edge fades only, as in the riso video.
import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';
import ffmpeg from 'ffmpeg-static';
import { W, H, FRAME_BYTES, renderFrame } from './video.mjs';
import { TL } from './hud.mjs';

const args = process.argv.slice(2);
const hud = !args.includes('--no-hud');
const out = args.find(a => !a.startsWith('--')) || 'out/a-solucao/a-solucao-tiktok.mp4';
fs.mkdirSync(path.dirname(out), { recursive: true });

const AUDIO = 'audio/' + fs.readdirSync('audio').find(n => n.startsWith(TL.audio_prefix) && n.endsWith('.wav'));
const FRAMES = TL.frames, FPS = TL.fps, DURATION = FRAMES / FPS;

const dec = spawn(ffmpeg, ['-v', 'error', '-framerate', String(FPS), '-start_number', '1', '-i', 'blender/solucao/frames/f_%04d.png',
  '-frames:v', String(FRAMES), '-f', 'rawvideo', '-pix_fmt', 'rgba', 'pipe:1'], { stdio: ['ignore', 'pipe', 'inherit'] });

const enc = spawn(ffmpeg, [
  '-y', '-v', 'error',
  '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', `${W}x${H}`, '-r', String(FPS), '-i', 'pipe:0',
  '-ss', TL.start.toFixed(3), '-t', DURATION.toFixed(3), '-i', AUDIO,
  '-filter_complex',
  `[0:v]scale=${W * 4}:${H * 4}:flags=neighbor,format=yuv420p[v];` +
  `[1:a]afade=t=in:d=0.008,afade=t=out:st=${(DURATION - 0.008).toFixed(3)}:d=0.008[a]`,
  '-map', '[v]', '-map', '[a]',
  '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-maxrate', '14M', '-bufsize', '28M',
  '-profile:v', 'high', '-level', '4.2', '-r', String(FPS),
  '-c:a', 'aac', '-b:a', '256k', '-ar', '44100',
  '-movflags', '+faststart', out,
], { stdio: ['pipe', 'inherit', 'inherit'] });
const done = new Promise((res, rej) => enc.on('close', code => (code ? rej(new Error(`ffmpeg exited ${code}`)) : res())));

const t0 = Date.now();
let pending = Buffer.alloc(0), i = 0;
for await (const chunk of dec.stdout) {
  pending = pending.length ? Buffer.concat([pending, chunk]) : chunk;
  while (pending.length >= FRAME_BYTES) {
    const frame = renderFrame(pending.subarray(0, FRAME_BYTES), i / FPS, { hud });
    pending = pending.subarray(FRAME_BYTES);
    if (!enc.stdin.write(Buffer.from(frame))) await new Promise(r => enc.stdin.once('drain', r));
    if (i % 30 === 0) process.stdout.write(`\rframe ${i}/${FRAMES}`);
    i++;
  }
}
enc.stdin.end();
await done;
if (i !== FRAMES) throw new Error(`expected ${FRAMES} frames, got ${i}`);
console.log(`\rrendered ${i} frames in ${((Date.now() - t0) / 1000).toFixed(1)}s -> ${out}`);
