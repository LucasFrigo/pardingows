// Renders every frame and pipes it into ffmpeg with the chorus audio:
//   node src/surupardo/render.mjs [out.mp4]
import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';
import ffmpeg from 'ffmpeg-static';
import { W, H, SCALE } from '../shared/engine.mjs';
import { renderFrame } from './video.mjs';
import { AUDIO_FILE, SONG_START, DURATION, FPS } from './timeline.mjs';

const out = process.argv[2] || 'out/surupardo/surupardo-tiktok.mp4';
fs.mkdirSync(path.dirname(out), { recursive: true });
const frames = Math.round(DURATION * FPS);

const ff = spawn(ffmpeg, [
  '-y', '-v', 'error',
  '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', `${W}x${H}`, '-r', String(FPS), '-i', 'pipe:0',
  '-ss', String(SONG_START), '-t', String(DURATION), '-i', AUDIO_FILE,
  '-filter_complex',
  `[0:v]scale=${W * SCALE}:${H * SCALE}:flags=neighbor,format=yuv420p[v];` +
  `[1:a]afade=t=in:d=0.02,afade=t=out:st=${(DURATION - 0.04).toFixed(3)}:d=0.04[a]`,
  '-map', '[v]', '-map', '[a]',
  '-c:v', 'libx264', '-preset', 'slow', '-crf', '14', '-tune', 'animation',
  '-profile:v', 'high', '-level', '4.2', '-r', String(FPS),
  '-c:a', 'aac', '-b:a', '256k', '-ar', '44100',
  '-movflags', '+faststart', '-shortest', out,
], { stdio: ['pipe', 'inherit', 'inherit'] });

const done = new Promise((res, rej) => ff.on('close', code => (code ? rej(new Error(`ffmpeg exited ${code}`)) : res())));
const t0 = Date.now();
for (let i = 0; i < frames; i++) {
  const f = renderFrame(i / FPS);
  if (!ff.stdin.write(Buffer.from(f.px.buffer.slice(0)))) await new Promise(r => ff.stdin.once('drain', r));
  if (i % 60 === 0) process.stdout.write(`\rframe ${i}/${frames}`);
}
ff.stdin.end();
await done;
console.log(`\rrendered ${frames} frames in ${((Date.now() - t0) / 1000).toFixed(1)}s -> ${out}`);
