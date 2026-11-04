// Environments. Each scene draws a full 135x240 frame for video time v.
// Character hand offsets are in sprite units (x K on screen); everything else is art pixels.
import { W, H, hex, lerpColor, dither, hash, clamp } from '../shared/engine.mjs';
import { BIG, eachPixel, textWidth } from '../shared/font.mjs';
import { C, K, scaled, smurf, smurfette, blocky, put, cocktail, photo, heart, sparkle, dancer } from './art.mjs';
import { beatPos, beatPhase, beatNum, kick } from './timeline.mjs';

const P = {
  night0: hex('#0b0620'), night1: hex('#2e0f4a'),
  brick: hex('#4a1d3a'), mortar: hex('#33122b'), cornice: hex('#2a0d24'),
  board: hex('#17081f'), tubeOff: hex('#4a1b3d'),
  wall: hex('#2a1240'), panel: hex('#1f0d33'), mirror: hex('#3a1d5a'), shelf: hex('#6b3a22'),
  wood: hex('#8a4a26'), woodL: hex('#c06a3a'), chrome: hex('#d8d8f0'), chromeD: hex('#8a8aa8'),
  tuft: hex('#8a1238'), tuftD: hex('#5a0a24'), tuftL: hex('#b52a55'),
  floorA: hex('#1b0e29'), floorB: hex('#3a1d52'),
  ceiling: hex('#140822'), shadow: hex('#0a0412'),
  tileA: hex('#5b2a6e'), tileB: hex('#4c2160'), grout: hex('#2e1040'),
  water: hex('#1fb5c9'), waterL: hex('#7ff3ff'), waterD: hex('#13889c'),
  porcelain: hex('#efe8ff'), porcelainD: hex('#bdb2e0'),
  leaf: hex('#2fae5b'), leafD: hex('#1d7a3d'), trunk: hex('#7a4a22'),
  speaker: hex('#0d0a12'), cone: hex('#3a3550'),
};
const NEON = [C.pink, C.cyan, hex('#ffe14a'), hex('#b26bff'), hex('#4dff9a')];

// ---------------------------------------------------------------- neon text
// Neon tube text with an additive glow halo. on = 0..1 brightness.
export function neonText(s, str, x, y, color, scale = 1, on = 1) {
  if (on <= 0) {
    eachPixel(BIG, str, x, y, scale, (px, py) => s.set(px, py, P.tubeOff));
    return;
  }
  const lit = [];
  eachPixel(BIG, str, x, y, scale, (px, py) => lit.push(px, py));
  const R = scale > 1 ? 3 : 2;
  for (let i = 0; i < lit.length; i += 2)
    for (let oy = -R; oy <= R; oy++)
      for (let ox = -R; ox <= R; ox++) {
        const d = Math.hypot(ox, oy);
        if (d > 0 && d <= R) s.add(lit[i] + ox, lit[i + 1] + oy, color, on * 0.05 * (R + 1 - d));
      }
  const core = lerpColor(color, C.white, 0.65);
  for (let i = 0; i < lit.length; i += 2) {
    const px = lit[i], py = lit[i + 1];
    s.set(px, py, scale > 1 && (px - x) % scale === 0 && (py - y) % scale === 0 ? core : color);
  }
}
const centered = (str, scale = 1) => 67 - Math.floor(textWidth(BIG, str, scale) / 2);

// ---------------------------------------------------------------- shared bits
function gradientSky(s, y0, y1) {
  for (let y = y0; y < y1; y++) {
    const t = (y - y0) / (y1 - y0);
    for (let x = 0; x < W; x++) s.set(x, y, dither(x, y, t) ? P.night1 : P.night0);
  }
}

function discoBall(s, cx, cy, r, v) {
  s.line(cx, 0, cx, cy - r, P.chromeD);
  const tiles = [hex('#5a5f80'), hex('#9aa0c0'), hex('#d9dcf0'), C.white, C.cyanL, C.pinkL];
  for (let y = Math.floor(cy - r); y <= cy + r; y++)
    for (let x = Math.floor(cx - r); x <= cx + r; x++) {
      const dx = (x + 0.5 - cx) / r, dy = (y + 0.5 - cy) / r;
      if (dx * dx + dy * dy > 1) continue;
      const u = Math.floor(Math.asin(clamp(dx / Math.sqrt(1 - dy * dy + 1e-6), -1, 1)) * 4 + v * 6);
      const k = Math.floor(hash(u * 13.1 + Math.floor((y - cy) / 2) * 7.7 + Math.floor(v * 10) * 0.37) * 10);
      s.set(x, y, tiles[k < 4 ? 0 : k < 7 ? 1 : Math.min(tiles.length - 1, k - 5)]);
    }
  s.glow(cx, cy, r + 6, C.white, 0.25);
}

// Sweeping light beams from (cx, cy). power scales brightness.
function beams(s, cx, cy, v, power = 1) {
  for (let i = 0; i < 4; i++) {
    const a = Math.PI / 2 + Math.sin(v * (1.3 + i * 0.4) + i * 2) * 0.9;
    const len = 280, wdt = 0.09;
    s.poly([[cx, cy], [cx + Math.cos(a - wdt) * len, cy + Math.sin(a - wdt) * len], [cx + Math.cos(a + wdt) * len, cy + Math.sin(a + wdt) * len]],
      NEON[i % NEON.length], 0.09 * power, true);
  }
}

function wallDots(s, v, n = 18, maxY = 130) {
  for (let i = 0; i < n; i++) {
    const x = ((hash(i) * W + v * 22 * (i % 2 ? 1 : -1)) % W + W) % W;
    const y = 20 + hash(i + 50) * (maxY - 20);
    const c = NEON[i % NEON.length];
    s.add(x, y, c, 0.9); s.add(x + 1, y, c, 0.4); s.add(x - 1, y, c, 0.4); s.add(x, y + 1, c, 0.4); s.add(x, y - 1, c, 0.4);
  }
}

function checkerFloor(s, y0, tint = 0) {
  for (let y = y0; y < H; y++)
    for (let x = 0; x < W; x++)
      s.set(x, y, (Math.floor(x / 9) + Math.floor((y - y0) / 7)) % 2 ? P.floorB : P.floorA);
  if (tint) for (let y = y0; y < y0 + 30; y++) for (let x = 0; x < W; x++) s.add(x, y, C.pink, tint * (1 - (y - y0) / 30));
}

export function crowd(s, v, y = 244, energy = 1) {
  const bp = beatPos(v);
  [6, 27, 48, 70, 92, 113, 132].forEach((x, i) => {
    const ph = bp * 0.5 * energy + (i % 2) * 0.5;
    dancer(s, x, y - Math.round(kick(v) * 3 * energy) * (i % 2), ph, hex('#0f0619'), i % 2 ? C.pink : C.cyan, i % 3 === 1);
  });
}

// ---------------------------------------------------------------- EXTERIOR
const FLICKER = [[0, 0], [0.05, 1], [0.09, 0], [0.16, 1], [0.2, 0.3], [0.24, 1]];
export const neonLevel = v => { let l = 0; for (const [t, on] of FLICKER) if (v >= t) l = on; return l; };
export const DOOR = { x: 67, y: 168 };

export function exterior(s, v, smurfX) {
  const on = neonLevel(v);
  gradientSky(s, 0, 62);
  for (let i = 0; i < 26; i++) {
    const x = hash(i) * W, y = hash(i + 100) * 58;
    if (hash(i + Math.floor(v * 5)) > 0.25) s.set(x, y, hash(i + 3) > 0.6 ? C.white : hex('#8a7fb8'));
  }
  for (let i = 0; i < 9; i++) { // distant skyline
    const bw = 10 + hash(i + 9) * 14, bx = i * 16 - 4, bh = 14 + hash(i + 20) * 26;
    s.rect(bx, 62 - bh, bw, bh, hex('#1a0b30'));
    for (let wy = 62 - bh + 3; wy < 60; wy += 4) for (let wx = bx + 2; wx < bx + bw - 2; wx += 3)
      if (hash(wx * 3 + wy * 7) > 0.7) s.set(wx, wy, hex('#e8b94a'));
  }
  // facade
  s.rect(0, 60, W, 155, P.brick);
  for (let y = 60, row = 0; y < 215; y += 4, row++) {
    s.rect(0, y, W, 1, P.mortar);
    for (let x = (row % 2) * 4; x < W; x += 8) s.rect(x, y + 1, 1, 3, P.mortar);
  }
  s.rect(0, 56, W, 5, P.cornice); s.rect(0, 56, W, 1, hex('#5a2a4a'));

  // sign board + neon
  s.rect(9, 64, 117, 44, P.board);
  s.rect(9, 64, 117, 1, hex('#3a1a40')); s.rect(9, 107, 117, 1, hex('#05020a'));
  if (on > 0) s.glow(67, 88, 80, C.pink, on * 0.22);
  neonText(s, 'CASA DE SWING', centered('CASA DE SWING'), 68, C.cyan, 1, on);
  neonText(s, 'SURUPARDO', centered('SURUPARDO', 2), 80, C.pink, 2, on);
  neonText(s, '♥ DESDE 1984 ♥', centered('♥ DESDE 1984 ♥'), 97, hex('#ffe14a'), 1, on);

  // windows with dancing silhouettes
  for (const wx of [5, 106]) {
    s.rect(wx, 124, 24, 34, hex('#2a0d24'));
    s.rect(wx + 2, 126, 20, 30, on ? hex('#ff7ad9') : hex('#5a1f4a'));
    if (on) dancer(s, wx + 12, 160, beatPos(v) * 0.5 + wx, hex('#5a0f4a'), hex('#ffb8ec'), wx > 50);
    for (let y = 128; y < 156; y += 3) s.rect(wx + 2, y, 20, 1, hex('#c2409f'), 0.5);
    s.rect(wx, 158, 24, 2, hex('#5a2a4a'));
  }

  // big door + striped awning
  s.rect(42, 118, 51, 97, C.goldD);
  s.rect(44, 120, 47, 95, hex('#3a0f30'));
  for (let y = 120; y < 215; y++) s.rect(45, y, 45, 1, lerpColor(hex('#ff7ad9'), hex('#6a1658'), (y - 120) / 95), on ? 1 : 0.35);
  if (on) s.glow(67, 150, 30, C.pinkL, 0.35);
  for (let x = 36; x < 99; x++) {
    const stripe = Math.floor((x - 36) / 5) % 2 ? C.pink : C.white;
    s.rect(x, 106, 1, 10 + ((x - 36) % 5 === 2 ? 1 : 0), stripe);
  }
  s.rect(35, 105, 65, 1, hex('#2a0d24'));

  // sidewalk + velvet rope
  s.rect(0, 215, W, 25, hex('#2a1a3a'));
  s.rect(0, 215, W, 1, hex('#4b3563'));
  for (let x = 0; x < W; x += 18) s.rect(x, 216, 1, 24, hex('#22142f'));
  if (on) for (let y = 216; y < 240; y++) for (let x = 42; x < 93; x++) s.add(x, y, C.pink, 0.18 * (1 - (y - 216) / 24));
  for (const px of [8, 34, 100, 126]) { s.rect(px, 198, 2, 17, C.gold); s.ellipse(px + 1, 197, 2, 2, C.gold); }
  for (const [a, b2] of [[9, 35], [101, 127]])
    for (let x = a; x <= b2; x++) s.rect(x, 201 + Math.round(Math.sin((x - a) / (b2 - a) * Math.PI) * 5), 1, 2, C.red);

  // our hero strutting in on the beat
  const bp = beatPos(v), swing = Math.sin(bp * Math.PI) * 3;
  put(s, smurf({
    pose: 'walk', step: bp / 2, bob: beatPhase(v) < 0.5 ? 0 : -1, shades: true, glint: beatNum(v) % 2 === 0,
    hand: [4 + swing, -12], backHand: [-4 - swing, -12],
  }), smurfX, 216);
}

// ---------------------------------------------------------------- BAR
export const BAR_TOP = 128;
export const SEAT = [28, 165];
export const BARTENDER_X = 104;

// st: { smurf: smurf() opts, smurfette: {x, ...opts} | null, drinkX, drinkSpeed, photoDown,
//       crowd, beams, aura, auraT, signOn }
export function bar(s, v, st = {}) {
  const s2 = scaled(s, K);
  // wall + ceiling
  s.rect(0, 0, W, BAR_TOP, P.wall);
  for (let x = 4; x < W; x += 9) s.rect(x, 18, 1, BAR_TOP - 18, P.panel);
  s.rect(0, 0, W, 18, P.ceiling);
  // mirror + shelves + bottles
  s.rect(50, 62, 85, 66, P.mirror);
  for (let i = 0; i < 4; i++) s.line(58 + i * 22, 127, 74 + i * 22, 62, hex('#4a2a70'));
  s.glow(92, 95, 45, C.cyan, 0.12);
  const bottleCols = [hex('#2fd16a'), hex('#e8b94a'), hex('#ff5d7a'), hex('#5ac8ff'), hex('#b26bff'), hex('#f2f2f2')];
  for (const sy of [84, 108]) {
    s.rect(50, sy, 85, 2, P.shelf);
    for (let i = 0; i < 13; i++) {
      const bx = 53 + i * 6 + Math.floor(hash(i + sy) * 2), bh = 7 + Math.floor(hash(i * 3 + sy) * 5);
      const col = bottleCols[Math.floor(hash(i * 7 + sy) * bottleCols.length)];
      s.rect(bx, sy - bh, 3, bh, col);
      s.rect(bx + 1, sy - bh - 2, 1, 2, col);
      s.set(bx, sy - bh + 1, C.white);
      s.rect(bx, sy - 4, 3, 2, hex('#f2e9d0'));
    }
  }
  neonText(s, '♥', 13, 64, C.pink, 3, 1);
  neonText(s, 'SURUPARDO', centered('SURUPARDO'), 46, C.pink, 1, st.signOn ?? 1);
  discoBall(s, 67, 30, 8, v);
  wallDots(s, v);

  // bartender, behind the counter
  const sf = st.smurfette;
  if (sf) put(s, smurfette({ ...sf, t: v }), sf.x, sf.y ?? BAR_TOP + 30, { flip: sf.flip ?? true });

  // counter
  s.rect(0, BAR_TOP, W, 3, P.wood); s.rect(0, BAR_TOP, W, 1, P.woodL);
  s.rect(0, BAR_TOP + 3, W, 1, P.chrome);
  s.rect(0, BAR_TOP + 4, W, 26, P.tuft);
  for (let y = BAR_TOP + 7, r = 0; y < BAR_TOP + 28; y += 6, r++)
    for (let x = (r % 2) * 5 + 2; x < W; x += 10) {
      s.set(x, y, P.tuftD); s.set(x + 1, y, P.tuftD); s.set(x, y - 1, P.tuftL);
      s.line(x - 4, y - 3, x, y, P.tuftD, 0.4); s.line(x + 5, y - 3, x + 1, y, P.tuftD, 0.4);
    }
  s.rect(0, BAR_TOP + 30, W, 2, P.chrome);
  checkerFloor(s, BAR_TOP + 32, 0.15);

  // props on the counter (2x like the characters)
  if (st.photo !== false) photo(s2, 31, BAR_TOP / K, st.photoDown ? 1 : 0);
  if (st.drinkX != null) {
    cocktail(s2, st.drinkX / K, BAR_TOP / K, 1);
    if (st.drinkSpeed) for (let i = 1; i < 4; i++) s.rect(st.drinkX + 6 + i * 5, BAR_TOP - 12 + i * 2, 4, 1, C.white, 0.6);
  }

  // stool + our smurf
  const [sx, sy] = SEAT;
  s.rect(sx - 1, sy + 6, 3, 26, P.chrome); s.rect(sx - 1, sy + 6, 1, 26, C.white);
  s.ellipse(sx, sy + 32, 10, 2, P.chromeD);
  s.ellipse(sx + 1, sy + 3, 13, 3.5, C.red); s.rect(sx - 10, sy + 1, 22, 1, hex('#ff6a85'));

  if (st.aura) aura(s, v, st);
  const gold = st.aura ? (c => (c === C.out ? C.gold : c)) : null;
  put(s, smurf({ pose: 'sit', shades: true, ...st.smurf }), sx, sy, { map: gold });

  if (st.beams) beams(s, 67, 30, v, st.beams);
  if (st.crowd) crowd(s, v, 244, st.crowd);
}

export const AURA_CENTER = [SEAT[0] + 4, SEAT[1] - 44];
function aura(s, v, st) {
  const [cx, cy] = AURA_CENTER;
  const a = st.aura, rot = v * 1.6;
  for (let i = 0; i < 12; i++) {
    const t0 = rot + i * Math.PI / 6, w = 0.12;
    s.poly([[cx, cy], [cx + Math.cos(t0 - w) * 180, cy + Math.sin(t0 - w) * 180], [cx + Math.cos(t0 + w) * 180, cy + Math.sin(t0 + w) * 180]],
      i % 2 ? C.gold : hex('#ff9a3c'), 0.22 * a, true);
  }
  s.glow(cx, cy, 48, C.gold, 0.7 * a);
  const since = v - (st.auraT ?? v);
  if (since >= 0 && since < 0.6) s.ring(cx, cy, 8 + since * 220, 3, hex('#fff2a8'), 1 - since / 0.6);
  for (let i = 0; i < 16; i++) {
    const ang = hash(i) * 6.28 + v * 0.8, r = 30 + hash(i + 40) * 45;
    if (hash(i + Math.floor(v * 8)) > 0.45) sparkle(s, cx + Math.cos(ang) * r, cy + Math.sin(ang) * r * 0.8, 1 + (i % 2), i % 3 ? C.gold : C.white);
  }
}

// ---------------------------------------------------------------- HOT TUB
export function hotTub(s, v) {
  for (let y = 0; y < 136; y++)
    for (let x = 0; x < W; x++) {
      const g = x % 11 === 0 || y % 11 === 0;
      s.set(x, y, g ? P.grout : (Math.floor(x / 11) + Math.floor(y / 11)) % 2 ? P.tileA : P.tileB);
    }
  for (let y = 136; y < H; y++)
    for (let x = 0; x < W; x++) s.set(x, y, (x + y) % 14 === 0 || (x - y + 280) % 14 === 0 ? hex('#3a1550') : hex('#2a0f3c'));
  neonText(s, 'VIP', centered('VIP', 2), 34, C.cyan, 2, 1);
  neonText(s, '♥', 36, 38, C.pink, 1, 1);
  neonText(s, '♥', 94, 38, C.pink, 1, 1);

  // three pairs of little white pants on the hooks: everyone in the tub is pelado
  s.rect(4, 60, 70, 2, P.shelf);
  for (let i = 0; i < 3; i++) {
    const px = 7 + i * 23, sway = Math.round(Math.sin(v * 3 + i) * 0.8);
    s.rect(px + 8, 62, 2, 3, P.chromeD);
    s.rect(px + sway, 65, 18, 8, C.cap);
    s.rect(px + sway, 73, 8, 12, C.cap); s.rect(px + 10 + sway, 73, 8, 12, C.cap);
    s.rect(px + sway, 65, 18, 2, C.capD);
    s.rect(px + 8 + sway, 73, 2, 4, C.capD);
    s.ellipse(px + 9 + sway, 69, 2, 2, C.capD);  // the tail hole
    s.rect(px - 1 + sway, 65, 1, 20, C.out); s.rect(px + 18 + sway, 65, 1, 20, C.out);
  }
  // palm in a pot, very Miami 1984
  s.thick(122, 132, 117, 72, 1.8, P.trunk);
  for (let i = 0; i < 6; i++) {
    const a = -Math.PI / 2 + (i - 2.5) * 0.6 + Math.sin(v * 2 + i) * 0.05;
    s.thick(117, 72, 117 + Math.cos(a) * 22, 72 + Math.sin(a) * 12 + 10, 1.8, i % 2 ? P.leaf : P.leafD);
  }

  // tub: side, rim, water
  const cx = 67, cy = 152;
  s.ellipse(cx, cy + 28, 64, 12, P.porcelainD);
  s.rect(cx - 64, cy, 128, 28, P.porcelainD);
  for (let x = cx - 56; x < cx + 64; x += 14) s.rect(x, cy + 8, 1, 26, hex('#a79bd1'));
  s.ellipse(cx, cy, 64, 20, P.porcelain);
  s.ellipse(cx, cy + 1, 59, 16, P.porcelainD);
  s.ellipse(cx, cy + 2, 57, 14.5, P.water);
  s.ellipse(cx, cy + 6, 48, 8, P.waterD);
  s.glow(cx, cy + 2, 56, C.cyan, 0.25);

  // three in the tub, cut at the waterline
  const WATER = cy - 1;
  const bob = i => Math.round(Math.sin(beatPos(v) * Math.PI + i * 1.3));
  put(s, smurf({ shades: true, glint: beatNum(v) % 2 === 0, hand: [6, -30 + bob(0)], backHand: [-4, -12] }), 21, 186 + bob(0), { maxY: WATER });
  put(s, smurfette({ t: v, wink: beatPhase(v) > 0.5 && beatNum(v) % 4 === 3, hand: [7, -34], drink: true }), 68, 193 + bob(1), { maxY: WATER, flip: true });
  put(s, smurf({ mouth: 'open', hand: [6, -24], backHand: [-5, -12] }), 114, 186 + bob(2), { maxY: WATER, flip: true });
  for (const [bx, i] of [[23, 0], [66, 1], [112, 2]]) { // ripples around bodies
    const r = 15 + ((v * 6 + i) % 3);
    s.ellipse(bx, WATER, r, 2.5, P.waterL, 0.35);
    s.ellipse(bx, WATER, r - 3, 1.5, P.water);
  }
  for (let i = 0; i < 14; i++) s.rect(18 + ((i * 17 + v * 14) % 100), cy + 4 + (i % 4) * 2, 3, 1, P.waterL, 0.8);
  for (let i = 0; i < 12; i++) { // bubbles
    const ph = (v * 1.7 + hash(i)) % 1, bx = 20 + hash(i + 3) * 95, by = cy + 10 - ph * 8;
    if (ph < 0.85) s.ring(bx, by, 1.5 + ph, 1, P.waterL);
    else sparkle(s, bx, by - 1, 1, P.waterL);
  }
  for (let i = 0; i < 9; i++) { // steam
    const ph = (v * 0.35 + hash(i + 11)) % 1;
    const x = 15 + hash(i + 7) * 105 + Math.sin(v * 2 + i) * 4, y = cy - 8 - ph * 100;
    s.ellipse(x, y, 8 + ph * 10, 5 + ph * 7, C.white, 0.15 * Math.sin(ph * Math.PI));
  }
  for (let i = 0; i < 4; i++) { // hearts drifting up
    const ph = (v * 0.8 + i / 4) % 1;
    heart(s, 64 + Math.sin(ph * 9 + i) * 12, 96 - ph * 50, ph < 0.8 ? C.pink : C.pinkL);
  }
}

// ---------------------------------------------------------------- DANCE FLOOR
export const FLOOR_Y = 140;
export const GUY = { x: 62, y: 168 };

// st: { guy: blocky() opts & {x, y, built, pop}, smurfette: {x, ...opts} | null, frame: 0..1, cloud, xMark }
export function danceFloor(s, v, st = {}) {
  s.rect(0, 0, W, FLOOR_Y, hex('#1c0b2e'));
  for (let x = 6; x < W; x += 9) s.rect(x, 18, 1, FLOOR_Y - 18, hex('#170926'));
  neonText(s, 'PISTA', centered('PISTA'), 34, hex('#4dff9a'), 1, 1);
  wallDots(s, v, 24, FLOOR_Y - 10);
  const k = kick(v, 10);
  for (const sx of [0, 117]) { // speakers pumping on the kick
    s.rect(sx, 72, 18, 68, P.speaker); s.rect(sx, 72, 18, 1, hex('#2a2540'));
    for (const [cy2, r] of [[86, 5], [108, 7], [128, 5]]) {
      s.ellipse(sx + 9, cy2, r + k, r + k, P.cone);
      s.ellipse(sx + 9, cy2, 2 + k, 2 + k, hex('#6a6488'));
    }
  }
  const bp = beatPos(v);
  [[24, 0], [42, 1], [86, 2], [104, 3]].forEach(([x, i]) =>
    dancer(s, x, FLOOR_Y + 2, bp * 0.5 + i * 0.25, hex('#120820'), NEON[i], i % 2 === 0));

  // light-up floor, re-patterned every beat
  const bn = beatNum(v);
  for (let r = 0; r < 10; r++)
    for (let c = 0; c < 9; c++) {
      const x = c * 15, y = FLOOR_Y + r * 10;
      const lit = hash(c * 3.1 + r * 7.3 + bn * 1.7) > 0.62;
      const col = NEON[(c + r + bn) % NEON.length];
      s.rect(x, y, 15, 10, P.shadow);
      s.rect(x + 1, y + 1, 13, 8, lit ? lerpColor(col, P.shadow, 0.3 - 0.2 * kick(v)) : lerpColor(col, P.shadow, 0.88));
      if (lit) s.rect(x + 2, y + 2, 4, 1, C.white, 0.35);
    }

  const g = st.guy;
  if (st.frame && g) { // big neon square framing the square guy
    const sz = 72 + Math.round(kick(v) * 4);
    const fx = Math.round(g.x - sz / 2), fy = Math.round(g.y - 42 - sz / 2);
    for (let i = 0; i < 2; i++) {
      s.rect(fx - i, fy - i, sz + 2 * i, 1, C.cyan, st.frame); s.rect(fx - i, fy + sz + i - 1, sz + 2 * i, 1, C.cyan, st.frame);
      s.rect(fx - i, fy - i, 1, sz + 2 * i, C.cyan, st.frame); s.rect(fx + sz + i - 1, fy - i, 1, sz + 2 * i, C.cyan, st.frame);
    }
    s.glow(g.x, g.y - 42, 50, C.cyan, 0.2 * st.frame);
  }
  if (g) {
    // built = 1..3 reveals him block by block (legs, body, head), like placing blocks
    const minY = g.built == null ? -Infinity : [g.y + 2, g.y - 21, g.y - 51, -Infinity][g.built];
    put(s, blocky(g), g.x, g.y, { minY });
    if (g.pop) s.glow(g.x, g.pop.y, 24, C.white, g.pop.a);
  }
  if (st.smurfette) {
    const sf = st.smurfette;
    put(s, smurfette({ ...sf, t: v }), sf.x, sf.y ?? 180, { flip: sf.flip ?? true });
  }
  if (st.cloud) rainCloud(s, g.x, g.y - 94, v, st.cloud);
  if (st.xMark) bigX(s, g.x, g.y - 42, st.xMark);
}

function rainCloud(s, x, y, v, a) {
  const c = hex('#6a6488');
  s.ellipse(x - 7, y, 8, 5, c, a); s.ellipse(x + 5, y - 2, 9, 6, c, a); s.ellipse(x, y + 3, 13, 4, c, a);
  for (let i = 0; i < 8; i++) {
    const ph = (v * 3 + i / 8) % 1;
    s.rect(x - 11 + i * 3, y + 6 + ph * 22, 1, 3, C.cyan, a * (1 - ph));
  }
}

function bigX(s, x, y, a) {
  const r = 26 * Math.min(1, a * 1.2);
  for (let o = -2; o <= 2; o++) {
    s.line(x - r + o, y - r, x + r + o, y + r, C.red);
    s.line(x + r + o, y - r, x - r + o, y + r, C.red);
  }
}
