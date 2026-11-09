// Builds src/erva/timeline.json from the snapped syllable times (blender/erva/sync/attacks.json). Run once after attacks.py;
// after that the timeline is the source of truth and is edited by hand (re-running overwrites hand edits, so it refuses unless --force).
//   node src/erva/sync/make_timeline.mjs [--force]
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
const OUT = path.join(ROOT, 'src/erva/timeline.json');
if (fs.existsSync(OUT) && !process.argv.includes('--force')) throw new Error(`${OUT} exists: pass --force to overwrite hand edits`);

const BPM = 150, BEAT = 60 / BPM, BAR = 8 * BEAT; // a couplet is one 3.2 s bar of the half-time feel
const BEAT0 = 48.0; // FL Studio grid from 0 s; bar 0 is the downbeat after the "vou te" pickup
const START = 47.6, END = 101.6, FPS = 24;
const FRAMES = Math.round((END - START) * FPS);

// Caption text per sung line, '-' marks syllables (same count as the aligner's spelling). Censoring as in the LEGO cut.
const TEXT = {
  1: 'vou te con-tar a his-tó-ria', 2: 'do par-dão e da er-va',
  3: 'só es-pe-ra eu dar um pu-xe', 4: 'no ca-chim-bo com a E-va', '4m': '(mnham mnham mnham)',
  5: 'par-dão es-ta-va an-dan-do', 6: 'so-zi-nho no me-re-tre-vaz',
  7: 'deu dois pas-so pra fren-te', 8: 'e ta-va so-zi-nho na sel-va',
  9: 'an-dan-do no jar-dim', 10: 'u-ma co-bra vei-o de fi-nin',
  11: 'che-gou na me-nis-quên-cia', 12: 'o-fe-re-ceu um ba-si-a-din', '12m': '(mnham mnham mnham)',
  13: 'par-dão sem pen-sar', 14: 'a-cei-tou lo-go es-se ca-mi-nho',
  15: 'es-sa é da bo-a, par-dão', 16: 'o-q a-chou, fa-la pra mim',
  17: 'es-sa flor é bo-a mas', 18: 'a-cho que num com-pen-sa',
  19: 'tar-de de-mais, par-dão', 20: 'já rou-bei su-a vi-cên-cia',
  21: 'su-a al-ma é mi-nha a-go-ra', 22: 'não ve-nha com me-nis-quên-cia',
  23: 'HA-HA-HA HO-HO-HO, HO-HO-HO HA-HA-HA',
  24: 'vai se f#-der su-a co-bra mo-le', 25: 'vo-cê não me as-sus-ta',
  26: 'sou fe-cha-do cos par-do', 27: 'já ves-te a ca-ra-pu-ça',
  28: 'fu-mei dois ci-gar-ro', 29: 'ou-ve mi-nha bar-ra, su-a p#-ta',
  30: 'cê tá fe-cha-do com os ca-ra', 31: 'não cai-o na su-a a-ra-pu-ca',
};

// One card (and one storyboard moment) per couplet. rows are line ids, or [id, from, to] for part of a line;
// adlib is a small third row.
const CARDS = [
  ['conto', 'NARRADOR', [[1], [2]]], ['cachimbo', 'NARRADOR', [[3], [4]], '4m'],
  ['trevas', 'NARRADOR', [[5], [6]]], ['selva', 'NARRADOR', [[7], [8]]],
  ['jardim', 'NARRADOR', [[9], [10]]], ['basiadin', 'NARRADOR', [[11], [12]], '12m'],
  ['caminho', 'NARRADOR', [[13], [14]]], ['da_boa', 'COBRA', [[15], [16]]],
  ['compensa', 'PARDÃO', [[17], [18]]], ['tarde', 'COBRA', [[19], [20]]],
  ['alma', 'COBRA', [[21], [22]]], ['risada', 'COBRA', [[['23', 0, 2]], [['23', 2, 4]]]],
  ['mole', 'PARDÃO', [[24], [25]]], ['crew', 'PARDÃO', [[26], [27]]],
  ['cigarros', 'PARDÃO', [[28], [29]]], ['arapuca', 'PARDÃO', [[30], [31]]],
];

// Syllables placed by judgement instead of the snap (see notes)
const OVERRIDE = { '31:sua': [98.36, 98.43], '31:arapuca': [98.5, 98.6, 98.8, 99.0] };

const { lines } = JSON.parse(fs.readFileSync(path.join(ROOT, 'blender/erva/sync/attacks.json'), 'utf8'));
const byId = Object.fromEntries(lines.map(l => [l.line, l]));
const r3 = x => Math.round(x * 1000) / 1000;
function words(id) {
  const caps = TEXT[id].split(' ');
  const got = byId[id].words;
  if (caps.length !== got.length) throw new Error(`line ${id}: ${caps.length} caption words, ${got.length} timed`);
  return caps.map((c, i) => {
    const syl = OVERRIDE[`${id}:${got[i].w}`] || got[i].syl;
    // the laugh's words are marked by '-' too; mnham has one syllable per word
    const n = c.split('-').length;
    if (n !== syl.length) throw new Error(`line ${id} word ${c}: ${n} syllables, ${syl.length} timed`);
    return [c, r3(syl[0]), syl.map(r3)];
  });
}

const eighth = BEAT / 2;
let lastSyl = START;
const cards = CARDS.map(([moment, speaker, rows, adlib], i) => {
  const r = rows.map(ids => ids.flatMap(id => Array.isArray(id) ? words(id[0]).slice(id[1], id[2]) : words(id)));
  const first = r[0][0][1];
  // the card appears on the 8th note at or before 150 ms ahead of its first syllable, after the last card's last syllable
  const k = Math.floor((first - 0.15 - BEAT0) / eighth);
  let t = Math.max(BEAT0 + k * eighth, lastSyl + 0.12);
  if (i === 0) t = START;
  const card = { t: r3(Math.round((t - START) * FPS) / FPS + START), moment, speaker, rows: r };
  if (adlib) card.adlib = words(adlib);
  const all = [...r.flat(), ...(card.adlib || [])].flatMap(w => w[2]);
  lastSyl = Math.max(...all);
  return card;
});
cards.push({ t: r3(BEAT0 + 16 * BAR), moment: 'fim', speaker: null, rows: [] });

// Visual cuts on the bar lines; the first is the window start (the pickup), the last is the FIM card
const shots = cards.map((c, i) => ({ t: i === 0 ? START : r3(BEAT0 + i * BAR), moment: c.moment }));

const TL = {
  _: 'All timing lives here, read by Blender (shots) and Node (captions). Times are song seconds. Video time v = song - start, frame index n = round(v * 24). A card word is [text with syllable marks, first syllable, [syllable onsets]]. To fix a late or early syllable, change its number and run: npm run erva:proof. Times: CTC forced aligner (with syllable onsets from its character spans) and Whisper on the Demucs vocal stem, each syllable snapped to the vocal attack within 80 ms (first) or 60 ms (others) by src/erva/sync/attacks.py. The notes list everything placed by judgement.',
  audio: 'audio/pardão&erva.wav',
  mix: 'blender/erva/sync/mix.wav',
  mix_t0: START,
  start: START,
  frames: FRAMES,
  fps: FPS,
  bpm: BPM,
  beat0: BEAT0,
  bar: BAR,
  notes: {
    cut: `Window ${START} to ${END} s (${FRAMES} frames at ${FPS} fps). The 16 couplets are the 16 bars of 3.2 s from ${BEAT0} to ${BEAT0 + 16 * BAR}; the start is the beat before, for the "vou te" pickup. The bar after the last couplet carries the FIM card. mix.wav (src/erva/sync/mix.py) uses the instrumental stem before 47.66 (the tail of the previous verse's "estar") and from 99.10-99.20 on (the next verse starts at 99.04), and fades out over the last second.`,
    grid: '150 BPM from 0 s. grid.py fitted 150.01 BPM with its phase 16 ms early (STFT window lead); the band\'s earliest bar hits land exactly on multiples of 3.2 s.',
    '4 Eva': 'You wrote "com a eva"; both Whisper passes hear "com a erva", even when prompted with "eva". The aligner can\'t tell them apart (0.11 vs 0.09). Kept as Eva until you say otherwise.',
    '8 sozinho': 'You wrote "e tava no meio da selva"; the aligner scores "sozinho na selva" 0.71 against 0.49, and both Whisper passes hear "sozinho". Captioned as sung; same syllable count either way.',
    '14 logo': 'You wrote "aceitou esse novo caminho"; the aligner scores "aceitou logo esse caminho" 0.53 against 0.44 (its "novo" collapses to 80 ms), and both Whisper passes hear "logo". Captioned as sung.',
    mnham: 'Not phonetic enough for the aligner. Placed on the three vocal bumps before each next bar: 53.83/54.04/54.05 is tight (only 0.35 s between "Eva" and "pardão"); 66.66/66.85/67.06 matches Whisper\'s prompted pass. Check by ear.',
    laugh: 'Read off the spectrogram: four groups of short-short-long, the long HA/HO on the beat. Snapped.',
    '31 arapuca': '"sua arapuca" is sung elided (su-a-ra-pu-ca); syllables set by hand from the loudness dips.',
    accents: 'Standard words are written with accents (história, pardão, você, não, já); your slang spellings are kept (meretrevaz, menisquência, basiadin, de finin, cos, num, cê tá, oq). "menisquencia"/"vicencia" got a circumflex: say if you want them bare.',
  },
  cards,
  shots,
};
fs.writeFileSync(OUT, JSON.stringify(TL, null, 1)
  .replace(/\[\n\s+([\d.]+),?\n?\s*([\d.,\s]*)\]/g, (m) => m.replace(/\s+/g, ' ').replace(/\[ /, '[').replace(/ \]/, ']'))
  .replace(/\[\n\s+("[^"]+"),\n\s+([\d.]+),\n\s+(\[[^\]]*\])\n\s+\]/g, '[$1, $2, $3]'));
console.log(`wrote ${OUT}: ${cards.length} cards, ${FRAMES} frames`);
for (const [i, c] of cards.entries()) console.log(`${String(i + 1).padStart(2)} ${c.moment.padEnd(10)} card ${c.t.toFixed(3)} shot ${shots[i].t.toFixed(3)}  ${c.rows.map(r => r.map(w => w[0].replace(/-/g, '')).join(' ')).join(' / ')}`);
