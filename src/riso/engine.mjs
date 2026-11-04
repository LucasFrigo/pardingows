// Risograph print engine. Everything is drawn as vector paths into three spot-ink TONE layers
// (0..1 per pixel) at 540x960. At composite time each ink plate is halftoned, shifted
// (misregistration), textured and multiplied onto paper -> RGBA, upscaled x2 at encode time.
export const W = 540;
export const H = 960;
export const SCALE = 2;

// Spot inks (riso Fluorescent Pink, Medium Blue, Yellow). Overprints multiply:
// P+B = deep violet (our "black"), P+Y = orange-red, B+Y = green.
export const INKS = {
  P: [255, 72, 176],
  B: [0, 120, 191],
  Y: [255, 232, 0],
};
const KEYS = ['P', 'B', 'Y'];
const PAPER = [243, 236, 221];

// ---------------------------------------------------------------- math + noise
export const clamp = (v, a = 0, b = 1) => (v < a ? a : v > b ? b : v);
export const lerp = (a, b, t) => a + (b - a) * t;
export const easeOut = t => 1 - (1 - clamp(t)) ** 3;
export const easeIn = t => clamp(t) ** 3;
export const easeInOut = t => (t = clamp(t), t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2);
export const backOut = (t, k = 2.2) => (t = clamp(t) - 1, 1 + (k + 1) * t ** 3 + k * t * t);
export const between = (v, a, b) => clamp((v - a) / (b - a));

// Integer hash -> [0, 1). Deterministic so every render is identical.
export function hash(i, j = 0, k = 0) {
  let h = (Math.imul(i | 0, 374761393) + Math.imul(j | 0, 668265263) + Math.imul(k | 0, 2147483647)) | 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  h ^= h >>> 16;
  return (h >>> 0) / 4294967296;
}
// Float-friendly hash for seeds like 12.5.
export const rnd = (a, b = 0, c = 0) => hash(Math.floor(a * 977), Math.floor(b * 613), Math.floor(c * 331));

export function vnoise(x, y) {
  const xi = Math.floor(x), yi = Math.floor(y), xf = x - xi, yf = y - yi;
  const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf);
  const a = hash(xi, yi), b = hash(xi + 1, yi), c = hash(xi, yi + 1), d = hash(xi + 1, yi + 1);
  return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
}

// ---------------------------------------------------------------- path helpers (local units)
export function arc(cx, cy, rx, ry, a0, a1, n = 0) {
  n = n || Math.max(6, Math.ceil(Math.abs(a1 - a0) / 12));
  const pts = [];
  for (let i = 0; i <= n; i++) {
    const a = (a0 + (a1 - a0) * i / n) * Math.PI / 180;
    pts.push([cx + Math.cos(a) * rx, cy + Math.sin(a) * ry]);
  }
  return pts;
}
export const ellipse = (cx, cy, rx, ry, n = 0) => arc(cx, cy, rx, ry, 0, 360, n || Math.max(16, Math.ceil((rx + ry) * 0.5))).slice(0, -1);
export const rect = (x, y, w, h) => [[x, y], [x + w, y], [x + w, y + h], [x, y + h]];
export function roundRect(x, y, w, h, r) {
  r = Math.min(r, w / 2, h / 2);
  return [...arc(x + w - r, y + r, r, r, -90, 0, 5), ...arc(x + w - r, y + h - r, r, r, 0, 90, 5),
    ...arc(x + r, y + h - r, r, r, 90, 180, 5), ...arc(x + r, y + r, r, r, 180, 270, 5)];
}
// Jagged "torn paper" outline around a rectangle. seed picks the tear pattern.
export function tornRect(x, y, w, h, seed, jag = 2.5, step = 7) {
  const pts = [];
  const side = (x0, y0, x1, y1, s) => {
    const n = Math.max(2, Math.round(Math.hypot(x1 - x0, y1 - y0) / step));
    for (let i = 0; i < n; i++) {
      const t = i / n, nx = -(y1 - y0), ny = x1 - x0, l = Math.hypot(nx, ny) || 1;
      const o = (hash(seed, s, i) - 0.5) * 2 * jag;
      pts.push([x0 + (x1 - x0) * t + nx / l * o, y0 + (y1 - y0) * t + ny / l * o]);
    }
  };
  side(x, y, x + w, y, 1); side(x + w, y, x + w, y + h, 2); side(x + w, y + h, x, y + h, 3); side(x, y + h, x, y, 4);
  return pts;
}

// ---------------------------------------------------------------- the print
export class Print {
  constructor() {
    this.L = { P: new Float32Array(W * H), B: new Float32Array(W * H), Y: new Float32Array(W * H) };
    this.cov = new Float32Array(W * H);
    this.m = [1, 0, 0, 1, 0, 0];   // current transform (a b c d e f), canvas-style
    this.stack = [];
    this.boilSeed = 0;           // re-rolled every 2-3 frames ("on twos")
    this.boilAmp = 1;            // px of wobble
    this.alpha = 1;              // global fade (becomes halftone)
  }

  clear() { for (const k of KEYS) this.L[k].fill(0); this.m = [1, 0, 0, 1, 0, 0]; this.stack = []; this.alpha = 1; }

  // ---- transform stack
  save() { this.stack.push([...this.m, this.alpha]); }
  restore() { const s = this.stack.pop(); this.m = s.slice(0, 6); this.alpha = s[6]; }
  transform(a, b, c, d, e, f) {
    const [A, B, C, D, E, F] = this.m;
    this.m = [A * a + C * b, B * a + D * b, A * c + C * d, B * c + D * d, A * e + C * f + E, B * e + D * f + F];
  }
  translate(x, y) { this.transform(1, 0, 0, 1, x, y); }
  scale(sx, sy = sx) { this.transform(sx, 0, 0, sy, 0, 0); }
  rotate(a) { const c = Math.cos(a), s = Math.sin(a); this.transform(c, s, -s, c, 0, 0); }
  get zoom() { return Math.sqrt(Math.abs(this.m[0] * this.m[3] - this.m[1] * this.m[2])); }
  apply([x, y]) { const [a, b, c, d, e, f] = this.m; return [a * x + c * y + e, b * x + d * y + f]; }

  // Transform, resample to <= 7px steps and wobble ("boil"). id decorrelates shapes.
  prep(pts, closed, boil, id) {
    const sp = pts.map(p => this.apply(p));
    const out = [];
    const n = closed ? sp.length : sp.length - 1;
    for (let i = 0; i < n; i++) {
      const a = sp[i], b = sp[(i + 1) % sp.length];
      const steps = Math.max(1, Math.ceil(Math.hypot(b[0] - a[0], b[1] - a[1]) / 7));
      for (let s = 0; s < steps; s++) out.push([a[0] + (b[0] - a[0]) * s / steps, a[1] + (b[1] - a[1]) * s / steps]);
    }
    if (!closed) out.push(sp[sp.length - 1]);
    const amp = this.boilAmp * boil;
    if (amp > 0) {
      const sd = this.boilSeed * 7.31 + id * 3.17, L = 1 / 22;
      for (const p of out) {
        const nx = vnoise(p[0] * L + sd, p[1] * L + 11.3), ny = vnoise(p[0] * L + 41.7, p[1] * L + sd);
        p[0] += (nx - 0.5) * 2 * amp; p[1] += (ny - 0.5) * 2 * amp;
      }
    }
    return out;
  }

  // ---- coverage rasterizers (write into this.cov, return bbox)
  covPoly(rings) {
    let x0 = W, y0 = H, x1 = 0, y1 = 0;
    const edges = [];
    for (const r of rings)
      for (let i = 0; i < r.length; i++) {
        const a = r[i], b = r[(i + 1) % r.length];
        if (a[1] === b[1]) continue;
        edges.push(a[0], a[1], b[0], b[1]);
        x0 = Math.min(x0, a[0]); x1 = Math.max(x1, a[0]); y0 = Math.min(y0, a[1]); y1 = Math.max(y1, a[1]);
      }
    x0 = Math.max(0, Math.floor(x0)); y0 = Math.max(0, Math.floor(y0));
    x1 = Math.min(W - 1, Math.ceil(x1)); y1 = Math.min(H - 1, Math.ceil(y1));
    if (x1 < x0 || y1 < y0) return null;
    const cov = this.cov, xs = [];
    for (let y = y0; y <= y1; y++) {
      const row = y * W;
      for (let s = 0; s < 4; s++) {
        const yc = y + (s + 0.5) / 4;
        xs.length = 0;
        for (let e = 0; e < edges.length; e += 4) {
          const ay = edges[e + 1], by = edges[e + 3];
          if ((ay <= yc && by > yc) || (by <= yc && ay > yc)) {
            const ax = edges[e];
            xs.push(ax + (yc - ay) * (edges[e + 2] - ax) / (by - ay));
          }
        }
        xs.sort((p, q) => p - q);
        for (let i = 0; i + 1 < xs.length; i += 2) {
          const xa = Math.max(x0, xs[i]), xb = Math.min(x1 + 1, xs[i + 1]);
          if (xb <= xa) continue;
          const ia = Math.floor(xa), ib = Math.floor(xb);
          if (ia === ib) { cov[row + ia] += 0.25 * (xb - xa); continue; }
          cov[row + ia] += 0.25 * (ia + 1 - xa);
          for (let k = ia + 1; k < ib; k++) cov[row + k] += 0.25;
          if (ib <= x1) cov[row + ib] += 0.25 * (xb - ib);
        }
      }
    }
    return [x0, y0, x1, y1];
  }

  covStroke(pts, w, taper) {
    let bx0 = W, by0 = H, bx1 = -1, by1 = -1;
    const cov = this.cov, n = pts.length;
    const rad = i => {
      let r = w / 2 * (1 + (vnoise(i * 0.35 + this.boilSeed * 1.7, 5.5) - 0.5) * 0.35);
      if (taper) r *= 0.45 + 0.55 * Math.sin(Math.PI * clamp((i + 0.5) / n)) ;
      return Math.max(0.35, r);
    };
    let ra = rad(0);
    for (let i = 0; i < Math.max(1, n - 1); i++) {
      const a = pts[i], b = pts[Math.min(i + 1, n - 1)], rb = rad(i + 1);
      const rm = Math.max(ra, rb) + 1;
      const x0 = Math.max(0, Math.floor(Math.min(a[0], b[0]) - rm)), x1 = Math.min(W - 1, Math.ceil(Math.max(a[0], b[0]) + rm));
      const y0 = Math.max(0, Math.floor(Math.min(a[1], b[1]) - rm)), y1 = Math.min(H - 1, Math.ceil(Math.max(a[1], b[1]) + rm));
      const dx = b[0] - a[0], dy = b[1] - a[1], ll = dx * dx + dy * dy;
      for (let y = y0; y <= y1; y++)
        for (let x = x0; x <= x1; x++) {
          const px = x + 0.5 - a[0], py = y + 0.5 - a[1];
          const t = ll ? clamp((px * dx + py * dy) / ll) : 0;
          const d = Math.hypot(px - dx * t, py - dy * t);
          const c = ra + (rb - ra) * t - d + 0.5;
          if (c > 0) { const i = y * W + x; if (c > cov[i]) cov[i] = c > 1 ? 1 : c; }
        }
      if (x0 < bx0) bx0 = x0; if (y0 < by0) by0 = y0; if (x1 > bx1) bx1 = x1; if (y1 > by1) by1 = y1;
      ra = rb;
    }
    return bx1 < 0 ? null : [bx0, by0, bx1, by1];
  }

  // Apply this.cov (inside bbox) to the ink layers, then clear it.
  // mode: 'over' = opaque paint (inks not named go to 0), 'ink' = overprint (max),
  //       'knock' = cut to bare paper, 'sub' = remove only the named inks.
  commit(bb, paint, mode) {
    if (!bb) return;
    const [x0, y0, x1, y1] = bb, cov = this.cov, A = this.alpha;
    const tP = paint.P || 0, tB = paint.B || 0, tY = paint.Y || 0;
    const { P, B, Y } = this.L;
    for (let y = y0; y <= y1; y++)
      for (let i = y * W + x0, e = y * W + x1; i <= e; i++) {
        let c = cov[i];
        if (c <= 0) continue;
        cov[i] = 0;
        c = (c > 1 ? 1 : c) * A;
        if (mode === 'over') {
          P[i] += (tP - P[i]) * c; B[i] += (tB - B[i]) * c; Y[i] += (tY - Y[i]) * c;
        } else if (mode === 'ink') {
          if (tP * c > P[i]) P[i] = tP * c;
          if (tB * c > B[i]) B[i] = tB * c;
          if (tY * c > Y[i]) Y[i] = tY * c;
        } else if (mode === 'knock') {
          P[i] *= 1 - c; B[i] *= 1 - c; Y[i] *= 1 - c;
        } else if (mode === 'sub') {
          P[i] *= 1 - c * tP; B[i] *= 1 - c * tB; Y[i] *= 1 - c * tY;
        }
      }
  }

  // ---- public drawing API (points in local coordinates)
  fill(pts, paint, { mode = 'over', boil = 1, id = 0 } = {}) {
    const rings = Array.isArray(pts[0][0]) ? pts : [pts];
    this.commit(this.covPoly(rings.map(r => this.prep(r, true, boil, id + 1))), paint, mode);
  }
  // width is in local units (scaled by the transform).
  stroke(pts, width, paint, { mode = 'ink', boil = 1, id = 0, closed = false, taper = false } = {}) {
    const sp = this.prep(pts, closed, boil, id + 7);
    if (closed) sp.push(sp[0]);
    this.commit(this.covStroke(sp, width * this.zoom, taper), paint, mode);
  }
  // Filled shape with an outline in another ink. The classic riso cut-out look.
  shape(pts, fillPaint, line = { B: 1 }, width = 2.2, { id = 0, boil = 1, mode = 'over' } = {}) {
    if (fillPaint) this.fill(pts, fillPaint, { mode, boil, id });
    if (line) this.stroke(pts, width, line, { closed: true, boil, id });
  }
  dot(x, y, r, paint, opts = {}) { this.fill(ellipse(x, y, r, r, 10), paint, opts); }

  // ---- whole-layer effects
  snapshot() { return { P: this.L.P.slice(), B: this.L.B.slice(), Y: this.L.Y.slice() }; }
  // Keep the snapshot wherever keep(x, y) is true (used for torn-paper wipes).
  mergeSnapshot(s, keep) {
    for (let y = 0; y < H; y++)
      for (let x = 0; x < W; x++) {
        if (!keep(x, y)) continue;
        const i = y * W + x;
        this.L.P[i] = s.P[i]; this.L.B[i] = s.B[i]; this.L.Y[i] = s.Y[i];
      }
  }
  // Print jam: ink drags downward in streaks, rows buckle sideways.
  smear(amount, seed) {
    if (amount <= 0) return;
    const decay = 1 - 0.35 / (1 + amount * 6);
    for (const k of KEYS) {
      const L = this.L[k], src = L.slice();
      for (let y = 0; y < H; y++) {
        const sh = Math.round((vnoise(y / 37, seed) - 0.5) * 40 * amount);
        for (let x = 0; x < W; x++) {
          const sx = x - sh;
          L[y * W + x] = sx >= 0 && sx < W ? src[y * W + sx] : 0;
        }
      }
      for (let x = 0; x < W; x++) {
        const d = decay * (0.92 + 0.08 * hash(x, seed));
        for (let y = 1; y < H; y++) {
          const i = y * W + x, p = L[i - W] * d;
          if (p > L[i]) L[i] = p;
        }
      }
    }
  }
}

// ---------------------------------------------------------------- composite
// Halftone screens (per-ink angle), paper + ink textures, all precomputed once.
const CELL = 6;
const ANGLE = { P: 15, B: 75, Y: 0 };
const SCREEN = {};
for (const k of KEYS) {
  const a = ANGLE[k] * Math.PI / 180, c = Math.cos(a), s = Math.sin(a);
  const D = new Float32Array(W * H);
  for (let y = 0; y < H; y++)
    for (let x = 0; x < W; x++) {
      const u = ((x + 0.5) * c + (y + 0.5) * s) / CELL, v = (-(x + 0.5) * s + (y + 0.5) * c) / CELL;
      const fu = u - Math.round(u), fv = v - Math.round(v);
      D[y * W + x] = Math.sqrt(fu * fu + fv * fv) / 0.70711;
    }
  SCREEN[k] = D;
}
const SHARP = CELL * 0.70711;
// tone -> dot radius (area-correct until the dots touch, then closing the holes)
const RLUT = new Float32Array(1025);
for (let i = 0; i <= 1024; i++) {
  const t = i / 1024;
  RLUT[i] = t <= 0.785 ? Math.sqrt(2 * t / Math.PI) : 0.70711 + (t - 0.785) / 0.215 * 0.29289;
}

const VARIANTS = 4;
function makePaper(seed) {
  const px = new Uint8Array(W * H * 3);
  for (let y = 0; y < H; y++)
    for (let x = 0; x < W; x++) {
      const i = y * W + x;
      const g = (hash(x, y, seed) - 0.5) * 9 + (vnoise(x / 90 + seed, y / 90) - 0.5) * 8 + (vnoise(x / 3.5, y / 14 + seed * 3) - 0.5) * 4;
      px[i * 3] = clamp(PAPER[0] + g, 0, 255); px[i * 3 + 1] = clamp(PAPER[1] + g, 0, 255); px[i * 3 + 2] = clamp(PAPER[2] + g * 1.1, 0, 255);
    }
  // dust specks and fibres
  for (let n = 0; n < 260; n++) {
    let x = hash(n, seed, 1) * W, y = hash(n, seed, 2) * H;
    const fibre = n % 3 === 0, len = fibre ? 4 + hash(n, seed, 3) * 10 : 1;
    const ang = hash(n, seed, 4) * 6.28, dark = fibre ? -22 : -70 * hash(n, seed, 5) - 20;
    for (let s = 0; s < len; s++) {
      const xi = Math.floor(x), yi = Math.floor(y);
      if (xi >= 0 && yi >= 0 && xi < W && yi < H) for (let c = 0; c < 3; c++) px[(yi * W + xi) * 3 + c] = clamp(px[(yi * W + xi) * 3 + c] + dark, 0, 255);
      x += Math.cos(ang + s * 0.3); y += Math.sin(ang + s * 0.3);
    }
  }
  return px;
}
function makeInkTex(seed) {
  const t = new Float32Array(W * H);
  for (let y = 0; y < H; y++) {
    const roller = 0.96 + 0.04 * vnoise(seed * 5.1, y / 23);
    for (let x = 0; x < W; x++) {
      let d = roller * (0.86 + 0.14 * vnoise(x / 70 + seed * 9, y / 55)) * (0.94 + 0.06 * hash(x, y, seed + 50));
      if (hash(x, y, seed + 99) < 0.006) d *= 0.25; // ink dropouts
      t[y * W + x] = d;
    }
  }
  return t;
}
const PAPERS = Array.from({ length: VARIANTS }, (_, i) => makePaper(i + 1));
const INKTEX = Array.from({ length: VARIANTS * 3 }, (_, i) => makeInkTex(i + 11));
const FACT = KEYS.map(k => INKS[k].map(c => 1 - c / 255));

// reg = { P: [dx, dy, skew], ... } plate offsets in px; variant picks paper/ink texture set.
export function composite(print, reg, variant, out) {
  out = out || Buffer.alloc(W * H * 4);
  const paper = PAPERS[variant % VARIANTS];
  const plates = KEYS.map((k, ki) => ({
    L: print.L[k], D: SCREEN[k], T: INKTEX[(variant % VARIANTS) * 3 + ki], f: FACT[ki],
    dx: Math.round(reg[k][0]), dy: Math.round(reg[k][1]), sk: reg[k][2] || 0,
  }));
  for (let y = 0; y < H; y++) {
    const rowShift = plates.map(p => p.dx + Math.round(p.sk * (y - H / 2)));
    for (let x = 0; x < W; x++) {
      const i = y * W + x;
      let r = paper[i * 3], g = paper[i * 3 + 1], b = paper[i * 3 + 2];
      for (let k = 0; k < 3; k++) {
        const p = plates[k], sx = x - rowShift[k], sy = y - p.dy;
        if (sx < 0 || sy < 0 || sx >= W || sy >= H) continue;
        const j = sy * W + sx, t = p.L[j];
        if (t <= 0.004) continue;
        let c;
        if (t >= 0.996) c = 1;
        else {
          c = (RLUT[(t * 1024) | 0] - p.D[j]) * SHARP + 0.5;
          if (c <= 0) continue;
          if (c > 1) c = 1;
        }
        c *= p.T[j];
        r *= 1 - c * p.f[0]; g *= 1 - c * p.f[1]; b *= 1 - c * p.f[2];
      }
      const o = i * 4;
      out[o] = r; out[o + 1] = g; out[o + 2] = b; out[o + 3] = 255;
    }
  }
  return out;
}
