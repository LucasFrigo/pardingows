// The game HUD, drawn over each frame at 270x480. Everything is a pure function of video time,
// so any frame can be rendered alone. Lyrics are the trick names, as they're sung.
import fs from 'fs';
import { hex, lerpColor } from '../shared/engine.mjs';
import { BIG, MINI, drawText, textWidth } from '../shared/font.mjs';

export const TL = JSON.parse(fs.readFileSync(new URL('./timeline.json', import.meta.url), 'utf8'));
const START = TL.start;
const C = Object.fromEntries(Object.entries(TL.cues).map(([k, t]) => [k, t - START]));
const S = Object.fromEntries(Object.entries(TL.shots).map(([k, [a, b]]) => [k, [a - START, b - START]]));
export const W = 270, H = 480;

const WHITE = hex('#ffffff'), BLACK = hex('#0b0b12'), YEL = hex('#ffd23f'), ORG = hex('#ff8a1f'), RED = hex('#e8211c'),
  BLUE = hex('#2f6fe0'), CYAN = hex('#2fd0ff'), GRY = hex('#3a3d48'), DIM = hex('#07070d'), GRN = hex('#5fe04a');

const LINES = TL.lines.map(l => ({
  words: l.words.map(([text, t, style = 'n']) => ({ text, v: t - START, style })),
})).map((l, i, all) => ({ ...l, v: l.words[0].v, next: all[i + 1] ? all[i + 1].words[0].v : Infinity }));
const POINTS = { n: 150, key: 900, censor: 1300, goon: 2500, special: 25000 };

const clamp = (x, a = 0, b = 1) => (x < a ? a : x > b ? b : x);
const phase = (v, a, b) => clamp((v - a) / (b - a));
const center = (s, str, y, color, opt = {}) => {
  const w = textWidth(opt.font || BIG, str, opt.scale || 1);
  drawText(s, str, Math.round((W - w) / 2), y, color, { outline: BLACK, ...opt });
};
const brNum = n => Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.');

export function scoreAt(v) {
  let score = 0;
  for (const [i, l] of LINES.entries())
    for (const w of l.words) score += POINTS[w.style] * (1 + i * 0.5) * phase(v, w.v, w.v + 0.25);
  if (v >= C.slam) score *= 1 - 0.8 * phase(v, C.slam, C.slam + 0.25);       // the bail takes it
  score += 1600000 * phase(v, C.launch, C.held_note) ** 2;                  // and the special pays it back
  score += 7700000 * phase(v, C.held_note, S.special[1]) ** 1.5;
  return score;
}

function specialAt(v) {
  if (v < C.slam) return 0.08 + 0.3 * phase(v, 1, C.slam);
  if (v < C.reassemble) return 0;
  return phase(v, C.reassemble, C.goon_down);
}

function topBar(s, v) {
  drawText(s, brNum(scoreAt(v)), 8, 10, WHITE, { scale: 2, outline: BLACK });

  const left = Math.max(120 - v, 0), m = Math.floor(left / 60), sec = Math.floor(left % 60);
  const clock = `${m}:${String(sec).padStart(2, '0')}`;
  drawText(s, clock, W - 8 - textWidth(BIG, clock, 2), 10, WHITE, { scale: 2, outline: BLACK });

  // Special meter: blue, then flashing fire when full
  const fill = specialAt(v), full = fill >= 1, x = 8, y = 30, w = 104, h = 7;
  s.rect(x - 1, y - 1, w + 2, h + 2, BLACK);
  s.rect(x, y, w, h, GRY);
  const flicker = Math.floor(v * 15) % 2 === 0;
  s.rect(x, y, Math.round(w * fill), h, full ? (flicker ? ORG : YEL) : BLUE);
  if (full) drawText(s, 'SPECIAL', x + w + 6, y, flicker ? YEL : ORG, { outline: BLACK });

  // C-P-F collected, standing in for S-K-A-T-E
  const slots = [['C', C.cpf_c], ['P', C.cpf_p], ['F', C.cpf_f]];
  slots.forEach(([ch, cue], i) => {
    const got = v >= cue;
    drawText(s, ch, W - 8 - (3 - i) * 13 + 7, 30, got ? YEL : GRY, { outline: BLACK });
  });
}

function balance(s, v) {
  if (v < C.land_ledge || v >= C.ledge_exit) return;
  const y = 330, w = 110, x = (W - w) / 2;
  s.rect(x - 1, y - 1, w + 2, 6, BLACK);
  s.rect(x, y, w, 4, GRY);
  s.rect(x + w * 0.4, y, w * 0.2, 4, GRN);
  const needle = 0.5 + 0.34 * Math.sin((v - C.land_ledge) * 5.5) * phase(v, C.land_ledge, C.ledge_exit);
  s.rect(x + w * needle - 1, y - 3, 3, 10, WHITE);
}

// Lays out the revealed words of the current line as a trick string, wrapped to the frame.
function trickString(s, v) {
  const line = LINES.find(l => v >= l.v && v < Math.min(l.next, l.words.at(-1).v + 2.6));
  if (!line) return;
  const shown = line.words.filter(w => v >= w.v);
  if (!shown.length) return;
  const last = shown.at(-1);
  const big = last.style === 'special' || last.style === 'goon';

  const rows = [[]];
  let rowW = 0;
  const maxW = W - 14;
  for (const w of shown) {
    const hero = w.style === 'special' || w.style === 'goon';
    const scale = hero ? 3 : 2;
    const prefix = w.style !== 'n' && (rows[0].length || rows.length > 1) ? '+' : '';
    const cw = textWidth(BIG, w.text, scale) + (prefix ? textWidth(BIG, prefix, 2) + 8 : 0);
    const wrap = rowW && rowW + 8 + cw > maxW;
    if (wrap) { rows.push([]); rowW = 0; }
    // a word that starts its own row needs no "+", which also lets the held note fit the frame
    const own = !rows.at(-1).length;
    const width = own ? textWidth(BIG, w.text, scale) : cw;
    rows.at(-1).push({ ...w, scale, prefix: own ? '' : prefix, cw: width });
    rowW += width + 8;
  }

  const rowH = r => (r.some(w => w.scale === 3) ? 27 : 19);
  const total = rows.reduce((a, r) => a + rowH(r), 0);
  let y = 392 - total;
  for (const row of rows) {
    const rw = row.reduce((a, w) => a + w.cw, 0) + (row.length - 1) * 8;
    let x = Math.round((W - rw) / 2);
    for (const w of row) {
      if (w.prefix) {
        drawText(s, w.prefix, x, y + (w.scale === 3 ? 3 : 0), WHITE, { scale: 2, outline: BLACK });
        x += textWidth(BIG, w.prefix, 2) + 8;
      }
      const fresh = v - w.v < 0.1;
      const base = { n: WHITE, key: YEL, censor: RED, goon: ORG, special: ORG }[w.style];
      let col = fresh ? WHITE : base;
      if (w.style === 'special') col = Math.floor(v * 15) % 2 ? YEL : ORG;
      drawText(s, w.text, x, y, col, { scale: w.scale, outline: BLACK });
      x += textWidth(BIG, w.text, w.scale) + 8;
    }
    y += rowH(row);
  }

  // "4.250 x 2": points so far times the keywords hit, the game's running combo line
  const pts = shown.reduce((a, w) => a + POINTS[w.style], 0);
  const mult = Math.max(1, shown.filter(w => w.style !== 'n').length);
  const combo = `${brNum(pts)} X ${mult}`;
  center(s, combo, y + 2, big ? YEL : WHITE, { scale: 1 });
}

function goal(s, v, a, b, top, body, color) {
  if (v < a || v >= b) return;
  const slide = phase(v, a, a + 0.1);
  const y = Math.round(58 - (1 - slide) * 40);
  s.rect(0, y, W, 34, DIM, 0.72);
  center(s, top, y + 4, color);
  center(s, body, y + 15, WHITE, { scale: 2 });
}

function banners(s, v) {
  // Title on the way in
  if (v < C.ollie - 0.02) {
    const a = phase(v, 0, 0.12);
    s.rect(0, 60, W, 102, DIM, 0.7 * a);
    center(s, 'A SOLUÇÃO', 68, YEL, { scale: 3 });
    center(s, 'DE TODOS OS PROBLEMAS', 104, WHITE);
    center(s, 'DA VIDA', 116, YEL, { scale: 2 });
    center(s, "PARD'JHONSON PRO SKATER", 142, CYAN);
  }

  goal(s, v, C.cpf_f, S.cpf[1], 'GOAL COMPLETE', 'CPF', GRN);
  goal(s, v, S.celular[0], C.phone_given, 'NEW GOAL', 'CELULAR', YEL);
  goal(s, v, C.phone_given + 0.02, S.celular[1], 'GOAL COMPLETE', 'CELULAR', GRN);

  // The block that keeps the screen's contents out of the shot
  if (v >= C.shock && v < S.galeria[1]) {
    const on = Math.floor(v * 7.5) % 2 === 0 || v > C.shock + 0.5;
    s.rect(0, 286, W, 40, BLACK);  // below the face, so the scream stays visible
    if (on) center(s, 'CENSURADO', 294, WHITE, { scale: 3, outline: RED });
  }

  if (v >= C.slam && v < C.reassemble) {
    const k = 1 - phase(v, C.slam, C.slam + 0.12);
    center(s, 'BAIL!', 110 - Math.round(k * 30), RED, { scale: 5, outline: WHITE });
    if (v >= C.slam + 0.25) center(s, 'JUGULAR', 160, WHITE, { scale: 3 });
  }

  if (v >= C.p2_flash && v < C.p2_flash + 1.3) {
    const on = Math.floor(v * 10) % 2 === 0;
    s.rect(0, 70, W, 44, DIM, 0.75);
    center(s, 'PLAYER 2', 74, on ? CYAN : WHITE, { scale: 2 });
    center(s, 'HAS JOINED', 93, on ? WHITE : CYAN, { scale: 2 });
  }

  if (v >= C.phone_dies && v < C.high_score + 0.15) {
    center(s, '(???????)', 150, YEL, { scale: 3 });
  }
}

function sunburst(s, v) {
  // The special's rays behind the HUD: additive wedges spinning around the middle of the frame
  if (v < C.held_note || v >= S.special[1]) return;
  const cx = W / 2, cy = H * 0.38, a0 = v * 2.2;
  const strength = 0.22 * phase(v, C.held_note, C.held_note + 0.1);
  const col = hex('#ffb040');
  for (let i = 0; i < 12; i += 2) {
    const a = a0 + (i * Math.PI) / 6, b = a + Math.PI / 6;
    s.poly([[cx, cy], [cx + Math.cos(a) * 600, cy + Math.sin(a) * 600], [cx + Math.cos(b) * 600, cy + Math.sin(b) * 600]], col, strength, true);
  }
}

function flash(s, v) {
  const hits = [[C.slam, 0.14, hex('#ffffff')], [C.p2_flash, 0.14, hex('#ffffff')], [C.p2_hit, 0.1, hex('#ffffff')],
    [C.launch, 0.1, hex('#fff2a0')], [C.held_note, 0.2, hex('#ffd060')], [C.phone_dies, 0.16, hex('#cfe4ff')]];
  for (const [t, d, c] of hits) {
    if (v >= t && v < t + d) s.rect(0, 0, W, H, c, 0.85 * (1 - (v - t) / d));
  }
}

function highScore(s, v) {
  const a = phase(v, C.high_score, C.high_score + 0.18);
  s.rect(0, 0, W, H, DIM, 0.82 * a);
  if (a < 1) return;
  center(s, 'HIGH SCORES', 54, YEL, { scale: 3 });
  const rows = [['1', "PARD'JHONSON", '9.999.999', CYAN], ['2', 'POLÍCIA', '190', WHITE], ['3', 'BANANA SPLIT', '40', WHITE], ['4', 'CELULAR', '0', RED]];
  rows.forEach(([n, name, pts, col], i) => {
    const y = 98 + i * 24;
    const appear = C.high_score + 0.2 + i * 0.09;
    if (v < appear) return;
    drawText(s, n, 12, y, YEL, { outline: BLACK });
    drawText(s, name, 26, y, col, { outline: BLACK });
    drawText(s, pts, W - 12 - textWidth(BIG, pts), y, col, { outline: BLACK });
  });
  center(s, 'A SOLUÇÃO', 232, YEL, { scale: 3 });
  center(s, 'DE TODOS OS PROBLEMAS', 268, WHITE);
  center(s, 'DA VIDA', 282, YEL, { scale: 2 });
  center(s, 'PARDINGOWS', 330, WHITE, { font: MINI, scale: 3 });
  if (Math.floor(v * 3) % 2 === 0) center(s, 'PRESS START', 372, WHITE, { scale: 2 });
}

export function drawHud(s, v) {
  sunburst(s, v);
  flash(s, v);
  topBar(s, v);
  balance(s, v);
  if (v < C.high_score) {
    banners(s, v);
    trickString(s, v);
  }
  if (v >= C.high_score) highScore(s, v);
}
