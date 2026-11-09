// Builds src/pardao/timeline.json from the snapped word times (blender/pardao/sync/attacks.json). Run once after attacks.py;
// after that the timeline is the source of truth and is edited by hand (re-running overwrites hand edits, so it refuses unless --force).
//   node src/pardao/sync/make_timeline.mjs [--force]
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
const OUT = path.join(ROOT, 'src/pardao/timeline.json');
if (fs.existsSync(OUT) && !process.argv.includes('--force')) throw new Error(`${OUT} exists: pass --force to overwrite hand edits`);

const BPM = 127, BEAT = 60 / BPM, BAR = 4 * BEAT;
const START = 157.574; // band hit measured on the stem, 20 ms after the fitted grid
const BARS = 17, FPS = 30;
const FRAMES = Math.round(BARS * BAR * FPS);

// One game moment per sung line (see the plan's storyboard). 'speaker' is the name tag on the dialogue box.
const MOMENTS = [
  ['card', 'PARDO'], ['apagao', 'PARDO'], ['crew', 'PARDOS'], ['baseado', 'PARDO'],
  ['banger', 'PARDO'], ['combo', 'PARDO'], ['horda', 'PARDOS'], ['muro', 'PARDOS'],
  ['continue', 'PARDO'], ['aquecimento', 'PARDOS'], ['mapa', 'PARDO'], ['perdeu', 'PARDO'],
  ['golpes', 'PARDO'], ['momento', 'PARDO'], ['sotaque', 'PARDO'], ['jumento', 'PARDO'], ['resultado', 'PARDJHONSON'],
];
// Row break per line: index of the first word on the second caption row (0 = one row)
const BRK = [3, 3, 2, 3, 3, 2, 2, 2, 2, 2, 3, 2, 2, 0, 2, 2, 0];
// Words placed by judgement instead of the snap: the aligner time is kept (see notes)
const KEEP_ALIGNER = new Set(['4:muito', '15:com']);

const { rows } = JSON.parse(fs.readFileSync(path.join(ROOT, 'blender/pardao/sync/attacks.json'), 'utf8'));
const lines = [];
for (const r of rows) {
  const t = KEEP_ALIGNER.has(`${r.line}:${r.word}`) ? r.aligner : r.t;
  (lines[r.line - 1] ||= []).push([r.word, Math.round(t * 1000) / 1000]);
}
const eighth = BEAT / 2;
const shots = lines.map((words, i) => {
  if (i === 0) return { t: START, moment: MOMENTS[0][0] };
  // The 8th note at or before the first word (one frame of slack), so a line never starts after its own first word
  const k = Math.floor((words[0][1] - START + 1 / FPS) / eighth);
  return { t: Math.round((START + k * eighth) * 1000) / 1000, moment: MOMENTS[i][0] };
});

const TL = {
  _: 'All timing lives here, read by Blender (shots) and Node (captions, HUD). Times are song seconds. Video time v = song - start, frame index n = round(v * 30). To fix a late or early word, change its number and run: npm run pardao:proof. Word times: CTC forced aligner and Whisper on the Demucs vocal stem, snapped to the vocal attack within 80 ms (src/pardao/sync/attacks.py). The notes list every word placed by judgement.',
  audio: 'audio/PARDÃO2000_2.wav',
  mix: 'blender/pardao/sync/song.wav',
  mix_t0: 0,
  start: START,
  frames: FRAMES,
  fps: FPS,
  bpm: BPM,
  beat0: START,
  notes: {
    cut: `Window ${START} to ${(START + BARS * BAR).toFixed(3)} s, exactly ${BARS} bars at ${BPM} BPM. Grid fitted on the instrumental stem (src/pardao/sync/grid.py), band hits within 39 ms of it across all bars. 16 bars would cut into 'jumento' (187.75), so the 17th bar carries the 'pardjhonson' tag. The vocal stem has wordless backing vocals across both cut points (Whisper hears no words there).`,
    '1 descobri': 'Whisper put it at 157.74, the aligner at 158.30 in every spelling variant (score 0.88 as descubri). Aligner kept; the sound from 157.58 is wordless backing.',
    '4 muito': 'No attack within 80 ms, aligner time (score 0.63).',
    '15 com': 'Aligner score 0.00 and Whisper hears only "o sotaque": possibly not sung. Aligner time kept so the caption reads as written.',
    '8 só lamento': 'Not found in the vocal stem (aligner score 0.01-0.02 between muro and então, neither Whisper pass hears it). Left out of the captions until the user says where it is.',
    shots: 'Each moment cut is the 8th note at or before (1 frame slack) the first word of the line\'s first word; the first one is the window start.',
  },
  lines: lines.map((words, i) => ({ moment: MOMENTS[i][0], speaker: MOMENTS[i][1], brk: BRK[i], words })),
  shots,
};
fs.writeFileSync(OUT, JSON.stringify(TL, null, 1).replace(/\[\n\s+("[^"]+"),\n\s+([\d.]+)\n\s+\]/g, '[$1, $2]'));
console.log(`wrote ${OUT}: ${lines.length} lines, ${FRAMES} frames`);
for (const [i, s] of shots.entries()) console.log(`${String(i + 1).padStart(2)} ${s.moment.padEnd(12)} cut ${s.t.toFixed(3)}  first word ${lines[i][0][1].toFixed(3)}  ${lines[i].map(w => w[0]).join(' ')}`);
