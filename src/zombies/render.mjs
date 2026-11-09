// Composites the video and pipes it into ffmpeg with the censored mix:
//   node src/zombies/render.mjs [out.mp4] [--no-ui] [--frames dir]   finished video from Blender's PNGs. An animatic with gaps holds the nearest frame.
//   node src/zombies/render.mjs --proof [out.mp4]                    lyric proof: captions, bleeps, beat marker and gag markers over black
// The song plays for song_frames, then silence until frames. Writes <out>.boxes.json for sync/check.py.
import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import ffmpeg from 'ffmpeg-static';
import { createCanvas } from '@napi-rs/canvas';
import { TL, W, H, FPS, drawUI, wordBoxes, frameOf } from './ui.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const args = process.argv.slice(2);
const proof = args.includes('--proof');
const ui = !args.includes('--no-ui');
const fi = args.indexOf('--frames');
const DIR = fi >= 0 ? path.resolve(args[fi + 1]) : path.join(ROOT, 'blender/zombies/frames');
const pos = args.filter((a, i) => !a.startsWith('--') && !(fi >= 0 && i === fi + 1));
const fallback = proof ? 'out/pardos-vs-zombies/pardos-vs-zombies-proof.mp4' : 'out/pardos-vs-zombies/pardos-vs-zombies-tiktok.mp4';
const out = path.resolve(pos[0] || path.join(ROOT, fallback));
fs.mkdirSync(path.dirname(out), { recursive: true });

const MIX = path.join(ROOT, TL.mix);
if (!fs.existsSync(MIX)) throw new Error(`no censored mix at ${MIX}: run src/zombies/sync/bleep.py`);
const FRAMES = TL.frames, DURATION = FRAMES / FPS, SONG_S = TL.song_frames / FPS;

const proofCanvas = createCanvas(W, H);
const ctx = proofCanvas.getContext('2d', { alpha: false });
const allWords = TL.lines.flatMap(l => l.words);
const beatLen = 60 / TL.bpm;

// Beat dots, a readout and the gag markers, so a late word can be reported by its number
function drawProof(v, f) {
  const song = v + TL.start;
  ctx.fillStyle = '#10130f';
  ctx.fillRect(0, 0, W, H);
  const beats = (song - TL.beat0) / beatLen;
  const beat = Math.floor(beats + 1e-6);
  const phase = beats - beat;
  for (let i = 0; i < 4; i++) {
    const on = ((beat % 4) + 4) % 4 === i;
    const r = on ? 44 + 26 * (1 - Math.min(1, phase * 2.5)) : 30;
    ctx.fillStyle = on ? (i === 0 ? '#c8261a' : '#f2f2ea') : 'rgba(242,242,234,.25)';
    ctx.beginPath();
    ctx.arc(240 + i * 200, 900, r, 0, Math.PI * 2);
    ctx.fill();
  }
  let cur = allWords[0];
  for (const w of allWords) if (frameOf(w[1]) <= f - 1) cur = w;
  ctx.fillStyle = '#f2f2ea';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'alphabetic';
  ctx.font = '56px VT323';
  ctx.fillText(`música ${song.toFixed(2)} s · quadro ${f}`, W / 2, 1040);
  ctx.font = '96px VT323';
  ctx.fillText(`${cur[0].replace('#', '_')}  ${cur[1].toFixed(2)}`, W / 2, 1170);

  for (const g of TL.gags) {
    const [a, z] = g.bleep;
    if (song >= a - 0.005 && song < z + 0.005) {
      ctx.fillStyle = '#e0261a';
      ctx.fillRect(0, 1440, W, 120);
      ctx.fillStyle = '#fff';
      ctx.font = '96px VT323';
      ctx.fillText(`BIP  ${g.word}`, W / 2, 1530);
    }
    const dt = song - g.t;
    if (g.full && song >= g.full[0] && song < g.full[1]) {
      ctx.strokeStyle = '#e0261a';
      ctx.lineWidth = 8;
      ctx.strokeRect(20, 20, W - 40, 780);
      ctx.fillStyle = '#e0261a';
      ctx.font = '64px VT323';
      ctx.fillText('ZUMBI: TELA CHEIA', W / 2, 420);
    } else if (g.window && dt >= 0 && dt < g.window) {
      ctx.strokeStyle = '#f2f2ea';
      ctx.lineWidth = 8;
      ctx.strokeRect(44, 240, 360, 360);
      ctx.fillStyle = '#f2f2ea';
      ctx.font = '48px VT323';
      ctx.fillText('ZUMBI', 224, 430);
    }
  }
  if (f - 1 >= TL.song_frames) {
    ctx.fillStyle = '#c8261a';
    ctx.font = '128px VT323';
    ctx.fillText('VOCÊ MORREU', W / 2, 700);
  }
  ctx.textAlign = 'left';
}

const enc = spawn(ffmpeg, [
  '-y', '-v', 'error',
  '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', `${W}x${H}`, '-r', String(FPS), '-i', 'pipe:0',
  '-ss', (TL.start - TL.mix_t0).toFixed(3), '-t', SONG_S.toFixed(3), '-i', MIX,
  '-filter_complex', `[0:v]format=yuv420p[v];[1:a]afade=t=in:d=0.003,afade=t=out:st=${(SONG_S - 0.008).toFixed(3)}:d=0.008,apad=whole_dur=${DURATION.toFixed(3)}[a]`,
  '-map', '[v]', '-map', '[a]',
  '-c:v', 'libx264', '-preset', proof ? 'veryfast' : 'slow', '-crf', '17', '-maxrate', '14M', '-bufsize', '28M',
  '-profile:v', 'high', '-level', '4.2', '-r', String(FPS), '-t', DURATION.toFixed(3),
  '-c:a', 'aac', '-b:a', '256k', '-ar', '44100',
  '-movflags', '+faststart', out,
], { stdio: ['pipe', 'inherit', 'inherit'] });
const done = new Promise((res, rej) => enc.on('close', code => (code ? rej(new Error(`ffmpeg exited ${code}`)) : res())));

const renderFrame = proof ? null : (await import('./video.mjs')).renderFrame;
const t0 = Date.now();
for (let i = 0; i < FRAMES; i++) {
  const v = i / FPS;
  let data;
  if (proof) {
    drawProof(v, i + 1);
    drawUI(ctx, v);
    data = ctx.getImageData(0, 0, W, H).data;
  } else {
    data = await renderFrame(DIR, i + 1, v, { ui });
  }
  if (!enc.stdin.write(Buffer.from(data.buffer, data.byteOffset, data.byteLength))) await new Promise(r => enc.stdin.once('drain', r));
  if (i % 30 === 0) process.stdout.write(`\rframe ${i}/${FRAMES}`);
}
enc.stdin.end();
await done;

fs.writeFileSync(out.replace(/\.mp4$/, '.boxes.json'), JSON.stringify({ start: TL.start, fps: FPS, frames: FRAMES, song_frames: TL.song_frames, mix_t0: TL.mix_t0, boxes: wordBoxes(ctx), gags: TL.gags }));
console.log(`\rrendered ${FRAMES} frames in ${((Date.now() - t0) / 1000).toFixed(1)}s -> ${out}`);
