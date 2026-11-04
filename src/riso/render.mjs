// Renders every frame and pipes it into ffmpeg with the song window:
//   node src/riso/render.mjs [out.mp4] [--no-subs]
// Internal 540x960 -> 1080x1920 (x2). Audio gets 8 ms edge fades only, so the loop seam stays tight.
import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';
import ffmpeg from 'ffmpeg-static';
import { W, H, SCALE } from './engine.mjs';
import { renderFrame } from './video.mjs';
import { AUDIO_FILE, SONG_START, DURATION, FPS } from './timeline.mjs';

const args = process.argv.slice(2);
const subs = !args.includes('--no-subs');
const out = args.find(a => !a.startsWith('--')) || (subs ? 'out/vida-de-pardo/vida-de-pardo-tiktok.mp4' : 'out/vida-de-pardo/vida-de-pardo-tiktok-sem-legenda.mp4');
fs.mkdirSync(path.dirname(out), { recursive: true });
const frames = Math.round(DURATION * FPS);

const ff = spawn(ffmpeg, [
  '-y', '-v', 'error',
  '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', `${W}x${H}`, '-r', String(FPS), '-i', 'pipe:0',
  '-ss', SONG_START.toFixed(3), '-t', DURATION.toFixed(3), '-i', AUDIO_FILE,
  '-filter_complex',
  `[0:v]scale=${W * SCALE}:${H * SCALE}:flags=lanczos,format=yuv420p[v];` +
  `[1:a]afade=t=in:d=0.008,afade=t=out:st=${(DURATION - 0.008).toFixed(3)}:d=0.008[a]`,
  '-map', '[v]', '-map', '[a]',
  // the paper grain changes every 2 frames; cap the bitrate so it doesn't eat ~80 Mbps
  '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-maxrate', '12M', '-bufsize', '24M',
  '-profile:v', 'high', '-level', '4.2', '-r', String(FPS),
  '-c:a', 'aac', '-b:a', '256k', '-ar', '44100',
  '-movflags', '+faststart', '-shortest', out,
], { stdio: ['pipe', 'inherit', 'inherit'] });

const done = new Promise((res, rej) => ff.on('close', code => (code ? rej(new Error(`ffmpeg exited ${code}`)) : res())));
const t0 = Date.now();
for (let i = 0; i < frames; i++) {
  const f = renderFrame(i / FPS, { subs });
  if (!ff.stdin.write(Buffer.from(f))) await new Promise(r => ff.stdin.once('drain', r));
  if (i % 30 === 0) process.stdout.write(`\rframe ${i}/${frames}`);
}
ff.stdin.end();
await done;
console.log(`\rrendered ${frames} frames in ${((Date.now() - t0) / 1000).toFixed(1)}s -> ${out}`);
