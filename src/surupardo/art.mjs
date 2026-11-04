// Characters and props. Each character is drawn facing RIGHT into its own sprite,
// outlined, then blitted (optionally flipped) into the frame.
import { Surface, hex } from '../shared/engine.mjs';

export const C = {
  out: hex('#1a0d1f'),
  skin: hex('#a0623a'), skinD: hex('#6e3c1e'), skinL: hex('#c98552'),
  cap: hex('#f7f3ff'), capD: hex('#c7bfe6'),
  hair: hex('#ffd84a'), hairD: hex('#d8961c'),
  gold: hex('#ffd23f'), goldD: hex('#c48612'),
  black: hex('#0e0b14'), glint: hex('#c8faff'), white: hex('#ffffff'),
  mouth: hex('#3d0d1a'), tongue: hex('#ff5d7a'), lips: hex('#ff2e7e'),
  pink: hex('#ff3fb4'), pinkL: hex('#ffc2ea'), cyan: hex('#33e8ff'), cyanL: hex('#c9fbff'),
  purple: hex('#7b3fe4'), red: hex('#e8173c'), redD: hex('#8a0f2a'),
  pale: hex('#f6d5c3'), paleD: hex('#dcae98'), blond: hex('#f2d36b'), blondD: hex('#c9a43c'),
  polo: hex('#9fd3ff'), poloD: hex('#6aa6d9'), jeans: hex('#3b5bab'), jeansD: hex('#2a3f7a'),
};

const SPR_W = 48, SPR_H = 64, AX = 24, AY = 58; // sprite size and feet anchor, in sprite units
export const K = 2; // characters render at 2x art pixels, with a crisp 1px outline

// Proxy that multiplies every coordinate by k, so shapes are defined once in sprite units.
export function scaled(surf, k) {
  const set = (x, y, c) => surf.rect(Math.floor(x) * k, Math.floor(y) * k, k, k, c);
  return {
    set,
    rect: (x, y, w, h, c, a) => surf.rect(x * k, y * k, w * k, h * k, c, a),
    ellipse: (cx, cy, rx, ry, c, a) => surf.ellipse(cx * k, cy * k, rx * k, ry * k, c, a),
    ring: (cx, cy, r, t, c, a) => surf.ring(cx * k, cy * k, r * k, t * k, c, a),
    thick: (x0, y0, x1, y1, r, c) => surf.thick(x0 * k, y0 * k, x1 * k, y1 * k, r * k, c),
    poly: (pts, c, a) => surf.poly(pts.map(([x, y]) => [x * k, y * k]), c, a),
    line: (x0, y0, x1, y1, c) => {
      const n = Math.max(1, Math.abs(Math.round(x1) - Math.round(x0)), Math.abs(Math.round(y1) - Math.round(y0)));
      for (let i = 0; i <= n; i++) set(Math.round(x0 + (x1 - x0) * i / n), Math.round(y0 + (y1 - y0) * i / n), c);
    },
  };
}

function sprite() {
  const surf = new Surface(SPR_W * K, SPR_H * K);
  surf.ax = AX * K;
  surf.ay = AY * K;
  return [surf, scaled(surf, K)];
}

// ---------------------------------------------------------------- heads
// Smurf head centered at (x, y), facing right.
export function head(s, x, y, o = {}) {
  const f = !!o.female;
  if (f) { // shoulder-length hair behind
    s.ellipse(x - 5, y + 3, 4, 7, C.hair);
    s.ellipse(x - 4, y + 8, 4, 3.5, C.hair);
    s.ellipse(x - 7, y + 6, 1.5, 4, C.hairD);
  }
  s.ellipse(x - 6.5, y + 1, 2, 2.5, C.skinD);                 // ear
  s.ellipse(x, y, 7.5, 7, C.skinD);                           // skull (shadow side)
  s.ellipse(x + 1, y - 0.5, 6.5, 6.2, C.skin);
  s.ellipse(x + 3.5, y + 3, 4.5, 3.8, C.skin);                // cheeks / muzzle
  s.ellipse(x + 7.5, y + 1.2, 3, 2.6, C.skin);                // the nose
  s.set(x + 8, y, C.skinL); s.set(x + 9, y, C.skinL); s.set(x + 4, y + 1, C.skinL);

  // mouth
  const m = o.mouth || 'smile';
  if (m === 'open') { s.ellipse(x + 5, y + 5.5, 1.8, 1.6, C.mouth); s.set(x + 5, y + 6, C.tongue); }
  else if (m === 'o') { s.ellipse(x + 5.5, y + 5.5, 1.2, 1.2, C.mouth); }
  else {
    const mc = f ? C.lips : C.mouth;
    s.set(x + 3, y + 4, mc); s.set(x + 4, y + 5, mc); s.set(x + 5, y + 5, mc); s.set(x + 6, y + 5, mc); s.set(x + 7, y + 4, mc);
  }
  if (f) { s.set(x + 6, y + 6, C.lips); s.set(x + 5, y + 6, C.lips); }

  // eyes
  if (o.shades) {
    const sy = y - 3 + (o.shadesDown || 0);
    s.rect(x + 1, sy, 6, 2, C.black);
    s.set(x + 2, sy + 2, C.black); s.set(x + 5, sy + 2, C.black);
    s.line(x - 5, sy, x + 1, sy, C.black);
    if (o.shadesDown) { s.rect(x + 2, y - 3, 2, 1, C.white); s.set(x + 3, y - 3, C.black); }
    if (o.glint) { s.set(x + 5, sy, C.white); s.set(x + 6, sy, C.glint); }
  } else if (o.wink) {
    s.set(x + 3, y - 2, C.black); s.set(x + 4, y - 1, C.black); s.set(x + 5, y - 1, C.black); s.set(x + 6, y - 2, C.black);
    s.set(x + 6, y - 3, C.black);
  } else if (o.heartEyes) {
    s.rect(x + 3, y - 3, 3, 2, C.pink); s.set(x + 4, y - 1, C.pink);
  } else {
    s.rect(x + 3, y - 3, 3, 3, C.white);
    s.rect(x + 4, y - 2, 2, 2, C.black);
    s.set(x + 4, y - 2, C.white);
    if (f) { s.line(x + 3, y - 4, x + 6, y - 4, C.black); s.set(x + 7, y - 5, C.black); s.set(x + 2, y - 4, C.black); }
  }

  // phrygian cap (the classic white floppy hat)
  const r = f ? -6 : -5;
  s.ellipse(x - 1, y - 7, 8.5, 5, C.cap);
  s.ellipse(x + 4, y - 9, 5, 3.5, C.cap);
  s.ellipse(x + 8, y - 7.5, 2.8, 2.8, C.cap);
  s.ellipse(x + 9.5, y - 5, 1.7, 1.9, C.cap);
  s.rect(x - 8, y + r, 14, 2, C.cap);
  s.rect(x - 8, y + r + 1, 9, 1, C.capD);
  s.ellipse(x - 6, y - 8, 1.2, 2, C.capD);
  s.set(x + 6, y - 5, C.capD); s.set(x + 7, y - 4, C.capD);
  if (f) { // bangs + hoop earring
    s.ellipse(x + 1.5, y - 4.5, 4, 1.5, C.hair);
    s.set(x + 3, y - 4, C.hairD);
    s.ring(x - 6.5, y + 5, 1.6, 1, C.gold);
  }
}

// ---------------------------------------------------------------- full bodies
function arm(s, sx, sy, hx, hy, c) {
  s.thick(sx, sy, hx, hy, 1.3, c);
  s.ellipse(hx, hy, 1.9, 1.9, c);
}

// The brown Smurf. pose: 'stand' | 'walk' | 'sit'.
// hand / backHand: front/back hand position relative to the feet anchor (sit: seat anchor).
export function smurf(o = {}) {
  const [spr, s] = sprite();
  const x = AX, y = AY, b = o.bob || 0;
  const sit = o.pose === 'sit';
  const ty = sit ? y - 11 : y - 17;              // torso center
  const hy = (sit ? y - 24 : y - 30) + b;        // head center

  // back arm (behind body)
  const bh = o.backHand || [-4, sit ? -5 : -11];
  arm(s, x - 1, ty - 3 + b, x + bh[0], y + bh[1], C.skinD);

  // legs
  if (sit) { // thigh forward, knee, shin hanging over the stool edge
    s.rect(x + 1, y - 7, 9, 5, C.cap);
    s.ellipse(x + 10, y - 4.5, 2.5, 2.5, C.cap);
    s.rect(x + 8, y - 4, 4, 8, C.cap);
    s.rect(x + 8, y - 3, 1, 7, C.capD);
    s.ellipse(x + 12, y + 4.5, 3.5, 1.8, C.cap);
    s.rect(x + 1, y - 3, 7, 1, C.capD);
  } else {
    const p = o.step || 0, sw = o.pose === 'walk' ? Math.sin(p * Math.PI * 2) * 2.5 : 0;
    const lift = o.pose === 'walk' ? Math.max(0, Math.cos(p * Math.PI * 2)) * 1.5 : 0;
    s.rect(x - 4 - sw, y - 8, 3, 6, C.capD);
    s.ellipse(x - 2.5 - sw, y - 1.5, 3.2, 1.8, C.capD);
    s.rect(x + 1 + sw, y - 8 - lift, 3, 6, C.cap);
    s.ellipse(x + 3.5 + sw, y - 1.5 - lift, 3.2, 1.8, C.cap);
  }

  // torso, pants, tail
  s.ellipse(x, ty + b, 5.5, 6, C.skinD);
  s.ellipse(x + 1, ty - 0.5 + b, 4.5, 5.2, C.skin);
  const py = sit ? y - 5 : y - 10;
  s.ellipse(x, py, 6, 4.5, C.cap);
  s.rect(x - 6, py - 3, 12, 3, C.cap);
  s.rect(x - 6, py - 1, 3, 2, C.capD);
  s.ellipse(x - 7, py - 1, 2, 2, C.cap);
  // gold chain + pendant
  for (const [cx, cy] of [[-1, -5], [0, -4], [1, -3], [2, -3], [3, -2], [4, -3]]) s.set(x + cx, ty + cy + b, C.gold);
  s.set(x + 3, ty - 1 + b, C.gold); s.set(x + 3, ty + b, C.goldD);

  head(s, x + 1, hy, o);

  // front arm (+ held drink)
  const fh = o.hand || [4, sit ? -4 : -11];
  arm(s, x + 1, ty - 3 + b, x + fh[0], y + fh[1], C.skin);
  if (o.drink) cocktail(s, x + fh[0] + 1, y + fh[1] + 1, o.drinkLevel ?? 1);

  return spr.outline(C.out);
}

// The brown Smurfette in a white sequin mini dress.
export function smurfette(o = {}) {
  const [spr, s] = sprite();
  const x = AX, y = AY, b = o.bob || 0, t = o.t || 0;
  const ty = y - 18;
  const hy = y - 31 + b;

  const bh = o.backHand || [-4, -12];
  arm(s, x - 1, ty - 4 + b, x + bh[0], y + bh[1], C.skinD);

  const p = o.step || 0, sw = o.walk ? Math.sin(p * Math.PI * 2) * 2.5 : 0;
  s.rect(x - 3 - sw, y - 10, 2, 8, C.skinD);
  s.rect(x - 4 - sw, y - 2, 4, 2, C.capD); s.set(x - 4 - sw, y, C.capD);
  s.rect(x + 1 + sw, y - 10, 2, 8, C.skin);
  s.rect(x + sw, y - 2, 4, 2, C.cap); s.set(x + sw, y, C.cap);

  // neck/shoulders, then dress
  s.ellipse(x + 0.5, ty - 4 + b, 4.5, 3, C.skin);
  s.rect(x, ty - 9 + b, 2, 4, C.skin);
  s.poly([[x - 5, ty - 3 + b], [x + 5, ty - 3 + b], [x + 7, y - 8], [x - 7, y - 8]], C.cap);
  s.ellipse(x + 3, ty - 1 + b, 3, 2.5, C.cap);
  s.rect(x - 6, ty - 2 + b, 2, 12, C.capD);
  s.rect(x - 5, ty + 2 + b, 10, 1, C.lips);                 // waist belt
  s.line(x + 4, y - 8, x + 3, y - 12, C.skin);                 // side slit
  for (let i = 0; i < 6; i++) {                                // sequins sparkle
    const k = Math.floor(t * 12 + i * 7) % 9;
    s.set(x - 4 + ((i * 5 + k) % 9), ty + 1 + ((i * 3 + k) % 8) + b, k < 3 ? C.cyanL : C.pinkL);
  }

  head(s, x + 1, hy, { ...o, female: true });
  if (o.hairFlip) { // hair swung forward over the shoulder
    s.ellipse(x - 1 + o.hairFlip * 2, hy + 3, 3, 6, C.hair);
    s.set(x + o.hairFlip * 2, hy + 6, C.hairD);
  }

  const fh = o.hand || [4, -12];
  arm(s, x + 1, ty - 4 + b, x + fh[0], y + fh[1], C.skin);
  if (o.drink) cocktail(s, x + fh[0] + 1, y + fh[1] + 1, 1);

  return spr.outline(C.out);
}

// The square white guy. arms: [left, right] each 'down' | 'up' | 'out' | 'head' | 'offer'.
export function blocky(o = {}) {
  const [spr, s] = sprite();
  const x = AX, y = AY, b = o.bob || 0;
  const [la, ra] = o.arms || ['down', 'down'];
  const armRect = (side, pose) => {
    const ax = side < 0 ? x - 9 : x + 6;
    if (pose === 'up') s.rect(ax, y - 37 + b, 3, 12, side < 0 ? C.poloD : C.polo);
    else if (pose === 'out') s.rect(side < 0 ? x - 18 : x + 6, y - 24 + b, 12, 3, side < 0 ? C.poloD : C.polo);
    else if (pose === 'head') { s.rect(ax, y - 33 + b, 3, 8, C.polo); s.rect(side < 0 ? x - 9 : x + 3, y - 36 + b, 6, 3, C.polo); }
    else if (pose === 'offer') s.rect(x + 6, y - 22 + b, 10, 3, C.polo);
    else s.rect(ax, y - 24 + b, 3, 11, side < 0 ? C.poloD : C.polo);
    // square hands
    if (pose === 'up') s.rect(ax, y - 40 + b, 3, 3, C.pale);
    else if (pose === 'out') s.rect(side < 0 ? x - 21 : x + 18, y - 24 + b, 3, 3, C.pale);
    else if (pose === 'offer') s.rect(x + 16, y - 23 + b, 3, 3, C.pale);
    else if (pose === 'down') s.rect(ax, y - 13 + b, 3, 3, C.pale);
  };
  // legs + square shoes
  s.rect(x - 5, y - 10, 4, 8, C.jeans); s.rect(x + 1, y - 10, 4, 8, C.jeansD);
  s.rect(x - 6, y - 2, 5, 2, C.black); s.rect(x + 1, y - 2, 5, 2, C.black);
  // body + square tie
  s.rect(x - 6, y - 25 + b, 12, 15, C.polo);
  s.rect(x - 6, y - 25 + b, 3, 15, C.poloD);
  s.rect(x - 1, y - 24 + b, 2, 2, C.red); s.rect(x - 1, y - 22 + b, 2, 6, C.redD);
  // cube head
  s.rect(x - 6, y - 38 + b, 12, 12, C.pale);
  s.rect(x - 6, y - 38 + b, 2, 12, C.paleD);
  s.rect(x - 6, y - 40 + b, 12, 3, C.blond); s.rect(x - 6, y - 37 + b, 3, 2, C.blondD);
  s.rect(x - 4, y - 34 + b, 2, 2, C.black); s.rect(x + 2, y - 34 + b, 2, 2, C.black);
  s.rect(x - 2, y - 29 + b, 4, 1, o.sad ? C.out : C.mouth);
  if (o.sad) { s.set(x - 3, y - 28 + b, C.mouth); s.set(x + 2, y - 28 + b, C.mouth); }
  else { s.set(x - 5, y - 31 + b, C.tongue); s.set(x + 4, y - 31 + b, C.tongue); }
  armRect(-1, la);
  armRect(1, ra);
  if (ra === 'offer') squareFlower(s, x + 17, y - 23 + b, o.wilt || 0);
  return spr.outline(C.out);
}

// Place a character sprite with its feet (or seat) anchor at frame pixel (x, y).
export function put(frame, spr, x, y, opts = {}) {
  frame.draw(spr, x - spr.ax, y - spr.ay, opts);
}

// ---------------------------------------------------------------- props
// Martini glass with its base at (x, y). level 0..1 = how full.
export function cocktail(s, x, y, level = 1) {
  s.poly([[x - 3.5, y - 7], [x + 3.5, y - 7], [x + 0.5, y - 3]], C.cyanL);
  if (level > 0) {
    const top = y - 3 - 3.5 * level;
    s.poly([[x - 3 * level, top], [x + 3 * level + 1, top], [x + 0.5, y - 3.5]], C.pink);
    s.set(x + 2, y - 8, C.red); s.set(x + 3, y - 8, C.red);
  }
  s.rect(x, y - 3, 1, 2, C.cyanL);
  s.rect(x - 2, y - 1, 5, 1, C.cyanL);
}

export function squareFlower(s, x, y, wilt = 0) {
  s.rect(x, y - 1 - (wilt > 0.5 ? 0 : 6), 1, wilt > 0.5 ? 2 : 7, hex('#3fbf4a'));
  const fx = wilt > 0.5 ? x + 2 : x - 1, fy = wilt > 0.5 ? y - 1 : y - 10;
  s.rect(fx, fy, 3, 3, hex('#ff5d7a'));
  s.set(fx + 1, fy + 1, C.gold);
}

// Tiny photo frame of the square boyfriend.
export function photo(s, x, y, down = 0) {
  if (down) { s.rect(x - 1, y - 2, 9, 2, C.goldD); s.rect(x - 1, y - 2, 9, 1, C.gold); return; }
  s.rect(x, y - 9, 7, 9, C.gold);
  s.rect(x + 1, y - 8, 5, 7, hex('#9fd3ff'));
  s.rect(x + 2, y - 7, 3, 3, C.pale);
  s.set(x + 2, y - 6, C.black); s.set(x + 4, y - 6, C.black);
  s.rect(x + 2, y - 4, 3, 2, C.polo);
  s.set(x + 1, y - 10, C.goldD);
}

export function heart(s, x, y, c = C.pink) {
  for (const [dx, dy] of [[1, 0], [3, 0], [0, 1], [1, 1], [2, 1], [3, 1], [4, 1], [0, 2], [1, 2], [2, 2], [3, 2], [4, 2], [1, 3], [2, 3], [3, 3], [2, 4]])
    s.set(x + dx, y + dy, c);
}

export function sparkle(s, x, y, size, c = C.white) {
  s.set(x, y, c);
  for (let i = 1; i <= size; i++) { s.set(x + i, y, c); s.set(x - i, y, c); s.set(x, y + i, c); s.set(x, y - i, c); }
}

// Dancing crowd silhouette (some wear the smurf cap). Drawn straight into the frame.
export function dancer(s, x, y, phase, body, rim, cap = false) {
  const up = Math.sin(phase * Math.PI * 2);
  const b = Math.round(Math.abs(up) * 2);
  s.ellipse(x, y - 14 - b, 4, 4, body);
  if (cap) { s.ellipse(x - 1, y - 18 - b, 5, 3, body); s.ellipse(x + 3, y - 19 - b, 2.5, 2.5, body); }
  s.rect(x - 4, y - 10 - b, 8, 12, body);
  const la = up > 0 ? -1 : 1;
  s.thick(x - 3, y - 9 - b, x - 7, y - 9 - b - 7 * la, 1.2, body);
  s.thick(x + 3, y - 9 - b, x + 7, y - 9 - b + 7 * la, 1.2, body);
  for (let i = 0; i < 9; i++) s.set(x + 4, y - 9 - b + i, rim);
  s.set(x + 3, y - 16 - b, rim); s.set(x + 4, y - 15 - b, rim);
}
