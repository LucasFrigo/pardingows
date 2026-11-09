// renderFrame(img, v): one Blender frame becomes one finished frame. Scales to 1080x1920 if needed, adds a light plastic bloom, then the captions.
import { createCanvas } from '@napi-rs/canvas';
import { W, H, drawUI } from './ui.mjs';
import { drawFx } from './fx.mjs';

export { W, H };

const full = createCanvas(W, H);
const ctx = full.getContext('2d', { alpha: false });
const GLOW_W = 270, GLOW_H = 480;
const glow = createCanvas(GLOW_W, GLOW_H);
const g = glow.getContext('2d', { alpha: false });
const soft = createCanvas(GLOW_W, GLOW_H);
const s = soft.getContext('2d', { alpha: false });
const BLOOM = 0.16;

// Bright parts only: multiplying the picture by itself pushes everything but the highlights towards black. Blur spreads what's left.
function bloom(img, amount) {
  g.globalCompositeOperation = 'source-over';
  g.imageSmoothingQuality = 'medium';
  g.drawImage(img, 0, 0, GLOW_W, GLOW_H);
  g.globalCompositeOperation = 'multiply';
  g.drawImage(glow, 0, 0);
  g.drawImage(glow, 0, 0);
  s.filter = 'blur(6px)';
  s.drawImage(glow, 0, 0);
  s.filter = 'none';
  ctx.save();
  ctx.globalCompositeOperation = 'screen';
  ctx.globalAlpha = amount;
  ctx.imageSmoothingQuality = 'high';
  ctx.drawImage(soft, 0, 0, W, H);
  ctx.restore();
}

// With captions off, only the picture and its glow are drawn.
export function renderFrame(img, v, { ui = true } = {}) {
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = 'high';
  ctx.drawImage(img, 0, 0, W, H);
  bloom(img, BLOOM);
  drawFx(ctx, v);
  if (ui) drawUI(ctx, v);
  return ctx.getImageData(0, 0, W, H).data;
}
