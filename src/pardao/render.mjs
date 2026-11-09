// Composites the video and pipes it into ffmpeg with the song window:
//   node src/pardao/render.mjs [out.mp4] [--no-ui] [--frames dir]   finished video from Blender's PNGs. Stepped or missing frames hold the latest one rendered.
//   node src/pardao/render.mjs --proof [out.mp4]                    lyric proof: captions, beat marker and moment name over plain colour
// Captions and HUD are drawn here, so caption and sync fixes need no re-render. Writes <out>.boxes.json for sync/check.py.
import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import ffmpeg from 'ffmpeg-static';
import { createCanvas, loadImage } from '@napi-rs/canvas';
import { TL, W, H, FPS, drawUI, wordBoxes, frameOf, activeLine } from './ui.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const args = process.argv.slice(2);
const proof = args.includes('--proof');
const ui = !args.includes('--no-ui');
const fi = args.indexOf('--frames');
const DIR = fi >= 0 ? path.resolve(args[fi + 1]) : path.join(ROOT, 'blender/pardao/frames');
const pos = args.filter((a, i) => !a.startsWith('--') && !(fi >= 0 && i === fi + 1));
const fallback = proof ? 'out/pardao-2000/pardao-2000-proof.mp4' : ui ? 'out/pardao-2000/pardao-2000-tiktok.mp4' : 'out/pardao-2000/pardao-2000-tiktok-sem-legenda.mp4';
const out = path.resolve(pos[0] || path.join(ROOT, fallback));
fs.mkdirSync(path.dirname(out), { recursive: true });

const MIX = path.join(ROOT, TL.mix);
if (!fs.existsSync(MIX)) throw new Error(`no song copy at ${MIX}: copy ${TL.audio} there`);
const FRAMES = TL.frames, DURATION = FRAMES / FPS;
const renderFrame = proof ? null : (await import('./video.mjs')).renderFrame;

const proofCanvas = createCanvas(W, H);
const ctx = proofCanvas.getContext('2d');
const BG = ['#3b4a8c', '#11131c', '#7c3b8c', '#3f7a4a', '#c0612b', '#b8323a', '#5a5f6b', '#2a2a2a',
  '#24306b', '#d4751f', '#2f7d8c', '#6b5a3a', '#4a3b8c', '#1f6b9e', '#c4a12b', '#8c4a2b', '#d9b23a'];
const allWords = TL.lines.flatMap(l => l.words);
const beatLen = 60 / TL.bpm;
const BARS = Math.round(FRAMES / FPS / (4 * beatLen));

// Beat dots and a readout, so a late word can be reported by its number
function drawProof(v, f) {
  const song = v + TL.start;
  const idx = activeLine(f - 1);
  ctx.fillStyle = BG[idx % BG.length];
  ctx.fillRect(0, 0, W, H);
  const beats = (song - TL.beat0) / beatLen;
  const beat = Math.floor(beats + 1e-6);
  const phase = beats - beat;
  for (let i = 0; i < 4; i++) {
    const on = beat % 4 === i;
    const r = on ? 44 + 26 * (1 - Math.min(1, phase * 2.5)) : 30;
    ctx.fillStyle = on ? (i === 0 ? '#ff4a3c' : '#ffffff') : 'rgba(255,255,255,.4)';
    ctx.beginPath();
    ctx.arc(240 + i * 200, 620, r, 0, Math.PI * 2);
    ctx.fill();
  }
  let cur = allWords[0];
  for (const w of allWords) if (frameOf(w[1]) <= f - 1) cur = w;
  ctx.fillStyle = '#ffffff';
  ctx.textAlign = 'center';
  ctx.font = '64px Bungee';
  ctx.fillText(`${idx + 1}. ${TL.shots[idx].moment.toUpperCase()}`, W / 2, 330);
  ctx.font = '48px Russo';
  ctx.fillText(`compasso ${Math.floor(beat / 4) + 1}/${BARS} · tempo ${(beat % 4) + 1}`, W / 2, 420);
  ctx.font = '42px Russo';
  ctx.fillText(`música ${song.toFixed(2)} s · quadro ${f}`, W / 2, 490);
  if (frameOf(cur[1]) <= f - 1) {
    ctx.font = '80px Russo';
    ctx.fillText(`${cur[0]}  ${cur[1].toFixed(2)}`, W / 2, 860);
  }
  ctx.textAlign = 'left';
}

// Blender's frame f, or the latest one rendered before it: 15 fps poses render every second frame
const onDisk = proof ? [] : fs.readdirSync(DIR).filter(n => /^f_\d+\.png$/.test(n)).map(n => Number(n.match(/\d+/)[0])).sort((a, b) => a - b);
if (!proof && !onDisk.length) throw new Error(`no frames in ${DIR}`);
if (!proof) console.log(`${onDisk.length} of ${FRAMES} frames on disk`);
const META = proof ? {} : JSON.parse(fs.readFileSync(path.join(DIR, 'frames.json'), 'utf8'));
let cursor = 0;
function latest(f) {
  while (cursor + 1 < onDisk.length && onDisk[cursor + 1] <= f) cursor++;
  return onDisk[cursor];
}

const enc = spawn(ffmpeg, [
  '-y', '-v', 'error',
  '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', `${W}x${H}`, '-r', String(FPS), '-i', 'pipe:0',
  '-ss', (TL.start - TL.mix_t0).toFixed(3), '-t', DURATION.toFixed(3), '-i', MIX,
  '-filter_complex', `[0:v]format=yuv420p[v];[1:a]afade=t=in:d=0.003,afade=t=out:st=${(DURATION - 0.008).toFixed(3)}:d=0.008[a]`,
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
    drawProof(v, i + 1);
    drawUI(ctx, v);
    data = ctx.getImageData(0, 0, W, H).data;
  } else {
    const n = latest(i + 1);
    if (n !== lastNum) {
      lastImg = await loadImage(path.join(DIR, `f_${String(n).padStart(4, '0')}.png`));
      lastNum = n;
    }
    data = renderFrame(lastImg, v, { ui, pts: META[lastNum]?.pts || {} });
  }
  if (!enc.stdin.write(Buffer.from(data.buffer, data.byteOffset, data.byteLength))) await new Promise(r => enc.stdin.once('drain', r));
  if (i % 30 === 0) process.stdout.write(`\rframe ${i}/${FRAMES}`);
}
enc.stdin.end();
await done;

fs.writeFileSync(out.replace(/\.mp4$/, '.boxes.json'), JSON.stringify({ start: TL.start, fps: FPS, frames: FRAMES, mix_t0: TL.mix_t0, boxes: wordBoxes(ctx) }));
console.log(`\rrendered ${FRAMES} frames in ${((Date.now() - t0) / 1000).toFixed(1)}s -> ${out}`);
