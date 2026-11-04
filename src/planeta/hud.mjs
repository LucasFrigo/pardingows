// The mission HUD, drawn over each frame at 270x480. Everything is a pure function of video time,
// so any frame can be rendered alone. Lyrics pop up word by word as mission log entries.
import fs from 'fs';
import { hex } from '../shared/engine.mjs';
import { BIG, MINI, drawText, textWidth } from '../shared/font.mjs';

export const TL = JSON.parse(fs.readFileSync(new URL('./timeline.json', import.meta.url), 'utf8'));
const START = TL.start;
const C = Object.fromEntries(Object.entries(TL.cues).map(([k, t]) => [k, t - START]));
const S = Object.fromEntries(Object.entries(TL.shots).map(([k, [a, b]]) => [k, [a - START, b - START]]));
export const W = 270, H = 480;

const WHITE = hex('#ffffff'), BLACK = hex('#0b0b12'), YEL = hex('#ffd23f'), ORG = hex('#ff8a1f'), RED = hex('#e8211c'),
  CYAN = hex('#2fd0ff'), GRY = hex('#3a3d48'), DIM = hex('#07070d'), GRN = hex('#5fe04a'), KRAFT = hex('#c79a5c');

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

function melanina(v) {
  if (v < C.sun_rise) return 0.22;
  return 0.22 + 0.78 * phase(v, C.sun_rise, C.fardo);
}

function topBar(s, v) {
  // Oxygen runs down the whole video, and the bale takes a chunk of it
  const o2 = Math.max(0, 100 - v * 3.2 - (v >= C.fardo ? 25 : 0));
  drawText(s, 'OXIGÊNIO', 8, 10, CYAN, { outline: BLACK });
  drawText(s, `${Math.round(o2)}%`, 8, 21, o2 < 30 && Math.floor(v * 6) % 2 === 0 ? RED : WHITE, { scale: 2, outline: BLACK });
  const left = Math.max(120 - v, 0), m = Math.floor(left / 60), sec = Math.floor(left % 60);
  const clock = `${m}:${String(sec).padStart(2, '0')}`;
  drawText(s, clock, W - 8 - textWidth(BIG, clock, 2), 21, WHITE, { scale: 2, outline: BLACK });
  drawText(s, 'MISSÃO', W - 8 - textWidth(BIG, 'MISSÃO'), 10, CYAN, { outline: BLACK });

  // Melanin meter, which fills when the sun comes up and flashes when full
  const fill = melanina(v), full = fill >= 1, w = 92, h = 6, x = (W - w) / 2, y = 21;
  center(s, 'MELANINA', 10, full ? ORG : WHITE);
  s.rect(x - 1, y - 1, w + 2, h + 2, BLACK);
  s.rect(x, y, w, h, GRY);
  const flicker = Math.floor(v * 15) % 2 === 0;
  s.rect(x, y, Math.round(w * fill), h, full ? (flicker ? ORG : YEL) : KRAFT);
}

// Lays out the revealed words of the current line, wrapped to the frame.
function logLine(s, v) {
  const line = LINES.find(l => v >= l.v && v < Math.min(l.next, l.words.at(-1).v + 2.0));
  if (!line || line.hide) return;  // the title and the NÃOs get the whole frame instead
  const shown = line.words.filter(w => v >= w.v);
  if (!shown.length) return;

  const rows = [[]];
  let rowW = 0;
  const maxW = W - 14;
  for (const w of shown) {
    const scale = w.style === 'hit' || w.style === 'insult' ? 3 : 2;
    const ww = textWidth(BIG, w.text, scale);
    if (rowW && rowW + 8 + ww > maxW) { rows.push([]); rowW = 0; }
    rows.at(-1).push({ ...w, scale, ww });
    rowW += ww + 8;
  }
  const rowH = r => (r.some(w => w.scale === 3) ? 27 : 19);
  const total = rows.reduce((a, r) => a + rowH(r), 0);
  let y = 392 - total;
  for (const row of rows) {
    let x = Math.round((W - (row.reduce((a, w) => a + w.ww, 0) + (row.length - 1) * 8)) / 2);
    for (const w of row) {
      const fresh = v - w.v < 0.1;
      const base = { n: WHITE, key: YEL, insult: RED, hit: ORG }[w.style];
      // Insults land with a little shake
      const jig = w.style === 'insult' && v - w.v < 0.3 ? (Math.floor(v * 30) % 2 ? 2 : -2) : 0;
      drawText(s, w.text, x + jig, y, fresh ? WHITE : base, { scale: w.scale, outline: BLACK });
      x += w.ww + 8;
    }
    y += rowH(row);
  }
}

function banner(s, v, a, b, top, body, color) {
  if (v < a || v >= b) return;
  const y = Math.round(58 - (1 - phase(v, a, a + 0.1)) * 40);
  s.rect(0, y, W, 34, DIM, 0.72);
  center(s, top, y + 4, color);
  center(s, body, y + 15, WHITE, { scale: 2 });
}

function scanner(s, v) {
  // Brackets closing on his face, as the chimps fail to work out what he is
  if (v < C.scan || v >= S.rua2[1]) return;
  const u = phase(v, C.scan, C.pardo);
  const got = v >= C.pardo;
  const cx = 135, cy = 208, r = Math.round(116 - 26 * u), arm = 18;
  const col = got ? GRN : Math.floor(v * 10) % 2 ? YEL : WHITE;
  for (const [sx, sy] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) {
    const x = cx + sx * r, y = cy + sy * r;
    s.rect(sx < 0 ? x : x - arm, y, arm, 3, col);
    s.rect(x, sy < 0 ? y : y - arm, 3, arm, col);
  }
  const label = got ? 'ID: PARDO' : `ANALISANDO ${'.'.repeat(1 + (Math.floor(v * 6) % 3))}`;
  s.rect(0, 60, W, 16, DIM, 0.72);
  center(s, label, 64, col);
}

function dialog(s, v) {
  // Pardomon's name over his head, then what he says in a game text box
  if (v >= C.pardomon_in && v < C.nao) drawText(s, 'PARDOMON', W - 8 - textWidth(BIG, 'PARDOMON', 2), 150, CYAN, { scale: 2, outline: BLACK });
  if (v >= C.branco && v < C.nao) {
    s.rect(14, 56, W - 28, 28, DIM, 0.85);
    s.rect(14, 56, W - 28, 2, CYAN);
    center(s, 'PARDOMON DIZ:', 60, CYAN);
    center(s, 'VOCÊ É BRANCO', 71, WHITE);
  }
}

function banners(s, v) {
  banner(s, v, S.rua1[0], C.macaco, 'NOVO OBJETIVO', 'ANDAR NA RUA', YEL);
  banner(s, v, C.macaco + 0.02, S.rua1[1], 'OBJETIVO', 'FALHOU', RED);
  banner(s, v, C.sun_rise, C.fardo, 'ALERTA', 'SOL NA PELE', ORG);
  banner(s, v, C.fardo, S.sol[1], 'ITEM NOVO', '1 FARDO', RED);
  banner(s, v, C.papelao, C.papelao_off, 'ANÁLISE DA PELE', 'PAPELÃO', KRAFT);
  banner(s, v, C.pistola, S.standoff[1], 'RAIVA 100%', 'PISTOLA NA MÃO', RED);
  banner(s, v, S.cesar[0], C.nao1, 'CHEFE FINAL', 'MACACO CÉSAR', YEL);
}

function title(s, v) {
  // The title card lands as the song says it
  if (v < C.touchdown || v >= S.landing[1]) return;
  const a = phase(v, C.touchdown, C.touchdown + 0.1);
  s.rect(0, 74, W, 92, DIM, 0.72 * a);
  center(s, 'PLANETA', 82, YEL, { scale: 4 });
  center(s, 'DOS PARDOS', 118, WHITE, { scale: 3 });
  center(s, 'PARDINGOWS', 150, CYAN, { font: MINI, scale: 2 });
}

function bigNo(s, v) {
  // The NÃOs get the whole frame
  for (const [t, y, scale, d] of [[C.nao, 70, 8, 0.4], [C.nao1, 120, 8, 0.42], [C.nao2, 90, 10, 0.75]]) {
    if (v >= t && v < t + d) {
      const pop = Math.max(0, 1 - (v - t) / 0.08);
      center(s, 'NÃO', y - Math.round(pop * 12), Math.floor(v * 15) % 2 ? ORG : YEL, { scale: scale + Math.round(pop * 2), outline: RED });
    }
  }
}

function flash(s, v) {
  const hits = [[C.touchdown, 0.16, hex('#fff2a0')], [C.macaco, 0.08, hex('#ff3030')], [C.fardo, 0.16, hex('#ffffff')], [C.nao, 0.14, hex('#ffffff')],
    [C.papelao, 0.12, hex('#e0b070')], [C.pistola, 0.1, hex('#ffffff')], [C.nao1, 0.14, hex('#ffffff')], [C.nao2, 0.2, hex('#ffd060')]];
  for (const [t, d, c] of hits) {
    if (v >= t && v < t + d) s.rect(0, 0, W, H, c, 0.85 * (1 - (v - t) / d));
  }
}

function report(s, v) {
  const a = phase(v, S.report[0], S.report[0] + 0.18);
  s.rect(0, 0, W, H, DIM, 0.84 * a);
  if (a < 1) return;
  center(s, 'RELATÓRIO', 50, YEL, { scale: 3 });
  center(s, 'DA MISSÃO', 82, WHITE, { scale: 2 });
  const rows = [['COR DA PELE', 'PAPELÃO', KRAFT], ['BRANCO', 'NÃO', RED], ['MACACO', 'NÃO', RED], ['PARDO', 'SIM', GRN], ['FARDOS', '1', ORG]];
  rows.forEach(([name, val, col], i) => {
    const appear = S.report[0] + 0.2 + i * 0.12;
    if (v < appear) return;
    const y = 122 + i * 22;
    drawText(s, name, 18, y, WHITE, { outline: BLACK });
    drawText(s, val, W - 18 - textWidth(BIG, val, 2), y - 3, col, { scale: 2, outline: BLACK });
  });
  if (v < S.report[0] + 0.95) return;
  center(s, 'PLANETA', 244, YEL, { scale: 3 });
  center(s, 'DOS PARDOS', 272, WHITE, { scale: 2 });
  center(s, 'PARDINGOWS', 308, WHITE, { font: MINI, scale: 3 });
  if (Math.floor(v * 3) % 2 === 0) center(s, 'PRESS START', 350, WHITE, { scale: 2 });
}

export function drawHud(s, v) {
  flash(s, v);
  topBar(s, v);
  if (v >= S.report[0]) {
    report(s, v);
    return;
  }
  banners(s, v);
  scanner(s, v);
  dialog(s, v);
  title(s, v);
  logLine(s, v);
  bigNo(s, v);
}
