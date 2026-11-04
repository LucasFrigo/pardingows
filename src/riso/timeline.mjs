// All timing lives here. The track sits on a fixed 165 BPM grid (first beat at 0.173 s), so
// lyrics are written as musical positions 'bar.beat.16th' and converted to video time `v`.
// If a word is early/late, move it one 16th (or give it a song time in seconds) and re-render.

export const AUDIO_FILE = 'audio/VIDA DE PARDO (F#DEU... EU VOU ME C4G4R).wav';
export const BPM = 165;
export const BEAT = 60 / BPM;
export const BAR = BEAT * 4;
export const S16 = BEAT / 4;
const GRID0 = 0.173;

// Bar 39 beat 4 -> bar 56 beat 4: exactly 17 bars, so the loop seam keeps the beat.
export const SONG_START = GRID0 + 159 * BEAT;  // 57.991
export const SONG_END = GRID0 + 227 * BEAT;    // 82.718
export const DURATION = SONG_END - SONG_START;
export const FPS = 30;

// 'bar.beat.16th' (1-based beat and 16th) -> video time. A plain number is a song time in
// seconds, used where the singer drifts off the grid (the held "fudeeeu" in the stops).
export function at(pos) {
  if (typeof pos === 'number') return pos - SONG_START;
  const [bar, beat = 1, s = 1] = String(pos).split('.').map(Number);
  return GRID0 + ((bar * 4 + beat - 1) * 4 + s - 1) * S16 - SONG_START;
}
export const bar = n => at(`${n}.1.1`);

const EPS = 1e-6;
export const beatPos = v => (v + SONG_START - GRID0) / BEAT;      // absolute song beat
export const beatNum = v => Math.floor(beatPos(v) + EPS);
export const beatPhase = v => beatPos(v) + EPS - Math.floor(beatPos(v) + EPS);
export const s16Num = v => Math.floor(beatPos(v) * 4 + EPS);
export const beatInBar = v => beatNum(v) % 4;                     // 0 = downbeat
// 1.0 on the beat, decaying before the next one.
export const pulse = (v, decay = 9) => Math.exp(-decay * beatPhase(v) * BEAT);

// The two band stops (the vocal is left alone in silence).
export const STOP1 = [bar(46), at('46.4.3')];
export const STOP2 = [bar(54), at('54.4.3')];
export const inStop = v => (v >= STOP1[0] && v < STOP1[1]) || (v >= STOP2[0] && v < STOP2[1]);

// Lyrics. style: n = normal, key = emphasis (bigger, inked scrap), stamp, cut (the "ca-!"),
// shake (milkshake), cagar (the payoff). `end` is when the line is cleared.
const RAW = [
  { end: '41.3.4', words: [['UM', '39.4.3'], ['CAFÉ', '40.1.1'], ['COM', '40.1.3'], ['LEITE', '40.1.4', 'key'], ['NA', '40.3.1'], ['PADOCA', '40.3.2'], ['DE', '41.1.1'], ['MANHÃ', '41.1.3']] },
  { end: '43.3.4', words: [['MAIS', '41.4.3'], ['FUMAÇA', '42.1.2'], ['NO', '42.2.4'], ['CAMINHO', '42.3.1'], ['PRA', '42.4.3'], ['APAZIGUAR', '42.4.4']] },
  { end: '45.4.1', words: [['CHEGO', '43.4.3'], ['NO', '44.1.3'], ['TRAMPO', '44.2.2'], ['E', '44.3.4'], ['JÁ', '44.4.1'], ['TEM', '44.4.4'], ['1', '45.1.1', 'key'], ['REUNIÃO', '45.2.2']] },
  // stop 1: "fodeeeu" is held through the stop (until 67.84), a silent pause, then "eu vou me ca-"
  // comes in on the band's return; the held "caaa-" is cut off by "já" at 69.87
  { end: 69.87, mode: 'stop', words: [['F#D3U...', '45.4.1', 'stamp'], ['EU', 68.27], ['VOU', 68.80], ['ME', 69.07], ['CA-!', 69.50, 'cut']] },
  { end: '49.3.4', words: [['JÁ', 69.87], ['TEM', '48.1.1'], ['MUITOS', '48.1.3'], ['ANOS', '48.2.3'], ['LACTOSE', '48.3.3', 'key'], ['NÃO', '49.1.1'], ['CAI', '49.2.1'], ['BEM', '49.2.3']] },
  { end: '51.4.2', words: [['EU', '49.4.3'], ['NÃO', '50.1.1'], ['LIGO,', '50.1.3'], ['ME', '50.2.3'], ['DÁ', '50.3.1'], ['LOGO', '50.3.4'], ['UM', '50.4.4'], ['MILKSHAKE', '51.1.2', 'shake']] },
  { end: '53.4.2', words: [['EU', '51.4.3'], ['NUM', '52.1.1'], ['VOU', '52.1.3'], ['TOMAR', '52.2.1'], ['NENHUM', '52.3.3'], ['LEITE', '53.1.2', 'key'], ['VEGETAL', '53.2.2']] },
  // stop 2: same shape; "fodeeeu" held until 79.62, pause, then "eu vou me ca-gaaar" over the
  // band, the "gaaar" held to ~82.3. CAGAR!!! stays up until the page is torn away.
  { end: SONG_END, mode: 'stop', words: [['F#D3U...', '53.4.3', 'stamp'], ['EU', 79.97], ['VOU', 80.41], ['ME', 80.74], ['CAGAR!!!', 81.10, 'cagar']] },
];
export const LINES = RAW.map(l => ({
  mode: l.mode || 'normal',
  v: at(l.words[0][1]),
  end: at(l.end),
  words: l.words.map(([text, pos, style = 'n']) => ({ text, v: at(pos), style })),
}));

// The scissors snip the end of the held "caaa-" and the print jam smears on into "já".
// SIGNOFF: the (PARDJHONSON) stamp hits the bathroom door.
export const CA_CUT = at(69.78);
export const JAM_END = at(69.95);
export const SIGNOFF = at('56.2.1');

// Scene cuts (video time).
export const CUT = {
  padaria: 0,
  commute: at('41.4.3'),
  office: at('43.4.3'),
  meeting: at('44.3.4'),
  panic1: at('45.4.1'),
  calendar: at(69.87),
  lactose: at('48.3.3'),
  shrug: at('49.4.3'),
  milkshake: at('50.4.4'),
  vegetal: at('51.4.3'),
  panic2: at('53.4.3'),
  cagar: at(81.10),
  door: bar(56),
  tear: at('56.2.3'),
  end: DURATION,
};
