// The 1930s print: what a frame goes through after the cartoon is drawn and before the captions.
//   weave(frame)                      the gate weave: a sub-pixel jitter and a hair of rotation for drawImage
//   wear(ctx, frame)                  dust specks, the odd hair and vertical scratches, drawn onto the picture
//   filmFrame(data, frame, opts)      in place on RGBA pixels: luminance, a mild S-curve with crushed blacks, exposure
//                                     flicker, vignette, grain, then the sepia ramp (umber black to warm paper)
// Everything is seeded from the frame number, so a re-render is identical.
export const W = 1080, H = 1920;

export function rng(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// Sepia ramp, 256 steps: deep umber at 0, a warm mid brown, paper at 1
const STOPS = [[0, [22, 15, 10]], [0.18, [58, 42, 28]], [0.5, [136, 110, 80]], [0.8, [214, 196, 162]], [1, [248, 238, 214]]];
const LUT = new Uint8ClampedArray(256 * 3);
for (let i = 0; i < 256; i++) {
  const l = i / 255;
  let k = 0;
  while (k < STOPS.length - 2 && l > STOPS[k + 1][0]) k++;
  const [a, ca] = STOPS[k], [b, cb] = STOPS[k + 1];
  const u = (l - a) / (b - a);
  for (let c = 0; c < 3; c++) LUT[i * 3 + c] = ca[c] + (cb[c] - ca[c]) * u;
}

// Vignette: darker corners, a touch darker top and bottom like an old projector's hot spot
const VIG = new Float32Array(W * H);
for (let y = 0; y < H; y++) {
  for (let x = 0; x < W; x++) {
    const dx = (x - W / 2) / (W / 2), dy = (y - H / 2) / (H / 2);
    const r = Math.sqrt(dx * dx * 0.85 + dy * dy * 0.75);
    VIG[y * W + x] = 1 - 0.38 * Math.pow(Math.min(1, r / 1.25), 2.4);
  }
}

// Grain: a few big noise tables, read from a different offset every frame
const NOISE = [];
{
  const r = rng(1931);
  for (let k = 0; k < 3; k++) {
    const n = new Int8Array(W * H + 4096);
    for (let i = 0; i < n.length; i++) n[i] = Math.round((r() + r() + r() - 1.5) * 60);
    NOISE.push(n);
  }
}

export function weave(frame) {
  const r = rng(frame * 7919 + 13);
  // low-frequency wander plus a little per-frame shake
  const wx = Math.sin(frame * 0.37) * 1.2 + (r() - 0.5) * 1.4;
  const wy = Math.sin(frame * 0.23 + 1.3) * 1.6 + (r() - 0.5) * 1.8;
  const rot = (Math.sin(frame * 0.17) * 0.04 + (r() - 0.5) * 0.03) * Math.PI / 180;
  return { dx: wx, dy: wy, rot };
}

export function flicker(frame) {
  const r = rng(frame * 104729 + 7);
  return 1 + Math.sin(frame * 1.7) * 0.012 + (r() - 0.5) * 0.05;
}

// Scratches live for a while: they're seeded by their own slot and age, not the frame
function scratches(frame) {
  const out = [];
  for (let slot = 0; slot < 3; slot++) {
    const life = 18 + slot * 7;
    const gen = Math.floor((frame + slot * 11) / life);
    const r = rng(gen * 31 + slot * 1009);
    if (r() < 0.55) continue;
    const age = (frame + slot * 11) % life;
    out.push({ x: r() * W + age * (r() - 0.5) * 2, light: r() < 0.7, w: 1 + r() * 1.5, alpha: 0.25 + r() * 0.35, top: r() * H * 0.3,
      len: H * (0.5 + r() * 0.5) });
  }
  return out;
}

export function wear(ctx, frame) {
  const r = rng(frame * 2654435761);
  ctx.save();
  // dust: a few specks, mostly dark, a handful bright (dirt on the negative)
  const n = Math.floor(r() * 7);
  for (let i = 0; i < n; i++) {
    const x = r() * W, y = r() * H, rad = 1 + r() * r() * 5;
    ctx.fillStyle = r() < 0.75 ? `rgba(10,8,6,${0.5 + r() * 0.4})` : `rgba(255,250,240,${0.5 + r() * 0.4})`;
    ctx.beginPath();
    ctx.ellipse(x, y, rad, rad * (0.6 + r() * 0.6), r() * Math.PI, 0, Math.PI * 2);
    ctx.fill();
  }
  // a hair now and then
  if (r() < 0.07) {
    let x = r() * W, y = r() * H;
    ctx.strokeStyle = 'rgba(12,9,6,0.7)';
    ctx.lineWidth = 1.4;
    ctx.beginPath();
    ctx.moveTo(x, y);
    for (let k = 0; k < 6; k++) {
      x += (r() - 0.5) * 70;
      y += (r() - 0.3) * 60;
      ctx.quadraticCurveTo(x + (r() - 0.5) * 40, y + (r() - 0.5) * 40, x, y);
    }
    ctx.stroke();
  }
  for (const s of scratches(frame)) {
    ctx.strokeStyle = s.light ? `rgba(255,250,235,${s.alpha})` : `rgba(8,6,4,${s.alpha})`;
    ctx.lineWidth = s.w;
    ctx.beginPath();
    ctx.moveTo(s.x, s.top);
    ctx.lineTo(s.x + (r() - 0.5) * 3, s.top + s.len);
    ctx.stroke();
  }
  ctx.restore();
}

export function filmFrame(d, frame, { gain = 1, grain = 1 } = {}) {
  const fl = flicker(frame) * gain;
  const noise = NOISE[frame % NOISE.length];
  const off = Math.floor(rng(frame * 48271)() * 4000);
  for (let i = 0, p = 0; p < d.length; i++, p += 4) {
    let l = (0.299 * d[p] + 0.587 * d[p + 1] + 0.114 * d[p + 2]) / 255;
    l = (l - 0.06) / 0.9;
    l = l < 0 ? 0 : l > 1 ? 1 : l;
    const s = l < 0.5 ? 2 * l * l : 1 - 2 * (1 - l) * (1 - l);
    l = (l * 0.42 + s * 0.58) * fl * VIG[i];
    // grain is strongest in the mid-tones, as on film
    l += (noise[i + off] / 127) * 0.07 * grain * (0.35 + 1.3 * l * (1 - l));
    const k = (l < 0 ? 0 : l > 1 ? 255 : (l * 255) | 0) * 3;
    d[p] = LUT[k];
    d[p + 1] = LUT[k + 1];
    d[p + 2] = LUT[k + 2];
  }
  return d;
}
