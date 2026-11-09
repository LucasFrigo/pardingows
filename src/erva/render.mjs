// Composites the video and pipes it into ffmpeg with the window's audio (blender/erva/sync/mix.wav):
//   node src/erva/render.mjs [out.mp4] [--no-ui] [--frames dir]   finished video from Blender's PNGs. Frames are drawn on twos,
//                                                                 so a missing frame holds the latest one rendered before it.
//   node src/erva/render.mjs --proof [out.mp4]                    lyric proof: the bouncing ball, beat dots and readout on plain sepia
// Captions are drawn here, so caption and sync fixes need no re-render. Writes <out>.boxes.json for sync/check.py.
import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import ffmpeg from 'ffmpeg-static';
import { createCanvas, loadImage } from '@napi-rs/canvas';
import { TL, W, H, FPS, drawUI, wordBoxes, frameOf, activeCard } from './ui.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const args = process.argv.slice(2);
const proof = args.includes('--proof');
const ui = !args.includes('--no-ui');
const fi = args.indexOf('--frames');
const DIR = fi >= 0 ? path.resolve(args[fi + 1]) : path.join(ROOT, 'blender/erva/frames');
const pos = args.filter((a, i) => !a.startsWith('--') && !(fi >= 0 && i === fi + 1));
const fallback = proof ? 'out/pardao-erva/pardao-e-a-erva-proof.mp4'
  : ui ? 'out/pardao-erva/pardao-e-a-erva-tiktok.mp4' : 'out/pardao-erva/pardao-e-a-erva-tiktok-sem-legenda.mp4';
const out = path.resolve(pos[0] || path.join(ROOT, fallback));
fs.mkdirSync(path.dirname(out), { recursive: true });

const MIX = path.join(ROOT, TL.mix);
if (!fs.existsSync(MIX)) throw new Error(`no mix at ${MIX}: run src/erva/sync/mix.py`);
const FRAMES = TL.frames, DURATION = FRAMES / FPS;
const renderFrame = proof ? null : (await import('./video.mjs')).renderFrame;

const proofCanvas = createCanvas(W, H);
const ctx = proofCanvas.getContext('2d');
const allSyl = TL.cards.flatMap(c => [...c.rows.flat(), ...(c.adlib || [])]).flatMap(w => w[2].map((t, k) => [w[0].split('-')[k], t]));
const beatLen = 60 / TL.bpm;

// Sepia plate per card, 8 beat dots for the 3.2 s bar (the half-time feel), and a readout so a late syllable can be named
function drawProof(v, n) {
  const song = v + TL.start;
  const idx = activeCard(n);
  const shade = idx % 2 ? '#3b3226' : '#2c251c';
  ctx.fillStyle = shade;
  ctx.fillRect(0, 0, W, H);
  const beats = (song - TL.beat0) / beatLen;
  const beat = Math.floor(beats + 1e-6);
  const phase = beats - beat;
  const inBar = ((beat % 8) + 8) % 8;
  for (let i = 0; i < 8; i++) {
    const on = inBar === i;
    const r = on ? 30 + 20 * (1 - Math.min(1, phase * 2.5)) : 20;
    ctx.fillStyle = on ? (i === 0 ? '#f2d38a' : '#fbf5e6') : 'rgba(251,245,230,.25)';
    ctx.beginPath();
    ctx.arc(155 + i * 110, 640, r, 0, Math.PI * 2);
    ctx.fill();
  }
  const card = TL.cards[idx];
  ctx.fillStyle = '#fbf5e6';
  ctx.textAlign = 'center';
  ctx.font = '76px Limelight';
  ctx.fillText(`${idx + 1}. ${card.moment.toUpperCase()}`, W / 2, 330);
  ctx.font = '44px Alfa';
  const bar = Math.floor(beat / 8) + 1;
  ctx.fillText(`compasso ${bar}/17 · tempo ${inBar + 1}`, W / 2, 430);
  ctx.font = '40px Alfa';
  ctx.fillText(`música ${song.toFixed(2)} s · quadro ${n + 1}`, W / 2, 500);
  let cur = null;
  for (const s of allSyl) if (frameOf(s[1]) <= n) cur = s;
  if (cur && n - frameOf(cur[1]) < 12) {
    ctx.font = '84px Alfa';
    ctx.fillText(`${cur[0]}  ${cur[1].toFixed(2)}`, W / 2, 880);
  }
  if (card.moment === 'fim') {
    ctx.font = '220px Limelight';
    ctx.fillText('FIM', W / 2, 1400);
  }
  ctx.textAlign = 'left';
}

// Blender's frame f, or the latest one rendered before it
const onDisk = proof ? [] : fs.readdirSync(DIR).filter(n => /^f_\d+\.png$/.test(n)).map(n => Number(n.match(/\d+/)[0])).sort((a, b) => a - b);
if (!proof && !onDisk.length) throw new Error(`no frames in ${DIR}`);
if (!proof) console.log(`${onDisk.length} of ${FRAMES} frames on disk`);
const META = proof || !fs.existsSync(path.join(DIR, 'frames.json')) ? {} : JSON.parse(fs.readFileSync(path.join(DIR, 'frames.json'), 'utf8'));
let cursor = 0;
function latest(f) {
  while (cursor + 1 < onDisk.length && onDisk[cursor + 1] <= f) cursor++;
  return onDisk[cursor];
}

const enc = spawn(ffmpeg, [
  '-y', '-v', 'error',
  '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', `${W}x${H}`, '-r', String(FPS), '-i', 'pipe:0',
  '-ss', (TL.start - TL.mix_t0).toFixed(3), '-t', DURATION.toFixed(3), '-i', MIX,
  '-filter_complex', `[0:v]format=yuv420p[v];[1:a]afade=t=in:d=0.003[a]`,
  '-map', '[v]', '-map', '[a]',
  '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-maxrate', '14M', '-bufsize', '28M',
  '-profile:v', 'high', '-level', '4.2', '-r', String(FPS), '-t', DURATION.toFixed(3),
  '-c:a', 'aac', '-b:a', '256k', '-ar', '44100',
  '-movflags', '+faststart', out,
], { stdio: ['pipe', 'inherit', 'inherit'] });
const done = new Promise((res, rej) => enc.on('close', code => (code ? rej(new Error(`ffmpeg exited ${code}`)) : res())));

const t0 = Date.now();
let lastImg = null, lastNum = -1;
for (let i = 0; i < FRAMES; i++) {
  const v = i / FPS;
  let data;
  if (proof) {
    drawProof(v, i);
    if (ui) drawUI(ctx, v);
    data = ctx.getImageData(0, 0, W, H).data;
  } else {
    const n = latest(i + 1);
    if (n !== lastNum) {
      lastImg = await loadImage(path.join(DIR, `f_${String(n).padStart(4, '0')}.png`));
      lastNum = n;
    }
    data = renderFrame(lastImg, v, { ui, pts: META[lastNum]?.pts || {}, frame: i, fresh: n === i + 1 });
  }
  if (!enc.stdin.write(Buffer.from(data.buffer, data.byteOffset, data.byteLength))) await new Promise(r => enc.stdin.once('drain', r));
  if (i % 24 === 0) process.stdout.write(`\rframe ${i}/${FRAMES}`);
}
enc.stdin.end();
await done;

fs.writeFileSync(out.replace(/\.mp4$/, '.boxes.json'), JSON.stringify({ start: TL.start, fps: FPS, frames: FRAMES, mix_t0: TL.mix_t0, boxes: wordBoxes(ctx) }));
console.log(`\rrendered ${FRAMES} frames in ${((Date.now() - t0) / 1000).toFixed(1)}s -> ${out}`);
