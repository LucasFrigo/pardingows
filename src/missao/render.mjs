// Reads the Blender PNG sequences, runs every frame through renderFrame and pipes it into ffmpeg with the song window:
//   node src/missao/render.mjs [out.mp4] [--no-hud]
// Internal 270x480 -> 1080x1920 (x4 nearest). The song plays for song_frames, then silence until the end.
// Blender may have rendered only every second frame for a quick animatic, in which case the nearest one is held.
import { spawn, spawnSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import ffmpeg from 'ffmpeg-static';
import { W, H, PANEL_BYTES, FULL_BYTES, renderFrame } from './video.mjs';
import { TL } from './hud.mjs';

const args = process.argv.slice(2);
const hud = !args.includes('--no-hud');
const out = args.find(a => !a.startsWith('--')) || 'out/pardos-na-missao/pardos-na-missao-tiktok.mp4';
fs.mkdirSync(path.dirname(out), { recursive: true });

const AUDIO = 'audio/' + fs.readdirSync('audio').find(n => n.startsWith(TL.audio_prefix) && n.endsWith('.wav'));
const { frames: FRAMES, song_frames: SONG, merge_frame: MERGE, fps: FPS } = TL;
const DURATION = FRAMES / FPS, SONG_S = SONG / FPS;
const DIR = 'blender/missao/frames';

// Finds frame f, or in a --step animatic the nearest one rendered, and decodes it
function load(kind, f, bytes) {
  const name = g => `${DIR}/${kind}/f_${String(g).padStart(4, '0')}.png`;
  const hit = [f, f - 1, f + 1].find(g => fs.existsSync(name(g)));
  if (!hit) throw new Error(`no ${kind} frame near ${f}`);
  const r = spawnSync(ffmpeg, ['-v', 'error', '-i', name(hit), '-f', 'rawvideo', '-pix_fmt', 'rgba', 'pipe:1'], { maxBuffer: 1 << 24 });
  if (r.stdout.length !== bytes) throw new Error(`${name(hit)} is the wrong size`);
  return r.stdout;
}

const enc = spawn(ffmpeg, [
  '-y', '-v', 'error',
  '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', `${W}x${H}`, '-r', String(FPS), '-i', 'pipe:0',
  '-ss', TL.start.toFixed(3), '-t', SONG_S.toFixed(3), '-i', AUDIO,
  '-filter_complex',
  `[0:v]scale=${W * 4}:${H * 4}:flags=neighbor,format=yuv420p[v];` +
  `[1:a]afade=t=in:d=0.008,afade=t=out:st=${(SONG_S - 0.008).toFixed(3)}:d=0.008,apad=whole_dur=${DURATION.toFixed(3)}[a]`,
  '-map', '[v]', '-map', '[a]',
  '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-maxrate', '14M', '-bufsize', '28M',
  '-profile:v', 'high', '-level', '4.2', '-r', String(FPS), '-t', DURATION.toFixed(3),
  '-c:a', 'aac', '-b:a', '256k', '-ar', '44100',
  '-movflags', '+faststart', out,
], { stdio: ['pipe', 'inherit', 'inherit'] });
const done = new Promise((res, rej) => enc.on('close', code => (code ? rej(new Error(`ffmpeg exited ${code}`)) : res())));

const t0 = Date.now();
for (let i = 0; i < FRAMES; i++) {
  const f = i + 1, v = i / FPS;
  const frame = f <= MERGE
    ? renderFrame(load('story', f, PANEL_BYTES), load('run', f, PANEL_BYTES), v, { hud })
    : renderFrame(load('end', f, FULL_BYTES), null, v, { hud });
  if (!enc.stdin.write(Buffer.from(frame))) await new Promise(r => enc.stdin.once('drain', r));
  if (i % 30 === 0) process.stdout.write(`\rframe ${i}/${FRAMES}`);
}
enc.stdin.end();
await done;
console.log(`\rrendered ${FRAMES} frames in ${((Date.now() - t0) / 1000).toFixed(1)}s -> ${out}`);
