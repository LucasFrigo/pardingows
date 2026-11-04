// All timing lives here. Times are in seconds of the SONG unless named `v` (video time).
// If a lyric line is early/late, nudge its `at` value and re-render.

export const AUDIO_FILE = 'audio/PARDINGOWS OITENTA MERDA.wav';
export const SONG_START = 6.5;   // chorus window given by the artist
export const SONG_END = 21.0;
export const DURATION = SONG_END - SONG_START;
export const FPS = 30;

// Beat grid fitted to the track's onsets: 139.86 BPM, a beat lands at 6.386s,
// and the bass/kick drop (bar downbeat) lands at 7.673s.
export const BPM = 139.86;
export const BEAT = 60 / BPM;
export const BAR = BEAT * 4;
const FIRST_BEAT = 6.386 - SONG_START;
export const DROP = 7.673 - SONG_START;

const frac = x => x - Math.floor(x);
export const beatPos = v => (v - FIRST_BEAT) / BEAT;          // continuous beat counter
export const beatPhase = v => frac(beatPos(v));                 // 0 at each beat
export const beatNum = v => Math.floor(beatPos(v));
export const barPhase = v => frac((v - DROP) / BAR);            // 0 at each downbeat
// 1.0 on the beat, decaying to ~0 before the next one.
export const kick = (v, decay = 7) => Math.exp(-decay * beatPhase(v) * BEAT);

// Chorus lyrics, one line per bar. `/` breaks a caption into two rows.
// Words are spread over each line by syllable count (the number after the word).
const RAW = [
  [6.500, 'VEM:1 PRO:1 SURUPARDO:4'],
  [8.216, 'LÁ:1 SÓ:1 TEM:1 / PARDO:2 PELADO:3'],
  [9.932, 'TIRA:2 SUA:2 ROUPA,:2 / PARDA:2'],
  [11.648, 'ESQUECE:3 SEU:1 / NAMORADO:4'],
  [13.364, 'TIPO:2 MINECRAFT:3'],
  [15.080, 'ESSE:2 BRANCO:2 É:1 / QUADRADO:3'],
  [16.796, 'NÃO:1 EMPLACA:3 / COS:1 PARDINGOW:3'],
  [18.512, 'AQUI:2 É:1 AURA:2 / TODO:2 MUNDO:2 É:1 SAFADO:3'],
];
const SUNG_FRACTION = 0.85; // share of the bar the vocal actually fills

export const LINES = RAW.map(([at, spec], i) => {
  const end = i + 1 < RAW.length ? RAW[i + 1][0] : SONG_END;
  const rows = spec.split(' / ').map(r => r.split(' ').map(w => {
    const [text, syl] = w.split(':');
    return { text, syl: Number(syl) };
  }));
  const total = rows.flat().reduce((n, w) => n + w.syl, 0);
  const span = (end - at) * SUNG_FRACTION;
  let acc = 0;
  for (const w of rows.flat()) {
    w.v = at - SONG_START + span * acc / total;
    acc += w.syl;
  }
  return { v: at - SONG_START, end: end - SONG_START, rows };
});

// Line start times in video time, used as scene cut points.
export const CUT = LINES.map(l => l.v);
