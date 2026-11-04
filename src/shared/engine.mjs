// Tiny software rasterizer for pixel art. Everything is drawn at ART resolution
// (135x240) and upscaled x8 with nearest-neighbour at encode time -> 1080x1920.
export const W = 135;
export const H = 240;
export const SCALE = 8;

// Colors are packed as little-endian RGBA in a Uint32 (0 = transparent).
export function hex(s) {
  const n = parseInt(s.replace('#', ''), 16);
  return (0xff000000 | ((n & 0xff) << 16) | (n & 0xff00) | (n >>> 16)) >>> 0;
}
const R = c => c & 0xff, G = c => (c >>> 8) & 0xff, B = c => (c >>> 16) & 0xff;
const pack = (r, g, b) => (0xff000000 | (b << 16) | (g << 8) | r) >>> 0;

export function lerpColor(a, b, t) {
  t = t < 0 ? 0 : t > 1 ? 1 : t;
  return pack(
    Math.round(R(a) + (R(b) - R(a)) * t),
    Math.round(G(a) + (G(b) - G(a)) * t),
    Math.round(B(a) + (B(b) - B(a)) * t));
}

// 4x4 ordered dither: dither(x, y, 0.3) is true for ~30% of pixels in a stable pattern.
const BAYER = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5].map(v => (v + 0.5) / 16);
export const dither = (x, y, level) => level > BAYER[((y & 3) << 2) | (x & 3)];

export class Surface {
  constructor(w, h) {
    this.w = w;
    this.h = h;
    this.px = new Uint32Array(w * h);
  }

  clear(c = 0) { this.px.fill(c); return this; }

  get(x, y) {
    x = Math.floor(x); y = Math.floor(y);
    if (x < 0 || y < 0 || x >= this.w || y >= this.h) return 0;
    return this.px[y * this.w + x];
  }

  set(x, y, c) {
    x = Math.floor(x); y = Math.floor(y);
    if (!c || x < 0 || y < 0 || x >= this.w || y >= this.h) return;
    this.px[y * this.w + x] = c;
  }

  // Alpha blend; a >= 1 is a plain set.
  blend(x, y, c, a = 1) {
    if (a >= 1) return this.set(x, y, c);
    x = Math.floor(x); y = Math.floor(y);
    if (a <= 0 || x < 0 || y < 0 || x >= this.w || y >= this.h) return;
    const i = y * this.w + x, d = this.px[i];
    if (d) this.px[i] = lerpColor(d, c, a);
    else if (a >= 0.5) this.px[i] = c;
  }

  // Additive light, used for neon glow and beams.
  add(x, y, c, a = 1) {
    x = Math.floor(x); y = Math.floor(y);
    if (a <= 0 || x < 0 || y < 0 || x >= this.w || y >= this.h) return;
    const i = y * this.w + x, d = this.px[i];
    if (!d) return;
    this.px[i] = pack(
      Math.min(255, R(d) + R(c) * a | 0),
      Math.min(255, G(d) + G(c) * a | 0),
      Math.min(255, B(d) + B(c) * a | 0));
  }

  rect(x, y, w, h, c, a = 1) {
    const x0 = Math.max(0, Math.floor(x)), y0 = Math.max(0, Math.floor(y));
    const x1 = Math.min(this.w, Math.floor(x + w)), y1 = Math.min(this.h, Math.floor(y + h));
    for (let yy = y0; yy < y1; yy++)
      for (let xx = x0; xx < x1; xx++) this.blend(xx, yy, c, a);
  }

  ditherRect(x, y, w, h, c, level) {
    for (let yy = Math.floor(y); yy < y + h; yy++)
      for (let xx = Math.floor(x); xx < x + w; xx++)
        if (dither(xx, yy, level)) this.set(xx, yy, c);
  }

  ellipse(cx, cy, rx, ry, c, a = 1) {
    if (rx <= 0 || ry <= 0) return;
    for (let y = Math.floor(cy - ry); y <= Math.ceil(cy + ry); y++)
      for (let x = Math.floor(cx - rx); x <= Math.ceil(cx + rx); x++) {
        const dx = (x + 0.5 - cx) / rx, dy = (y + 0.5 - cy) / ry;
        if (dx * dx + dy * dy <= 1) this.blend(x, y, c, a);
      }
  }

  ring(cx, cy, r, thick, c, a = 1) {
    for (let y = Math.floor(cy - r - 1); y <= Math.ceil(cy + r + 1); y++)
      for (let x = Math.floor(cx - r - 1); x <= Math.ceil(cx + r + 1); x++) {
        const d = Math.hypot(x + 0.5 - cx, y + 0.5 - cy);
        if (d <= r && d > r - thick) this.blend(x, y, c, a);
      }
  }

  // Soft radial light, additive.
  glow(cx, cy, r, c, k = 1) {
    for (let y = Math.floor(cy - r); y <= Math.ceil(cy + r); y++)
      for (let x = Math.floor(cx - r); x <= Math.ceil(cx + r); x++) {
        const d = Math.hypot(x + 0.5 - cx, y + 0.5 - cy) / r;
        if (d < 1) this.add(x, y, c, k * (1 - d) * (1 - d));
      }
  }

  poly(pts, c, a = 1, additive = false) {
    let minY = Infinity, maxY = -Infinity;
    for (const [, y] of pts) { minY = Math.min(minY, y); maxY = Math.max(maxY, y); }
    for (let y = Math.floor(minY); y <= Math.ceil(maxY); y++) {
      const yc = y + 0.5, xs = [];
      for (let i = 0; i < pts.length; i++) {
        const [x0, y0] = pts[i], [x1, y1] = pts[(i + 1) % pts.length];
        if ((y0 <= yc && y1 > yc) || (y1 <= yc && y0 > yc)) xs.push(x0 + (yc - y0) / (y1 - y0) * (x1 - x0));
      }
      xs.sort((p, q) => p - q);
      for (let i = 0; i + 1 < xs.length; i += 2)
        for (let x = Math.ceil(xs[i] - 0.5); x <= Math.floor(xs[i + 1] - 0.5); x++)
          additive ? this.add(x, y, c, a) : this.blend(x, y, c, a);
    }
  }

  line(x0, y0, x1, y1, c, a = 1) {
    x0 = Math.round(x0); y0 = Math.round(y0); x1 = Math.round(x1); y1 = Math.round(y1);
    const dx = Math.abs(x1 - x0), dy = -Math.abs(y1 - y0);
    const sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1;
    let err = dx + dy;
    for (;;) {
      this.blend(x0, y0, c, a);
      if (x0 === x1 && y0 === y1) break;
      const e2 = 2 * err;
      if (e2 >= dy) { err += dy; x0 += sx; }
      if (e2 <= dx) { err += dx; y0 += sy; }
    }
  }

  // Round-capped thick line (limbs).
  thick(x0, y0, x1, y1, r, c) {
    const n = Math.max(1, Math.ceil(Math.hypot(x1 - x0, y1 - y0) * 2));
    for (let i = 0; i <= n; i++) this.ellipse(x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n, r, r, c);
  }

  // 1px outline around everything opaque (8-neighbour when diag = true).
  outline(c, diag = false) {
    const src = this.px.slice(), w = this.w, h = this.h;
    const on = (x, y) => x >= 0 && y >= 0 && x < w && y < h && src[y * w + x] !== 0;
    for (let y = 0; y < h; y++)
      for (let x = 0; x < w; x++) {
        if (src[y * w + x]) continue;
        if (on(x - 1, y) || on(x + 1, y) || on(x, y - 1) || on(x, y + 1) ||
            (diag && (on(x - 1, y - 1) || on(x + 1, y - 1) || on(x - 1, y + 1) || on(x + 1, y + 1))))
          this.px[y * w + x] = c;
      }
    return this;
  }

  // Blit another surface. map(c) can recolor (e.g. silhouettes, flashes).
  // maxY/minY clip by frame row (bodies sitting in water, block-by-block reveals).
  draw(src, dx, dy, { flip = false, scale = 1, alpha = 1, map = null, maxY = Infinity, minY = -Infinity } = {}) {
    dx = Math.round(dx); dy = Math.round(dy);
    for (let sy = 0; sy < src.h; sy++)
      for (let sx = 0; sx < src.w; sx++) {
        let c = src.px[sy * src.w + sx];
        const ty = dy + sy * scale;
        if (!c || ty >= maxY || ty < minY) continue;
        if (map) c = map(c);
        const tx = flip ? src.w - 1 - sx : sx;
        for (let oy = 0; oy < scale; oy++)
          for (let ox = 0; ox < scale; ox++)
            this.blend(dx + tx * scale + ox, dy + sy * scale + oy, c, alpha);
      }
  }

  // Nearest-neighbour zoom of this surface around (cx, cy) into dst.
  zoomInto(dst, cx, cy, z) {
    for (let y = 0; y < dst.h; y++)
      for (let x = 0; x < dst.w; x++) {
        const sx = Math.floor(cx + (x + 0.5 - dst.w / 2) / z);
        const sy = Math.floor(cy + (y + 0.5 - dst.h / 2) / z);
        dst.px[y * dst.w + x] = this.get(Math.min(this.w - 1, Math.max(0, sx)), Math.min(this.h - 1, Math.max(0, sy)));
      }
  }

  copy() {
    const s = new Surface(this.w, this.h);
    s.px.set(this.px);
    return s;
  }
}

// Small math helpers shared by the scenes.
export const clamp = (v, a = 0, b = 1) => (v < a ? a : v > b ? b : v);
export const lerp = (a, b, t) => a + (b - a) * t;
export const easeOut = t => 1 - (1 - clamp(t)) ** 3;
export const easeIn = t => clamp(t) ** 3;
export const easeInOut = t => (t = clamp(t), t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2);
// Deterministic hash noise so every render is identical.
export const hash = (n) => {
  let x = Math.sin(n * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
};
