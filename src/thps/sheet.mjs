// Builds a contact sheet from Blender frames: node src/thps/sheet.mjs out.png cols scale frame frame ...
import { spawnSync } from 'child_process';
import ffmpeg from 'ffmpeg-static';

const [out, cols, scale, ...frames] = process.argv.slice(2);
const c = Number(cols);
const inputs = frames.flatMap(f => ['-i', `blender/solucao/frames/f_${String(f).padStart(4, '0')}.png`]);
const rows = Math.ceil(frames.length / c);
let graph = '';
const rowNames = [];
for (let r = 0; r < rows; r++) {
  const idx = frames.map((_, i) => i).slice(r * c, (r + 1) * c);
  const pads = [...idx];
  let labels = pads.map(i => `[${i}]`).join('');
  // pad a short last row so vstack widths match
  while (labels.split('[').length - 1 < c) labels += '[pad]';
  const count = labels.split('[').length - 1;
  if (labels.includes('[pad]')) {
    const missing = c - idx.length;
    graph += `color=c=black:s=270x480:d=1,split=${missing}${Array.from({ length: missing }, (_, k) => `[p${k}]`).join('')};`;
    labels = pads.map(i => `[${i}]`).join('') + Array.from({ length: missing }, (_, k) => `[p${k}]`).join('');
  }
  graph += `${labels}hstack=${count}[r${r}];`;
  rowNames.push(`[r${r}]`);
}
graph += rows > 1 ? `${rowNames.join('')}vstack=${rows},` : `${rowNames[0]}`;
graph += `scale=iw*${scale}:ih*${scale}:flags=neighbor,format=rgb24`;
const r = spawnSync(ffmpeg, ['-y', '-v', 'error', ...inputs, '-filter_complex', graph, '-frames:v', '1', out], { stdio: 'inherit' });
process.exit(r.status);
