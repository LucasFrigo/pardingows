// renderFrame(img, v): one Blender frame becomes one finished frame. Smooth upscale, bloom and lens flare scaled by the Aero level, then the dialog UI.
import { createCanvas } from '@napi-rs/canvas';
import { W, H, TL, aeroLevel, drawUI } from './ui.mjs';

export { W, H };

const full = createCanvas(W, H);
const ctx = full.getContext('2d', { alpha: false });
const GLOW_W = 270, GLOW_H = 480;
const glow = createCanvas(GLOW_W, GLOW_H);
const g = glow.getContext('2d', { alpha: false });
const soft = createCanvas(GLOW_W, GLOW_H);
const s = soft.getContext('2d', { alpha: false });

// Bright parts only: multiplying the picture by itself pushes everything but the highlights towards black. Blur spreads what's left.
function bloom(img, amount) {
  g.globalCompositeOperation = 'source-over';
  g.imageSmoothingQuality = 'medium';
  g.drawImage(img, 0, 0, GLOW_W, GLOW_H);
  g.globalCompositeOperation = 'multiply';
  g.drawImage(glow, 0, 0);
  g.drawImage(glow, 0, 0);
  s.filter = 'blur(7px)';
  s.drawImage(glow, 0, 0);
  s.filter = 'none';
  ctx.save();
  ctx.globalCompositeOperation = 'screen';
  ctx.globalAlpha = amount;
  ctx.imageSmoothingQuality = 'high';
  ctx.drawImage(soft, 0, 0, W, H);
  ctx.restore();
}

function spot(x, y, r, color, alpha) {
  const gr = ctx.createRadialGradient(x, y, 0, x, y, r);
  gr.addColorStop(0, color);
  gr.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.globalAlpha = alpha;
  ctx.fillStyle = gr;
  ctx.fillRect(x - r, y - r, r * 2, r * 2);
}

// Sun high on the right, with a chain of soft ghosts across the frame
function flare(v, amount) {
  if (amount <= 0) return;
  const sx = 850 + 26 * Math.sin(v * 0.7), sy = 215 + 12 * Math.cos(v * 0.9);
  const twinkle = 1 + 0.08 * Math.sin(v * 9);
  ctx.save();
  ctx.globalCompositeOperation = 'lighter';
  spot(sx, sy, 330 * twinkle, 'rgba(255,250,225,1)', 0.55 * amount);
  spot(sx, sy, 90, 'rgba(255,255,255,1)', 0.9 * amount);
  // Long thin streak
  const st = ctx.createLinearGradient(sx - 520, 0, sx + 520, 0);
  st.addColorStop(0, 'rgba(180,230,255,0)');
  st.addColorStop(0.5, 'rgba(225,245,255,1)');
  st.addColorStop(1, 'rgba(180,230,255,0)');
  ctx.globalAlpha = 0.5 * amount;
  ctx.fillStyle = st;
  ctx.fillRect(sx - 520, sy - 3, 1040, 6);
  const cx = W / 2, cy = 800;
  for (const [t, r, col, a] of [[0.45, 60, 'rgba(120,255,210,1)', 0.16], [0.82, 34, 'rgba(255,190,240,1)', 0.2], [1.3, 92, 'rgba(120,200,255,1)', 0.13], [1.72, 48, 'rgba(190,255,190,1)', 0.14]]) {
    spot(sx + (cx - sx) * t, sy + (cy - sy) * t, r, col, a * amount);
  }
  ctx.restore();
}

// With captions off, only the picture and its glow are drawn.
export function renderFrame(img, v, { ui = true } = {}) {
  const level = aeroLevel(v);
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = 'high';
  ctx.drawImage(img, 0, 0, W, H);
  bloom(img, 0.22 + 0.13 * level);
  flare(v, Math.max(0, (level - 1.5) / 3.5));
  if (ui) drawUI(ctx, v);
  return ctx.getImageData(0, 0, W, H).data;
}
