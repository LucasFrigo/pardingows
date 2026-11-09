// renderFrame(img, v, opts): one finished 1080x1920 frame from Blender's raw 540x960 render.
//   raw render -> frame treatment (sway, double vision, black and white) -> 2D effects (fx.mjs)
//   -> PS2 pass (ps2.mjs: dither, bloom, interlace, x2, colour bleed, scanlines) -> HUD (hud.mjs) -> captions (ui.mjs)
// opts.pts are the anchors of the Blender frame on screen (frames.json); opts.ui false leaves the captions off.
import { createCanvas } from '@napi-rs/canvas';
import { ps2Frame, SRC_W, SRC_H, OUT_W, OUT_H } from './ps2.mjs';
import { drawFX, frameTransform } from './fx.mjs';
import { drawHUD } from './hud.mjs';
import { drawUI, TL } from './ui.mjs';

const nat = createCanvas(SRC_W, SRC_H);
const nctx = nat.getContext('2d');
const big = createCanvas(OUT_W, OUT_H);
const bctx = big.getContext('2d');
let prev = null;

export function renderFrame(img, v, { ui = true, pts = {}, fresh = false } = {}) {
  if (fresh) prev = null;
  const t = TL.start + v;
  const tr = frameTransform(t);
  nctx.setTransform(1, 0, 0, 1, 0, 0);
  nctx.fillStyle = '#000';
  nctx.fillRect(0, 0, SRC_W, SRC_H);
  if (tr && (tr.rot || tr.dx)) {
    nctx.save();
    nctx.translate(SRC_W / 2 + tr.dx, SRC_H / 2);
    nctx.rotate(tr.rot);
    nctx.scale(1.07, 1.07);
    nctx.drawImage(img, -SRC_W / 2, -SRC_H / 2, SRC_W, SRC_H);
    if (tr.double) {
      nctx.globalAlpha = tr.double;
      nctx.drawImage(img, -SRC_W / 2 + 16, -SRC_H / 2 + 5, SRC_W, SRC_H);
    }
    nctx.restore();
  } else {
    nctx.drawImage(img, 0, 0, SRC_W, SRC_H);
  }
  drawFX(nctx, t, pts);
  const src = nctx.getImageData(0, 0, SRC_W, SRC_H).data;
  if (tr && tr.desat) {
    const [tr_, tg, tb, ta] = tr.tint || [0, 0, 0, 0];
    for (let i = 0; i < src.length; i += 4) {
      const l = 0.3 * src[i] + 0.59 * src[i + 1] + 0.11 * src[i + 2];
      src[i] = (src[i] + (l - src[i]) * tr.desat) * (1 - ta) + tr_ * ta;
      src[i + 1] = (src[i + 1] + (l - src[i + 1]) * tr.desat) * (1 - ta) + tg * ta;
      src[i + 2] = (src[i + 2] + (l - src[i + 2]) * tr.desat) * (1 - ta) + tb * ta;
    }
  }
  const out = ps2Frame(src, prev);
  prev = new Uint8ClampedArray(src);
  const id = bctx.createImageData(OUT_W, OUT_H);
  id.data.set(out);
  bctx.putImageData(id, 0, 0);
  drawHUD(bctx, t, pts);
  if (ui) drawUI(bctx, v);
  return bctx.getImageData(0, 0, OUT_W, OUT_H).data;
}
