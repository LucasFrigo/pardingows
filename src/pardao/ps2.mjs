// The PS2 pass: turns one 540x960 EEVEE frame into a 1080x1920 frame that looks like a 2000s console game on a CRT.
//   1. 16-bit framebuffer: ordered (Bayer 4x4) dither down to 5 bits a channel, at native resolution
//   2. Bloom: bright parts blurred at quarter resolution and added back (the soft glow every PS2 night level had)
//   3. Interlace: on fast motion, odd lines keep the previous frame (combing), as 480i did
//   4. Bilinear x2 upscale, composite-cable colour bleed (red and blue a pixel apart), faint scanlines, slight vignette
//   node src/pardao/ps2.mjs in.png [more.png ...] --out dir     processes stills for review
import fs from 'fs';
import path from 'path';
import { createCanvas, loadImage } from '@napi-rs/canvas';

export const SRC_W = 540, SRC_H = 960, OUT_W = 1080, OUT_H = 1920;
const BAYER = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5].map(v => (v + 0.5) / 16 - 0.5);

function boxBlur(src, w, h, r, tmp) {
  // Separable box blur on a 3-channel float buffer, in place via tmp
  const n = 2 * r + 1;
  for (let y = 0; y < h; y++) {
    for (let c = 0; c < 3; c++) {
      let acc = 0;
      for (let x = -r; x <= r; x++) acc += src[(y * w + Math.min(w - 1, Math.max(0, x))) * 3 + c];
      for (let x = 0; x < w; x++) {
        tmp[(y * w + x) * 3 + c] = acc / n;
        acc += src[(y * w + Math.min(w - 1, x + r + 1)) * 3 + c] - src[(y * w + Math.max(0, x - r)) * 3 + c];
      }
    }
  }
  for (let x = 0; x < w; x++) {
    for (let c = 0; c < 3; c++) {
      let acc = 0;
      for (let y = -r; y <= r; y++) acc += tmp[(Math.min(h - 1, Math.max(0, y)) * w + x) * 3 + c];
      for (let y = 0; y < h; y++) {
        src[(y * w + x) * 3 + c] = acc / n;
        acc += tmp[(Math.min(h - 1, y + r + 1) * w + x) * 3 + c] - tmp[(Math.max(0, y - r) * w + x) * 3 + c];
      }
    }
  }
}

const QW = SRC_W / 4, QH = SRC_H / 4;
const qa = new Float32Array(QW * QH * 3), qb = new Float32Array(QW * QH * 3), qt = new Float32Array(QW * QH * 3);
const native = new Float32Array(SRC_W * SRC_H * 3);
const out = new Uint8ClampedArray(OUT_W * OUT_H * 4);

/**
 * src: RGBA bytes 540x960. prev: the previous frame's RGBA (or null). opts: { bloom, interlace }.
 * Returns RGBA bytes 1080x1920 (a shared buffer: copy it if it must outlive the next call).
 */
export function ps2Frame(src, prev = null, opts = {}) {
  const bloom = opts.bloom ?? 0.55, threshold = opts.threshold ?? 0.7;
  // Bloom source: bright pass at quarter resolution
  qa.fill(0);
  for (let y = 0; y < SRC_H; y++) {
    for (let x = 0; x < SRC_W; x++) {
      const i = (y * SRC_W + x) * 4;
      const r = src[i] / 255, g = src[i + 1] / 255, b = src[i + 2] / 255;
      const l = 0.3 * r + 0.59 * g + 0.11 * b;
      const k = Math.max(0, l - threshold) / (1 - threshold);
      const q = ((y >> 2) * QW + (x >> 2)) * 3;
      qa[q] += r * k / 16; qa[q + 1] += g * k / 16; qa[q + 2] += b * k / 16;
    }
  }
  qb.set(qa);
  boxBlur(qa, QW, QH, 2, qt);   // tight glow
  boxBlur(qb, QW, QH, 7, qt);   // wide haze
  // Native-resolution colour: bloom add, gentle contrast and saturation, interlace, then the 16-bit dither
  let motion = 0;
  if (prev && opts.interlace !== false) {
    for (let i = 0; i < src.length; i += 64) motion += Math.abs(src[i] - prev[i]) + Math.abs(src[i + 1] - prev[i + 1]);
    motion /= (src.length / 64) * 2 * 255;
  }
  const comb = motion > 0.045 && motion < 0.16;  // fast motion inside a shot shows the fields; a cut (much bigger change) never does
  for (let y = 0; y < SRC_H; y++) {
    const qy = Math.min(QH - 1, (y + 2) >> 2);
    for (let x = 0; x < SRC_W; x++) {
      const i = (y * SRC_W + x) * 4, o = (y * SRC_W + x) * 3;
      const s = comb && (y & 1) ? prev : src;
      let r = s[i] / 255, g = s[i + 1] / 255, b = s[i + 2] / 255;
      const q = (qy * QW + Math.min(QW - 1, (x + 2) >> 2)) * 3;
      r += bloom * (qa[q] * 0.9 + qb[q] * 0.7);
      g += bloom * (qa[q + 1] * 0.9 + qb[q + 1] * 0.7);
      b += bloom * (qa[q + 2] * 0.9 + qb[q + 2] * 0.7);
      const l = 0.3 * r + 0.59 * g + 0.11 * b;
      r = l + (r - l) * 1.12; g = l + (g - l) * 1.12; b = l + (b - l) * 1.12;
      // CRT black lift and a soft shoulder instead of a hard clip
      const tone = v => { v = 0.02 + v * 0.98; return v < 0.85 ? v : 0.85 + (1 - Math.exp(-(v - 0.85) * 4)) * 0.15; };
      const d = BAYER[(y & 3) * 4 + (x & 3)] / 31;
      native[o] = Math.round((tone(r) + d) * 31) / 31;
      native[o + 1] = Math.round((tone(g) + d) * 31) / 31;
      native[o + 2] = Math.round((tone(b) + d) * 31) / 31;
    }
  }
  // x2 bilinear upscale with colour bleed, scanlines and vignette
  for (let Y = 0; Y < OUT_H; Y++) {
    const sy = Math.min(SRC_H - 1.001, Math.max(0, (Y + 0.5) / 2 - 0.5));
    const y0 = Math.floor(sy), fy = sy - y0;
    const scan = (Y & 1) ? 0.93 : 1.0;
    const vy = (Y / OUT_H - 0.5) * 2;
    for (let X = 0; X < OUT_W; X++) {
      const vx = (X / OUT_W - 0.5) * 2;
      const vig = 1 - 0.18 * (vx * vx * 0.6 + vy * vy * 0.4);
      const o = (Y * OUT_W + X) * 4;
      for (let c = 0; c < 3; c++) {
        const shift = c === 0 ? 0.6 : c === 2 ? -0.6 : 0;   // red and blue land a little apart, like a composite cable
        const sx = Math.min(SRC_W - 1.001, Math.max(0, (X + 0.5) / 2 - 0.5 + shift));
        const x0 = Math.floor(sx), fx = sx - x0;
        const a = native[(y0 * SRC_W + x0) * 3 + c], b = native[(y0 * SRC_W + x0 + 1) * 3 + c];
        const cc = native[((y0 + 1) * SRC_W + x0) * 3 + c], dd = native[((y0 + 1) * SRC_W + x0 + 1) * 3 + c];
        const v = (a * (1 - fx) + b * fx) * (1 - fy) + (cc * (1 - fx) + dd * fx) * fy;
        out[o + c] = v * scan * vig * 255;
      }
      out[o + 3] = 255;
    }
  }
  return out;
}

export async function loadRGBA(file) {
  const img = await loadImage(file);
  const c = createCanvas(SRC_W, SRC_H);
  const ctx = c.getContext('2d');
  ctx.drawImage(img, 0, 0, SRC_W, SRC_H);
  return ctx.getImageData(0, 0, SRC_W, SRC_H).data;
}

if (process.argv[1]?.endsWith('ps2.mjs')) {
  const args = process.argv.slice(2);
  const oi = args.indexOf('--out');
  const dir = oi >= 0 ? args[oi + 1] : '.';
  const files = args.filter((a, i) => !a.startsWith('--') && i !== oi + 1);
  fs.mkdirSync(dir, { recursive: true });
  const c = createCanvas(OUT_W, OUT_H);
  const ctx = c.getContext('2d');
  for (const f of files) {
    const t0 = Date.now();
    const rgba = ps2Frame(await loadRGBA(f));
    const id = ctx.createImageData(OUT_W, OUT_H);
    id.data.set(rgba);
    ctx.putImageData(id, 0, 0);
    const o = path.join(dir, path.basename(f).replace('raw-', ''));
    fs.writeFileSync(o, c.toBuffer('image/png'));
    console.log(`${o} ${Date.now() - t0} ms`);
  }
}
