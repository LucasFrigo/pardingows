// The game layer, drawn over the stacked panels at 270x480. Everything is a pure function of video time,
// so any frame can be rendered alone. Lyrics pop up word by word on the seam between the panels.
import fs from 'fs';
import { hex } from '../shared/engine.mjs';
import { BIG, MINI, drawText, textWidth } from '../shared/font.mjs';

export const TL = JSON.parse(fs.readFileSync(new URL('./timeline.json', import.meta.url), 'utf8'));
const PLAN = fs.existsSync(new URL('./run_plan.json', import.meta.url))
  ? JSON.parse(fs.readFileSync(new URL('./run_plan.json', import.meta.url), 'utf8'))
  : { coins: [], cash: Infinity };
const START = TL.start;
const C = Object.fromEntries(Object.entries(TL.cues).map(([k, t]) => [k, t - START]));
const S = Object.fromEntries(Object.entries(TL.shots).map(([k, [a, b]]) => [k, [a - START, b - START]]));
export const W = 270, H = 480, SEAM = 240;
export const MERGE_V = TL.merge_frame / TL.fps;  // the first full-screen frame

const WHITE = hex('#ffffff'), BLACK = hex('#0b0b12'), YEL = hex('#ffd23f'), ORG = hex('#ff8a1f'), RED = hex('#e8211c'),
  CYAN = hex('#2fd0ff'), DIM = hex('#07070d'), GRN = hex('#7ec23a'), GOLD = hex('#f0b828');

const LINES = TL.lines.map(l => ({
  hide: l.hide,
  words: l.words.map(([text, t, style = 'n']) => ({ text, v: t - START, style })),
})).map((l, i, all) => ({ ...l, v: l.words[0].v, next: all[i + 1] ? all[i + 1].words[0].v : Infinity }));

const clamp = (x, a = 0, b = 1) => (x < a ? a : x > b ? b : x);
const phase = (v, a, b) => clamp((v - a) / (b - a));
const center = (s, str, y, color, opt = {}) => {
  const w = textWidth(opt.font || BIG, str, opt.scale || 1);
  drawText(s, str, Math.round((W - w) / 2), y, color, { outline: BLACK, ...opt });
};

const coinsAt = v => PLAN.coins.filter(t => t <= v).length;
export const moneyAt = v => coinsAt(v) + (v >= PLAN.cash ? 100 : 0);
const scoreAt = v => Math.floor(Math.min(v, C.grab) * 137) * 10 + coinsAt(v) * 50;

// Top strip of the runner panel: money on the left, score on the right, like the game it's sending up
function runnerHud(s, v) {
  const y = SEAM + 19;
  const money = `R$ ${moneyAt(v)}`;
  const flash = v >= PLAN.cash && v < PLAN.cash + 0.4 && Math.floor(v * 15) % 2 === 0;
  drawText(s, money, 7, y, flash ? WHITE : YEL, { scale: 2, outline: BLACK });
  const score = String(scoreAt(v)).padStart(6, '0');
  drawText(s, score, W - 7 - textWidth(BIG, score, 2), y, WHITE, { scale: 2, outline: BLACK });
  if (v >= PLAN.cash && v < PLAN.cash + 0.8) {
    const up = Math.round((v - PLAN.cash) * 22);
    drawText(s, '+100', 7, y + 18 + up, YEL, { outline: BLACK });
  }
}

// Words on the seam, wrapped to the frame, new ones flashing white
function seamLyrics(s, v) {
  const line = LINES.find(l => v >= l.v && v < Math.min(l.next, l.words.at(-1).v + 1.2));
  if (!line || line.hide) return;
  const shown = line.words.filter(w => v >= w.v);
  if (!shown.length) return;
  const rows = [[]];
  let rowW = 0;
  const maxW = W - 12;
  for (const w of shown) {
    const scale = w.style === 'hit' || w.style === 'insult' ? 3 : 2;
    const ww = textWidth(BIG, w.text, scale);
    if (rowW && rowW + 8 + ww > maxW) { rows.push([]); rowW = 0; }
    rows.at(-1).push({ ...w, scale, ww });
    rowW += ww + 8;
  }
  const rowH = r => (r.some(w => w.scale === 3) ? 27 : 19);
  const total = rows.reduce((a, r) => a + rowH(r), 0);
  let y = SEAM - Math.round(total / 2);
  for (const row of rows) {
    let x = Math.round((W - (row.reduce((a, w) => a + w.ww, 0) + (row.length - 1) * 8)) / 2);
    for (const w of row) {
      const fresh = v - w.v < 0.1;
      const base = { n: WHITE, key: YEL, insult: GRN, hit: ORG }[w.style];
      const jig = (w.style === 'insult' || w.style === 'hit') && v - w.v < 0.25 ? (Math.floor(v * 30) % 2 ? 2 : -2) : 0;
      drawText(s, w.text, x + jig, y, fresh ? WHITE : base, { scale: w.scale, outline: BLACK });
      x += w.ww + 8;
    }
    y += rowH(row);
  }
}

function banner(s, v, a, b, top, body, color) {
  if (v < a || v >= b) return;
  const y = Math.round(10 - (1 - phase(v, a, a + 0.1)) * 40);
  s.rect(0, y, W, 34, DIM, 0.72);
  center(s, top, y + 4, color);
  center(s, body, y + 15, WHITE, { scale: 2 });
}

function banners(s, v) {
  banner(s, v, C.objetivo, S.colchao[0] + 0.5, 'NOVO OBJETIVO', 'SALGADO BOM', YEL);
  banner(s, v, C.chasers_in, S.lixao[1], 'ALERTA', 'PARAGUAIOS NA COLA', RED);
  banner(s, v, C.cheirao, S.chao[1], 'STATUS', 'CHEIRÃO -50', GRN);
}

function title(s, v) {
  // The title lands as the song shouts it
  if (v < C.title1 || v >= S.dorme[1]) return;
  const second = v >= C.title2;
  center(s, 'PARDOS', 150, second ? WHITE : YEL, { scale: 4 });
  center(s, 'NA MISSÃO', 190, second ? YEL : WHITE, { scale: 3 });
  center(s, 'PARDINGOWS', 222, CYAN, { font: MINI, scale: 2 });
}

function doisReal(s, v) {
  // The price grows on each ask, on top of the beggars
  if (v < C.real1 || v >= C.nao) return;
  const n = v >= C.real3 ? 3 : v >= C.real2 ? 2 : 1;
  const age = v - (n === 3 ? C.real3 : n === 2 ? C.real2 : C.real1);
  const pop = Math.max(0, 1 - age / 0.08);
  center(s, 'R$ 2,00', 58 + 8 * (3 - n), RED, { scale: n + 2 + Math.round(pop), outline: WHITE });
}

function bigNo(s, v) {
  if (v < C.nao || v >= C.silence) return;
  const pop = Math.max(0, 1 - (v - C.nao) / 0.08);
  center(s, 'NÃO!', 44 - Math.round(pop * 14), Math.floor(v * 15) % 2 ? ORG : YEL, { scale: 11 + Math.round(pop * 2), outline: RED });
}

function ending(s, v) {
  if (v < C.silence) return;
  const age = v - C.silence;
  if (age > 0.1) {
    center(s, 'MISSÃO', 14, YEL, { scale: 5 });
    center(s, 'CUMPRIDA', 56, WHITE, { scale: 4 });
  }
  if (age > 0.72) {
    s.rect(0, 400, W, 62, DIM, 0.8);
    center(s, 'SALGADO', 407, GOLD, { scale: 2 });
    center(s, `R$ ${moneyAt(v)} NO BOLSO`, 426, WHITE, { scale: 2 });
    center(s, 'PARDINGOWS', 447, CYAN, { font: MINI, scale: 2 });
  }
}

function flash(s, v) {
  const hits = [[C.title1, 0.12, hex('#fff2a0')], [C.title2, 0.12, hex('#fff2a0')], [C.afflicao, 0.12, hex('#ffffff')], [C.dumpster, 0.12, hex('#ffffff')],
    [C.poop, 0.1, hex('#b08040')], [C.bosta, 0.12, hex('#7ec23a')], [C.grab, 0.14, hex('#ff3030')], [C.real1, 0.06, hex('#ffffff')], [C.real2, 0.06, hex('#ffffff')],
    [C.real3, 0.06, hex('#ffffff')], [C.nao, 0.12, hex('#ffffff')]];
  for (const [t, d, c] of hits) {
    if (v >= t && v < t + d) s.rect(0, 0, W, H, c, 0.8 * (1 - (v - t) / d));
  }
}

export function drawHud(s, v) {
  if (v < MERGE_V) {
    // A black line where the two panels meet
    s.rect(0, SEAM - 1, W, 2, BLACK);
    flash(s, v);
    runnerHud(s, v);
    banners(s, v);
    title(s, v);
    doisReal(s, v);
    seamLyrics(s, v);
    return;
  }
  flash(s, v);
  bigNo(s, v);
  ending(s, v);
}
