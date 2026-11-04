// Objects and the cut-out character. Each prop draws around its own local origin; callers place
// it with g.save()/translate()/scale(). Inks: P pink, B blue, Y yellow (tones 0..1, <1 = halftone).
import { arc, ellipse, rect, roundRect, tornRect, hash, clamp, lerp } from './engine.mjs';
import { drawText, measure, stamp } from './type.mjs';

export const INK = {
  line: { B: 1 },
  dark: { P: 1, B: 1 },
  pink: { P: 1 },
  blue: { B: 1 },
  yellow: { Y: 1 },
  red: { P: 1, Y: 1 },
  green: { B: 1, Y: 1 },
  skin: { Y: 1, P: 0.55, B: 0.3 },
  coffee: { P: 0.85, B: 1, Y: 0.55 },
  cafeLeite: { Y: 0.8, P: 0.5, B: 0.22 },
  wood: { Y: 0.75, P: 0.42, B: 0.12 },
  paper: {},
};
const KNOCK = { mode: 'knock' };

// ---------------------------------------------------------------- the mascot: SMURF PARDO
// Cut-out riso take on the PARDINGOWS mascot: brown skin, white floppy phrygian cap, white
// pants + shoes, gold chain, black shades. Origin at the feet, ~290 units tall, facing +x.
// Angles: 0 = limb hanging down, + = forward. mouth: smile | wavy | o | grin.
const limb = (o, a1, a2, l1, l2) => {
  const k = [o[0] + Math.sin(a1) * l1, o[1] + Math.cos(a1) * l1];
  return [o, k, [k[0] + Math.sin(a1 + a2) * l2, k[1] + Math.cos(a1 + a2) * l2]];
};
const CAP = [[-50, -2], [-54, -34], [-42, -62], [-16, -80], [16, -82], [42, -70], [60, -50], [70, -26], [64, -10],
  [52, -14], [46, -26], [38, -20], [10, -18], [-20, -14]];
const CAP_SHADE = [[-50, -2], [-54, -34], [-42, -62], [-24, -74], [-30, -40], [-34, -8]];
const MOUTHS = {
  smile: [[8, 31], [15, 35], [24, 35.5], [30, 32]],
  wavy: [[6, 33], [11, 30], [16, 35], [21, 30], [26, 35], [31, 31]],
  grin: [[4, 29], [17, 37], [33, 30]],
};
// Joint positions for a pose, without drawing (scenes use it to place things behind him).
export function smurfRig(pose = {}) {
  const { lean = 0, bob = 0, head = 0, arms = [[0.25, -0.4], [-0.2, -0.3]], legs = [[0.05, 0], [-0.05, 0]] } = pose;
  const hip = [0, -84 + bob];
  const up = (len, a = lean) => [hip[0] + Math.sin(a) * len, hip[1] - Math.cos(a) * len];
  const sh = up(70), ha = lean + head;
  const hc = [sh[0] + Math.sin(ha) * 50, sh[1] - Math.cos(ha) * 50];
  const perp = [Math.cos(lean), Math.sin(lean)];
  const L = legs.map((l, i) => limb([hip[0] + perp[0] * (i ? 14 : -14), hip[1] + 8], l[0], l[1], 38, 36));
  const A = arms.map((a, i) => limb([sh[0] + perp[0] * (i ? 30 : -30), sh[1] + perp[1] * (i ? 30 : -30) + 10], a[0], a[1], 36, 34));
  return { lean, hip, up, sh, ha, hc, perp, L, A, head: hc, hands: [A[0][2], A[1][2]], belly: up(26) };
}

export function smurf(g, pose = {}, id = 100) {
  const { tag = true, prop = null, mouth = 'smile' } = pose;
  const { lean, hip, up, ha, hc, perp, L, A, head, hands, belly } = smurfRig(pose);
  const rot = (c, a) => ([x, y]) => [c[0] + x * Math.cos(a) - y * Math.sin(a), c[1] + x * Math.sin(a) + y * Math.cos(a)];
  const Hd = pts => pts.map(rot(hc, ha)), Bd = pts => pts.map(rot(up(36), lean)), Hp = pts => pts.map(rot(hip, lean));
  const torso = Bd(ellipse(0, 0, 38, 46));
  const pants = Hp([[-40, -22], [40, -22], [42, 4], [24, 16], [-24, 16], [-42, 4]]);
  const tail = rot(hip, lean)([-44, -6]);
  const skull = Hd(ellipse(0, 0, 44, 42)), ear = Hd(ellipse(-41, 8, 10, 13, 12)), nose = Hd(ellipse(40, 13, 16, 13, 16));

  // pass 1: violet outline (everything slightly fatter), pass 2: inks on top
  const O = 7;
  for (const l of L) g.stroke(l, 26 + O, INK.dark, { id: id + 1, mode: 'over' });
  for (const a of A) g.stroke(a, 20 + O, INK.dark, { id: id + 2, mode: 'over' });
  g.fill(torso, INK.dark, { id: id + 3 }); g.stroke(torso, O, INK.dark, { id: id + 3, closed: true, mode: 'over' });
  g.fill(skull, INK.dark, { id: id + 4 }); g.stroke(skull, O, INK.dark, { id: id + 4, closed: true, mode: 'over' });
  g.fill(ellipse(tail[0], tail[1], 14, 14, 12), INK.dark, { id: id + 5 });

  for (const l of L) {
    g.stroke(l, 26, INK.paper, { id: id + 1, mode: 'over' });
    const f = [l[2][0] + 9, l[2][1] - 1];
    g.shape(ellipse(f[0], f[1], 19, 10, 14), INK.paper, INK.dark, 3.5, { id: id + 6 });
  }
  g.fill(ellipse(tail[0], tail[1], 10, 10, 12), INK.paper, { id: id + 5 });
  g.fill(torso, INK.skin, { id: id + 3 });
  g.shape(pants, INK.paper, INK.dark, 3.5, { id: id + 7 });
  g.fill(Hp([[-40, -22], [-18, -22], [-20, 16], [-24, 16], [-42, 4]]), { B: 0.16 }, { id: id + 8, mode: 'ink' });
  // gold chain + pendant
  const chain = Bd(arc(0, -40, 24, 26, 15, 165, 12));
  g.stroke(chain, 8, INK.dark, { id: id + 9 });
  g.stroke(chain, 4.5, INK.yellow, { id: id + 9, mode: 'over' });
  const pend = Bd([[0, -12]])[0];
  g.shape(ellipse(pend[0], pend[1], 8, 8, 12), INK.yellow, INK.dark, 3, { id: id + 10 });
  for (const a of A) g.stroke(a, 20 + O, INK.dark, { id: id + 2, mode: 'over' });
  for (const a of A) {
    g.stroke(a, 20, INK.skin, { id: id + 2, mode: 'over' });
    g.fill(ellipse(a[2][0], a[2][1], 13, 13), INK.skin, { id: id + 11 });
  }
  // head: skull, ear, shades, then the nose in front of them, mouth, cap
  g.fill(skull, INK.skin, { id: id + 4 });
  g.shape(ear, INK.skin, INK.dark, 3, { id: id + 12 });
  // 3/4 shades just under the cap brim: temple arm back to the ear, big near lens, small far lens
  // past the bridge. The nose sits lower and is drawn after, so it never cuts through a lens.
  g.stroke(Hd([[-2, -8], [-34, -2]]), 4, INK.dark, { id: id + 17 });
  g.fill(Hd(roundRect(-2, -16, 32, 18, 7)), INK.dark, { id: id + 15 });
  g.stroke(Hd([[29, -9], [36, -9]]), 4, INK.dark, { id: id + 16 });
  g.fill(Hd(roundRect(34, -14, 10, 13, 4)), INK.dark, { id: id + 16 });
  g.stroke(Hd([[5, -12], [12, -4]]), 3, INK.paper, { id: id + 18, mode: 'over', boil: 0.4 });
  g.shape(nose, INK.skin, INK.dark, 3.5, { id: id + 13 });
  g.stroke(Hd([[37, 8], [45, 7]]), 3, INK.paper, { id: id + 24, mode: 'over', boil: 0.4 });
  if (mouth === 'o') g.fill(Hd(ellipse(18, 32, 6, 6, 12)), INK.dark, { id: id + 14 });
  else g.stroke(Hd(MOUTHS[mouth] || MOUTHS.smile), 3.5, INK.dark, { id: id + 14 });
  g.fill(Hd(CAP), INK.paper, { id: id + 19 });
  g.fill(Hd(CAP_SHADE), { B: 0.18 }, { id: id + 20, mode: 'ink' });
  g.stroke(Hd([[22, -74], [40, -52], [46, -30]]), 3, INK.dark, { id: id + 21 });
  g.stroke(Hd([[-50, -4], [-20, -14], [10, -18], [38, -20]]), 3, INK.dark, { id: id + 22 });
  g.stroke(Hd(CAP), 4.5, INK.dark, { closed: true, id: id + 19 });
  if (tag) {
    const t = Bd([[14, 18]])[0];
    nameTag(g, t[0], t[1], lean, 0.9, id + 23);
  }
  if (prop) prop(g, A[1][2], A[0][2], hc);
  return { head: hc, hands: [A[0][2], A[1][2]], belly: up(26) };
}

// "OLÁ, EU SOU / PARDJHONSON" sticker.
export function nameTag(g, x, y, rot = 0, s = 1, id = 9) {
  g.save(); g.translate(x, y); g.rotate(rot - 0.08); g.scale(s);
  g.fill(roundRect(-32, -15, 64, 32, 5), INK.paper, { mode: 'knock', id, boil: 0.5 });
  g.fill(rect(-32, -15, 64, 10), INK.pink, { id: id + 1, boil: 0.5 });
  drawText(g, 'OLÁ', -measure('OLÁ', 6) / 2, -13.5, 6, { paint: {}, mode: 'knock', weight: 1.3, seed: 5, boil: 0.2, jitter: 0 });
  // fit the name inside the card with a margin, no letter jitter so it can't poke out
  const size = 50 / measure('PARDJHONSON', 1), w = measure('PARDJHONSON', size);
  drawText(g, 'PARDJHONSON', -w / 2, 1.5, size, { paint: INK.dark, weight: 1.25, seed: 6, boil: 0.15, jitter: 0 });
  g.restore();
}

// Simple coworker cut-out: head + shoulders.
export function bust(g, paint, id = 300, s = 1) {
  g.save(); g.scale(s);
  g.fill([[-46, 0], [-40, -50], [-22, -64], [22, -64], [40, -50], [46, 0]], paint, { id });
  g.fill(ellipse(0, -92, 24, 27), paint, { id: id + 1 });
  g.stroke([[-46, 0], [-40, -50], [-22, -64], [22, -64], [40, -50], [46, 0]], 3, INK.dark, { id, closed: false });
  g.stroke(ellipse(0, -92, 24, 27), 3, INK.dark, { id: id + 1, closed: true });
  g.restore();
}

export function sweat(g, x, y, ang = 0, s = 1, id = 50) {
  g.save(); g.translate(x, y); g.rotate(ang); g.scale(s);
  const drop = [[0, -14], ...arc(0, 0, 8, 8, -60, 240, 12)];
  g.fill(drop, { B: 0.25 }, { id });
  g.stroke(drop, 2.4, INK.blue, { id, closed: true });
  g.fill(ellipse(-2.5, 1, 2, 3.5, 8), {}, { mode: 'knock', id: id + 1 });
  g.restore();
}

// ---------------------------------------------------------------- padaria
// Copo americano. Origin at the bottom centre, 130 tall. level 0..1, contents paint.
export function glass(g, level, contents, { foam = 0, id = 20 } = {}) {
  const top = 132, wt = 46, wb = 36;
  const outline = [[-wb, 0], [wb, 0], [wt, -top], [-wt, -top]];
  const wAt = h => lerp(wb, wt, h / top);
  g.fill(outline, { B: 0.1 }, { id });
  if (level > 0) {
    const h = top * 0.94 * level;
    g.fill([[-wb + 2, -2], [wb - 2, -2], [wAt(h) - 2, -h], [-wAt(h) + 2, -h]], contents, { id: id + 1 });
    if (foam > 0) {
      const fh = 12 * foam;
      g.fill([[-wAt(h) + 2, -h], [wAt(h) - 2, -h], [wAt(h + fh) - 2, -h - fh], [-wAt(h + fh) + 2, -h - fh]], {}, { mode: 'knock', id: id + 2 });
      for (let i = 0; i < 5; i++) g.dot(-wAt(h) + 10 + i * 15, -h - fh + 2, 6, {}, { mode: 'knock', id: id + 3 + i });
      g.stroke([[-wAt(h) + 2, -h], [wAt(h) - 2, -h]], 1.5, { B: 0.5 }, { id: id + 2 });
    }
  }
  // the facets of a copo americano
  for (let i = -3; i <= 3; i++) {
    const x0 = i * wb / 3.6, x1 = i * wAt(top * 0.62) / 3.6;
    g.stroke([[x0, -4], [x1, -top * 0.62]], 2, INK.line, { id: id + 10 + i });
  }
  g.stroke([[-wAt(top * 0.62), -top * 0.62], [wAt(top * 0.62), -top * 0.62]], 2, INK.line, { id: id + 18 });
  g.stroke(outline, 3.2, INK.line, { closed: true, id: id + 19 });
  g.stroke([[-wt + 8, -top + 10], [-wb + 6, -12]], 5, {}, { mode: 'knock', id: id + 20, boil: 0.5 });
}

// Wavy steam / smoke wisps above (0, 0). t animates.
export function steam(g, t, { n = 3, h = 90, spread = 22, paint = { P: 1 }, width = 4, id = 60 } = {}) {
  for (let k = 0; k < n; k++) {
    const pts = [];
    for (let i = 0; i <= 12; i++) {
      const y = -i / 12 * h;
      pts.push([(k - (n - 1) / 2) * spread + Math.sin(i * 0.7 + t * 6 + k * 2) * 9 * (i / 12 + 0.3), y]);
    }
    g.stroke(pts, width, paint, { id: id + k, taper: true });
  }
}

// Metal pot (bule) with spout to the right, tilted by `tilt`. Origin = spout tip.
export function pot(g, tilt, { id = 70, milk = false } = {}) {
  g.save(); g.rotate(tilt); g.translate(-112, 24);
  const body = milk
    ? [[0, -64], [70, -64], [74, 40], [-4, 40]]
    : [[6, -60], [64, -60], [80, 40], [-10, 40]];
  const paint = milk ? { B: 0.18 } : { B: 0.45, Y: 0.15 };
  g.fill([[60, -40], [112, -24], [108, -18], [62, -22]], paint, { id: id + 1 });            // spout
  g.stroke([[60, -40], [112, -24], [108, -18], [62, -22]], 3, INK.line, { id: id + 1, closed: true });
  g.shape(body, paint, INK.line, 3.2, { id });
  g.stroke(arc(-6, -10, 26, 30, 100, 260, 10), 9, INK.dark, { id: id + 2 });              // handle
  if (!milk) g.shape([[18, -60], [52, -60], [44, -74], [26, -74]], { B: 0.7 }, INK.line, 3, { id: id + 3 });
  else g.shape(rect(-4, -70, 78, 8), { B: 0.3 }, INK.line, 3, { id: id + 3 });
  g.stroke([[18, -50], [14, 30]], 6, {}, { mode: 'knock', id: id + 4, boil: 0.5 });
  g.restore();
}

// Falling stream from (x0, y0) to (x1, y1). milk = paper stream with blue edges.
export function stream(g, x0, y0, x1, y1, t, milk, id = 80) {
  const pts = [];
  for (let i = 0; i <= 10; i++) {
    const k = i / 10;
    pts.push([lerp(x0, x1, k) + Math.sin(k * 9 + t * 30) * 2.5 * k, lerp(y0, y1, k * k * 0.4 + k * 0.6)]);
  }
  if (milk) {
    g.stroke(pts, 13, INK.line, { id });
    g.stroke(pts, 8, {}, { mode: 'knock', id });
  } else g.stroke(pts, 10, INK.coffee, { id, mode: 'over' });
}

export function counter(g, y, { id = 90 } = {}) {
  // marble top + tiled front, the padaria classic
  g.shape(rect(-40, y, 620, 30), { P: 0.12 }, INK.line, 3, { id });
  for (let i = 0; i < 6; i++) {
    const x = 20 + i * 95;
    g.stroke([[x, y + 6], [x + 30, y + 14], [x + 52, y + 9]], 1.6, { B: 0.7 }, { id: id + i + 1 });
  }
  g.fill(rect(-40, y + 30, 620, 400), { Y: 0.85 }, { id: id + 8 });
  for (let r = 0; r < 8; r++) g.stroke([[-40, y + 30 + r * 44], [580, y + 30 + r * 44]], 2.4, INK.line, { id: id + 10 + r });
  for (let c = 0; c < 15; c++) g.stroke([[-40 + c * 44, y + 30], [-40 + c * 44, y + 430]], 2.4, INK.line, { id: id + 30 + c });
}

export function bread(g, x, y, s = 1, id = 120) {
  g.save(); g.translate(x, y); g.scale(s);
  g.shape(ellipse(0, 0, 30, 15), INK.wood, INK.line, 2.6, { id });
  g.stroke([[-12, -6], [8, -12]], 3, { P: 0.9, Y: 0.6 }, { id: id + 1 });
  g.restore();
}

export function clock(g, x, y, r, t, id = 130) {
  g.save(); g.translate(x, y);
  g.shape(ellipse(0, 0, r, r), {}, INK.dark, 3.5, { id, mode: 'knock' });
  g.fill(ellipse(0, 0, r - 5, r - 5), {}, { mode: 'knock', id });
  for (let i = 0; i < 12; i++) {
    const a = i / 12 * Math.PI * 2;
    g.stroke([[Math.cos(a) * (r - 4), Math.sin(a) * (r - 4)], [Math.cos(a) * (r - 9), Math.sin(a) * (r - 9)]], 2, INK.line, { id: id + 1 + i });
  }
  const hand = (a, l, w, p) => g.stroke([[0, 0], [Math.sin(a) * l, -Math.cos(a) * l]], w, p, { id: id + 20 });
  hand(t * Math.PI / 6, r * 0.5, 4, INK.dark);
  hand(t * Math.PI * 2, r * 0.78, 2.5, INK.pink);
  g.dot(0, 0, 3, INK.dark);
  g.restore();
}

export function sun(g, x, y, r, t, id = 140) {
  g.save(); g.translate(x, y);
  for (let i = 0; i < 12; i++) {
    const a = i / 12 * Math.PI * 2 + t * 0.6;
    g.fill([[Math.cos(a - 0.12) * r * 1.2, Math.sin(a - 0.12) * r * 1.2], [Math.cos(a) * r * 1.75, Math.sin(a) * r * 1.75], [Math.cos(a + 0.12) * r * 1.2, Math.sin(a + 0.12) * r * 1.2]], { Y: 1 }, { id: id + i, mode: 'ink' });
  }
  g.fill(ellipse(0, 0, r, r), { Y: 1, P: 0.3 }, { id });
  g.stroke(ellipse(0, 0, r, r), 3, { P: 1 }, { closed: true, id });
  g.restore();
}

// ---------------------------------------------------------------- street
export function building(g, x, base, w, h, paint, seed, win = { Y: 0.9 }) {
  g.fill(rect(x, base - h, w, h), paint, { id: seed });
  g.stroke(rect(x, base - h, w, h), 2.5, INK.line, { closed: true, id: seed });
  for (let wy = base - h + 14; wy < base - 24; wy += 26)
    for (let wx = x + 10; wx < x + w - 16; wx += 22)
      if (hash(seed, wx, wy) > 0.35) g.fill(rect(wx, wy, 11, 14), hash(seed, wy, wx) > 0.6 ? win : {}, { mode: hash(seed, wy, wx) > 0.6 ? 'over' : 'knock', id: seed + wx });
}

export function bus(g, id = 160) {
  g.shape(roundRect(-160, -120, 320, 110, 18), { Y: 1 }, INK.dark, 4, { id });
  for (let i = 0; i < 5; i++) g.shape(rect(-140 + i * 56, -104, 44, 40), { B: 0.75 }, INK.dark, 3, { id: id + 1 + i });
  g.fill(rect(-160, -50, 320, 10), INK.pink, { id: id + 8 });
  for (const wx of [-100, 100]) {
    g.fill(ellipse(wx, -10, 24, 24), INK.dark, { id: id + 9 });
    g.fill(ellipse(wx, -10, 9, 9), { B: 0.3 }, { id: id + 10 });
  }
}

// Cloud of overlapping puffs (smoke). k scales, t animates.
export function cloud(g, x, y, k, t, seed, paint = { P: 0.35 }, line = { P: 1 }) {
  const puffs = [];
  for (let i = 0; i < 7; i++) {
    const a = i / 7 * Math.PI * 2 + seed;
    puffs.push([x + Math.cos(a) * 26 * k + Math.sin(t * 3 + i) * 3, y + Math.sin(a) * 15 * k, (16 + hash(seed, i) * 12) * k]);
  }
  for (const [px, py, r] of puffs) g.stroke(ellipse(px, py, r, r, 14), 3, line, { closed: true, id: seed * 10 });
  for (const [px, py, r] of puffs) g.fill(ellipse(px, py, r - 1.5, r - 1.5, 14), paint, { id: seed * 10 });
}

// Cigarette held at (0,0), pointing +x.
export function cigarette(g, id = 170) {
  g.fill(rect(0, -3, 26, 6), {}, { mode: 'knock', id });
  g.stroke(rect(0, -3, 26, 6), 1.6, INK.line, { closed: true, id });
  g.fill(rect(0, -3, 7, 6), { Y: 0.9, P: 0.3 }, { id: id + 1 });
  g.fill(rect(24, -3, 4, 6), INK.red, { id: id + 2 });
}

// ---------------------------------------------------------------- office
export function timeClock(g, punched, id = 180) {
  g.shape(roundRect(-90, -150, 180, 260, 14), { B: 0.55 }, INK.dark, 4, { id });
  g.fill(ellipse(0, -80, 56, 56), {}, { mode: 'knock', id: id + 1 });
  g.stroke(ellipse(0, -80, 56, 56), 4, INK.dark, { closed: true, id: id + 1 });
  for (let i = 0; i < 12; i++) {
    const a = i / 12 * Math.PI * 2;
    g.stroke([[Math.cos(a) * 48, -80 + Math.sin(a) * 48], [Math.cos(a) * 42, -80 + Math.sin(a) * 42]], 3, INK.line, { id: id + 2 + i });
  }
  g.stroke([[0, -80], [0, -118]], 4, INK.dark, { id: id + 20 });
  g.stroke([[0, -80], [30, -80 + 18]], 5, INK.dark, { id: id + 21 });
  g.fill(rect(-56, 20, 112, 14), INK.dark, { id: id + 22 });
  return [0, 27];
}
export function punchCard(g, stamped, id = 200) {
  g.fill(rect(-40, -130, 80, 130), {}, { mode: 'knock', id });
  g.stroke(rect(-40, -130, 80, 130), 2.5, INK.line, { closed: true, id });
  for (let r = 0; r < 7; r++) g.stroke([[-34, -112 + r * 15], [34, -112 + r * 15]], 1.2, { B: 0.6 }, { id: id + 1 + r });
  g.fill(rect(-40, -130, 80, 12), INK.pink, { id: id + 9 });
  if (stamped) stamp(g, '08:00', 0, -66, 15, { paint: INK.red, rot: -0.2, seed: 12, border: false, weight: 1.6 });
}

export function whiteboard(g, t, id = 220) {
  g.fill(rect(-150, -100, 300, 180), {}, { mode: 'knock', id });
  g.stroke(rect(-150, -100, 300, 180), 5, INK.dark, { closed: true, id });
  const bars = [0.8, 0.65, 0.5, 0.3, 0.12];
  bars.forEach((b, i) => g.shape(rect(-120 + i * 46, 60 - 130 * b, 32, 130 * b), i % 2 ? { B: 0.6 } : { P: 0.7 }, INK.line, 2.5, { id: id + 1 + i }));
  const arrow = [[-120, -70], [-40, -40], [20, -20], [110, 40]];
  g.stroke(arrow, 6, INK.red, { id: id + 10 });
  g.fill([[110, 40], [86, 34], [104, 18]], INK.red, { id: id + 11 });
}

export function table(g, id = 240) {
  g.shape([[-260, 0], [260, 0], [200, -70], [-200, -70]], INK.wood, INK.dark, 4, { id });
  g.fill(rect(-260, 0, 520, 24), { Y: 0.55, P: 0.35, B: 0.3 }, { id: id + 1 });
  g.stroke(rect(-260, 0, 520, 24), 3, INK.dark, { closed: true, id: id + 1 });
}

// Belly rumble: spiral + bubbles.
export function rumble(g, x, y, k, t, id = 260) {
  if (k <= 0) return;
  const pts = [];
  for (let i = 0; i <= 40; i++) {
    const a = i * 0.45 + t * 8, r = i * 0.9 * k;
    pts.push([x + Math.cos(a) * r, y + Math.sin(a) * r]);
  }
  g.stroke(pts, 3.5, INK.red, { id });
  for (let i = 0; i < 4; i++) {
    const a = i * 1.7 + t * 2;
    g.stroke(ellipse(x + Math.cos(a) * 46 * k, y + Math.sin(a) * 30 * k - 6, 5 * k, 5 * k, 10), 2, INK.red, { closed: true, id: id + i });
  }
}

// ---------------------------------------------------------------- calendar + cartons
export function calendar(g, year, id = 280) {
  g.fill(rect(-120, -150, 240, 280), {}, { mode: 'knock', id });
  g.fill(rect(-120, -150, 240, 56), INK.pink, { id: id + 1 });
  g.stroke(rect(-120, -150, 240, 280), 4, INK.dark, { closed: true, id });
  for (let i = 0; i < 6; i++) g.stroke(arc(-90 + i * 36, -150, 6, 12, 180, 360, 8), 4, INK.dark, { id: id + 2 + i });
  const w = measure(String(year), 64);
  drawText(g, String(year), -w / 2, -60, 64, { paint: INK.dark, weight: 1.5, seed: year, jitter: 0.3 });
  for (let r = 0; r < 3; r++)
    for (let c = 0; c < 7; c++) g.fill(rect(-100 + c * 29, 40 + r * 26, 18, 14), (r * 7 + c + year) % 9 === 0 ? INK.red : { B: 0.35 }, { id: id + 20 + r * 7 + c });
}
export function page(g, rot, id = 330) {
  g.save(); g.rotate(rot);
  g.fill(rect(-120, -150, 240, 280), {}, { mode: 'knock', id });
  g.fill(rect(-120, -150, 240, 56), { P: 0.6 }, { id: id + 1 });
  g.stroke(rect(-120, -150, 240, 280), 3, INK.line, { closed: true, id });
  g.restore();
}

// Gable-top milk carton, origin bottom centre (~230 tall).
export function milkCarton(g, { label = 'LEITE', paint = { B: 1 }, spots = true, id = 340 } = {}) {
  const front = rect(-60, -170, 120, 170), side = [[60, -170], [92, -186], [92, -16], [60, 0]];
  const gable = [[-60, -170], [60, -170], [36, -226], [-36, -226]];
  g.shape(side, { B: 0.25 }, INK.dark, 3.5, { id });
  g.shape(front, {}, INK.dark, 3.5, { id: id + 1, mode: 'knock' });
  g.shape(gable, { B: 0.12 }, INK.dark, 3.5, { id: id + 2 });
  g.shape(rect(-36, -240, 72, 14), { B: 0.4 }, INK.dark, 3, { id: id + 3 });
  if (spots) for (let i = 0; i < 6; i++) {
    const sx = -40 + hash(id, i) * 80, sy = -150 + hash(i, id) * 120;
    g.fill(ellipse(sx, sy, 10 + hash(id, i, 2) * 10, 7 + hash(id, i, 3) * 8, 10), paint, { id: id + 10 + i });
  }
  if (label) {
    const s = Math.min(22, 100 / (measure(label, 1)));
    g.fill(rect(-60, -96, 120, s + 16), paint, { id: id + 4 });
    drawText(g, label, -measure(label, s) / 2, -88, s, { paint: {}, mode: 'knock', weight: 1.5, seed: id });
  }
}

// Plant icons for the vegetal cartons.
export function plantIcon(g, kind, id = 360) {
  if (kind === 0) { // oat
    g.stroke([[0, 30], [0, -30]], 3, INK.dark, { id });
    for (let i = 0; i < 4; i++) for (const s of [-1, 1]) g.fill(ellipse(s * 9, -22 + i * 13, 6, 10, 10).map(([x, y]) => [x, y]), { Y: 1, P: 0.3 }, { id: id + i });
  } else if (kind === 1) { // soy pod
    g.shape(roundRect(-30, -12, 60, 24, 12), { B: 0.6, Y: 1 }, INK.dark, 3, { id });
    for (let i = -1; i <= 1; i++) g.fill(ellipse(i * 17, 0, 7, 7), { B: 1, Y: 1 }, { id: id + 2 + i });
  } else { // almond
    g.shape([[0, -30], ...arc(0, 4, 18, 26, -60, 240, 14)], INK.wood, INK.dark, 3, { id });
    g.stroke([[0, -20], [0, 22]], 2, { P: 1, Y: 1 }, { id: id + 1 });
  }
}
export function plantCarton(g, kind, id = 380) {
  const names = ['AVEIA', 'SOJA', 'AMÊNDOA'], tints = [{ Y: 0.6 }, { Y: 0.45, B: 0.3 }, { P: 0.3, Y: 0.4 }];
  g.shape(rect(-58, -200, 116, 200), tints[kind], INK.dark, 3.5, { id });
  g.shape([[58, -200], [80, -214], [80, -14], [58, 0]], { B: 0.35 }, INK.dark, 3, { id: id + 1 });
  g.shape([[-58, -200], [58, -200], [80, -214], [-36, -214]], { B: 0.2 }, INK.dark, 3, { id: id + 2 });
  g.shape(rect(-14, -232, 28, 20), INK.green, INK.dark, 3, { id: id + 3 });
  g.fill(rect(-58, -64, 116, 34), {}, { mode: 'knock', id: id + 4 });
  const s = Math.min(19, 96 / measure(names[kind], 1));
  drawText(g, names[kind], -measure(names[kind], s) / 2, -56, s, { paint: INK.dark, weight: 1.4, seed: id });
  g.save(); g.translate(0, -130); g.scale(1.4); plantIcon(g, kind, id + 10); g.restore();
}

// Belly x-ray: torso outline, stomach, angry gut.
export function bellyXray(g, t, anger, id = 420) {
  g.shape([[-150, -220], [150, -220], [175, 120], [-175, 120]], { Y: 0.55, P: 0.4, B: 0.18 }, INK.dark, 5, { id });
  const st = [[-60, -150], [40, -170], [96, -120], [70, -50], [-10, -40], [-70, -80]];
  g.shape(st, INK.pink, INK.dark, 4, { id: id + 1 });
  const gut = [];
  for (let i = 0; i <= 60; i++) {
    const k = i / 60;
    gut.push([Math.sin(k * 22 + t * 4 * anger) * 90 * (0.4 + k * 0.6), -30 + k * 130]);
  }
  g.stroke(gut, 12, INK.red, { id: id + 2 });
  g.stroke(gut, 4, INK.dark, { id: id + 3 });
  for (let i = 0; i < Math.round(anger * 5); i++) {
    const a = i * 1.3 + Math.floor(t * 8) * 0.7, cx = Math.cos(a) * 120, cy = 10 + Math.sin(a) * 80;
    bolt(g, cx, cy, a + 1.57, 0.7, id + 10 + i);
  }
}
export function bolt(g, x, y, ang, s, id = 450) {
  g.save(); g.translate(x, y); g.rotate(ang); g.scale(s);
  const p = [[-8, -40], [14, -40], [4, -8], [20, -8], [-12, 44], [-2, 6], [-18, 6]];
  g.shape(p, INK.yellow, INK.dark, 3.5, { id });
  g.restore();
}

// ---------------------------------------------------------------- milkshake
export function sunburst(g, x, y, r, t, n = 18, id = 470) {
  for (let i = 0; i < n; i++) {
    const a0 = (i / n) * Math.PI * 2 + t, a1 = ((i + 0.5) / n) * Math.PI * 2 + t;
    g.fill([[x, y], [x + Math.cos(a0) * r, y + Math.sin(a0) * r], [x + Math.cos(a1) * r, y + Math.sin(a1) * r]], i % 2 ? { Y: 1 } : { Y: 1, P: 0.25 }, { id: id + i, boil: 0.6 });
  }
}
export function sparkle(g, x, y, s, paint = { Y: 1 }, id = 500) {
  const p = [];
  for (let i = 0; i < 8; i++) {
    const a = i / 8 * Math.PI * 2, r = i % 2 ? s * 0.28 : s;
    p.push([x + Math.cos(a) * r, y + Math.sin(a) * r]);
  }
  g.shape(p, paint, INK.dark, 2.5, { id });
}
// Fluted sundae glass, origin at the base, ~330 tall to the cherry.
export function milkshake(g, t, id = 520) {
  g.shape([[-40, 0], [40, 0], [12, -14], [8, -60], [-8, -60], [-12, -14]], { B: 0.15 }, INK.dark, 3.5, { id });
  const bowl = [[-8, -60], [8, -60], [70, -190], [-70, -190]];
  g.fill(bowl, { P: 1, Y: 0.12 }, { id: id + 1 });
  for (let i = -2; i <= 2; i++) g.stroke([[i * 3, -64], [i * 26, -186]], 2.4, INK.dark, { id: id + 2 + i });
  g.stroke(bowl, 3.5, INK.dark, { closed: true, id: id + 1 });
  // whipped cream: stacked puffs
  const puffs = [[-56, -200, 24], [-20, -206, 28], [22, -204, 27], [56, -198, 22], [-34, -236, 24], [8, -244, 28], [42, -230, 20], [-6, -276, 22]];
  for (const [px, py, r] of puffs) g.stroke(ellipse(px, py + Math.sin(t * 5 + px) * 1.5, r, r * 0.86, 14), 3.2, INK.dark, { closed: true, id: id + 8 });
  for (const [px, py, r] of puffs) g.fill(ellipse(px, py + Math.sin(t * 5 + px) * 1.5, r - 1.5, r * 0.86 - 1.5, 14), {}, { mode: 'knock', id: id + 8 });
  // straw
  g.save(); g.translate(30, -240); g.rotate(0.35);
  g.fill(rect(-7, -120, 14, 120), {}, { mode: 'knock', id: id + 9 });
  for (let i = 0; i < 6; i++) g.fill([[-7, -120 + i * 22], [7, -128 + i * 22], [7, -116 + i * 22], [-7, -108 + i * 22]], { B: 1 }, { id: id + 10 + i });
  g.stroke(rect(-7, -120, 14, 120), 2.5, INK.dark, { closed: true, id: id + 9 });
  g.restore();
  // cherry
  g.stroke([[-6, -298], [4, -330], [18, -344]], 3, { B: 1, Y: 1 }, { id: id + 20 });
  g.shape(ellipse(-6, -296, 17, 16), INK.red, INK.dark, 3, { id: id + 21 });
  g.fill(ellipse(-11, -301, 4, 5, 8), {}, { mode: 'knock', id: id + 22 });
}

// ---------------------------------------------------------------- scissors, hand, door
// Scissors centred on the pivot, blades pointing -x. open = angle between blades (rad).
export function scissors(g, open, id = 560) {
  for (const s of [-1, 1]) {
    g.save(); g.rotate(s * open / 2);
    const blade = [[0, -6 * s], [-150, -2 * s], [-150, 2 * s], [0, 10 * s]];
    g.shape(blade, {}, INK.dark, 4.5, { id: id + (s > 0 ? 1 : 2), mode: 'knock' });
    g.stroke([[-140, 0], [-10, 3 * s]], 3, { B: 0.6 }, { id: id + 6 });
    g.stroke([[4, 4 * s], [40, 22 * s]], 9, INK.dark, { id: id + 3 });
    g.stroke(ellipse(64, 30 * s, 26, 18, 16), 10, INK.red, { closed: true, id: id + 4 });
    g.restore();
  }
  g.dot(0, 0, 6, INK.dark, { id: id + 5 });
}

// Smurf Pardo's arm reaching into frame, drawn like the full model: outlined brown limb ending
// in a round mitt. pts = shoulder (usually off-screen) -> [elbow] -> hand, in world units; s = size.
export function arm(g, pts, s = 1, id = 600) {
  g.stroke(pts, 27 * s, INK.dark, { id, mode: 'over' });
  g.stroke(pts, 20 * s, INK.skin, { id, mode: 'over' });
  const [hx, hy] = pts[pts.length - 1];
  g.shape(ellipse(hx, hy, 15 * s, 15 * s, 16), INK.skin, INK.dark, 3.5 * s, { id: id + 1 });
}

export function door(g, shake, occupied, id = 640) {
  g.fill(rect(-170, -560, 340, 560), INK.dark, { id });
  g.save(); g.translate(Math.sin(shake * 40) * 4 * clamp(shake), 0);
  g.shape(rect(-150, -540, 300, 540), { B: 0.62, Y: 0.25 }, INK.dark, 4, { id: id + 1 });
  g.stroke(rect(-112, -500, 224, 200), 4, INK.dark, { closed: true, id: id + 2 });
  g.stroke(rect(-112, -260, 224, 210), 4, INK.dark, { closed: true, id: id + 3 });
  g.fill(ellipse(116, -270, 13, 13), INK.yellow, { id: id + 4 });
  g.stroke(ellipse(116, -270, 13, 13), 3, INK.dark, { closed: true, id: id + 4 });
  // little WC plaque with a toilet icon
  g.shape(roundRect(-46, -470, 92, 74, 8), {}, INK.dark, 3, { id: id + 5, mode: 'knock' });
  g.fill([[-22, -440], [10, -440], [8, -428], [-4, -416], [4, -406], [-18, -406], [-14, -416], [-24, -428]], INK.blue, { id: id + 6 });
  g.fill(rect(10, -458, 14, 26), INK.blue, { id: id + 7 });
  // OCUPADO slider
  g.fill(rect(72, -330, 68, 22), occupied ? INK.red : INK.green, { id: id + 8 });
  g.stroke(rect(72, -330, 68, 22), 2.5, INK.dark, { closed: true, id: id + 8 });
  g.restore();
}

export function toiletRoll(g, unroll, t, id = 680) {
  const len = 30 + unroll * 380;
  const pts = [];
  for (let i = 0; i <= 20; i++) { const k = i / 20; pts.push([-k * len, 26 + Math.sin(k * 8 + t * 10) * 6 * k]); }
  g.stroke(pts, 26, INK.dark, { id: id + 1 });
  g.stroke(pts, 20, {}, { mode: 'knock', id: id + 1 });
  g.shape(ellipse(0, 0, 30, 30), {}, INK.dark, 3.5, { id, mode: 'knock' });
  g.fill(ellipse(0, 0, 10, 10), { B: 0.5 }, { id: id + 2 });
}

// Comic impact burst.
export function burst(g, x, y, r, paint, seed = 700, spikes = 14) {
  const p = [];
  for (let i = 0; i < spikes * 2; i++) {
    const a = i / (spikes * 2) * Math.PI * 2, rr = i % 2 ? r * (0.55 + hash(seed, i) * 0.15) : r * (0.9 + hash(seed, i) * 0.25);
    p.push([x + Math.cos(a) * rr, y + Math.sin(a) * rr]);
  }
  g.shape(p, paint, INK.dark, 4, { id: seed });
}

export function speedLines(g, n, len, t, paint = INK.line, id = 720) {
  for (let i = 0; i < n; i++) {
    const y = -300 + hash(id, i) * 600, x = ((hash(i, id) * 900 - t * 2400) % 900 + 900) % 900 - 450;
    g.stroke([[x, y], [x + len * (0.5 + hash(i, id, 3)), y]], 3 + hash(i, id, 4) * 4, paint, { id: id + i, taper: true });
  }
}

export { tornRect, ellipse, rect, roundRect, arc };
